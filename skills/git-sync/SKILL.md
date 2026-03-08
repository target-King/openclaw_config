# git-sync

## 目的
把 Git 管理的控制仓库内容同步到本地 `.openclaw` 目录，保持“源”和“本地工作目录”分离。

## 同步对象
- `managed-config/` -> `.openclaw/managed-source/`
- `skills/` -> `.openclaw/skills/`
- `agents/supervisor/` -> `.openclaw/workspace-supervisor/`
- `agents/coder/` -> `.openclaw/workspace-coder/`
- `agents/reviewer/` -> `.openclaw/workspace-reviewer/`
- `agents/ops/` -> `.openclaw/workspace-ops/`

## 不同步 / 不覆盖
- `sessions/`
- `credentials/`
- `auth/`
- `.env`
- `data/*.db`
- `logs/`

## 执行原则
- 先备份，再覆盖
- 尽量只同步源配置
- 不把运行态目录误当成 Git 管理目录
- 日志输出要明确

## 配套脚本
- `bootstrap-openclaw.ps1`
- `scripts/install.ps1`
- `scripts/sync.ps1`
- `scripts/backup.ps1`
