from pathlib import Path

from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.testclient import TestClient

from briefing.application.admin_queries import AdminQueries
from briefing.application.replay_failed import ReplayFailedUseCase
from briefing.application.sync_vault import SyncVaultUseCase
from briefing.domain.value_objects import ArticleStatus
from briefing.infrastructure.sources.dooray import DoorayAdapter
from briefing.infrastructure.sources.registry import SourceRegistry
from briefing.interface.admin.routes import build_admin_router
from tests.application.fakes import (
    FakeArticleRepository,
    FakeSync,
    make_article,
)

TEMPLATES_DIR = Path("src/briefing/interface/admin/templates")


def _make_app() -> tuple[FastAPI, FakeArticleRepository, FakeSync]:
    repo = FakeArticleRepository()
    sync = FakeSync()
    sources = SourceRegistry()
    sources.register(DoorayAdapter(token=None))
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    app = FastAPI()
    app.include_router(
        build_admin_router(
            templates=templates,
            queries=AdminQueries(repo, sync),
            sync_use_case=SyncVaultUseCase(repo, sync),
            replay_use_case=ReplayFailedUseCase(repo),
            sources=sources,
            log_path=Path("nonexistent.log"),
            require_admin=lambda: "admin",
        )
    )
    return app, repo, sync


def test_dashboard_renders_with_zero_articles():
    app, _, _ = _make_app()
    r = TestClient(app).get("/admin")
    assert r.status_code == 200
    assert "Dashboard" in r.text


def test_articles_list_renders():
    app, repo, _ = _make_app()
    repo.save(make_article(body="x"))
    r = TestClient(app).get("/admin/articles")
    assert r.status_code == 200
    assert "x" in r.text


def test_article_detail_404_when_missing():
    app, _, _ = _make_app()
    r = TestClient(app).get("/admin/articles/missing")
    assert r.status_code == 404


def test_article_retry_resets_failed():
    app, repo, _ = _make_app()
    a = make_article(body="x")
    repo.save(a)
    repo.update_status(a.id, ArticleStatus.FAILED, error="boom")
    r = TestClient(app).post(f"/admin/articles/{a.id}/retry", follow_redirects=False)
    assert r.status_code in (200, 303)
    assert repo.find_by_id(a.id).status is ArticleStatus.RECEIVED


def test_sync_manual_push_triggers_use_case():
    app, repo, sync = _make_app()
    a = make_article(body="x")
    repo.save(a)
    repo.update_status(a.id, ArticleStatus.PROCESSED)
    r = TestClient(app).post("/admin/sync/push")
    assert r.status_code == 200
    assert sync.pushed == 1


def test_sources_page_lists_dooray():
    app, _, _ = _make_app()
    r = TestClient(app).get("/admin/sources")
    assert "dooray" in r.text


def test_logs_page_handles_missing_log_file():
    app, _, _ = _make_app()
    r = TestClient(app).get("/admin/logs")
    assert r.status_code == 200
