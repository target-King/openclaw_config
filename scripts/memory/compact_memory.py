from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------
AUTO_SUMMARIZE_THRESHOLD = 5   # > 2 轮（4 条）即触发
DEFAULT_KEEP_RECENT = 4        # 保留最近 2 轮完整对话


def ensure_db_exists(db_path: Path) -> None:
    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}. Run init_db.py first.")


def _count_chunks(conn: sqlite3.Connection, dialog_id: str, topic: str) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM conversation_chunks WHERE dialog_id = ? AND topic = ?",
        (dialog_id, topic),
    ).fetchone()[0]


def compact(db_path: Path, dialog_id: str, keep_recent: int, delete_summarized: bool) -> None:
    """Delete old chunks, keeping only the *keep_recent* most recent per
    dialog+topic group — but only for groups that already have a summary."""
    ensure_db_exists(db_path)

    with sqlite3.connect(db_path) as conn:
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


def auto_compact(db_path: Path, dialog_id: str, keep_recent: int) -> None:
    """Auto mode: for each dialog+topic that exceeds the threshold, generate a
    summary (via summarize_topic) and then compact old chunks."""
    from summarize_topic import summarize

    ensure_db_exists(db_path)

    with sqlite3.connect(db_path) as conn:
        if dialog_id:
            groups = conn.execute(
                "SELECT DISTINCT dialog_id, topic FROM conversation_chunks WHERE dialog_id = ?",
                (dialog_id,),
            ).fetchall()
        else:
            groups = conn.execute(
                "SELECT DISTINCT dialog_id, topic FROM conversation_chunks"
            ).fetchall()

    compacted = 0
    for d_id, topic in groups:
        with sqlite3.connect(db_path) as conn:
            count = _count_chunks(conn, d_id, topic)
        if count <= AUTO_SUMMARIZE_THRESHOLD:
            continue

        print(f"[auto] {d_id}/{topic}: {count} chunks > threshold {AUTO_SUMMARIZE_THRESHOLD}, summarizing...")
        summarize(db_path, d_id, topic, limit=count)
        compact(db_path, d_id, keep_recent, delete_summarized=True)
        compacted += 1

    if compacted == 0:
        print("[auto] no dialog+topic exceeded threshold, nothing to do")
    else:
        print(f"[auto] compacted {compacted} dialog+topic group(s)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compact old conversation chunks after summaries exist.")
    parser.add_argument("--db", default="data/memory.db", help="Path to SQLite database.")
    parser.add_argument("--dialog-id", default="", help="Dialog identifier. If empty, compact ALL dialogs (use with caution).")
    parser.add_argument("--keep-recent", type=int, default=DEFAULT_KEEP_RECENT, help="How many recent chunks to keep per dialog+topic.")
    parser.add_argument(
        "--delete-summarized",
        action="store_true",
        help="Delete older chunks only if the dialog+topic already has at least one summary.",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Auto mode: summarize and compact any dialog+topic exceeding the chunk threshold.",
    )
    args = parser.parse_args()

    if args.auto:
        auto_compact(Path(args.db), args.dialog_id, args.keep_recent)
    else:
        compact(Path(args.db), args.dialog_id, args.keep_recent, args.delete_summarized)


if __name__ == "__main__":
    main()
