"""InfluxDB Cloud v2 line-protocol writer, matching automation-grafana's existing cloud settings."""
import os
import requests

def write_points(lines):
    if not lines:
        return
    url = os.getenv("INFLUX_URL", "https://us-east-1-1.aws.cloud2.influxdata.com").rstrip("/")
    bucket = os.getenv("INFLUX_BUCKET", "qa_metrics")
    organization = os.getenv("INFLUX_ORG", "")
    token = os.getenv("INFLUX_TOKEN", "")
    if not token:
        raise RuntimeError("INFLUX_TOKEN is required; bind it from Jenkins Credentials.")
    params = {"bucket": bucket, "precision": "ns"}
    if organization:
        params["org"] = organization
    response = requests.post(
        f"{url}/api/v2/write", params=params,
        data="\\n".join(lines),
        headers={
            "Authorization": f"Token {token}",
            "Content-Type": "text/plain; charset=utf-8",
        },
        timeout=60,
    )
    if response.status_code != 204:
        raise RuntimeError(
            f"InfluxDB Cloud write failed HTTP {response.status_code}: {response.text[:500]}"
        )
