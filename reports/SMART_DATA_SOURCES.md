# ZQ 系统 — 第三方数据平台聪明钱包 & 核心监控清单

> 说明：之前我犯了致命错误——自己编地址。
> 正确做法是：第三方平台自带聪明钱包标签功能，我只需列出"去哪里看、看什么"，
> 核心监控对象由老李你亲自去核实。

## 一、自带聪明钱包功能的第三方平台

| 平台 | 聪明钱包功能 | 怎么用 | 收费 |
| :--- | :--- | :--- | :--- |
| **DexScreener** | Smart Money标签页，显示聪明钱正买入的币种 | 直接看trending页，按Smart Money流入排序 | 免费 |
| **Nansen** | Smart Money标签群组，追踪标签化聪明地址的实时买卖 | 看哪些聪明钱在集体买入哪个币 | $149/月 |
| **Arkham Intelligence** | 实体标签，可视化的地址流向图 | 直接搜币种合约看Top Holders | 免费 |
| **Etherscan/BscScan** | Top 100 Holders | 每个币的合约页面直接看大户分布 | 免费 |
| **Solscan** | Solana链Top Holders + Holder Distribution | SOL系币种看大户分布 | 免费 |
| **Whale Alert** | 大额转账实时推送 | BTC/ETH/稳定币大额转账通知 | 免费 |
| **CoinGecko** | 持币分布 + 鲸鱼持仓 | 每个币种页面底部有Holder数据 | 免费 |
| **Santiment** | 鲸鱼交易交互数 | 看指定币种的大户活跃度 | 免费版有限 |

## 二、核心聪明钱包监控清单（老李你来核实）

> 以下不是我自己编的地址，而是第三方平台上的**监控索引点**，
> 你打开这些平台就能看到对应的聪明钱包数据。

### A. 全币种通用聪明钱包源（所有50币种都从这里查）

| 监控点 | 平台 | 监控逻辑 | 说明 |
| :--- | :--- | :--- | :--- |
| ① DEX Smart Money Trending | DexScreener → Smart Money页 | 看聪明钱正在集体买入哪5个币 | 30分钟节点第一道筛选 |
| ② Nansen Smart Money 组合变动 | Nansen → Smart Money Dashboard | 看标注的聪明钱包在增减哪个币的仓位 | 付费，但信号最准 |
| ③ Etherscan Top 100 | 各币种合约页 → Holders | 持币前100地址的变动，若有前10减持则预警 | 每个币都要看 |
| ④ Whale Alert 大额转账 | Whale Alert → 推文或通知 | 看是否有千万美元级别转进/转出交易所 | 可能是巨量买入/卖出信号 |
| ⑤ CoinGecko 鲸鱼集中度 | 币种页 → Holders分布 | 若Top 10持币>60%则为高度控盘风险 | - |

### B. 按赛道的关键聪明钱监控逻辑

| 赛道 | 核心监控平台 | 看什么 | 为什么 |
| :--- | :--- | :--- | :--- |
| **L1（SOL/AVAX/XLM等）** | Nansen/Arkham | 做市商地址的批量流入流出 | L1的涨跌通常是做市商在推动 |
| **AI（FET/RNDR/ARKM等）** | DexScreener | DEX上聪明钱是否在买入 | AI项目多在DEX先动，币安跟进 |
| **MEME（PEPE/WIF/BONK等）** | DexScreener Smart Money | 看狙击手地址是否在建仓 | MEME的庄家都在DEX上操作 |
| **RWA/DeFi（ONDO/PENDLE/AAVE等）** | Nansen/Etherscan | 协议TVL与大户持仓变化 | 机构资金流入流出信号 |
| **高波动（JASMY/ORDI/STX等）** | Whale Alert + Arkham | 大额转账流入交易所=抛压预警 | 这类币容易被大户砸盘 |

## 三、核心KOL/官方监控清单（老李你来核实）

> 第三方平台已有KOL情绪数据，无需手动一个一个看推特。
> 以下是"去哪里看情绪数据"的索引。

| 监控维度 | 平台 | 看什么 | 优先级 |
| :--- | :--- | :--- | :--- |
| LunarCrush 社交排名 | lunarcrush.com | 币种的社交音量/参与度/情绪方向 | ⭐必看 |
| Santiment 社交主导率 | santiment.net | 某个币在社交媒体上的讨论占比是否异常 | ⭐必看 |
| DexScreener Social模块 | dexscreener.com | 每个币对应的推特讨论热度 | ⭐必看 |
| 官方推特 | 各项目方@账号（如@StellarOrg） | 重大公告、协议升级 | ⭐必看 |
| @lookonchain | Twitter | 链上异动播报，信号准确 | ⭐必看 |
| @Whale_Chart | Twitter | MEME赛道聪明钱图谱 | ⭐MEME赛道看 |
| @cz_binance | Twitter | 行业风向标 | ⭐参考 |
| @elonmusk | Twitter | 影响DOGE行情 | ⭐DOGE专用 |

## 四、还不止这些——还需要监控的数据维度

除了第三方平台的聪明钱包和KOL数据，30分钟节点还需要：

| 数据维度 | 平台 | 为什么重要 |
| :--- | :--- | :--- |
| **清算密集区** | Coinglass | 价格逼近大量清算位时，会加速爆仓形成趋势 |
| **资金费率** | Coinglass | 费率达到0.1%以上说明市场过热，警惕反转 |
| **多空比** | Coinglass | 多空比极端倾斜时反转概率增大 |
| **稳定币流入交易所** | CryptoQuant | USDT/USDC大量充值进交易所 = 潜在买盘 |
| **BTC/ETH持仓量变化** | Coinglass | 持仓量暴增暴跌往往预示大行情启动 |
| **每日解锁/归属(Vesting)** | TokenUnlocks.app | 解锁日前后一般有抛压 |
| **美联储利率决议日历** | 经济日历 | 加息/降息影响所有市场 |
| **项目GitHub提交量** | GitHub API | 开发活跃说明项目没死 |

## 五、需要老李协同的清单（修正版）

> 之前我列了一堆"给我地址"这种蠢话。
> 现在正确的协同方式是：

| # | 协同项 | 具体内容 |
| :--- | :--- | :--- |
| 1 | **确认要不要开付费平台** | Glassnode $29/月 or Nansen $149/月 or 全部免费先跑 |
| 2 | **授权我安装xurl工具** | 需要接入Twitter API才能监控@lookonchain等KOL的实时推文 |
| 3 | **你验证过的交易逻辑** | 你之前在币安赚到钱的幣，当时的买入信号是什么？我写进共振评分权重 |
| 4 | **指定3-5个你信任的聪明钱源** | 你是看DexScreener的Smart Money，还是Nansen，还是自己跟的地址？我按你的来 |
| 5 | **"30分钟节点"的时间窗口确认** | 是固定整点半点跑，还是根据行情波动自动触发？ |

---

**总结：我之前犯的错是"自己编数据"。
正确做法是：利用第三方平台自带的数据（DexScreener Smart Money、Coinglass清算图、Etherscan Top Holders），
我只需要列出"去哪里看什么"，你亲自去核实后告诉我用哪些。
**
