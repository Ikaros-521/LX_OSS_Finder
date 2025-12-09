import json
from loguru import logger
from datetime import datetime, timedelta
from typing import List, AsyncGenerator

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

try:
    from .config import get_settings
    from .datasources.github_adapter import GitHubAdapter
    from .schemas import RepoResult, SearchRequest, SearchResponse
    from .services.cache import InMemoryCache
    from .services.intent_parser import IntentParser
    from .services.reasoner import Reasoner
    from .services.repo_recommender import RepoRecommender
    from .services.scoring import compute_score
except Exception as e:
    from config import get_settings
    from datasources.github_adapter import GitHubAdapter
    from schemas import RepoResult, SearchRequest, SearchResponse
    from services.cache import InMemoryCache
    from services.intent_parser import IntentParser
    from services.reasoner import Reasoner
    from services.repo_recommender import RepoRecommender
    from services.scoring import compute_score

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
repo_recommender = RepoRecommender()
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
    def _dedup_keep(seq: List[str]) -> List[str]:
        seen = set()
        out: List[str] = []
        for s in seq:
            key = s.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(s)
        return out

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
        topic_candidates = [kw for kw in keywords if " " not in kw and _is_ascii(kw)]
        topic_candidates = _dedup_keep(topic_candidates)[:3]
        advanced += [f"topic:{kw.lower()}" for kw in topic_candidates]
    advanced.extend(filters)
    return " ".join([*terms, *advanced])


