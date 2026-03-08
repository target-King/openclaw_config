"""
冒烟测试：两个真实 dialog 并发工作

场景 1 — 非阻塞：dialog-A 长任务（大量写入 + 摘要），dialog-B 短任务（少量写读），B 不受 A 阻塞
场景 2 — 数据隔离：两个 dialog 并发读写同一 topic，L1/L2 数据不串
场景 3 — 汇报路由：模拟 progress dispatcher，A 的进度只到 A 的 mailbox，B 的结果只到 B

运行方式：
  cd scripts/memory && python smoke_concurrent_dialogs.py
"""

from __future__ import annotations

import sqlite3
import tempfile
import threading
import time
from pathlib import Path

from init_db import init_db
from ingest_chat import ingest
from retrieve_context import retrieve_recent_chunks, retrieve_summary
from summarize_topic import summarize


# ---------------------------------------------------------------------------
# 基础设施
# ---------------------------------------------------------------------------
class Result:
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


def make_db() -> Path:
    tmp = tempfile.mkdtemp()
    db_path = Path(tmp) / "smoke_test.db"
    init_db(db_path)
    return db_path


# ---------------------------------------------------------------------------
# 场景 1：非阻塞
#   dialog-A: 200 次写入 + 摘要（模拟长任务）
#   dialog-B: 3 次写入 + 1 次读取（模拟短任务）
#   验证：B 在 A 完成之前就已经结束，且 B 耗时远小于 A
# ---------------------------------------------------------------------------
def scenario_1_non_blocking(r: Result) -> None:
    print("\n--- 场景 1：非阻塞 ---")
    db = make_db()

    DIALOG_A = "smoke-long-a"
    DIALOG_B = "smoke-short-b"
    TOPIC = "agent-design"
    A_COUNT = 200

    timings: dict[str, float] = {}
    errors: dict[str, list[str]] = {"A": [], "B": []}

    def dialog_a() -> None:
        """长任务：大量写入 + 生成摘要"""
        t0 = time.monotonic()
        for i in range(A_COUNT):
            try:
                ingest(db, DIALOG_A, TOPIC, "user", f"A-msg-{i}: 这是一段较长的对话内容用于模拟真实场景", "test", 2)
            except Exception as e:
                errors["A"].append(str(e))
                return
        # 生成摘要
        try:
            summarize(db, DIALOG_A, TOPIC, 50)
        except Exception as e:
            errors["A"].append(f"summarize: {e}")
        timings["A_end"] = time.monotonic()
        timings["A_duration"] = timings["A_end"] - t0

    def dialog_b() -> None:
        """短任务：少量写入 + 读取"""
        t0 = time.monotonic()
        try:
            for i in range(3):
                ingest(db, DIALOG_B, TOPIC, "user", f"B-quick-{i}", "test", 1)
            with sqlite3.connect(str(db)) as conn:
                retrieve_recent_chunks(conn, DIALOG_B, TOPIC, 10)
        except Exception as e:
            errors["B"].append(str(e))
        timings["B_end"] = time.monotonic()
        timings["B_duration"] = timings["B_end"] - t0

    ta = threading.Thread(target=dialog_a)
    tb = threading.Thread(target=dialog_b)

    ta.start()
    time.sleep(0.005)  # 让 A 先跑起来
    tb.start()

    ta.join(timeout=30)
    tb.join(timeout=10)

    # 检查无错误
    if errors["A"]:
        r.fail("S1.1 dialog-A 执行无错", "; ".join(errors["A"]))
    else:
        r.ok("S1.1 dialog-A 执行无错")

    if errors["B"]:
        r.fail("S1.2 dialog-B 执行无错", "; ".join(errors["B"]))
    else:
        r.ok("S1.2 dialog-B 执行无错")

    # B 应该比 A 快得多
    a_dur = timings.get("A_duration", 999)
    b_dur = timings.get("B_duration", 999)
    if b_dur < a_dur:
        r.ok(f"S1.3 B({b_dur:.3f}s) 先于 A({a_dur:.3f}s) 完成 — 未被阻塞")
    else:
        r.fail("S1.3 B 先于 A 完成", f"B={b_dur:.3f}s, A={a_dur:.3f}s")

    # B 的绝对耗时应该很短（< 2s）
    if b_dur < 2.0:
        r.ok(f"S1.4 B 绝对耗时合理 ({b_dur:.3f}s < 2s)")
    else:
        r.fail("S1.4 B 绝对耗时合理", f"B 耗时 {b_dur:.3f}s，超过 2s 阈值")


