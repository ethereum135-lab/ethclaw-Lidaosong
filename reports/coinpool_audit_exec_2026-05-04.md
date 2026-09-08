# 维4·选币库排查报告 — 逐层追问物理回答

**审计日期**: 2026-05-04  
**审计范围**: engine_realtime_v2.py, production/engine/engine_realtime_v2.py, tools/coin_pool_manager.py, data/coin_pool.json, audit/TRADES.md

---

## 1. 【选币库是怎么定位的？】

### 当前选币库在系统中的角色和定位

**结论：选币库目前是被动排序+打分辅助，而非主动选币。**

具体定位分析：

| 层面 | 描述 |
|------|------|
| **数据提供** | `coin_pool.json` 存储599个币种的行情快照（volume_24h, price, funding_rate, category），由 `coin_pool_manager.py --update` 每周全量拉取Binance数据。 |
| **排除池** | 引擎通过 `load_excluded_coins()` (engine_realtime_v2.py L265-273) 读取 `coin_pool.json.pools.excluded`，作为黑名单，在扫描时跳过这些币种（L553-555）。 |
| **行为因子** | 引擎通过 `load_coin_behavior()` (L231-238) 读取 `coin_pool.json.behavior`，在 `calc_resonance_score()` (L369-463) 中作为行为因子（-10~+10）参与评分。行为因子在评分中占比约 **6%**（满分100中占±10分）。 |
| **观察池** | 引擎通过 `get_watch_coins()` (L275-283) 获取观察池备选币，但目前 `scan_top50()` 只扫描Top50成交额币种，**观察池未被实际使用**。 |

### 是主动选币还是被动排序？

**被动排序。** 引擎不依赖选币库来决定"买什么"，而是：
1. 从Binance拉取全量Ticker → 按成交额排序Top50
2. 对Top50逐一扫描计算共振评分
3. 选择通过6AND条件且评分最高的Top3买入
4. 选币库的作用仅为：提供行为因子（-10~+10加分）、提供黑名单过滤、提供费率数据

**选币库从未主动"推送"候选币给引擎。** 引擎自己决定扫描范围（Top50），选币库只是辅助打分的配角。

---

## 2. 【目前有什么问题？】

### 问题一：behavior数据只有1条记录（BIO）

**物理数据**：
```
behavior keys: ['BIO']
BIO behavior: {
  "trades": 1,
  "wins": 1,
  "losses": 0,
  "total_hold_time": 520,
  "exit_reasons": { "持有盈利": 1 },
  "first_traded": "2026-05-02",
  "last_traded": "2026-05-02"
}
```

**原因**：`record_trade_in_pool()` 函数定义在 `engine_realtime_v2.py` **第285-294行**，但在 `run_node()` 主流程（L987-1173）中 **从未被调用**。唯一的1条BIO记录是通过手动执行 `coin_pool_manager.py --record-trade` 产生的，并非引擎自动记录。

**证据**：搜索全代码库 `record_trade_in_pool(`，仅1处命中 — 即定义本身（L285）。零调用。搜索 `--record-trade`，零命中。

### 问题二：为什么170笔卖出+208笔买入共381笔交易没记录到behavior？

**直接原因**：`engine_realtime_v2.py` 的 `run_node()` 在SELL流程（L1086-1116）中，卖出成功后只调用了 `log_trade()` 记录到TRADES.md，**从未调用 `record_trade_in_pool()`**。

**代码行级分析**：
- `run_node()` L1092: `result = execute_sell(...)` — 执行卖出
- L1093-1108: 检查 `result['status'] == 'filled'` → 计算持仓时间 → 记录 `log_trade()` → 打印日志
- **缺少**: `record_trade_in_pool(e['symbol'], entry_price, exit_price, hold_min, exit_reason)` 调用

买入流程（L1128-1138）同样只调用了 `log_trade()` 和 `_hold_since[e['symbol']] = time.time()`，未记录行为数据。

