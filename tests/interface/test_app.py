from fastapi.testclient import TestClient

from briefing.interface.app import create_app
from briefing.interface.settings import Settings


def test_create_app_smoke(tmp_path, monkeypatch):
    monkeypatch.setenv("BRIEFING_DB_PATH", str(tmp_path / "x.db"))
    monkeypatch.setenv("BRIEFING_VAULT_PATH", str(tmp_path / "vault"))
    (tmp_path / "vault").mkdir()
    monkeypatch.setenv("BRIEFING_STOPWORDS_PATH", "data/stopwords.txt")
    monkeypatch.setenv("BRIEFING_ADMIN_USER", "u")
    monkeypatch.setenv("BRIEFING_ADMIN_PASSWORD", "p")
    monkeypatch.setenv("BRIEFING_LOG_PATH", str(tmp_path / "x.log"))

    app = create_app(Settings(), start_worker=False)
    c = TestClient(app)

    r = c.post("/webhook/dooray", json={"text": "통합 테스트 메시지입니다."})
    assert r.status_code == 200

    r2 = c.get("/admin", auth=("u", "p"))
    assert r2.status_code == 200
