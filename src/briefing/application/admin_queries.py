from __future__ import annotations

from dataclasses import dataclass

from briefing.domain.entities import Article
from briefing.domain.ports import ArticleRepository, VaultSync
from briefing.domain.results import AdminFilter, SyncStatus
from briefing.domain.value_objects import SourceName


@dataclass
class DashboardSummary:
    pending_count: int
    per_source: dict[SourceName, int]
    sync: SyncStatus


class AdminQueries:
    def __init__(self, repo: ArticleRepository, sync: VaultSync) -> None:
        self._repo = repo
        self._sync = sync

    def dashboard(self) -> DashboardSummary:
        return DashboardSummary(
            pending_count=self._repo.count_pending(),
            per_source=self._repo.count_by_source(),
            sync=self._sync.status(),
        )

    def list_articles(self, filters: AdminFilter) -> list[Article]:
        return self._repo.list_for_admin(filters)

    def get_article(self, id: str) -> Article | None:
        return self._repo.find_by_id(id)
