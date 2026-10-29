import os, requests
URL=os.getenv("INFLUX_URL","https://us-east-1-1.aws.cloud2.influxdata.com").rstrip("/")
BUCKET=os.getenv("INFLUX_BUCKET","qa_metrics")
DATABASE=os.getenv("INFLUX_DATABASE","qa_metrics")
RP=os.getenv("INFLUX_RETENTION_POLICY","autogen")
TOKEN=os.getenv("INFLUX_TOKEN","")
def _check():
    if not TOKEN: raise RuntimeError("INFLUX_TOKEN missing; inject it from Jenkins Credentials.")
def latest_version(measurement, slug):
    _check()
    q=f'SELECT latest_version FROM "{measurement}" WHERE tool=\'{slug}\' ORDER BY time DESC LIMIT 1'
    r=requests.get(URL+"/query",params={"db":DATABASE,"rp":RP,"q":q},
      auth=(os.getenv("INFLUX_USERNAME","Santhosh"),TOKEN),timeout=30)
    r.raise_for_status(); data=r.json()
    if data.get("error"): raise RuntimeError(data["error"])
    results=data.get("results",[])
    if results and results[0].get("error"): raise RuntimeError(results[0]["error"])
    if not results or not results[0].get("series") or not results[0]["series"][0].get("values"): return None
    row=dict(zip(results[0]["series"][0]["columns"],results[0]["series"][0]["values"][0]))
    return row.get("latest_version")
def write_point(line):
    _check()
    r=requests.post(URL+"/api/v2/write",params={"bucket":BUCKET,"precision":"ns"},
      headers={"Authorization":"Token "+TOKEN,"Content-Type":"text/plain; charset=utf-8"},data=line,timeout=30)
    if r.status_code!=204: raise RuntimeError(f"InfluxDB write HTTP {r.status_code}: {r.text[:500]}")
