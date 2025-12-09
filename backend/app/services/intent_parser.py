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
    "ocr": ["ocr", "optical character recognition"],
}

# 需求描述词黑名单（这些词不应该作为搜索关键词）
REQUIREMENT_WORDS = {
    "快", "速度快", "快速", "高效", "高效能", "高性能", "performance", "fast", "quick", "speed",
    "好", "好用", "简单", "容易", "easy", "simple", "good",
    "新", "最新", "最新版", "new", "latest",
    "稳定", "可靠", "stable", "reliable",
    "免费", "开源", "free", "open source",
    "轻量", "轻量级", "lightweight", "light",
    "强大", "powerful", "strong",
    "完整", "complete", "full",
    "专业", "professional", "pro",
}

# 需求描述词到技术关键词的映射
REQUIREMENT_TO_TECH = {
    "快": ["fast", "performance", "optimized", "speed", "efficient"],
    "速度快": ["fast", "performance", "optimized", "speed", "efficient"],
    "快速": ["fast", "performance", "optimized", "speed"],
    "高效": ["efficient", "performance", "optimized"],
    "高性能": ["performance", "high-performance", "optimized"],
    "好用": ["easy", "simple", "user-friendly"],
    "简单": ["simple", "easy", "minimal"],
    "新": ["latest", "modern", "recent"],
    "最新": ["latest", "recent", "up-to-date"],
    "稳定": ["stable", "reliable"],
    "可靠": ["reliable", "stable"],
    "免费": ["free", "open-source"],
    "开源": ["open-source", "open source"],
    "轻量": ["lightweight", "light"],
    "轻量级": ["lightweight", "light"],
    "强大": ["powerful", "feature-rich"],
    "完整": ["complete", "full-featured"],
    "专业": ["professional", "enterprise"],
}


def heuristic_parse(user_query: str) -> ParsedIntent:
    lowered = user_query.lower()
    langs = [lang for lang in COMMON_LANGS if lang in lowered]
    
    # Extract technical keywords, filtering out requirement words
    rough = user_query.replace("，", " ").replace(",", " ").replace("的", " ").split()
    keywords = []
    for kw in rough:
        kw = kw.strip()
        if not kw:
            continue
        # Skip requirement words
        if kw in REQUIREMENT_WORDS or kw.lower() in REQUIREMENT_WORDS:
            # Convert requirement words to tech keywords
            if kw in REQUIREMENT_TO_TECH:
                keywords.extend(REQUIREMENT_TO_TECH[kw])
            elif kw.lower() in REQUIREMENT_TO_TECH:
                keywords.extend(REQUIREMENT_TO_TECH[kw.lower()])
            continue
        # Keep technical keywords
        keywords.append(kw)
    
    # Add Chinese->English hint expansions
    for zh, hints in CHINESE_HINTS.items():
        if zh.lower() in lowered:
            keywords.extend(hints)
    
    # Convert requirement words in query to tech keywords
    for req_word, tech_keywords in REQUIREMENT_TO_TECH.items():
        if req_word in user_query or req_word.lower() in lowered:
            keywords.extend(tech_keywords)
    
    # If no keywords found, use the original query (but clean it)
    if not keywords:
        # Remove requirement words from raw query
        cleaned = user_query
        for req in REQUIREMENT_WORDS:
            cleaned = cleaned.replace(req, " ").replace(req.lower(), " ")
        cleaned = " ".join(cleaned.split())
        if cleaned:
            keywords.append(cleaned)
        else:
            keywords.append(user_query.strip())
    
    # Deduplicate while preserving order
    seen = set()
    deduped: List[str] = []
    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower in seen:
            continue
        seen.add(kw_lower)
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
            "Given a user need, extract ONLY technical keywords (library names, frameworks, tools, technologies).\n"
            "Return JSON only, schema: {\"keywords\":[], \"languages\":[], \"description\":\"...\", \"filters\":[]}.\n"
            "- keywords: 3-6 items, ONLY technical terms (e.g., 'OCR', 'paddleocr', 'tesseract', 'opencv'). "
            "DO NOT include requirement descriptions like 'fast', 'quick', 'good', 'simple', 'easy', '速度快', '好用', '简单' etc. "
            "If user mentions 'fast' or '速度快', convert to technical keywords like 'performance', 'optimized', 'speed' instead. "
            "If the user writes in Chinese, also include reasonable English equivalents (e.g., 抖音→douyin,tiktok; 爬虫→crawler,scraper).\n"
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

