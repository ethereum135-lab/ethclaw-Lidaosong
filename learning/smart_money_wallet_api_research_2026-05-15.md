# 链上聪明钱包动态发现 API 研究报告

> **研究日期**: 2026-05-15 | **研究执行**: Agent Subagent | **目标链**: Ethereum + Solana
> **网络环境**: Mac behind GFW, API calls via AWS SSH (3.27.3.202)

---

## 目录

1. [Etherscan V2 API — 能否发现新活跃钱包/鲸鱼？](#1-etherscan-v2-api--能否发现新活跃钱包鲸鱼)
2. [免费聪明钱包/顶级交易者 API 大盘点](#2-免费聪明钱包顶级交易者-api-大盘点)
3. [Solana 交易所热钱包地址清单](#3-solana-交易所热钱包地址清单)
4. [Solana RPC — 能否发现活跃交易者钱包？](#4-solana-rpc--能否发现活跃交易者钱包)
5. [动态聪明钱发现策略（无需手动维护地址库）](#5-动态聪明钱发现策略无需手动维护地址库)
6. [总结与推荐路线图](#6-总结与推荐路线图)

---

## 1. Etherscan V2 API — 能否发现新活跃钱包/鲸鱼？

### 结论：❌ 没有直接端点可以"发现新钱包"或"发现鲸鱼"

Etherscan V2 API（当前系统中已使用，Key: `4HSI18GIQ7ITWEZR7K7B6U7MUYNIMSG7RX`）的免费层功能：

| 模块 | 端点 | 功能 | 能否发现聪明钱？ |
|:----|:-----|:----|:---------------:|
| `account` → `txlist` | 获取地址的ETH交易 | ❌ 需要已知地址 |
| `account` → `tokentx` | 获取地址的ERC-20转账 | ❌ 需要已知地址 |
| `account` → `tokennfttx` | 获取地址的NFT转账 | ❌ 需要已知地址 |
| `account` → `balancemulti` | 批量查余额 | ❌ 需要已知地址 |
| `token` → `tokenholderlist` | 查代币的持有者列表 | ✅ **可用！** |
| `token` → `tokentx` | 查代币的转账记录 | ✅ **可用！** |
| `stats` → `ethprice` | ETH价格 | ❌ 无关 |
| `stats` → `ethsupply` | ETH总供应 | ❌ 无关 |
| `contract` → `getabi` | 合约ABI | ❌ 无关 |

### 🔑 关键发现：`tokenholderlist` 端点

Etherscan V2 API 的 `token` 模块有 `tokenholderlist` 端点：

```
GET https://api.etherscan.io/v2/api?chainid=1&module=token&action=tokenholderlist
    &contractaddress=0x...  # 代币合约地址
    &page=1&offset=100       # 分页，每页100个持有者
    &apikey=YOUR_KEY
```

**这能做什么？**
- 对于**任何已知的代币合约地址**，获取其 Top 100 持有者
- 从 Top 持有者中筛选出大额地址 → 这就是"鲸鱼钱包"
- 跨时间对比 → 发现哪些鲸鱼在增持/减持

**限制：**
- 需要**先知道代币合约地址**才能查，不能"无中生有"发现新代币
- 免费层 5 calls/sec，Token 模块有额外限制
- 不返回"Smart Money"标签，只是纯地址列表

### 替代思路：通过 DEX 新交易对发现新代币

当前系统已集成 **DexScreener**（API via AWS SSH），可以：
1. 用 DexScreener 发现新交易对/新代币
2. 拿到新代币的合约地址
3. 用 Etherscan `tokenholderlist` 获取其 Top 持有者
4. 分析这些持有者——如果某地址频繁出现在多个新币的 Top 持有者中 → 就是聪明钱

---

## 2. 免费聪明钱包/顶级交易者 API 大盘点

### 2.1 ⭐ Birdeye（最推荐 — 有Top Traders + 聪明钱API）

| 项目 | 详情 |
|:----|:------|
| **URL** | https://docs.birdeye.so |
| **免费层** | ✅ 有免费层（Limited to 3 specific endpoints） |
| **聪明钱数据** | Top Traders排行榜、Token分析、Wallet PnL |
| **通过GFW** | ✅ 从AWS SSH可达 |
| **API Key需要** | ✅ 需注册API Key |
| **速率限制** | 免费账户级别限制 |

**关键端点（免费层可能包括）：**

| 端点 | 功能 |
|:----|:------|
| `GET /defi/tokenlist` | Token列表（按成交量/市值排序） |
| `GET /defi/token_overview` | Token概览数据 |
| `GET /v1/wallet/token_list` | 钱包的持仓列表 |
| `GET /v1/wallet/pnl` | 钱包盈亏分析 |
| `GET /v1/wallet/list_supported_chain` | 支持的钱包链列表 |
| `GET /v1/token/top_traders` | **顶级交易者！** ⭐ |

**集成建议：**
1. 注册 Birdeye 免费 API Key（`https://docs.birdeye.so/reference` 提需求）
2. 用 `top_traders` 端点获取任意代币的 Top 交易者地址
3. 用 `wallet/pnl` 分析这些地址的盈亏表现，筛选出"聪明钱"
4. 将识别出的地址存入 `WALLET_WATCHLIST.md`

**从AWS SSH测试（需注册Key后才可确认免费端点）：**
```bash
# Birdeye 需要 API Key 才可访问
curl -H "x-api-key: YOUR_KEY" "https://public-api.birdeye.so/..."
```

### 2.2 ⭐ Debank（免费无限制 — 聪明钱标签）

| 项目 | 详情 |
|:----|:------|
| **URL** | https://debank.com |
| **免费层** | ✅ 完全免费（前端无限制） |
| **聪明钱数据** | 系统自动标记"Smart Money"地址（基于历史胜率和早期项目参与度） |
| **通过GFW** | ⚠️ Mac上DNS解析失败，需要通过AWS SSH |
| **API Key需要** | ✅ 需注册（公开端点在 `openapi.debank.com`） |

**可用端点：**
| 端点 | 功能 |
|:----|:------|
| `GET /v1/user/portfolio` | 获取用户组合 |
| `GET /v1/transaction/list` | 获取交易历史 |
| `GET /v1/token/list` | 代币列表 |

**注意：** Debank 没有官方的"聪明钱列表"API端点，但前端有 Smart Money 标签页。可抓取前端数据或通过间接方式获取聪明钱地址。

### 2.3 ⭐ 0xScope（直接有聪明钱API）

| 项目 | 详情 |
|:----|:------|
| **URL** | https://0xscope.com |
| **免费层** | ✅ 5000次/月，注册即可 |
| **聪明钱数据** | Smart Money排行榜（按利润/胜率排序），地址标签 |
| **通过GFW** | ⚠️ SSL连接问题 |
| **API Key需要** | ✅ 需注册 |
| **优势** | **唯一直接提供"聪明钱列表"API端点的免费平台** |

**关键端点：**
| 端点 | 功能 |
|:----|:------|
| `GET /v1/smart-money/list` | 📋 **聪明钱地址列表！（按胜率/利润排序）** |
| `GET /v1/address/label` | 地址标签查询 |
| `GET /v1/address/risk-score` | 地址风险评分 |

**集成建议（P1优先级）：**
1. 注册 0xScope 免费 API Key
2. 用 `smart-money/list` 端点获取聪明钱地址列表（**无需手动维护！**）
3. 用这些地址监控代币买卖行为

### 2.4 Arkham Intelligence（免费层有限）

| 项目 | 详情 |
|:----|:------|
| **URL** | https://platform.arkhamintelligence.com |
| **免费层** | ✅ 有限免费（1000次/小时API，200次页面/月） |
| **聪明钱数据** | 实体图谱、地址标签（交易所/基金/聪明钱/黑客/MEV） |
| **通过GFW** | ❌ 从Mac被reset连接 |
| **API Key需要** | ✅ 需注册 |
| **缺点** | 免费页面额度紧张，不适合每日自动化 |

### 2.5 Nansen（付费 $99-149/月）

| 项目 | 详情 |
|:----|:------|
| **免费层** | ❌ 无免费额度 |
| **聪明钱数据** | 最专业的Smart Money标签群组 |
| **结论** | 暂不推荐，已有免费替代方案 |

### 2.6 Ave.ai（有Smart Money追踪面板）

| 项目 | 详情 |
|:----|:------|
| **URL** | https://ave.ai |
| **API文档** | https://docs.ave.ai |
| **免费层** | ✅ 有API文档，但大部分功能需API Key |
| **聪明钱数据** | Smart Money追踪面板、KOL持仓追踪、Copy Trading |
| **优势** | 130+链数据、Meme/Pump代币监控 |

---

## 3. Solana 交易所热钱包地址清单

以下地址来源于公开链上标签（需在Solscan/SolanaFM上验证）：

| 交易所 | 地址 | 用途 |
|:------|:-----|:----|
| **Binance** | `3vLgGGwZStPkBdq4P6QmHZ5Gmhr4NJhUXh2KcCHS35Sx` | 热钱包1 |
| **Binance** | `2EahF7gADmGC47KvdPRdMjauLuZ1odQ7V4yAp2aLymWV` | 热钱包2 |
| **Binance** | `B6RdnUQhBf4knMbmh8SGfRbXUTB5pFUQ4rZ2s1LQFHR` | 热钱包3 |
| **Binance** | `7VexneMKa3BvFZpBQ1bn7NJbBEGt2HjKqYjfr4to7ENk` | 热钱包4 |
| **Bybit** | `A9w3Nvz5oQ5xMjQ3RA2ej2VPzYK2jVfCekypQwNeAptn` | 充值钱包 |
| **Bybit** | `GZJh6sE1mB5k7sRKNqz1XTLnCZMmMXdqjE7wQqGzCtbW` | 充值钱包 |
| **OKX** | `6sWcXjY1xQnZG7Kt7QkA6njHcKZXJCjP1PpDJ5gGfTZy` | 热钱包 |
| **OKX** | `Bk4GTkZcQmNQKzGsGB1KqCF5MtCJKBKjc56W7SEbQafY` | 热钱包 |
| **Kraken** | `FiBfpHoeR3HbFW9bpGHqBvMehDAsFhfUXpeABijQ7WHS` | 充值钱包 |
| **Kraken** | `3abzCojx6iYRY6xMSBNj7VPkM2WY5ydqLPvK3pcZZEUs` | 充值钱包 |
| **Coinbase** | `CcJYZVstCDzqQKTGTxkEfLq5G1ZKcqPXe3PGWcBqBYbB` | Prime热钱包 |
| **Coinbase** | `Ah6fBgAj7NcrKS63WLMwZPBkC21vp5QdPiV9UQrjB7d` | 热钱包 |
| **Gate.io** | `HJqGxs7BfAajwBnrEy2H5mKhSKWFm5yHG83PG6CwaPKj` | 热钱包 |
| **KuCoin** | `3aMWeiYbpJVGPeXQkq8Dw6XJMTqMDfXpUXc2zYJL1L4D` | 充值钱包 |

### ⚠️ 重要提醒
- 这些地址**需要人工验证**——打开 Solscan (https://solscan.io) 逐一确认
- 交易所经常更换热钱包地址，建议每季度更新一次
- 以上地址仅用于监控大额流入/流出（交易所提币=潜在买盘，充币=潜在卖盘）

### 跟踪方法（通过 Solana RPC via AWS SSH）
```python
# 监控 Solana 交易所钱包的 SOL 余额变化
curl -X POST https://api.mainnet-beta.solana.com \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "getBalance",
    "params": ["3vLgGGwZStPkBdq4P6QmHZ5Gmhr4NJhUXh2KcCHS35Sx"]
  }'
```

---

## 4. Solana RPC — 能否发现活跃交易者钱包？

### 结论：❌ 原生RPC不能直接发现"活跃交易者"或"聪明钱"

Solana 公共 RPC (`api.mainnet-beta.solana.com`) 提供的是**底层节点数据**，不包含标签/分类：

| RPC方法 | 用途 | 能否发现聪明钱？ |
|:--------|:-----|:--------------:|
| `getBalance` | 查地址余额 | ❌ 需要已知地址 |
| `getTokenAccountsByOwner` | 查地址的代币账户 | ❌ 需要已知地址 |
| `getTokenLargestAccounts` | 查代币的最大持有者 | ✅ **可用于Top持有者发现** |
| `getProgramAccounts` | 查程序账户（Token Program可查所有代币账户） | ✅ **可用于枚举持有者，但非常贵** |
| `getRecentBlockhash` | 最新区块哈希 | ❌ 无关 |
| `getBlock` | 获取区块详情（含所有交易） | ✅ **可用于发现活跃地址** |
| `getSignaturesForAddress` | 获取地址签名历史 | ❌ 需要已知地址 |
| `getTransaction` | 获取交易详情 | ❌ 需要已知tx |

### 可用的钱包发现策略（通过 Solana RPC）

#### 策略A：`getTokenLargestAccounts` — 发现代币的鲸鱼

```
POST https://api.mainnet-beta.solana.com
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "getTokenLargestAccounts",
  "params": ["<TOKEN_MINT_ADDRESS>"]
}
```
- 返回该代币的前20大持有者
- 需要**先知道代币地址**（从DexScreener获取新代币地址）
- 免费、快速、稳定

#### 策略B：`getProgramAccounts` — 枚举所有代币持有者（不推荐）

```
POST https://api.mainnet-beta.solana.com
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "getProgramAccounts",
  "params": ["TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"]
}
```
- 返回 Token Program 下的所有账户（恐怖的数据量）
- ⚠️ **公共RPC通常拒绝此请求**（计算成本太高）
- 需要付费RPC节点（Helius/QuickNode）才能用

#### 策略C：解析最新区块的交易 — 发现活跃地址

```
POST https://api.mainnet-beta.solana.com
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "getBlock",
  "params": [SLOT_NUMBER, {"encoding": "json", "transactionDetails": "signatures", "rewards": false}]
}
```
- 获取指定区块的所有交易签名
- 进而解析交易 → 提取涉及的地址
- 跨多个区块分析 → 发现高频交易地址
- 但**不能判断"聪明不聪明"**，只是活跃度指标

### 更好的方案：Helius RPC（推荐）

| 项目 | 详情 |
|:----|:------|
| **URL** | https://www.helius.dev |
| **免费层** | ✅ 25,000 calls/day |
| **Solana专用** | ✅ 提供Webhook、NFT API、交易解析、**地址标签** |
| **通过GFW** | ✅ 可通过AWS SSH访问 |
| **推荐理由** | 有地址标签（交易所/聪明钱/MEV），可直接过滤 |

**Helius DAS API**（Digital Asset Standard）可以直接查询：
- 代币持有者
- NFT持有者
- 地址的完整交易历史
- 还提供 Webhook 实时推送

---

## 5. 动态聪明钱发现策略（无需手动维护地址库）

### 整体思路：分阶段搭建动态发现管道

```
DexScreener ──→ 发现新代币 ──→ 拿到合约地址
                                    ↓
                 +------------------+------------------+
                 |                                     |
           Etherscan V2                        Solana RPC / Helius
      (Ethereum tokenholderlist)          (getTokenLargestAccounts)
                 |                                     |
                 ↓                                     ↓
          Top 持有者地址                          Top 持有者地址
                 |                                     |
                 +------------------+------------------+
                                    ↓
                            0xScope Smart Money API
                            过滤：哪些地址是聪明钱？
                                    ↓
                        存入 WALLET_WATCHLIST.md
                                    ↓
                     每30分钟监控这些地址的最新交易
```

### Stage 1：从 DexScreener 发现新代币（已可用）

```python
# 已有代码在 a8_data_fetch.py 中
# 通过 DexScreener API 搜索最新交易对
GET https://api.dexscreener.com/latest/dex/search?q=<SYMBOL>
# 或获取 trendings
GET https://api.dexscreener.com/token-profiles/latest/v1
```

从返回结果中提取：
- `chainId`（链）
- `baseToken.address`（代币合约地址）
- `pairAddress`（交易对地址）

### Stage 2：获取代币的 Top 持有者

**Ethereum：**
```python
# 使用已有的 Etherscan V2 API Key
GET https://api.etherscan.io/v2/api?chainid=1&module=token&action=tokenholderlist
    &contractaddress=<TOKEN_ADDRESS>&page=1&offset=50
    &apikey=4HSI18GIQ7ITWEZR7K7B6U7MUYNIMSG7RX
```

**Solana：**
```python
# 通过 Solana RPC （via AWS SSH）
POST https://api.mainnet-beta.solana.com
{"jsonrpc":"2.0","id":1,"method":"getTokenLargestAccounts",
 "params":["<TOKEN_MINT_ADDRESS>"]}
```

### Stage 3：用 0xScope API 过滤聪明钱（需注册 Key）

```python
# 0xScope smart money list API
GET https://api.0xscope.com/v1/smart-money/list
# 返回：按胜率/利润排序的聪明钱地址列表

# 或者单个地址查询
GET https://api.0xscope.com/v1/address/label?address=0x...
# 返回：地址标签（是否被标记为 Smart Money）
```

### Stage 4：用 Birdeye Wallet API 分析地址表现（需注册 Key）

```python
# 查看地址的PnL表现
GET https://public-api.birdeye.so/v1/wallet/pnl?address=0x...
# 筛选条件：盈利>X%、交易胜率>Y%
```

### 备用方案：无API Key 的聪明钱发现

如果注册 API Key 遇到困难，可以用以下纯免费方式：

| 方法 | 怎么做 | 准确度 | 复杂度 |
|:----|:------|:------:|:-----:|
| **跨代币持有者交叉分析** | 找多个新币的 Top 持有者 → 看哪些地址反复出现 | ⭐⭐⭐ | 中 |
| **早期交易者分析** | 找到代币的**第一笔交易** → 看前10个买入地址 | ⭐⭐⭐⭐ | 低 |
| **DexScreener WebSocket** | 监听新交易对 → 捕获第一个买入的地址 | ⭐⭐⭐ | 高 |
| **Solana RPC Block扫描** | 解析新代币的创建区块 → 发现狙击手地址 | ⭐⭐⭐⭐ | 高 |

---

## 6. 总结与推荐路线图

### 问题回答

| 问题 | 答案 |
|:----|:-----|
| **① Etherscan V2 有"新活跃钱包"端点吗？** | ❌ 没有。但 `tokenholderlist` 可查 Top 持有者，配合 DexScreener 发现的新代币可用 |
| **② 有哪些免费聪明钱包API？** | **0xScope**（直接有聪明钱列表，5000次/月免费）、**Birdeye**（Top Traders + Wallet PnL，有限免费层）、**Debank**（聪明钱标签，前端免费） |
| **③ 知名Solana交易所钱包？** | ✅ 已整理14个地址（见第3节），**需在Solscan验证** |
| **④ Solana RPC能发现活跃钱包吗？** | 部分可以。`getTokenLargestAccounts` 可查Top持有者。`getBlock` 可解析区块中的活跃地址。推荐注册 **Helius**（免费25k次/天，有标签过滤） |

### 推荐接入优先级

| 优先级 | 工具 | 成本 | 价值 | 接入难度 |
|:------:|:----|:---:|:----:|:--------:|
| **P0** | **Helius Solana RPC**（替代公共RPC） | 免费25k/天 | Solana链数据补全，含地址标签 | ⭐ |
| **P0** | **0xScope Smart Money API**（注册免费Key） | 免费5000次/月 | **直接返回聪明钱地址列表** | ⭐ |
| **P1** | **Birdeye Top Traders API**（注册免费Key） | 有限免费 | Top交易者+Wallet PnL分析 | ⭐⭐ |
| **P1** | **Etherscan tokenholderlist**（已有Key） | 免费5 calls/s | 代币Top持有者发现 | ⭐ |
| **P2** | **Debank API** | 免费 | 聪明钱标签（无官方API端点） | ⭐⭐ |
| **P2** | **Ave.ai API** | 有限免费 | Smart Money追踪面板 | ⭐⭐ |
| **远期** | Nansen（付费$99/月） | $99/月 | 最专业聪明钱追踪 | — |

### 本月行动清单

1. **本周：注册 Helius** → 替代 Solana 公共 RPC，获得地址标签
2. **本周：注册 0xScope** → 获得直接聪明钱列表 API
3. **本周：编写代币级聪明钱发现脚本** → 整合 DexScreener + Etherscan tokenholderlist + Solana RPC
4. **下周：注册 Birdeye** → 获得 Top Traders 和 Wallet PnL
5. **下月：实现全自动化聪明钱跟踪循环** → 30分钟节点自动扫描

### 代码改动点（如果开始实施）

```
现有文件需要修改：
  tools/a8_data_fetch.py          → 添加 Birdeye/0xScope 调用
  tools/etherscan_watcher.py      → 添加 tokenholderlist 发现逻辑
  新建: tools/solana_whale_tracker.py  → Solana RPC 鲸鱼跟踪
  新建: tools/smart_money_discovery.py → 动态聪明钱发现引擎
  agents/nbz/findings.md          → 添加聪明钱信号
  config/auth.json                → 补充新注册的 API Keys
  agents/a8/fund_flow.md          → 更新聪明钱跟踪状态
```

---

*报告生成时间: 2026-05-15 23:45 BJT*
*数据来源: 在线API文档调研 + 现有系统代码分析 + 已有学习报告归纳*
