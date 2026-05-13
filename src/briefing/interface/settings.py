from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BRIEFING_", env_file=".env", extra="ignore")

    db_path: Path = Field(default=Path("data/briefing.db"))
    vault_path: Path = Field(default=Path("vault"))
    log_path: Path = Field(default=Path("data/briefing.log"))
    stopwords_path: Path = Field(default=Path("data/stopwords.txt"))

    git_remote: str = "origin"
    git_branch: str = "main"
    git_user_name: str = "briefing-bot"
    git_user_email: str = "briefing@example.com"

    worker_interval_sec: int = 5
    sync_idle_sec: int = 60
    max_retry: int = 3

    dooray_token: str | None = None

    admin_user: str = "admin"
    admin_password: str = "change-me"

    keyword_top_n: int = 5
