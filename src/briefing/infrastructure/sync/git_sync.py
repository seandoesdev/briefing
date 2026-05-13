from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from git import Repo
from git.exc import GitCommandError

from briefing.domain.results import SyncResult, SyncStatus


class GitVaultSync:
    def __init__(self, vault_path: Path, *, remote: str = "origin", branch: str = "main") -> None:
        self._vault = Path(vault_path)
        self._remote = remote
        self._branch = branch
        self._last_push_at: datetime | None = None
        self._last_error: str | None = None

    def _repo(self) -> Repo:
        return Repo(self._vault)

    def commit_and_push(self, message: str) -> SyncResult:
        try:
            repo = self._repo()
        except Exception as e:
            return SyncResult.failure(f"open failed: {e}")

        try:
            repo.git.add("--all")
            # If working tree has no untracked/modified AND index matches HEAD, no-op.
            if not repo.is_dirty(untracked_files=True) and not repo.index.diff("HEAD"):
                return SyncResult.success(commit_sha=None, article_count=0)

            repo.index.commit(message)
            sha = repo.head.commit.hexsha
            repo.git.push(self._remote, self._branch)
            self._last_push_at = datetime.now(timezone.utc)
            self._last_error = None
            return SyncResult.success(commit_sha=sha, article_count=1)
        except GitCommandError as e:
            self._last_error = str(e)
            return SyncResult.failure(str(e))
        except Exception as e:
            self._last_error = repr(e)
            return SyncResult.failure(repr(e))

    def status(self) -> SyncStatus:
        try:
            repo = self._repo()
            sha = repo.head.commit.hexsha
        except Exception:
            sha = None
        return SyncStatus(
            last_push_at=self._last_push_at,
            last_commit_sha=sha,
            pending_count=0,
            last_error=self._last_error,
        )
