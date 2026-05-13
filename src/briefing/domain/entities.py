from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from briefing.domain.value_objects import (
    ArticleId,
    ArticleStatus,
    PayloadHash,
    SourceName,
    Tag,
)


@dataclass
class Article:
    id: ArticleId
    source: SourceName
    external_id: str | None
    payload_hash: PayloadHash
    received_at: datetime
    title: str
    body: str
    url: str | None
    tags: list[Tag]
    raw_payload: dict
    status: ArticleStatus = ArticleStatus.RECEIVED
    output_path: Path | None = None
    error: str | None = None
    retry_count: int = 0
    processed_at: datetime | None = None
    published_at: datetime | None = None

    def with_status(
        self,
        status: ArticleStatus,
        *,
        output_path: Path | None = None,
        error: str | None = None,
        processed_at: datetime | None = None,
        published_at: datetime | None = None,
    ) -> "Article":
        return Article(
            id=self.id,
            source=self.source,
            external_id=self.external_id,
            payload_hash=self.payload_hash,
            received_at=self.received_at,
            title=self.title,
            body=self.body,
            url=self.url,
            tags=list(self.tags),
            raw_payload=dict(self.raw_payload),
            status=status,
            output_path=output_path or self.output_path,
            error=error if error is not None else self.error,
            retry_count=self.retry_count,
            processed_at=processed_at or self.processed_at,
            published_at=published_at or self.published_at,
        )
