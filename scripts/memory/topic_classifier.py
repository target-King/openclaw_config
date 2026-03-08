"""Keyword-based topic auto-classifier.

Maps incoming content to one of the predefined topics defined in
``memory-spec/topic-splitting.md``.  The classifier is intentionally simple
(keyword matching) so it runs instantly without any external dependency.
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Predefined topics — keep in sync with memory-spec/topic-splitting.md
# ---------------------------------------------------------------------------
TOPIC_KEYWORDS: dict[str, list[str]] = {
    "openclaw-config": [
        "配置", "config", "openclaw", "managed-config", "目录结构", "仓库",
    ],
    "agent-design": [
        "agent", "agents", "supervisor", "coder", "reviewer", "ops",
        "scheduler", "project-analyst", "分派", "调度",
    ],
    "skill-design": [
        "skill", "skills", "技能", "SKILL.md",
    ],
    "three-layer-memory": [
        "记忆", "memory", "L1", "L2", "L3", "三层", "摘要", "summary",
        "conversation_chunks", "topic_summaries", "long_term_facts",
        "compact", "ingest", "retrieve", "压缩", "检索",
    ],
    "rag-system": [
        "RAG", "rag", "embedding", "向量", "检索增强", "hybrid search",
    ],
    "deployment-sync": [
        "部署", "deploy", "同步", "sync", "安装", "install", "路径",
        "backup", "备份", "rsync", "scp",
    ],
    "project-conventions": [
        "命名", "naming", "规范", "convention", "风格", "style", "目录风格",
    ],
}

DEFAULT_TOPIC = "general"


def classify(text: str) -> str:
    """Return the best-matching topic for *text*, or ``'general'``."""
    if not text:
        return DEFAULT_TOPIC

    text_lower = text.lower()
    scores: dict[str, int] = {}

    for topic, keywords in TOPIC_KEYWORDS.items():
        score = 0
        for kw in keywords:
            # Case-insensitive count of keyword occurrences
            count = len(re.findall(re.escape(kw.lower()), text_lower))
            score += count
        if score > 0:
            scores[topic] = score

    if not scores:
        return DEFAULT_TOPIC

    return max(scores, key=scores.get)  # type: ignore[arg-type]
