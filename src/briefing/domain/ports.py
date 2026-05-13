from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from briefing.domain.entities import Article
from briefing.domain.results import AdminFilter, SyncResult, SyncStatus
from briefing.domain.value_objects import (
    ArticleId,
    ArticleStatus,
    PayloadHash,
    SourceName,
    Tag,
)


@runtime_checkable
class SourceAdapter(Protocol):
    name: SourceName

    def parse(self, raw_payload: dict) -> Article: ...

    def verify(self, headers: dict, raw_body: bytes) -> bool: ...


@runtime_checkable
class KeywordExtractor(Protocol):
    def extract(self, text: str) -> list[Tag]: ...


@runtime_checkable
class ArticleRepository(Protocol):
    def save(self, article: Article) -> None: ...

    def find_by_hash(self, h: PayloadHash) -> Article | None: ...

    def find_by_id(self, id: ArticleId) -> Article | None: ...

    def list_pending(self, limit: int) -> list[Article]: ...

    def list_for_admin(self, filters: AdminFilter) -> list[Article]: ...

    def update_status(
        self,
        id: ArticleId,
        status: ArticleStatus,
        *,
        output_path: Path | None = None,
        error: str | None = None,
        increment_retry: bool = False,
    ) -> None: ...

    def update_tags(self, id: ArticleId, tags: list[Tag]) -> None: ...

    def count_by_source(self) -> dict[SourceName, int]: ...

    def count_pending(self) -> int: ...


@runtime_checkable
class VaultPublisher(Protocol):
    def publish(self, article: Article) -> Path: ...


@runtime_checkable
class VaultSync(Protocol):
    def commit_and_push(self, message: str) -> SyncResult: ...

    def status(self) -> SyncStatus: ...
