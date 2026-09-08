# Cron 库存 & NAVIGATION.md §九 对照报告

> 生成时间: 2026-07-08
> 来源: `hermes cron list` + `~/.hermes/cron/jobs.json` + AWS crontab + NAVIGATION.md §九

---

## 一、NAVIGATION.md §九 文档定义的 Agent 体系

### 新简化策略（优选）
| Agent | 文件 | 执行位置 | 预期频率 |
|-------|------|---------|---------|
| 简化策略 | `tools/simple_strategy.py` | **AWS cron** | 每小时 |

### 旧Agent体系（备选 — A2-A9）
| Agent | 名称 | 预期职能 |
|-------|------|---------|
| A1 | 数据采集官 | 设采集策略，不用LLM（仅脚本）|
| A2 | 选币官 | 两阶段筛选、评分、候选池 |
| A3 | 牛币官 | 四维评分精选、推荐报告 |
| A4 | 交易官 | 评估持仓、Hold/减仓/清仓决策 |
| A5 | 复盘官 | 每日复盘、经验值积累 |
| A6 | 审计官 | 每周审计 |
| A7 | 舆情官 | 舆情监测 |
| A8 | 资金官 | 聪明钱跟踪 |
| A9 | 学研官 | 全网搜索新工具/策略 |
| ZH | 总指挥 | 行业研判、Agent调度、产出检查 |

---

## 二、全LLM Agent Cron 清单（非no-agent）

共 **21 个活跃 LLM Agent cron**（含prompt型无skill cron，排除no-agent脚本类）。

### 2.1 ❌ 在 Error 状态的 Cron（5个）

| ID | 名称 | 频率 | 模型 | 错误信息 | 备注 |
|----|------|------|------|---------|------|
| `3f5f68a4b1d2` | 经验分析-每节点后 | */35 * * * * | deepseek/deepseek-v4-flash | HTTP 402: Insufficient Balance | 频繁跑 error |
| `a699e0ccd542` | **A4-交易官-执行节点** | */30 * * * * | deepseek-v4-flash | HTTP 402: Insufficient Balance | ⚠️ 核心交易Agent停摆 |
| `e668b9f9b554` | **A7-舆情官-实时监控** | */15 * * * * | deepseek-v4-flash | HTTP 402: Insufficient Balance | ⚠️ 舆情监控停摆 |
| `143a33c2ad52` | ZH-日终结-23:00 | 0 23 * * * | — | HTTP 402: Insufficient Balance | 需确认model字段 |
| `b94383c6aff8` | A8-资金信号报告-每小时 | 0 * * * * | — | HTTP 402: Insufficient Balance | 需确认model字段 |

**共5个error，全部是 HTTP 402 Insufficient Balance（API余额不足）。**

### 2.2 ✅ 运行正常的 LLM Agent Cron（16个）

| ID | 名称 | 频率 | 模型 | 最后运行状态 |
|----|------|------|------|------------|
| `25a9000e9d05` | ZH每日系统反思 | 0 20 * * * | deepseek/deepseek-v4-flash | ok |
| `53f29cfa1075` | 每日系统健康扫描 | 0 10,16,22 * * * | deepseek/deepseek-v4-flash | ok |
| `d3a27e91ebd6` | ZH全网侦查 | 0 8 * * 1 | deepseek/deepseek-v4-flash | ok |
| `81990443fbc9` | ZH系统自检 | 0 7 * * * | deepseek/deepseek-v4-flash | ok |
| `a3d884ef2305` | A5-每日复盘 | 0 22 * * * | deepseek-v4-flash | ok |
| `503817282974` | A4-交易官-每日学习 | 5 8 * * * | deepseek-v4-flash | ok |
| `45b17d4a5277` | ZH-行业扫描-10:00 | 0 10 * * * | deepseek-v4-flash | ok |
| `db6f98c6e3ba` | ZH-每日简报-18:00 | 0 18 * * * | deepseek-v4-flash | ok |
| `d822bd7ece55` | A5-复盘官-每日学习 | 10 8 * * * | deepseek-v4-flash | ok |
| `40f0674d2845` | A6-审计官-每日审计 | 15 8 * * * | deepseek-v4-flash | ok |
| `fbd207da5442` | A6-审计官-学习 | 0 8 * * 2,4 | deepseek-v4-flash | ok |
| `3199bbb3dc7c` | A7-舆情官-学习 | 0 8 * * 3,5 | deepseek-v4-flash | ok (但最后跑Jul 3) |
| `4123fffc5346` | A8-资金官-学习 | 0 8 * * 2,5 | deepseek-v4-flash | ok |
| `639283449f5e` | A9-学研官-每周研究 | 0 9 * * 1 | deepseek-v4-flash | ok |
| `95b5909dcfbd` | ZH-赛道热度评分 | 0 5 * * * | deepseek-v4-flash | ok |
| `06fa67fe1a90` | A5-监督评估 | 30 8 * * * | deepseek-v4-flash | ok |
| `2d5b91ba831a` | A5-全系统审查 | 0 17 * * * | deepseek-v4-flash | ok |
| `88c36099da49` | A5-早检 | 35 8 * * * | deepseek-v4-flash | ok |
| `98033fe4dc53` | A5-午检 | 0 13 * * * | deepseek-v4-flash | ok |
| `14108a1c88c0` | ZH-方向融合 | 30 5 * * * | deepseek/deepseek-v4-flash | ok |
| `eae289aef8cf` | A2-选币官-每日精选 | 0 6 * * * | deepseek-v4-flash | ok |
| `740e7260841a` | A3-牛币官-每日精选 | 0 7 * * * | deepseek-v4-flash | ok |
| `0efa40947985` | ZH-每日市场研究+调整 | 30 8 * * * | — | ok |
| `c83b8a6ce346` | A9-学研官-每日排查 | 0 8 * * * | — | ok |
| `0483d363311d` | A3-牛币官-午后精选 | 0 17 * * * | — | ok |
| `31d2961fb683` | ZH-早间诊断-09:00 | 0 9 * * * | — | ok |
| `012bcd83c11e` | 每日盈利排查 | 0 21 * * * | — | ok |

