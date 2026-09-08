# 维2·Skill排查报告 — 2026-05-04

> **审计方法：** 全量skills_list + cron jobs.json + 引擎源码 + 交易记录 + SKILL.md逐项分析
> **审计依据：** WORK_STANDARD.md 九维度追问链条
> **输出时间：** 2026-05-04 11:34 UTC+8

---

## 一、【缺少什么Skill？】全量扫描对照9维度

### 1.1 当前交易相关Skill清单（共5个，均在 devops/ 目录下）

| # | Skill名称 | 描述 | 覆盖维度 |
|:---|:---|---|:---:|
| 1 | `zq-web4-realtime-execution` | 实时执行引擎（评分/进场/出场） | ③策略、⑤盈利、⑥亏损 |
| 2 | `zq-web4-coin-pool-system` | 选币库系统（管理/行为追踪） | ④选币库 |
| 3 | `zq-web4-socratic-verification` | 苏格拉底验证（强制物理验证方法论） | 跨维度质量 |
| 4 | `zq-web4-self-improvement-loop` | 自我进化循环（反思/搜索/策略改进） | ⑦复盘、⑧数据源 |
| 5 | `zq-web4-system-management` | 系统运维（备份/部署/架构） | ①工具（运维层面） |

### 1.2 交易系统9维度 vs Skill覆盖分析

| 维度 | 当前覆盖 | 覆盖状态 | 缺什么Skill？ |
|:---|---|:---:|:---|
| ① 工具排查 | 无专用Skill（system-management仅覆盖运维） | ❌ 缺 | **`zq-web4-tool-audit`** — 自动检查所有已装工具（Python库/CLI/系统工具）的版本、激活状态、使用频率、是否有更好的替代 |
| ② Skill排查 | 无专用Skill | ❌ 缺 | **`zq-web4-skill-audit`** — 自动扫描所有Hermes Skill，标记未激活/未使用的Skill，对比系统需求缺口 |
| ③ 策略排查 | `zq-web4-realtime-execution`（核心） | ⚠️ 部分覆盖 | 缺一个**策略版本管理Skill** — 记录每次策略参数变更、回测结果、AB对比数据。当前策略变更日志散落在CHANGELOG.md和MEMORY.md中 |
| ④ 选币库排查 | `zq-web4-coin-pool-system` | ✅ 有 | 已覆盖 |
| ⑤ 盈利排查 | 无专用Skill（realtime-execution含盈利归因逻辑） | ❌ 缺 | **`zq-web4-profit-analysis`** — 独立的盈利归因分析模块：每日盈利交易特征提取、盈利模式DNA识别（BIO型 vs 趋势型 vs 消息型）、盈利持续性评估 |
| ⑥ 亏损排查 | 无专用Skill（ERRORS.md是手动维护） | ❌ 缺 | **`zq-web4-loss-analysis`** — 互锁亏损模式检测（E2误触占比、E3波持续时间、-2010频次）、亏损根因自动化分类（选币/入场/出场/数据/执行） |
| ⑦ 复盘排查 | `zq-web4-self-improvement-loop`（含复盘哲学） | ⚠️ 部分覆盖 | 缺一个**复盘模板Skill** — 强制24:00复盘流程，含四维分析模板（盈利点/亏损点/系统完善/系统多余） |
| ⑧ 数据源排查 | `zq-web4-self-improvement-loop`（含搜索方法论） | ⚠️ 部分覆盖 | 缺一个**数据源管理Skill** — 所有数据源的可用性监控、时延追踪、API key有效期管理、替代方案自动切换 |
| ⑨ 日最强币排查 | 无专用Skill | ❌ 缺 | **`zq-web4-top-daily-coin`** — 每天自动扫描BIO型特征候选币（排名飙升+放量+费率正+趋势刚转正+聪明钱提前进场），输出Top 3候选并标注数据支撑 |

### 1.3 【缺少的Skill】汇总 — 共6个

| 优先级 | 缺少的Skill | 对应维度 | 核心解决 |
|:---:|:---|---|:---|
| P0 | **`zq-web4-loss-analysis`** | ⑥亏损 | 所有亏损归因（E2占比、E3波、-2010）、模式识别、自动产生改进建议 |
| P0 | **`zq-web4-profit-analysis`** | ⑤盈利 | BIO型盈利模式识别、利润保护信号分析、日目标达成追踪 |
| P1 | **`zq-web4-top-daily-coin`** | ⑨日最强币 | 每天自动识别BIO型潜力币（3特征同时出现） |
| P1 | **`zq-web4-tool-audit`** | ①工具 | 全量工具扫描（已装/未装/激活/未激活/替代方案） |
| P2 | **`zq-web4-data-source-monitor`** | ⑧数据源 | 数据源可用性、时延、API key生命周期管理 |
| P2 | **`zq-web4-skill-audit`** | ②Skill | 与当前维2功能重叠，可合并 |

