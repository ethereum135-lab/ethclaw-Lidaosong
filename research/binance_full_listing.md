# 研究方向一：币安全量上架币种入库方案

## 1. 币安目前有多少上架币种（现货交易对）？

**实时数据（2026-05-31 通过 AWS EC2 查询）：**

| 维度 | 数量 |
|------|------|
| USDT 现货交易对（TRADING 状态） | **430 个** |
| USDT 总交易对（含 BREAK/已下架） | 663 个 |
| 交易所总交易对（所有报价币） | 1371 个（TRADING），3590 个（含 BREAK） |
| USDT 交易对中无可交易状态 | 0 个（全部可交易） |

**当前池子现状对比：**
| 指标 | 当前值 |
|------|--------|
| 全量池 total_coins | 592 个（含 removed） |
| 全量池 active | 292 个 |
| 全量池 warning | 214 个 |
| 精选池 prime pool | 172 个 |
| 实际应有 USDT TRADING | 430 个 |

**结论**：目前全量池包含了233个已经下架（BREAK状态）的币种，而active+warnining=506个，比实际TRADING的430个多出76个，说明冗余数据在累积。

---

## 2. 如何通过API获取币安全量币种列表？

### 方案A：`exchangeInfo`（推荐 — 一次调用获取全量）

```
GET https://api.binance.com/api/v3/exchangeInfo
```

- 一次性返回所有交易对信息（当前约3500条，含所有状态）
- **无认证要求**（公开API）
- 包含字段：`symbol`, `baseAsset`, `quoteAsset`, `status`, `isSpotTradingAllowed`, `isMarginTradingAllowed`, `filters`（精度、最小交易量等）

```python
# 过滤 USDT 现货交易对
symbols = [s for s in data['symbols'] 
           if s['status'] == 'TRADING' 
           and s['quoteAsset'] == 'USDT' 
           and s['isSpotTradingAllowed']
          ]
```
返回 430 个活跃 USDT 现货对。

### 方案B：`ticker/24hr` — 带成交量数据

```
GET https://api.binance.com/api/v3/ticker/24hr
```

- 返回每个交易对的24小时统计数据（价格变化、成交量、最高最低价等）
- 当前 `coin_pool_manager.py` 使用的就是这个
- 约 0.5~1MB 响应体，建议通过 SOCKS5 隧道访问
- **限流**：1200次/分钟（公开），不用太担心

### 方案C：`ticker/price` — 仅价格

```
GET https://api.binance.com/api/v3/ticker/price
```

- 只返回 symbol + price，响应体很小（约80KB）
- 适合快速价格检查

### 当前网络方案（GFW穿透）

```
Mac本地 → SOCKS5代理(localhost:1080) → AWS EC2(15.134.211.154) → Binance API
```

通过 `scripts/tunnel_binance.sh` 维护，但日志显示隧道时常断开（`Operation timed out`, `Connection reset by peer`）。建议：
- 直接在 AWS EC2 上运行全量数据拉取脚本，然后 SCP/S3 同步回本地
- 或使用 `curl -x socks5h://127.0.0.1:1080` 走代理

---

## 3. 常用的币种分类方法

### 维度一：按赛道（Sector）— 当前系统已有
当前 CATEGORY_MAP 定义了 **19个赛道**：

| 赛道 | 当前覆盖 | 实际需要 |
|------|---------|---------|
| layer1 | 43 | 43 |
| layer2 | 13 | 13 |
| defi | 56 | ~58 |
| meme | 24 | ~30+ |
| ai | 20 | ~22 |
| gamefi | 19 | ~19 |
| rwa | 10 | ~10 |
| depin | 8 | ~8 |
| btc_ecosystem | 5 | ~5 |
| cex | 6 | ~6 |
| cosmos | 4 | ~4 |
| oracle | 5 | ~7 |
| privacy | 4 | ~4 |
| lsd | 3 | ~4 |
| storage | 2 | ~2 |
| nft | 3 | ~3 |
| crosschain | 3 | ~3 |
| pow | 6 | ~6 |
| other | 0 | **~280个未归类** |

**现状**：CATEGORY_MAP 只覆盖了 150/430 个币种，**280个币没有分类**（被标记为 'other'）。

