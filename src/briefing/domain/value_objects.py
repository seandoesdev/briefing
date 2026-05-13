from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import NewType

SourceName = NewType("SourceName", str)
PayloadHash = NewType("PayloadHash", str)
ArticleId = NewType("ArticleId", str)
Tag = NewType("Tag", str)


class ArticleStatus(StrEnum):
    RECEIVED = "received"
    PROCESSED = "processed"
    PUBLISHED = "published"
    FAILED = "failed"


def payload_hash(payload: dict) -> PayloadHash:
    """Deterministic SHA-256 hex digest of a JSON-serialisable payload."""
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return PayloadHash(hashlib.sha256(canonical).hexdigest())
