# ZQ-Scouter 侦察报告

**侦察日期**: 2026-05-04 (周一)
**报告范围**: 2026-04-27 ~ 2026-05-04
**侦察方向**: 5个维度 / 共评估30+工具/API

---

## 一览

| 优先级 | 工具 | 价值类型 | 集成门槛 | 备注 |
|:------:|:----|:--------:|:--------:|:----|
| P0 | DexScreener Stream API | DEX实时价格 | 低(免费/无Key) | 新币发现+C双验证 |
| P0 | FundingTracker CN | 资金费率/多空比 | 低(网页数据) | 填补评分公式缺口 |
| P0 | CryptoCortex | 波动率指数 | 中(社区项目) | 第二新维度 |
| P1 | GoPlus | Token安全扫描 | 低(免费API) | 扩展新币时必备 |
| P1 | Mesa (新) | 新L1链数据聚合 | 中(新项目) | 战略储备 |
| P1 | AlgoTrader ML Plugin | LightGBM/XGBoost模型 | 中(需部署) | ML出场信号参考 |
| P1 | Dune Community Plan | SQL链上查询 | 中(需要SQL) | 深度分析 |
| P2 | TensorFlow Crypto Agent | 开源量化框架 | 低(MIT开源) | 参考代码库 |

---

## P0 — 本周应集成

### 1. DexScreener Stream API ★★★★★
- **类型**: DEX实时数据流API
- **发布日期**: 2026-05-01
- **描述**: Solana/Ethereum/BSC等链DEX实时价格+流动性快照，每秒更新
- **免费**: 完全免费，无需API Key，仅限速10次/秒/IP
- **链接**: https://dexscreener.com/docs/api
- **价值分析**:
  - 我们当前只依赖Binance CEX价格，缺DEX侧验证
  - 该API可补足"新币发现"模块（DEX先于CEX上线新币）
  - 免费无Key意味着零集成成本
  - **判定**: 高价值，建议在 engine_realtime_v2 中加入DEX价格交叉引用

### 2. FundingTracker CN ★★★★★
- **类型**: 资金费率/多空比/未平仓量追踪
- **描述**: 实时展示币安/OKX全部合约的资金费率变化，近期新增OKX对比
- **免费**: 基础数据完全免费，历史数据导出需注册
- **链接**: https://fundingtracker.io/cn
- **价值分析**:
  - **我们的评分12因子中已列了资金费率因子(得分项)，但依赖的是Binance Futures API**
  - 此工具可将资金费率数据范围扩展到OKX
  - 多空比+OI图表可作为买入/卖出的辅助判断
  - **判定**: 高价值，提升信号精度

### 3. CryptoCortex ★★★★☆
- **类型**: 社区聚合市场数据API
- **发布日期**: 2026-04-20
- **描述**: 现货+永续合约+波动率指数，延迟<2秒，REST+WebSocket
- **免费**: 完全免费，捐赠模式
- **链接**: https://cryptocortex.dev
- **价值分析**:
  - **波动率指数**是我们评分公式完全缺失的维度
  - 加入"波动率>阈值"作为AND进场条件之一，可过滤低波动横盘假信号
  - 社区项目稳定性需观察，但免费无风险
  - **判定**: 探索性集成，先观察2周稳定性

---

## P1 — 本月考虑集成

### 4. GoPlus Token Scanner ★★★★☆
- **类型**: 实时Token安全扫描
- **新特性**: 2026-05-01 Mempool Security Layer
- **免费**: 基础Token扫描免费
- **链接**: https://gopluslabs.io
- **价值**: 当前只监控6个已知币种，安全风险低。但未来扩展新币时必用
- **判定**: 战略防御工具，新币扩展时优先启用

### 5. Mesa (全新发布) ★★★★☆
- **类型**: 新L1链(Sui/Aptos/Sei)数据聚合
- **发布日期**: 2026-04 (全新项目)
- **免费**: 公共仪表盘免费，高级API付费
- **链接**: https://mesa.xyz
- **价值**: 唯一专注新公链的免费聚合工具。如果策略要扩展出以太坊/Solana生态，这就是入口
- **判定**: 战略储备

