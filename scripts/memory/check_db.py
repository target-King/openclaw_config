from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Thresholds for bloat warnings
# ---------------------------------------------------------------------------
CHUNK_COUNT_WARN = 10          # per dialog+topic
TOTAL_CONTENT_WARN = 50000     # total chars across all chunks


def check(db_path: Path) -> None:
    if not db_path.exists():
        print(f"[error] database not found: {db_path}")
        sys.exit(1)

    with sqlite3.connect(db_path) as conn:
        # --- Basic table overview -------------------------------------------
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"[ok] tables: {tables}")
        for table in tables:
            count = conn.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()[0]
            print(f"  {table}: {count} rows")

        # --- Per dialog+topic breakdown (L1) --------------------------------
        groups = conn.execute(
            """
            SELECT dialog_id, topic, COUNT(*) AS cnt, SUM(LENGTH(content)) AS total_chars
            FROM conversation_chunks
            GROUP BY dialog_id, topic
            ORDER BY cnt DESC
            """
        ).fetchall()

        if groups:
            print("\n----- L1 chunks by dialog+topic -----")
            bloated = []
            for dialog_id, topic, cnt, total_chars in groups:
                marker = " [!]" if cnt > CHUNK_COUNT_WARN else ""
                print(f"  {dialog_id} / {topic}: {cnt} chunks, {total_chars} chars{marker}")
                if cnt > CHUNK_COUNT_WARN:
                    bloated.append((dialog_id, topic, cnt))

            if bloated:
                print(f"\n[warn] {len(bloated)} dialog+topic group(s) exceed threshold ({CHUNK_COUNT_WARN} chunks):")
                for d, t, c in bloated:
                    print(f"  -> {d}/{t} ({c} chunks) — consider: python compact_memory.py --dialog-id {d} --delete-summarized")

        # --- Per dialog+topic breakdown (L2) --------------------------------
        summaries = conn.execute(
            """
            SELECT dialog_id, topic, COUNT(*) AS cnt, MAX(summary_version) AS latest_ver
            FROM topic_summaries
            GROUP BY dialog_id, topic
            ORDER BY cnt DESC
            """
        ).fetchall()

        if summaries:
            print("\n----- L2 summaries by dialog+topic -----")
            for dialog_id, topic, cnt, latest_ver in summaries:
                print(f"  {dialog_id} / {topic}: {cnt} summaries, latest version={latest_ver}")

        # --- L3 facts overview ----------------------------------------------
        fact_count = conn.execute(
            "SELECT COUNT(*) FROM long_term_facts WHERE status = 'active'"
        ).fetchone()[0]
        print(f"\n----- L3 active facts: {fact_count} -----")

        # --- Global content size warning ------------------------------------
        total_content = conn.execute(
            "SELECT COALESCE(SUM(LENGTH(content)), 0) FROM conversation_chunks"
        ).fetchone()[0]
        if total_content > TOTAL_CONTENT_WARN:
            print(f"\n[warn] total L1 content size = {total_content} chars (threshold {TOTAL_CONTENT_WARN})")
            print("  -> consider running: python compact_memory.py --auto")
        else:
            print(f"\n[info] total L1 content size = {total_content} chars")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/memory.db")
    args = parser.parse_args()
    check(Path(args.db))
