from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request

from briefing.application.ingest_article import IngestArticleUseCase
from briefing.domain.value_objects import SourceName
from briefing.infrastructure.sources.registry import SourceRegistry

log = logging.getLogger(__name__)


def build_webhook_router(
    sources: SourceRegistry, ingest: IngestArticleUseCase
) -> APIRouter:
    router = APIRouter()

    @router.post("/webhook/{source}")
    async def webhook(source: str, request: Request):
        adapter = sources.get(SourceName(source))
        if adapter is None:
            raise HTTPException(status_code=404, detail=f"unknown source: {source}")

        raw_body = await request.body()
        headers = {k: v for k, v in request.headers.items()}

        if not adapter.verify(headers, raw_body):
            raise HTTPException(status_code=401, detail="signature verification failed")

        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="invalid json")

        if not payload:
            raise HTTPException(status_code=400, detail="empty payload")

        try:
            article = adapter.parse(payload)
        except Exception as e:
            log.exception("parse failed for source=%s", source)
            return {"status": "parse_failed", "error": repr(e)}

        result = ingest.execute(article)
        return {"status": result.value, "id": article.id}

    return router
