"""
Dialog 隔离行为验收测试

验证项：
  V1 - 不同 dialog 拥有独立上下文（L1/L2 隔离）
  V2 - 同一 dialog 内串行写入数据一致
  V3 - 不同 dialog 允许并行操作
  V4 - (规范审查，非自动化) 进度汇报绑定正确 dialog
  V5 - (规范审查，非自动化) 子 Agent 调用链 dialog 隔离
  V6 - L3 长期事实全局共享

运行方式：
  python scripts/memory/test_dialog_isolation.py
"""

from __future__ import annotations

import sqlite3
import tempfile
import threading
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# 复用项目中的现有脚本逻辑
# ---------------------------------------------------------------------------
from init_db import init_db
from ingest_chat import ingest
from retrieve_context import retrieve_recent_chunks, retrieve_summary, retrieve_facts
from summarize_topic import summarize


class Result:
    """简易测试结果收集器"""

    def __init__(self) -> None:
        self.passed: list[str] = []
        self.failed: list[str] = []

    def ok(self, name: str) -> None:
        self.passed.append(name)
        print(f"  [PASS] {name}")

    def fail(self, name: str, reason: str) -> None:
        self.failed.append(f"{name}: {reason}")
        print(f"  [FAIL] {name} — {reason}")

    def summary(self) -> None:
        total = len(self.passed) + len(self.failed)
        print(f"\n{'='*60}")
        print(f"结果：{len(self.passed)}/{total} 通过")
        if self.failed:
            print("失败项：")
            for f in self.failed:
                print(f"  - {f}")
        else:
            print("全部通过。")
        print(f"{'='*60}")


def make_test_db() -> Path:
    """创建临时测试数据库"""
    tmp = tempfile.mkdtemp()
    db_path = Path(tmp) / "test_memory.db"
    init_db(db_path)
    return db_path


def insert_fact(db_path: Path, category: str, key: str, value: str) -> None:
    """直接向 L3 写入一条 fact（L3 无 dialog_id）"""
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO long_term_facts(category, key, value) VALUES (?, ?, ?)",
            (category, key, value),
        )
        conn.commit()


# ===========================================================================
# V1: 不同 dialog 拥有独立上下文
# ===========================================================================
def test_v1_dialog_context_isolation(r: Result) -> None:
    print("\n--- V1: 不同 dialog 独立上下文 ---")
    db = make_test_db()

    DIALOG_A = "dialog-a-001"
    DIALOG_B = "dialog-b-002"
    TOPIC = "agent-design"

    # dialog-A 写入 L1
    ingest(db, DIALOG_A, TOPIC, "user", "dialog-A 的秘密内容", "test", 3)
    ingest(db, DIALOG_A, TOPIC, "assistant", "dialog-A 的回复", "test", 2)

    # dialog-A 生成 L2 摘要
    summarize(db, DIALOG_A, TOPIC, 10)

    with sqlite3.connect(str(db)) as conn:
        # dialog-B 查询 L1 → 期望为空
        l1_b = retrieve_recent_chunks(conn, DIALOG_B, TOPIC, 10)
        if len(l1_b) == 0:
            r.ok("V1.1 dialog-B 读不到 dialog-A 的 L1")
        else:
            r.fail("V1.1 dialog-B 读不到 dialog-A 的 L1", f"返回了 {len(l1_b)} 条记录")

        # dialog-B 查询 L2 → 期望为空
        l2_b = retrieve_summary(conn, DIALOG_B, TOPIC, 10)
        if len(l2_b) == 0:
            r.ok("V1.2 dialog-B 读不到 dialog-A 的 L2")
        else:
            r.fail("V1.2 dialog-B 读不到 dialog-A 的 L2", f"返回了 {len(l2_b)} 条记录")

        # dialog-A 查自己 → 期望有数据
        l1_a = retrieve_recent_chunks(conn, DIALOG_A, TOPIC, 10)
        if len(l1_a) == 2:
            r.ok("V1.3 dialog-A 能读到自己的 L1 (2条)")
        else:
            r.fail("V1.3 dialog-A 能读到自己的 L1", f"期望 2 条，实际 {len(l1_a)} 条")

        l2_a = retrieve_summary(conn, DIALOG_A, TOPIC, 10)
        if len(l2_a) >= 1:
            r.ok("V1.4 dialog-A 能读到自己的 L2 摘要")
        else:
            r.fail("V1.4 dialog-A 能读到自己的 L2 摘要", "L2 为空")

    # dialog-B 也写入相同 topic 的内容
    ingest(db, DIALOG_B, TOPIC, "user", "dialog-B 的独立内容", "test", 1)

    with sqlite3.connect(str(db)) as conn:
        # 再次验证 A 看不到 B
        l1_a2 = retrieve_recent_chunks(conn, DIALOG_A, TOPIC, 10)
        if len(l1_a2) == 2:
            r.ok("V1.5 dialog-A 不受 dialog-B 写入影响 (仍为2条)")
        else:
            r.fail("V1.5 dialog-A 不受 dialog-B 写入影响", f"期望 2 条，实际 {len(l1_a2)} 条")

        # B 查自己
        l1_b2 = retrieve_recent_chunks(conn, DIALOG_B, TOPIC, 10)
        if len(l1_b2) == 1:
            r.ok("V1.6 dialog-B 只能读到自己的 1 条 L1")
        else:
            r.fail("V1.6 dialog-B 只能读到自己的 L1", f"期望 1 条，实际 {len(l1_b2)} 条")