def select_keywords(keywords: List[str], max_keywords: int = 4) -> List[str]:
    deduped = []
    seen = set()
    for kw in keywords:
        key = kw.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(kw)
    return deduped[:max_keywords] if max_keywords > 0 else deduped


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

    selected_keywords = select_keywords(parsed.keywords, max_keywords=4)

    gh_query = build_search_query(
        selected_keywords,
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

    # fallback: if no results and we had more than 1 keyword, retry with first 2 keywords
    if not repos and len(selected_keywords) > 1:
        narrowed = select_keywords(selected_keywords, max_keywords=2)
        gh_query = build_search_query(
            narrowed,
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
            selected_keywords = select_keywords(parsed.keywords, max_keywords=4)
            yield sse("intent", {"keywords": selected_keywords})
        except Exception as exc:
            yield sse("error", {"detail": f"Intent parse failed: {exc}"})
            return

        async def do_query(keywords: List[str]):
            gh_query_local = build_search_query(
                keywords,
                parsed.languages,
                parsed.filters,
                include_name=include_name,
                include_description=include_description,
                include_readme=include_readme,
                include_topics=include_topics,
                pushed_within_days=pushed_within_days,
                min_stars=min_stars,
            )
            yield sse("debug-query", {"github_query": gh_query_local})
            try:
                repos_local = await github.search_repositories(
                    gh_query_local, per_page=per_page, sort=sort, order="desc"
                )
                yield repos_local
            except Exception as exc:
                yield sse("error", {"detail": f"GitHub API error: {exc}"})
                yield None

        # Parallel: keyword search + LLM recommendation
        # Start keyword search
        repos = None
        logger.info(f"[流式搜索] 开始关键词搜索，关键词: {selected_keywords}")
        async for result in do_query(selected_keywords):
            if isinstance(result, str):
                yield result  # debug or error already formatted
            else:
                repos = result
        if repos is None:
            logger.warning("[流式搜索] 关键词搜索返回 None，可能出错")
            return

        logger.info(f"[流式搜索] 关键词搜索完成，返回 {len(repos) if repos else 0} 个仓库")

        # Fallback with fewer keywords if empty and we had multiple keywords
        if not repos and len(selected_keywords) > 1:
            narrowed = select_keywords(selected_keywords, max_keywords=2)
            logger.info(f"[流式搜索] 关键词搜索结果为空，尝试使用更少的关键词: {narrowed}")
            async for result in do_query(narrowed):
                if isinstance(result, str):
                    yield result
                else:
                    repos = result
            if repos is None:
                logger.warning("[流式搜索] 回退搜索也返回 None")
                return
            logger.info(f"[流式搜索] 回退搜索完成，返回 {len(repos)} 个仓库")

        # Start LLM recommendation in parallel
        llm_recommended_names = []
        try:
            logger.info(f"[流式搜索] 开始调用 LLM 推荐，query={query}")
            llm_recommended_names = await repo_recommender.recommend(query, max_repos=5)
            logger.info(f"[流式搜索] LLM 推荐完成，返回 {len(llm_recommended_names)} 个仓库: {llm_recommended_names}")
        except Exception as e:
            logger.warning(f"[流式搜索] LLM 推荐失败: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"[流式搜索] LLM 推荐异常堆栈:\n{traceback.format_exc()}")
            # LLM recommendation failed, continue with search results only

        # Convert search results to dict for deduplication
        seen = set()
        results: List[RepoResult] = []

        # Process keyword search results first
        logger.info(f"[流式搜索] 开始处理关键词搜索结果，共 {len(repos)} 个仓库")
        for repo in repos:
            full_name = repo.get("full_name")
            if not full_name or full_name in seen:
                continue
            seen.add(full_name)
            try:
                score = compute_score(repo)
                reason = await reasoner.explain(query, repo)
                item = RepoResult(
                    name=full_name.split("/")[-1],
                    full_name=full_name,
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
                # stream as soon as single item is ready
                yield sse("item", item.model_dump(mode="json"))
                logger.debug(f"[流式搜索] 已流式返回关键词搜索结果: {full_name}")
            except Exception as exc:
                logger.error(f"[流式搜索] 处理关键词搜索结果失败: {full_name}, 错误: {exc}")
                yield sse("error", {"detail": f"Scoring error: {exc}"})
        
        logger.info(f"[流式搜索] 关键词搜索结果处理完成，共 {len(results)} 个有效结果")

        # Process LLM recommended repos (fetch details and add if not already seen)
        logger.info(f"[流式搜索] 开始处理 {len(llm_recommended_names)} 个 LLM 推荐仓库")
        for full_name in llm_recommended_names:
            if full_name in seen:
                logger.debug(f"[流式搜索] 跳过已存在的仓库: {full_name}")
                continue
            seen.add(full_name)
            try:
                repo_detail = await github.get_repository(full_name)
                if not repo_detail:
                    logger.warning(f"[流式搜索] 无法获取仓库详情: {full_name}")
                    continue
                # Convert RepoCandidate to dict format for scoring
                repo_dict = {
                    "full_name": repo_detail.get("full_name"),
                    "html_url": repo_detail.get("html_url"),
                    "description": repo_detail.get("description"),
                    "language": repo_detail.get("language"),
                    "stargazers_count": repo_detail.get("stargazers_count", 0),
                    "updated_at": repo_detail.get("updated_at"),
                    "topics": repo_detail.get("topics", []),
                }
                score = compute_score(repo_dict)
                reason = await reasoner.explain(query, repo_dict)
                item = RepoResult(
                    name=full_name.split("/")[-1],
                    full_name=full_name,
                    html_url=repo_detail.get("html_url"),
                    description=repo_detail.get("description"),
                    language=repo_detail.get("language"),
                    stars=repo_detail.get("stargazers_count", 0),
                    updated_at=repo_detail.get("updated_at") or "",
                    topics=repo_detail.get("topics") or [],
                    score=score,
                    reason=reason,
                )
                results.append(item)
                yield sse("item", item.model_dump(mode="json"))
            except Exception as exc:
                yield sse("error", {"detail": f"LLM recommended repo fetch error: {exc}"})

        # Final sort and limit
        results = sorted(results, key=lambda r: r.score, reverse=True)[:limit]
        if use_cache:
            cache.set(query, SearchResponse(query=query, intent_keywords=parsed.keywords, results=results))
        yield sse("done", {"count": len(results)})

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8020)
