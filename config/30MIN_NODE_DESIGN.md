# ZQ Web 4.0 — 30分钟节点引擎设计文档 v1.0

> **核心理念**：每一轮30分钟是一个独立的决策节点，只看当前数据决定动作。
> 没有"亏损"概念，只有"数据支持进场 / 数据不支持进场"。
> 亏损的唯一原因：进场前没看数据，数据已经告诉你不能进了。
>
> 发布日期：2026-04-30 | 状态：设计定稿 → 待编码

---

## 目录

1. [引擎架构总览](#1-引擎架构总览)
2. [节点时间线](#2-节点时间线)
3. [数据扫描层](#3-数据扫描层)
4. [进场决策层](#4-进场决策层)
5. [出场决策层](#5-出场决策层)
6. [不持仓决策层](#6-不持仓决策层)
7. [执行层](#7-执行层)
8. [与现有引擎的差异](#8-与现有引擎的差异)
9. [错误处理与容灾](#9-错误处理与容灾)

---

## 1. 引擎架构总览

```
┌─────────────────────────────────────────────────────┐
│               30分钟节点引擎 (Node Engine)              │
├─────────────────────────────────────────────────────┤
│  每30分钟 ⏰ 独立触发一次，完整执行以下5层：             │
│                                                     │
│  Layer 1: 数据扫描层                                  │
│    ↓ 输出: DataSnapshot{price, rsi, volume, trend}   │
│                                                     │
│  Layer 2: 进场决策层 (针对 USDT 可用余额)              │
│    ↓ 输出: EntrySignal{coin_list, amounts, reason}   │
│                                                     │
│  Layer 3: 出场决策层 (针对当前持仓)                     │
│    ↓ 输出: ExitSignal{coin_list, reason}             │
│                                                     │
│  Layer 4: 不持仓决策层 (什么都不做)                     │
│    ↓ 输出: StaySignal{reason} (可选跳过)              │
│                                                     │
│  Layer 5: 执行层 (下单 + 限流 + 日志)                  │
│    ↓ 输出: ExecutionResult{trade_ids, errors}        │
└─────────────────────────────────────────────────────┘
```

---

## 2. 节点时间线

每个30分钟节点的标准执行流程（耗时 ≤ 60秒）：

```
T + 0min  ⏰ 节点触发
          ├── Layer 1: 数据扫描 (公共行情 + K线 + RSI)        ~3-5s
          ├── Layer 2: 进场决策 (评分 + 条件检查)              ~1s
          ├── Layer 3: 出场决策 (持仓检查 + 条件检查)           ~2s
          ├── Layer 4: 不持仓决策 (USDT空仓判断)              ~1s
          └── Layer 5: 执行下单 (市价买卖 + 限流等待)          ~10-15s

T + 1min  ✅ 节点完成，进入休眠
          └── sleep(1740)  ← 29分钟剩余时间

T + 30min ⏰ 下一个节点触发

总计休眠时间 ≈ 1740 秒 (确保下一节点准时在整30分钟边界触发)
```

**关键设计原则**：
- 每节点不超过60秒完成，预留29分钟缓冲
- 节点间**无状态耦合**——没有成本价、没有累计盈亏
- 每一轮都是"清空认知，重看数据"

---

## 3. 数据扫描层

### 3.1 数据源与API

| 数据 | API Endpoint | 用途 | 获取频率 |
| :--- | :--- | :--- | :--- |
| 24h行情 | `GET /api/v3/ticker/24hr` | 成交额、涨幅 | 每节点1次 |
| 当前价格 | `GET /api/v3/ticker/price?symbol={}` | 实时市价 | 每节点1次 |
| 30min K线 | `GET /api/v3/klines?interval=30m&limit=15` | RSI、均线、成交量基线 | 每节点1次 |
| 1h K线 | `GET /api/v3/klines?interval=1h&limit=24` | 中期趋势判断 | 每节点1次 |
| 账户余额 | `GET /api/v3/account` | USDT可用、持仓量 | 每节点1次 |
| 交易规则 | `GET /api/v3/exchangeInfo?symbol={}` | LOT_SIZE、精度 | 首次或缓存 |

### 3.2 数据指标计算公式

#### 3.2.1 RSI(14) — 30分钟K线

```
RSI = 100 - (100 / (1 + RS))
RS = 过去14根30minK线的平均涨幅 / 平均跌幅

输入: 14根30分钟K线的收盘价 (用klines API取15根，最后1根是当前)
公式:
  gains = [close[i] - close[i-1] if close[i] > close[i-1] else 0 for i in range(1, 15)]
  losses = [close[i-1] - close[i] if close[i] < close[i-1] else 0 for i in range(1, 15)]
  avg_gain = sum(gains) / 14
  avg_loss = sum(losses) / 14
  RS = avg_gain / avg_loss if avg_loss != 0 else 999
  RSI = 100 - (100 / (1 + RS))
```

#### 3.2.2 成交量异动 (Volume Surge)

```
基线 = 过去14根30minK线的平均成交量 (排除最高和最低各2个异常值)
当前量 = 最后一根30minK线的成交量 (当前正在形成的K线)
异动率 = 当前量 / 基线

成交量异动判定:
  surge_flag = True if 异动率 > 1.5 else False
  decline_flag = True if 异动率 < 0.5 else False
```

#### 3.2.3 趋势得分 (Trend Score)

```
EMA7 = 7周期指数移动平均 (30min K线收盘价)
EMA25 = 25周期指数移动平均 (30min K线收盘价)
EMA99 = 99周期指数移动平均 (从1h K线换算)

趋势评分:
  +2  if 价格 > EMA7 > EMA25  (强势上涨)
  +1  if 价格 > EMA7 但 EMA7 <= EMA25  (刚启动)
   0  if 价格在 EMA7 和 EMA25 之间  (盘整)
  -1  if 价格 < EMA7 但 EMA7 > EMA25  (回调)
  -2  if 价格 < EMA7 < EMA25  (下跌趋势)
```

#### 3.2.4 价格位置 (Price Position)

```
30min最高 = max(close[-14:])  # 近14根30minK线的最高收盘价
30min最低 = min(close[-14:])  # 近14根30minK线的最低收盘价
当前位置 = (当前价格 - 30min最低) / (30min最高 - 30min最低) * 100

位置评分:
  +1  if 30% ≤ 当前位置 ≤ 70%  (合理中位区)
   0  if 当前位置 < 30%  (低位，可能有支撑也可能破位)
  -1  if 当前位置 > 70%  (高位，追高风险)
```

### 3.3 数据扫描输出结构

```python
DataSnapshot = {
    "timestamp": 1714348800000,       # 节点时间戳
    "symbol": "DOGEUSDT",
    "price": 0.10345,                  # 当前价格
    "volume_24h": 1250000000,          # 24h成交额(USDT)
    "volume_30m_baseline": 45000000,   # 30min成交量基线
    "volume_30m_current": 68000000,    # 当前30min成交量
    "volume_surge_ratio": 1.51,        # 成交量异动率
    "volume_surge_flag": True,         # 成交量是否异动
    "price_change_24h": 3.45,          # 24h涨幅%
    "rsi_14": 58.3,                    # RSI(14)
    "price_position": 45.0,            # 价格位置百分比
    "ema7": 0.10200,                   # EMA7
    "ema25": 0.10000,                  # EMA25
    "trend_score": 2,                  # 趋势评分(-2~+2)
    "price_position_score": 1,         # 位置评分(-1~+1)
}
```

### 3.4 数据采集代码框架

```python
def scan_data(symbol: str) -> DataSnapshot:
    \"\"\"扫描单个币种的完整数据结构\"\"\"
    # 1. 获取30min K线数据（15根）
    kline_30m = requests.get(
        "https://api.binance.com/api/v3/klines",
        params={"symbol": symbol, "interval": "30m", "limit": 15},
        timeout=5
    ).json()
    closes = [float(k[4]) for k in kline_30m]
    volumes = [float(k[5]) for k in kline_30m]

    # 2. 计算RSI
    rsi = calc_rsi(closes, period=14)

    # 3. 计算成交量基线
    baseline_vol = calc_volume_baseline(volumes[:-1])  # 排除当前K线
    current_vol = volumes[-1]
    surge_ratio = current_vol / baseline_vol if baseline_vol > 0 else 1.0

    # 4. 计算EMA
    ema7 = calc_ema(closes, period=7)
    ema25 = calc_ema(closes, period=25)

    # 5. 趋势评分
    trend = calc_trend_score(closes[-1], ema7, ema25)

    # 6. 获取24h行情
    ticker = requests.get(
        "https://api.binance.com/api/v3/ticker/24hr",
        params={"symbol": symbol},
        timeout=5
    ).json()
    vol_24h = float(ticker["quoteVolume"])
    chg_24h = float(ticker["priceChangePercent"])

    return DataSnapshot(
        symbol=symbol, price=closes[-1],
        volume_24h=vol_24h, volume_30m_baseline=baseline_vol,
        volume_30m_current=current_vol, volume_surge_ratio=surge_ratio,
        price_change_24h=chg_24h, rsi_14=rsi,
        price_position=calc_price_position(closes),
        ema7=ema7, ema25=ema25, trend_score=trend,
        price_position_score=calc_position_score(closes)
    )
```

---

## 4. 进场决策层

### 4.1 核心哲学

> **30分钟内根本不会亏，因为你看了数据才进场。**
> 数据在30分钟窗口内不会突然翻脸——如果翻了，说明进场时数据端已经给了信号。

### 4.2 进场必要条件（AND条件，必须全部满足）

| # | 条件 | 阈值 | 说明 |
| :--- | :--- | :--- | :--- |
| 1 | RSI(14) | `20 < RSI < 70` | 不能超买也不能超卖 |
| 2 | 成交量异动 | `成交量异动率 ≥ 1.0` | 不能缩量下跌 |
| 3 | 趋势得分 | `trend_score ≥ 0` | 不能处于下降趋势 |
| 4 | 价格位置 | `price_position_score ≥ 0` | 不在高位追涨 |
| 5 | 24h成交额排名 | Top 50 | 有足够流动性 |
| 6 | 24h涨幅 | `-5% < price_change < 15%` | 不是暴涨末段也不是暴跌抄底 |

### 4.3 共振评分公式 (用于排序选择Top3)

```python
def resonance_score(snap: DataSnapshot) -> float:
    \"\"\"共振评分 0-100，越高越好\"\"\"
    # 成交额得分 (0-40分)
    # 成交额越高越好，按Top50排名线性映射
    volume_score = max(0, 40 - rank * 0.8)  # rank从1开始

    # RSI得分 (0-20分)
    # 40-60为最佳区间
    if 40 <= snap.rsi_14 <= 60:
        rsi_score = 20
    elif 30 <= snap.rsi_14 < 40 or 60 < snap.rsi_14 <= 65:
        rsi_score = 15
    elif 20 <= snap.rsi_14 < 30 or 65 < snap.rsi_14 < 70:
        rsi_score = 10
    else:
        rsi_score = 0  # 超买/超卖，不进

    # 成交量异动得分 (0-20分)
    if snap.volume_surge_ratio >= 2.0:
        volume_surge_score = 20
    elif snap.volume_surge_ratio >= 1.5:
        volume_surge_score = 15
    elif snap.volume_surge_ratio >= 1.0:
        volume_surge_score = 10
    else:
        volume_surge_score = 0

    # 趋势得分 (0-20分)
    trend_map = {2: 20, 1: 15, 0: 10, -1: 0, -2: 0}
    trend_score = trend_map.get(snap.trend_score, 0)

    return volume_score + rsi_score + volume_surge_score + trend_score
```

### 4.4 进场执行逻辑

```
输入: 币种快照列表 (Top50)
输出: EntryPlan (要买入的币种 + 金额)

步骤:
1. 对所有Top50币种执行 DataSnapshot 扫描
2. 过滤通过"进场必要条件"的币种
3. 按共振评分排序
4. 取Top3：
   - #1 Leader仓位: USDT可用 * 50%
   - #2 Volume仓位: USDT可用 * 30%
   - #3 Sentiment仓位: USDT可用 * 20%
5. 如果某个币种共振评分 < 40，即使排进Top3也不进（数据不支持）
6. 如果Top3中所有币种评分都 < 40，整轮不进场
```

**特殊规则**：
- 每笔最低金额：`≥ 10 USDT`（Binance最小名义值约束）
- 如果可用USDT总额 < 30 USDT，跳过本轮买入
- **不强制用完所有USDT**——不符合条件的币种不买，剩下的USDT继续等待

---

## 5. 出场决策层

### 5.1 核心哲学

> 没有"亏损"概念，只有"数据不支持继续持有"。
> 出场不是因为亏了钱，而是因为当前数据告诉你：**这个币不值得再拿了**。

### 5.2 出场条件（OR条件，满足任意一条即卖出）

| # | 条件 | 阈值 | 说明 |
| :--- | :--- | :--- | :--- |
| E1 | RSI转空 | `RSI(14) 从 >60 降到 <45` | 动能衰减信号 |
| E2 | 成交量萎缩 | `成交量异动率 < 0.6` | 没人玩了 |
| E3 | 趋势转跌 | `trend_score 从 >=0 降到 -1 或 -2` | 趋势走坏 |
| E4 | 共振评分骤降 | `当前评分 < 上次评分 * 0.7` | 评分大幅下滑 |
| E5 | 价格异常 | `24h涨幅 < -8%` | 异常大跌 |
| E6 | 连续两节点评分垫底 | `连续2轮评分排Top50后20名` | 流动性退化 |

### 5.3 出场执行逻辑

```
输入: 当前持仓列表 + 各币种新扫描的 DataSnapshot
输出: ExitPlan (要卖出的币种 + 数量)

步骤:
1. 对每个持仓币种执行 DataSnapshot 扫描
2. 检查是否满足出场条件 (任意一条即触发)
3. 如果触发出场 → 市价卖出全部可用持仓
4. 如果未触发出场 → 继续持有，不操作
```

### 5.4 移仓逻辑（Swap）

当出场触发时，被卖出的USDT可以立即用于进场决策。
但**必须在同一个30分钟节点内**完成：先出场 → 数据扫描 → 再进场。

```
同一节点内执行顺序:
1. ✅ 扫描所有持仓币种数据
2. ✅ 如果有出场信号 → 卖出
3. ✅ 扫描候选币种数据
4. ✅ 如果有进场信号 → 买入
5. ✅ 等待下一节点
```

---

## 6. 不持仓决策层

### 6.1 核心哲学

> USDT不满足条件时直接空仓等待，**这是正确决策，不是失败**。
> 强于空仓等待，弱于胡乱进场。

### 6.2 空仓等待条件

| 场景 | 条件 | 动作 |
| :--- | :--- | :--- |
| 无持仓 + 无可进场币种 | 所有Top50币种均未通过进场必要条件 | ✅ 全部USDT，等待下一节点 |
| 有持仓 + 持仓都未触发出场 | 持仓币种数据仍支持持有 | ✅ 持有不动，用USDT余额尝试进场 |
| 有持仓 + 持仓触发出场 | 出场条件触发 | ✅ 卖出后USDT等待，本节点不再进场 |
| 无持仓 + USDT < 30 | 资金不足最小交易量 | ✅ 自动等待 |

### 6.3 决策矩阵

```
                     ┌──────────────────┬──────────────────┐
                     │  有可进场币种     │  无可进场币种     │
┌────────────────────┼──────────────────┼──────────────────┤
│  有持仓(未触发出场) │  持有+买新币     │  仅持有不动       │
│  有持仓(触发出场)   │  卖出+买入新币   │  卖出后空仓等待   │
│  无持仓            │  买入新币        │  空仓等待         │
└────────────────────┴──────────────────┴──────────────────┘
```

---

## 7. 执行层

### 7.1 下单执行

#### 市价买入

```python
def execute_market_buy(symbol: str, quote_amount: float) -> OrderResult:
    \"\"\"市价买入，按USDT金额下单\"\"\"
    # 1. 获取交易规则
    exchange_info = get_exchange_info(symbol)
    lot_step = exchange_info["lot_step"]
    min_notional = exchange_info["min_notional"]

    # 2. 检查金额
    if quote_amount < min_notional:
        return OrderResult(skip=True, reason=f"金额<{min_notional}")

    # 3. 市价买入
    params = {
        "symbol": symbol,
        "side": "BUY",
        "type": "MARKET",
        "quoteOrderQty": str(round(quote_amount, 2))
    }
    code, result = signed_api("POST", "/api/v3/order", params)
    ...
```

#### 市价卖出

```python
def execute_market_sell(symbol: str, quantity: float) -> OrderResult:
    \"\"\"市价卖出，按币数量下单\"\"\"
    # 1. 获取交易规则
    exchange_info = get_exchange_info(symbol)
    lot_step = exchange_info["lot_step"]
    step_precision = get_precision(lot_step)

    # 2. 调整数量精度
    qty = floor_to_step(quantity, lot_step)

    # 3. 市价卖出
    params = {
        "symbol": symbol,
        "side": "SELL",
        "type": "MARKET",
        "quantity": str(qty)
    }
    code, result = signed_api("POST", "/api/v3/order", params)
    ...
```

### 7.2 限流策略

| 限制项 | 阈值 | 处理方式 |
| :--- | :--- | :--- |
| API权重 | 每30分钟1200权重 | 监控返回header `X-MBX-USED-WEIGHT` |
| 订单间隔 | 每单间隔 ≥ 3秒 | `time.sleep(3)` |
| 封禁(418) | 出现418 | 重试等待`retry-after`秒，跳过本轮 |
| 公共API | 不限流但有限制 | 1200权重/分钟 |

### 7.3 错误处理

```python
def execute_with_retry(func, max_retries=3, retry_delay=5):
    \"\"\"带重试的执行包装\"\"\"
    for attempt in range(max_retries):
        try:
            result = func()
            if result["status"] == 418:
                wait = result.get("retry_after", 300)
                print(f"⛔ API封禁，等待{wait}s")
                time.sleep(wait)
                continue
            return result
        except requests.Timeout:
            print(f"⏱️ 超时(第{attempt+1}次)，重试中...")
            time.sleep(retry_delay)
        except Exception as e:
            log_error(f"执行异常: {func.__name__}", str(e))
            time.sleep(retry_delay)
    return {"status": "failed", "reason": "超过最大重试次数"}
```

### 7.4 日志与审计

每条执行记录写入 `audit/TRADES.md`：

```
格式: | 时间 | 操作 | 币种 | 数量 | 价格 | 原因 | 决策数据摘要 |
```

每条节点扫描写入 `audit/NODES.md`（新文件）：

```
格式: | 时间 | 扫描币种数 | 通过进场条件数 | 进场币种 | 出场币种 | 空仓原因 |
```

每条错误写入 `audit/ERRORS.md`：

```
格式: | 时间 | 上下文 | 错误类型 | 错误详情 | 处理方式 |
```

---

## 8. 与现有引擎的差异

| 维度 | engine_realtime_v1.py (现状) | 30分钟节点引擎 (新设计) |
| :--- | :--- | :--- |
| 出场逻辑 | ❌ 无（仅占位符） | ✅ 6条数据驱动出场条件 |
| 止损方式 | ❌ 脚本分离(force_sell_doge.py) | ✅ 内建于引擎，数据不支持即卖 |
| 评分维度 | 仅成交额+涨幅 | 成交额+RSI+成交量异动+趋势+位置 |
| RSI | ❌ 无 | ✅ RSI(14) 30min K线计算 |
| 趋势判断 | ❌ 无 | ✅ EMA7/25 + 趋势评分 |
| 成本价概念 | ⚠️ 有（P&L隐含） | ❌ 没有，只看当前数据 |
| 空仓决策 | ❌ 只有"USDT<$30"条件 | ✅ 完整决策矩阵 |
| 节点独立性 | ❌ 持仓状态耦合 | ✅ 每节点独立决策 |
| 扫描频率 | 每节点1次 | 同左，但数据结构更完整 |
| 错误重试 | ❌ 无 | ✅ 3次重试+418封禁处理 |

---

## 9. 错误处理与容灾

### 9.1 网络故障

| 场景 | 处理 |
| :--- | :--- |
| Binance API超时 | 重试3次，间隔5秒，仍失败则跳过本轮 |
| 公共行情API失败 | 回退到Binance REST API的公共ticker |
| DNS解析失败 | 等待60秒后重试，仍失败标记本轮为"网络异常" |

### 9.2 数据异常

| 场景 | 处理 |
| :--- | :--- |
| RSI计算除零 | 返回RSI=50（中性），标注"数据不足" |
| 成交量基线=0 | 返回异动率=1.0（无异常），标注"数据不足" |
| K线数据不足14根 | 缩短周期到可用数据量 |
| 价格=0或负数 | 跳过该币种，标记数据异常 |

### 9.3 订单异常

| 场景 | 处理 |
| :--- | :--- |
| 418封禁 | 等待`retry-after`秒后重试1次，仍封禁则跳过本轮 |
| -1013 LOT_SIZE错误 | 重新计算精度后重试 |
| -2010 资金不足 | 标记余额误差，跳过买入，下节点重新检查 |
| -1010 下单失败(未知) | log_error，跳过该币种 |

### 9.4 容灾降级

```
数据降级路径:
  Binance REST (首选) → CoinGecko公共API (备选1) → 跳过本轮 (备选2)

执行降级路径:
  完整交易 (首选) → 仅执行出场不进场 (备选) → 完全不操作 (末选)
```

---

## 附录A：关键代码模块清单

| 模块 | 文件 | 职责 |
| :--- | :--- | :--- |
| 数据扫描器 | `scanner.py` | 采集API数据、计算RSI/EMA/成交量基线 |
| 进场决策器 | `entry_decision.py` | 进场条件检查、共振评分、Top3选择 |
| 出场决策器 | `exit_decision.py` | 出场条件检查、持仓评分监控 |
| 节点调度器 | `node_scheduler.py` | 30分钟定时触发、节点生命周期管理 |
| 执行引擎 | `executor.py` | 下单、限流、重试、日志 |
| 配置器 | `config.py` | 加载阈值配置、交易对白名单 |

## 附录B：默认阈值配置

```json
{
  "entry": {
    "rsi_min": 20,
    "rsi_max": 70,
    "volume_surge_min": 1.0,
    "trend_score_min": 0,
    "price_change_min": -5,
    "price_change_max": 15,
    "min_resonance_score": 40,
    "min_usdt_total": 30,
    "min_order_usdt": 10
  },
  "exit": {
    "rsi_drop_threshold": 45,
    "rsi_drop_from": 60,
    "volume_decline_ratio": 0.6,
    "trend_drop_threshold": -1,
    "score_drop_ratio": 0.7,
    "price_crash_threshold": -8.0,
    "consecutive_bad_rank_count": 2,
    "bad_rank_threshold": 30
  },
  "execution": {
    "order_interval_sec": 3,
    "max_retries": 3,
    "retry_delay_sec": 5,
    "node_timeout_sec": 60,
    "node_interval_sec": 1800
  }
}
```