# ===========================================================================
# V2: 同一 dialog 内串行写入一致性
# ===========================================================================
def test_v2_same_dialog_serial_consistency(r: Result) -> None:
    print("\n--- V2: 同一 dialog 内串行写入一致性 ---")
    db = make_test_db()

    DIALOG = "dialog-serial-001"
    TOPIC = "three-layer-memory"
    TOTAL = 10

    # 用线程并发向同一 dialog 写入
    errors: list[str] = []

    def writer(idx: int) -> None:
        try:
            ingest(db, DIALOG, TOPIC, "user", f"消息-{idx}", "test", 1)
        except Exception as e:
            errors.append(f"线程 {idx}: {e}")

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(TOTAL)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    if errors:
        r.fail("V2.1 并发写入无报错", "; ".join(errors))
    else:
        r.ok("V2.1 并发写入无报错")

    with sqlite3.connect(str(db)) as conn:
        rows = retrieve_recent_chunks(conn, DIALOG, TOPIC, 100)
        if len(rows) == TOTAL:
            r.ok(f"V2.2 写入 {TOTAL} 条全部到账")
        else:
            r.fail(f"V2.2 写入 {TOTAL} 条全部到账", f"实际 {len(rows)} 条")

        # 检查内容无重复
        contents = [row[2] for row in rows]
        unique = set(contents)
        if len(unique) == TOTAL:
            r.ok("V2.3 无重复内容")
        else:
            r.fail("V2.3 无重复内容", f"去重后 {len(unique)} 条")


