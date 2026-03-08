"""Tests for dialog lifecycle management: expiry, L2 version pruning, L3 guardrails."""
from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

# Ensure sibling modules are importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from init_db import init_db
from expire_dialogs import scan_stale_dialogs, expire_l1, expire_l2, expire_all
from summarize_topic import summarize, _prune_old_versions, MAX_SUMMARY_VERSIONS

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_pass = 0
_fail = 0


def _make_db() -> Path:
    d = tempfile.mkdtemp()
    db = Path(d) / "test_lifecycle.db"
    init_db(db)
    return db


def _insert_chunk(conn: sqlite3.Connection, dialog_id: str, topic: str, role: str, content: str) -> None:
    conn.execute(
        "INSERT INTO conversation_chunks(dialog_id, topic, role, content) VALUES (?, ?, ?, ?)",
        (dialog_id, topic, role, content),
    )


def _insert_summary(conn: sqlite3.Connection, dialog_id: str, topic: str, version: int, summary: str) -> None:
    conn.execute(
        "INSERT INTO topic_summaries(dialog_id, topic, summary, summary_version, source_chunk_count) VALUES (?, ?, ?, ?, ?)",
        (dialog_id, topic, summary, version, 1),
    )


def _insert_fact(conn: sqlite3.Connection, category: str, key: str, value: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO long_term_facts(category, key, value) VALUES (?, ?, ?)",
        (category, key, value),
    )


def _backdate_chunks(conn: sqlite3.Connection, dialog_id: str, days: int) -> None:
    conn.execute(
        "UPDATE conversation_chunks SET created_at = datetime('now', ? || ' days') WHERE dialog_id = ?",
        (f"-{days}", dialog_id),
    )


def _backdate_summaries(conn: sqlite3.Connection, dialog_id: str, days: int) -> None:
    conn.execute(
        "UPDATE topic_summaries SET updated_at = datetime('now', ? || ' days') WHERE dialog_id = ?",
        (f"-{days}", dialog_id),
    )


def _chunk_count(conn: sqlite3.Connection, dialog_id: str) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM conversation_chunks WHERE dialog_id = ?", (dialog_id,),
    ).fetchone()[0]


def _summary_count(conn: sqlite3.Connection, dialog_id: str) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM topic_summaries WHERE dialog_id = ?", (dialog_id,),
    ).fetchone()[0]


def _fact_count(conn: sqlite3.Connection) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM long_term_facts WHERE status = 'active'",
    ).fetchone()[0]


def check(name: str, condition: bool) -> None:
    global _pass, _fail
    if condition:
        _pass += 1
        print(f"  [PASS] {name}")
    else:
        _fail += 1
        print(f"  [FAIL] {name}")


# ---------------------------------------------------------------------------
# TA: Dialog Expiry Tests
# ---------------------------------------------------------------------------

def test_ta1_scan_identifies_stale():
    """scan_stale_dialogs returns dialogs inactive for > expire_days."""
    db = _make_db()
    with sqlite3.connect(db) as conn:
        _insert_chunk(conn, "stale-1", "general", "user", "old message")
        _backdate_chunks(conn, "stale-1", 10)
        _insert_chunk(conn, "active-1", "general", "user", "new message")
        conn.commit()

    stale = scan_stale_dialogs(db, 7)
    ids = [r[0] for r in stale]
    check("TA.1 scan finds stale dialog", "stale-1" in ids)
    check("TA.1 scan excludes active dialog", "active-1" not in ids)


def test_ta2_expire_l1_deletes():
    """expire_l1 with dry_run=False deletes all L1 chunks."""
    db = _make_db()
    with sqlite3.connect(db) as conn:
        for i in range(5):
            _insert_chunk(conn, "d-expire", "general", "user", f"msg {i}")
        conn.commit()

    deleted = expire_l1(db, "d-expire", dry_run=False)
    with sqlite3.connect(db) as conn:
        remaining = _chunk_count(conn, "d-expire")
    check("TA.2 expire_l1 deletes all chunks", deleted == 5 and remaining == 0)


def test_ta3_l2_within_grace_not_deleted():
    """L2 summaries within the grace period are NOT deleted."""
    db = _make_db()
    with sqlite3.connect(db) as conn:
        _insert_summary(conn, "d-grace", "general", 1, "summary text")
        _backdate_summaries(conn, "d-grace", 8)  # 8 days old, grace = 14
        conn.commit()

    deleted = expire_l2(db, "d-grace", 14, dry_run=False)
    with sqlite3.connect(db) as conn:
        remaining = _summary_count(conn, "d-grace")
    check("TA.3 L2 within grace period preserved", deleted == 0 and remaining == 1)


def test_ta4_l2_past_grace_deleted():
    """L2 summaries past the grace period ARE deleted."""
    db = _make_db()
    with sqlite3.connect(db) as conn:
        _insert_summary(conn, "d-old", "general", 1, "old summary")
        _backdate_summaries(conn, "d-old", 20)  # 20 days old, grace = 14
        conn.commit()

    deleted = expire_l2(db, "d-old", 14, dry_run=False)
    with sqlite3.connect(db) as conn:
        remaining = _summary_count(conn, "d-old")
    check("TA.4 L2 past grace period deleted", deleted == 1 and remaining == 0)


def test_ta5_active_dialog_untouched():
    """Active dialogs are not returned by scan and not affected by expire_all."""
    db = _make_db()
    with sqlite3.connect(db) as conn:
        _insert_chunk(conn, "d-active", "general", "user", "recent message")
        conn.commit()

    stale = scan_stale_dialogs(db, 7)
    ids = [r[0] for r in stale]
    check("TA.5 active dialog not in stale list", "d-active" not in ids)


