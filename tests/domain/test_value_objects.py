# tests/domain/test_value_objects.py
from briefing.domain.value_objects import (
    ArticleStatus,
    payload_hash,
)


def test_article_status_values():
    assert ArticleStatus.RECEIVED.value == "received"
    assert ArticleStatus.PROCESSED.value == "processed"
    assert ArticleStatus.PUBLISHED.value == "published"
    assert ArticleStatus.FAILED.value == "failed"


def test_payload_hash_is_deterministic():
    p1 = {"a": 1, "b": [2, 3]}
    p2 = {"b": [2, 3], "a": 1}
    assert payload_hash(p1) == payload_hash(p2)
    assert len(payload_hash(p1)) == 64  # SHA-256 hex
