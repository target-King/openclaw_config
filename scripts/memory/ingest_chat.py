from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def ensure_db_exists(db_path: Path) -> None:
    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}. Run init_db.py first.")


def ingest(db_path: Path, dialog_id: str, topic: str, role: str, content: str, source: str, importance: int) -> None:
    ensure_db_exists(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO conversation_chunks(dialog_id, topic, role, content, source, importance)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (dialog_id, topic, role, content, source, importance),
        )
        conn.commit()
    print(f"[ok] inserted conversation chunk (dialog={dialog_id})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Insert one conversation chunk into local memory DB.")
    parser.add_argument("--db", default="data/memory.db", help="Path to SQLite database.")
    parser.add_argument("--dialog-id", required=True, help="Dialog identifier for session isolation.")
    parser.add_argument("--topic", required=True, help="Topic name.")
    parser.add_argument("--role", required=True, choices=["user", "assistant", "system", "tool"], help="Role.")
    parser.add_argument("--content", required=True, help="Conversation text content.")
    parser.add_argument("--source", default="manual", help="Source label.")
    parser.add_argument("--importance", type=int, default=1, help="Importance score, suggested 1-5.")
    args = parser.parse_args()

    ingest(Path(args.db), args.dialog_id, args.topic, args.role, args.content, args.source, args.importance)


if __name__ == "__main__":
    main()
