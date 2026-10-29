import os
import re
import requests
from packaging.version import Version, InvalidVersion


def latest_stable(repository):
    session = requests.Session()
    session.headers.update({
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    if os.getenv("GITHUB_TOKEN"):
        session.headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]

    url = f"https://api.github.com/repos/{repository}/releases?per_page=30"
    response = session.get(url, timeout=30)
    response.raise_for_status()

    for release in response.json():
        if release.get("draft") or release.get("prerelease"):
            continue

        tag = release.get("tag_name", "").lstrip("vV")
        match = re.search(
            r"(?<!\d)(\d+\.\d+(?:\.\d+)?(?:[-+][0-9A-Za-z.-]+)?)",
            tag,
        )
        if not match:
            continue

        try:
            version = Version(match.group(1))
            if version.is_prerelease or version.is_devrelease:
                continue
            return {
                "version": str(version),
                "url": release.get(
                    "html_url",
                    f"https://github.com/{repository}/releases",
                ),
                "date": release.get("published_at") or "",
            }
        except InvalidVersion:
            continue

    raise RuntimeError(
        f"No stable semantic-version GitHub release found for {repository}"
    )
