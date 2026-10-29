import os,re,requests
from packaging.version import Version,InvalidVersion
def latest_stable(repository):
    s=requests.Session()
    s.headers.update({"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28"})
    if os.getenv("GITHUB_TOKEN"): s.headers["Authorization"]="Bearer "+os.environ["GITHUB_TOKEN"]
    r=s.get(f'https://api.github.com/repos/{repository}/releases?per_page=30',timeout=30); r.raise_for_status()
    for rel in r.json():
        if rel.get("draft") or rel.get("prerelease"): continue
        m=re.search(r'(?<!\\d)(\\d+\\.\\d+(?:\\.\\d+)?(?:[-+][0-9A-Za-z.-]+)?)',rel.get("tag_name","").lstrip("vV"))
        if not m: continue
        try:
            v=Version(m.group(1))
            if v.is_prerelease or v.is_devrelease: continue
            return {"version":str(v),"url":rel.get("html_url",f'https://github.com/{repository}/releases'),"date":rel.get("published_at") or ""}
        except InvalidVersion: pass
    raise RuntimeError(f"No stable semantic-version GitHub release found for {repository}")
