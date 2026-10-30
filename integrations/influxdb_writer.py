"""InfluxDB Cloud v2 line-protocol writer."""

import os
import requests


def write_points(lines):
    if not lines:
        return

    url = os.getenv(
        "INFLUX_URL",
        "https://us-east-1-1.aws.cloud2.influxdata.com"
    ).rstrip("/")

    bucket = os.getenv("INFLUX_BUCKET", "qa_metrics")
    organization = os.getenv("INFLUX_ORG", "")
    token = os.getenv("INFLUX_TOKEN", "")

    if not token:
        raise RuntimeError(
            "INFLUX_TOKEN is required; bind it from Jenkins Credentials."
        )

    # Validate and join records using actual newline characters.
    valid_lines = [line.strip() for line in lines if line and line.strip()]

    if not valid_lines:
        return

    payload = "\n".join(valid_lines) + "\n"

    params = {
        "bucket": bucket,
        "precision": "ns"
    }

    if organization:
        params["org"] = organization

    response = requests.post(
        f"{url}/api/v2/write",
        params=params,
        data=payload.encode("utf-8"),
        headers={
            "Authorization": f"Token {token}",
            "Content-Type": "text/plain; charset=utf-8",
        },
        timeout=60,
    )

    if response.status_code != 204:
        raise RuntimeError(
            f"InfluxDB Cloud write failed "
            f"HTTP {response.status_code}: {response.text[:1000]}"
        )

    print(f"Successfully wrote {len(valid_lines)} points to InfluxDB.")