def test_ta6_dry_run_no_deletion():
    """dry_run=True reports counts but does not delete."""
    db = _make_db()
    with sqlite3.connect(db) as conn:
        for i in range(3):
            _insert_chunk(conn, "d-dry", "general", "user", f"msg {i}")
        conn.commit()

    reported = expire_l1(db, "d-dry", dry_run=True)
    with sqlite3.connect(db) as conn:
        remaining = _chunk_count(conn, "d-dry")
    check("TA.6 dry_run reports count", reported == 3)
    check("TA.6 dry_run does not delete", remaining == 3)


def test_ta7_l3_not_affected():
    """Dialog expiry does not touch L3 facts."""
    db = _make_db()
    with sqlite3.connect(db) as conn:
        _insert_chunk(conn, "d-expire3", "general", "user", "msg")
        _backdate_chunks(conn, "d-expire3", 10)
        _insert_fact(conn, "test-cat", "test-key", "test-value")
        conn.commit()

    with sqlite3.connect(db) as conn:
        before = _fact_count(conn)

    expire_all(db, 7, 14, dry_run=False, dialog_id="d-expire3")

    with sqlite3.connect(db) as conn:
        after = _fact_count(conn)
    check("TA.7 L3 facts unchanged after expiry", before == after and after == 1)


# ---------------------------------------------------------------------------
# TB: L2 Version Pruning Tests
# ---------------------------------------------------------------------------

def test_tb1_prune_keeps_latest_n():
    """After 5 versions, pruning keeps only the latest 3."""
    db = _make_db()
    with sqlite3.connect(db) as conn:
        for v in range(1, 6):
            _insert_summary(conn, "d-prune", "topic-a", v, f"summary v{v}")
        conn.commit()

        pruned = _prune_old_versions(conn, "d-prune", "topic-a", 3)
        conn.commit()

        remaining = conn.execute(
            "SELECT summary_version FROM topic_summaries WHERE dialog_id = 'd-prune' AND topic = 'topic-a' ORDER BY summary_version",
        ).fetchall()
        versions = [r[0] for r in remaining]

    check("TB.1 pruned 2 old versions", pruned == 2)
    check("TB.1 kept versions 3,4,5", versions == [3, 4, 5])


def test_tb2_no_prune_when_within_limit():
    """When version count <= keep_n, nothing is pruned."""
    db = _make_db()
    with sqlite3.connect(db) as conn:
        for v in range(1, 4):
            _insert_summary(conn, "d-ok", "topic-b", v, f"summary v{v}")
        conn.commit()

        pruned = _prune_old_versions(conn, "d-ok", "topic-b", 3)
        conn.commit()

        count = _summary_count(conn, "d-ok")
    check("TB.2 no pruning when within limit", pruned == 0 and count == 3)


def test_tb3_prune_isolated_per_dialog_topic():
    """Pruning one dialog+topic does not affect another."""
    db = _make_db()
    with sqlite3.connect(db) as conn:
        for v in range(1, 6):
            _insert_summary(conn, "d-a", "topic-x", v, f"summary v{v}")
            _insert_summary(conn, "d-b", "topic-x", v, f"summary v{v}")
        conn.commit()

        _prune_old_versions(conn, "d-a", "topic-x", 3)
        conn.commit()

        count_a = conn.execute(
            "SELECT COUNT(*) FROM topic_summaries WHERE dialog_id = 'd-a' AND topic = 'topic-x'",
        ).fetchone()[0]
        count_b = conn.execute(
            "SELECT COUNT(*) FROM topic_summaries WHERE dialog_id = 'd-b' AND topic = 'topic-x'",
        ).fetchone()[0]

    check("TB.3 d-a pruned to 3", count_a == 3)
    check("TB.3 d-b untouched at 5", count_b == 5)


def test_tb4_summarize_auto_prunes():
    """Calling summarize() auto-prunes old versions via the integrated call."""
    db = _make_db()
    dialog = "d-auto-prune"
    topic = "topic-auto"

    # Insert enough chunks so summarize works
    with sqlite3.connect(db) as conn:
        for i in range(3):
            _insert_chunk(conn, dialog, topic, "user", f"message {i}")
            _insert_chunk(conn, dialog, topic, "assistant", f"reply {i}")
        conn.commit()

    # Generate 5 summaries
    for _ in range(5):
        summarize(db, dialog, topic, 10, keep_versions=3)

    with sqlite3.connect(db) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM topic_summaries WHERE dialog_id = ? AND topic = ?",
            (dialog, topic),
        ).fetchone()[0]

    check("TB.4 summarize auto-prunes to keep_versions=3", count == 3)


# ---------------------------------------------------------------------------
# Run all
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("Dialog Lifecycle Tests")
    print("=" * 60)

    print("\n--- TA: Dialog Expiry ---")
    test_ta1_scan_identifies_stale()
    test_ta2_expire_l1_deletes()
    test_ta3_l2_within_grace_not_deleted()
    test_ta4_l2_past_grace_deleted()
    test_ta5_active_dialog_untouched()
    test_ta6_dry_run_no_deletion()
    test_ta7_l3_not_affected()

    print("\n--- TB: L2 Version Pruning ---")
    test_tb1_prune_keeps_latest_n()
    test_tb2_no_prune_when_within_limit()
    test_tb3_prune_isolated_per_dialog_topic()
    test_tb4_summarize_auto_prunes()

    print()
    print("=" * 60)
    total = _pass + _fail
    print(f"Results: {_pass}/{total} passed, {_fail} failed")
    if _fail:
        print("SOME TESTS FAILED")
        sys.exit(1)
    else:
        print("ALL TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
