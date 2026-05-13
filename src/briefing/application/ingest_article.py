from __future__ import annotations

from enum import StrEnum

from briefing.domain.entities import Article
from briefing.domain.ports import ArticleRepository


class IngestResult(StrEnum):
    STORED = "stored"
    DUPLICATE = "duplicate"


class IngestArticleUseCase:
    def __init__(self, repo: ArticleRepository) -> None:
        self._repo = repo

    def execute(self, article: Article) -> IngestResult:
        if self._repo.find_by_hash(article.payload_hash) is not None:
            return IngestResult.DUPLICATE
        self._repo.save(article)
        return IngestResult.STORED
