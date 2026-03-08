# 记忆保留策略

## 目标
让记忆系统逐步积累有价值信息，而不是逐步堆满噪音。

## conversation_chunks
- 保留最近原始片段
- 已生成摘要后，可归档较旧片段
- 重要片段可延长保留时间

## topic_summaries
- 同一 topic 允许多次更新摘要
- 旧摘要不必立刻删除，可标记为被替代
- 优先保留最新、最完整的一版

## long_term_facts
- 仅保存稳定规则
- 写入要谨慎
- 一旦规则失效，应及时修订或失效标记

## 不应长期保留的内容
- 一次性猜测
- 已过期调试日志
- 临时试错指令
- 敏感密钥

## Dialog 过期策略

- L1 chunks：`dialog_id` 连续 7 天无新写入 → 自动过期候选
- L2 summaries：额外宽限 14 天（可配置），到期后才删除
- L3 facts：全局共享，不受 dialog 过期影响
- 默认 dry-run，需 `--execute` 确认后才真正删除
- 脚本：`scripts/memory/expire_dialogs.py`

## L2 版本裁剪策略

- 每个 `(dialog_id, topic)` 最多保留 3 个最新 summary version
- 生成新摘要时自动裁剪旧版本（同一事务内完成）
- 旧摘要被替代后无检索价值，自动清理减少数据库膨胀

## L3 容量管理

- 活跃 fact 超过 50 条时 `check_db.py` 打印 `[warn]` 告警
- 超过 100 条时打印 `[critical]` 并按 category 分组审计
- 建议定期审查 `confidence < 60` 的 fact
- 失效的 fact 应及时标记 `status='archived'`
