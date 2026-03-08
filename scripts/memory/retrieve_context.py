from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from typing import Iterable

# ---------------------------------------------------------------------------
# Tunable limits
# ---------------------------------------------------------------------------
CONTEXT_WARN_CHARS = 3000      # 总 context 字符数告警阈值


def ensure_db_exists(db_path: Path) -> None:
    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}. Run init_db.py first.")


def query_like_terms(keywords: str) -> list[str]:
    terms = [x.strip() for x in keywords.split(",") if x.strip()]
    return [f"%{t}%" for t in terms]


# ---------------------------------------------------------------------------
# Layer retrievers
# ---------------------------------------------------------------------------

def retrieve_recent_chunks(
    conn: sqlite3.Connection, dialog_id: str, topic: str, limit: int
) -> list[tuple]:
    return conn.execute(
        """
        SELECT id, role, content, created_at
        FROM conversation_chunks
        WHERE dialog_id = ? AND topic = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (dialog_id, topic, limit),
    ).fetchall()


def retrieve_summary(conn: sqlite3.Connection, dialog_id: str, topic: str, limit: int) -> list[tuple]:
    return conn.execute(
        """
        SELECT id, summary_version, summary, updated_at
        FROM topic_summaries
        WHERE dialog_id = ? AND topic = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (dialog_id, topic, limit),
    ).fetchall()


def retrieve_facts(conn: sqlite3.Connection, keywords: str, limit: int) -> list[tuple]:
    if not keywords:
        return conn.execute(
            """
            SELECT id, category, key, value, updated_at
            FROM long_term_facts
            WHERE status = 'active'
            ORDER BY updated_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    terms = query_like_terms(keywords)
    conditions = []
    params: list[str | int] = []
    for term in terms:
        conditions.append("(key LIKE ? OR value LIKE ?)")
        params.extend([term, term])

    sql = f"""
        SELECT id, category, key, value, updated_at
        FROM long_term_facts
        WHERE status = 'active' AND ({' OR '.join(conditions)})
        ORDER BY updated_at DESC, id DESC
        LIMIT ?
    """
    params.append(limit)
    return conn.execute(sql, params).fetchall()


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def _rows_char_size(rows: Iterable[tuple]) -> int:
    return sum(len(str(r)) for r in rows)


def print_section(title: str, rows: list[tuple]) -> int:
    """Print a section and return total character count."""
    print(f"\n===== {title} =====")
    if not rows:
        print("(empty)")
        return 0
    for row in rows:
        print(row)
    return _rows_char_size(rows)


# ---------------------------------------------------------------------------
# Main — implements short-circuit retrieval (L1 → L2 → L3)
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Retrieve memory context from SQLite.")
    parser.add_argument("--db", default="data/memory.db", help="Path to SQLite database.")
    parser.add_argument("--dialog-id", required=True, help="Dialog identifier for session isolation.")
    parser.add_argument("--topic", default="", help="Topic name. If empty and --auto-topic is set, auto-classify from --query.")
    parser.add_argument("--query", default="", help="The current user query (used for auto-topic classification).")
    parser.add_argument("--keywords", default="", help="Comma separated keywords.")
    parser.add_argument("--recent-limit", type=int, default=4, help="Recent L1 chunk limit (default 4 = 2 rounds).")
    parser.add_argument("--summary-limit", type=int, default=1, help="L2 summary limit.")
    parser.add_argument("--fact-limit", type=int, default=3, help="L3 fact limit.")
    parser.add_argument("--auto-topic", action="store_true", help="Auto-classify topic from --query when --topic is empty.")
    args = parser.parse_args()

    db_path = Path(args.db)
    ensure_db_exists(db_path)

    # --- Resolve topic ------------------------------------------------------
    topic = args.topic
    if not topic and args.auto_topic:
        from topic_classifier import classify
        topic = classify(args.query or args.keywords)
        print(f"[auto-topic] classified as: {topic}")
    elif not topic and args.query:
        from topic_classifier import classify
        topic = classify(args.query)
        print(f"[auto-topic] classified as: {topic}")

    total_chars = 0
    recent: list[tuple] = []
    summary: list[tuple] = []
    facts: list[tuple] = []

    with sqlite3.connect(db_path) as conn:
        if topic:
            # --- Short-circuit: if L2 summary exists, reduce L1 to 1 --------
            summary = retrieve_summary(conn, args.dialog_id, topic, args.summary_limit)
            if summary:
                recent = retrieve_recent_chunks(conn, args.dialog_id, topic, min(args.recent_limit, 1))
            else:
                recent = retrieve_recent_chunks(conn, args.dialog_id, topic, args.recent_limit)

        # L3 facts are global — no dialog_id filter
        # Only query L3 when L1+L2 are insufficient or keywords explicitly provided
        if args.keywords or (not recent and not summary):
            facts = retrieve_facts(conn, args.keywords, args.fact_limit)

    total_chars += print_section("L1 Recent Chunks", recent)
    total_chars += print_section("L2 Topic Summaries", summary)
    total_chars += print_section("L3 Long-term Facts", facts)

    # Context size warning
    if total_chars > CONTEXT_WARN_CHARS:
        print(f"\n[warn] total context size = {total_chars} chars (threshold {CONTEXT_WARN_CHARS}), consider compacting")
    else:
        print(f"\n[info] total context size = {total_chars} chars")


if __name__ == "__main__":
    main()
