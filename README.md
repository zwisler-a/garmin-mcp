# garmin-mcp

MCP server that exposes Garmin Connect data (activities, steps, sleep, heart rate,
body battery, HRV, stress, etc.) as tools, backed by the
[`garminconnect`](https://pypi.org/project/garminconnect/) library.

## Setup

1. Copy `.env.example` to `.env` and fill in your Garmin Connect credentials:

   ```
   cp .env.example .env
   ```

2. Install dependencies (already done in `.venv`):

   ```
   .venv/bin/pip install -e .
   ```

3. Call the `login` tool first, before any other tool. It reuses cached session
   tokens from `~/.garminconnect` (override with `GARMIN_TOKEN_STORE`) if present,
   otherwise logs in with `GARMIN_EMAIL`/`GARMIN_PASSWORD`. If your account has MFA
   enabled, `login` returns `status: "needs_mfa"` — check your email/authenticator
   app for the code and call `submit_mfa_code` with it to finish. After a successful
   login, tokens are cached so future runs skip login/MFA until they expire.

## Running via Docker

A prebuilt image is published to Docker Hub as `zwisler/garmin-mcp` (built by the
`.github/workflows/docker-publish.yml` GitHub Actions workflow on every push to
`main` and on `v*` tags).

```
docker run -i --rm \
  --env-file .env \
  -v garmin-mcp-tokens:/data \
  zwisler/garmin-mcp
```

- `-i` keeps stdin open — required, since MCP talks JSON-RPC over stdio.
- `--env-file .env` supplies `GARMIN_EMAIL`/`GARMIN_PASSWORD`.
- The named volume persists cached session tokens (`GARMIN_TOKEN_STORE` defaults
  to `/data/garminconnect` inside the image) across container restarts, so you
  don't have to log in / do MFA every run.

To register this with Claude Code instead of the local venv, point `.mcp.json` at:

```json
{
  "mcpServers": {
    "garmin-connect": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "--env-file", ".env", "-v", "garmin-mcp-tokens:/data", "zwisler/garmin-mcp"]
    }
  }
}
```

### Building and pushing manually

```
docker build -t zwisler/garmin-mcp:latest .
docker push zwisler/garmin-mcp:latest
```

### CI setup

The GitHub Actions workflow needs two repo secrets to push to Docker Hub:

- `DOCKERHUB_USERNAME` — your Docker Hub username
- `DOCKERHUB_TOKEN` — a Docker Hub access token (Account Settings → Security →
  New Access Token), not your password

## Registering with Claude Code

This repo includes a `.mcp.json` pointing at the venv's Python interpreter, so
Claude Code picks it up automatically when running from this directory.

To register manually elsewhere:

```
claude mcp add garmin-connect /Users/zwisler/PycharmProjects/garmin-mcp/.venv/bin/python /Users/zwisler/PycharmProjects/garmin-mcp/server.py
```

## Available tools

- `login` — call this first
- `submit_mfa_code(code)` — only if `login` returned `status: "needs_mfa"`
- `get_user_profile`
- `get_daily_summary(day)`
- `get_steps(day)`
- `get_heart_rate(day)`
- `get_sleep(day)`
- `get_body_battery(start_day, end_day)`
- `get_stress(day)`
- `get_hrv(day)`
- `get_body_composition(day)`
- `get_activities(limit, start)`
- `get_activities_by_date(start_day, end_day, activity_type)`
- `get_activity_details(activity_id)`
- `get_activity_splits(activity_id)`
- `get_race_predictions`
- `get_training_readiness(day)`
- `get_respiration(day)`
- `get_spo2(day)`
- `get_devices`
- `get_personal_records`

All `day` parameters accept `YYYY-MM-DD` and default to today.
