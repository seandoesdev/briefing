import asyncio

import pytest

from briefing.application.publish_pending import PublishPendingUseCase
from briefing.application.sync_vault import SyncVaultUseCase
from briefing.domain.value_objects import ArticleStatus
from briefing.worker.background import BackgroundWorker
from tests.application.fakes import (
    FakeArticleRepository,
    FakeExtractor,
    FakePublisher,
    FakeSync,
    make_article,
)


@pytest.mark.asyncio
async def test_worker_processes_pending():
    repo = FakeArticleRepository()
    repo.save(make_article(body="x"))
    publish = PublishPendingUseCase(repo, FakeExtractor(), FakePublisher(), max_retry=3)
    sync = SyncVaultUseCase(repo, FakeSync())
    w = BackgroundWorker(publish, sync, interval_sec=0.01, sync_idle_sec=0.01)

    task = asyncio.create_task(w.run())
    await asyncio.sleep(0.1)
    w.stop()
    await task

    assert all(a.status is ArticleStatus.PUBLISHED for a in repo.by_id.values())


@pytest.mark.asyncio
async def test_worker_stops_cleanly_on_empty_queue():
    repo = FakeArticleRepository()
    publish = PublishPendingUseCase(repo, FakeExtractor(), FakePublisher(), max_retry=3)
    sync = SyncVaultUseCase(repo, FakeSync())
    w = BackgroundWorker(publish, sync, interval_sec=0.01, sync_idle_sec=0.01)

    task = asyncio.create_task(w.run())
    await asyncio.sleep(0.05)
    w.stop()
    await task
