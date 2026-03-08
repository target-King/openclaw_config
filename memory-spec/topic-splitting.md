# Topic 拆分规则

## 目的
避免所有对话都堆在一个桶里，导致检索和摘要越来越乱。

## 当前推荐主题
- openclaw-config
- agent-design
- skill-design
- three-layer-memory
- rag-system
- deployment-sync
- project-conventions
- general

## 路由原则
- 配置、目录、skills、agents -> openclaw-config / agent-design / skill-design
- 记忆、摘要、检索 -> three-layer-memory / rag-system
- 同步、路径、脚本、安装 -> deployment-sync
- 项目命名、目录风格 -> project-conventions
- 无法判断 -> general

## 实践建议
- 一个主题达到一定长度，就生成摘要
- 主题名要稳定，不要频繁改
- 不同主题尽量不要混写进一个摘要

## Dialog 与 Topic 的关系

topic 桶内部需要按 `dialogId` 再做一层隔离：

- 同一个 topic 可能同时在多个对话框中被讨论
- L1/L2 按 `dialogId + topic` 双键存储和检索，互不干扰
- topic 路由结果需要透传 `dialogId`，确保后续记忆操作绑定到正确的对话框
- topic 本身是全局稳定的分类维度，不因 dialog 增减而变化
