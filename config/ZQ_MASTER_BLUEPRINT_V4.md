# 🏗️ ZQ Web 4.0 总蓝图 V4 — 每日盈利导向
> **版本：** V4 (2026-09-09 全局审计后升级)
> **变更摘要：** 资金$240→$201(实查)；策略网格→ETH趋势通道v3.1；新增六大系统架构层；新增CI/CD+Codex管道编排+Ollama本地推理+视觉内容生成；交易数据库+审计档案库已创建
> **来源：** 老李战略部署 + 六大系统全局审计
> **核心目标：** 一天都不放过，每日总资×0.1~0.3%复利（中值0.2%），$201→1,000,000U
> **指导思想：** 总蓝图→子蓝图→逐层细化到每个Agent/工具/文档/学习计划
> **铁律：** 创建B替代A后，必须立即删除A（铁律九）

---

## 第0层：铁律层 — 不可违反的系统底线

```
铁律一~九（见 config/IRON_RULES.md 全文）
核心：
  · 验证为王 — 任何汇报必须带上物理证据
  · 苏格拉底闭环 — 质疑→澄清→验证→发现→修复→归档
  · 数据驱动实操 — 三方共振，30分钟末位淘汰
  · 落地责任制 — 15分钟内归入 audit/ 档案库
  · 每日盈利0.1~0.3% + 资金全利用
  · 每日盈利自检 — 连续3天不达标触发全链审查
  · 信息分享≠修改指令
  · 日清日结·三排查三跑通三验证
  · 先排查后创建，替代旧版必须删除
```

**审计验证（2026-09-09）：**
- ✅ 铁律一：total_asset.json 已同步到 shared_context（source=binance_api_real_balance）
- ✅ 铁律四：audit/ 档案库已创建
- ✅ 铁律五：真实余额 $201.16（Binance API 实查，2026-09-08 21:20）
- ✅ 铁律八：本次审计执行三排查三验证

---

## 第1层：战略层 — 资金路线图

| 阶段 | 资金区间 | 日目标 | 核心策略 | 预计周期 |
|:----|:---------|:------|:---------|:--------|
| **P1** | **$201(当前)** → 1,000U | 总资×0.1~0.3%/天 = $0.20~$0.60 | ETH趋势通道v3.1（Donchian 5日突破+2%盈利锁定） | 持续 |
| **P2** | 1,000U → 10,000U | 2%/天 ≈ 20U→200U | 现货轮动+精选杠杆 | ~120天 |
| **P3** | 10,000U → 100,000U | 2%/天 | 全赛道+合约+多策略并行 | ~120天 |
| **P4** | 100,000U → 1,000,000U | 2%/天 | 全球最赚钱的交易系统 | ~120天 |

**当前资金：$201.16（Binance API 实查，2026-09-08 21:20 BJT）**
> V4修正：V3写$240但实际API余额$201.16（-9.37% from $221.96前收盘）
> 当前持仓：ETH 0.0323枚 ($80.61) + USDT $2.61 + 其他币种约$118
> 策略模式：eth（持有ETH，等待趋势通道信号）
**当前日目标：$0.20~$0.60/天（≈年化35-200%）**

---

## 第2层：架构层 — 六大系统 + Agent体系

### 2.0 六大系统总览（V4新增）

| # | 系统 | 代号 | 职责 | 运行方式 | 完成度 |
|---|------|------|------|----------|--------|
| 1 | **Vibe-Trading** | 地基 | 数据引擎+API服务+交易数据同步 | systemd服务(端口8899) | 95% |
| 2 | **Hermes** | 手 | 交易执行+辩论桥接+风控+紧急停止 | Cron定时任务 | 94% |
| 3 | **TraeCode** | 脑 | 规则库+辩论引擎+学习闭环+权重自调 | Cron定时任务 | 93% |
| 4 | **OpenClaw** | 眼 | 心跳监控+异常告警+看门狗+事件总线 | Cron定时任务 | 93% |
| 5 | **WorkBuddy** | 嘴 | 内容生成+多平台发布+视觉海报+反馈闭环 | Cron定时任务 | 96% |
| 6 | **Codex** | 运维 | 管道编排+状态看板+错误重试+Ollama推理 | Cron定时任务 | 96% |

