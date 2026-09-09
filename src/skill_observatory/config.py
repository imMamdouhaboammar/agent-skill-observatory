from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite+pysqlite:///./skill_observatory.db"
    github_token: str = ""
    github_api_url: str = "https://api.github.com"
    max_repositories_per_query: int = 50
    request_timeout_seconds: float = 30.0
    user_agent: str = "agent-skill-observatory/0.1"

    model_config = SettingsConfigDict(env_prefix="SKILLOBS_", env_file=".env", extra="ignore")
