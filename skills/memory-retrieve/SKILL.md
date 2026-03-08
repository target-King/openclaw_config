# memory-retrieve

## 目的
根据当前问题，从三层记忆里取出最相关的上下文，而不是把整段历史全部塞回上下文。

## 适用场景
- 需要回忆某个主题此前讨论过什么
- 当前问题依赖历史规则、路径、偏好
- 对话过长，不能直接携带全部历史

## 核心流程

```
消息进入
  │
  ▼ 内容有意义？ ──否──> 丢弃（不入库）
  │是
  ▼ 自动分类 topic（关键词匹配）
  │
  ▼ 写入 L1（dialog_id + topic）
  │
  ▼ 该 topic chunk 数 > 5？ ──否──> 结束
  │是
  ▼ 自动 summarize（生成/更新 L2 摘要）
  │
  ▼ 自动 compact（只保留最近 4 条 = 2 轮对话）
```

## 默认检索顺序（短路策略）
1. 自动分类 topic（从 query 内容推断，或手动指定）
2. 仅检索该 topic 下的数据：
   - L1：最近 4 条（2 轮完整对话）
   - L2：话题摘要（若 L2 存在，L1 缩减至 1 条）
   - L3：长期事实（仅在 L1+L2 不足或有明确关键词时查询）

## 输入
- 当前问题（query）
- dialogId（**必须**，用于 L1/L2 的 dialog 隔离过滤）
- topic（可选，为空时自动从 query 分类）
- 关键词（可选）

## 输出
- 完整的上下文片段（不截断，保证信息完整性）
- 话题摘要
- 长期事实候选
- 命中的来源层级
- context 总字符数（超过 3000 字符时告警）

## 执行原则
- 能从 L1 解决，就不继续下探
- L2 摘要已存在时，L1 仅保留最新 1 条
- L3 仅在 L1+L2 不足或有明确关键词时检索
- 返回摘要，不返回整库
- 不返回敏感信息
- L1/L2 检索时按 dialogId + topic 过滤，不跨 dialog 或跨 topic 取数据
- L3 检索不过滤 dialogId，全局共享
- 切换角色模式时，通过读取 `roles/<role>.md` 加载该角色详细行为规范

## 默认参数
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--recent-limit` (L1) | 4 | 2 轮完整对话；有摘要时自动降为 1 |
| `--summary-limit` (L2) | 1 | 通常最新一版摘要足够 |
| `--fact-limit` (L3) | 3 | 只取最相关的事实 |

## Topic 自动分类（topic_classifier）
- 基于关键词匹配，将内容路由到预定义的 topic
- 预定义 topic 见 `memory-spec/topic-splitting.md`
- 无法匹配时归入 `general`
- ingest 和 retrieve 均支持 `--auto-topic`

## 写入侧控制（ingest_chat）
- 无意义内容直接丢弃（"好的"、"收到"、"ok" 等短确认语）
- `role=tool` 且 `importance < 2` 的输出不写入 L1
- 不截断内容，保证信息完整性
- 写入后自动检查是否需要压缩

## 实时压缩（每次写入后自动触发）
- 同一 dialog+topic 下 chunk 超过 5 条（> 2 轮）时自动触发
- 先 summarize（生成 L2 摘要），再 compact（删除旧 chunk）
- compact 后只保留最近 4 条（2 轮完整对话）
- 生成摘要时自动裁剪旧版本，每个 dialog+topic 最多保留 3 个 summary version
- 无需手动干预，写入即压缩

## 摘要生成（summarize_topic）
- 从该 topic 全部 chunk 生成摘要
- 过滤 role=tool 的输出，优先保留 assistant 结论
- 近似去重，每条摘要行上限 200 字符
- 总行数上限 15 行

## 监控（check_db）
- 按 dialog+topic 分组统计 chunk 数量和总字符数
- 超过 10 条的分组标记 [!] 告警
- 全局 L1 总字符数超过 50000 时告警
- L2 摘要版本堆积超过 5 个时告警
- L3 活跃 fact 超过 50 条时 [warn]，超过 100 条时 [critical] 并按 category 审计
- 检测超过 7 天无活跃的 stale dialog，提示运行过期清理

## 配套脚本
- `scripts/memory/topic_classifier.py` — topic 自动分类器
- `scripts/memory/ingest_chat.py --dialog-id <id> --auto-topic --content <text>` — 写入（自动分类+自动压缩）
- `scripts/memory/retrieve_context.py --dialog-id <id> --query <text>` — 检索（自动分类 topic）
- `scripts/memory/compact_memory.py --auto --dialog-id <id>` — 手动批量压缩
- `scripts/memory/expire_dialogs.py --dry-run` — 扫描过期 dialog（仅报告）
- `scripts/memory/expire_dialogs.py --execute` — 执行过期清理（真正删除）
- `scripts/memory/check_db.py --db <path>` — 监控

## 未来增强
- embedding 检索
- 混合检索
- 多 topic 聚合
