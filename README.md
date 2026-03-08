# OpenClaw Home

这是一个 **Git 管理的 OpenClaw 控制仓库**。

它的定位不是直接替代 OpenClaw 的运行目录，而是作为你的 **源配置仓库**，统一管理：

- agents
- skills
- managed-config
- scripts
- memory-spec
- 模板文件
- 一键同步脚本

等本机安装 OpenClaw 后，或者你想先把本地目录准备好时，再通过脚本把这里的内容同步到本地的 `.openclaw` 目录。

---

## 一、仓库目标

这个仓库解决的是三个问题：

1. **把 Agent / Skill / 规则放进 Git**
2. **把运行态和敏感信息排除在 Git 之外**
3. **用脚本把仓库内容同步到本地 OpenClaw 目录**

---

## 二、仓库里放什么

本仓库应该纳入 Git 的内容：

- `agents/`
- `skills/`
- `managed-config/`
- `scripts/`
- `templates/`
- `memory-spec/`
- `README.md`
- `.env.example`
- `.gitignore`
- `bootstrap-openclaw.bat`
- `bootstrap-openclaw.ps1`
- `bootstrap-openclaw.sh`

---

## 三、不放进 Git 的内容

以下内容属于运行态、本地态或敏感信息，不应直接提交到 Git：

- 真实 `.env`
- token / key / credential
- OpenClaw sessions
- OpenClaw auth / credentials
- SQLite 数据库文件
- 向量索引文件
- cache
- logs
- 临时导出文件

---

## 四、目录说明

### `agents/`
存放多 Agent 的角色定义、行为规则、记忆使用策略。

默认包含：

- `supervisor`：总控、任务分流、记忆路由
- `coder`：代码实现
- `reviewer`：审查与风险检查
- `ops`：部署、诊断、同步、日志

每个 agent 目录中包含：

- `AGENTS.md`
- `SOUL.md`
- `USER.md`
- `TOOLS.md`

### `skills/`
存放共享 Skill。

初期包含：

- `memory-retrieve`
- `memory-summarize`
- `topic-router`
- `repo-health`
- `git-sync`

每个 Skill 至少包含：

- `SKILL.md`

### `managed-config/`
存放控制仓库自己的托管配置，而不是强行冒充 OpenClaw 官方运行时配置。

默认包含：

- `openclaw.json5`
- `agents.json5`
- `skills.json5`
- `channels.json5`

### `scripts/`
存放可执行脚本。

分两类：

1. 系统脚本
   - `install.ps1`
   - `sync.ps1`
   - `backup.ps1`
   - `doctor.ps1`

2. 记忆系统脚本
   - `memory/init_db.py`
   - `memory/ingest_chat.py`
   - `memory/retrieve_context.py`
   - `memory/summarize_topic.py`
   - `memory/compact_memory.py`

### `memory-spec/`
存放记忆系统设计文档。

包含：

- `three-layer-memory.md`
- `rag-flow.md`
- `topic-splitting.md`
- `retention-policy.md`

### `templates/`
存放新增 Agent / Skill 时可复用的模板文件。

---

## 五、三层记忆设计

本仓库默认采用三层记忆结构：

### L1：当前会话记忆
- 保存最近几轮上下文
- 优先级最高
- 不作为长期事实存储

### L2：话题摘要记忆
- 按 topic 拆分
- 当同一主题对话过长时压缩为摘要
- 用于中期检索
- 用来减少上下文长度

### L3：长期事实记忆
- 保存长期稳定的信息
- 例如路径规范、项目规则、命名习惯、用户偏好
- 写入频率低
- 读取价值高

---

## 六、检索顺序

默认检索顺序：

1. L1 当前会话
2. L2 话题摘要
3. L3 长期事实

原则：

- 能从 L1 解决，就不查更深层
- 会话过长时，优先压缩到 L2
- 稳定规则与偏好，写入 L3
- 不把整段历史直接塞回上下文

---

## 七、关于 OpenClaw 兼容性

这套仓库先解决 **“源管理 + 同步”**，不强依赖你当前机器已经安装 OpenClaw。

也就是说：

