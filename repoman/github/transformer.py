"""Transform GitHub API responses into Elasticsearch documents."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from repoman.embeddings.encoder import EmbeddingEncoder


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        # GitHub uses ISO 8601 timestamps.
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _days_between(start: datetime, end: datetime) -> int:
    return max(int((end - start).total_seconds() // 86400), 0)


def classify_issue_sentiment(text: str) -> str:
    """Cheap sentiment classifier (keyword-based)."""
    t = (text or "").lower()
    if any(w in t for w in ("thank", "awesome", "great", "love")):
        return "positive"
    if any(w in t for w in ("wtf", "angry", "broken", "unusable", "terrible")):
        return "frustrated"
    if any(w in t for w in ("bug", "error", "fail", "crash", "regression")):
        return "negative"
    return "neutral"


def classify_repo_status(last_commit_date: datetime | None) -> str:
    now = datetime.now(tz=UTC)
    if not last_commit_date:
        return "needs_attention"
    age = now - last_commit_date
    if age <= timedelta(days=30):
        return "active"
    if age <= timedelta(days=90):
        return "stale"
    if age >= timedelta(days=180):
        return "abandoned"
    return "needs_attention"


@dataclass(slots=True)
class RepoDerivedScores:
    completeness_score: float
    activity_score: float
    community_score: float

    @property
    def health_score(self) -> float:
        return round(
            (self.completeness_score * 0.3)
            + (self.activity_score * 0.4)
            + (self.community_score * 0.3),
            2,
        )


def compute_activity_score(last_commit_date: datetime | None) -> float:
    if not last_commit_date:
        return 0.0
    now = datetime.now(tz=UTC)
    days = max((now - last_commit_date).days, 0)
    # 0d => 100, 180d+ => 0
    return round(max(0.0, 100.0 * (1.0 - min(days, 180) / 180.0)), 2)


def compute_community_score(stars: int, forks: int, contributors: int) -> float:
    # Soft cap each signal to keep scores in 0-100.
    score = 0.0
    score += min(stars, 5000) / 5000.0 * 50.0
    score += min(forks, 2000) / 2000.0 * 20.0
    score += min(contributors, 200) / 200.0 * 30.0
    return round(min(max(score, 0.0), 100.0), 2)


def compute_completeness_score(*, readme_text: str | None, has_license: bool, has_contributing: bool) -> float:
    readme_ok = bool(readme_text and len(readme_text.strip()) >= 500)
    present = sum([readme_ok, has_license, has_contributing])
    return round((present / 3.0) * 100.0, 2)


def repository_to_document(
    repo: dict[str, Any],
    *,
    readme_text: str | None,
    has_contributing: bool,
    has_license: bool,
    description_embedding: list[float],
    derived_scores: RepoDerivedScores,
) -> dict[str, Any]:
    last_commit_date = _parse_dt(repo.get("pushed_at"))
    return {
        "repo_id": str(repo.get("id", "")),
        "name": repo.get("name") or "",
        "full_name": repo.get("full_name") or "",
        "description": repo.get("description") or "",
        "description_embedding": description_embedding,
        "language": repo.get("language") or "",
        "topics": list(repo.get("topics") or []),
        "stars": int(repo.get("stargazers_count") or 0),
        "forks": int(repo.get("forks_count") or 0),
        "open_issues_count": int(repo.get("open_issues_count") or 0),
        "has_readme": bool(readme_text),
        "has_contributing": has_contributing,
        "has_license": has_license,
        "last_commit_date": (last_commit_date.isoformat() if last_commit_date else None),
        "created_at": repo.get("created_at"),
        "updated_at": repo.get("updated_at"),
        "health_score": derived_scores.health_score,
        "status": classify_repo_status(last_commit_date),
        "recommendations": [],
    }


def issues_to_documents(
    issues: list[dict[str, Any]],
    *,
    repo_full_name: str,
    encoder: EmbeddingEncoder,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    now_dt = now or datetime.now(tz=UTC)
    out: list[dict[str, Any]] = []

    for item in issues:
        created_at = _parse_dt(item.get("created_at")) or now_dt
        updated_at = _parse_dt(item.get("updated_at")) or created_at
        closed_at = _parse_dt(item.get("closed_at"))
        end = closed_at or now_dt
        days_open = _days_between(created_at, end)

        is_pull_request = bool(item.get("pull_request"))
        labels = [
            label.get("name")
            for label in (item.get("labels") or [])
            if isinstance(label, dict) and label.get("name")
        ]
        assignees = [a.get("login") for a in (item.get("assignees") or []) if isinstance(a, dict) and a.get("login")]
        body = item.get("body") or ""

        out.append(
            {
                "issue_id": str(item.get("id", "")),
                "repo_full_name": repo_full_name,
                "title": item.get("title") or "",
                "body": body,
                "body_embedding": encoder.encode(body),
                "state": item.get("state") or "",
                "labels": labels,
                "is_pull_request": is_pull_request,
                "author": (item.get("user") or {}).get("login") or "",
                "assignees": assignees,
                "created_at": created_at.isoformat(),
                "updated_at": updated_at.isoformat(),
                "closed_at": (closed_at.isoformat() if closed_at else None),
                "days_open": days_open,
                "comment_count": int(item.get("comments") or 0),
                "sentiment": classify_issue_sentiment(f"{item.get('title') or ''}\n{body}"),
                "is_stale": (item.get("state") == "open") and ((now_dt - updated_at) >= timedelta(days=30)),
            }
        )

    return out


def build_repo_scores(
    repo: dict[str, Any],
    *,
    readme_text: str | None,
    has_license: bool,
    has_contributing: bool,
    contributors_count: int,
) -> RepoDerivedScores:
    last_commit_date = _parse_dt(repo.get("pushed_at"))
    completeness = compute_completeness_score(
        readme_text=readme_text,
        has_license=has_license,
        has_contributing=has_contributing,
    )
    activity = compute_activity_score(last_commit_date)
    community = compute_community_score(
        stars=int(repo.get("stargazers_count") or 0),
        forks=int(repo.get("forks_count") or 0),
        contributors=contributors_count,
    )
    return RepoDerivedScores(
        completeness_score=completeness,
        activity_score=activity,
        community_score=community,
    )
