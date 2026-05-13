from datetime import datetime, timezone

from briefing.domain.results import AdminFilter, SyncResult, SyncStatus


def test_sync_result_success_factory():
    r = SyncResult.success(commit_sha="abc123", article_count=5)
    assert r.ok is True
    assert r.commit_sha == "abc123"
    assert r.error is None


def test_sync_result_failure_factory():
    r = SyncResult.failure(error="auth denied")
    assert r.ok is False
    assert r.error == "auth denied"


def test_admin_filter_defaults():
    f = AdminFilter()
    assert f.source is None
    assert f.status is None
    assert f.limit == 50
    assert f.offset == 0


def test_sync_status_dataclass():
    s = SyncStatus(
        last_push_at=datetime(2026, 5, 13, tzinfo=timezone.utc),
        last_commit_sha="abc",
        pending_count=0,
        last_error=None,
    )
    assert s.pending_count == 0