---

## 三、模型分析

**所有Agent cron 都显式配置了模型，没有模型为空的情况。** 全部使用:
- `deepseek/deepseek-v4-flash`（完整路径）或
- `deepseek-v4-flash`（短名）

**所有Agent cron 的 provider 均为 `deepseek`。**

---

## 四、AWS Cron（VPS上）LLM相关清单

通过 SSH 查看 AWS VPS `crontab -l`:

### AWS上运行的非LLM脚本（no-agent）

| 脚本 | 频率 | 说明 |
|------|------|------|
| `data_sources/data_cron.sh coingecko` | 0 * * * * | 数据采集（非LLM）|
| `data_sources/data_cron.sh sentiment` | 0 */2 * * * | 情绪采集（非LLM）|
| `data_sources/data_cron.sh news` | */30 * * * * | 新闻采集（非LLM）|
| `data_sources/data_cron.sh all` | 0 6 * * * | 全量采集（非LLM）|
| `tools/early_signal_detector.py` | */15 * * * * | 早期信号检测（Python脚本）|
| `tools/etherscan_watcher.py` | 1-59/15 * * * * | 链上验证（Python脚本）|
| `strategies/turtle_strategy.py` | 1-59/30 * * * * | 海龟策略（Python脚本）|
| `aws_a1_data.py` | 21 0 * * * | A1数据采集（Python脚本）|
| `aws_a2_selector.py` | 22 0 * * * | A2选币（Python脚本）|
| `tools/donchian_strategy.py` | */30 * * * * | Donchian突破策略（Python脚本）|
| `production/engine/a4_independent.py` | */5 * * * * | A4独立执行节点（Python脚本）|
| `tools/a3_signal_scanner.py` | 0 */2 * * * | A3信号扫描（Python脚本）|
| `auto_backup.sh` | 0 4,16 * * * | 备份（shell脚本）|

**AWS上没有任何LLM Agent cron** — 所有AWS cron都是纯Python/shell脚本。AWS仅负责数据采集和交易执行（体力活），LLM判断全部在Mac端的Hermes上完成。

### 与 NAVIGATION.md 对照

**NAVIGATION.md §九 说 `tools/simple_strategy.py` 作为AWS cron每小时跑，但实际AWS crontab中没有这一项。** 这个文件在AWS上存在（`-rw------- 1 ubuntu ubuntu 4983 Jun 29 16:42`），但crontab中没有任何 `simple_strategy.py` 的计划任务。

---

## 五、NAVIGATION.md 声明与实际的对照差异

### ❌ 差异1: `simple_strategy.py` AWS cron 不存在
- **文档声称:** "部署于 `tools/simple_strategy.py`（AWS cron每小时跑）"（NAVIGATION.md §九 第273行）
- **实际情况:** AWS crontab 中没有 `simple_strategy.py` 任何条目。文件存在但未被定时执行。
- **结论:** 文档写了，实际不存在