- 你现在没安装 OpenClaw，也可以先维护这套仓库
- 运行 `bootstrap-openclaw.bat` 后，会先准备本地 `.openclaw` 目录结构
- 若未来你的 OpenClaw 版本和运行时配置项不同，**以你实际安装版本的运行时要求为准**
- 本仓库负责的是：Agent 文件、Skill 文件、三层记忆规则、同步脚本、托管配置

---

## 八、快速开始

### 1. 先把这套仓库放到本地

Windows 示例：

`D:\Projects\openclaw-home`

Linux 示例：

`~/projects/openclaw-home`

### 2. 按系统运行入口脚本

#### Windows
运行：

`bootstrap-openclaw.bat`

或：

```powershell
./bootstrap-openclaw.ps1
```

#### Linux
先给执行权限：

```bash
chmod +x bootstrap-openclaw.sh scripts/*.sh scripts/lib/*.sh
```

再运行：

```bash
./bootstrap-openclaw.sh
```

它会：

- 创建本地 `.openclaw` 控制目录（如果不存在）
- 备份已有重要文件（如果存在）
- 同步 skills
- 同步各 agent 的工作区内容
- 同步托管配置到 `managed-source`

### 3. 跨平台路径规则

- Windows 默认目标目录：`%USERPROFILE%\.openclaw`
- Linux 默认目标目录：`$HOME/.openclaw`
- 两个系统都支持用环境变量 `OPENCLAW_HOME` 覆盖默认目录

### 4. 初始化本地记忆库
在仓库根目录执行：

```bash
python scripts/memory/init_db.py
```

### 5. 写入测试数据
例如：

```powershell
python scripts/memory/ingest_chat.py --topic openclaw-config --role user --content "我想做一个 Git 管理的 OpenClaw 控制仓库"
```

### 6. 生成话题摘要
```powershell
python scripts/memory/summarize_topic.py --topic openclaw-config
```

### 7. 检索上下文
```powershell
python scripts/memory/retrieve_context.py --topic openclaw-config
```

---

## 九、实施顺序建议

### 阶段 1：先把规则写明白
- Agent 定义
- Skill 定义
- 三层记忆设计文档
- 检索流程文档

### 阶段 2：先跑通最小实现
- SQLite 初始化
- 会话写入
- 话题摘要
- 上下文检索
- 记忆压缩

### 阶段 3：再对接真实 OpenClaw 运行时
- 安装 OpenClaw
- 对照运行时要求调整路径
- 把控制仓库和实际运行目录衔接起来

---

## 十、维护原则

1. Git 管规则，不管运行态
2. 先做最小可运行，再做复杂增强
3. 先 SQLite，再考虑向量检索
4. 先 Topic + Summary，再考虑复杂 RAG
5. 配置、脚本、文档分开维护
6. 所有 Agent 与 Skill 都尽量可复用、可扩展、可迁移

---

## 十一、当前包里已经写好的内容

当前 starter 包已经包含：

- 完整目录骨架
- 4 个 agent 的初版角色文件
- 5 个 shared skills 的初版说明
- 三层记忆与 topic-aware memory 文档
- SQLite 最小版记忆脚本
- Windows 一键同步与检查脚本
- Git 忽略规则
- 环境变量示例

---

## 十二、建议下一步

你现在最适合做的是：

1. 先运行 `bootstrap-openclaw.bat`
2. 再运行 `python scripts/memory/init_db.py`
3. 然后把你自己的项目规则、路径规范、命名规范慢慢写进：
   - `agents/*/SOUL.md`
   - `memory-spec/*.md`
   - `skills/*/SKILL.md`

这样这套仓库就会从“骨架”变成你自己的长期控制中心。


## 十三、双系统支持说明

这套仓库现在支持：

- Windows：`.bat + .ps1`
- Linux：`.sh`
- Python 记忆脚本：Windows / Linux 共用

统一原则：

- 仓库结构只有一套
- Agent 文件只有一套
- Skill 文件只有一套
- 三层记忆规则只有一套
- 区别只在入口脚本和路径解析

默认路径：

- Windows：`%USERPROFILE%\.openclaw`
- Linux：`$HOME/.openclaw`

也就是说，你可以：

- Windows 本地维护
- Linux 服务器部署
- 同一个 Git 仓库同时服务两边
