from pathlib import Path

from fastapi.testclient import TestClient
from git import Repo

from briefing.interface.app import create_app
from briefing.interface.settings import Settings


def _setup_remote(tmp_path: Path) -> tuple[Path, Path]:
    remote = tmp_path / "remote.git"
    Repo.init(remote, bare=True)
    vault = tmp_path / "vault"
    repo = Repo.init(vault)
    with repo.config_writer() as cw:
        cw.set_value("user", "name", "test")
        cw.set_value("user", "email", "test@example.com")
    repo.git.checkout("-b", "main")
    repo.git.commit("--allow-empty", "-m", "init")
    repo.create_remote("origin", str(remote))
    repo.git.push("--set-upstream", "origin", "main")
    return vault, remote


def test_e2e_webhook_to_vault_to_push(tmp_path, monkeypatch):
    vault, remote = _setup_remote(tmp_path)
    monkeypatch.setenv("BRIEFING_DB_PATH", str(tmp_path / "x.db"))
    monkeypatch.setenv("BRIEFING_VAULT_PATH", str(vault))
    monkeypatch.setenv("BRIEFING_STOPWORDS_PATH", "data/stopwords.txt")
    monkeypatch.setenv("BRIEFING_ADMIN_USER", "u")
    monkeypatch.setenv("BRIEFING_ADMIN_PASSWORD", "p")
    monkeypatch.setenv("BRIEFING_LOG_PATH", str(tmp_path / "x.log"))

    settings = Settings()
    app = create_app(settings, start_worker=False)
    client = TestClient(app)

    with client:
        r = client.post(
            "/webhook/dooray",
            json={
                "text": "네이버가 새로운 AI 반도체를 발표했습니다. 자세한 내용은 링크를 참조하세요.",
                "attachments": [{"title": "네이버 AI 반도체", "titleLink": "https://example.com"}],
            },
        )
        assert r.status_code == 200

        from briefing.application.publish_pending import PublishPendingUseCase
        from briefing.infrastructure.nlp.kiwi_extractor import KiwiKeywordExtractor
        from briefing.infrastructure.persistence.connection import open_connection
        from briefing.infrastructure.persistence.schema import migrate
        from briefing.infrastructure.persistence.sqlite_article_repo import (
            SqliteArticleRepository,
        )
        from briefing.infrastructure.vault.markdown_publisher import (
            MarkdownVaultPublisher,
        )

        conn = open_connection(settings.db_path)
        migrate(conn)
        repo_for_check = SqliteArticleRepository(conn)
        pub_uc = PublishPendingUseCase(
            repo_for_check,
            KiwiKeywordExtractor(stopwords_path=settings.stopwords_path),
            MarkdownVaultPublisher(settings.vault_path),
            max_retry=3,
        )
        assert pub_uc.execute(batch=10) == 1

        r3 = client.post("/admin/sync/push", auth=("u", "p"))
        assert r3.status_code == 200 and r3.json()["ok"] is True

    files = list((vault / "dooray").glob("*.md"))
    assert len(files) == 1
    content = files[0].read_text(encoding="utf-8")
    assert "네이버" in content
    assert "#" in content
