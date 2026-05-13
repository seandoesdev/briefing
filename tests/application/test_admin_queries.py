from briefing.application.admin_queries import AdminQueries
from briefing.domain.results import AdminFilter
from briefing.domain.value_objects import ArticleStatus
from tests.application.fakes import FakeArticleRepository, FakeSync, make_article


def test_dashboard_summary():
    repo = FakeArticleRepository()
    repo.save(make_article(body="a"))
    repo.save(make_article(body="b"))
    queries = AdminQueries(repo, FakeSync())

    summary = queries.dashboard()

    assert summary.pending_count == 2
    assert summary.per_source["dooray"] == 2


def test_list_articles_passes_filters():
    repo = FakeArticleRepository()
    repo.save(make_article(body="a"))
    queries = AdminQueries(repo, FakeSync())

    items = queries.list_articles(AdminFilter(status=ArticleStatus.RECEIVED))

    assert len(items) == 1
