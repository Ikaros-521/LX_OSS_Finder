import json
from datetime import datetime, timedelta
from typing import List, AsyncGenerator

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .config import get_settings
from .datasources.github_adapter import GitHubAdapter
from .schemas import RepoResult, SearchRequest, SearchResponse
from .services.cache import InMemoryCache
from .services.intent_parser import IntentParser
from .services.reasoner import Reasoner
from .services.scoring import compute_score


settings = get_settings()
app = FastAPI(title="LX OSS Finder", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

github = GitHubAdapter()
intent_parser = IntentParser()
reasoner = Reasoner()
cache = InMemoryCache()


def build_search_query(
    keywords: List[str],
    languages: List[str],
    filters: List[str],
    include_name: bool,
    include_description: bool,
    include_readme: bool,
    include_topics: bool,
    pushed_within_days: int,
    min_stars: int,
) -> str:
    def _is_ascii(s: str) -> bool:
        try:
            s.encode("ascii")
            return True
        except UnicodeEncodeError:
            return False

    terms = [f'"{kw}"' if " " in kw else kw for kw in keywords]
    scopes = []
    if include_name:
        scopes.append("name")
    if include_description:
        scopes.append("description")
    if include_readme:
        scopes.append("readme")
    scope_str = f"in:{','.join(scopes)}" if scopes else ""
    advanced = [scope_str] if scope_str else []
    if languages:
        advanced += [f"language:{lang}" for lang in languages]
    if pushed_within_days > 0:
        cutoff = (datetime.utcnow() - timedelta(days=pushed_within_days)).date()
        advanced.append(f"pushed:>{cutoff}")
    if min_stars > 0:
        advanced.append(f"stars:>={min_stars}")
    if include_topics:
        advanced += [f"topic:{kw.lower()}" for kw in keywords if " " not in kw and _is_ascii(kw)]
    advanced.extend(filters)
    return " ".join([*terms, *advanced])


def sse(event: str, data: dict) -> str:
    # default=str converts types like HttpUrl/Enum to JSON-friendly strings
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.post("/search", response_model=SearchResponse)
async def search(body: SearchRequest):
    cached = cache.get(body.query) if body.use_cache else None
    if cached:
        return cached

    try:
        parsed = await intent_parser.parse(body.query)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    # ensure at least user query as keyword to avoid empty searches
    if not parsed.keywords:
        parsed.keywords = [body.query]

    gh_query = build_search_query(
        parsed.keywords,
        parsed.languages,
        parsed.filters,
        include_name=body.include_name,
        include_description=body.include_description,
        include_readme=body.include_readme,
        include_topics=body.include_topics,
        pushed_within_days=body.pushed_within_days,
        min_stars=body.min_stars,
    )
    try:
        repos = await github.search_repositories(
            gh_query, per_page=body.per_page, sort=body.sort, order="desc"
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"GitHub API error: {exc}")

    results: List[RepoResult] = []
    for repo in repos:
        score = compute_score(repo)
        reason = await reasoner.explain(body.query, repo)
        results.append(
            RepoResult(
                name=repo.get("full_name", "").split("/")[-1],
                full_name=repo.get("full_name"),
                html_url=repo.get("html_url"),
                description=repo.get("description"),
                language=repo.get("language"),
                stars=repo.get("stargazers_count", 0),
                updated_at=repo.get("updated_at", ""),
                topics=repo.get("topics", []),
                score=score,
                reason=reason,
            )
        )

    results = sorted(results, key=lambda r: r.score, reverse=True)[: body.limit]
    response = SearchResponse(query=body.query, intent_keywords=parsed.keywords, results=results)
    if body.use_cache:
        cache.set(body.query, response)
    return response


@app.get("/search/stream")
async def search_stream(
    query: str = Query(..., min_length=1),
    use_cache: bool = Query(True),
    per_page: int = Query(12, ge=1, le=50),
    limit: int = Query(10, ge=1, le=50),
    include_name: bool = Query(True),
    include_description: bool = Query(True),
    include_readme: bool = Query(True),
    include_topics: bool = Query(True),
    pushed_within_days: int = Query(365, ge=0, le=2000),
    min_stars: int = Query(0, ge=0),
    sort: str | None = Query("best"),
):
    cached = cache.get(query) if use_cache else None
    if cached:
        async def cached_stream() -> AsyncGenerator[str, None]:
            yield sse("intent", {"keywords": cached.intent_keywords})
            for item in cached.results:
                yield sse("item", item.model_dump(mode="json"))
            yield sse("done", {"count": len(cached.results)})
        return StreamingResponse(cached_stream(), media_type="text/event-stream")

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            parsed = await intent_parser.parse(query)
            if not parsed.keywords:
                parsed.keywords = [query]
            yield sse("intent", {"keywords": parsed.keywords})
        except Exception as exc:
            yield sse("error", {"detail": f"Intent parse failed: {exc}"})
            return

        gh_query = build_search_query(
            parsed.keywords,
            parsed.languages,
            parsed.filters,
            include_name=include_name,
            include_description=include_description,
            include_readme=include_readme,
            include_topics=include_topics,
            pushed_within_days=pushed_within_days,
            min_stars=min_stars,
        )
        yield sse("debug-query", {"github_query": gh_query})
        try:
            repos = await github.search_repositories(gh_query, per_page=per_page, sort=sort, order="desc")
        except Exception as exc:
            yield sse("error", {"detail": f"GitHub API error: {exc}"})
            return

        results: List[RepoResult] = []
        for repo in repos:
            try:
                score = compute_score(repo)
                reason = await reasoner.explain(query, repo)
                item = RepoResult(
                    name=repo.get("full_name", "").split("/")[-1],
                    full_name=repo.get("full_name"),
                    html_url=repo.get("html_url"),
                    description=repo.get("description"),
                    language=repo.get("language"),
                    stars=repo.get("stargazers_count", 0),
                    updated_at=repo.get("updated_at", ""),
                    topics=repo.get("topics", []),
                    score=score,
                    reason=reason,
                )
                results.append(item)
            except Exception as exc:
                yield sse("error", {"detail": f"Scoring error: {exc}"})

        results = sorted(results, key=lambda r: r.score, reverse=True)[:limit]
        for item in results:
            yield sse("item", item.model_dump(mode="json"))
        if use_cache:
            cache.set(query, SearchResponse(query=query, intent_keywords=parsed.keywords, results=results))
        yield sse("done", {"count": len(results)})

    return StreamingResponse(event_generator(), media_type="text/event-stream")

