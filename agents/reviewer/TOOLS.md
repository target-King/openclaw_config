# Reviewer · TOOLS

## 工具使用重点
- 检查必需文件是否齐全
- 检查脚本是否会误覆盖敏感目录
- 检查是否把运行态误放进 Git

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
