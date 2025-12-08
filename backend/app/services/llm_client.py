from typing import Optional

from openai import AsyncOpenAI

from ..config import get_settings


class LLMClient:
    def __init__(self):
        settings = get_settings()
        if not settings.openai_api_key:
            # allow caller to handle absence
            self.client = None
            return
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=str(settings.openai_api_base) if settings.openai_api_base else None,
            timeout=20,
            max_retries=2,
        )

    async def chat(self, system_prompt: str, user_prompt: str, model: str = "gpt-4o-mini") -> str:
        if not self.client:
            raise RuntimeError("LLM client not configured")
        resp = await self.client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            temperature=0.3,
            timeout=20,
        )
        return resp.choices[0].message.content or ""
