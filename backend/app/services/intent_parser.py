from typing import List

from pydantic import BaseModel

from .llm_client import LLMClient


class ParsedIntent(BaseModel):
    keywords: List[str]
    languages: List[str]
    description: str
    filters: List[str] = []


COMMON_LANGS = {
    "python",
    "java",
    "javascript",
    "typescript",
    "go",
    "rust",
    "php",
    "c++",
    "c#",
    "swift",
    "kotlin",
    "dart",
}

CHINESE_HINTS = {
    "抖音": ["douyin", "tiktok"],
    "爬虫": ["crawler", "scraper"],
    "弹幕": ["danmu", "barrage", "bullet screen"],
    "直播": ["live streaming", "live stream"],
    "短视频": ["short video"],
    "视频": ["video"],
    "下载": ["download"],
    "评论": ["comment"],
    "账号": ["account"],
    "登录": ["login", "auth"],
}


def heuristic_parse(user_query: str) -> ParsedIntent:
    lowered = user_query.lower()
    langs = [lang for lang in COMMON_LANGS if lang in lowered]
    # simple keyword split by space/punctuation
    rough = user_query.replace("，", " ").replace(",", " ").split()
    keywords = [kw.strip() for kw in rough if kw.strip()]
    if user_query.strip():
        # always keep the raw query as a fallback keyword
        keywords.append(user_query.strip())
    # add simple Chinese->English hint expansions
    for zh, hints in CHINESE_HINTS.items():
        if zh in user_query:
            keywords.extend(hints)
    # deduplicate while preserving order
    seen = set()
    deduped: List[str] = []
    for kw in keywords:
        if kw.lower() in seen:
            continue
        seen.add(kw.lower())
        deduped.append(kw)
    return ParsedIntent(
        keywords=deduped[:6],
        languages=langs,
        description=user_query,
        filters=[],
    )


class IntentParser:
    def __init__(self):
        try:
            self.llm = LLMClient()
        except Exception:
            self.llm = None

    async def parse(self, user_query: str) -> ParsedIntent:
        if not self.llm or not self.llm.client:
            return heuristic_parse(user_query)

        system_prompt = (
            "You are an expert search prompt generator for GitHub.\n"
            "Given a user need, produce compact search hints.\n"
            "Return JSON only, schema: {\"keywords\":[], \"languages\":[], \"description\":\"...\", \"filters\":[]}.\n"
            "- keywords: 3-6 items, short tokens (tech names, frameworks, libs); if the user writes in Chinese, also include reasonable English equivalents (e.g., 抖音→douyin,tiktok; 爬虫→crawler,scraper). Always include the raw query as one keyword if unsure.\n"
            "- languages: list of programming languages when explicitly mentioned.\n"
            "- description: brief restatement of the intent.\n"
            "- filters: optional advanced search filters (e.g., framework-specific tags), avoid inventing versions.\n"
            "Do NOT add GitHub syntax (no in:, language:, topic:) here—only raw tokens. Avoid hallucinations."
        )
        user_prompt = f"User need: {user_query}"
        try:
            content = await self.llm.chat(system_prompt, user_prompt)
            data = ParsedIntent.model_validate_json(content)
            # if LLM returns too few keywords, augment with heuristic hints (especially Chinese -> English)
            if len(data.keywords) < 3:
                extra = heuristic_parse(user_query)
                merged = data.keywords + extra.keywords
                # dedup and cap
                seen = set()
                merged_dedup: List[str] = []
                for kw in merged:
                    if kw.lower() in seen:
                        continue
                    seen.add(kw.lower())
                    merged_dedup.append(kw)
                data.keywords = merged_dedup[:6]
                # merge languages as well
                for lang in extra.languages:
                    if lang not in data.languages:
                        data.languages.append(lang)
            return data
        except Exception:
            return heuristic_parse(user_query)