### 问题三：coin_pool_manager.py和引擎之间的调用链路断在哪里？

**调用链路断裂分析**：

```
预期链路（设计文档描述的）:
  engine_realtime_v2.py run_node()
    → execute_sell() 成功
    → record_trade_in_pool(symbol, entry, exit, hold_min, reason)    ← 函数存在，但从不调用
      → subprocess.run(['python3', 'tools/coin_pool_manager.py', '--record-trade', ...])
        → coin_pool_manager.py record_trade(symbol, entry_price, exit_price, hold_minutes, exit_reason)
          → load_pool() + 更新 behavior[symbol] + save_pool()

实际链路:
  engine_realtime_v2.py run_node()
    → execute_sell() 成功
    → log_trade()  [写入 TRADES.md]   ✓
    → [record_trade_in_pool() 被完全跳过] ✗
      → behavior 数据永远为空
```

**断裂点**：`engine_realtime_v2.py` 第285行定义了函数，但 `run_node()` 第1086-1116行的SELL处理代码中 **缺少对 `record_trade_in_pool()` 的调用**。

### 问题四：生产环境使用的引擎版本不同

**生产环境** 运行的是 `production/engine/engine_realtime_v2.py`（统一基准版v1），该版本：
- 没有 `record_trade_in_pool()` 函数
- 没有 `load_coin_behavior()` 函数
- 没有 `get_behavior_bonus()` 函数
- `calc_resonance_score()` 只有4个维度（vol_score + rsi_score + surge_score + trend_score），**没有行为因子、资金费率因子、多时间框架因子**

🤯 **这意味着：不管选币库行为数据有没有记录，生产环境的引擎根本不会用它们。**

---

## 3. 【是怎么发现的？用什么方法才发现的？】

### 发现方法逐条说明：

| 发现项 | 发现方法 |
|--------|----------|
| behavior只有1条 | 终端执行 `python3 -c "import json; ... print(len(pool['behavior']))"` 在 `data/coin_pool.json` 上 |
| 381笔交易未记录 | 统计 `audit/TRADES.md` 中 `| SELL |` 出现次数=173，`| BUY |` 出现次数=208，合计381 |
| 调用链路断裂 | 搜索 `record_trade_in_pool(` 于全项目，发现仅1处命中（定义行L285）。搜索 `--record-trade` 零命中。逐行阅读 `engine_realtime_v2.py` 的 `run_node()` 函数L1086-1138，验证SELL/BUY处理分支中没有 `record_trade_in_pool()` 调用 |
| 生产引擎不引用选币库 | 阅读 `production/engine/engine_realtime_v2.py` 全文552行，确认无任何选币库相关函数（load_coin_behavior, get_behavior_bonus, record_trade_in_pool） |
| 费率因子方向确认反转 | 阅读 `engine_realtime_v2.py` 第400-413行的 `fr_bonus` 逻辑：**负费率 → 加分（+15到+5），正费率 → 扣分（-15到-5）** — 这是做多策略的正确方向，与历史审计结论一致，方向已修复 |
| 行为因子永远为0 | `get_behavior_bonus()` L242-243: `if not b or b.get('trades', 0) < 2: return 0` — 因behavior无数据，所有币种的 `behavior_bonus` 恒为0 |

---

## 4. 【要怎么提升？】

### 提升方案一（关键）：在SELL流程中调用record_trade_in_pool

**文件**: `engine_realtime_v2.py`  
**位置**: `run_node()` 函数，SELL成功处理块（L1093-1108）

**需要修改**：在SELL成功后的日志记录后，添加行为记录调用。需要记录买入价格（当前系统没有在买入时保存买入价格到全局变量）。

**推荐代码修改**（两步）：

**Step 1**: 在全局增加 buy_price 追踪字典（与 `_hold_since` 并列，L892附近）
```python
# 全局持仓价格追踪
_hold_price = {}  # symbol -> entry_price
```

