from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

# ---------------------------------------------------------------------------
# Tunable limits
# ---------------------------------------------------------------------------
MIN_IMPORTANCE_TOOL = 2        # role=tool 时的最低 importance 门槛（< 此值跳过写入）
AUTO_COMPACT_THRESHOLD = 5     # 超过此数量自动触发 summarize+compact（> 2 轮 = 4 条）
AUTO_COMPACT_KEEP = 4          # 压缩后保留最近 4 条（2 轮完整对话）

# ---------------------------------------------------------------------------
# Trivial / meaningless content patterns — these never enter the database
# ---------------------------------------------------------------------------
_TRIVIAL_PATTERNS: set[str] = {
    "ok", "okay", "好", "好的", "嗯", "收到", "明白", "是的", "对",
    "了解", "知道了", "行", "可以", "没问题", "继续", "下一步",
    "yes", "no", "sure", "got it", "thanks", "thank you", "谢谢",
}


def ensure_db_exists(db_path: Path) -> None:
    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}. Run init_db.py first.")


def _is_trivial(content: str) -> bool:
    """Return True if content is a trivial acknowledgment with no retrieval value."""
    normalized = content.strip().lower().rstrip("。.!！~")
    return normalized in _TRIVIAL_PATTERNS


def _should_skip(role: str, importance: int, content: str) -> tuple[bool, str]:
    """Return (should_skip, reason) tuple."""
    if _is_trivial(content):
        return True, "trivial content"
    if role == "tool" and importance < MIN_IMPORTANCE_TOOL:
        return True, f"low-importance {role} (importance={importance}, threshold={MIN_IMPORTANCE_TOOL})"
    return False, ""


def _auto_classify_topic(content: str) -> str:
    """Classify content into a topic using keyword matching."""
    from topic_classifier import classify
    return classify(content)


def _maybe_auto_compact(db_path: Path, dialog_id: str, topic: str) -> None:
    """If the chunk count for this dialog+topic exceeds the threshold,
    auto-trigger summarize + compact to keep only the latest 2 rounds."""
    from summarize_topic import summarize
    from compact_memory import compact

    with sqlite3.connect(db_path) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM conversation_chunks WHERE dialog_id = ? AND topic = ?",
            (dialog_id, topic),
        ).fetchone()[0]

    if count <= AUTO_COMPACT_THRESHOLD:
        return

    print(f"[auto-compact] {dialog_id}/{topic}: {count} chunks > {AUTO_COMPACT_THRESHOLD}, compressing...")
    summarize(db_path, dialog_id, topic, limit=count)
    compact(db_path, dialog_id, AUTO_COMPACT_KEEP, delete_summarized=True)


def ingest(
    db_path: Path,
    dialog_id: str,
    topic: str,
    role: str,
    content: str,
    source: str,
    importance: int,
    *,
    auto_topic: bool = False,
    auto_compact: bool = True,
) -> None:
    ensure_db_exists(db_path)

    # --- Skip meaningless content -------------------------------------------
    skip, reason = _should_skip(role, importance, content)
    if skip:
        print(f"[skip] {reason}, not ingested")
        return

    # --- Auto-classify topic if requested -----------------------------------
    if auto_topic and not topic:
        topic = _auto_classify_topic(content)
        print(f"[auto-topic] classified as: {topic}")

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO conversation_chunks(dialog_id, topic, role, content, source, importance)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (dialog_id, topic, role, content, source, importance),
        )
        conn.commit()
    print(f"[ok] inserted chunk (dialog={dialog_id}, topic={topic}, len={len(content)})")

    # --- Auto-compact after every write -------------------------------------
    if auto_compact:
        _maybe_auto_compact(db_path, dialog_id, topic)


def main() -> None:
    parser = argparse.ArgumentParser(description="Insert one conversation chunk into local memory DB.")
    parser.add_argument("--db", default="data/memory.db", help="Path to SQLite database.")
    parser.add_argument("--dialog-id", required=True, help="Dialog identifier for session isolation.")
    parser.add_argument("--topic", default="", help="Topic name. If empty and --auto-topic is set, auto-classify.")
    parser.add_argument("--role", required=True, choices=["user", "assistant", "system", "tool"], help="Role.")
    parser.add_argument("--content", required=True, help="Conversation text content.")
    parser.add_argument("--source", default="manual", help="Source label.")
    parser.add_argument("--importance", type=int, default=1, help="Importance score, suggested 1-5.")
    parser.add_argument("--auto-topic", action="store_true", help="Auto-classify topic from content when --topic is empty.")
    parser.add_argument("--no-auto-compact", action="store_true", help="Disable auto-compact after ingest.")
    args = parser.parse_args()

    if not args.topic and not args.auto_topic:
        parser.error("--topic is required unless --auto-topic is set")

    ingest(
        Path(args.db),
        args.dialog_id,
        args.topic,
        args.role,
        args.content,
        args.source,
        args.importance,
        auto_topic=args.auto_topic,
        auto_compact=not args.no_auto_compact,
    )


if __name__ == "__main__":
    main()
