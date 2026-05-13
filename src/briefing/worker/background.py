from __future__ import annotations

import asyncio
import logging
import time

from briefing.application.publish_pending import PublishPendingUseCase
from briefing.application.sync_vault import SyncVaultUseCase

log = logging.getLogger(__name__)


class BackgroundWorker:
    def __init__(
        self,
        publish: PublishPendingUseCase,
        sync: SyncVaultUseCase,
        *,
        interval_sec: float,
        sync_idle_sec: float,
        batch: int = 10,
    ) -> None:
        self._publish = publish
        self._sync = sync
        self._interval = interval_sec
        self._sync_idle = sync_idle_sec
        self._batch = batch
        self._stop = asyncio.Event()
        self._last_publish_at: float = 0.0

    def stop(self) -> None:
        self._stop.set()

    async def run(self) -> None:
        while not self._stop.is_set():
            try:
                count = self._publish.execute(batch=self._batch)
                now = time.monotonic()
                if count > 0:
                    self._last_publish_at = now
                if (
                    self._last_publish_at > 0
                    and now - self._last_publish_at >= self._sync_idle
                ):
                    self._sync.execute()
                    self._last_publish_at = 0.0
            except Exception:
                log.exception("worker tick failed")
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self._interval)
            except asyncio.TimeoutError:
                pass
