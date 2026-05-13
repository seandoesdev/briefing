from __future__ import annotations

from datetime import datetime, timezone

from briefing.domain.ports import ArticleRepository, VaultSync
from briefing.domain.results import AdminFilter, SyncResult
from briefing.domain.value_objects import ArticleStatus


class SyncVaultUseCase:
    def __init__(self, repo: ArticleRepository, sync: VaultSync) -> None:
        self._repo = repo
        self._sync = sync

    def execute(self) -> SyncResult:
        processed = self._repo.list_for_admin(
            AdminFilter(status=ArticleStatus.PROCESSED, limit=1000)
        )
        if not processed:
            return SyncResult.success(commit_sha=None, article_count=0)

        message = f"briefing: {len(processed)} article(s) at {datetime.now(timezone.utc).isoformat()}"
        result = self._sync.commit_and_push(message)
        if not result.ok:
            return result

        for a in processed:
            self._repo.update_status(a.id, ArticleStatus.PUBLISHED)
        return SyncResult.success(commit_sha=result.commit_sha, article_count=len(processed))
