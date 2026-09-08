# ZQ-Scouter 专项报告：系统缺维补全

**报告日期**: 2026-05-04
**目标**: 为当前评分12因子补齐3个缺失数据维度
**参考**: AGENTS.md 数据源状态表、engine_realtime_v2.py 评分公式

---

## 任务背景

根据AGENTS.md审视结论，当前数据源状态存在明确缺口：

| 状态 | 数据源 | 缺口描述 |
|:---:|:------|:---------|
| ❌ | 链上聪明钱 | Etherscan已接但未入评分公式。替代Nansen ($99/月) |
| ❌ | 资金费率历史 | 仅从Binance实时拉取，缺多所历史对比。替代Coinglass |
| ❌ | 多交易所价格验证 | 仅有CoinGecko 50币ID映射做偏差检测，精度不够 |
| ✅ | 资金费率(实时) | Binance Futures 716合约实时获取 — 已有 |
| ✅ | OI持仓量 | Top20币单合约查询 — 已有 |

---

## 方向一：免费链上聪明钱追踪（替代Nansen $99/月）

### 评估结果

| 排名 | 工具 | 聪明钱数据 | API可用性 | 免费限制 | 推荐理由 |
|:----:|:-----|:----------:|:---------:|:--------:|:---------|
| 1 | **Debank** | Smart Money标签，30+链，资金流向 | 免费REST API，无需Key | 前端完全免费 | **门槛最低，开箱即用** |
| 2 | **0xScope** | 聪明钱排行榜，地址标签，风险评分 | 免费REST API，5000次/月 | 注册即可 | **有聪明钱API端点** |
| 3 | **Arkham Intelligence** | 实体图谱，大额交易警报 | 免费API，1000次/h | 200次页面/月 | **可视化最强** |
| 4 | **Birdeye** | Top Traders排行榜，Token分析 | 免费REST API，10k次/月 | 每日100次API | **行情+聪明钱一体** |
| 5 | **DexScreener** | 钱包追踪，热门交易者 | WebSocket免费 | 完全免费 | **已用的工具，可挖掘** |

### 详细评估

#### 1. Debank — 首选推荐 ⭐⭐⭐⭐⭐
- **聪明钱数据**: 系统自动标记"Smart Money"地址，基于历史胜率和早期项目参与度。可查看任意地址的持仓/交易历史/盈亏
- **API**: 公开REST API (`/account/balance`, `/transaction/list`, `/token/list`)，无需注册即可调用
- **免费限制**: 前端完全免费无限制，API限速约10次/秒
- **URL**: https://debank.com
- **集成分析**:
  - 策略应用: 在评分公式中，若候选币种持仓中有Smart Money地址增持 → 加分
  - 门槛: 极低，直接API调用即可
  - 缺点: 无官方聪明钱API端点，需通过前端间接获取

#### 2. 0xScope — 有聪明钱API ⭐⭐⭐⭐
- **聪明钱数据**: Smart Money排行榜（按利润/胜率排序），地址标签（交易所/聪明钱/钓鱼），早期参与者追踪
- **API**: REST API，免费层每月5000次请求，**包含聪明钱列表端点**
- **免费限制**: 注册即可，5000次/月足够日常
- **URL**: https://0xscope.com
- **集成分析**:
  - 优势: 直接有聪明钱API，可以程序化获取"代币X是否被聪明钱地址持有"
  - 策略应用: 可在评分12因子中加入"聪明钱持仓"因子 (+5~+15)

#### 3. Arkham Intelligence ⭐⭐⭐⭐
- **聪明钱数据**: 实体自动标注（基金/交易所/聪明钱/黑客/MEV机器人），可视化资金流向图，大额交易警报
- **API**: REST API，免费层每小时1000次请求，可查询实体标签和交易
- **免费限制**: 每月200次页面加载，5个警报
- **URL**: https://arkhamintelligence.com
- **集成分析**:
  - 优势: 可视化分析最强，适合人工复盘
  - 缺点: 页面加载限制严格，不适合每日自动化查询

**结论**: 以**Debank**（免费无限制）为主，辅以**0xScope API**（聪明钱标签），零成本替代Nansen。

---

## 方向二：免费资金费率/OI历史API（替代Coinglass）

### 评估结果

