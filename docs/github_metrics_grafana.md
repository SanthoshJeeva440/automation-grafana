# GitHub account and repository metrics

## Measurements

- `github_profile_metrics`: followers, following, public repository and gist counts.
- `github_account_repository_summary`: total owned repositories split by public/private plus forked/archived counts.
- `github_repository_metrics`: one snapshot per owned repository, including commits, contributors, PR counts, forks, stars, watchers and issue count.

## Metric definitions and caveats

- `commits_total` is the number of commits returned by the repository commits endpoint (default branch history), not every commit across all branches.
- `contributors_total` is GitHub's contributors endpoint count; GitHub may omit anonymous contributors and may return a 202 while building statistics.
- `pull_requests_total` counts PRs in all states (open and closed, including merged, because GitHub treats merged PRs as closed).
- `forks` is the current repository fork count.
- Public/private repo totals depend on the token's accessible scope. Without a token, private repositories cannot be enumerated.
- Followers and following are profile-wide; profile public repo count is the public count provided by GitHub.
- GitHub API has rate limits. Use a read-only token stored in Jenkins Credentials; never commit it.
- This snapshot runner does not claim to calculate a user's total GitHub contribution graph. That graph uses a separate GraphQL contribution calendar.
- The InfluxDB timestamps are collection time, so Grafana can show trends over daily/weekly snapshots.

## Jenkins

Add a Jenkins Secret Text credential with ID `github-read-token`, then bind it to `GITHUB_TOKEN`. Reuse the existing InfluxDB credential as `INFLUX_TOKEN` if your InfluxDB deployment uses token auth.

Example stage:

```groovy
stage('Collect GitHub profile metrics') {
  steps {
    withCredentials([
      string(credentialsId: 'github-read-token', variable: 'GITHUB_TOKEN'),
      string(credentialsId: 'influx-cloud-token', variable: 'INFLUX_TOKEN')
    ]) {
      sh 'python3 runners/github_profile_metrics_runner.py'
    }
  }
}
```

This package uses the InfluxDB Cloud v2 `/api/v2/write` endpoint and bucket `qa_metrics`, matching the cloud URL already configured in this repository. For a local InfluxDB 1.8 instance, adapt the writer to its `/write?db=...` endpoint.

## Example InfluxQL queries

```sql
-- Profile followers / following trend
SELECT LAST("followers"), LAST("following")
FROM "github_profile_metrics"
WHERE $timeFilter
GROUP BY time($__interval) fill(null)

-- Public vs private owned repositories
SELECT LAST("public_repositories"), LAST("private_repositories"), LAST("total_owned_repositories")
FROM "github_account_repository_summary"
WHERE $timeFilter
GROUP BY time($__interval) fill(null)

-- Current repository leaderboard: commits
SELECT LAST("commits_total")
FROM "github_repository_metrics"
WHERE $timeFilter
GROUP BY "repository"

-- PR totals by repository
SELECT LAST("pull_requests_total"), LAST("pull_requests_open"), LAST("pull_requests_closed")
FROM "github_repository_metrics"
WHERE $timeFilter
GROUP BY "repository"

-- Contributors by repository
SELECT LAST("contributors_total")
FROM "github_repository_metrics"
WHERE $timeFilter
GROUP BY "repository"

-- Forks by repository
SELECT LAST("forks")
FROM "github_repository_metrics"
WHERE $timeFilter
GROUP BY "repository"
```
