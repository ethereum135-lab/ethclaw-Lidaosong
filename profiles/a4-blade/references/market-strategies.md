# A4 市场级交易策略 — 完整执行指南

> 来源：全网搜索 + 专业交易者方法论
> 不是从系统历史数据推导的，是从市场里学来的
> 2026-05-17

---

## 策略1：RSI背离入场法

### 核心原理

```
价格创新低 + RSI没创新低 = 买方在悄悄进场（背离信号）
等价格突破前一个高点 → 确认趋势反转 → 买入

普通RSI用法（系统现在用的）：
  RSI>70 → 卖出 ❌（太简单，假信号多）

专业RSI用法（市场用的）：
  价格低点 < 前一个低点
  RSI低点 > 前一个RSI低点
  → 背离成立 → 等价格涨过前高 → 买入 ✅
```

### A4执行流程

```bash
# 每30分钟检查（SSH到AWS获取数据）
ssh web4 "python3 -c '
import json, requests

# 取最近100根1h K线
url = \"https://api.binance.com/api/v3/klines?symbol=SYMBOLUSDT&interval=1h&limit=100\"
data = requests.get(url).json()

# 取收盘价和RSI
closes = [float(k[4]) for k in data]

# 计算RSI(14)
def rsi(prices, period=14):
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0: return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

rsi_values = [rsi(closes[i-14:i]) for i in range(14, len(closes))]

# 找最近两个低点
last_30_closes = closes[-30:]
last_30_rsis = rsi_values[-30:]
min1_idx = last_30_closes.index(min(last_30_closes))
min1_price = last_30_closes[min1_idx]
min1_rsi = last_30_rsis[min1_idx]

# 找前一个低点（min1之前的30根里找）
prev_30_closes = closes[-60:-30]
prev_30_rsis = rsi_values[-60:-30]
min2_idx = prev_30_closes.index(min(prev_30_closes))
min2_price = prev_30_closes[min2_idx]
min2_rsi = prev_30_rsis[min2_idx]

# 背离判断
if min1_price < min2_price and min1_rsi > min2_rsi:
    print(f\"BULLISH_DIVERGENCE: price_low={min1_price:.4f} rsi_low={min1_rsi:.1f}\")
    # 等价格突破前高就买入
    prev_high = max(last_30_closes[:min1_idx])
    current_price = closes[-1]
    if current_price > prev_high:
        print(f\"BREAKOUT_CONFIRMED: buy now @ {current_price:.4f}\")
    else:
        print(f\"WAITING_BREAKOUT: need > {prev_high:.4f} to enter\")
else:
    print(\"NO_DIVERGENCE\")
'"
```

### 退出规则

```
退出条件（满足任一即退出）：
  1. RSI(4h) > 70 → 清仓（P1规则，胜率89.7%）
  2. 买入后48h无+3%以上涨幅 → 时间止损（市场证明的规则）
  3. -5%硬止损
```

---

## 策略2：赛道轮动选币法

### 核心原理

```
不看单个币好不好——看"钱在往哪个赛道流"。
赛道对了，里面的币自然会涨。

当前赛道热度（2026年5月，全网验证）：
  AI Agents（FET/TAO/VIRTUAL）→ 叙事最强，机构在进
  RWA（ONDO/MKR）→ 合规资金流入，稳定
  Depin → Solana生态扩张，量在起来
  ETH L2 → Arbitrum/Optimism在吸筹
```

### A4执行流程

```bash
# 每天08:00先查赛道热度
ssh web4 "python3 -c '
import requests

# 用CoinGecko赛道数据判断热度
categories = [\"artificial-intelligence\", \"real-world-assets-rwa\", \"depin\", \"layer-2\"]
for cat in categories:
    url = f\"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&category={cat}&order=volume_desc&per_page=5&page=1\"
    data = requests.get(url).json()
    vol = sum(c[\"total_volume\"] for c in data if c.get(\"total_volume\"))
    change = sum(c[\"price_change_percentage_24h\"] for c in data if c.get(\"price_change_percentage_24h\")) / len(data)
    print(f\"{cat}: 24h_vol=\${vol:.0f} avg_change={change:+.2f}%\")
'"

# 结论：选24h成交量最大 + 平均涨幅为正的赛道
# 只做该赛道成交量前2的币
```

### 没有赛道信号时的做法

```
如果所有赛道24h平均涨幅都为负（全市场下跌）：
  → 不做任何新买入
  → 持有现金等市场恢复
  这不是"空转"，是"守纪律"
```

---

## 策略3：2%风险金管理法

### 核心原理

```
不是"买多少钱"——是"最多亏多少钱"。

每笔交易最大亏损 = 总资金的2%
$430 × 2% = $8.6

止损距离决定仓位大小：
  仓位 = $8.6 / 止损距离%
  止损设-5% → 仓位 = $8.6/0.05 = $172
  止损设-3% → 仓位 = $8.6/0.03 = $286

永远不超过单笔$8.6的风险。
连续亏10笔也只亏$86。
```

### A4执行流程

```bash
# 每次买入前计算仓位
MAX_RISK = total_usdt * 0.02  # $430 * 2% = $8.6
STOP_LOSS_PCT = 0.05          # -5%止损

position_size = MAX_RISK / STOP_LOSS_PCT  # $8.6 / 0.05 = $172

# 但如果USDT不够$172，就按实际可用金额
actual_position = min(position_size, available_usdt)

# 风控检查
if actual_position < 15:  # 小于$15不操作（不够cover手续费）
    print("SKIP: position too small to cover fees")
else:
    print(f"BUY: ${actual_position:.0f}")
```

---

## 三策略合并执行流程

```
每30分钟A4执行节点：
  
  ① 赛道扫描（08:00/13:00/18:00各一次）
     → 确定当前热门赛道
     → 选该赛道成交量前2的币
  
  ② RSI背离检查（每次节点）
     → 对候选币做1h/4h RSI背离检测
     → 有背离 → 等突破前高确认
     → 确认 → 进入买入流程
  
  ③ 2%风险金计算
     → max_risk = USDT × 2%
     → position = max_risk / stop_loss_pct
     → 如果position < $15 → 跳过（不够cover费用）
  
  ④ 买入（通过AWS）
     → ssh web4 "aws_executor.py --buy SYM position"
     → 记录 entry_type = "rsi_divergence"
  
  ⑤ 持仓管理
     ├─ RSI(4h) > 70 → 清仓（P1规则）
     ├─ 买入后48h无+3% → 时间止损
     ├─ -5%硬止损
     ├─ 24h超时强制评估
     └─ 都不触发 → Hold
```

---

## 和当前A4的差异

| 维度 | 当前A4 | 市场策略 |
|:-----|:-------|:---------|
| 选币 | A3推荐/A2管道/RSI+BB | 赛道轮动 → RSI背离 → 2%风控 |
| 入场 | trend_checker验证 | RSI背离+突破前高确认 |
| 仓位 | $15-30固定 | 动态计算（max_risk/止损距离） |
| 退出 | E系列混合 | P1(89.7%) + 48h时间止损 + -5%硬止损 |
| 不交易时 | 空转HOLD | 赛道全跌→守纪律不买 |
