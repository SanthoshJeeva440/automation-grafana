"""Collect GitHub account and repository metrics into InfluxDB (InfluxDB 1.8/InfluxQL compatible)."""
from __future__ import annotations
import os, sys, time, logging
from datetime import datetime, timezone
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from integrations.influxdb_writer import write_points

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger("github-profile-metrics")

GITHUB_API = os.getenv("GITHUB_API_URL", "https://api.github.com").rstrip("/")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "SanthoshJeeva440")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
PER_PAGE = min(max(int(os.getenv("GITHUB_PER_PAGE", "100")), 1), 100)
MAX_PAGES = int(os.getenv("GITHUB_MAX_PAGES", "100"))
INCLUDE_PRIVATE = os.getenv("GITHUB_INCLUDE_PRIVATE", "true").lower() == "true"

class GitHubClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "automation-grafana-metrics-runner",
        })
        if GITHUB_TOKEN:
            self.session.headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    def get(self, path, params=None):
        url = path if path.startswith("http") else f"{GITHUB_API}/{path.lstrip('/')}"
        response = self.session.get(url, params=params, timeout=30)
        if response.status_code == 403 and response.headers.get("X-RateLimit-Remaining") == "0":
            raise RuntimeError("GitHub API rate limit exceeded; use a token or retry after reset.")
        response.raise_for_status()
        return response

    def paginate(self, path, params=None):
        params = dict(params or {})
        params.setdefault("per_page", PER_PAGE)
        items = []
        for page in range(1, MAX_PAGES + 1):
            params["page"] = page
            batch = self.get(path, params).json()
            if not isinstance(batch, list):
                raise RuntimeError(f"Expected list from {path}, received {type(batch).__name__}")
            items.extend(batch)
            if len(batch) < PER_PAGE:
                return items
        raise RuntimeError(f"Pagination exceeded GITHUB_MAX_PAGES={MAX_PAGES} for {path}")

def esc_tag(value):
    return str(value or "unknown").replace("\\", "\\\\").replace(" ", "\\ ").replace(",", "\\,").replace("=", "\\=")

def esc_field(value):
    return str(value or "").replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").replace("\r", " ")

def point(measurement, tags, fields, timestamp):
    tagset = ",".join(f"{k}={esc_tag(v)}" for k, v in tags.items())
    fieldset = ",".join(fields)
    return f"{measurement},{tagset} {fieldset} {timestamp}"

def str_field(name, value):
    return f'{name}="{esc_field(value)}"'

def int_field(name, value):
    return f"{name}={int(value)}i"

def collect():
    gh = GitHubClient()
    now_ns = time.time_ns()
    observed_at = datetime.now(timezone.utc).isoformat()
    lines = []

    # Profile endpoint provides public counts and profile metadata.
    profile = gh.get(f"users/{GITHUB_USERNAME}").json()
    profile_tags = {"username": GITHUB_USERNAME, "account_type": profile.get("type", "User")}
    profile_fields = [
        int_field("followers", profile.get("followers", 0)),
        int_field("public_repos", profile.get("public_repos", 0)),
        int_field("public_gists", profile.get("public_gists", 0)),
        int_field("following", len(gh.paginate(f"users/{GITHUB_USERNAME}/following"))),
        str_field("name", profile.get("name", "")),
        str_field("company", profile.get("company", "")),
        str_field("location", profile.get("location", "")),
        str_field("html_url", profile.get("html_url", "")),
        str_field("created_at", profile.get("created_at", "")),
        str_field("observed_at_utc", observed_at),
    ]
    lines.append(point("github_profile_metrics", profile_tags, profile_fields, now_ns))

    # Owned repositories: authenticated endpoint includes private repos visible to this token.
    repos_endpoint = "user/repos" if GITHUB_TOKEN else f"users/{GITHUB_USERNAME}/repos"
    repos = gh.paginate(repos_endpoint, {"type": "owner", "sort": "created", "direction": "asc"})
    owned = [r for r in repos if r.get("owner", {}).get("login", "").lower() == GITHUB_USERNAME.lower()]
    if not INCLUDE_PRIVATE:
        owned = [r for r in owned if not r.get("private", False)]

    public_count = sum(not r.get("private", False) for r in owned)
    private_count = sum(bool(r.get("private", False)) for r in owned)
    profile_tags = {"username": GITHUB_USERNAME}
    lines.append(point("github_account_repository_summary", profile_tags, [
        int_field("total_owned_repositories", len(owned)),
        int_field("public_repositories", public_count),
        int_field("private_repositories", private_count),
        int_field("forked_repositories", sum(bool(r.get("fork")) for r in owned)),
        int_field("archived_repositories", sum(bool(r.get("archived")) for r in owned)),
        str_field("observed_at_utc", observed_at),
    ], now_ns))

    for repo in owned:
        full_name = repo["full_name"]
        common_tags = {"username": GITHUB_USERNAME, "repository": full_name, "visibility": "private" if repo.get("private") else "public"}
        try:
            commits = gh.paginate(f"repos/{full_name}/commits")
            contributors = gh.paginate(f"repos/{full_name}/contributors")
            pulls = gh.paginate(f"repos/{full_name}/pulls", {"state": "all", "sort": "created", "direction": "asc"})
            open_prs = sum(p.get("state") == "open" for p in pulls)
            closed_prs = len(pulls) - open_prs
            fields = [
                int_field("commits_total", len(commits)),
                int_field("contributors_total", len(contributors)),
                int_field("pull_requests_total", len(pulls)),
                int_field("pull_requests_open", open_prs),
                int_field("pull_requests_closed", closed_prs),
                int_field("forks", repo.get("forks_count", 0)),
                int_field("stars", repo.get("stargazers_count", 0)),
                int_field("watchers", repo.get("subscribers_count", repo.get("watchers_count", 0))),
                int_field("open_issues", repo.get("open_issues_count", 0)),
                int_field("size_kb", repo.get("size", 0)),
                int_field("is_fork", int(bool(repo.get("fork")))),
                int_field("is_archived", int(bool(repo.get("archived")))),
                str_field("default_branch", repo.get("default_branch", "")),
                str_field("language", repo.get("language", "")),
                str_field("created_at", repo.get("created_at", "")),
                str_field("updated_at", repo.get("updated_at", "")),
                str_field("pushed_at", repo.get("pushed_at", "")),
                str_field("html_url", repo.get("html_url", "")),
                str_field("observed_at_utc", observed_at),
            ]
            lines.append(point("github_repository_metrics", common_tags, fields, now_ns))
            LOG.info("%s commits=%d contributors=%d PRs=%d forks=%d", full_name, len(commits), len(contributors), len(pulls), repo.get("forks_count", 0))
        except requests.HTTPError as exc:
            LOG.error("Skipping %s due to GitHub API error: %s", full_name, exc)
        except Exception:
            LOG.exception("Skipping repository %s", full_name)

    # Account-level events are not a substitute for an exact all-time contribution count.
    LOG.info("Collected profile + %d owned repositories; writing %d points", len(owned), len(lines))
    write_points(lines)
    return len(owned), len(lines)

if __name__ == "__main__":
    count, points = collect()
    print(f"GitHub metrics collection completed: repositories={count}, points={points}")
