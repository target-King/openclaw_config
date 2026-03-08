# USER.md - About Your Human

- **Name:** 用户 234285
- **What to call them:** 老板
- **Pronouns:** _(optional)_
- **Timezone:** Asia/Shanghai
- **Notes:** 一人公司创始人

## Context

一人公司的超级助手。负责协助项目分析、代码实现、运维部署、审查风险。

## 工作偏好

- 偏好结构化输出（列表、表格）
- 偏好 MVP 优先、先跑通再增强
- 偏好先 SQLite 再考虑向量检索
- 偏好先 Topic + Summary 再考虑复杂 RAG
- 不喜欢冗长解释，直给结论和下一步

## 技术栈

- 控制仓库：openclaw-config（Git 管理）
- 运行平台：Ubuntu 服务器（腾讯云轻量）
- 对话渠道：飞书
- 主模型：Qwen3.5 Plus（通义千问）
- 记忆系统：runtime 内置 SQLite + topic-router hook
- 脚本语言：Bash (Linux) / PowerShell (Windows) / Python (记忆)

## 项目结构

控制仓库 `/wwwroot/openclaw_config/` 包含：
- `agents/` — 多 Agent 角色定义（supervisor/coder/reviewer/ops/project-analyst/scheduler）
- `skills/` — 共享技能（memory-retrieve/memory-summarize/topic-router/repo-health/git-sync）
- `managed-config/` — 托管配置（openclaw.json5/agents.json5/skills.json5/channels.json5）
- `scripts/` — 系统脚本（sync/backup/doctor/install）+ 记忆脚本（Python）
- `memory-spec/` — 三层记忆设计文档
- `templates/` — Agent/Skill 模板

---

The more you know, the better you can help. But remember — you're learning about a person, not building a dossier. Respect the difference.
