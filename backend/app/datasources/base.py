from typing import Protocol, List, Optional


class RepoCandidate(dict):
    """Lightweight mapping to hold repository metadata."""

    full_name: str
    html_url: str
    description: Optional[str]
    language: Optional[str]
    stargazers_count: int
    forks_count: int
    open_issues_count: int
    updated_at: str
    topics: List[str]
    default_branch: str
    owner_type: Optional[str]
    license: Optional[str]


class DataSource(Protocol):
    async def search_repositories(self, query: str, per_page: int = 10) -> List[RepoCandidate]:
        ...