### 2.1 Agent总览

| Agent | 职责 | 所在系统 | 身份/对标 | 协同对象 | 学习频率 |
|:------|:-----|:---------|:---------|:---------|:--------|
| **A1** | 数据采集 | Vibe-Trading | 数据管道(脚本) | A2/A3/A7/A8 | N/A(脚本) |
| **A2** | 选币官 | Vibe-Trading | 精选池管理 | A3/A4/A7 | 每天 |
| **A3** | 牛币官 | TraeCode | 研究涨幅榜根因 | A2/A4/Quant | 每天 |
| **A4/Blade** | 交易执行 | Hermes | 仓位管理者 | A3/Quant | 每天 |
| **A5** | 全系统监督 | OpenClaw | 复盘审查 | 所有Agent | 每天 |
| **A6** | 审计官 | OpenClaw | 偏差率审计 | A3/A4/A5 | 每周2次 |
| **A7** | 舆情官 | TraeCode | 情绪监控 | A3/Commander | 每天 |
| **A8** | 资金官 | Hermes | 大额买入检测 | A3/A4 | 每天 |
| **A9** | 学研官 | Codex | 每日Agent排查+研究 | 所有Agent | 每天 |
| **ZH/Commander** | 决策中枢 | TraeCode | 综合决策+辩论引擎 | 所有Agent | 每天 |
| **Scouter** | 信息侦察 | Codex | 每周一全网工具扫描 | Commander | 每周 |

### 2.2 必备基础技能（所有Agent通用）
| 技能 | 说明 | 状态 |
|------|------|------|
| `post-fix-defense-mechanism` | 修复后防御机制 | ✅ 已有 |
| `zq-web4-system-management` | 系统管理全貌 | ✅ 已有 |
| `zq-web4-socratic-verification` | 苏格拉底验证 | ✅ 已有 |
| `zq-web4-realtime-execution` | 实时执行标准 | ✅ 已有 |

### 2.3 SOUL.md — Agent人格定义
| Agent | 人格 | 权限边界 |
|------|------|----------|
| Hermes(执行) | 铁血执行者 | 下单/平仓/风控/日志，不改策略参数 |
| TraeCode(决策) | 冷静分析师 | 规则匹配/辩论/权重调整，不直接下单 |
| OpenClaw(监控) | 全天候哨兵 | 心跳检测/异常告警，不干预交易 |
| WorkBuddy(传播) | 创意传播者 | 内容生成/发布/反馈，不改交易系统 |
| Codex(运维) | 后勤总管 | 管道编排/重试/告警，不参与决策 |

---

## 第3层：策略层

> **系统所有交易决策以 `NAVIGATION.md` 为唯一策略基准。**

### 3.1 当前策略：ETH趋势通道 v3.1

**一句话策略：** 价格突破近5日最高价→全仓买ETH；跌破近5日最低价→全仓卖ETH锁USDT；持仓后1h收盘自峰值回落≥2%→全仓卖出锁利。

| 维度 | 规则 |
|:-----|:-----|
| 工具 | `tools/trend_bot.py`（每10分钟Cron） |
| 交易对 | ETHUSDT（只做现货，无杠杆） |
| ENTRY | mode=cash 且 价格 > 近120根已收盘1hK线最高价 → 市价全仓买入 |
| EXIT① | mode=eth 且 价格 < 近120根已收盘1hK线最低价 → 全仓卖出（通道破位） |
| EXIT② | mode=eth 且 最新1h收盘价 < 峰值×98% → 全仓卖出（盈利锁定） |
| 通道 | 120根1hK线=5日（只用已收盘K线） |
| 回测 | +27.2%收益，7笔，57%胜率，-3.3%最大回撤 |

**当前状态：** mode=eth，peak_close=$2509.65，channel_high=$2546.66，channel_low=$2431.61

