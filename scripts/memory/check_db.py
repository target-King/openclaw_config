from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Thresholds for bloat warnings
# ---------------------------------------------------------------------------
CHUNK_COUNT_WARN = 10          # per dialog+topic
TOTAL_CONTENT_WARN = 50000     # total chars across all chunks
L3_ACTIVE_FACT_WARN = 50       # L3 active fact count warning
L3_ACTIVE_FACT_CRITICAL = 100  # L3 active fact count critical
L2_VERSION_WARN = 5            # per dialog+topic summary version accumulation
STALE_DIALOG_DAYS = 7          # days without activity before a dialog is stale


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
            version_bloated = []
            for dialog_id, topic, cnt, latest_ver in summaries:
                marker = " [!]" if cnt > L2_VERSION_WARN else ""
                print(f"  {dialog_id} / {topic}: {cnt} summaries, latest version={latest_ver}{marker}")
                if cnt > L2_VERSION_WARN:
                    version_bloated.append((dialog_id, topic, cnt))

            if version_bloated:
                print(f"\n[warn] {len(version_bloated)} dialog+topic group(s) have too many summary versions (>{L2_VERSION_WARN}):")
                for d, t, c in version_bloated:
                    print(f"  -> {d}/{t} ({c} versions) — consider: python summarize_topic.py --dialog-id {d} --topic {t}")

        # --- L3 facts overview ----------------------------------------------
        fact_count = conn.execute(
            "SELECT COUNT(*) FROM long_term_facts WHERE status = 'active'"
        ).fetchone()[0]
        print(f"\n----- L3 active facts: {fact_count} -----")

        if fact_count > L3_ACTIVE_FACT_CRITICAL:
            print(f"[critical] L3 active fact count ({fact_count}) exceeds critical threshold ({L3_ACTIVE_FACT_CRITICAL})")
            categories = conn.execute(
                "SELECT category, COUNT(*) AS cnt FROM long_term_facts WHERE status = 'active' GROUP BY category ORDER BY cnt DESC"
            ).fetchall()
            print("  by category:")
            for cat, cnt in categories:
                print(f"    {cat}: {cnt}")
            print("  -> review low-confidence facts: SELECT * FROM long_term_facts WHERE status = 'active' AND confidence < 60")
        elif fact_count > L3_ACTIVE_FACT_WARN:
            print(f"[warn] L3 active fact count ({fact_count}) exceeds warning threshold ({L3_ACTIVE_FACT_WARN})")
            categories = conn.execute(
                "SELECT category, COUNT(*) AS cnt FROM long_term_facts WHERE status = 'active' GROUP BY category ORDER BY cnt DESC"
            ).fetchall()
            print("  by category:")
            for cat, cnt in categories:
                print(f"    {cat}: {cnt}")
            print("  -> consider archiving stale facts")

        # --- Global content size warning ------------------------------------
        total_content = conn.execute(
            "SELECT COALESCE(SUM(LENGTH(content)), 0) FROM conversation_chunks"
        ).fetchone()[0]
        if total_content > TOTAL_CONTENT_WARN:
            print(f"\n[warn] total L1 content size = {total_content} chars (threshold {TOTAL_CONTENT_WARN})")
            print("  -> consider running: python compact_memory.py --auto")
        else:
            print(f"\n[info] total L1 content size = {total_content} chars")

        # --- Stale dialogs ---------------------------------------------------
        stale = conn.execute(
            """
            SELECT dialog_id, MAX(created_at) AS last_active, COUNT(*) AS cnt
            FROM conversation_chunks
            GROUP BY dialog_id
            HAVING MAX(created_at) < datetime('now', ? || ' days')
            ORDER BY last_active ASC
            """,
            (f"-{STALE_DIALOG_DAYS}",),
        ).fetchall()

        if stale:
            print(f"\n----- Stale dialogs (>{STALE_DIALOG_DAYS} days inactive) -----")
            for dialog_id, last_active, cnt in stale:
                l2_cnt = conn.execute(
                    "SELECT COUNT(*) FROM topic_summaries WHERE dialog_id = ?",
                    (dialog_id,),
                ).fetchone()[0]
                parts = f"  {dialog_id}: last active {last_active}, {cnt} L1 chunks"
                if l2_cnt:
                    parts += f", {l2_cnt} L2 summaries"
                print(parts)
            print(f"  -> consider: python expire_dialogs.py --execute")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/memory.db")
    args = parser.parse_args()
    check(Path(args.db))
