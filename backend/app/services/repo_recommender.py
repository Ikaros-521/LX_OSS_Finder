import json
import re
from typing import List, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from .llm_client import LLMClient


class RepoRecommender:
    """使用 LLM 基于用户需求推荐知名的 GitHub 仓库"""

    def __init__(self):
        try:
            self.llm = LLMClient()
        except Exception:
            self.llm = None

    async def recommend(self, user_query: str, max_repos: int = 5) -> List[str]:
        """
        基于用户需求推荐 GitHub 仓库的 full_name 列表
        返回格式: ["owner/repo1", "owner/repo2", ...]
        """
        logger.info(f"[LLM推荐] 开始推荐，query={user_query}, max_repos={max_repos}")
        if not self.llm or not self.llm.client:
            logger.warning("[LLM推荐] LLM client 未初始化，跳过推荐")
            return []

        system_prompt = (
            "You are a GitHub repository expert. Based on user needs, recommend well-known, "
            "actively maintained GitHub repositories.\n\n"
            "IMPORTANT: You MUST return ONLY a valid JSON array of repository full names. "
            "Format: [\"owner/repo-name\", \"owner/repo-name\", ...]\n"
            "Do NOT include any explanations, markdown code blocks, or other text. "
            "Just the JSON array.\n"
            "Example output: [\"microsoft/vscode\", \"facebook/react\", \"vercel/next.js\"]"
        )
        user_prompt = (
            f"User need: {user_query}\n\n"
            f"Recommend exactly {max_repos} GitHub repositories that best match this need. "
            "Return ONLY a JSON array like: [\"owner1/repo1\", \"owner2/repo2\", ...]"
        )

        try:
            # Use default model from config (no need to pass model explicitly)
            logger.info(f"[LLM推荐] 调用 LLM API")
            response = await self.llm.chat(system_prompt, user_prompt)
            logger.debug(f"[LLM推荐] 收到原始响应 (query={user_query}):\n{response}")
            
            # 尝试提取 JSON 数组
            cleaned = response.strip()
            # 移除可能的 markdown 代码块标记
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.MULTILINE)
                cleaned = re.sub(r"\s*```\s*$", "", cleaned, flags=re.MULTILINE)
            cleaned = cleaned.strip()
            logger.debug(f"[LLM推荐] 清理后:\n{cleaned}")

            # 尝试从文本中提取 JSON 数组（更宽松的解析）
            # 先尝试直接解析
            try:
                repos = json.loads(cleaned)
            except json.JSONDecodeError:
                # 如果直接解析失败，尝试提取方括号内的内容
                match = re.search(r'\[.*?\]', cleaned, re.DOTALL)
                if match:
                    try:
                        repos = json.loads(match.group(0))
                        logger.debug(f"[LLM推荐] 从文本中提取到 JSON: {match.group(0)}")
                    except json.JSONDecodeError:
                        logger.error(f"[LLM推荐] JSON 解析失败，无法提取有效数组")
                        return []
                else:
                    logger.error(f"[LLM推荐] 未找到 JSON 数组格式")
                    return []

            if isinstance(repos, list):
                # 验证格式并过滤
                valid = []
                for repo in repos[:max_repos]:
                    if isinstance(repo, str) and "/" in repo and len(repo.split("/")) == 2:
                        valid.append(repo)
                logger.debug(f"[LLM推荐] 解析成功，有效仓库数: {len(valid)}, 列表: {valid}")
                return valid
            else:
                logger.warning(f"[LLM推荐] 解析结果不是列表: {type(repos)}, 值: {repos}")
                return []
        except json.JSONDecodeError as e:
            logger.error(f"[LLM推荐] JSON 解析失败: {e}")
            logger.error(f"[LLM推荐] 原始响应: {response}")
            return []
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            logger.error(f"[LLM推荐] 异常: {error_type}: {error_msg}")
            logger.exception("[LLM推荐] 异常堆栈:")
            return []