> ⚠️ V4审计修复：swing_engine、mean_rev_bot、grid_bridge已停用（与NAVIGATION.md冲突）

### 3.2 策略数据库架构

```
strategies/__trade_db__/          # V4已创建
├── trades.jsonl                   # 每笔交易记录
├── trade_stats.json               # 统计分析
├── strategy_metrics.json          # 策略表现指标
└── README.md                      # 策略说明

data/trades/
├── trend_state.json               # trend_bot状态文件
├── trend_trades.jsonl             # 原始交易记录
└── daily_profit_log.csv           # 每日盈亏日志
```

---

## 第4层：执行层 — 日/周/月节奏

### 4.1 每日时间线（V4审计验证）

| 时间 | 事件 | Cron状态 | 脚本 |
|:----|:-----|:---------|:-----|
| 05:00 | A1数据采集 | ✅ | coin_pool更新 |
| 05:30 | A2选币+选币池 | ✅ | selector |
| 07:00 | A3牛币官精选 | ✅ | bull_agent |
| 08:00 | A9排查+内容生成 | ✅ | prediction_market + content_loop |
| 09:00 | 经济日历+指标 | ✅ | economic_calendar + economic_indicators |
| 10:00 | 行业扫描 | ✅ | sector_scan |
| 13:00 | A5午检+日报 | ✅ | daily_pnl_report |
| 22:00 | 逐笔复盘+学习闭环 | ✅ | learning_loop + daily_learning_review |
| 23:30 | 自动收盘循环 | ✅ | auto_close_loop |
| 每5分钟 | 管道编排器 | ✅ | pipeline_orchestrator |
| 每10分钟 | trend_bot | ✅ | trend_bot.py（唯一策略） |
| 每5分钟 | 数据同步 | ✅ | sync_trading_data |
| 每5分钟 | 风控检查 | ✅ | risk_manager |
| 每5分钟 | 监控告警 | ✅ | system_monitor + watchdog |
| 每日8/20 | 视觉海报 | ✅ | content_visual_generator |
| 每日3:30 | 数据清理 | ✅ | data_cleanup |

**执行节点（A4/trend_bot）：** 每10分钟一次，全天不间断

### 4.2 Agent学习计划

| Agent | 学习频率 | 学习内容 | 学习来源 |
|:------|:---------|:---------|:---------|
| A3 | 每天 | 当日涨幅榜根因分析 | 币安涨幅榜+新闻 |
| A4 | 每天 | 上一日交易复盘 | trades.jsonl+交易数据库 |
| A5 | 每天 | 系统全链路分析 | 各Agent产出+reviews/ |
| A7 | 每天 | 舆情监控技巧 | 社交媒体趋势 |
| A8 | 每周2次 | 大额资金流动规律 | 链上数据 |
| A9 | 每天 | 新工具/新策略研究 | 全网搜索 |
| ZH | 每天 | 市场+系统+决策复盘 | 综合+rule_learning |

### 4.3 复盘机制

| 频率 | 机制 | 输出 |
|------|------|------|
| 每日22:00 | 逐笔交易复盘 | reviews/review_YYYYMMDD.md |
| 每日22:00 | 学习闭环 | reviews/ + rule_performance.json |
| 每日10:00 | 规则学习 | rule_library优先级自动调整 |
| 每周日 | 策略优化建议 | content_strategy.json |

---

## 第5层：基础设施层 — 工具/文档/第三方

### 5.1 六大系统基础设施

| 系统 | 核心组件 | 位置 |
|------|----------|------|
| Vibe-Trading | vibe-trading服务(端口8899) | /home/ubuntu/.vibe-trading/ |
| Hermes | trend_bot + debate + risk + kill_switch | shared_context/ + zq_web4_trading_system/tools/ |
| TraeCode | rule_library + debate_engine + learning_loop | shared_context/ |
| OpenClaw | heartbeat + system_monitor + watchdog + event_bus | shared_context/ |
| WorkBuddy | content_loop + publisher + visual_generator + feedback | shared_context/ |
| Codex | pipeline_orchestrator + alert_notifier + ollama + dashboard | shared_context/codex/ |