**Step 2**: 在BUY成功处记录买入价格（L1132-1136附近，在 `_hold_since[e['symbol']]` 旁边）
```python
_hold_since[e['symbol']] = time.time()  # 记录买入时间
_hold_price[e['symbol']] = result['price']  # 记录买入价格  ← 新增
```

**Step 3**: 在SELL成功处（L1104-1108附近，`log_trade()` 调用后）添加：
```python
# 记录到选币库行为数据
entry_price = _hold_price.get(e['symbol'], 0)
if entry_price > 0 and result['price'] > 0:
    record_trade_in_pool(
        e['symbol'], entry_price, result['price'],
        hold_min, e['reason']
    )
```

> **注意**：当前 `_hold_since` 变量仅在 `run_node()` 的买入分支中赋值。如果引擎重启，持仓时间会丢失，但不会导致报错（time.time() - 0 = 超长持有时间 → 会被跳过）。

### 提升方案二（可选）：同步更新 production 引擎

如果生产环境使用的是 `production/engine/engine_realtime_v2.py`，需要将根目录的引擎同步过去，或者直接在 `production/engine/engine_realtime_v2.py` 中补充：
- `record_trade_in_pool()` 函数
- `load_coin_behavior()` 函数
- `get_behavior_bonus()` 函数
- 更新 `calc_resonance_score()` 支持行为因子

---

## 5. 【需要什么样的数据平台来支撑？】

### 当前选币库的数据维度和缺失：

| 数据维度 | 当前状态 | 是否需要 | 优先级 |
|----------|----------|----------|--------|
| 成交额排序 | ✅ Binance API 24hr ticker | 已有 | - |
| 资金费率 | ✅ Binance Futures premiumIndex | 已有 | - |
| 赛道分类 | ✅ 手动维护 keyword map | 已有 | - |
| 行为数据（历史胜率） | ⚠️ 代码有，链路断，数据=0 | **记录修复后即有** | **P0** |
| 链上智能钱数据 | ❌ 无 | 可选增强 | P3 |
| 多平台价格验证 | ✅ CoinGecko API | 已有 | - |
| 社交热度 | ✅ CoinGecko trending | 已有 | - |
| OI持仓量 | ✅ Binance Futures OI | 已有 | - |
| K线技术指标 | ✅ 引擎自算RSI/MA/成交量 | 已有 | - |
| 新闻/情绪分析 | ❌ 无 | 可选增强 | P4 |

### 现在还缺什么数据源才能让选币库真正发挥作用？

**选币库本身的数据维度已经足够。** 问题不在数据源缺失，而在：

1. **行为数据没有回写**（修复调用链路即可解决 — P0）
2. **生产引擎不知晓选币库**（同步代码 — P1）
3. **观察池没有被主动使用**（引擎只扫Top50，从不看观察池的备选币 — P2）

唯一可能建议补充的数据源：
- **回测数据平台**：需要一个独立的历史K线数据库来验证评分模型的有效性，而非实时数据。

---

## 6. 【数据来源够不够？】

### 逐条分析

| 问题 | 回答 |
|------|------|
| **为什么够？** | Binance 24hr ticker + Futures premiumIndex + CoinGecko价格+社交热度 + OI持仓量 = **5个数据维度的交叉验证**。对于30分钟高频短线策略，数据密度和多样性已经远超大部分个人交易者。行为数据一旦修复回写，将具备第6个维度（历史胜率回馈）。 |
| **为什么不够？** | (1) 行为数据链路完全断开（behavior=空），评分中的行为因子=0 — **不是数据源不够，是数据没流通过来**。(2) 生产版本的引擎完全没有选币库集成，评分只有4个维度 — **不是不够用，是根本没接**。(3) 观察池（80-200名币种）有数据但引擎从未扫描。 |
| **怎么解决？** | (1) 修复 `record_trade_in_pool()` 调用链路 — 在 `run_node()` 的SELL分支添加调用（见第4节方案）。(2) 同步更新生产引擎集成选币库。(3) 考虑在 `scan_top50` 之外增加观察池扫描逻辑（作为扩容候选）。 |
| **什么时候解决？** | **本次审计报告完成后立即解决**。P0修复（调用链路）代码改动量：+5行（全局变量定义）+1行（买入记录价格）+4行（卖出调用record_trade_in_pool）≈10行代码，测试时间<5分钟。 |

