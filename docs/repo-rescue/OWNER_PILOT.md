# Repo Rescue owner pilot: first repair

Date: 2026-10-06. Owner: `wildhash`. This is an owner-consented internal pilot,
not a paying customer, accepted customer delivery, or revenue event.

## Reproduced failures

RepoMan base: `a2949be9dcaec601e94ccd55e654f167620a4893`.

- `actionlint` 1.7.7 rejected `.github/workflows/ci.yml:47`: the `env` context
  is unavailable in `jobs.<job>.services.<service>.image`. This explains why
  the workflow could fail before any jobs start.
- The job runs on the host runner, but its Elasticsearch URL used a container
  hostname and the service exposed no host port.
- An unconstrained install selected Elasticsearch Python client 9.5.1 while
  Compose and CI select Elasticsearch server 8.13.0.
- A new regression test reproduced an immediate ingest/search failure for
  repositories both with and without issues. Elasticsearch acknowledged the
  writes before search could see them; `--analyze` could then report the newly
  ingested repository missing.

The repair uses a literal service tag, publishes port 9200 on the runner,
constrains the Python client to major version 8, and refreshes the two input
indices before ingestion returns. The refresh trades one request per ingestion
for predictable immediate reads. Workflow tokens have read-only permissions;
the service is ephemeral and the embedding provider is the local hash encoder.

## Local verification

Python 3.12.14; Elasticsearch Python client 8.19.3 after the repair.

```bash
pip install -e '.[dev]'
ruff check repoman tests
ruff format --check repoman tests
pytest tests/unit -q
actionlint .github/workflows/ci.yml
```

- Baseline: 54 unit tests passed; workflow validation failed.
- Regression before the code fix: 2 tests failed with `Repository owner/pilot
  not found in repoman-repositories`.
- After: 56 unit tests passed; lint, formatting, and workflow validation passed.
- Two existing `datetime.utcnow()` deprecation warnings remain.
- No Docker runtime was available locally. A real Elasticsearch smoke run must
  be confirmed in the pull request's CI; mocks do not establish that result.

## First target: DifficultAI

[Static inventory](difficultai-baseline.json) was produced with RepoMan's existing
`RepoIngester._analyse` on a temporary `git archive` of
`wildhash/difficultai@8c8e558374cc639abe4b0fe627cf7bc5787d471b`.
Only tracked files from that exact commit were scanned; no target code was run
by the inventory operation. The archive was removed afterwards.

The snapshot found 52 files and a file-presence health score of 75/100. **This
score does not mean the product works.** The root-only manifest scanner misses
the nested React/Vite application. This static inventory is not the experimental
multi-model `repoman audit` or an autonomous repair execution.

Separate direct verification found:

- `npm ci --ignore-scripts` and `npm run build` pass in `apps/web/demo`.
- [The previous Pages run](https://github.com/wildhash/difficultai/actions/runs/29208702045)
  built the site, then failed in Configure Pages with `Not Found`.
- The web connection handler leaves the room connected if microphone setup
  fails and can overwrite early transcripts on successful connection.
- The voice worker references legacy `agents.VoiceAssistant` and realtime
  STT/TTS APIs. Live voice compatibility still needs a separate SDK validation
  and a credentialed end-to-end session.

The next bounded repair targets independent web CI and connection cleanup.
Deployment, live voice operation, scorecard durability, customer acceptance,
payments, and revenue are unverified.
