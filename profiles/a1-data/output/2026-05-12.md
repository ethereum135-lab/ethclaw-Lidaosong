# A1 数据采集报告 — 2026-05-12

采集时间：05:05 BJT
采集日期：2026-05-12（星期二）

---

## ① 市场情绪

| 指标 | 数值 |
|:----|:----:|
| F&G 恐慌指数 | **48 / 100** |
| 状态标签 | **Neutral（中性）** |
| 数据来源 | [Alternative.me Fear & Greed Index](https://api.alternative.me/fng/) |

> 市场情绪处于中性区间，无明显恐慌或贪婪倾向。

---

## ② 资金费率（Top 10）

**数据来源：** OKX API（`https://www.okx.com/api/v5/public/funding-rate`）
**说明：** Binance FAPI 返回 HTTP 451（地区限制），已按预案切换至 OKX 备源。

| # | 币种 | 费率 | 方向 | 说明 |
|:-:|:----|:----:|:----:|:-----|
| 1 | BTC | −0.00634% | 🔴 空付多 | 空头持仓者向多头支付资金 |
| 2 | ETH | +0.00600% | 🟢 多付空 | 多头持仓者向空头支付资金 |
| 3 | SOL | −0.00548% | 🔴 空付多 | 空头持仓者向多头支付资金 |
| 4 | XRP | +0.01000% | 🟢 多付空 | 多头持仓者向空头支付资金 |
| 5 | BNB | +0.00478% | 🟢 多付空 | 多头持仓者向空头支付资金 |
| 6 | ADA | +0.01000% | 🟢 多付空 | 多头持仓者向空头支付资金 |
| 7 | DOGE | +0.00279% | 🟢 多付空 | 多头持仓者向空头支付资金 |
| 8 | LINK | +0.00898% | 🟢 多付空 | 多头持仓者向空头支付资金 |
| 9 | SUI | +0.00324% | 🟢 多付空 | 多头持仓者向空头支付资金 |
| 10 | AVAX | +0.00020% | 🟢 多付空 | 多头持仓者向空头支付资金 |

**摘要：** 8/10 币种费率为正（多头支付空头），2/10 为负（BTC、SOL 空头支付多头）。整体费率绝对值较小，市场杠杆情绪温和。

---

## ③ 社交热度

**数据来源：** [CoinGecko Trending Search API](https://api.coingecko.com/api/v3/search/trending)

| 排名 | 币种 | 符号 |
|:---:|:----|:----:|
| 1 | Zano | ZANO |
| 2 | LAB | LAB |
| 3 | Venice Token | VVV |
| 4 | Osmosis | OSMO |
| 5 | wojak | WOJAK |
| 6 | Pudgy Penguins | PENGU |
| 7 | Sui | SUI |
| 8 | Bittensor | TAO |
| 9 | Chainlink | LINK |
| 10 | Bitcoin | BTC |

---

## ④ 聪明钱包 — 待接入

**缺少工具：** 聪明钱包追踪 API（如 Nansen、Arkham Intelligence、0xScope 等）
**当前状态：** 暂无可用 API 接入，标记为「待接入」

---

## ⑤ 链上数据 — 待接入

**缺少工具：** 链上数据 API（如 Glassnode、Dune Analytics、DefiLlama 等）
**当前状态：** 暂无可用 API 接入，标记为「待接入」

---

## ⑥ 新闻舆情 — 待接入

**缺少工具：** 新闻聚合/舆情分析 API（如 LunarCrush、TheTie、CryptoPanic 等）
**当前状态：** 暂无可用 API 接入，标记为「待接入」

---

## 采集摘要

| 维度 | 状态 | 数据来源 |
|:----|:----:|:---------|
| ① 市场情绪 | ✅ 已采集 | Alternative.me F&G Index |
| ② 资金费率 | ✅ 已采集（备源切换） | OKX API（Binance 451→OKX） |
| ③ 社交热度 | ✅ 已采集 | CoinGecko Trending |
| ④ 聪明钱包 | ❌ 待接入 | 缺少 API |
| ⑤ 链上数据 | ❌ 待接入 | 缺少 API |
| ⑥ 新闻舆情 | ❌ 待接入 | 缺少 API |

**Binance FAPI 故障记录：** 2026-05-12 05:05 BJT 请求 Binance FAPI 返回 HTTP 451（地区限制），已按预案自动切换至 OKX API 备源，采集成功。
