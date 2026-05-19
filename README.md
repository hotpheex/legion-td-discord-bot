# Legion TD Tournament Discord Bot

Serverless Discord bot to help manage [Legion TD 2 Nova Cup tournaments](https://beta.legiontd2.com/esports/#about) in the [Tournament Discord Server](https://discord.gg/GJVRgHrGZV)
Runs on Lambda functions exposed via API Gateway written in Troposphere and deployed with Sceptre.

```
.
├── cloudformation <= AWS infrastructure as code
├── scripts        <= CI scripts
└── src
    ├── handler    <= Handles initial request & invokes respective lambda
    ├── checkin    <= Checkin before tournament
    ├── manage     <= Tournament organiser commands
    ├── results    <= Report match results
    ├── libs       <= Shared classes included in all functions
    └── tests
```

Run the test suite:

`src/tests` holds characterization tests that pin the current behaviour of
the `checkin`, `manage` and `results` handlers. All external services
(Google Sheets, Challonge, boto3/SSM, Discord) are mocked; no test makes a
real network call.

```
# one-time setup
python3 -m venv .venv
.venv/bin/pip install pytest pytest-mock pytest-env pynacl gspread requests boto3

# run the suite (config lives in pytest.ini)
.venv/bin/pytest
```

With the project dependencies already installed (e.g. via `pipenv install`)
the suite also runs with a plain `pytest` from the repo root.

Update Discord slash commands:

```
scripts/slash_cmds.py <dev | prod>
```

Deploy changes:

Make sure dependencies are installed: `pipenv install`

```
scripts/deploy.sh <dev | prod>
```

## Parallel-run platform bridge

While the new tournament platform runs alongside this legacy bot, the
`checkin`, `sort_signups` and `results` handlers mirror their events to the
platform's `/legacy/*` endpoints (see `src/libs/platform.py`). The bridge is
**fire-and-forget and fail-open**: the call is made synchronously after the
Discord reply, with a short timeout, and every failure is swallowed so the
bot is never affected.

It is configured via two stack parameters (set as environment variables for
Sceptre, alongside the existing `GOOGLE_API_KEY` etc.):

| Variable                | Stack parameter      | Purpose                                                                 |
| ----------------------- | -------------------- | ----------------------------------------------------------------------- |
| `PLATFORM_BASE_URL_DEV` / `PLATFORM_BASE_URL_PROD` | `PlatformBaseUrl`   | Base URL of the platform API Worker, e.g. `https://api.example.com`.    |
| `LEGACY_BRIDGE_SECRET`  | `LegacyBridgeSecret` | Shared secret; sent in the `x-legacy-bridge-secret` header. Must match the platform's `LEGACY_BRIDGE_SECRET`. |

Leave `PlatformBaseUrl` (or the secret) empty to disable the bridge — the
notifier then simply no-ops.
