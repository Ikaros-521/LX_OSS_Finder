from typing import List, Optional
from pydantic import BaseModel, HttpUrl


class SearchRequest(BaseModel):
    query: str
    use_cache: bool = True
    per_page: int = 12
    limit: int = 10  # top N to return after scoring
    include_name: bool = True
    include_description: bool = True
    include_readme: bool = True
    include_topics: bool = True
    pushed_within_days: int = 1825
    min_stars: int = 0


class RepoResult(BaseModel):
    name: str
    full_name: str
    html_url: HttpUrl
    description: Optional[str]
    language: Optional[str]
    stars: int
    updated_at: str
    topics: List[str]
    score: float
    reason: str


class SearchResponse(BaseModel):
    query: str
    intent_keywords: List[str]
    results: List[RepoResult]

