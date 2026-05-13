from datetime import datetime, timezone

from briefing.domain.entities import Article
from briefing.domain.value_objects import ArticleId, PayloadHash, SourceName, Tag
from briefing.infrastructure.vault.markdown_publisher import MarkdownVaultPublisher


def _article(**overrides):
    base = dict(
        id=ArticleId("11111111-1111-1111-1111-111111111111"),
        source=SourceName("dooray"),
        external_id=None,
        payload_hash=PayloadHash("a" * 64),
        received_at=datetime(2026, 5, 13, 14, 32, tzinfo=timezone.utc),
        title="네이버 AI",
        body="네이버가 새 모델을 발표했다.",
        url="https://example.com/a",
        tags=[Tag("네이버"), Tag("AI")],
        raw_payload={},
    )
    base.update(overrides)
    return Article(**base)


def test_publish_creates_dated_file(tmp_path):
    pub = MarkdownVaultPublisher(tmp_path)
    path = pub.publish(_article())
    assert path == tmp_path / "dooray" / "2026-05-13.md"
    content = path.read_text(encoding="utf-8")
    assert "네이버 AI" in content
    assert "#네이버" in content
    assert "https://example.com/a" in content


def test_publish_appends_to_existing(tmp_path):
    pub = MarkdownVaultPublisher(tmp_path)
    pub.publish(_article(payload_hash=PayloadHash("a" * 64), body="첫 번째"))
    pub.publish(
        _article(
            id=ArticleId("22222222-2222-2222-2222-222222222222"),
            payload_hash=PayloadHash("b" * 64),
            body="두 번째",
        )
    )
    path = tmp_path / "dooray" / "2026-05-13.md"
    content = path.read_text(encoding="utf-8")
    assert "첫 번째" in content
    assert "두 번째" in content
    assert content.count("# 2026-05-13") == 1


def test_publish_handles_missing_url_and_empty_tags(tmp_path):
    pub = MarkdownVaultPublisher(tmp_path)
    path = pub.publish(_article(url=None, tags=[]))
    content = path.read_text(encoding="utf-8")
    assert "**url**" not in content
    assert "**tags**: (none)" in content
