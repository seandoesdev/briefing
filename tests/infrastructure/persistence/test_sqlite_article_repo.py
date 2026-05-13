from datetime import datetime, timezone
from uuid import uuid4

from briefing.domain.entities import Article
from briefing.domain.results import AdminFilter
from briefing.domain.value_objects import (
    ArticleId,
    ArticleStatus,
    PayloadHash,
    SourceName,
    Tag,
)
from briefing.infrastructure.persistence.connection import open_connection
from briefing.infrastructure.persistence.schema import migrate
from briefing.infrastructure.persistence.sqlite_article_repo import SqliteArticleRepository


def _conn(tmp_path):
    c = open_connection(tmp_path / "x.db")
    migrate(c)
    return c


def _make_article(*, body="본문", hash="a" * 64, source="dooray"):
    return Article(
        id=ArticleId(str(uuid4())),
        source=SourceName(source),
        external_id=None,
        payload_hash=PayloadHash(hash),
        received_at=datetime(2026, 5, 13, 14, 32, tzinfo=timezone.utc),
        title=body[:20],
        body=body,
        url=None,
        tags=[],
        raw_payload={"text": body},
    )


def test_save_and_find_by_id(tmp_path):
    repo = SqliteArticleRepository(_conn(tmp_path))
    a = _make_article()
    repo.save(a)
    out = repo.find_by_id(a.id)
    assert out.body == a.body
    assert out.status is ArticleStatus.RECEIVED


def test_find_by_hash(tmp_path):
    repo = SqliteArticleRepository(_conn(tmp_path))
    a = _make_article(hash="b" * 64)
    repo.save(a)
    out = repo.find_by_hash(a.payload_hash)
    assert out is not None and out.id == a.id


def test_list_pending_only_returns_received(tmp_path):
    repo = SqliteArticleRepository(_conn(tmp_path))
    a = _make_article(hash="c" * 64)
    b = _make_article(hash="d" * 64)
    repo.save(a)
    repo.save(b)
    repo.update_status(b.id, ArticleStatus.PROCESSED)
    pending = repo.list_pending(limit=10)
    assert [p.id for p in pending] == [a.id]


def test_update_tags_replaces_existing(tmp_path):
    repo = SqliteArticleRepository(_conn(tmp_path))
    a = _make_article(hash="e" * 64)
    repo.save(a)
    repo.update_tags(a.id, [Tag("AI"), Tag("반도체")])
    out = repo.find_by_id(a.id)
    assert set(out.tags) == {"AI", "반도체"}

    repo.update_tags(a.id, [Tag("뉴스")])
    out2 = repo.find_by_id(a.id)
    assert out2.tags == ["뉴스"]


def test_list_for_admin_filter_by_status(tmp_path):
    repo = SqliteArticleRepository(_conn(tmp_path))
    a = _make_article(hash="f" * 64)
    repo.save(a)
    repo.update_status(a.id, ArticleStatus.FAILED, error="boom")

    items = repo.list_for_admin(AdminFilter(status=ArticleStatus.FAILED))
    assert len(items) == 1
    assert items[0].error == "boom"


def test_update_status_increments_retry(tmp_path):
    repo = SqliteArticleRepository(_conn(tmp_path))
    a = _make_article(hash="9" * 64)
    repo.save(a)
    repo.update_status(a.id, ArticleStatus.RECEIVED, error="x", increment_retry=True)
    repo.update_status(a.id, ArticleStatus.RECEIVED, error="y", increment_retry=True)
    out = repo.find_by_id(a.id)
    assert out.retry_count == 2


def test_count_by_source_and_pending(tmp_path):
    repo = SqliteArticleRepository(_conn(tmp_path))
    repo.save(_make_article(hash="1" * 64))
    repo.save(_make_article(hash="2" * 64))
    assert repo.count_pending() == 2
    assert repo.count_by_source() == {"dooray": 2}


def test_clear_error_with_empty_string(tmp_path):
    """ReplayFailed uses error='' to clear the error column."""
    repo = SqliteArticleRepository(_conn(tmp_path))
    a = _make_article(hash="8" * 64)
    repo.save(a)
    repo.update_status(a.id, ArticleStatus.FAILED, error="boom")
    repo.update_status(a.id, ArticleStatus.RECEIVED, error="")
    assert repo.find_by_id(a.id).error is None
