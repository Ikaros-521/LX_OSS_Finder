import httpx
from typing import List
from .base import DataSource, RepoCandidate
try:
    from ..config import get_settings
except Exception as e:
    from config import get_settings


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
        # httpx proxies should be a dict with protocol keys
        if self.settings.github_proxy:
            # Convert proxy string to httpx format
            proxy_url = self.settings.github_proxy
            if proxy_url.startswith("http://") or proxy_url.startswith("https://"):
                client_kwargs["proxies"] = {"http://": proxy_url, "https://": proxy_url}
            elif proxy_url.startswith("socks5://"):
                # For SOCKS5, need to use httpx with socks support
                client_kwargs["proxies"] = {"http://": proxy_url, "https://": proxy_url}
            else:
                # Default to http
                client_kwargs["proxies"] = {"http://": proxy_url, "https://": proxy_url}
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
                    {
                        "full_name": item.get("full_name"),
                        "html_url": item.get("html_url"),
                        "description": item.get("description"),
                        "language": item.get("language"),
                        "stargazers_count": item.get("stargazers_count", 0),
                        "forks_count": item.get("forks_count", 0),
                        "open_issues_count": item.get("open_issues_count", 0),
                        "updated_at": item.get("pushed_at") or item.get("updated_at"),
                        "topics": item.get("topics", []),
                        "default_branch": item.get("default_branch"),
                        "owner_type": (item.get("owner") or {}).get("type"),
                        "license": (item.get("license") or {}).get("spdx_id"),
                    }
                )
            )
        return results

    async def get_repository(self, full_name: str) -> RepoCandidate | None:
        """根据 full_name 获取单个仓库的详细信息"""
        try:
            resp = await self.client.get(f"/repos/{full_name}", headers=self.headers, timeout=20)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            # 404 或其他错误，返回 None
            return None
        except httpx.RequestError:
            return None

        item = resp.json()
        return RepoCandidate(
            {
                "full_name": item.get("full_name"),
                "html_url": item.get("html_url"),
                "description": item.get("description"),
                "language": item.get("language"),
                "stargazers_count": item.get("stargazers_count", 0),
                "forks_count": item.get("forks_count", 0),
                "open_issues_count": item.get("open_issues_count", 0),
                "updated_at": item.get("pushed_at") or item.get("updated_at"),
                "topics": item.get("topics", []),
                "default_branch": item.get("default_branch"),
                "owner_type": (item.get("owner") or {}).get("type"),
                "license": (item.get("license") or {}).get("spdx_id"),
            }
        )

