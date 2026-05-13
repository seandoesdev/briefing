from __future__ import annotations

import hmac
from datetime import datetime, timezone
from uuid import uuid4

from briefing.domain.entities import Article
from briefing.domain.value_objects import (
    ArticleId,
    PayloadHash,
    SourceName,
    payload_hash,
)


class DoorayAdapter:
    name = SourceName("dooray")

    def __init__(self, *, token: str | None) -> None:
        self._token = token

    def verify(self, headers: dict, raw_body: bytes) -> bool:
        if not self._token:
            return True
        provided = headers.get("X-Dooray-Token") or headers.get("x-dooray-token")
        if not provided:
            return False
        return hmac.compare_digest(provided, self._token)

    def parse(self, raw_payload: dict) -> Article:
        text = raw_payload.get("text", "") or ""
        attachments = raw_payload.get("attachments") or []

        title = ""
        url: str | None = None
        body_parts: list[str] = []

        if text:
            body_parts.append(text)
        if attachments:
            att = attachments[0]
            title = att.get("title") or ""
            url = att.get("titleLink")
            for a in attachments:
                t = a.get("text")
                if t:
                    body_parts.append(t)

        body = "\n\n".join(p for p in body_parts if p).strip()
        if not title:
            title = body[:40] if body else "(no title)"

        return Article(
            id=ArticleId(str(uuid4())),
            source=self.name,
            external_id=raw_payload.get("event_id") or raw_payload.get("messageId"),
            payload_hash=PayloadHash(payload_hash(raw_payload)),
            received_at=datetime.now(timezone.utc),
            title=title,
            body=body,
            url=url,
            tags=[],
            raw_payload=raw_payload,
        )
