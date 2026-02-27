# RepoMan

RepoMan is a multi-model “agent council” that can ingest GitHub repos into Elasticsearch, score repo health, and (optionally) run a debate-to-consensus pipeline before making code changes.

```text
GitHub -> ingest -> Elasticsearch -> FastAPI -> dashboards
            |
            +-> agent council (audit -> debate -> execute -> validate) (WIP)
```

## MVP scope

**Works today**

- [x] Ingest GitHub repos/issues/PRs into Elasticsearch (`repoman es ingest`)
- [x] Repo health scoring + dashboards backed by Elasticsearch
- [x] A multi-agent consensus loop (requires LLM API keys)

**Roadmap / WIP**

- [ ] Make the 7-phase “transform and ship fixes” flow reproducible and safe by default
- [ ] Stronger sandboxing + least-privilege GitHub token guidance
- [ ] More first-class “repo portfolio” views (org-level insights, cross-repo duplicate detection, etc.)

## Why Elasticsearch

Elasticsearch is the system-of-record for RepoMan because it supports:

- **Full-text search** across repos, issues, and PRs (filters, aggregations, faceting)
- **Vector search** (dense vectors) for semantic similarity
- **Dashboards/analytics** for “repo health” scoring and portfolio-level views

## Quickstart

1. Copy `.env.example` to `.env` and set `REPOMAN_GITHUB_TOKEN`.
2. Start the stack:

```bash
make docker-up
```

3. Create indices (idempotent):

```bash
repoman es setup
```

### 1-command demo

Once your `.env` is configured, you can run:

```bash
make demo
```

## Ingest + analyze

```bash
# Ingest a single repo
repoman es ingest https://github.com/wildhash/RepoMan --analyze

# Or ingest by user/org (top N most recently updated)
repoman es ingest wildhash --limit 10 --analyze

# Optional: raise the per-repo issues/PRs cap (default: REPOMAN_GITHUB_ISSUE_INGEST_LIMIT, env default 300)
repoman es ingest wildhash --limit 10 --issues-limit 1000 --analyze

# Or ingest via GitHub search
repoman es ingest "language:python stars:>1000 vector database" --limit 10
```

## Search & dashboards API

The FastAPI server exposes Elasticsearch-backed endpoints:

```bash
# Full-text repo search
curl "http://localhost:8000/api/search/repositories?q=agent&language=Python"

# Full-text issue search
curl "http://localhost:8000/api/search/issues?q=timeout&repo_full_name=wildhash/RepoMan"

# Semantic repo search
curl -X POST "http://localhost:8000/api/search/semantic/repositories" \
  -H 'content-type: application/json' \
  -d '{"query":"vector search"}'

# Dashboards
curl "http://localhost:8000/api/dashboard/repo-health"
curl "http://localhost:8000/api/dashboard/top-languages"
```
