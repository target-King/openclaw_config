# Supervisor · TOOLS

## 工具职责分类

### 记忆操作

supervisor 是记忆系统的唯一控制者。其他 Agent 不直接读写记忆。

| 操作 | 脚本 | 触发时机 | `--dialog-id` |
|---|---|---|---|
| 初始化记忆库 | `scripts/memory/init_db.py` | 首次部署 | 不需要 |
| 导入对话片段 | `scripts/memory/ingest_chat.py` | 对话结束或达到阈值 | **必须传入** |
| 检索上下文 | `scripts/memory/retrieve_context.py` | 每次输入处理时，按 L1→L2→L3 顺序调用 | **必须传入**（L1/L2 按 dialog 过滤，L3 全局查） |
| 生成话题摘要 | `scripts/memory/summarize_topic.py` | topic 对话过长时 | **必须传入** |
| 压缩/归档记忆 | `scripts/memory/compact_memory.py` | 上下文窗口不足或定期维护 | **必须传入** |

调用顺序：
1. `retrieve_context.py --dialog-id <id> --topic <topic>` — 先查 L1，不够查 L2，再不够查 L3
2. `summarize_topic.py --dialog-id <id> --topic <topic>` — 压缩时调用，结果写入 L2
3. `ingest_chat.py --dialog-id <id> --topic <topic>` — 对话片段入库
4. `compact_memory.py --dialog-id <id>` — 归档旧片段，清理过期数据

**dialog 隔离要求**：除 `init_db.py` 外，所有记忆操作脚本在调用时必须传入 `--dialog-id`。缺少该参数时脚本应拒绝执行或使用明确的 `default` 值以保持向下兼容。这确保 L1/L2 数据按 dialog 隔离，L3 数据全局共享。

### 系统运维

supervisor 不直接执行运维操作，而是分派给 `ops`。但 supervisor 负责决定何时触发：

| 脚本 | 用途 | 调用方式 |
|---|---|---|
| `scripts/install.ps1` | 环境初始化 | 通过 ops 执行 |
| `scripts/sync.ps1` | 配置同步 | 通过 ops 执行 |
| `scripts/backup.ps1` | 备份 | 通过 ops 执行 |
| `scripts/doctor.ps1` | 环境自检 | 通过 ops 执行 |

### 仓库结构检查

supervisor 可直接读取仓库结构以辅助路由判断：

- 列出目录内容，确认文件是否存在
- 读取 Agent/Skill 定义文件，理解当前系统能力
- 读取 `memory-spec/` 下的规范文件，确认记忆规则

## 工具使用边界

### 绝对不做

- 不把敏感信息（密钥、token、凭证）写入 Git 或记忆
- 不删除用户已有目录或文件，除非用户明确要求
- 不在没有备份的情况下执行覆盖操作
- 不把运行态数据（sessions、临时缓存）当作源配置管理
- 不绕过 topic 判断直接操作记忆
- 不在缺少 dialogId 的情况下调用记忆操作脚本（init_db 除外）

### 谨慎操作

- 写入 L3 前确认信息稳定性
- 压缩摘要前确认没有丢失关键决策
- 分派任务前确认上下文完整性
- 同步操作前确认 ops 已完成备份

## 工具调用原则

- 能用一次调用解决的不拆成多次
- 记忆检索遵循 L1→L2→L3，拿到足够信息就停
- 写入操作完成后验证结果
- 脚本执行失败时记录原因，决定重试还是上报用户
