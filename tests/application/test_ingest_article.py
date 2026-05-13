from briefing.application.ingest_article import IngestArticleUseCase, IngestResult
from tests.application.fakes import FakeArticleRepository, make_article


def test_ingest_new_article_stored():
    repo = FakeArticleRepository()
    uc = IngestArticleUseCase(repo)
    a = make_article(body="first")

    result = uc.execute(a)

    assert result is IngestResult.STORED
    assert repo.find_by_id(a.id) is a


def test_ingest_duplicate_payload_is_skipped():
    repo = FakeArticleRepository()
    uc = IngestArticleUseCase(repo)
    a1 = make_article(body="dup")
    a2 = make_article(body="dup")  # same payload → same hash
    assert a1.payload_hash == a2.payload_hash

    uc.execute(a1)
    result = uc.execute(a2)

    assert result is IngestResult.DUPLICATE
    assert len(repo.by_id) == 1
