import sqlite3

from briefing.infrastructure.persistence.connection import open_connection
from briefing.infrastructure.persistence.schema import migrate


def test_migrate_creates_tables(tmp_path):
    db = tmp_path / "x.db"
    conn = open_connection(db)
    migrate(conn)
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    names = [r[0] for r in rows]
    assert "articles" in names
    assert "article_tags" in names
    assert "sync_log" in names
    assert "parse_failures" in names


def test_migrate_is_idempotent(tmp_path):
    db = tmp_path / "x.db"
    conn = open_connection(db)
    migrate(conn)
    migrate(conn)  # second run must not raise
    conn.execute("SELECT 1").fetchone()


def test_payload_hash_unique(tmp_path):
    db = tmp_path / "x.db"
    conn = open_connection(db)
    migrate(conn)
    conn.execute(
        "INSERT INTO articles (id, source, payload_hash, received_at, title, body, raw_payload, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("1", "dooray", "h", "2026-05-13", "t", "b", "{}", "received"),
    )
    conn.commit()
    try:
        conn.execute(
            "INSERT INTO articles (id, source, payload_hash, received_at, title, body, raw_payload, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("2", "dooray", "h", "2026-05-13", "t", "b", "{}", "received"),
        )
        conn.commit()
        raised = False
    except sqlite3.IntegrityError:
        raised = True
    assert raised
