# topic-router

## 目的
判断当前对话属于哪个主题，为后续检索和摘要选择正确的话题桶。

## 已知主题
- openclaw-config
- agent-design
- skill-design
- three-layer-memory
- rag-system
- deployment-sync
- project-conventions
- general

## 输入
- 当前问题
- dialogId（**必须**，路由结果需透传给后续记忆操作）
- 可选的历史摘要
- 可选的关键词

## 输出
- topic
- topic 置信度
- 推荐下游动作
- dialogId（透传，确保下游检索和写入绑定到正确的对话框）

## 路由规则
- 涉及 Agent / Skill / 配置：优先 openclaw-config / agent-design / skill-design
- 涉及三层记忆 / 检索：优先 three-layer-memory / rag-system
- 涉及同步 / 路径 / 安装 / 双击脚本：优先 deployment-sync
- 若无法确定：落回 general

## 配套脚本
当前版本先用规则路由，不单独写脚本；后续可扩展。

## 未来增强
- 关键词权重
- topic 别名
- topic 热度统计
