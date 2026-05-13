from fastapi import FastAPI
from fastapi.testclient import TestClient

from briefing.application.ingest_article import IngestArticleUseCase
from briefing.infrastructure.sources.dooray import DoorayAdapter
from briefing.infrastructure.sources.registry import SourceRegistry
from briefing.interface.webhook.routes import build_webhook_router
from tests.application.fakes import FakeArticleRepository


def _make_app(*, token: str | None = None) -> tuple[FastAPI, FakeArticleRepository]:
    repo = FakeArticleRepository()
    ingest = IngestArticleUseCase(repo)
    sources = SourceRegistry()
    sources.register(DoorayAdapter(token=token))
    app = FastAPI()
    app.include_router(build_webhook_router(sources, ingest))
    return app, repo


def test_webhook_stores_new_article():
    app, repo = _make_app()
    client = TestClient(app)
    r = client.post("/webhook/dooray", json={"text": "테스트 메시지"})
    assert r.status_code == 200
    assert r.json()["status"] == "stored"
    assert len(repo.by_id) == 1


def test_webhook_idempotent():
    app, repo = _make_app()
    client = TestClient(app)
    body = {"text": "동일 메시지"}
    client.post("/webhook/dooray", json=body)
    r = client.post("/webhook/dooray", json=body)
    assert r.status_code == 200
    assert r.json()["status"] == "duplicate"
    assert len(repo.by_id) == 1


def test_webhook_unknown_source_returns_404():
    app, _ = _make_app()
    client = TestClient(app)
    r = client.post("/webhook/unknown", json={"text": "x"})
    assert r.status_code == 404


def test_webhook_rejects_invalid_token():
    app, _ = _make_app(token="s3cret")
    client = TestClient(app)
    r = client.post("/webhook/dooray", headers={"X-Dooray-Token": "wrong"}, json={"text": "x"})
    assert r.status_code == 401


def test_webhook_empty_body_returns_400():
    app, _ = _make_app()
    client = TestClient(app)
    r = client.post("/webhook/dooray", json={})
    assert r.status_code == 400