### 5.2 CI/CD 流水线（V4新增）

| 组件 | 状态 | 说明 |
|------|------|------|
| GitHub仓库 | ✅ | ethereum135-lab/ethclaw-Lidaosong |
| CI/CD Workflow | ✅ | 代码检查→蓝图验证→自动部署 |
| GitHub Secrets | ✅ | DEPLOY_HOST + DEPLOY_SSH_KEY + DEPLOY_KNOWN_HOSTS |
| 部署SSH密钥 | ✅ | ed25519，已添加到服务器 |
| 自动部署 | ✅ | push到main分支自动触发 |

### 5.3 第三方平台

| 平台 | 状态 | 说明 |
|:-----|:---------|:-----|
| 币安 | ✅ 已接入 | 现货交易+数据（API仅读取+交易权限） |
| Telegram | ✅ 已修复 | 告警Bot已配置在alert_notifier.py |
| DeepSeek | ✅ 已配置 | API Key在.env，模型deepseek-v4-flash |
| Ollama | ✅ 本地部署 | qwen2.5:0.5b-instruct-q4_0（CPU-only降级方案） |
| CoinGecko | ✅ 可用 | 免费API |
| DexScreener | ✅ 可用 | 链上数据 |
| 飞书 | ⚠️ 未配置 | 需要API权限配置 |
| WeChat | ⚠️ 未配置 | 需要更新 |

### 5.4 文档库架构

```
docs/
├── team_workflow.md              # 团队工作流
├── sub_blueprints/               # 子蓝图（V4待创建）
│   ├── A1_data_collector.md
│   ├── A2_selector.md
│   ├── A3_bull.md
│   ├── A4_blade.md
│   ├── A5_review.md
│   ├── A6_audit.md
│   ├── A7_sentinel.md
│   ├── A8_fund.md
│   ├── A9_research.md
│   └── ZH_commander.md
config/
├── ZQ_MASTER_BLUEPRINT_V4.md     # 本文件
├── IRON_RULES.md                  # 铁律
NAVIGATION.md                      # 策略基准
SOUL.md                            # Agent人格定义
audit/                             # 审计档案库
├── index.json                     # 索引
└── audit_YYYYMMDD_*.json          # 审计记录
```

### 5.5 共享上下文目录结构

```
/home/ubuntu/shared_context/
├── trades/                        # 交易数据
│   ├── positions.json             # 当前持仓
│   ├── total_asset.json           # 总资产（source=binance_api_real_balance）
│   └── order_history.json
├── strategy/                      # 策略输出
│   └── debate_result.json         # 辩论结果
├── risk/                          # 风控
│   ├── risk_status.json
│   └── stop_order_audit.json
├── macro/                         # 宏观
│   ├── fear_greed.json
│   ├── market_regime.json
│   ├── rule_library.json
│   └── dashboard.json
├── fx/                            # 外汇
├── futures/                       # 期货
├── content/                       # 内容
│   └── visual/                    # 视觉海报
├── reviews/                       # 复盘
├── strategies/__trade_db__/       # 交易数据库
├── audit/                         # 审计档案库
├── codex/                         # 运维
│   ├── pipeline_orchestrator.py
│   ├── pipeline_dashboard.py
│   ├── alert_notifier.py
│   ├── task_runner.py
│   └── ollama_inference.py
├── monitor/                       # 监控
│   ├── heartbeats.json
│   └── vibe_health_history.json
├── logs/                          # 日志
└── reports/                       # 报告
    └── pipeline_dashboard.html
```

---

## 第6层：风控层 — 11道风控门（V4明确）