---

## 二、【Skill安装后有没有激活使用？】cron引用检查

### 2.1 各Skill在cron中的引用情况

| Skill | 是否在cron中被引用 | 引用的cron名称 | cron最后状态 |
|:---|---|:---|:---:|
| `zq-web4-realtime-execution` | ✅ **是** | `zq_web4_autonomous_trading`（30分钟）、`ZQ每日复盘-五大点`、`ZQ每日自我反思与策略进化` | ⚠️ 30分钟节点✅ok，其余❌error |
| `zq-web4-socratic-verification` | ✅ **是** | `ZQ每日自我反思与策略进化`、`ZQ-Quant每日分析` | ❌ error / null |
| `zq-web4-system-management` | ✅ **是** | `ZQ每日自我反思与策略进化`、`ZQ-Quant每日分析` | ❌ error / null |
| `zq-web4-coin-pool-system` | ❌ **否** | — | — |
| `zq-web4-self-improvement-loop` | ❌ **否** | — | — |

### 2.2 在引擎中的调用情况

| Skill | 引擎是否调用其内容 | 引擎文件 | 调用方式 |
|:---|---|:---|:---|
| `zq-web4-realtime-execution` | ✅ **是（核心）** | `engine_realtime_v2.py` | 引擎架构完全遵循此Skill设计（6AND/6OR/评分公式/资金费率/趋势判断） |
| `zq-web4-coin-pool-system` | ⚠️ **部分** | `engine_realtime_v2.py` | `load_coin_behavior()` + `get_behavior_bonus()` + `record_trade_in_pool()` 被调用，但实际效果=0（只有1条behavior记录） |
| `zq-web4-socratic-verification` | ❌ **否** | — | 方法论层Skill，不编码进引擎 |
| `zq-web4-self-improvement-loop` | ❌ **否** | — | 方法论层Skill |
| `zq-web4-system-management` | ❌ **否** | — | 运维层Skill |

### 2.3 【建了没用的】和【在用的】

| 分类 | Skill | 说明 |
|:---|:---|---:|
| ✅ **在用（有效）** | `zq-web4-realtime-execution` | 30分钟节点290次ok运行 |
| ⚠️ **在用（无效）** | `zq-web4-socratic-verification` | 被2个cron加载但全部error |
| ⚠️ **在用（无效）** | `zq-web4-system-management` | 被2个cron加载但全部error |
| ❌ **建了没用** | `zq-web4-coin-pool-system` | 有cron但不加载此Skill，引擎调了但效果=0 |
| ❌ **建了没用** | `zq-web4-self-improvement-loop` | 无cron引用，从未在引擎/任务中被调用 |

### 2.4 ⚠️ 致命问题：7/8个cron全部error

```json
// 只有 zq_web4_autonomous_trading 的 last_status 是 "ok"
// 其他7个cron全部报：
{
  "last_status": "error",
  "last_error": "RuntimeError: Error code: 400 - 
    {'error': {'message': 'The supported API model names are deepseek-v4-pro or 
     deepseek-v4-flash, but you passed .'}}"
}
```

**根因：** 这些cron job没有显式设置 model 字段，系统默认model名称变成了空字符串。只有 `zq_web4_autonomous_trading` 显式设置了 `"model": "deepseek/deepseek-v4-flash"`。

---

## 三、【使用的怎么样？】在用Skill逐项评估

### 3.1 `zq-web4-realtime-execution` — ⭐⭐⭐⭐⭐

| 评估维度 | 结论 | 物理数据 |
|:---|---|:---:|
| 解决核心问题？ | ✅ **部分解决** — 实现了自动选币评分（6AND进场/6OR出场），但尚未解决「盈利」核心问题 | 290次运行，已执行348笔交易 |
| 产出质量？ | ✅ **高** — 代码1025行、36个函数、40+参考文档、SKILL.md篇幅极大、陷阱列表详尽 | `engine_realtime_v2.py` 持续迭代至v2.3 |
| 产出被采纳？ | ⚠️ **部分采纳** — 引擎输出的选币评分被用于每30分钟节点交易；但买入选币不被coin_pool采纳（behavior记录仅1条），复盘建议不总被执行 | TRADES.md 记录完整，但coin_pool.json behavior=1 |
| 文档完整度 | ✅ **极高** — 40+ reference files, 6个脚本文件 | 所有引擎状态模式都有文档记录：核心态/边际态/混合态/E3波/E2阻断等 |