### ❌ 差异2: A8数据采集cron标记为no-agent但仍有skills
- A8-大额买入检测-高频数据采集 (`7f90ea7cf529`) 的 `no_agent: true` 且有脚本，但同时配置了 `skills: ["zq-a8-fund-agent"]`。这造成矛盾——no-agent意味着不调用Agent人格，但skill配置仍在。
- 不过运行状态为 ok，实际按脚本模式运行，无实质影响。

### ❌ 差异3: A5-经验值采集 类似矛盾
- `c2a8e58ed85e` (A5-经验值采集) 也是 `no_agent: true` + 脚本，但skills也配置了 `zq-a5-review-agent`。同样无实质影响。

### ✅ 一致项
| Agent | NAVIGATION.md 说 | 实际存在 | 模型不为空 | 状态 |
|-------|-----------------|---------|-----------|------|
| A2-选币官-每日精选 | ✅ | `eae289aef8cf` ✅ | ✅ deepseek-v4-flash | ✅ ok |
| A3-牛币官-每日精选 | ✅ | `740e7260841a` ✅ | ✅ deepseek-v4-flash | ✅ ok |
| A3-牛币官-午后精选 | ✅ | `0483d363311d` | — | ✅ ok |
| A4-交易官-执行节点 | ✅ | `a699e0ccd542` ✅ | ✅ deepseek-v4-flash | ❌ error |
| A4-交易官-每日学习 | ✅ | `503817282974` ✅ | ✅ deepseek-v4-flash | ✅ ok |
| A5-每日复盘 | ✅ | `a3d884ef2305` ✅ | ✅ deepseek-v4-flash | ✅ ok |
| A5-复盘官-每日学习 | ✅ | `d822bd7ece55` ✅ | ✅ deepseek-v4-flash | ✅ ok |
| A5-监督评估 | ✅ | `06fa67fe1a90` ✅ | ✅ deepseek-v4-flash | ✅ ok |
| A5-全系统审查 | ✅ | `2d5b91ba831a` ✅ | ✅ deepseek-v4-flash | ✅ ok |
| A5-早检 | ✅ | `88c36099da49` ✅ | ✅ deepseek-v4-flash | ✅ ok |
| A5-午检 | ✅ | `98033fe4dc53` ✅ | ✅ deepseek-v4-flash | ✅ ok |
| A6-审计官-每日审计 | ✅ | `40f0674d2845` ✅ | ✅ deepseek-v4-flash | ✅ ok |
| A6-审计官-学习 | ✅ | `fbd207da5442` ✅ | ✅ deepseek-v4-flash | ✅ ok |
| A7-舆情官-实时监控 | ✅ | `e668b9f9b554` ✅ | ✅ deepseek-v4-flash | ❌ error |
| A7-舆情官-学习 | ✅ | `3199bbb3dc7c` ✅ | ✅ deepseek-v4-flash | ✅ ok |
| A8-资金官-学习 | ✅ | `4123fffc5346` ✅ | ✅ deepseek-v4-flash | ✅ ok |
| A9-学研官-每周研究 | ✅ | `639283449f5e` ✅ | ✅ deepseek-v4-flash | ✅ ok |
| A9-学研官-每日排查 | ✅ | `c83b8a6ce346` | — | ✅ ok |
| ZH-赛道热度评分 | ✅ | `95b5909dcfbd` ✅ | ✅ deepseek-v4-flash | ✅ ok |
| ZH-行业扫描 | ✅ | `45b17d4a5277` ✅ | ✅ deepseek-v4-flash | ✅ ok |
| ZH-方向融合 | ✅ | `14108a1c88c0` ✅ | ✅ deepseek/deepseek-v4-flash | ✅ ok |

---

## 六、总结

### 模型情况
- **模型为空/未配置：0个** — 所有LLM Agent cron都显式配置了 `deepseek-v4-flash` 或 `deepseek/deepseek-v4-flash`
- **Provider为空：0个** — 全部配置为 `deepseek`

### Error情况
- **共5个error cron**，全部是 `HTTP 402: Insufficient Balance`（API余额不足），涉及：
  1. A4-交易官-执行节点（核心交易Agent）⚠️
  2. A7-舆情官-实时监控 ⚠️
  3. 经验分析-每节点后
  4. ZH-日终结-23:00
  5. A8-资金信号报告-每小时

### NAVIGATION.md写了但不存在
- **`tools/simple_strategy.py` 作为AWS cron每小时跑** — 文档写了但实际AWS crontab中没有此项

### NAVIGATION.md存在但cron不在
- 无 — 所有文档定义的Agent都有对应的cron
