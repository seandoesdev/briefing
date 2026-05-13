from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from briefing.domain.entities import Article
from briefing.domain.results import AdminFilter
from briefing.domain.value_objects import (
    ArticleId,
    ArticleStatus,
    PayloadHash,
    SourceName,
    Tag,
)


class SqliteArticleRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    @staticmethod
    def _row_to_article(row: sqlite3.Row, tags: list[str]) -> Article:
        return Article(
            id=ArticleId(row["id"]),
            source=SourceName(row["source"]),
            external_id=row["external_id"],
            payload_hash=PayloadHash(row["payload_hash"]),
            received_at=_to_dt(row["received_at"]),
            title=row["title"],
            body=row["body"],
            url=row["url"],
            tags=[Tag(t) for t in tags],
            raw_payload=json.loads(row["raw_payload"]),
            status=ArticleStatus(row["status"]),
            output_path=Path(row["output_path"]) if row["output_path"] else None,
            error=row["error"],
            retry_count=row["retry_count"],
            processed_at=_to_dt(row["processed_at"]) if row["processed_at"] else None,
            published_at=_to_dt(row["published_at"]) if row["published_at"] else None,
        )

    def _tags_for(self, id: str) -> list[str]:
        rows = self._conn.execute(
            "SELECT tag FROM article_tags WHERE article_id = ? ORDER BY tag", (id,)
        ).fetchall()
        return [r["tag"] for r in rows]

    def save(self, article: Article) -> None:
        self._conn.execute(
            """
            INSERT INTO articles
              (id, source, external_id, payload_hash, received_at, title, body, url,
               raw_payload, status, output_path, error, retry_count,
               processed_at, published_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                article.id,
                article.source,
                article.external_id,
                article.payload_hash,
                article.received_at,
                article.title,
                article.body,
                article.url,
                json.dumps(article.raw_payload, ensure_ascii=False),
                article.status.value,
                str(article.output_path) if article.output_path else None,
                article.error,
                article.retry_count,
                article.processed_at,
                article.published_at,
            ),
        )

    def find_by_id(self, id: ArticleId) -> Article | None:
        row = self._conn.execute("SELECT * FROM articles WHERE id = ?", (id,)).fetchone()
        if not row:
            return None
        return self._row_to_article(row, self._tags_for(row["id"]))

    def find_by_hash(self, h: PayloadHash) -> Article | None:
        row = self._conn.execute(
            "SELECT * FROM articles WHERE payload_hash = ?", (h,)
        ).fetchone()
        if not row:
            return None
        return self._row_to_article(row, self._tags_for(row["id"]))

    def list_pending(self, limit: int) -> list[Article]:
        rows = self._conn.execute(
            "SELECT * FROM articles WHERE status = ? ORDER BY received_at LIMIT ?",
            (ArticleStatus.RECEIVED.value, limit),
        ).fetchall()
        return [self._row_to_article(r, self._tags_for(r["id"])) for r in rows]

    def list_for_admin(self, filters: AdminFilter) -> list[Article]:
        clauses: list[str] = []
        params: list = []
        if filters.source is not None:
            clauses.append("source = ?")
            params.append(filters.source)
        if filters.status is not None:
            clauses.append("status = ?")
            params.append(filters.status.value)
        if filters.date_from is not None:
            clauses.append("received_at >= ?")
            params.append(filters.date_from)
        if filters.date_to is not None:
            clauses.append("received_at < ?")
            params.append(filters.date_to)
        if filters.query:
            clauses.append("(title LIKE ? OR body LIKE ?)")
            q = f"%{filters.query}%"
            params.extend([q, q])
        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        sql = (
            f"SELECT * FROM articles {where} "
            f"ORDER BY received_at DESC LIMIT ? OFFSET ?"
        )
        params.extend([filters.limit, filters.offset])
        rows = self._conn.execute(sql, params).fetchall()
        out = [self._row_to_article(r, self._tags_for(r["id"])) for r in rows]
        if filters.tag:
            out = [a for a in out if filters.tag in a.tags]
        return out

    def update_status(
        self,
        id: ArticleId,
        status: ArticleStatus,
        *,
        output_path: Path | None = None,
        error: str | None = None,
        increment_retry: bool = False,
    ) -> None:
        sets: list[str] = ["status = ?"]
        params: list = [status.value]
        if output_path is not None:
            sets.append("output_path = ?")
            params.append(str(output_path))
        if error is not None:
            # Empty string sentinel = clear (port semantic: None means "leave unchanged")
            sets.append("error = ?")
            params.append(error if error != "" else None)
        if increment_retry:
            sets.append("retry_count = retry_count + 1")
        if status is ArticleStatus.PROCESSED:
            sets.append("processed_at = ?")
            params.append(datetime.now(timezone.utc))
        if status is ArticleStatus.PUBLISHED:
            sets.append("published_at = ?")
            params.append(datetime.now(timezone.utc))
        params.append(id)
        self._conn.execute(f"UPDATE articles SET {', '.join(sets)} WHERE id = ?", params)

    def update_tags(self, id: ArticleId, tags: list[Tag]) -> None:
        self._conn.execute("DELETE FROM article_tags WHERE article_id = ?", (id,))
        self._conn.executemany(
            "INSERT INTO article_tags (article_id, tag) VALUES (?, ?)",
            [(id, t) for t in tags],
        )

    def count_by_source(self) -> dict[SourceName, int]:
        rows = self._conn.execute(
            "SELECT source, COUNT(*) AS c FROM articles GROUP BY source"
        ).fetchall()
        return {SourceName(r["source"]): r["c"] for r in rows}

    def count_pending(self) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS c FROM articles WHERE status = ?",
            (ArticleStatus.RECEIVED.value,),
        ).fetchone()
        return int(row["c"])


def _to_dt(value) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))
