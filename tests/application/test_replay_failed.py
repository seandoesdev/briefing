from briefing.application.replay_failed import ReplayFailedUseCase
from briefing.domain.value_objects import ArticleStatus
from tests.application.fakes import FakeArticleRepository, make_article


def test_replay_resets_failed_to_received():
    repo = FakeArticleRepository()
    a = make_article(body="x")
    repo.save(a)
    repo.update_status(a.id, ArticleStatus.FAILED, error="boom")
    uc = ReplayFailedUseCase(repo)

    uc.execute()

    out = repo.find_by_id(a.id)
    assert out.status is ArticleStatus.RECEIVED
    assert out.error is None
