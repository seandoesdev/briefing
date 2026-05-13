from briefing.application.publish_pending import PublishPendingUseCase
from briefing.domain.value_objects import ArticleStatus, Tag
from tests.application.fakes import (
    FakeArticleRepository,
    FakeExtractor,
    FakePublisher,
    make_article,
)


def test_publish_pending_writes_and_marks_processed():
    repo = FakeArticleRepository()
    a = make_article(body="네이버 AI 발표")
    repo.save(a)
    uc = PublishPendingUseCase(repo, FakeExtractor(), FakePublisher(), max_retry=3)

    uc.execute(batch=10)

    out = repo.find_by_id(a.id)
    assert out.status is ArticleStatus.PROCESSED
    assert Tag("AI") in out.tags
    assert out.output_path is not None


def test_publish_pending_failure_increments_retry_and_stays_received():
    repo = FakeArticleRepository()
    a = make_article(body="x")
    repo.save(a)
    uc = PublishPendingUseCase(repo, FakeExtractor(), FakePublisher(raise_on_publish=True), max_retry=3)

    uc.execute(batch=10)

    out = repo.find_by_id(a.id)
    assert out.status is ArticleStatus.RECEIVED
    assert out.retry_count == 1
    assert out.error is not None


def test_publish_pending_exceeds_max_retry_becomes_failed():
    repo = FakeArticleRepository()
    a = make_article(body="x")
    repo.save(a)
    publisher = FakePublisher(raise_on_publish=True)
    uc = PublishPendingUseCase(repo, FakeExtractor(), publisher, max_retry=2)

    uc.execute(batch=10)
    uc.execute(batch=10)

    out = repo.find_by_id(a.id)
    assert out.status is ArticleStatus.FAILED
    assert out.retry_count == 2


def test_publish_pending_extractor_failure_still_publishes_without_tags():
    repo = FakeArticleRepository()
    a = make_article(body="x")
    repo.save(a)
    uc = PublishPendingUseCase(
        repo, FakeExtractor(raise_on_extract=True), FakePublisher(), max_retry=3
    )

    uc.execute(batch=10)

    out = repo.find_by_id(a.id)
    assert out.status is ArticleStatus.PROCESSED
    assert out.tags == []
