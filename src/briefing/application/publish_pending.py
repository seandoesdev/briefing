from __future__ import annotations

import logging

from briefing.domain.ports import ArticleRepository, KeywordExtractor, VaultPublisher
from briefing.domain.value_objects import ArticleStatus

log = logging.getLogger(__name__)


class PublishPendingUseCase:
    def __init__(
        self,
        repo: ArticleRepository,
        extractor: KeywordExtractor,
        publisher: VaultPublisher,
        *,
        max_retry: int,
    ) -> None:
        self._repo = repo
        self._extractor = extractor
        self._publisher = publisher
        self._max_retry = max_retry

    def execute(self, *, batch: int) -> int:
        processed = 0
        for article in self._repo.list_pending(limit=batch):
            try:
                try:
                    tags = self._extractor.extract(article.body)
                except Exception:
                    log.warning("keyword extraction failed", exc_info=True)
                    tags = []
                self._repo.update_tags(article.id, tags)
                article.tags = list(tags)

                path = self._publisher.publish(article)
                self._repo.update_status(
                    article.id, ArticleStatus.PROCESSED, output_path=path, error=None
                )
                processed += 1
            except Exception as e:
                new_count = article.retry_count + 1
                final_status = (
                    ArticleStatus.FAILED if new_count >= self._max_retry else ArticleStatus.RECEIVED
                )
                self._repo.update_status(
                    article.id, final_status, error=repr(e), increment_retry=True
                )
                log.error("publish failed for %s", article.id, exc_info=True)
        return processed
