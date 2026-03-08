from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def ensure_db_exists(db_path: Path) -> None:
    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}. Run init_db.py first.")


def build_summary(rows: list[tuple], topic: str) -> str:
    if not rows:
        return f"Topic: {topic}\nNo source chunks found."

    lines = [f"Topic: {topic}", "Summary:"]
    for _, role, content, created_at in rows[:10]:
        short = " ".join(content.strip().split())
        if len(short) > 120:
            short = short[:117] + "..."
        lines.append(f"- [{created_at}] {role}: {short}")
    lines.append("Conclusion:")
    lines.append("- 当前为 starter 级摘要；后续可接入更强的摘要器。")
    return "\n".join(lines)


def summarize(db_path: Path, dialog_id: str, topic: str, limit: int) -> None:
    ensure_db_exists(db_path)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, role, content, created_at
            FROM conversation_chunks
            WHERE dialog_id = ? AND topic = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (dialog_id, topic, limit),
        ).fetchall()
        summary_text = build_summary(rows, topic)

        latest = conn.execute(
            """
            SELECT COALESCE(MAX(summary_version), 0)
            FROM topic_summaries
            WHERE dialog_id = ? AND topic = ?
            """,
            (dialog_id, topic),
        ).fetchone()[0]

        conn.execute(
            """
            INSERT INTO topic_summaries(dialog_id, topic, summary, summary_version, source_chunk_count)
            VALUES (?, ?, ?, ?, ?)
            """,
            (dialog_id, topic, summary_text, latest + 1, len(rows)),
        )
        conn.commit()

    print(f"[ok] summary created (dialog={dialog_id})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a simple topic summary from conversation chunks.")
    parser.add_argument("--db", default="data/memory.db", help="Path to SQLite database.")
    parser.add_argument("--dialog-id", required=True, help="Dialog identifier for session isolation.")
    parser.add_argument("--topic", required=True, help="Topic name.")
    parser.add_argument("--limit", type=int, default=20, help="How many recent chunks to include.")
    args = parser.parse_args()

    summarize(Path(args.db), args.dialog_id, args.topic, args.limit)


if __name__ == "__main__":
    main()