# ---------------------------------------------------------------------------
# 场景 2：数据隔离
#   两个 dialog 并发地向同一 topic 写入 + 生成摘要
#   然后各自读取，验证 L1/L2 数据不串
# ---------------------------------------------------------------------------
def scenario_2_data_isolation(r: Result) -> None:
    print("\n--- 场景 2：L1/L2 数据隔离 ---")
    db = make_db()

    DIALOG_A = "iso-alpha"
    DIALOG_B = "iso-beta"
    TOPIC = "three-layer-memory"
    A_COUNT = 30
    B_COUNT = 20
    A_PREFIX = "ALPHA_MARKER_"
    B_PREFIX = "BETA_MARKER_"

    barrier = threading.Barrier(2)  # 让两个线程同时开始
    errors: dict[str, list[str]] = {"A": [], "B": []}

    def writer_a() -> None:
        barrier.wait()
        try:
            for i in range(A_COUNT):
                ingest(db, DIALOG_A, TOPIC, "user", f"{A_PREFIX}{i}", "test", 2)
            summarize(db, DIALOG_A, TOPIC, 50)
        except Exception as e:
            errors["A"].append(str(e))

    def writer_b() -> None:
        barrier.wait()
        try:
            for i in range(B_COUNT):
                ingest(db, DIALOG_B, TOPIC, "user", f"{B_PREFIX}{i}", "test", 1)
            summarize(db, DIALOG_B, TOPIC, 50)
        except Exception as e:
            errors["B"].append(str(e))

    ta = threading.Thread(target=writer_a)
    tb = threading.Thread(target=writer_b)
    ta.start()
    tb.start()
    ta.join(timeout=30)
    tb.join(timeout=30)

    if errors["A"] or errors["B"]:
        r.fail("S2.1 并发写入无错", f"A={errors['A']}, B={errors['B']}")
    else:
        r.ok("S2.1 并发写入无错")

    # L1 隔离验证
    with sqlite3.connect(str(db)) as conn:
        a_l1 = retrieve_recent_chunks(conn, DIALOG_A, TOPIC, 100)
        b_l1 = retrieve_recent_chunks(conn, DIALOG_B, TOPIC, 100)

        # A 应该有 A_COUNT 条，内容全带 ALPHA_MARKER_
        a_contents = [row[2] for row in a_l1]
        b_contents = [row[2] for row in b_l1]

        a_count_ok = len(a_l1) == A_COUNT
        b_count_ok = len(b_l1) == B_COUNT
        if a_count_ok and b_count_ok:
            r.ok(f"S2.2 L1 条数正确 (A={len(a_l1)}, B={len(b_l1)})")
        else:
            r.fail("S2.2 L1 条数正确", f"A={len(a_l1)}(期望{A_COUNT}), B={len(b_l1)}(期望{B_COUNT})")

        # A 的 L1 不包含 BETA_MARKER_
        a_has_beta = any(B_PREFIX in c for c in a_contents)
        if not a_has_beta:
            r.ok("S2.3 A 的 L1 不含 B 的数据")
        else:
            r.fail("S2.3 A 的 L1 不含 B 的数据", "发现 BETA_MARKER_ 泄露到 A")

        # B 的 L1 不包含 ALPHA_MARKER_
        b_has_alpha = any(A_PREFIX in c for c in b_contents)
        if not b_has_alpha:
            r.ok("S2.4 B 的 L1 不含 A 的数据")
        else:
            r.fail("S2.4 B 的 L1 不含 A 的数据", "发现 ALPHA_MARKER_ 泄露到 B")

    # L2 隔离验证
    with sqlite3.connect(str(db)) as conn:
        a_l2 = retrieve_summary(conn, DIALOG_A, TOPIC, 10)
        b_l2 = retrieve_summary(conn, DIALOG_B, TOPIC, 10)

        if len(a_l2) >= 1 and len(b_l2) >= 1:
            r.ok(f"S2.5 L2 各自生成摘要 (A={len(a_l2)}, B={len(b_l2)})")
        else:
            r.fail("S2.5 L2 各自生成摘要", f"A={len(a_l2)}, B={len(b_l2)}")

        # A 的摘要内容应含 ALPHA 不含 BETA
        a_summary_text = " ".join(row[2] for row in a_l2)
        b_summary_text = " ".join(row[2] for row in b_l2)

        if A_PREFIX in a_summary_text and B_PREFIX not in a_summary_text:
            r.ok("S2.6 A 的 L2 摘要只含 A 的数据")
        else:
            r.fail("S2.6 A 的 L2 摘要只含 A 的数据",
                   f"含ALPHA={A_PREFIX in a_summary_text}, 含BETA={B_PREFIX in a_summary_text}")

        if B_PREFIX in b_summary_text and A_PREFIX not in b_summary_text:
            r.ok("S2.7 B 的 L2 摘要只含 B 的数据")
        else:
            r.fail("S2.7 B 的 L2 摘要只含 B 的数据",
                   f"含BETA={B_PREFIX in b_summary_text}, 含ALPHA={A_PREFIX in b_summary_text}")