# ===========================================================================
# V3: 不同 dialog 允许并行
# ===========================================================================
def test_v3_cross_dialog_parallelism(r: Result) -> None:
    print("\n--- V3: 不同 dialog 允许并行 ---")
    db = make_test_db()

    DIALOG_A = "dialog-slow-a"
    DIALOG_B = "dialog-fast-b"
    TOPIC = "rag-system"
    SLOW_COUNT = 50

    b_start = 0.0
    b_end = 0.0
    a_errors: list[str] = []
    b_errors: list[str] = []

    def slow_dialog_a() -> None:
        """模拟 dialog-A 执行大量写入（慢任务）"""
        for i in range(SLOW_COUNT):
            try:
                ingest(db, DIALOG_A, TOPIC, "user", f"A-heavy-{i}", "test", 1)
            except Exception as e:
                a_errors.append(str(e))

    def fast_dialog_b() -> None:
        """dialog-B 做少量读写"""
        nonlocal b_start, b_end
        b_start = time.monotonic()
        try:
            ingest(db, DIALOG_B, TOPIC, "user", "B-quick-msg", "test", 1)
            with sqlite3.connect(str(db)) as conn:
                retrieve_recent_chunks(conn, DIALOG_B, TOPIC, 5)
        except Exception as e:
            b_errors.append(str(e))
        b_end = time.monotonic()

    ta = threading.Thread(target=slow_dialog_a)
    tb = threading.Thread(target=fast_dialog_b)

    ta.start()
    # 稍微延迟让 A 先开始
    time.sleep(0.01)
    tb.start()

    ta.join()
    tb.join()

    if a_errors:
        r.fail("V3.1 dialog-A 慢任务无报错", "; ".join(a_errors))
    else:
        r.ok("V3.1 dialog-A 慢任务无报错")

    if b_errors:
        r.fail("V3.2 dialog-B 快任务无报错", "; ".join(b_errors))
    else:
        r.ok("V3.2 dialog-B 快任务无报错")

    b_duration = b_end - b_start
    # B 的操作应该在 2 秒内完成（正常情况远小于此）
    if b_duration < 2.0:
        r.ok(f"V3.3 dialog-B 未被 A 阻塞 (耗时 {b_duration:.3f}s)")
    else:
        r.fail(f"V3.3 dialog-B 未被 A 阻塞", f"B 耗时 {b_duration:.3f}s，疑似被阻塞")

    # 验证两个 dialog 的数据互不干扰
    with sqlite3.connect(str(db)) as conn:
        a_rows = retrieve_recent_chunks(conn, DIALOG_A, TOPIC, 100)
        b_rows = retrieve_recent_chunks(conn, DIALOG_B, TOPIC, 100)

        if len(a_rows) == SLOW_COUNT and len(b_rows) == 1:
            r.ok(f"V3.4 数据隔离正确 (A={len(a_rows)}, B={len(b_rows)})")
        else:
            r.fail("V3.4 数据隔离", f"A={len(a_rows)} (期望{SLOW_COUNT}), B={len(b_rows)} (期望1)")


# ===========================================================================
# V4 + V5: 规范审查（静态分析）
# ===========================================================================
def test_v4_v5_spec_review(r: Result) -> None:
    print("\n--- V4+V5: 规范文档审查 ---")

    spec_dir = Path(__file__).resolve().parent.parent.parent
    checks = {
        "V4.1 进度汇报格式包含 dialogId": (
            spec_dir / "agents" / "supervisor" / "AGENTS.md",
            "dialog:",
        ),
        "V4.2 汇报只路由到发起对话框": (
            spec_dir / "agents" / "supervisor" / "AGENTS.md",
            "只路由到发起该任务的对话框",
        ),
        "V5.1 分派模板携带 dialogId": (
            spec_dir / "agents" / "supervisor" / "AGENTS.md",
            "dialogId: <当前 dialog 的 ID>",
        ),
        "V5.2 子 Agent 返回携带 dialogId": (
            spec_dir / "agents" / "supervisor" / "AGENTS.md",
            "结果中同样必须携带",
        ),
        "V5.3 思考链第 0 步确认 dialogId": (
            spec_dir / "agents" / "supervisor" / "SOUL.md",
            "确认 dialogId",
        ),
        "V5.4 缺少 dialogId 拒绝继续": (
            spec_dir / "agents" / "supervisor" / "SOUL.md",
            "缺少 dialogId 时拒绝继续",
        ),
        "V5.5 不跨 dialog 检索 L1/L2": (
            spec_dir / "agents" / "supervisor" / "SOUL.md",
            "不跨 dialog 检索",
        ),
    }

    for name, (path, keyword) in checks.items():
        if not path.exists():
            r.fail(name, f"文件不存在: {path}")
            continue
        content = path.read_text(encoding="utf-8")
        if keyword in content:
            r.ok(name)
        else:
            r.fail(name, f"未找到关键规范: '{keyword}'")


