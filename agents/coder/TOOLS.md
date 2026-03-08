# Coder · TOOLS

## 工具使用重点
- 重点关注 scripts/ 与 managed-config/
- 优先生成最小可运行实现
- 避免破坏已有结构

## 工具使用边界
- 不直接把敏感信息写入 Git
- 不把运行态 sessions、credentials 当成源配置
- 不默认删除用户已有目录
- 对同步类操作，优先备份再覆盖

## 建议配合的脚本
- `scripts/install.ps1`
- `scripts/sync.ps1`
- `scripts/backup.ps1`
- `scripts/doctor.ps1`

## 记忆相关脚本
- `scripts/memory/init_db.py`
- `scripts/memory/ingest_chat.py`
- `scripts/memory/retrieve_context.py`
- `scripts/memory/summarize_topic.py`
- `scripts/memory/compact_memory.py`
