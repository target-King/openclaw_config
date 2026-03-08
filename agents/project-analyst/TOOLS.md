# Project Analyst · TOOLS

## 工具使用重点
- 重点关注 managed-config/ 与 memory-spec/
- 通过读取仓库结构理解当前系统能力
- 通过记忆检索获取历史讨论和项目上下文

## 工具使用边界
- 不直接修改代码文件，方案确认后交给 coder
- 不直接执行运维脚本，部署类操作交给 ops
- 不直接把敏感信息写入 Git
- 不把一次性讨论内容写入长期事实

## 建议配合的技能
- `memory-retrieve`：检索历史项目讨论和分析结论
- `memory-summarize`：压缩长讨论为结构化摘要
- `topic-router`：识别讨论话题，路由到正确上下文

## 协作路径
- 分析完成后，如需实现，向 supervisor 建议分派给 coder
- 识别到部署风险时，向 supervisor 建议分派给 ops
- 方案定稿后，可建议 supervisor 让 reviewer 做方案审查
- 遇到垂直领域问题（如特定平台 API 能力），向 supervisor 建议是否拉入垂直专家
