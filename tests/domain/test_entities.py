from datetime import datetime, timezone

from briefing.domain.entities import Article
from briefing.domain.value_objects import (
    ArticleId,
    ArticleStatus,
    PayloadHash,
    SourceName,
    Tag,
)


def _article(**overrides):
    base = dict(
        id=ArticleId("11111111-1111-1111-1111-111111111111"),
        source=SourceName("dooray"),
        external_id=None,
        payload_hash=PayloadHash("a" * 64),
        received_at=datetime(2026, 5, 13, 14, 32, tzinfo=timezone.utc),
        title="제목",
        body="본문",
        url=None,
        tags=[],
        raw_payload={"text": "본문"},
        status=ArticleStatus.RECEIVED,
        output_path=None,
        error=None,
        retry_count=0,
    )
    base.update(overrides)
    return Article(**base)


def test_article_default_status_received():
    a = _article()
    assert a.status is ArticleStatus.RECEIVED


def test_article_with_tags():
    a = _article(tags=[Tag("AI"), Tag("반도체")])
    assert "AI" in a.tags