**具体产出质量数据：**
- 评分质量：评分>=85的币胜率30%，75-85的38%（高分可能是追高信号）
- 资金费率方向反了导致负作用（负费率加分=扣分应当，2026-05-04最新审计）
- 唯一盈利BIO是歪打正着（负费率加分的受益者）

### 3.2 `zq-web4-socratic-verification` — ⭐⭐⭐

| 评估维度 | 结论 | 物理数据 |
|:---|---|:---:|
| 解决核心问题？ | ⚠️ **方法论解决了，但执行没跟上** — 哲学「数据要物理验证」已写入工作流，但cron全部error导致无法执行 | cron全部error |
| 产出质量？ | ✅ 高质量方法论文档，6个reference文件，逻辑链条完整 | SKILL.md + references/ |
| 产出被采纳？ | ⚠️ 方法论已被写入日常Agent prompts和WORK_STANDARD.md，但可执行性不足 | — |

### 3.3 `zq-web4-system-management` — ⭐⭐⭐

| 评估维度 | 结论 | 物理数据 |
|:---|---|:---:|
| 解决核心问题？ | ⚠️ **备份功能✅，其他部分闲置** — backup脚本可运行，但8维架构/云部署等章节未激活 | 备份cron因model error失败；手动运行backup_full.sh成功 |
| 产出质量？ | ✅ 文档完整（12个reference文件、架构图、备份验证） | 已验证 |
| 产出被采纳？ | ⚠️ 备份架构被采纳（backup_full.sh在跑），但8维架构层状态未真正使用 | 手动备份OK，自动cron不跑 |

---

## 四、【需要怎么提升？】具体改进方案

### 4.1 `zq-web4-realtime-execution`

| 问题 | 具体改进操作 |
|:---|---|
| 资金费率方向反了 | `engine_realtime_v2.py` 第400-414行：将负费率评分逻辑从+15改为-15，正费率从-15改为+15。发布时间：**立即** |
| 评分>=85胜率反而不如75-85 | 增加趋势2的惩罚（高位追涨），trend=2在评分中降权20%。阈值需AB测试 |
| 行为数据只有1条 | 修复`record_trade_in_pool()`写入路径从`behavior.json`改为`coin_pool.json.behavior`，确保每次sell后写入成功 |
| 选币库不参与实时决策 | 在`scan_top50()`中增加从coin_pool读取的历史胜率因子（-10~+10），让行为数据反向影响评分 |
| 无主动止盈 | 已在v2.3中实现P信号（RSI>80 + 1h趋势衰竭），确认真实运行中是否有被触发过 |

### 4.2 `zq-web4-coin-pool-system`

| 问题 | 具体改进操作 |
|:---|---|
| --update 每周cron error | 手动运行一次抓取完整错误输出，修复API调用（可能是Binance API变更/超时）。如遇auth.json路径问题，改用`cd ~/zq_web4_trading_system && python3 -c`方式调用 |
| behavior记录断裂 | 修改`record_trade_in_pool()`写的是`behavior.json`还是`coin_pool.json.behavior`字段。读取TRADES.md所有348笔卖出，批量回填到pool |
| 引擎不读pool | 在引擎增加`load_coin_pool_score()`函数，从pool读取历史胜率作为评分因子（-10~+10），量化为代码行数约20行 |

### 4.3 `zq-web4-socratic-verification`

| 问题 | 具体改进操作 |
|:---|---|
| cron全部error不执行 | 修复所有cron的model配置，添加 `"model": "deepseek/deepseek-v4-flash"` |
| 方法论文档缺少可执行检查清单 | 增加 `scripts/socratic_checklist.sh` — 运行后逐一检查是否做了物理验证、是否查了时间、是否查了前因后果 |
| 建议写入参考模板 | 在SKILL.md中增加「每次汇报前自检矩阵」模板 |

### 4.4 `zq-web4-self-improvement-loop`

| 问题 | 具体改进操作 |
|:---|---|
| 从未被cron引用 | 将`ZQ每周全网学习扫描`和`ZQ-Scouter每周一全网扫描`两个cron的skills表增加此skill |
| 缺少强制复盘执行器 | 创建 `scripts/daily_review.py` — 读取TRADES.md今天所有交易，自动输出四维分析模板（盈利点/亏损点/系统完善/系统多余） |

### 4.5 `zq-web4-system-management`

| 问题 | 具体改进操作 |
|:---|---|
| 备份cron model error | 同样添加 `"model": "deepseek/deepseek-v4-flash"` 修复 |
| 自动排查看板未实现 | 在报告中加入8维架构层的图标化状态（🟢🟡🔴） |

