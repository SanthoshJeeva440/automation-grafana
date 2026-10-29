# automation-grafana

Third repository for Grafana/InfluxDB monitoring, separate from `automation-pipelines` and `automation-ci-config`.

## Layout
- `config/common.properties`: shared non-secret connection settings
- `config/tools.json`: tools and official GitHub repositories to monitor
- `runners/`: Python runner entry points
- `measurements/`: measurement definitions
- `integrations/`: InfluxDB and GitHub clients
- `utils/`: version comparison and email formatting
- `dashboards/`: exported Grafana dashboard JSON
- `tests/`: basic version-comparison tests

## Cloud settings
InfluxDB URL: `https://us-east-1-1.aws.cloud2.influxdata.com`; bucket: `qa_metrics`.
Create a bucket-scoped token with read/write access and save it in Jenkins Credentials as Secret text, ID `influx-cloud-token`. Do not commit credentials.
For InfluxQL reads, create/check a DBRP mapping from database `qa_metrics`, retention policy `autogen`, to the correct bucket. This may require a separate token with DBRP management permission.

## Jenkins
Install Pipeline Utility Steps and Email Extension plugins. Configure Gmail SMTP (`smtp.gmail.com`, port 465 SSL or 587 STARTTLS) using an App Password where supported. The included Jenkinsfile uses `H 8 * * 5`, Friday during the 08:00 hour in Jenkins controller timezone. Configure the controller timezone to Asia/Kolkata for India morning.
First run establishes a baseline. Later runs email only on detected stable upgrades; failures trigger a failure email.

## Grafana
Use InfluxDB Cloud Serverless, InfluxQL, URL above, database `qa_metrics`, and a read-enabled token as the datasource password. Example query:
```sql
SELECT LAST("latest_version") FROM "automation_tool_versions" GROUP BY "tool", "category"
```
Upgrade observations:
```sql
SELECT "latest_version", "previous_version", "upgrade_detected" FROM "automation_tool_versions" WHERE "upgrade_detected" = true
```

## Limitations
Uses GitHub Releases rather than all package registries. Some projects may publish packages without GitHub releases or use unusual version tags. Review output and extend collectors as needed.
