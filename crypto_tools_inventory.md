# Crypto 数据工具/API/Skill 全网清单

> 整理日期：2026-05-12
> 用途：为9 Agent 交易系统提供真实数据源，按类别划分

---

## 目录

1. [综合市场数据 API](#1-综合市场数据-api)
2. [链上数据分析](#2-链上数据分析)
3. [交易平台 API（CEX）](#3-交易平台-apicex)
4. [DEX / DeFi 数据](#4-dex--defi-数据)
5. [NFT 数据](#5-nft-数据)
6. [区块浏览器 / 节点 API](#6-区块浏览器--节点-api)
7. [新闻 / 情绪 / 社交数据](#7-新闻--情绪--社交数据)
8. [MCP / AI Agent Skills（直接可用的 Skill 工具）](#8-mcp--ai-agent-skills直接可用的-skill-工具)
9. [技术分析 / 量化数据](#9-技术分析--量化数据)
10. [宏观 / 汇率 / 经济数据](#10-宏观--汇率--经济数据)
11. [数据聚合平台（SQL 查询）](#11-数据聚合平台sql-查询)

---

## 1. 综合市场数据 API

| 工具名称 | 网址 | 用途 | 付费 | 免费额度 | 需注册 |
|---------|------|------|------|---------|--------|
| **CoinGecko** | https://www.coingecko.com/api | 实时/历史价格、市值、交易量、开发者/社交数据，覆盖 10000+ 币种 | 付费 (Pro) | ✅ 有免费 Demo API（30 calls/min，限制较多） | ✅ 免费 Key |
| **CoinMarketCap** | https://coinmarketcap.com/api/ | 实时价格、市值排名、历史数据、币种信息 | 付费 (Starter $29/月起) | ❌ 无免费额度，需付费 | ✅ 需注册 |
| **CoinCap** | https://docs.coincap.io/ | 实时价格、市场数据，轻量级 REST API + WebSocket | 免费 | ✅ 完全免费，无 API Key 需（但支持 x402 微支付） | ❌ 无需注册 |
| **CoinPaprika** | https://api.coinpaprika.com | 价格、市值、ICO数据、团队信息、白皮书链接 | 免费 | ✅ 完全免费，无速率限制 | ❌ 无需注册 |
| **CryptoCompare** | https://www.cryptocompare.com/api | 价格、历史 OHLCV、社交数据、新闻、矿池数据 | 付费 (Pro) | ✅ 有免费层（100k calls/月） | ✅ 需注册 |
| **Nomics** | https://nomics.com/docs/ | 历史和实时价格、市场数据、交易所数据 | 付费 | ✅ 有免费层（有限 calls） | ✅ 需注册 Key |
| **Messari** | https://messari.io/api | 机构级研究数据、资产基本面、市场数据 | 付费 | ✅ 免费层（基础数据有限） | ✅ 需注册 |
| **CoinRanking** | https://developers.coinranking.com/api | 实时价格、市场数据 | 付费 | ✅ 有免费层 | ✅ 需注册 |
| **CoinAPI** | https://docs.coinapi.io/ | 聚合 50+ 交易所数据、历史价格 | 付费 ($99/月起) | ❌ 无免费额度 | ✅ 需注册 |
| **Coinlib** | https://coinlib.io/apidocs | 实时价格、市场数据 | 付费 | ✅ 有免费层（200 calls/天） | ✅ 需注册 Key |
| **Coinlore** | https://www.coinlore.com/cryptocurrency-data-api | 实时价格、市值、交易量 | 免费 | ✅ 完全免费 | ❌ 无需注册 |
| **BitcoinAverage** | https://apiv2.bitcoinaverage.com/ | 专业级数字资产价格数据 | 付费 | ❌ 无免费额度 | ✅ 需注册 |
| **BraveNewCoin** | https://bravenewcoin.com/developers | 200+ 交易所实时和历史数据 | 付费 | ❌ 无免费额度 | ✅ 需注册 |
| **CoinStats** | https://documenter.getpostman.com/view/5734027/RzZ6Hzr3 | 加密追踪器数据 | 免费 | ✅ 免费 | ❌ 无需注册 |
| **CryptingUp** | https://www.cryptingup.com/apidoc | 行情数据 | 免费 | ✅ 免费 | ❌ 无需注册 |
| **Finage** | https://finage.co.uk | 实时股票、外汇、加密货币数据 | 付费 | ✅ 有免费层 | ✅ 需注册 |
| **Finnhub** | https://finnhub.io/docs/api | 实时 REST/WebSocket 股票、外汇、加密货币数据 | 付费 | ✅ 有免费层（60 calls/min） | ✅ 需注册 |
| **Yahoo Finance API** | https://www.yahoofinanceapi.com/ | 股票和加密货币实时数据 | 付费 | ✅ 有免费层（有限） | ✅ 需注册 Key |

---

## 2. 链上数据分析

| 工具名称 | 网址 | 用途 | 付费 | 免费额度 | 需注册 |
|---------|------|------|------|---------|--------|
| **Glassnode** | https://glassnode.com/ | 链上指标（活跃地址、持币者分布、交易所流量、MVRV 等） | 付费 | ✅ 有限免费数据（基础指标） | ✅ 需注册 |
| **Dune Analytics** | https://dune.com/ | 链上 SQL 查询平台，支持 Ethereum、Solana、Polygon 等多链 | 付费 (Pro) | ✅ 免费查询（有限制，结果可公开） | ✅ 需注册 |
| **Covalent** | https://www.covalenthq.com/docs/api/ | 多链数据聚合器（余额、交易、NFT、历史数据） | 付费 | ✅ 有免费层（100k calls/月） | ✅ 需注册 Key |
| **Nansen** | https://www.nansen.ai/ | 链上标签、聪明钱追踪、资金流向分析 | 付费（$99/月起） | ❌ 无免费额度 | ✅ 需注册 |
| **Arkham Intelligence** | https://platform.arkhamintelligence.com/ | 链上实体分析、地址标签、交易图谱 | 付费 | ✅ 有限免费访问 | ✅ 需注册 |
| **Chainalysis** | https://www.chainalysis.com/ | 机构级链上合规和分析 | 付费（企业定价） | ❌ 无免费额度 | ✅ 需注册 |
| **Bitquery** | https://bitquery.io/ | 多链 GraphQL API（交易、转账、DEX、NFT 数据） | 付费 | ✅ 有免费层（有限 calls） | ✅ 需注册 |
| **Etherscan API** | https://etherscan.io/apis | 以太坊浏览器 API（交易、余额、合约、ABI） | 付费 (Pro) | ✅ 免费层（5 calls/sec） | ✅ 需注册 Key |
| **Solscan API** | https://public-api.solscan.io/ | Solana 区块链浏览器 API | 免费 | ✅ 免费 | ✅ 需注册 |
| **BSCScan API** | https://bscscan.com/apis | BNB Chain 浏览器 API | 付费 | ✅ 免费层（5 calls/sec） | ✅ 需注册 Key |
| **Mempool.space** | https://mempool.space/api | 比特币交易费、内存池、区块数据 | 免费 | ✅ 完全免费 | ❌ 无需注册 |
| **Blockchair** | https://blockchair.com/api | 多链区块浏览器 API（BTC、ETH、BSC 等 18 条链） | 付费 | ✅ 免费层（有限 calls） | ✅ 需注册 |
| **Etherscan (The Graph)** | https://thegraph.com/ | 去中心化索引协议，GraphQL 查询区块链数据 | 付费（按查询付费） | ✅ 免费查询（有限额度） | ✅ 需注册 |
| **Watchdata** | https://docs.watchdata.io | 简单可靠的以太坊区块链 API | 付费 | ✅ 免费层 | ✅ 需注册 Key |

---

## 3. 交易平台 API（CEX）

| 工具名称 | 网址 | 用途 | 付费 | 免费额度 | 需注册 |
|---------|------|------|------|---------|--------|
| **Binance API** | https://github.com/binance/binance-spot-api-docs | 现货/合约交易、K线、深度、账户管理 | 免费（交易收手续费） | ✅ 市场数据免费 | ✅ 需注册 |
| **Binance MCP** | https://github.com/nirholas/Binance-MCP | MCP 服务器，封装 Binance API（现货、钱包、Staking、理财、矿池） | 免费 | ✅ 开源免费 | ✅ 需 Binance Key |
| **Bybit API** | https://bybit-exchange.github.io/docs/ | 现货/合约交易、K线、账户管理 | 免费（交易收手续费） | ✅ 市场数据免费 | ✅ 需注册 |
| **OKX API** | https://www.okx.com/docs/ | 现货/合约/期权交易 | 免费（交易收手续费） | ✅ 市场数据免费 | ✅ 需注册 |
| **Kraken API** | https://docs.kraken.com/rest/ | 现货/期货交易 | 免费（交易收手续费） | ✅ 市场数据免费 | ✅ 需注册 |
| **Coinbase API** | https://developers.coinbase.com | 现货交易、价格、钱包 | 免费（交易收手续费） | ✅ 市场数据免费 | ✅ 需注册 |
| **KuCoin API** | https://docs.kucoin.com/ | 现货/合约交易 | 免费（交易收手续费） | ✅ 市场数据免费 | ✅ 需注册 |
| **Gate.io API** | https://www.gate.io/api2 | 现货/合约/杠杆交易 | 免费（交易收手续费） | ✅ 市场数据免费 | ✅ 需注册 |
| **Coinbase Pro (Advanced Trade)** | https://docs.pro.coinbase.com/ | 高级交易、市场数据 | 免费（交易收手续费） | ✅ 市场数据免费 | ✅ 需注册 |
| **Bitfinex API** | https://docs.bitfinex.com/docs | 现货/衍生品交易 | 免费（交易收手续费） | ✅ 市场数据免费 | ✅ 需注册 |
| **Huobi API** | https://huobiapi.github.io/docs | 现货/合约交易 | 免费（交易收手续费） | ✅ 市场数据免费 | ✅ 需注册 |
| **Crypto.com Exchange API** | https://exchange-docs.crypto.com/ | 现货/合约交易 | 免费（交易收手续费） | ✅ 市场数据免费 | ✅ 需注册 |
| **Robinhood Crypto API** | https://robinhood-mcp-server.vercel.app/ | Robinhood 加密货币交易 | 免费（交易收手续费） | ✅ 市场数据免费 | ✅ 需注册 |
| **Gemini API** | https://docs.gemini.com/rest-api/ | 现货交易 | 免费（交易收手续费） | ✅ 市场数据免费 | ✅ 需注册 |
| **Poloniex API** | https://docs.poloniex.com | 现货交易 | 免费（交易收手续费） | ✅ 市场数据免费 | ✅ 需注册 |

---

## 4. DEX / DeFi 数据

| 工具名称 | 网址 | 用途 | 付费 | 免费额度 | 需注册 |
|---------|------|------|------|---------|--------|
| **DexPaprika** | https://dexpaprika.com/ | DEX 数据（流动性、交易对、交易量），CoinPaprika 的 DeFi 分支 | 免费 | ✅ 完全免费 | ❌ 无需注册 |
| **DexScreener** | https://dexscreener.com/ | 实时 DEX 价格、图表、新币发现 | 免费 | ✅ 完全免费 | ❌ 无需注册 |
| **DefiLlama** | https://defillama.com/docs/api | TVL、收益、A 池数据、跨链 DeFi 数据 | 免费 | ✅ 完全免费 | ❌ 无需注册 |
| **Dune Analytics** | https://dune.com/ | 链上 SQL -> DeFi 项目数据深度查询 | 付费 (Pro) | ✅ 免费查询 | ✅ 需注册 |
| **The Graph** | https://thegraph.com/ | 去中心化子图网络，索引 DeFi 协议数据 | 付费（按查询） | ✅ 有限免费试用 | ✅ 需注册 |
| **0x API** | https://0x.org/api | DEX 聚合路由、报价 | 付费（收手续费） | ✅ 市场数据免费 | ✅ 需注册 Key |
| **1inch API** | https://1inch.io/api/ | DEX 聚合、最佳价格路由 | 免费（收手续费） | ✅ 市场数据免费 | ❌ 无需注册 |
| **dYdX API** | https://docs.dydx.exchange/ | 去中心化衍生品交易 | 免费（交易收费） | ✅ 市场数据免费 | ✅ 需注册 |
| **Zapper API** | https://zapper.xyz/ | DeFi 组合追踪 | 付费 | ❌ 有限免费 | ✅ 需注册 |
| **Zerion API** | https://zerion.io/ | 钱包/DeFi 组合数据 | 付费 | ❌ 有限免费 | ✅ 需注册 |
| **Debank API** | https://debank.com/ | 多链 DeFi 组合追踪、协议数据 | 付费 | ✅ 免费层 | ✅ 需注册 Key |
| **DefiYield** | https://defiyield.app/ | DeFi 收益分析、风险评分 | 免费 | ✅ 免费 | ❌ 无需注册 |
| **Philidor Labs MCP** | https://github.com/Philidor-Labs/philidor-mcp | DeFi 金库风险分析，700+ 金库风险评分对比 | 免费 | ✅ 开源免费 | ❌ 无需 Key |

---

## 5. NFT 数据

| 工具名称 | 网址 | 用途 | 付费 | 免费额度 | 需注册 |
|---------|------|------|------|---------|--------|
| **OpenSea API** | https://docs.opensea.io/ | 最大的 NFT 市场 API（集合、出价、交易） | 付费 | ✅ 免费层（有限 calls） | ✅ 需注册 Key |
| **Reservoir** | https://reservoir.tools/ | NFT 聚合交易、流动性数据 | 付费 | ✅ 免费层 | ✅ 需注册 |
| **icy.tools** | https://developers.icy.tools/ | GraphQL NFT API（交易、趋势、集合） | 付费 | ✅ 有限免费 | ✅ 需注册 Key |
| **NFTPort** | https://docs.nftport.xyz/ | 多链 NFT API（元数据、交易、所有权） | 付费 | ✅ 免费层（500 calls/月） | ✅ 需注册 |
| **Alchemy NFT API** | https://www.alchemy.com/nft-api | NFT 数据（所有权、元数据、转账） | 付费 | ✅ 免费层（300M compute/月） | ✅ 需注册 |
| **Moralis** | https://moralis.io/ | 多链 NFT / Token API（价格、余额、转账） | 付费 | ✅ 免费层（40k calls/月） | ✅ 需注册 |
| **SimpleHash** | https://simplehash.com/ | 跨链 NFT API（元数据、稀有度、交易） | 付费 | ✅ 免费层 | ✅ 需注册 |
| **Bitquery NFT API** | https://bitquery.io/ | NFT 交易、借贷、出价 GraphQL API | 付费 | ✅ 免费层 | ✅ 需注册 |

---

## 6. 区块浏览器 / 节点 API

| 工具名称 | 网址 | 用途 | 付费 | 免费额度 | 需注册 |
|---------|------|------|------|---------|--------|
| **Infura** | https://infura.io/product/ethereum | 以太坊/IPFS 节点服务 | 付费 | ✅ 免费层（100k calls/天） | ✅ 需注册 |
| **Alchemy** | https://docs.alchemy.com/alchemy/ | 多链节点服务 + NFT API + WebSocket | 付费 | ✅ 免费层（300M compute units/月） | ✅ 需注册 |
| **QuickNode** | https://www.quicknode.com/ | 多链节点服务（Ethereum、Solana、Polygon 等） | 付费（$9/月起） | ✅ 免费层（有限） | ✅ 需注册 |
| **Ankr** | https://www.ankr.com/ | 多链 RPC 节点服务 | 付费 | ✅ 免费公共 RPC（有限速率） | ❌ 无需注册（公开 RPC） |
| **Blockdaemon** | https://blockdaemon.com/ | 机构级节点服务 | 付费（企业） | ❌ 无免费额度 | ✅ 需注册 |
| **NOWNodes** | https://nownodes.io/ | 区块链节点 API（50+ 链） | 付费（$0.5/天起） | ✅ 免费层（有限） | ✅ 需注册 |
| **GetBlock** | https://getblock.io/ | 区块链节点 API | 付费（$1.5/月起） | ✅ 免费层（40k calls/天） | ✅ 需注册 |
| **Chainstack** | https://chainstack.com/ | 托管区块链节点 | 付费（$49/月起） | ✅ 免费层 | ✅ 需注册 |
| **Blockfrost** | https://blockfrost.io/ | Cardano 节点 API | 付费 | ✅ 免费层 | ✅ 需注册 Key |
| **Helius** | https://helius.xyz/ | Solana RPC + API（webhooks、NFT、交易） | 付费 | ✅ 免费层（25k calls/日） | ✅ 需注册 |
| **Tatum** | https://tatum.io/ | 多链区块链 API（50+ 链，地址生成、交易、NFT） | 付费 | ✅ 免费层（5000 credits） | ✅ 需注册 |

---

## 7. 新闻 / 情绪 / 社交数据

| 工具名称 | 网址 | 用途 | 付费 | 免费额度 | 需注册 |
|---------|------|------|------|---------|--------|
| **Crypto News API** | https://cryptonews-api.com/ | 加密新闻聚合、情绪分析 | 付费 | ✅ 免费层（有限 calls） | ✅ 需注册 |
| **Crypto-Vision** | https://github.com/nirholas/crypto-vision | 最全面的加密货币 API：实时价格、OHLCV、订单簿、市值、DeFi TVL 和收益 | 免费 | ✅ 完全免费（开源） | ❌ 无需注册 |
| **nirholas/cryptocurrency.cv** | https://github.com/nirholas/cryptocurrency.cv | 免费加密新闻聚合器（RSS/Atom/JSON）、BTC、ETH、DeFi、Solana、Altcoin 新闻 | 免费 | ✅ 完全免费，无需 Key | ❌ 无需注册 |
| **LunarCrush** | https://lunarcrush.com/ | 社交情绪分析、影响力指标、社交活动数据 | 付费 | ✅ 免费层（有限） | ✅ 需注册 |
| **Santiment** | https://santiment.net/ | 链上 + 社交 + 市场数据（开发活动、社交量、情绪） | 付费 | ✅ 有限免费数据 | ✅ 需注册 |
| **The Tie** | https://www.thetie.io/ | 机构级加密新闻情绪、社交媒体数据 | 付费（企业） | ❌ 无免费额度 | ✅ 需注册 |
| **Lunar API** | https://lunarapi.com/ | 新闻、情绪、社交媒体数据 | 付费 | ✅ 免费层 | ✅ 需注册 |
| **CoinTelegraph RSS** | https://cointelegraph.com/rss | 加密新闻 RSS 源 | 免费 | ✅ 完全免费 | ❌ 无需注册 |
| **NewsAPI** | https://newsapi.org/ | 全球新闻聚合（可筛选加密货币） | 付费 | ✅ 免费层（100 calls/天） | ✅ 需注册 |

---

## 8. MCP / AI Agent Skills（直接可用的 Skill 工具）

| 工具名称 | 网址 | 用途 | 付费 | 免费额度 | 需注册 |
|---------|------|------|------|---------|--------|
| **CoinCap MCP** | https://github.com/QuantGeekDev/coincap-mcp | CoinCap API 的 MCP 封装，获取实时加密数据 | ⭐ 92 | ✅ 免费 | ❌ 无需注册 |
| **MCP Crypto Price** | https://github.com/truss44/mcp-crypto-price | 通过 CoinCap 提供实时加密分析的 MCP 服务器 | ⭐ 39 | ✅ 免费 | ❌ 无需注册 |
| **Binance MCP** | https://github.com/nirholas/Binance-MCP | Binance 全套 API（现货、理财、Staking、矿池）MCP 封装 | ⭐ 25 | ✅ 免费（开源） | ✅ 需 Binance Key |
| **Binance-US MCP** | https://github.com/nirholas/Binance-US-MCP | Binance.US MCP 封装 | ⭐ 21 | ✅ 免费（开源） | ✅ 需 Binance Key |
| **CEX Watch MCP** | https://github.com/Zanecex101/cex-watch-mcp | 监控多家 CEX 的公开数据，无后端、无 API Key | ⭐ 22 | ✅ 免费（开源 + 公开端点） | ❌ 无需注册 |
| **CoinPaprika Claude Plugin** | https://github.com/coinpaprika/claude-marketplace | 29+14 MCP 工具，无需 API Key，免费的加密市场和 DeFi 分析 | ⭐ 6 | ✅ 完全免费，无需 Key | ❌ 无需注册 |
| **Robinhood MCP** | https://github.com/rohitsingh-iitd/robinhood-mcp-server | Robinhood Crypto API 的 MCP 封装 | ⭐ 30 | ✅ 免费（开源） | ✅ 需 Robinhood Key |
| **BNB Chain MCP** | https://github.com/nirholas/bnbchain-mcp | BNB Chain 开发工具（DeFi 交易、DEX Swap、合约部署、Token 操作） | ⭐ 28 | ✅ 免费（开源） | ✅ 需 Key |
| **Crypto-Ex-MCP** | https://github.com/sydowma/crypto_exchange_mcp | Bybit/OKX/Binance 公开 API 的 MCP 统一接口 | ⭐ 6 | ✅ 免费（开源） | ❌ 公开数据无需 Key |
| **Surf MCP** | https://github.com/asksurf-ai/surf-mcp | Surf 加密数据 API 的 MCP，动态生成工具 | ⭐ 4 | ✅ 免费 | ❌ 无需注册 |
| **Dune Sim API MCP** | https://github.com/duneanalytics/sim-api-mcp | Dune 链上数据 Sim API 的 MCP 工具 | ⭐ 2 | ✅ 免费 | ✅ 需 Dune Key |
| **Philidor MCP** | https://github.com/Philidor-Labs/philidor-mcp | DeFi 金库风险分析 MCP（700+ 金库） | ⭐ 4 | ✅ 免费，无需 Key | ❌ 无需注册 |
| **Alpha Vantage MCP** | https://github.com/deepsuthar496/alpha-ventage-mcp | 股票、加密货币、市场指数的实时数据 MCP | ⭐ 4 | ✅ 免费 | ✅ 需 Key |
| **Coinbase MCP Server** | https://github.com/visusnet/coinbase-mcp-server | Coinbase Advanced Trading API 的 MCP 封装 | ⭐ 4 | ✅ 免费（开源） | ✅ 需 Coinbase Key |

---

## 9. 技术分析 / 量化数据

| 工具名称 | 网址 | 用途 | 付费 | 免费额度 | 需注册 |
|---------|------|------|------|---------|--------|
| **TradingView API** | https://www.tradingview.com/rest-api-spec/ | 图表数据、技术指标、筛选器 | 付费（企业） | ❌ 有限公共数据 | ✅ 需注册 |
| **Technical Analysis API** | https://technical-analysis-api.com | 结合价格和技术指标 | 付费 | ✅ 免费层 | ✅ 需注册 Key |
| **Alpha Vantage** | https://www.alphavantage.co/ | 股票、外汇、加密货币技术指标 | 付费 | ✅ 免费层（25 calls/天） | ✅ 需注册 Key |
| **TAAPI.io** | https://taapi.io/ | 200+ 技术指标（RSI、MACD、布林带等） | 付费 | ✅ 免费层（有限 calls） | ✅ 需注册 |
| **Finta (Python)** | https://github.com/peerchemist/finta | Python 技术指标计算库（免费） | 免费 | ✅ 开源免费 | ❌ 无需注册 |
| **ta-lib** | https://github.com/mrjbq7/ta-lib | Python/C++ 技术分析库（200+ 指标） | 免费 | ✅ 开源免费 | ❌ 无需注册 |

---

## 10. 宏观 / 汇率 / 经济数据

| 工具名称 | 网址 | 用途 | 付费 | 免费额度 | 需注册 |
|---------|------|------|------|---------|--------|
| **Exchangerate.host** | https://exchangerate.host | 实时法币/加密货币汇率 | 免费 | ✅ 免费 | ❌ 无需注册 |
| **ExchangeRates API** | https://exchangeratesapi.io | 汇率换算、历史数据 | 付费 | ✅ 免费层 | ✅ 需注册 |
| **FRED API** | https://fred.stlouisfed.org/docs/api/ | 美联储经济数据（利率、通胀、GDP 等） | 免费 | ✅ 完全免费 | ✅ 需注册 Key |
| **Open Exchange Rates** | https://openexchangerates.org/ | 实时和历史汇率 | 付费 | ✅ 免费层（1000 calls/月） | ✅ 需注册 |
| **CoinDesk BPI** | https://old.coindesk.com/coindesk-api/ | 比特币价格指数 | 免费 | ✅ 完全免费 | ❌ 无需注册 |
| **Yahoo Finance (yfinance)** | https://pypi.org/project/yfinance/ | Python 库：股票/加密货币历史数据 | 免费 | ✅ 开源免费 | ❌ 无需注册 |

---

## 11. 数据聚合平台（SQL 查询）

| 工具名称 | 网址 | 用途 | 付费 | 免费额度 | 需注册 |
|---------|------|------|------|---------|--------|
| **Dune Analytics** | https://dune.com/ | 链上数据 SQL 查询引擎（Eth、Solana、Polygon 等） | 付费 (Pro) | ✅ 免费查询（结果公开） | ✅ 需注册 |
| **Flipside Crypto** | https://flipsidecrypto.xyz/ | 链上数据 SQL 查询 + 仪表盘 | 付费 | ✅ 免费查询有额度 | ✅ 需注册 |
| **Google BigQuery Public Datasets** | https://cloud.google.com/bigquery/public-data | Google 公开数据集（BTC、ETH 交易数据） | 付费（按查询量） | ✅ 每月 1TB 免费 | ✅ 需 Google Cloud |
| **Footprint Analytics** | https://footprint.network/ | 跨链数据分析和 SQL 查询 | 付费 | ✅ 免费层 | ✅ 需注册 |
| **Bitquery** | https://bitquery.io/ | 多链 GraphQL + SQL 数据聚合 | 付费 | ✅ 免费层 | ✅ 需注册 |

---

## 快速推荐：9 Agent 系统建议使用的 Top 优先级

### 🔥 立即可用（免费、无需注册）
1. **CoinGecko API** - 最全面的市场数据基础源
2. **CoinCap API** - 轻量级实时价格 + 无注册即可用
3. **CoinPaprika** - 价格、市值、ICO 数据，零门槛
4. **DefiLlama API** - TVL 和 DeFi 协议数据
5. **DexScreener** - DEX 实时交易对数据
6. **nirholas/cryptocurrency.cv** - 免费新闻聚合
7. **CoinPaprika Claude Plugin** - Agent 可直接调用的 MCP 工具
8. **CoinCap MCP** - MCP 封装的实时数据

### 🛡️ 建议注册免费 Key（免费额度充足）
9. **Alchemy** - 节点 + NFT 数据（300M compute/月免费）
10. **Covalent** - 多链聚合数据（100k calls/月免费）
11. **Etherscan API** - 以太坊链上数据（5 calls/sec 免费）
12. **Binance API** - 交易所市场数据（完全免费）

---

## 使用的搜索来源

- GitHub API 搜索（repositories 关键词：crypto data API, mcp server crypto, onchain data, defi data tool, nft data api）
- public-apis GitHub 仓库（加密货币和区块链分类）
- 各个官方文档站点的直接查阅
- CoinCap 官方文档站点
