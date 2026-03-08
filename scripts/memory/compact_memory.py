from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def ensure_db_exists(db_path: Path) -> None:
    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}. Run init_db.py first.")


def compact(db_path: Path, dialog_id: str, keep_recent: int, delete_summarized: bool) -> None:
    ensure_db_exists(db_path)

    with sqlite3.connect(db_path) as conn:
        # Group by dialog_id + topic for proper isolation
        if dialog_id:
            groups = conn.execute(
                "SELECT DISTINCT dialog_id, topic FROM conversation_chunks WHERE dialog_id = ?",
                (dialog_id,),
            ).fetchall()
        else:
            groups = conn.execute(
                "SELECT DISTINCT dialog_id, topic FROM conversation_chunks"
            ).fetchall()

        total_deleted = 0
        for d_id, topic in groups:
            has_summary = conn.execute(
                "SELECT 1 FROM topic_summaries WHERE dialog_id = ? AND topic = ? LIMIT 1",
                (d_id, topic),
            ).fetchone()

            if delete_summarized and has_summary:
                rows = conn.execute(
                    """
                    SELECT id
                    FROM conversation_chunks
                    WHERE dialog_id = ? AND topic = ?
                    ORDER BY id DESC
                    """,
                    (d_id, topic),
                ).fetchall()

                keep_ids = {row[0] for row in rows[:keep_recent]}
                delete_ids = [row[0] for row in rows if row[0] not in keep_ids]

                if delete_ids:
                    conn.executemany(
                        "DELETE FROM conversation_chunks WHERE id = ?",
                        [(x,) for x in delete_ids],
                    )
                    total_deleted += len(delete_ids)

        conn.commit()

    print(f"[ok] compact finished, deleted chunks: {total_deleted}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compact old conversation chunks after summaries exist.")
    parser.add_argument("--db", default="data/memory.db", help="Path to SQLite database.")
    parser.add_argument("--dialog-id", default="", help="Dialog identifier. If empty, compact ALL dialogs (use with caution).")
    parser.add_argument("--keep-recent", type=int, default=3, help="How many recent chunks to keep per dialog+topic.")
    parser.add_argument(
        "--delete-summarized",
        action="store_true",
        help="Delete older chunks only if the dialog+topic already has at least one summary.",
    )
    args = parser.parse_args()

    compact(Path(args.db), args.dialog_id, args.keep_recent, args.delete_summarized)


if __name__ == "__main__":
    main()
