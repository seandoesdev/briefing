from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from briefing.domain.entities import Article
from briefing.domain.results import AdminFilter, SyncResult, SyncStatus
from briefing.domain.value_objects import (
    ArticleId,
    ArticleStatus,
    PayloadHash,
    SourceName,
    Tag,
    payload_hash,
)


@dataclass
class FakeArticleRepository:
    by_id: dict[ArticleId, Article] = field(default_factory=dict)

    def save(self, article: Article) -> None:
        self.by_id[article.id] = article

    def find_by_hash(self, h: PayloadHash) -> Article | None:
        for a in self.by_id.values():
            if a.payload_hash == h:
                return a
        return None

    def find_by_id(self, id: ArticleId) -> Article | None:
        return self.by_id.get(id)

    def list_pending(self, limit: int) -> list[Article]:
        out = [a for a in self.by_id.values() if a.status is ArticleStatus.RECEIVED]
        return out[:limit]

    def list_for_admin(self, filters: AdminFilter) -> list[Article]:
        out = list(self.by_id.values())
        if filters.source is not None:
            out = [a for a in out if a.source == filters.source]
        if filters.status is not None:
            out = [a for a in out if a.status == filters.status]
        return out[filters.offset : filters.offset + filters.limit]

    def update_status(
        self,
        id: ArticleId,
        status: ArticleStatus,
        *,
        output_path: Path | None = None,
        error: str | None = None,
        increment_retry: bool = False,
    ) -> None:
        a = self.by_id[id]
        retry = a.retry_count + (1 if increment_retry else 0)
        new_error = a.error
        if error is not None:
            # Empty string is the "clear" sentinel (since None means "leave unchanged")
            new_error = error if error != "" else None
        self.by_id[id] = Article(
            id=a.id,
            source=a.source,
            external_id=a.external_id,
            payload_hash=a.payload_hash,
            received_at=a.received_at,
            title=a.title,
            body=a.body,
            url=a.url,
            tags=list(a.tags),
            raw_payload=dict(a.raw_payload),
            status=status,
            output_path=output_path or a.output_path,
            error=new_error,
            retry_count=retry,
            processed_at=a.processed_at,
            published_at=a.published_at,
        )

    def update_tags(self, id: ArticleId, tags: list[Tag]) -> None:
        a = self.by_id[id]
        a.tags = list(tags)

    def count_by_source(self) -> dict[SourceName, int]:
        out: dict[SourceName, int] = {}
        for a in self.by_id.values():
            out[a.source] = out.get(a.source, 0) + 1
        return out

    def count_pending(self) -> int:
        return sum(1 for a in self.by_id.values() if a.status is ArticleStatus.RECEIVED)


@dataclass
class FakeExtractor:
    tags: list[Tag] = field(default_factory=lambda: [Tag("AI"), Tag("반도체")])
    raise_on_extract: bool = False

    def extract(self, text: str) -> list[Tag]:
        if self.raise_on_extract:
            raise RuntimeError("nlp failed")
        return list(self.tags)


@dataclass
class FakePublisher:
    written: list[Article] = field(default_factory=list)
    raise_on_publish: bool = False

    def publish(self, article: Article) -> Path:
        if self.raise_on_publish:
            raise RuntimeError("disk full")
        self.written.append(article)
        return Path(f"/vault/{article.source}/{article.received_at.date()}.md")


@dataclass
class FakeSync:
    pushed: int = 0
    fail_next: bool = False

    def commit_and_push(self, message: str) -> SyncResult:
        if self.fail_next:
            self.fail_next = False
            return SyncResult.failure("push rejected")
        self.pushed += 1
        return SyncResult.success(commit_sha=f"sha{self.pushed:04d}", article_count=1)

    def status(self) -> SyncStatus:
        return SyncStatus(
            last_push_at=None, last_commit_sha=None, pending_count=0, last_error=None
        )


def make_article(*, body: str = "본문", source: str = "dooray", payload: dict | None = None) -> Article:
    p = payload or {"text": body}
    return Article(
        id=ArticleId(str(uuid4())),
        source=SourceName(source),
        external_id=None,
        payload_hash=payload_hash(p),
        received_at=datetime(2026, 5, 13, 14, 32),
        title=body[:20],
        body=body,
        url=None,
        tags=[],
        raw_payload=p,
    )
