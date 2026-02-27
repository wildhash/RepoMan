"""GitHub REST API client helpers."""

from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx
import structlog

from repoman.config import Settings

log = structlog.get_logger()


def parse_repo_full_name(value: str) -> str:
    """Parse `owner/repo` from a GitHub repo URL or full_name string."""
    v = value.strip()
    if v.startswith("http://") or v.startswith("https://"):
        parts = v.rstrip("/").split("/")
        if len(parts) >= 2:
            return f"{parts[-2]}/{parts[-1].removesuffix('.git')}"
    return v


@dataclass(slots=True)
class GitHubClient:
    """Minimal async GitHub client with rate limit handling."""

    token: str = ""
    _client: httpx.AsyncClient = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url="https://api.github.com",
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                **({"Authorization": f"Bearer {self.token}"} if self.token else {}),
            },
            timeout=30,
        )

    @classmethod
    def from_settings(cls, settings: Settings) -> GitHubClient:
        return cls(token=settings.github_token)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get_repo(self, repo_full_name: str) -> dict[str, Any]:
        owner, repo = parse_repo_full_name(repo_full_name).split("/", 1)
        return await self._request_json("GET", f"/repos/{owner}/{repo}")

    async def get_languages(self, repo_full_name: str) -> dict[str, int]:
        owner, repo = parse_repo_full_name(repo_full_name).split("/", 1)
        return await self._request_json("GET", f"/repos/{owner}/{repo}/languages")

    async def get_contributors(self, repo_full_name: str, *, limit: int = 200) -> list[dict[str, Any]]:
        owner, repo = parse_repo_full_name(repo_full_name).split("/", 1)
        return await self._paginate(f"/repos/{owner}/{repo}/contributors", limit=limit)

    async def get_readme_text(self, repo_full_name: str) -> str | None:
        owner, repo = parse_repo_full_name(repo_full_name).split("/", 1)
        try:
            data = await self._request_json("GET", f"/repos/{owner}/{repo}/readme")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise

        content = data.get("content")
        if not content:
            return None
        try:
            decoded = base64.b64decode(content).decode("utf-8", errors="ignore")
            return decoded
        except Exception:
            return None

    async def file_exists(self, repo_full_name: str, path: str) -> bool:
        owner, repo = parse_repo_full_name(repo_full_name).split("/", 1)
        try:
            await self._request_json(
                "GET",
                f"/repos/{owner}/{repo}/contents/{path.lstrip('/')}",
            )
            return True
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return False
            raise

    async def list_issues(
        self,
        repo_full_name: str,
        *,
        state: str = "all",
        since: datetime | None = None,
        limit: int = 300,
    ) -> list[dict[str, Any]]:
        owner, repo = parse_repo_full_name(repo_full_name).split("/", 1)
        params: dict[str, Any] = {
            "state": state,
            "per_page": 100,
            "sort": "updated",
            "direction": "desc",
        }
        if since is not None:
            params["since"] = since.astimezone(UTC).isoformat()

        return await self._paginate(f"/repos/{owner}/{repo}/issues", params=params, limit=limit)

    async def search_repositories(self, query: str, *, limit: int = 50) -> list[dict[str, Any]]:
        params = {"q": query, "per_page": min(limit, 100), "sort": "stars", "order": "desc"}
        data = await self._request_json("GET", "/search/repositories", params=params)
        return list(data.get("items") or [])

    async def list_user_repos(self, user_or_org: str, *, limit: int = 200) -> list[dict[str, Any]]:
        info = await self._request_json("GET", f"/users/{user_or_org}")
        kind = (info.get("type") or "").lower()
        base = f"/orgs/{user_or_org}/repos" if kind == "organization" else f"/users/{user_or_org}/repos"
        return await self._paginate(
            base,
            params={"per_page": 100, "sort": "updated", "direction": "desc"},
            limit=limit,
        )

    async def _paginate(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        limit: int,
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        page = 1
        while len(out) < limit:
            p = dict(params or {})
            p.update({"page": page, "per_page": p.get("per_page", 100)})
            data = await self._request_json("GET", path, params=p)
            if not isinstance(data, list) or not data:
                break
            out.extend(data)
            if len(data) < p["per_page"]:
                break
            page += 1
        return out[:limit]

    async def _request_json(self, method: str, path: str, *, params: dict[str, Any] | None = None) -> Any:
        resp = await self._client.request(method, path, params=params)
        await self._respect_rate_limit(resp)
        resp.raise_for_status()
        return resp.json()

    async def _respect_rate_limit(self, resp: httpx.Response) -> None:
        remaining = resp.headers.get("X-RateLimit-Remaining")
        reset = resp.headers.get("X-RateLimit-Reset")
        if remaining is None or reset is None:
            return

        try:
            if int(remaining) > 0:
                return
            reset_ts = int(reset)
        except ValueError:
            return

        now_ts = int(datetime.now(tz=UTC).timestamp())
        sleep_for = max(reset_ts - now_ts, 0) + 1
        log.warning("github_rate_limit_sleep", seconds=sleep_for)
        await asyncio.sleep(sleep_for)
