# RepoMan
RepoMan deploys a council of specialized AI agents, each powered by different models, that analyze, debate, critique, and converge on a plan before touching a single line of code. Think of it as an AI engineering firm that audits and rehabilitates repos.

## Elasticsearch integration

RepoMan can ingest GitHub repositories into Elasticsearch for full-text search, semantic search, and analytics.

### Local setup (docker-compose)

1. Copy `.env.example` to `.env` and set `REPOMAN_GITHUB_TOKEN`.
2. Start the stack:

```bash
docker compose up --build -d
```

3. Create indices (idempotent):

```bash
repoman es setup
```

### Ingest + analyze

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

### Search & dashboards API

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