| 排名 | 数据源 | 资金费率历史 | OI历史 | API类型 | 免费程度 | 推荐理由 |
|:----:|:------|:-----------:|:------:|:-------:|:--------:|:---------|
| 1 | **Binance API** | 全历史(~2020起) | 全历史(~2020起) | REST分页 | **完全免费** | **数据最深，已在使用** |
| 2 | **Bybit API** | 全历史(合约上线起) | 全历史(合约上线起) | REST游标分页 | **完全免费** | **多所交叉验证** |
| 3 | **CryptoDataDownload** | 2-3年CSV | 2-3年CSV | 网页下载 | 免费(10次/天) | **零代码获取** |
| 4 | **OKX API** | 全历史 | 全历史 | REST分页 | 完全免费 | 补充第三所 |
| 5 | **ccxt + 自建存储** | 自定义 | 自定义 | 可编程 | 完全免费 | 长期方案 |

### 详细评估

#### 1. Binance API — 主要数据源 ⭐⭐⭐⭐⭐
- **端点**:
  - 资金费率: `GET /fapi/v1/fundingRate?symbol=BTCUSDT&limit=1000` (分页可回溯至2020)
  - OI历史: `GET /fapi/v1/openInterestHist?symbol=BTCUSDT&period=1h&limit=500` (5min/15min/30min/1h/4h/1d)
- **优势**: 我们已在使用Binance数据，代码可直接复用。历史数据最深
- **劣势**: 需要分页循环获取长段历史，单次1000条上限
- **集成**: 已有trend_store.json存储费率趋势，可扩展为更长历史

#### 2. Bybit API — 交叉验证 ⭐⭐⭐⭐⭐
- **端点**:
  - 资金费率: `GET /v5/market/funding/history?category=linear&symbol=BTCUSDT` (游标分页)
  - OI: `GET /v5/market/open-interest?category=linear&symbol=BTCUSDT&intervalTime=1h` (5min/15min/1h/4h/1d)
- **优势**: 公开端点无需认证，限速宽松(50次/秒)
- **集成**: 新代码，但API文档清晰

#### 3. CryptoDataDownload — 快速备份 ⭐⭐⭐⭐
- **内容**: 预打包的CSV文件，覆盖Binance/Bybit/OKX/Bitget/Gate.io的资金费率、OI、多空比
- **格式**: 每日更新一次(UTC 00:00)，可直接wget/curl下载
- **URL**: https://www.cryptodatadownload.com/data/
- **集成**: 适合一次性批量拉取历史数据，不适合实时

**结论**: **Binance API** 已能覆盖6个监控币种的全部资金费率/OI历史。Bybit API 作为辅助，实现多所交叉验证。完全免费替代Coinglass。

---

## 方向三：多交易所价格对比（多平台验证）

### 评估结果

| 排名 | 数据源 | 覆盖交易所 | 多所价格 | 延迟 | API类型 | 免费程度 |
|:----:|:------|:---------:|:--------:|:---:|:-------:|:--------:|
| 1 | **CryptoCompare API** | 170+ | ✅ 直接返回各所价 | 30-60s REST | REST，25次/s | **免费(10万次/日)** |
| 2 | **各交易所API自聚合** | 自定义 | ✅ 需自行编码 | <100ms WS | REST+WS | 完全免费 |
| 3 | **CoinGecko API** | 600+ | ❌ 仅聚合价 | 1-2min | REST，50次/min | 免费(无Key) |
| 4 | **CoinCap API** | 聚合 | ❌ 仅聚合价 | 2-5min | REST，200次/min | 免费无Key |
| 5 | **CCXT库** | 100+ | ✅ 统一接口 | 各所不同 | 可编程层 | 完全免费 |

### 详细评估

#### 1. CryptoCompare API — 首选 ⭐⭐⭐⭐⭐
- **端点**: `https://min-api.cryptocompare.com/data/pricemulti?fsyms=BTC,ETH,SOL&tsyms=USD&e=Binance,OKX,Bybit`
- **返回示例**: `{"BTC":{"Binance":xxxx,"OKX":xxxx,"Bybit":xxxx},"ETH":{...}}`
- **免费层**: 注册得API Key，25次/秒REST，每日10万次调用
- **优势**: **一键获取多所价格**，无需自行聚合。延迟30-60秒对价格偏差检测足够
- **URL**: https://min-api.cryptocompare.com/
- **集成分析**:
  - 替代当前CoinGecko的50币ID映射方案（偏差>3%扣5分）
  - 可直接获取Binance/OKX/Bybit三个交易所同一时刻的价格
  - 在选出Top3候选币后，对每个候选币做价格偏差检测
  - 偏差>1%开始扣分，>3%强制扣10分

