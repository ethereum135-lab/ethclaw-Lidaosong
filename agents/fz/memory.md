# ZQ-FZ 总控记忆

## 2026-05-09 08:30 决策记录

### 物理验证结果
- **余额**: $360.40 (Binance API via AWS, 实时验证)
- **P&L**: -$69.60 (-16.19% vs $430)
- **持仓**: DASH $124.63 (34.6%) / LUNC $114.84 (31.9%) / BONK $67.78 (18.8%) / CHZ $44.12 (12.2%) / USDT $9.03 (2.5%)
- **BTC**: $80,195 (+0.36%) — 市场平稳
- **引擎**: Mac PAUSED (~68h), AWS ACTIVE (每30分钟)
- **FK Veto**: 之前RL3触发(TRX 63.7%) → TRX已卖出 → 已清除veto
- **BHZ**: 最后检查05-07，缺05-08/05-09检查

### P0修复
1. ✅ FK veto清除 — TRX已卖，当前持仓无超标
2. ✅ 创建 agents/fz/ 目录 + ident.md + memory.md

### P1待办
- BHZ缺失05-08/05-09检查 → 需排查cron
- 当前持仓策略评估
- Mac引擎作为备份恢复
- 连续亏损根因：E3误触退出 + 评分系统未区分趋势质量

### 系统状态
- AWS crontab: */30 engine + */15 early_signal + */15 etherscan + 每小时CoinGecko/sentiment/news
- 数据系统采集了但引擎未集成（BHZ #3 未解决）
- 回测亏损无后续决策（BHZ #2 未解决）
- Scouter从未输出（BHZ #1 未解决）

## 2026-05-10 08:30 决策记录

### 物理验证结果
- **余额**: $332.75 (Binance API via AWS, 08:30 CST实时)
- **P&L**: -$97.25 (-22.62% vs $430)
- **持仓**: ENA $284.38 (85.5%) / CHZ $43.84 (13.2%) / USDT $3.00 (0.9%) / 尘埃 $1.53 (0.5%)
- **BTC**: ~$80,793 (+0.68%) — 市场平稳
- **引擎**: AWS Active (162节点), Mac PAUSED (~89h)
- **FK Veto**: RL2+RL3触发。FZ更新了数据(05:38 FK数据过时: ICP→ENA已转换)
- **BHZ**: 11闭环 / 2待评估

