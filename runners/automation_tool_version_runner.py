import json,os,sys,time
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from integrations.github_release_client import latest_stable
from integrations.influxdb_client import latest_version,write_point
from utils.version_comparator import is_upgrade
TOOLS=json.loads((ROOT/"config/tools.json").read_text())
REPORT=ROOT/"upgrade_report.json"; MEAS="automation_tool_versions"
def tag(v): return str(v).replace("\\","\\\\").replace(" ","\\ ").replace(",","\\,").replace("=","\\=")
def field(v): return str(v).replace("\\","\\\\").replace('"','\\"').replace("\\n"," ")
def main():
    report={"checked_at_utc":datetime.now(timezone.utc).isoformat(),"bucket":os.getenv("INFLUX_BUCKET","qa_metrics"),"measurement":MEAS,"checked_count":0,"upgrades":[],"errors":[]}
    ts=time.time_ns()
    for t in TOOLS:
        try:
            latest=latest_stable(t["repository"]); previous=latest_version(MEAS,t["slug"]); upgrade=is_upgrade(previous,latest["version"])
            tags=f'tool={tag(t["slug"])},category={tag(t["category"])},source=github'
            fields=[f'latest_version="{field(latest["version"])}"',f'previous_version="{field(previous or "unknown")}"',f'upgrade_detected={str(upgrade).lower()}',f'release_url="{field(latest["url"])}"',f'release_date="{field(latest["date"])}"',f'repository="{field(t["repository"])}"',f'tool_name="{field(t["name"])}"']
            write_point(f'{MEAS},{tags} {",".join(fields)} {ts}')
            report["checked_count"]+=1
            print(f'{t["name"]}: {previous or "BASELINE"} -> {latest["version"]}; upgraded={upgrade}')
            if upgrade: report["upgrades"].append({"name":t["name"],"category":t["category"],"previous_version":previous,"latest_version":latest["version"],"release_url":latest["url"],"release_date":latest["date"]})
        except Exception as e:
            report["errors"].append({"tool":t["name"],"error":str(e)}); print(f'ERROR {t["name"]}: {e}',file=sys.stderr)
    REPORT.write_text(json.dumps(report,indent=2))
    print(f'Checked {report["checked_count"]}/{len(TOOLS)}; upgrades={len(report["upgrades"])}; errors={len(report["errors"])}')
    return 2 if report["errors"] else 0
if __name__=="__main__": raise SystemExit(main())
