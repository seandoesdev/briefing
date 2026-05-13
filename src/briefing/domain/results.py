from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from briefing.domain.value_objects import ArticleStatus, SourceName


@dataclass
class SyncResult:
    ok: bool
    commit_sha: str | None = None
    article_count: int = 0
    error: str | None = None

    @classmethod
    def success(cls, commit_sha: str | None, article_count: int) -> "SyncResult":
        return cls(ok=True, commit_sha=commit_sha, article_count=article_count)

    @classmethod
    def failure(cls, error: str) -> "SyncResult":
        return cls(ok=False, error=error)


@dataclass
class SyncStatus:
    last_push_at: datetime | None
    last_commit_sha: str | None
    pending_count: int
    last_error: str | None


@dataclass
class AdminFilter:
    source: SourceName | None = None
    status: ArticleStatus | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    tag: str | None = None
    query: str | None = None
    limit: int = 50
    offset: int = 0