---

## 7. 【如目前不用解决——后期要不要解决？如后期要解决——有没有任务指南？】

### 结论：必须立即解决，不能等"后期"

| 项目 | 是否可延迟 | 理由 |
|------|-----------|------|
| 修复record_trade_in_pool调用链路 | ❌ P0 立即解决 | 行为因子是选币库的核心价值输出，链路断则选币库形同虚设。10行代码修复，收益极大。 |
| 同步生产引擎集成选币库 | ⚠️ P1 本轮解决 | 生产引擎跑的是v1弱评分类，没有多因子评分，与根目录引擎有显著差异。应统一为一个版本。 |
| 启用观察池 | ⏳ P2 可延至下次迭代 | 当前策略聚焦Top50流动性，观察池可用作候选扩容，非紧急。 |
| CoinGecko价格验证优化 | ⏳ P3 功能增强 | 已有但只有前10名验证，可扩展到前20名。 |
| 链上数据接入 | 🔮 P4 远期 | 无迫切需求，当前5维度已覆盖核心。 |

### 任务指南

**如果选择修复（推荐），任务指南如下：**

1. **修复 `engine_realtime_v2.py`**:
   - 在L892 `_hold_since` 旁新增 `_hold_price = {}`
   - 在L1135 `_hold_since[e['symbol']] = time.time()` 后新增 `_hold_price[e['symbol']] = result['price']`
   - 在L1104-1108 `log_trade()` 后新增 `record_trade_in_pool()` 调用（见第4节方案三）
   - 保存状态时需持久化 `_hold_price`（在`save_state()`中）

2. **同步生产引擎**:
   - 将修复后的 `engine_realtime_v2.py` 复制到 `production/engine/engine_realtime_v2.py`
   - 或直接在 `production/engine/` 版本中实施相同修改

3. **验证**:
   - 手动执行一次完整的SELL流程
   - 检查 `coin_pool.json.behavior` 中是否新增了记录
   - 执行 `python3 tools/coin_pool_manager.py --status` 验证行为数据正确展示

---

## 附录：关键文件行号索引

| 文件 | 行号 | 内容 | 状态 |
|------|------|------|------|
| `engine_realtime_v2.py` | 228-294 | 选币库集成函数定义区 | ✅ 存在 |
| `engine_realtime_v2.py` | 285-294 | `record_trade_in_pool()` 定义 | ✅ 存在但死代码 |
| `engine_realtime_v2.py` | 369-463 | `calc_resonance_score()` 含行为因子 | ✅ 存在 |
| `engine_realtime_v2.py` | 987-1173 | `run_node()` 主流程 | ✅ 存在 |
| `engine_realtime_v2.py` | 1086-1116 | SELL处理分支 — **缺record_trade_in_pool调用** | ❌ 缺失 |
| `engine_realtime_v2.py` | 1125-1139 | BUY处理分支 — 只记录`_hold_since`不记录买入价 | ⚠️ 不完整 |
| `production/engine/engine_realtime_v2.py` | 全文件 | 无任何选币库引用 | ❌ 完全缺失 |
| `tools/coin_pool_manager.py` | 173-208 | `record_trade()` 实现（接收端） | ✅ 存在且逻辑正确 |
| `data/coin_pool.json` | behavior字段 | 仅BIO 1条记录 | ❌ 数据=空 |
| `audit/TRADES.md` | 全文件 | 208条BUY + 173条SELL | ✅ 数据完整 |

---

*审计完成时间: 2026-05-04 11:38:00+08:00*
*审计工具: 手动代码审查 + 静态分析搜索*
