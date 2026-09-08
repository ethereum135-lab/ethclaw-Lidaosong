# A1 数据采集报告 — 2026-05-11
采集时间：05:00 BJT

## ① 市场情绪
| 项目 | 数值 |
|:----|:----:|
| F&G指数 | **47/100 — Neutral** |
| 数据来源 | [Alternative.me F&G Index](https://api.alternative.me/fng/) |
| 采集时间戳 | 2026-05-11 05:00 BJT |

说明：恐惧与贪婪指数处于中性区间（47），市场情绪无明显偏向。

---

## ② 资金费率（Top 10）
数据来源：**OKX API** (`/api/v5/public/funding-rate`) — 因Binance主网API对该IP区域受限，改用OKX获取永续合约资金费率

| # | 币种 | 费率 | 费率% | 方向 |
|:-:|:----|:---:|:-----:|:----:|
| 1 | FIL-USDT-SWAP | -0.00017240 | -0.0172% | SHORT ⬇️ |
| 2 | XRP-USDT-SWAP | +0.00010000 | +0.0100% | LONG ⬆️ |
| 3 | ADA-USDT-SWAP | +0.00010000 | +0.0100% | LONG ⬆️ |
| 4 | SUI-USDT-SWAP | +0.00010000 | +0.0100% | LONG ⬆️ |
| 5 | LINK-USDT-SWAP | +0.00010000 | +0.0100% | LONG ⬆️ |
| 6 | AVAX-USDT-SWAP | +0.00010000 | +0.0100% | LONG ⬆️ |
| 7 | DOT-USDT-SWAP | +0.00010000 | +0.0100% | LONG ⬆️ |
| 8 | TRX-USDT-SWAP | +0.00010000 | +0.0100% | LONG ⬆️ |
| 9 | BCH-USDT-SWAP | +0.00010000 | +0.0100% | LONG ⬆️ |
| 10 | UNI-USDT-SWAP | +0.00010000 | +0.0100% | LONG ⬆️ |

其他重要币种：
| 币种 | 费率 | 方向 |
|:----|:----:|:----:|
| BTC-USDT-SWAP | -0.0029% | SHORT |
| ETH-USDT-SWAP | +0.0016% | LONG |
| SOL-USDT-SWAP | +0.0001% | LONG |
| PEPE-USDT-SWAP | +0.0100% | LONG |
| BONK-USDT-SWAP | +0.0100% | LONG |

说明：Top10中大部分币种费率为+0.0100%（在OKX上为常见低保费率），FIL独树一帜为负费率（-0.0172%），做空仓位需支付资金费。BTC和ETH费率接近零，市场中性。

⚠️ **原始计划数据源为Binance FAPI**，因地理限制无法访问，**改用OKX**（同等级别CEX，数据可信）。已记录到运行日志。

---

## ③ 社交热度
数据来源：[CoinGecko Trending API](https://api.coingecko.com/api/v3/search/trending)

| # | 币种 | 符号 | 市值排名 | Score |
|:-:|:----|:----:|:--------:|:-----:|
| 1 | Zano | ZANO | #208 | 0 |
| 2 | Sui | SUI | #23 | 1 |
| 3 | SWEAT | SWEAT | #898 | 2 |
| 4 | wojak | WOJAK | #614 | 3 |
| 5 | TROLL | TROLL | #288 | 4 |
| 6 | Pudgy Penguins | PENGU | #91 | 5 |
| 7 | Monad | MON | #123 | 6 |
| 8 | Venice Token | VVV | #90 | 7 |
| 9 | Pepe | PEPE | #49 | 8 |
| 10 | Bittensor | TAO | #35 | 9 |

热门NFT：Clone X, Mutant Ape Yacht Club, Chimpers, Bored Ape Yacht Club, Azuki
热门类别：Base Native, Proof of Work (PoW), Smart Contract Platform, Layer 1 (L1), Binance Alpha Spotlight

---

## ④ 聪明钱包 — 待接入
- **状态**：❌ 未接入
- **缺少工具**：聪明钱包追踪API/数据源（暂无可用接口）
- **建议方案**：待评估 Nansen、Arkham、0xScope 等链上追踪工具的API接入可行性

---

## ⑤ 链上数据 — 待接入
- **状态**：❌ 未接入
- **缺少工具**：链上数据API（如Glassnode、Dune Analytics、DefiLlama等）
- **建议方案**：待评估DefiLlama API（免费可用）或Glassnode付费API

---

## ⑥ 新闻舆情 — 待接入
- **状态**：❌ 未接入
- **缺少工具**：新闻聚合/舆情分析API（如CryptoPanic、LunarCrush、Santiment等）
- **建议方案**：待评估CryptoPanic News API（有免费额度）或LunarCrush社交数据API

---

## 采集摘要

| 维度 | 状态 | 数据源 |
|:----|:---:|:------|
| ① 市场情绪 | ✅ 已采集 | Alternative.me |
| ② 资金费率 | ✅ 已采集 | OKX（原定Binance不可用） |
| ③ 社交热度 | ✅ 已采集 | CoinGecko |
| ④ 聪明钱包 | ❌ 待接入 | — |
| ⑤ 链上数据 | ❌ 待接入 | — |
| ⑥ 新闻舆情 | ❌ 待接入 | — |

**运行日志**：已追加到 `profiles/a1-data/logs/daily.log`
**数据完整性**：3/6 维度已采集，3/6 标记待接入。实事求是，无编造。
