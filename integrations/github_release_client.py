import os
import re

import requests
from packaging.version import Version, InvalidVersion


def _version_from_tag(tag):
    """Return a stable semantic version parsed from a tag, or None."""
    match = re.search(
        r"(?<!\d)[vV]?(\d+\.\d+(?:\.\d+)?(?:[-+][0-9A-Za-z.-]+)?)",
        (tag or "").strip(),
    )
    if not match:
        return None

    try:
        version = Version(match.group(1))
    except InvalidVersion:
        return None

    if version.is_prerelease or version.is_devrelease:
        return None
    return version


def latest_stable(repository):
    session = requests.Session()
    session.headers.update({
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })

    if os.getenv("GITHUB_TOKEN"):
        session.headers["Authorization"] = (
            "Bearer " + os.environ["GITHUB_TOKEN"]
        )

    # First, use published stable GitHub releases.
    url = f"https://api.github.com/repos/{repository}/releases?per_page=100"
    response = session.get(url, timeout=30)
    response.raise_for_status()

    candidates = []
    for release in response.json():
        if release.get("draft") or release.get("prerelease"):
            continue

        version = _version_from_tag(release.get("tag_name", ""))
        if version is not None:
            candidates.append({
                "version_obj": version,
                "version": str(version),
                "url": release.get("html_url") or
                       f"https://github.com/{repository}/releases",
                "date": release.get("published_at") or "",
            })

    if candidates:
        latest = max(candidates, key=lambda item: item["version_obj"])
        latest.pop("version_obj")
        return latest

    # Fall back to tags when a project has no GitHub Release objects.
    url = f"https://api.github.com/repos/{repository}/tags?per_page=100"
    response = session.get(url, timeout=30)
    response.raise_for_status()

    candidates = []
    for tag in response.json():
        name = tag.get("name", "")
        version = _version_from_tag(name)
        if version is not None:
            candidates.append({
                "version_obj": version,
                "version": str(version),
                "url": f"https://github.com/{repository}/releases/tag/{name}",
                "date": "",
            })

    if candidates:
        latest = max(candidates, key=lambda item: item["version_obj"])
        latest.pop("version_obj")
        return latest

    raise RuntimeError(
        f"No stable semantic-version GitHub release or tag found "
        f"for {repository}"
    )
