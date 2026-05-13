from __future__ import annotations

from briefing.domain.ports import ArticleRepository
from briefing.domain.results import AdminFilter
from briefing.domain.value_objects import ArticleStatus


class ReplayFailedUseCase:
    def __init__(self, repo: ArticleRepository) -> None:
        self._repo = repo

    def execute(self, *, article_id: str | None = None) -> int:
        if article_id is not None:
            self._repo.update_status(article_id, ArticleStatus.RECEIVED, error="")
            return 1
        failed = self._repo.list_for_admin(
            AdminFilter(status=ArticleStatus.FAILED, limit=1000)
        )
        for a in failed:
            self._repo.update_status(a.id, ArticleStatus.RECEIVED, error="")
        return len(failed)
