from briefing.application.sync_vault import SyncVaultUseCase
from briefing.domain.value_objects import ArticleStatus
from tests.application.fakes import FakeArticleRepository, FakeSync, make_article


def _processed(repo, body="x"):
    a = make_article(body=body)
    repo.save(a)
    repo.update_status(a.id, ArticleStatus.PROCESSED)
    return a


def test_sync_pushes_and_marks_published():
    repo = FakeArticleRepository()
    a = _processed(repo)
    uc = SyncVaultUseCase(repo, FakeSync())

    result = uc.execute()

    assert result.ok is True
    assert repo.find_by_id(a.id).status is ArticleStatus.PUBLISHED


def test_sync_failure_leaves_status_unchanged():
    repo = FakeArticleRepository()
    a = _processed(repo)
    uc = SyncVaultUseCase(repo, FakeSync(fail_next=True))

    result = uc.execute()

    assert result.ok is False
    assert repo.find_by_id(a.id).status is ArticleStatus.PROCESSED


def test_sync_with_no_processed_articles_is_noop():
    repo = FakeArticleRepository()
    uc = SyncVaultUseCase(repo, FakeSync())

    result = uc.execute()

    assert result.ok is True
    assert result.article_count == 0
