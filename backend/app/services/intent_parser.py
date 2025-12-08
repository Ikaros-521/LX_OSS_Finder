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


def heuristic_parse(user_query: str) -> ParsedIntent:
    lowered = user_query.lower()
    langs = [lang for lang in COMMON_LANGS if lang in lowered]
    # simple keyword split by space/punctuation
    keywords = [kw for kw in user_query.replace("，", " ").replace(",", " ").split() if kw]
    if not keywords:
        keywords = [user_query]
    return ParsedIntent(
        keywords=keywords[:5],
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
            "You turn user needs into concise GitHub search hints. "
            "Return JSON with keys: keywords (list), languages (list), description (string), filters (list). "
            "Prefer concrete technology names and avoid hallucinating. Keep keywords short."
        )
        user_prompt = f"User need: {user_query}"
        try:
            content = await self.llm.chat(system_prompt, user_prompt)
            data = ParsedIntent.model_validate_json(content)
            return data
        except Exception:
            return heuristic_parse(user_query)

