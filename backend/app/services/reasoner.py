from typing import Dict, Any

from .llm_client import LLMClient


class Reasoner:
    def __init__(self):
        try:
            self.llm = LLMClient()
        except Exception:
            self.llm = None

    async def explain(self, user_query: str, repo: Dict[str, Any]) -> str:
        fallback = (
            f"{repo.get('full_name')}：活跃度 {repo.get('stargazers_count', 0)}⭐，最近更新 {repo.get('updated_at', '')}，"
            "请查看 README 示例与 issue 活跃度评估可用性。"
        )
        if not self.llm or not self.llm.client:
            return fallback

        system_prompt = (
            "You craft concise, factual recommendations for GitHub repos. "
            "Base your answer only on provided metadata. 1-2 sentences. "
            "Mention suitability, effort level, and any risks (maintenance, docs)."
        )
        repo_snippet = (
            f"Name: {repo.get('full_name')}\n"
            f"Description: {repo.get('description')}\n"
            f"Stars: {repo.get('stargazers_count')}, Updated: {repo.get('updated_at')}, "
            f"Language: {repo.get('language')}\n"
            f"Topics: {', '.join(repo.get('topics', []))}"
        )
        user_prompt = f"User need: {user_query}\nRepo data:\n{repo_snippet}"
        try:
            return await self.llm.chat(system_prompt, user_prompt)
        except Exception:
            return fallback

