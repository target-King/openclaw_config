from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from typing import Iterable


def ensure_db_exists(db_path: Path) -> None:
    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}. Run init_db.py first.")


def query_like_terms(keywords: str) -> list[str]:
    terms = [x.strip() for x in keywords.split(",") if x.strip()]
    return [f"%{t}%" for t in terms]


def retrieve_recent_chunks(conn: sqlite3.Connection, dialog_id: str, topic: str, limit: int) -> list[tuple]:
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


def print_section(title: str, rows: Iterable[tuple]) -> None:
    print(f"\n===== {title} =====")
    found = False
    for row in rows:
        found = True
        print(row)
    if not found:
        print("(empty)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrieve memory context from SQLite.")
    parser.add_argument("--db", default="data/memory.db", help="Path to SQLite database.")
    parser.add_argument("--dialog-id", required=True, help="Dialog identifier for session isolation.")
    parser.add_argument("--topic", default="", help="Topic name.")
    parser.add_argument("--keywords", default="", help="Comma separated keywords.")
    parser.add_argument("--recent-limit", type=int, default=3, help="Recent L1 chunk limit.")
    parser.add_argument("--summary-limit", type=int, default=2, help="L2 summary limit.")
    parser.add_argument("--fact-limit", type=int, default=5, help="L3 fact limit.")
    args = parser.parse_args()

    db_path = Path(args.db)
    ensure_db_exists(db_path)

    with sqlite3.connect(db_path) as conn:
        if args.topic:
            recent = retrieve_recent_chunks(conn, args.dialog_id, args.topic, args.recent_limit)
            summary = retrieve_summary(conn, args.dialog_id, args.topic, args.summary_limit)
        else:
            recent = []
            summary = []
        # L3 facts are global — no dialog_id filter
        facts = retrieve_facts(conn, args.keywords, args.fact_limit)

    print_section("L1 Recent Chunks", recent)
    print_section("L2 Topic Summaries", summary)
    print_section("L3 Long-term Facts", facts)


if __name__ == "__main__":
    main()