建议新增赛道（基于280个未分类币的分析）：
- **real world asset / synthetic**: USUAL, RESOLV, ENA（已有）→ 可与 RWA 合并
- **sonic / move 生态**: SUI（已有layer1）, MOVE, OMNI → 一些新公链
- **CeFi / CEX代币**: 已有部分
- **DePIN / 基础设施**: GRASS, IO, CLORE → 已有 depin 分类
- **AI Agent / Meme**: AI16Z, VIRTUAL → 已有ai分类
- **DeSci**: 新赛道（如有）
- **ETF/质押衍生品**: WBETH, BNSOL, BB → 类似 stETH 但非杠杆

### 维度二：按市值（Market Cap）
通过 CoinGecko/CoinMarketCap API 获取，分为：
- **巨无霸** (>100亿): BTC, ETH, SOL, BNB, XRP
- **大盘** (10亿~100亿): ADA, AVAX, LINK, DOT, TON
- **中盘** (1亿~10亿): 大多数主流币
- **小盘** (1000万~1亿): 许多新上的山寨币
- **微盘** (<1000万): 流动性极差币

**API来源**: CoinGecko `/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc`

### 维度三：按波动率（Volatility）
从24h K线计算：
- **高波动** (>15% 日波动): 适合短线/动量策略
- **中波动** (5~15%): 适合趋势跟踪
- **低波动** (<5%): BTC, ETH 等大市值币

### 维度四：按流动性（Liquidity）
以24h USDT成交量为准（当前系统已有）：

| 等级 | 成交量门槛 | 币数 | 适合策略 |
|------|-----------|------|---------|
| S级 | >$5000万 | ~50个 | 任意策略，滑点低 |
| A级 | $1000~5000万 | ~50个 | 主流策略，注意滑点 |
| B级 | $100万~1000万 | ~150个 | 小资金策略 |
| C级 | $10万~100万 | ~130个 | 谨慎交易，滑点明显 |
| D级 | <$10万 | ~50个 | 不可交易（流动性风险） |

当前数据：TOP50最低成交量$680万，TOP200最低$70万，TOP400最低$11.5万。

### 维度五：按生态/叙事（Ecosystem Narrative）
- **BTC生态**: 铭文、二层、LST
- **ETH生态**: L2、DeFi、LSD
- **Solana生态**: Meme、DeFi、DePIN
- **Sui生态**: 新兴公链
- **Move生态**: Aptos, Sui, Movement

### 维度六：按价格区间
- 低价币 (<$0.01): 适合批量买入
- 中价币 ($0.01~$10): 主流交易区间
- 高价币 (>$10): BTC, ETH, BNB

---

## 4. 扩展到全量币种的技术方案

### 4.1 数据源

| 数据源 | 用途 | 频率 | 认证 |
|--------|------|------|------|
| **Binance exchangeInfo** | 全量币种列表+状态 | 每天1次 | 无 |
| **Binance ticker/24hr** | 24h成交量+价格变化 | 每6小时 | 无 |
| **Binance klines** | K线数据用于信号计算 | 每30分钟 | 无 |
| **CoinGecko API** | 市值+赛道分类+排名 | 每天1次 | 免费key |
| **CoinMarketCap API** | 市值+赛道（备选） | 每天1次 | 免费key（250/天） |

### 4.2 存储方案（修改 coin_pool_manager.py）

**当前问题**：
1. 全量池 `coin_pool.json` 存储了592个币但包含233个已下架币
2. 精选池 `coin_pool_prime.json` 只有172个币
3. CATEGORY_MAP 硬编码只覆盖35%的币种

**建议的存储分层**：

```
data/
├── binance_all_list.json         # 新：Binance全量列表（430个TRADING币）
│   ├── {symbol, status, baseAsset, quoteAsset, isSpotTradingAllowed, filters}
│   └── updated_at: timestamp
├── coin_pool.json                # 现有：全量池（592个，含历史数据）
│   └── 保持兼容，但去掉BREAK币
├── coin_pool_prime.json          # 现有：精选池（172个）
│   └── 可扩展为全量扫描的结果
├── coin_sectors.json             # 新：赛道分类映射（动态更新，替代硬编码CATEGORY_MAP）
│   └── {symbol: sector, source: "coingecko|manual|llm"}
├── coin_metadata.json            # 新：币种元数据
│   ├── 市值/24h成交量/波动率/流动性等级
│   └── 赛道/生态/叙事标签
└── signals.json                  # 现有：A3信号输出
```

### 4.3 更新频率建议

