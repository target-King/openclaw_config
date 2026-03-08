from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS conversation_chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dialog_id TEXT NOT NULL DEFAULT 'default',
        topic TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        source TEXT DEFAULT 'manual',
        importance INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS topic_summaries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dialog_id TEXT NOT NULL DEFAULT 'default',
        topic TEXT NOT NULL,
        summary TEXT NOT NULL,
        summary_version INTEGER DEFAULT 1,
        source_chunk_count INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS long_term_facts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        key TEXT NOT NULL,
        value TEXT NOT NULL,
        confidence INTEGER DEFAULT 80,
        status TEXT DEFAULT 'active',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_conversation_dialog_topic_created
    ON conversation_chunks(dialog_id, topic, created_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_summary_dialog_topic_updated
    ON topic_summaries(dialog_id, topic, updated_at)
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_fact_category_key
    ON long_term_facts(category, key)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_conversation_dialog_created
    ON conversation_chunks(dialog_id, created_at)
    """,
]


def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        for sql in SCHEMA:
            conn.execute(sql)
        conn.commit()
    print(f"[ok] initialized database: {db_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize local memory SQLite database.")
    parser.add_argument("--db", default="data/memory.db", help="Path to SQLite database file.")
    args = parser.parse_args()
    init_db(Path(args.db))


if __name__ == "__main__":
    main()