---

## 五、【有没有反馈机制？】error处理/monitoring检查

| Skill | error处理机制 | monitoring方式 | 状态 |
|:---|---|:---:|:---:|
| `zq-web4-realtime-execution` | ✅ API错误-1022/-2010/418 都有处理逻辑；ERRORS.md手动维护 | ⚠️ cron last_status监控只有ok/error两级，不够精细 | 🟡 部分OK |
| `zq-web4-coin-pool-system` | ❌ 无 | ❌ 无 — --update error了但没有告警 | 🔴 缺失 |
| `zq-web4-socratic-verification` | ❌ 方法论Skill，无代码级error处理 | ❌ 无 | 🔴 缺失 |
| `zq-web4-self-improvement-loop` | ❌ 无 | ❌ 无 | 🔴 缺失 |
| `zq-web4-system-management` | ⚠️ 备份脚本有exit code检查，但cron不跑 | ❌ 备份成功与否无主动通知 | 🔴 缺失 |

**关键发现：** 所有cron job的error类型为「model名称空字符串」— 这是**统一样式错误**。不是个别bug，是配置问题。

---

## 六、【任务指南？】是否有对应的任务指南文档

| Skill | 有任务指南？ | 指南位置 | 类型 |
|:---|---|:---|:---:|
| `zq-web4-realtime-execution` | ✅ **有** | SKILL.md 是整个可执行指南（66+陷阱、40+references、6个脚本） | 图文并茂 |
| `zq-web4-coin-pool-system` | ✅ **有** | SKILL.md 包含选币库架构、修复路径、赛道分类 | 偏设计文档 |
| `zq-web4-socratic-verification` | ✅ **有** | SKILL.md 含方法论、自检清单、哲学追加 | 方法论文档 |
| `zq-web4-self-improvement-loop` | ✅ **有** | SKILL.md 含反思流程、搜索方法论、自动修改原则 | 流程文档 |
| `zq-web4-system-management` | ✅ **有** | SKILL.md 含部署流程、备份SOP、故障处理 | 运维手册 |

**结论：** 所有5个Skill都有内容完整的SKILL.md作为任务指南。但存在的问题：
1. `zq-web4-coin-pool-system` 的修复指南写的是「应该修复」，没有**具体的修复步骤命令**
2. `zq-web4-self-improvement-loop` 的复盘模板是描述性的，不是**可执行的脚本**

---

## 七、总结与P0行动项

### 7.1 整体评分

| 维度 | 评分 | 说明 |
|:---|---:|:---|
| Skill覆盖（9维度） | 5/9 | 缺少盈利/亏损/日最强币/工具/数据源管理Skill |
| Skill激活率 | 3/5 | 2个建了没用，3个在用的中仅1个有效 |
| 执行稳定性 | 1/5 | 8个cron中7个error，唯一ok的是30分钟节点 |
| 产出质量 | 3/5 | 实时执行Skill质量高，但方法论Skill无执行反馈 |
| 反馈机制 | 2/5 | 只有引擎有基本error处理，cron没有精细监控 |
| 任务指南 | 4/5 | 都有文档，但部分缺少可执行命令 |

### 7.2 P0行动项（24小时内必须完成）

1. **修复7个error cron** — 打开jobs.json，对所有缺失model字段的cron添加 `"model": "deepseek/deepseek-v4-flash"`
2. **修复资金费率方向** — `engine_realtime_v2.py` 负费率扣分、正费率加分
3. **修复选币库behavior断裂** — 确认写入路径，回填348笔交易历史
4. **激活`zq-web4-self-improvement-loop`** — 将"ZQ每周全网学习扫描"和"ZQ-Scouter"两个cron关联到此Skill

### 7.3 需要新建的Skill优先级

| 优先级 | Skill名称 | 何时建 | 最低可行版本 |
|:---:|:---|---|:---|
| P0 | `zq-web4-loss-analysis` | 本周 | 读取TRADES.md → 输出亏损归因表（E2占比/E3波频次/平均亏损额） |
| P0 | `zq-web4-profit-analysis` | 本周 | 识别BIO型盈利特征 → 输出明日候选币和特征匹配度 |
| P1 | `zq-web4-top-daily-coin` | 下周 | 每天自动扫描Top 50中「排名飙升+放量+费率正+趋势刚转正」 |
| P2 | `zq-web4-tool-audit` + `zq-web4-data-source-monitor` | 持续 | 合并进现有自动排查框架 |

---

*审计执行人：ZQ Agent (维2·Skill排查)*
*审计时间：2026-05-04 11:34 UTC+8*
*下一维待排查：维3·策略排查*
