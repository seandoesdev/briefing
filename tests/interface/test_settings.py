from pathlib import Path

from briefing.interface.settings import Settings


def test_settings_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("BRIEFING_DB_PATH", str(tmp_path / "db.sqlite"))
    monkeypatch.setenv("BRIEFING_VAULT_PATH", str(tmp_path / "vault"))
    monkeypatch.setenv("BRIEFING_ADMIN_USER", "u")
    monkeypatch.setenv("BRIEFING_ADMIN_PASSWORD", "p")
    s = Settings()
    assert s.db_path == tmp_path / "db.sqlite"
    assert s.vault_path == tmp_path / "vault"
    assert s.admin_user == "u"