# ===========================================================================
# V6: L3 全局共享
# ===========================================================================
def test_v6_l3_global_sharing(r: Result) -> None:
    print("\n--- V6: L3 全局共享 ---")
    db = make_test_db()

    DIALOG_A = "dialog-l3-a"
    DIALOG_B = "dialog-l3-b"

    # 写入 L3 fact（无 dialog_id 参与）
    insert_fact(db, "project-conventions", "naming-style", "kebab-case")

    with sqlite3.connect(str(db)) as conn:
        # 验证 long_term_facts 表无 dialog_id 列
        cols = [row[1] for row in conn.execute("PRAGMA table_info(long_term_facts)").fetchall()]
        if "dialog_id" not in cols:
            r.ok("V6.1 long_term_facts 表无 dialog_id 列")
        else:
            r.fail("V6.1 long_term_facts 表无 dialog_id 列", f"列: {cols}")

        # dialog-A 查 L3
        facts_a = retrieve_facts(conn, "naming", 10)
        if len(facts_a) >= 1:
            r.ok("V6.2 dialog-A 可读到 L3 全局 fact")
        else:
            r.fail("V6.2 dialog-A 可读到 L3 全局 fact", "查询为空")

        # dialog-B 查 L3 (用不同关键词也能查到)
        facts_b = retrieve_facts(conn, "kebab", 10)
        if len(facts_b) >= 1:
            r.ok("V6.3 dialog-B 可读到同一条 L3 fact")
        else:
            r.fail("V6.3 dialog-B 可读到同一条 L3 fact", "查询为空")

    # 验证 L1/L2 表确实有 dialog_id 列
    with sqlite3.connect(str(db)) as conn:
        chunk_cols = [row[1] for row in conn.execute("PRAGMA table_info(conversation_chunks)").fetchall()]
        summary_cols = [row[1] for row in conn.execute("PRAGMA table_info(topic_summaries)").fetchall()]

        if "dialog_id" in chunk_cols:
            r.ok("V6.4 conversation_chunks 表包含 dialog_id 列")
        else:
            r.fail("V6.4 conversation_chunks 包含 dialog_id", f"列: {chunk_cols}")

        if "dialog_id" in summary_cols:
            r.ok("V6.5 topic_summaries 表包含 dialog_id 列")
        else:
            r.fail("V6.5 topic_summaries 包含 dialog_id", f"列: {summary_cols}")


# ===========================================================================
# 补充: 检测 --dialog-id 默认值风险
# ===========================================================================
def test_extra_default_dialogid_risk(r: Result) -> None:
    print("\n--- 补充: --dialog-id 默认值风险检测 ---")

    spec_dir = Path(__file__).resolve().parent.parent.parent
    scripts_to_check = [
        ("retrieve_context.py", spec_dir / "scripts" / "memory" / "retrieve_context.py"),
        ("ingest_chat.py", spec_dir / "scripts" / "memory" / "ingest_chat.py"),
        ("summarize_topic.py", spec_dir / "scripts" / "memory" / "summarize_topic.py"),
        ("compact_memory.py", spec_dir / "scripts" / "memory" / "compact_memory.py"),
    ]

    for name, path in scripts_to_check:
        if not path.exists():
            r.fail(f"X.{name} 存在", "文件不存在")
            continue
        content = path.read_text(encoding="utf-8")
        # 逐行检测 --dialog-id 的定义方式
        dialog_id_line = ""
        for line in content.splitlines():
            if "--dialog-id" in line:
                dialog_id_line = line.strip()
                break

        if not dialog_id_line:
            r.fail(f"X.{name} --dialog-id 参数存在", "未找到 --dialog-id 参数定义")
        elif "required=True" in dialog_id_line:
            r.ok(f"X.{name} --dialog-id 为 required")
        elif 'default="default"' in dialog_id_line or "default='default'" in dialog_id_line:
            r.fail(
                f"X.{name} --dialog-id 无静默默认值",
                '当前默认值为 "default"，规范要求缺失时应拒绝执行',
            )
        elif 'default=""' in dialog_id_line or "default=''" in dialog_id_line:
            # compact_memory 允许空值（表示操作所有 dialog），需要人工确认
            if "compact" in name:
                r.ok(f"X.{name} --dialog-id 默认空串 (compact 全量操作，可接受)")
            else:
                r.fail(
                    f"X.{name} --dialog-id 无静默默认值",
                    '当前默认值为空字符串，规范要求缺失时应拒绝执行',
                )
        else:
            r.ok(f"X.{name} --dialog-id 处理方式待人工确认")


# ===========================================================================
# 入口
# ===========================================================================
def main() -> None:
    print("=" * 60)
    print("Dialog 隔离行为验收测试")
    print("=" * 60)

    r = Result()

    test_v1_dialog_context_isolation(r)
    test_v2_same_dialog_serial_consistency(r)
    test_v3_cross_dialog_parallelism(r)
    test_v4_v5_spec_review(r)
    test_v6_l3_global_sharing(r)
    test_extra_default_dialogid_risk(r)

    r.summary()

    # 返回非零退出码表示有失败
    if r.failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
