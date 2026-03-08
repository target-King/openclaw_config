from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

# ---------------------------------------------------------------------------
# Tunable limits
# ---------------------------------------------------------------------------
MAX_SUMMARY_LINES = 15         # 摘要最大行数
MAX_LINE_CHARS = 200           # 摘要中每条的字符上限
ROLES_PRIORITY = ("assistant", "user")  # 优先保留的角色（结论 > 提问 > 工具输出）


def ensure_db_exists(db_path: Path) -> None:
    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}. Run init_db.py first.")


def _shorten(text: str, max_len: int = MAX_LINE_CHARS) -> str:
    short = " ".join(text.strip().split())
    if len(short) <= max_len:
        return short
    return short[: max_len - 3] + "..."


def build_summary(rows: list[tuple], topic: str) -> str:
    """Build a compact summary that prioritises conclusions over raw output.

    Improvements over the original starter implementation:
    - Filters out ``role=tool`` rows (verbose tool output adds noise, not value)
    - Prioritises ``assistant`` conclusions, then ``user`` questions
    - Deduplicates near-identical lines
    - Caps total line count to keep summaries lean
    """
    if not rows:
        return f"Topic: {topic}\nNo source chunks found."

    # Separate rows by role; skip tool output entirely
    prioritised: list[tuple] = []
    for row in rows:
        _, role, content, created_at = row
        if role == "tool":
            continue
        prioritised.append(row)

    # Sort: assistant first (conclusions), then user, then others
    def _role_order(r: tuple) -> int:
        role = r[1]
        if role == "assistant":
            return 0
        if role == "user":
            return 1
        return 2

    prioritised.sort(key=_role_order)

    lines: list[str] = [f"Topic: {topic}", "Key points:"]
    seen: set[str] = set()

    for _, role, content, created_at in prioritised:
        short = _shorten(content)
        # Simple deduplication — skip if we already have a very similar line
        dedup_key = short[:60].lower()
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        lines.append(f"- [{created_at}] {role}: {short}")
        if len(lines) >= MAX_SUMMARY_LINES:
            break

    skipped_tool = sum(1 for r in rows if r[1] == "tool")
    if skipped_tool:
        lines.append(f"(omitted {skipped_tool} tool-output chunks)")

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

    print(f"[ok] summary created (dialog={dialog_id}, topic={topic}, version={latest + 1}, source_chunks={len(rows)})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a simple topic summary from conversation chunks.")
    parser.add_argument("--db", default="data/memory.db", help="Path to SQLite database.")
    parser.add_argument("--dialog-id", required=True, help="Dialog identifier for session isolation.")
    parser.add_argument("--topic", required=True, help="Topic name.")
    parser.add_argument("--limit", type=int, default=15, help="How many recent chunks to include.")
    args = parser.parse_args()

    summarize(Path(args.db), args.dialog_id, args.topic, args.limit)


if __name__ == "__main__":
    main()
