from __future__ import annotations

import sqlite3

SCHEMA_VERSION = 1

_SQL_V1 = """
CREATE TABLE IF NOT EXISTS articles (
  id            TEXT PRIMARY KEY,
  source        TEXT NOT NULL,
  external_id   TEXT,
  payload_hash  TEXT UNIQUE NOT NULL,
  received_at   TIMESTAMP NOT NULL,
  title         TEXT NOT NULL,
  body          TEXT NOT NULL,
  url           TEXT,
  raw_payload   TEXT NOT NULL,
  status        TEXT NOT NULL,
  output_path   TEXT,
  error         TEXT,
  retry_count   INTEGER NOT NULL DEFAULT 0,
  processed_at  TIMESTAMP,
  published_at  TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_articles_status   ON articles(status);
CREATE INDEX IF NOT EXISTS idx_articles_source   ON articles(source);
CREATE INDEX IF NOT EXISTS idx_articles_received ON articles(received_at);

CREATE TABLE IF NOT EXISTS article_tags (
  article_id  TEXT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
  tag         TEXT NOT NULL,
  PRIMARY KEY (article_id, tag)
);
CREATE INDEX IF NOT EXISTS idx_article_tags_tag ON article_tags(tag);

CREATE TABLE IF NOT EXISTS sync_log (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  pushed_at     TIMESTAMP NOT NULL,
  commit_sha    TEXT,
  article_count INTEGER,
  status        TEXT NOT NULL,
  error         TEXT
);

CREATE TABLE IF NOT EXISTS parse_failures (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  source       TEXT NOT NULL,
  received_at  TIMESTAMP NOT NULL,
  raw_payload  TEXT NOT NULL,
  error        TEXT NOT NULL,
  resolved     INTEGER NOT NULL DEFAULT 0
);
"""


def _current_version(conn: sqlite3.Connection) -> int:
    return int(conn.execute("PRAGMA user_version").fetchone()[0])


def migrate(conn: sqlite3.Connection) -> None:
    version = _current_version(conn)
    if version < 1:
        conn.executescript(_SQL_V1)
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
