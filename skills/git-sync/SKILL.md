# git-sync

## 目的

把 Git 管理的控制仓库内容同步到服务器端 `.openclaw` 目录，保持"源"和"运行目录"分离。

## 标准化同步流程

针对服务器因仓库不同步引起的所有问题，统一采用以下流程处理，不在服务器上直接修改文件：

```
1. 本地修改  — 在本地控制仓库 (openclaw-config) 中完成修改和修复
2. 推送远程  — git add / git commit / git push，将变更推送到 Git 远程仓库
3. 服务器拉取 — 在服务器端执行 git pull，获取最新仓库内容
4. 执行同步  — 在服务器端运行 scripts/sync.ps1（或 sync.sh），将仓库内容分发到 .openclaw 目录
```

此流程是处理所有同步类问题的唯一正确路径。禁止跳过任何步骤或在服务器端直接编辑文件。

## 同步对象

- `managed-config/` -> `.openclaw/managed-source/`
- `skills/` -> `.openclaw/skills/`
- `agents/supervisor/` -> `.openclaw/workspace-supervisor/`
- `agents/coder/` -> `.openclaw/workspace-coder/`
- `agents/reviewer/` -> `.openclaw/workspace-reviewer/`
- `agents/ops/` -> `.openclaw/workspace-ops/`
- `agents/project-analyst/` -> `.openclaw/workspace-project-analyst/`

## 不同步 / 不覆盖

- `sessions/`
- `credentials/`
- `auth/`
- `.env`
- `data/*.db`
- `logs/`

## 执行原则

- 所有修改必须在本地控制仓库中完成，通过 Git 流转到服务器
- 同步前先备份（`scripts/backup.ps1`），再覆盖
- 同步前先检查仓库健康（`scripts/doctor.ps1`），确保结构完整
- 尽量只同步源配置，不把运行态目录误当成 Git 管理目录
- 日志输出要明确，每一步有可追溯的记录

## 故障处理

当服务器出现因仓库不同步导致的问题时：

1. **不要**在服务器上直接修改文件
2. 在本地控制仓库中定位并修复问题
3. 运行 `scripts/doctor.ps1`（或 `doctor.sh`）确认仓库结构完整
4. 提交并推送修复到远程仓库
5. 在服务器端拉取最新代码
6. 在服务器端重新执行 `scripts/sync.ps1`（或 `sync.sh`）

## 配套脚本

| 脚本 | 用途 |
|---|---|
| `scripts/sync.ps1` / `scripts/sync.sh` | 执行同步（含推送前检查、服务器拉取、文件分发） |
| `scripts/doctor.ps1` / `scripts/doctor.sh` | 同步前仓库健康检查 |
| `scripts/backup.ps1` / `scripts/backup.sh` | 同步前目标目录备份 |
| `scripts/install.ps1` / `scripts/install.sh` | 首次安装目录初始化 |
| `bootstrap-openclaw.ps1` / `bootstrap-openclaw.sh` | 完整引导 |
