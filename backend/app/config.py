from functools import lru_cache
from typing import Optional

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_api_base: Optional[HttpUrl] = Field(
        default=None, alias="OPENAI_API_BASE"
    )  # for self-hosted proxies
    github_token: Optional[str] = Field(default=None, alias="GITHUB_TOKEN")
    github_base_url: HttpUrl = Field(
        default="https://api.github.com", alias="GITHUB_BASE_URL"
    )
    github_proxy: Optional[str] = Field(default=None, alias="GITHUB_PROXY")
    cache_ttl_seconds: int = Field(default=3600, alias="CACHE_TTL_SECONDS")
    cors_origins: list[str] = Field(default=["*"], alias="CORS_ORIGINS")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # ignore unrelated env vars to avoid validation errors


@lru_cache
def get_settings() -> Settings:
    return Settings()