### 6. AlgoTrader ML Plugin v2.1 ★★★☆☆
- **类型**: 开源ML量化交易库(LightGBM+XGBoost)
- **发布日期**: 2026-04-28
- **免费**: MIT完全开源
- **链接**: https://github.com/algotrader/ml-plugin
- **价值**: 可参考其特征工程方法，用于6OR出场条件中ML辅助判断趋势反转概率
- **判定**: 代码参考级

### 7. Dune Community Plan 升级 ★★★☆☆
- **类型**: SQL链上查询平台
- **更新**: 2026-05-02免费用户查询额度升至50万行/月
- **免费**: 公共仪表盘和查询免费
- **链接**: https://dune.com/pricing
- **价值**: 做深度归因分析时，需要链上数据支持（资金流向、钱包行为）
- **判定**: 按需使用

---

## P2 — 值得关注

| 名称 | 描述 | 备注 |
|:-----|:-----|:-----|
| TensorFlow Crypto Agent | 开源ML框架+历史数据加载器 | MIT协议，参考用 |
| NeuralTrade Signals | LSTM+链上数据，3信号/周免费 | 信号交叉验证 |
| Hyperion Bot v0.9.3 | RL套利机器人+Uniswap V4 | DEX套利参考 |
| SwapHub (开源) | OKX DEX聚合器+中文文档 | 战略扩展OKX时用 |
| AlphaBot CN | 币安Alpha选币分析(Telegram) | 新币发现，需手动 |
| CoinDaily CN | 中文加密新闻AI摘要 | 信息输入 |
| DevPortal CN | 中文Web3 API网关 | RPC节点备用 |
| Nansen Query Free | 链上Smart Money标签(100次/天) | 智能资金追踪 |
| Blocknative | 内存池数据+Gas估算免费层 | Gas优化 |
| EigenPhi | 内存池交易+MEV分析(5分钟延迟免费) | 监控工具 |

---

## 对我们的系统而言最直接的改善

### 当前评分公式12因子
```
成交额排名(40) + RSI(20) + 量比(20) + 趋势(20)
+ 4h趋势加分(0~15) + 1h趋势加分(-5~8)
+ 资金费率(-15~+15) + OI(+5)
+ 社交热度(+10) + Dex热度(+5)
+ 涨幅惩罚(-30~+5) + 行为经验(-10~+10)
```

### 建议新增维度

| 新维度 | 来源 | 权重建议 | 影响 |
|:-------|:-----|:--------:|:-----|
| 资金费率(OKX交叉) | FundingTracker | 已有费率因子但可交叉验证 | 降低单一交易所偏差 |
| 波动率指数 | CryptoCortex | +10/-5 | 过滤低波动横盘 |
| DEX价格偏差 | DexScreener | -5 (偏差>3%) | 防CEX价格操纵 |

### 一句话结论
- **DexScreener Stream API + FundingTracker** 是两个可以直接提升当前策略的免费工具
- **CryptoCortex** 的波动率维度值得探索
- **GoPlus** 是未来扩展新币的安全保障

---

## 风险点

1. **CryptoCortex** 是社区项目，服务器稳定性不确定 — 先观察2周
2. **FundingTracker** 没有公开API文档，可能需要爬虫抓取
3. **DexScreener** 10次/秒的速率限制在实时交易时可能不足 — 需测试实际延迟
4. **AlphaBot** 仅限Telegram使用，无法直接代码集成
5. **Mesa** 全新项目（2026-04发布），长期维护能力未知

---

## 下次侦察计划 (2026-05-11)

1. 追踪本周推荐的 P0 工具的状态变化
2. 搜索新的链上数据分析API
3. 关注 CoinGecko 和 CoinMarketCap 的免费层变化
4. 搜索飞书/Discord机器人新能力
5. 关注Hermes Skills Hub新技能发布

---

*报告由 ZQ-Scouter 自动生成于 2026-05-04 01:32 UTC+8*
*环境: Hermes Agent on macOS (ZQ-Scouter profile)*