# ---------------------------------------------------------------------------
# 场景 3：汇报路由
#   模拟一个 progress dispatcher：
#   - A 和 B 各自产出进度消息
#   - dispatcher 按 dialogId 投递到对应 mailbox
#   - 验证 A 的 mailbox 里没有 B 的消息，反之亦然
# ---------------------------------------------------------------------------
class ProgressDispatcher:
    """模拟 supervisor 的进度汇报路由器"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._mailboxes: dict[str, list[dict]] = {}

    def report(self, dialog_id: str, step: str, status: str) -> None:
        """投递进度消息，按 dialogId 路由"""
        msg = {"dialog_id": dialog_id, "step": step, "status": status, "ts": time.monotonic()}
        with self._lock:
            if dialog_id not in self._mailboxes:
                self._mailboxes[dialog_id] = []
            self._mailboxes[dialog_id].append(msg)

    def get_mailbox(self, dialog_id: str) -> list[dict]:
        with self._lock:
            return list(self._mailboxes.get(dialog_id, []))


def scenario_3_report_routing(r: Result) -> None:
    print("\n--- 场景 3：汇报路由隔离 ---")

    DIALOG_A = "report-alpha"
    DIALOG_B = "report-beta"

    dispatcher = ProgressDispatcher()
    barrier = threading.Barrier(2)

    def task_a() -> None:
        """模拟 dialog-A 的长任务，产出多次进度汇报"""
        barrier.wait()
        steps = ["拆分任务", "派发 coder", "等待 coder 返回", "整合结果", "完成"]
        for s in steps:
            dispatcher.report(DIALOG_A, s, "in_progress" if s != "完成" else "done")
            time.sleep(0.01)

    def task_b() -> None:
        """模拟 dialog-B 的短任务，只有开始和结束"""
        barrier.wait()
        dispatcher.report(DIALOG_B, "直接回答", "in_progress")
        time.sleep(0.005)
        dispatcher.report(DIALOG_B, "完成", "done")

    ta = threading.Thread(target=task_a)
    tb = threading.Thread(target=task_b)
    ta.start()
    tb.start()
    ta.join(timeout=10)
    tb.join(timeout=10)

    mb_a = dispatcher.get_mailbox(DIALOG_A)
    mb_b = dispatcher.get_mailbox(DIALOG_B)

    # A 应该有 5 条
    if len(mb_a) == 5:
        r.ok(f"S3.1 A 的 mailbox 收到 5 条汇报")
    else:
        r.fail("S3.1 A 的 mailbox 收到 5 条汇报", f"实际 {len(mb_a)} 条")

    # B 应该有 2 条
    if len(mb_b) == 2:
        r.ok(f"S3.2 B 的 mailbox 收到 2 条汇报")
    else:
        r.fail("S3.2 B 的 mailbox 收到 2 条汇报", f"实际 {len(mb_b)} 条")

    # A 的 mailbox 里所有 dialog_id 都是 A
    a_ids = {m["dialog_id"] for m in mb_a}
    if a_ids == {DIALOG_A}:
        r.ok("S3.3 A 的 mailbox 不含 B 的消息")
    else:
        r.fail("S3.3 A 的 mailbox 不含 B 的消息", f"dialog_ids: {a_ids}")

    # B 的 mailbox 里所有 dialog_id 都是 B
    b_ids = {m["dialog_id"] for m in mb_b}
    if b_ids == {DIALOG_B}:
        r.ok("S3.4 B 的 mailbox 不含 A 的消息")
    else:
        r.fail("S3.4 B 的 mailbox 不含 A 的消息", f"dialog_ids: {b_ids}")

    # A 最后一条是"完成"
    if mb_a and mb_a[-1]["step"] == "完成" and mb_a[-1]["status"] == "done":
        r.ok("S3.5 A 的最后汇报标记为完成")
    else:
        r.fail("S3.5 A 的最后汇报标记为完成", f"最后一条: {mb_a[-1] if mb_a else 'empty'}")

    # B 最后一条是"完成"
    if mb_b and mb_b[-1]["step"] == "完成" and mb_b[-1]["status"] == "done":
        r.ok("S3.6 B 的最后汇报标记为完成")
    else:
        r.fail("S3.6 B 的最后汇报标记为完成", f"最后一条: {mb_b[-1] if mb_b else 'empty'}")


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------
def main() -> None:
    print("=" * 60)
    print("冒烟测试：两个真实 dialog 并发工作")
    print("=" * 60)

    r = Result()

    scenario_1_non_blocking(r)
    scenario_2_data_isolation(r)
    scenario_3_report_routing(r)

    r.summary()

    if r.failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
