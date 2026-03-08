# Scheduler · TOOLS

## 工具使用重点

专注 `openclaw cron` 命令族。所有定时任务操作通过 CLI 完成。

## 完整命令参考

### `openclaw cron add` — 创建 job

| 参数 | 说明 | 示例 |
|---|---|---|
| `--name` | job 名称（必须） | `--name "Morning brief"` |
| `--at` | 一次性时间（ISO8601 或人类可读时长） | `--at "20m"` / `--at "2026-03-09T08:00:00+08:00"` |
| `--every` | 固定间隔（毫秒） | `--every 1800000`（30 分钟） |
| `--cron` | cron 表达式（5 段或 6 段含秒） | `--cron "0 7 * * *"` |
| `--tz` | 时区（IANA 格式，配合 `--cron` 使用） | `--tz "Asia/Shanghai"` |
| `--session` | 执行模式 | `main` / `isolated` |
| `--system-event` | main session 的事件文本 | `--system-event "提醒：检查邮件"` |
| `--message` | isolated session 的提示文本 | `--message "生成今日简报"` |
| `--wake` | main session 唤醒模式 | `now` / `next-heartbeat` |
| `--announce` | 启用渠道投递（isolated 默认启用） | |
| `--no-deliver` | 禁用投递 | |
| `--channel` | 投递渠道 | `telegram` / `whatsapp` / `slack` / `discord` / `feishu` / `last` |
| `--to` | 投递目标 | 渠道特定的 chat_id / channel_id |
| `--agent` | 绑定执行 agent | `--agent ops` |
| `--model` | 覆盖模型 | `--model opus` |
| `--thinking` | 覆盖思考深度 | `off` / `minimal` / `low` / `medium` / `high` / `xhigh` |
| `--stagger` | 允许执行偏移窗口 | `--stagger 30s` |
| `--exact` | 精确执行，不偏移 | |
| `--delete-after-run` | 一次性 job 执行后自动删除（`--at` 默认启用） | |
| `--keep-after-run` | 一次性 job 执行后保留（不删除） | |

#### 创建示例

一次性提醒（main session）：

```bash
openclaw cron add \
  --name "Meeting reminder" \
  --at "20m" \
  --session main \
  --system-event "提醒：20 分钟后有会议" \
  --wake now \
  --delete-after-run
```

每日早报（isolated，投递到飞书）：

```bash
openclaw cron add \
  --name "Morning brief" \
  --cron "0 7 * * *" \
  --tz "Asia/Shanghai" \
  --session isolated \
  --message "生成今日简报：天气、日历、邮件摘要" \
  --announce \
  --channel feishu \
  --to "<chat_id>"
```

每周深度分析（isolated，指定模型）：

```bash
openclaw cron add \
  --name "Weekly review" \
  --cron "0 9 * * 1" \
  --tz "Asia/Shanghai" \
  --session isolated \
  --message "本周项目进展深度分析" \
  --model opus \
  --thinking high \
  --announce
```

### `openclaw cron edit <jobId>` — 编辑 job

支持 add 的参数子集，按需 patch：

```bash
openclaw cron edit <jobId> --message "更新后的提示" --model opus
openclaw cron edit <jobId> --cron "0 8 * * *" --tz "Asia/Shanghai"
openclaw cron edit <jobId> --announce --channel telegram --to "chat_id"
openclaw cron edit <jobId> --no-deliver
openclaw cron edit <jobId> --agent ops
openclaw cron edit <jobId> --clear-agent
openclaw cron edit <jobId> --exact
```

### `openclaw cron remove <jobId>` — 删除 job

操作前必须先 `list` 确认 job 详情。

### `openclaw cron list` — 列出所有 job

查看当前全部 cron job 的状态。每次增删改操作后必须执行。

### `openclaw cron run <jobId>` — 手动触发

```bash
openclaw cron run <jobId>          # 强制立即执行
openclaw cron run <jobId> --due    # 仅在到期时执行
```

### `openclaw cron runs --id <jobId>` — 查看运行历史

```bash
openclaw cron runs --id <jobId> --limit 10
```

用于诊断 job 是否正常运行、查看失败原因和重试状态。

## 诊断工作流

```
1. openclaw cron list               → 确认 job 是否存在，是否 enabled
2. openclaw cron runs --id <jobId>  → 看最近执行记录、成功/失败/重试
3. 判断问题类型：
   - 配置问题（表达式、时区、delivery 目标错误）→ edit 修复
   - 环境问题（API 限流、网络错误）→ 建议 supervisor 分派给 ops
   - job 被禁用 → edit 重新启用
```

## 重试机制（内置）

了解即可，不需要手动管理：

- **一次性 job**：transient 错误最多重试 3 次（30s → 1m → 5m），permanent 错误立即禁用
- **周期 job**：连续失败时指数退避（30s → 1m → 5m → 15m → 60m），下次成功后重置

## 工具使用边界

### 绝对不做

- 不直接读写 `~/.openclaw/cron/jobs.json`
- 不修改 `managed-config/openclaw.json5` 中的 `cron` 配置节
- 不把 chat_id、webhook URL 等投递目标写入记忆
- 不创建 `--every` < 60000ms 的 job
- 不在没有 `--tz` 的情况下使用 `--cron`
- 不批量删除 job（每次只删一个，逐个确认）

### 谨慎操作

- 编辑正在运行中的 job 前，先 `runs` 确认没有活跃执行
- 创建 announce 类 job 前，确认 channel 配置已启用
- 使用 `--agent` 前，确认该 agent 存在且 enabled

## 记忆相关脚本

scheduler 不直接调用记忆脚本。记忆操作由 supervisor 控制。