### 交易链: ICP→ENA转换 (05:38→08:30)
- 05:38 FK检查: ICP $289.76 (86.1%)
- 08:30 AWS节点: ICP E4评分骤降(88.4→61.4) → 卖出ICP@$3.511 → USDT $288.32
- 立即全仓买入ENA (#34, 评分71.8) @ $0.1306 → 2184.68 ENA = $284.38
- ENA仅排名#34 — Top 5 (BNB/ZEC/DYM/SAHARA/XLM)全未通过6AND过滤

### 🔴 核心发现: 引擎无单币仓位上限
- `grep max_position_pct` → 无结果。引擎无单币仓位上限
- 当只有1个候选通过过滤时 → ratios=[1.0] → 全仓进1个币
- 模式: ICP 86.1% → ENA 85.5% → 下一个还是85%+
- `min_enter_score=55, entry_min_per_trade=5`

### P0执行
1. ✅ FK veto更新 — 反映当前ENA 85.5%现实
2. 🔴 引擎缺max_position_pct (单币仓位上限) — 需在THRESHOLDS加 `"max_alloc_pct": 0.5`
3. ⚠️ ENA -2.03% 24h已跌 — $284×(跌10%→$28损失→$304触发RL5)

### P1
4. Top 5全不过滤 — 6AND条件可能过严
5. Mac引擎PAUSED 89h — 保持暂停(AWS活跃)
6. 83种尘埃币积累 — 不影响交易，但需定期清理

### 给老李的建议
- ENA 85.5%集中 → 等待引擎E4/E3退出或手动减仓
- 代码修复: 生产引擎加 `max_alloc_pct: 0.5` (单币最多50%)
- Top 5不过滤根因需排查: 是趋势方向(-1)导致还是其他条件?

## 2026-05-11 08:42 决策记录

### 物理验证结果
- **余额**: $329.39 (Binance API via AWS, 08:31 CST实时)
- **P&L**: -$100.61 (-23.40% vs $430)
- **持仓**: SOL $107.16 (32.5%) / LINK $62.64 (19.0%) / STRK $58.71 (17.8%) / CHZ $44.05 (13.4%) / DOGE $41.45 (12.6%) / UNI $4.87 (1.5%) / USDT $9.13 (2.8%)
- **BTC**: $81,803 (+1.39% 24h) — 市场平稳偏多
- **F&G**: 48 (Neutral)
- **引擎**: AWS ACTIVE (每30分钟), Mac PAUSED (~118h)
- **FK Veto**: ALL CLEAR — 5条红线全部通过 (FK-20260511-0741)
- **BHZ**: 17期全部闭环(11绿/0红), Scouter首次运行✅
- **Scouter**: ✅ 首次成功运行！147行，2个推荐+5个参考

### 引擎节点状态（UTC时间）
| 节点 | USDT | 动作 |
|:---|:---:|:---|
| 22:00 | $218.75 | 6AND通过0，无可进场 |
| 22:30 | $9.13 | 买入进场（花$209）→ USDT降至$9.13 |
| 23:00 | $9.13 | HOLD — 无出场信号 |
| 23:30 | $9.13 | HOLD — 无出场信号 |
| 00:00 | $9.13 | HOLD — 无出场信号 |
| 00:30 | $9.13 | HOLD — USDT<$10跳过进场 |

### 🟢 P0已执行

**P0-1: max_alloc_pct = 0.5 添加到引擎** ✅
- **问题**: 引擎THRESHOLDS缺单币仓位上限。历史：ICP 86.1% → ENA 85.5%，全仓进1币
- **根因**: `max_positions==1` 时 `ratios=[1.0]` — 100%资金进1币
- **修复**: 
  - THRESHOLDS 加 `"max_alloc_pct": 0.5` (line 92)
  - 分配逻辑加 `min(r, max_alloc_pct)` 约束 (lines 882-889)
  - root+production+全部同步到AWS
  - MD5验证通过: `e387376cc23e742b31e3d65ed67a23cd`
  - 编译验证通过: Mac ✅ / AWS ✅

**P0-2: root←production同步** ✅
- 之前46行diff，已消除至0行
- MD5三方一致: Mac root = Mac production = AWS production

### 🟡 P1评估

**1. USDT死锁 ($9.13 < $10) — 等待自然退出，不干预**
- 原因: 22:30节点花$209买入持仓，属正常行为
- 当前6个持仓无出场信号，引擎在HOLD等待
- 不降低entry_usdt_min: $5买入会触发MIN_NOTIONAL(-1013)
- 下一个自然卖出会释放USDT，恢复正常循环
- **决策: 观察，不手动干预**

**2. Scouter首次运行 — 2个推荐评估**
- **hftbacktest** ✅有用: 专业回测引擎 → 填补策略验证缺口。中难度(300-500行)，建议排P2
- **CryptoTradingAgents** ✅有用: 7+数据源 → 填补NBZ数据多样性。低难度(200行)，建议排P1
- **建议**: CryptoTradingAgents本周集成(数据源插件给NBZ)，hftbacktest下周评估

**3. NBZ findings 过期 (05-08)**
- 当前NBZ数据3天未更新
- 需要手动触发一轮，或修复cron

### 系统健康
- 🔴 无P0问题
- 🟡 USDT死锁 (观察，自然解)
- 🟡 NBZ过期 (需手动触发)
- 🟢 FK ALL CLEAR | BHZ全闭环 | Scouter首跑
- 🟢 P1保护 + direction_judger + max_alloc_pct 全部在岗

### 关键保护状态（AWS引擎验证）
| 保护 | 行号 | 状态 |
|:---|:---:|:---:|
| P1保护 `and not is_new` | line 948 | ✅ |
| direction_judger 4h趋势抑制 | line 983, 998 | ✅ |
| max_alloc_pct 单币上限50% | line 92, 882-889 | ✅ 本次新增 |
| entry_usdt_min=$10 | line 81 | ✅ |
| entry_min_per_trade=$5 | line 82 | ✅ |
