from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.templating import Jinja2Templates

from briefing.application.admin_queries import AdminQueries
from briefing.application.ingest_article import IngestArticleUseCase
from briefing.application.publish_pending import PublishPendingUseCase
from briefing.application.replay_failed import ReplayFailedUseCase
from briefing.application.sync_vault import SyncVaultUseCase
from briefing.infrastructure.nlp.kiwi_extractor import KiwiKeywordExtractor
from briefing.infrastructure.persistence.connection import open_connection
from briefing.infrastructure.persistence.schema import migrate
from briefing.infrastructure.persistence.sqlite_article_repo import SqliteArticleRepository
from briefing.infrastructure.sources.dooray import DoorayAdapter
from briefing.infrastructure.sources.registry import SourceRegistry
from briefing.infrastructure.sync.git_sync import GitVaultSync
from briefing.infrastructure.vault.markdown_publisher import MarkdownVaultPublisher
from briefing.interface.admin.auth import build_admin_auth_dependency
from briefing.interface.admin.routes import build_admin_router
from briefing.interface.settings import Settings
from briefing.interface.webhook.routes import build_webhook_router
from briefing.worker.background import BackgroundWorker

TEMPLATES_DIR = Path(__file__).parent / "admin" / "templates"


def _configure_logging(log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)


def create_app(settings: Settings | None = None, *, start_worker: bool = True) -> FastAPI:
    settings = settings or Settings()
    _configure_logging(settings.log_path)

    conn = open_connection(settings.db_path)
    migrate(conn)
    repo = SqliteArticleRepository(conn)
    extractor = KiwiKeywordExtractor(
        stopwords_path=settings.stopwords_path, top_n=settings.keyword_top_n
    )
    publisher = MarkdownVaultPublisher(settings.vault_path)
    sync = GitVaultSync(
        settings.vault_path, remote=settings.git_remote, branch=settings.git_branch
    )

    sources = SourceRegistry()
    sources.register(DoorayAdapter(token=settings.dooray_token))

    ingest = IngestArticleUseCase(repo)
    publish = PublishPendingUseCase(repo, extractor, publisher, max_retry=settings.max_retry)
    sync_uc = SyncVaultUseCase(repo, sync)
    replay = ReplayFailedUseCase(repo)
    queries = AdminQueries(repo, sync)

    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    require_admin = build_admin_auth_dependency(settings.admin_user, settings.admin_password)
    worker = BackgroundWorker(
        publish,
        sync_uc,
        interval_sec=settings.worker_interval_sec,
        sync_idle_sec=settings.sync_idle_sec,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        task = None
        if start_worker:
            task = asyncio.create_task(worker.run())
        try:
            yield
        finally:
            worker.stop()
            if task:
                await task

    app = FastAPI(lifespan=lifespan)
    app.include_router(build_webhook_router(sources, ingest))
    app.include_router(
        build_admin_router(
            templates=templates,
            queries=queries,
            sync_use_case=sync_uc,
            replay_use_case=replay,
            sources=sources,
            log_path=settings.log_path,
            require_admin=require_admin,
        )
    )
    return app
