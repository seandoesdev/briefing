from __future__ import annotations

import hmac
import json
import logging
from datetime import datetime, timezone
from uuid import uuid4

from briefing.domain.entities import Article
from briefing.domain.value_objects import (
    ArticleId,
    PayloadHash,
    SourceName,
    payload_hash,
)

log = logging.getLogger(__name__)


class DoorayAdapter:
    """Dooray webhook payload → Article.

    Permissive on purpose: even if the payload doesn't match any known shape,
    we still produce an Article (with body=raw JSON) so the user can see it
    in the admin UI and adjust mappings later. parse() never raises.
    """

    name = SourceName("dooray")

    def __init__(self, *, token: str | None) -> None:
        self._token = token

    def verify(self, headers: dict, raw_body: bytes) -> bool:
        if not self._token:
            return True
        # case-insensitive header lookup
        normalized = {k.lower(): v for k, v in headers.items()}
        provided = normalized.get("x-dooray-token") or normalized.get("token")
        if not provided:
            return False
        return hmac.compare_digest(provided, self._token)

    def parse(self, raw_payload: dict) -> Article:
        title, body, url = _extract_fields(raw_payload)

        return Article(
            id=ArticleId(str(uuid4())),
            source=self.name,
            external_id=_first_str(
                raw_payload,
                "event_id",
                "messageId",
                "message_id",
                "id",
            ),
            payload_hash=PayloadHash(payload_hash(raw_payload)),
            received_at=datetime.now(timezone.utc),
            title=title,
            body=body,
            url=url,
            tags=[],
            raw_payload=raw_payload,
        )


def _first_str(payload: dict, *keys: str) -> str | None:
    for k in keys:
        v = payload.get(k)
        if isinstance(v, (str, int)) and str(v).strip():
            return str(v)
    return None


def _extract_fields(payload: dict) -> tuple[str, str, str | None]:
    """Try multiple known Dooray-ish shapes; fall back to raw JSON dump.

    Returns (title, body, url).
    """
    # Shape 1: 표준 incoming webhook (slack-like) — text + attachments[]
    text = payload.get("text") or ""
    attachments = payload.get("attachments") or []

    title = ""
    url: str | None = None
    body_parts: list[str] = []

    if isinstance(text, str) and text.strip():
        body_parts.append(text.strip())

    if isinstance(attachments, list) and attachments:
        first = attachments[0] if isinstance(attachments[0], dict) else {}
        title = (first.get("title") or "").strip()
        url = first.get("titleLink") or first.get("title_link")
        for a in attachments:
            if not isinstance(a, dict):
                continue
            t = a.get("text")
            if isinstance(t, str) and t.strip():
                body_parts.append(t.strip())
            fields = a.get("fields") or []
            for f in fields if isinstance(fields, list) else []:
                if isinstance(f, dict):
                    title_f = f.get("title", "")
                    value_f = f.get("value", "")
                    if value_f:
                        body_parts.append(f"**{title_f}**: {value_f}".strip())

    # Shape 2: Dooray Hook (messenger / project event 등) — message 객체
    if not body_parts and isinstance(payload.get("message"), dict):
        msg = payload["message"]
        msg_text = msg.get("text") or msg.get("content") or ""
        if msg_text:
            body_parts.append(str(msg_text))
        if not title:
            title = (msg.get("subject") or msg.get("title") or "").strip()

    # Shape 3: 메일 / 알림류 — subject + content
    if not body_parts:
        for key in ("content", "body", "message_text", "description"):
            v = payload.get(key)
            if isinstance(v, str) and v.strip():
                body_parts.append(v.strip())
                break

    if not title:
        for key in ("subject", "title", "name"):
            v = payload.get(key)
            if isinstance(v, str) and v.strip():
                title = v.strip()
                break

    # Final fallback: 알려진 모양 아님 — JSON 전체를 body로 (사용자가 admin에서 보고 매핑 추가 가능)
    if not body_parts:
        log.warning(
            "dooray payload didn't match any known shape; storing raw JSON. keys=%s",
            list(payload.keys()),
        )
        body_parts.append(json.dumps(payload, ensure_ascii=False, indent=2))

    body = "\n\n".join(body_parts).strip()

    if not title:
        # body의 첫 줄(or 첫 40자)을 제목으로
        first_line = body.split("\n", 1)[0].strip()
        title = first_line[:60] if first_line else "(no title)"

    return title, body, url
