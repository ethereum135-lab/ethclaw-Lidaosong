# Hermes Agent 团队化分工指南

## 为什么需要团队化？

如果你把所有需求都塞给一个 Agent，很快会遇到两个问题：

1. **上下文和记忆越聊越乱** — 研究、写代码、查资料、回消息全混在同一个会话里
2. **一次只能处理一个任务** — 让 Agent 跑研究时，别的事只能干等着

真正把 Hermes 用顺的人，往往不是把单个 Agent 调得更猛，而是尽快把它组织成**一个有分工的团队**。

可以把 Hermes 团队理解成一个小型数字工作室：
- 有的 Agent 专门做规划
- 有的 Agent 负责研究
- 有的 Agent 负责执行
- 还有的 Agent 只做复核和交付

每个角色只处理自己那一段，上下文就会干净很多。而且团队化以后，你终于不用再等单个 Agent 慢慢排队，而是可以把任务拆开分别推进。

---

## 核心思路：Profile 隔离

Hermes 的 **Profile** 机制是实现团队化的基础。每个 Profile 是**完全独立的 Agent 实例**——独立的记忆、独立的会话、独立的人格。

```
默认 profile         → "我什么都会"（上下文越来越乱）
多个 profile 分工    → 每个只做一件事（上下文干净）
```

---

## 四步搭建团队骨架

### 第一步：克隆 Profile

用你已有的基础配置，克隆出多个角色：

```bash
hermes profile create agent-planner --clone
hermes profile create agent-researcher --clone
hermes profile create agent-executor --clone
hermes profile create agent-reviewer --clone
```

每个 Profile 继承你调好的模型、API Key、工具集，但后续的**记忆和会话完全独立**。

克隆完成后会自动生成快捷命令：
```bash
# 直接调用对应角色
agent-planner chat
agent-researcher chat
```

### 第二步：写 SOUL.md（角色灵魂）

每个 Profile 目录下都有一个 `SOUL.md` 文件，这是 Agent 的人格定义。在这里写清楚：

- **你是谁** — 这个角色的身份定位
- **你擅长什么** — 核心职责和能力
- **你不该碰什么** — 边界，防止越权
- **你的工作流** — 如何处理任务
- **你的信条** — 行为准则

路径：`~/.hermes/profiles/<profile-name>/SOUL.md`

**示例（通用模板）：**

```markdown
# Agent-Planner — 规划者

## 你是谁
你是团队的规划大脑。你不执行具体任务，你负责拆解问题、制定方案、分配工作。

## 你擅长什么
- 把模糊的需求拆解成可执行的任务列表
- 设计技术方案和架构
- 评估任务的优先级和依赖关系
- 判断什么时候该交给 Researcher，什么时候该交给 Executor

## 你不该碰什么
- ❌ 不写具体代码
- ❌ 不做外部搜索
- ❌ 不执行具体操作

## 你的信条
- "好的规划让执行变得简单。"
- "如果任务拆得不够细，那就是规划还没做完。"
```

### 第三步：写 AGENTS.md（团队共享上下文）

在项目根目录放一个 `AGENTS.md`，让整个团队共享：
- 团队架构图（谁负责什么）
- 协作流程（任务怎么流转）
- 当前项目状态
- 通用规则（所有角色都要遵守的规范）

每个 Profile 启动时都会读到这个文件，确保大家知道自己在哪里、别人在做什么。

### 第四步：写 MEMORY.md（共享状态）

在项目根目录放一个 `MEMORY.md`，记录团队当前共享状态：
- 项目当前进度
- 已知的问题和待办
- 已采用的改进记录
- 重要的决策历史

这个文件让不同 Profile 之间能"接力"——Executor 干完活更新状态，Planner 接下来能知道该做什么。

---

## 三个文件各管什么

| 文件 | 位置 | 作用 |
|------|------|------|
| `SOUL.md` | 每个 Profile 目录下 | 定义单个 Agent 的人格和边界——"我是谁？该做什么？不该做什么？" |
| `AGENTS.md` | 项目根目录 | 定义团队共享背景——"我们正在做什么项目？协作规则是什么？" |
| `MEMORY.md` | 项目根目录 | 记录当前共享状态——"项目走到哪了？有什么已知问题？" |

**SOUL.md 管"我是哪个角色"，AGENTS.md 管"我们在做什么项目"，MEMORY.md 管"现在到哪了"。** 三个文件分开以后，团队协作才会稳定。

---

## 任务流转示例

```
Planner: "这个需求拆成3步，Researcher 先去调研方案，然后 Executor 来实现"

    → Researcher: 搜索调研 → 输出方案评估 → 更新 MEMORY.md

    → Planner: 看 Researcher 的结果 → 确定实施方案 → 下指令给 Executor

    → Executor: 执行具体实现 → 完成任务 → 更新 MEMORY.md

    → Reviewer: 复核 Executor 的结果 → 确认没问题 → 通知交付
```

每个角色只处理自己那一段，上下文不会污染。

---

## 常用命令

```bash
# 查看所有 Profile
hermes profile list

# 用指定角色执行任务
agent-planner chat -q "为这个需求做一份规划"
agent-researcher chat -q "调研一下这个技术方案"

# 查看某个角色的 SOUL.md
cat ~/.hermes/profiles/agent-planner/SOUL.md

# 编辑某个角色的 SOUL.md
vim ~/.hermes/profiles/agent-planner/SOUL.md

# 删除不需要的角色
hermes profile delete agent-old-role
```

---

## 最重要的原则

这套方法的真正价值不是让 Hermes 看起来更高级，而是让它**终于能像团队一样稳定工作**：
- 任务拆得更细
- 上下文更干净
- 每个 Agent 有自己的角色边界
- 可以同时推进多件事

如果你现在已经有一个跑通的 Hermes，下一步最值得做的不是继续往单个会话里塞更多需求，而是尽快把它团队化。
