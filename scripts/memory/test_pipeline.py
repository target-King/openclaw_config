"""End-to-end test for the three-layer memory pipeline."""
from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

DB = "/wwwroot/openclaw_config/data/memory.db"
SCRIPTS = "/wwwroot/openclaw_config/scripts/memory"
DIALOG = "test-dialog-001"
TOPIC = "openclaw-config"


def run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(f"$ {' '.join(cmd)}")
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.returncode != 0:
        print(f"[STDERR] {result.stderr.strip()}")
        sys.exit(1)
    return result.stdout


def main() -> None:
    print("=" * 60)
    print("Step 1: L1 - Ingest conversation chunks")
    print("=" * 60)

    test_messages = [
        ("user", "I want to set up a Git-managed OpenClaw control repo"),
        ("assistant", "I'll help you create the repo structure with agents, skills, and managed-config directories"),
        ("user", "What about memory? I need three-layer memory support"),
        ("assistant", "We'll implement L1 session, L2 topic summary, and L3 long-term facts using SQLite"),
        ("user", "Great, let's also add a project-analyst agent"),
        ("assistant", "Added project-analyst with responsibilities for feasibility analysis and MVP design"),
    ]

    for role, content in test_messages:
        run([
            "python3", f"{SCRIPTS}/ingest_chat.py",
            "--db", DB,
            "--dialog-id", DIALOG,
            "--topic", TOPIC,
            "--role", role,
            "--content", content,
            "--source", "e2e-test",
            "--importance", "2",
        ])

    print()
    print("=" * 60)
    print("Step 2: L2 - Generate topic summary")
    print("=" * 60)

    run([
        "python3", f"{SCRIPTS}/summarize_topic.py",
        "--db", DB,
        "--dialog-id", DIALOG,
        "--topic", TOPIC,
        "--limit", "20",
    ])

    print()
    print("=" * 60)
    print("Step 3: L3 - Insert long-term facts")
    print("=" * 60)

    conn = sqlite3.connect(DB)
    facts = [
        ("project-convention", "repo-structure", "agents/ skills/ managed-config/ scripts/ templates/ memory-spec/", 90),
        ("path-rule", "openclaw-home", "Linux: $HOME/.openclaw | Windows: %USERPROFILE%\\.openclaw", 95),
        ("memory-rule", "three-layer-mode", "L1=session L2=topic-summary L3=long-term-facts, retrieval order: L1->L2->L3", 90),
    ]
    for category, key, value, confidence in facts:
        conn.execute(
            "INSERT OR REPLACE INTO long_term_facts(category, key, value, confidence) VALUES (?, ?, ?, ?)",
            (category, key, value, confidence),
        )
        print(f"[ok] L3 fact inserted: [{category}] {key}")
    conn.commit()
    conn.close()

    print()
    print("=" * 60)
    print("Step 4: Full retrieval - L1 + L2 + L3")
    print("=" * 60)

    run([
        "python3", f"{SCRIPTS}/retrieve_context.py",
        "--db", DB,
        "--dialog-id", DIALOG,
        "--topic", TOPIC,
        "--keywords", "memory,three-layer",
        "--recent-limit", "5",
        "--summary-limit", "2",
        "--fact-limit", "5",
    ])

    print()
    print("=" * 60)
    print("Step 5: Compact - cleanup old chunks")
    print("=" * 60)

    run([
        "python3", f"{SCRIPTS}/compact_memory.py",
        "--db", DB,
        "--dialog-id", DIALOG,
        "--keep-recent", "3",
        "--delete-summarized",
    ])

    print()
    print("=" * 60)
    print("Step 6: Post-compact retrieval verification")
    print("=" * 60)

    run([
        "python3", f"{SCRIPTS}/retrieve_context.py",
        "--db", DB,
        "--dialog-id", DIALOG,
        "--topic", TOPIC,
        "--keywords", "memory",
        "--recent-limit", "5",
        "--summary-limit", "2",
        "--fact-limit", "5",
    ])

    print()
    print("=" * 60)
    print("Step 7: Final DB state")
    print("=" * 60)

    conn = sqlite3.connect(DB)
    for table in ["conversation_chunks", "topic_summaries", "long_term_facts"]:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {count} rows")
    conn.close()

    print()
    print("ALL STEPS PASSED - Three-layer memory pipeline verified.")


if __name__ == "__main__":
    main()
