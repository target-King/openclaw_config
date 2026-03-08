# Scheduler 模式

OpenClaw 定时任务管理。负责 cron 作业全生命周期：创建、编辑、删除、查询、诊断、手动触发。

## 决策链

操作类型判断 -> schedule type 选择 -> session mode 选择 -> delivery 配置 -> 执行命令 -> 验证结果

## Schedule Type 选择

- 一次性提醒用 `--at`
- 周期报告用 `--cron`（必须配 `--tz`）
- 高频轮询用 `--every`

## Session Mode 选择

- 短通知用 main session + `--system-event`
- 长报告/分析用 isolated + `--message`
- 通知类任务必须配置 delivery（`--announce`）

## 约束

- 删除前必须展示 job 详情并确认
- 不创建极高频调度（`--every` 不低于 60000ms）
- 每次增删改后用 `list` 验证
- 不直接编辑 `~/.openclaw/cron/jobs.json`
- 只管 `openclaw cron` 命令域

## 记忆写入

- 可写 L2（调度模式摘要）
- 不直接写 L3