| 数据 | 频率 | 原因 |
|------|------|------|
| 全量币种列表 | **每天1次** (08:00 BJT) | 新币上架/下架不频繁 |
| 24h成交量+价格 | **每6小时** (08/14/20/02) | 同现有 CACHE_TTL_HOURS=6 |
| 赛道分类 | **每周1次** | 需要人工/LLM审核 |
| K线信号扫描 | **每30分钟** | 交易信号需要高频 |
| 市值数据 | **每天1次** | 变化不剧烈 |

### 4.4 具体修改步骤

#### Step 1: 修复全量池 — 只保留TRADING币种
修改 `fetch_all_tickers()` 或新增方法，拉取 `exchangeInfo` 来确定哪些是当前活跃交易对：

```python
def fetch_active_usdt_pairs():
    """获取币安全量活跃USDT现货交易对"""
    info = fetch_exchange_info()
    active = [s for s in info['symbols']
              if s['status'] == 'TRADING'
              and s['quoteAsset'] == 'USDT'
              and s['isSpotTradingAllowed']]
    # 排除稳定币、结构化产品
    return [s['baseAsset'] for s in active if base not in STABLE_LIST
            and not any(kw in s['baseAsset'] for kw in LEVERAGE_KEYWORDS)]
```

#### Step 2: 动态赛道分类替代硬编码CATEGORY_MAP
将450行硬编码的 `CATEGORY_MAP` 替换为外部数据源：

**方案A: CoinGecko 自动分类**（推荐）
```python
# coingecko.com/api/documentation
GET https://api.coingecko.com/api/v3/coins/{id}
# 返回中包含 categories 数组
```

**方案B: LLM 辅助分类**
```python
def classify_coin_llm(symbol):
    """通过LLM判断赛道（对未知币种）"""
    prompt = f"Classify {symbol} token into one of: layer1, layer2, defi, meme, ai, rwa, depin..."
    # 调用LLM API
```

**方案C: 手动维护 + 自动发现**
- 保留现有150个手工映射
- 对280个未知币，批量查询CoinGecko获取分类
- 输出到 `coin_sectors.json`

#### Step 3: 数据迁移计划

| 阶段 | 内容 | 预计工作量 |
|------|------|-----------|
| 1 | 新增 `exchangeInfo` 拉取 + 全量列表文件 | 1天 |
| 2 | 修复 `build_pool` 只保留TRADING币 | 半天 |
| 3 | 集成 CoinGecko 赛道分类 | 1~2天 |
| 4 | 扩展 `coin_pool_manager.py` 支持全量430个币的扫描 | 1天 |
| 5 | 新增分类存储文件 + 索引优化 | 半天 |

### 4.5 核心代码改动建议

**`coin_pool_manager.py` 修改点**：

1. **新增 `fetch_exchange_info()`** 
   - 调用 `exchangeInfo` 获取全量币种列表
   - 缓存到 `data/binance_all_list.json`

2. **修改 `fetch_all_tickers()`**
   - 先用 `exchangeInfo` 过滤出 TRADING 状态的 USDT 对
   - 再用 `ticker/24hr` 获取成交量数据
   - 这样不会把 BREAK 状态的币拉进来

3. **`CATEGORY_MAP` → 外部化**
   - 移出硬编码到 `data/coin_sectors.json`
   - 自动合并 CoinGecko 数据
   - 保留手动 override 机制

4. **扩展 `build_prime_pool()`**
   - 支持从全量430个币中扫描
   - 不再局限于 ~200 个池子

### 4.6 当前限制与风险

| 风险 | 说明 | 缓解措施 |
|------|------|---------|
| GFW阻断 | 直接从Mac访问被451拦截 | 走SSH隧道或AWS直连 |
| SSH隧道不稳定 | 日志显示频繁断连 | 改用AWS直连脚本+SCP回传 |
| API限流 | ticker/24hr 返回1400+个对 | 限制每6小时1次 |
| 新币上架 | Binance每天可能有新币 | exchangeInfo每日1次拉取 |
| 分类缺失 | 280个币未分类 | CoinGecko批量补齐 |

### 4.7 建议优先级

1. **立即修复**：修改 `build_pool` 只拉取活跃的430个USDT对，去掉BREAK币的数据污染
2. **本周**：280个未分类币的赛道补齐（CoinGecko批量查询）
3. **下周**：存储分层改造，新增 `binance_all_list.json` 和 `coin_sectors.json`
4. **后续**：扩展扫描范围从172个精选池 → 430个全量池
