from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_EXPIRE_DAYS = 7        # L1 chunks: no activity for 7 days -> stale
DEFAULT_L2_GRACE_DAYS = 14     # L2 summaries: extra grace period before deletion


def ensure_db_exists(db_path: Path) -> None:
    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}. Run init_db.py first.")


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------

def scan_stale_dialogs(
    db_path: Path,
    expire_days: int,
    *,
    dialog_id: str = "",
) -> list[tuple[str, str, int]]:
    """Return list of (dialog_id, last_active, chunk_count) for stale dialogs."""
    ensure_db_exists(db_path)
    with sqlite3.connect(db_path) as conn:
        if dialog_id:
            rows = conn.execute(
                """
                SELECT dialog_id, MAX(created_at) AS last_active, COUNT(*) AS cnt
                FROM conversation_chunks
                WHERE dialog_id = ?
                GROUP BY dialog_id
                HAVING MAX(created_at) < datetime('now', ? || ' days')
                """,
                (dialog_id, f"-{expire_days}"),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT dialog_id, MAX(created_at) AS last_active, COUNT(*) AS cnt
                FROM conversation_chunks
                GROUP BY dialog_id
                HAVING MAX(created_at) < datetime('now', ? || ' days')
                ORDER BY last_active ASC
                """,
                (f"-{expire_days}",),
            ).fetchall()
    return rows


# ---------------------------------------------------------------------------
# Expire L1
# ---------------------------------------------------------------------------

def expire_l1(db_path: Path, dialog_id: str, *, dry_run: bool = True) -> int:
    """Delete all L1 chunks for *dialog_id*. Returns the number of deleted rows."""
    ensure_db_exists(db_path)
    with sqlite3.connect(db_path) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM conversation_chunks WHERE dialog_id = ?",
            (dialog_id,),
        ).fetchone()[0]
        if count == 0:
            return 0
        if dry_run:
            return count
        conn.execute(
            "DELETE FROM conversation_chunks WHERE dialog_id = ?",
            (dialog_id,),
        )
        conn.commit()
    return count


# ---------------------------------------------------------------------------
# Expire L2
# ---------------------------------------------------------------------------

def expire_l2(db_path: Path, dialog_id: str, grace_days: int, *, dry_run: bool = True) -> int:
    """Delete L2 summaries for *dialog_id* whose updated_at exceeds the grace period."""
    ensure_db_exists(db_path)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id FROM topic_summaries
            WHERE dialog_id = ?
              AND updated_at < datetime('now', ? || ' days')
            """,
            (dialog_id, f"-{grace_days}"),
        ).fetchall()
        if not rows:
            return 0
        if dry_run:
            return len(rows)
        conn.executemany(
            "DELETE FROM topic_summaries WHERE id = ?",
            [(r[0],) for r in rows],
        )
        conn.commit()
    return len(rows)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def expire_all(
    db_path: Path,
    expire_days: int,
    l2_grace_days: int,
    *,
    dry_run: bool = True,
    dialog_id: str = "",
    keep_l2: bool = False,
) -> dict[str, dict[str, int]]:
    """Scan stale dialogs and expire their L1 (and optionally L2) data."""
    stale = scan_stale_dialogs(db_path, expire_days, dialog_id=dialog_id)

    if not stale:
        print(f"[scan] no stale dialogs found (threshold: {expire_days} days)")
        return {}

    print(f"[scan] found {len(stale)} stale dialog(s) (threshold: {expire_days} days)")

    results: dict[str, dict[str, int]] = {}
    total_l1 = 0
    total_l2 = 0

    for d_id, last_active, chunk_count in stale:
        l1_count = expire_l1(db_path, d_id, dry_run=dry_run)
        l2_count = 0
        if not keep_l2:
            l2_count = expire_l2(db_path, d_id, l2_grace_days, dry_run=dry_run)

        parts = f"  {d_id}: last active {last_active}, {l1_count} L1 chunks"
        if l2_count:
            parts += f", {l2_count} L2 summaries"
        print(parts)

        results[d_id] = {"l1_deleted": l1_count, "l2_deleted": l2_count}
        total_l1 += l1_count
        total_l2 += l2_count

    if dry_run:
        msg = f"\n[dry-run] would delete {total_l1} L1 chunks"
        if total_l2:
            msg += f", {total_l2} L2 summaries"
        msg += f" across {len(stale)} dialog(s)"
        print(msg)
        print("  -> re-run with --execute to apply")
    else:
        msg = f"\n[ok] deleted {total_l1} L1 chunks"
        if total_l2:
            msg += f", {total_l2} L2 summaries"
        msg += f" across {len(stale)} dialog(s)"
        print(msg)

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Expire stale dialogs and clean up their L1/L2 data.")
    parser.add_argument("--db", default="data/memory.db", help="Path to SQLite database.")
    parser.add_argument("--expire-days", type=int, default=DEFAULT_EXPIRE_DAYS, help="Days without activity before a dialog is stale.")
    parser.add_argument("--l2-grace-days", type=int, default=DEFAULT_L2_GRACE_DAYS, help="Extra grace days before L2 summaries are deleted.")
    parser.add_argument("--dialog-id", default="", help="Target a specific dialog. If empty, scan all.")
    parser.add_argument("--keep-l2", action="store_true", help="Only expire L1 chunks, never delete L2 summaries.")

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", default=True, help="Report only, do not delete (default).")
    mode.add_argument("--execute", action="store_true", help="Actually delete expired data.")
    args = parser.parse_args()

    dry_run = not args.execute

    expire_all(
        Path(args.db),
        args.expire_days,
        args.l2_grace_days,
        dry_run=dry_run,
        dialog_id=args.dialog_id,
        keep_l2=args.keep_l2,
    )


if __name__ == "__main__":
    main()
