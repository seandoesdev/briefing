from tests.application.fakes import FakeArticleRepository, make_article


def test_fake_repo_roundtrip():
    repo = FakeArticleRepository()
    a = make_article(body="hello")
    repo.save(a)
    assert repo.find_by_id(a.id) is a
    assert repo.find_by_hash(a.payload_hash) is a