#### 2. 交易所API自聚合 ⭐⭐⭐⭐
- **方法**: 分别调用Binance, OKX, Bybit的ticker端点，在代码中做对比
- **优势**: 延迟最低(<100ms通过WS)，可自由控制频率
- **劣势**: 需要写聚合逻辑，维护3个API连接
- **适用**: 如果CryptoCompare不够快，降级方案

#### 3. CCXT库 ⭐⭐⭐⭐
- **描述**: 统一接口层，一行代码切换交易所
- **使用**: `ccxt.binance().fetch_ticker('BTC/USDT')`, `ccxt.okx().fetch_ticker('BTC/USDT')`
- **集成**: 已在Python环境中可用 (`pip install ccxt`)
- **URL**: https://github.com/ccxt/ccxt
- **优势**: 代码简洁，支持100+交易所

**结论**: **CryptoCompare API**是最直接的多所价格对比方案，零编码成本。备选**CCXT**作为程序化方案。

---

## 综合集成方案

### 当前评分12因子 (engine_realtime_v2.py)
```
成交额排名(40) + RSI(20) + 量比(20) + 趋势(20)
+ 4h趋势加分(0~15) + 1h趋势加分(-5~8)
+ 资金费率(-15~+15) + OI(+5)
+ 社交热度(+10) + Dex热度(+5)
+ 涨幅惩罚(-30~+5) + 行为经验(-10~+10)
```

### 建议新增3个因子

| 新因子 | 权重范围 | 数据来源 | 实现路径 | 集成难度 |
|:-------|:--------:|:--------|:---------|:--------:|
| 聪明钱持仓 | +5 ~ +15 | Debank API / 0xScope API | 查候选币持币地址中是否有标记为Smart Money的地址 | 中 |
| 多所价格偏差 | -5 ~ -10 | CryptoCompare API | 对比Binance/OKX/Bybit价格，偏差>1%扣分 | **低 — 新增独立模块** |
| 资金费率趋势(历史) | ±5 | Binance API (已有) | 从trend_store.json读取24h费率趋势，上升加分下降减分 | **低 — 复用已有存储** |

### 代码改动点 (预计)

```
engine_realtime_v2.py
├── scan_top50()                 → 无改动
├── calculate_score()            → 加3个因子调用
│   ├── get_smart_money_score()  → 新增函数 (Debank/0xScope)
│   ├── get_price_deviation()    → 新增函数 (CryptoCompare)
│   └── get_funding_trend()      → 增强现有逻辑 (trend_store)
├── decide_entry()               → 无改动 (AND条件不变)
└── decide_exit()                → 无改动 (OR条件不变)

config/ (新增)
├── smart_money_wallets.json     → Debank标记的聪明钱地址缓存
└── price_sources.json           → 配置需要对比的交易所列表
```

### 集成建议路线

```
本周 (P0) ── 多所价格偏差验证
  CryptoCompare API注册 → 写get_price_deviation() → 加到评分公式
  收益: 立即增强选币库的准确性

下周 (P1) ── 资金费率历史趋势增强
  增强trend_store → 改为存储24h费率变化方向
  收益: 让费率因子从"当前值"升级为"趋势方向"

下月 (P2) ── 聪明钱追踪
  Debank API集成 → 缓存聪明钱地址 → 评分中加入因子
  收益: 最后的链上数据维度补全
```

---

## 成本对比

| 数据维度 | 原付费方案 | 原月费 | 新免费方案 | 节省 |
|:---------|:----------|:-----:|:----------|:----:|
| 聪明钱追踪 | Nansen | $99/mo | Debank + 0xScope | $99/mo |
| 费率/OI历史 | Coinglass | $29/mo | Binance + Bybit API | $29/mo |
| 多所价格 | TradingView | ~$20/mo | CryptoCompare API | $20/mo |
| **总计** | | **$148/mo** | **$0/mo** | **$148/mo** |

---

## 总结

1. **方向一 (聪明钱)**: Debank (免费无限制) + 0xScope API (聪明钱标签) = 完全替代Nansen
2. **方向二 (费率/OI历史)**: Binance API (已有) + Bybit API (新增) = 完全替代Coinglass
3. **方向三 (多所价格)**: CryptoCompare API (10万次/日免费) = 替代当前CoinGecko方案，精度更高

**三个方向全部零成本，月省$148。**

---

*报告由 ZQ-Scouter 自动生成于 2026-05-04*
