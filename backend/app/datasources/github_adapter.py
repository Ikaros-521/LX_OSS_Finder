import httpx
from typing import List
from .base import DataSource, RepoCandidate
from ..config import get_settings


class GitHubAdapter(DataSource):
    def __init__(self):
        self.settings = get_settings()
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "LX-OSS-Finder",
        }
        if self.settings.github_token:
            headers["Authorization"] = f"Bearer {self.settings.github_token}"
        self.headers = headers
        client_kwargs = {
            "base_url": str(self.settings.github_base_url),
        }
        if self.settings.github_proxy:
            client_kwargs["proxies"] = self.settings.github_proxy
        self.client = httpx.AsyncClient(**client_kwargs)

    async def search_repositories(
        self, query: str, per_page: int = 10, sort: str | None = None, order: str = "desc"
    ) -> List[RepoCandidate]:
        params = {"q": query, "per_page": per_page}
        if sort and sort != "best":
            params["sort"] = sort
            params["order"] = order
        try:
            resp = await self.client.get("/search/repositories", params=params, headers=self.headers, timeout=20)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            body = exc.response.text
            status = exc.response.status_code
            raise RuntimeError(f"GitHub {status}: {body}") from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"GitHub request error: {type(exc).__name__} {repr(exc)}") from exc

        data = resp.json()
        items = data.get("items", [])
        results: List[RepoCandidate] = []
        for item in items:
            results.append(
                RepoCandidate(
                    full_name=item.get("full_name"),
                    html_url=item.get("html_url"),
                    description=item.get("description"),
                    language=item.get("language"),
                    stargazers_count=item.get("stargazers_count", 0),
                    forks_count=item.get("forks_count", 0),
                    open_issues_count=item.get("open_issues_count", 0),
                    updated_at=item.get("pushed_at") or item.get("updated_at"),
                    topics=item.get("topics", []),
                    default_branch=item.get("default_branch"),
                    owner_type=(item.get("owner") or {}).get("type"),
                    license=(item.get("license") or {}).get("spdx_id"),
                )
            )
        return results

