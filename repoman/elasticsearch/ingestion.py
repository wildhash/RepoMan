"""GitHub ingestion and analysis pipeline backed by Elasticsearch."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from elasticsearch import AsyncElasticsearch

from repoman.analysis.completeness import CompletenessResult, compute_completeness
from repoman.analysis.direction import assess_repo_direction
from repoman.analysis.duplicates import DuplicateIssueGroup, find_duplicate_issue_groups
from repoman.analysis.recommendations import ActionItem, generate_action_items
from repoman.analysis.staleness import StaleCounts, query_stale_counts
from repoman.config import Settings
from repoman.elasticsearch.constants import ANALYSIS_DATA_STREAM, ISSUES_INDEX, REPOSITORIES_INDEX
from repoman.elasticsearch.indexer import bulk_index
from repoman.embeddings.encoder import EmbeddingEncoder, create_encoder
from repoman.github.fetcher import GitHubClient, parse_repo_full_name
from repoman.github.transformer import (
    RepoDerivedScores,
    build_repo_scores,
    compute_activity_score,
    compute_community_score,
    compute_completeness_score,
    issues_to_documents,
    repository_to_document,
)

log = structlog.get_logger()


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _recommendations_from_action_items(items: list[ActionItem]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in items:
        out.append({"type": item.category, "severity": item.priority, "message": item.description})
    return out


class ElasticsearchIngestionService:
    """Fetch GitHub data and index into Elasticsearch."""

    def __init__(
        self,
        config: Settings,
        *,
        es: AsyncElasticsearch,
        github: GitHubClient | None = None,
        encoder: EmbeddingEncoder | None = None,
    ) -> None:
        self._config = config
        self._es = es
        self._github = github or GitHubClient.from_settings(config)
        self._encoder = encoder or create_encoder(config)

    async def aclose(self) -> None:
        await self._github.aclose()

    async def ingest_input(self, value: str, *, limit: int = 20) -> list[str]:
        """Resolve an input (repo URL, user/org, or search query) to repo full_names."""
        v = (value or "").strip()
        if not v:
            return []

        if v.startswith("http://") or v.startswith("https://") or v.count("/") == 1:
            return [parse_repo_full_name(v)]

        if " " in v or ":" in v:
            items = await self._github.search_repositories(v, limit=limit)
            out: list[str] = []
            for item in items:
                full_name = item.get("full_name")
                if isinstance(full_name, str) and full_name:
                    out.append(full_name)
            return out

        repos = await self._github.list_user_repos(v, limit=limit)
        out_repos: list[str] = []
        for repo in repos:
            full_name = repo.get("full_name")
            if isinstance(full_name, str) and full_name:
                out_repos.append(full_name)
        return out_repos

    async def ingest_repo(self, repo_input: str, *, issues_limit: int | None = None) -> dict[str, Any]:
        """Ingest a single repo and its issues/PRs."""
        repo_full_name = parse_repo_full_name(repo_input)
        repo = await self._github.get_repo(repo_full_name)

        readme_text = await self._github.get_readme_text(repo_full_name)
        has_contributing = await self._file_exists_any(repo_full_name, ["CONTRIBUTING.md", "contributing.md"])
        has_license = await self._file_exists_any(repo_full_name, ["LICENSE", "LICENSE.md", "license", "license.md"])
        has_ci = await self._file_exists_any(
            repo_full_name,
            [".github/workflows", ".travis.yml", "Jenkinsfile", ".circleci"],
        )
        has_tests = await self._file_exists_any(repo_full_name, ["tests", "test", "__tests__"])
        has_pm = await self._file_exists_any(
            repo_full_name,
            [
                "package.json",
                "pyproject.toml",
                "requirements.txt",
                "go.mod",
                "Cargo.toml",
                "pom.xml",
            ],
        )

        completeness: CompletenessResult = compute_completeness(
            readme_text=readme_text,
            has_license=has_license,
            has_contributing=has_contributing,
            has_ci_config=has_ci,
            has_tests=has_tests,
            has_package_manager_config=has_pm,
        )

        contributors = await self._github.get_contributors(repo_full_name, limit=200)
        derived: RepoDerivedScores = build_repo_scores(
            repo,
            readme_text=readme_text,
            has_license=has_license,
            has_contributing=has_contributing,
            contributors_count=len(contributors),
        )
        description = repo.get("description") or ""
        description_embedding = self._encoder.encode(description)

        repo_doc = repository_to_document(
            repo,
            readme_text=readme_text,
            has_contributing=has_contributing,
            has_license=has_license,
            description_embedding=description_embedding,
            derived_scores=derived,
        )

        # Index repository metadata.
        await self._es.index(index=REPOSITORIES_INDEX, id=repo_doc["repo_id"], document=repo_doc, refresh=False)

        # Issues/PRs
        effective_issues_limit = (
            self._config.github_issue_ingest_limit if issues_limit is None else issues_limit
        )
        issues = await self._github.list_issues(
            repo_full_name,
            state="all",
            since=_now() - timedelta(days=365),
            limit=effective_issues_limit,
        )
        issue_docs = issues_to_documents(issues, repo_full_name=repo_full_name, encoder=self._encoder)

        actions = [
            {
                "_op_type": "index",
                "_index": ISSUES_INDEX,
                "_id": d["issue_id"],
                "_source": d,
            }
            for d in issue_docs
            if d.get("issue_id")
        ]
        if actions:
            await bulk_index(self._es, actions)

        log.info(
            "es_ingest_completed",
            repo_full_name=repo_full_name,
            issues_indexed=len(actions),
        )

        return {
            "repo_full_name": repo_full_name,
            "repo_id": repo_doc.get("repo_id"),
            "issues_indexed": len(actions),
            "completeness_score": completeness.completeness_score,
            "missing_elements": completeness.missing_elements,
            "health_score": derived.health_score,
        }

    async def analyze_repo(self, repo_full_name: str) -> dict[str, Any]:
        """Run analysis powered by Elasticsearch queries and index results."""
        repo_doc = await self._get_repo_doc(repo_full_name)

        completeness_score = compute_completeness_score(
            readme_text=("x" * 500 if repo_doc.get("has_readme") else None),
            has_license=bool(repo_doc.get("has_license")),
            has_contributing=bool(repo_doc.get("has_contributing")),
        )

        last_commit = repo_doc.get("last_commit_date")
        last_commit_dt = (
            datetime.fromisoformat(last_commit) if isinstance(last_commit, str) and last_commit else None
        )
        activity_score = compute_activity_score(last_commit_dt)
        community_score = compute_community_score(
            stars=int(repo_doc.get("stars") or 0),
            forks=int(repo_doc.get("forks") or 0),
            contributors=0,
        )

        stale: StaleCounts = await query_stale_counts(self._es, repo_full_name=repo_full_name)
        duplicates: list[DuplicateIssueGroup] = await find_duplicate_issue_groups(
            self._es, repo_full_name=repo_full_name
        )
        direction = await assess_repo_direction(
            self._es,
            repo_full_name=repo_full_name,
            repo_topics=list(repo_doc.get("topics") or []),
            repo_description=repo_doc.get("description") or "",
        )

        missing_elements = []
        if not repo_doc.get("has_readme"):
            missing_elements.append("README")
        if not repo_doc.get("has_license"):
            missing_elements.append("LICENSE")
        if not repo_doc.get("has_contributing"):
            missing_elements.append("CONTRIBUTING")

        action_items = generate_action_items(
            missing_elements=missing_elements,
            stale_issues_count=stale.stale_issues_count,
            stale_prs_count=stale.stale_prs_count,
            duplicate_groups=duplicates,
            direction_diverges=direction.diverges,
        )

        analyzed_at = _now()
        analysis_doc = {
            "@timestamp": analyzed_at.isoformat(),
            "repo_full_name": repo_full_name,
            "analyzed_at": analyzed_at.isoformat(),
            "completeness_score": completeness_score,
            "activity_score": activity_score,
            "community_score": community_score,
            "missing_elements": missing_elements,
            "duplicate_issue_groups": [asdict(d) for d in duplicates],
            "stale_issues_count": stale.stale_issues_count,
            "stale_prs_count": stale.stale_prs_count,
            "direction_assessment": direction.summary,
            "action_items": [asdict(i) for i in action_items],
        }
        await self._es.index(index=ANALYSIS_DATA_STREAM, document=analysis_doc, refresh=False)

        # Backfill repo recommendations for simpler querying.
        repo_id = repo_doc.get("repo_id")
        if not isinstance(repo_id, str) or not repo_id:
            raise RuntimeError("Repository document is missing repo_id")
        await self._es.update(
            index=REPOSITORIES_INDEX,
            id=repo_id,
            doc={"recommendations": _recommendations_from_action_items(action_items)},
            refresh=False,
        )

        return analysis_doc

    async def _file_exists_any(self, repo_full_name: str, paths: list[str]) -> bool:
        for p in paths:
            if await self._github.file_exists(repo_full_name, p):
                return True
        return False

    async def _get_repo_doc(self, repo_full_name: str) -> dict[str, Any]:
        resp = await self._es.search(
            index=REPOSITORIES_INDEX,
            size=1,
            query={"term": {"full_name": repo_full_name}},
        )
        hits = (resp.get("hits") or {}).get("hits") or []
        if not hits:
            raise RuntimeError(
                f"Repository {repo_full_name} not found in {REPOSITORIES_INDEX}. Run ingestion first."
            )
        return hits[0].get("_source") or {}