| # | 风控门 | 规则 | 状态 |
|---|--------|------|------|
| 1 | 单笔亏损 | ≤总资×1% | ✅ |
| 2 | 保证金下限 | ≥10% | ✅ |
| 3 | 连亏熔断 | 连续3天不达标→全链审查 | ✅ |
| 4 | 止损执行 | DSL止损开启 | ✅ |
| 5 | 紧急停止 | kill_switch.py守护 | ✅ |
| 6 | 持仓限制 | 策略决定 | ✅ |
| 7 | 相关性闸门 | 超限禁止开仓 | ✅ |
| 8 | 经济事件 | S/A/B级前60分钟禁开仓 | ✅ |
| 9 | 冷却期 | 合约4小时/期货48小时 | ✅ |
| 10 | 每日开仓上限 | 合约5次/天 | ✅ |
| 11 | 辩论HOLD | 轻仓试探×0.70, 止损收紧10% | ✅ |

---

## 执行优先级（V4更新）

| 优先级 | 任务 | 说明 | 进度 | 状态 | 完成日期 |
|:------|:-----|:-----|:----|:----|:--------|
| ✅ P0 | 蓝图V4资金修正 | $240→$201.16(API实查) | 100% | ✅ | 2026-09-09 |
| ✅ P0 | 策略冲突修复 | 停用swing/mean_rev/grid_bridge | 100% | ✅ | 2026-09-09 |
| ✅ P0 | 交易数据库 | strategies/__trade_db__/已创建 | 100% | ✅ | 2026-09-09 |
| ✅ P0 | 审计档案库 | audit/已创建+首条审计归档 | 100% | ✅ | 2026-09-09 |
| ✅ P0 | total_asset同步 | shared_context/trades/total_asset.json | 100% | ✅ | 2026-09-09 |
| ✅ P0 | CI/CD流水线 | GitHub Actions三Job流水线 | 100% | ✅ | 2026-09-09 |
| ✅ P0 | Codex管道编排 | 错峰调度+编排器+看板+重试+告警 | 100% | ✅ | 2026-09-09 |
| ✅ P1 | Telegram告警 | alert_notifier.py已配置Bot | 100% | ✅ | 2026-09-09 |
| ✅ P1 | Ollama本地推理 | qwen2.5:0.5b + 封装API | 100% | ✅ | 2026-09-09 |
| ✅ P1 | 视觉内容生成 | SVG海报3类(行情/辩论/风控) | 100% | ✅ | 2026-09-09 |
| ✅ P1 | 六大系统审计 | 全局对照+三排查三验证 | 100% | ✅ | 2026-09-09 |
| ⏸ P2 | 子蓝图文档 | A1-A9 + ZH子蓝图 | 0% | ⏸ 待创建 | — |
| ⏸ P2 | 飞书接入 | 需要API权限配置 | 0% | ⏸ 待配置 | — |
| ⏸ P2 | 工具分类清理 | 71个tools/脚本分类归档 | 0% | ⏸ 待排期 | — |
| ⏸ P3 | 旧文档清理 | 铁律九：A→B替代时删除A | 0% | ⏸ 待排期 | — |
| ⏸ P3 | 策略分析统计 | 从trades.jsonl提取规律 | 0% | ⏸ 待排期 | — |

---

## V3→V4 变更日志

| 变更项 | V3 | V4 |
|--------|-----|-----|
| 资金 | $240 | $201.16（API实查） |
| 日目标 | $0.24~$0.72 | $0.20~$0.60 |
| 策略 | 网格(已废弃) | ETH趋势通道v3.1 |
| 架构 | Agent体系(A1-A9) | 六大系统+Agent体系 |
| CI/CD | 无 | GitHub Actions完整流水线 |
| 管道编排 | 无 | Codex 5阶段编排器 |
| 本地推理 | 无 | Ollama qwen2.5:0.5b |
| 视觉内容 | 无 | SVG海报3类 |
| 交易数据库 | 待建 | strategies/__trade_db__/已创建 |
| 审计档案 | 无 | audit/已创建 |
| Telegram | 标记失效 | 已修复(Bot配置在alert_notifier) |
| 策略冲突 | swing+mean_rev+grid并行 | 仅trend_bot(符合NAVIGATION.md) |

---

> **核心信念：** 在AI Agent世界里没有不可能的，只有你想不到的没有办不到。
> 每一天0.2%，不是等系统"完善"了才盈利——是从今天就开始。
> 今天亏了就是今天亏了——复盘找原因，明天改。
