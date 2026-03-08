from __future__ import annotations

import sqlite3
import sys
from pathlib import Path


def check(db_path: Path) -> None:
    if not db_path.exists():
        print(f"[error] database not found: {db_path}")
        sys.exit(1)
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"[ok] tables: {tables}")
        for table in tables:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  {table}: {count} rows")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/memory.db")
    args = parser.parse_args()
    check(Path(args.db))
