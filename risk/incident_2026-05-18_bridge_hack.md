# 事件记录：Verus-Ethereum桥黑客攻击

> 来源：A7舆情官 13:15 BJT 发现
> 记录时间：2026-05-18 15:05 BJT
> 优先级：中（非系统风险，无持仓暴露）

## 事件摘要
Verus-Ethereum跨链桥遭黑客利用合约逻辑漏洞，损失$11M-$11.58M。
攻击者：mint未背书ERC-20 VRSC → Uniswap兑换6,800 ETH → 混币器洗钱。

## 风险评估
- **系统影响：无** — 持仓(DOT/TON/UNI/XEC/ADA)无暴露
- **VRSC跌幅：** 34%（$5.20→$3.43），小市值币孤立事件
- **非架构漏洞** — 是federation桥代码bug，非zk/IBC类桥的设计缺陷
- **全局影响：** 零 — BTC/ETH/主流币未受波及

## 学习要点
1. Federation/轻节点桥连续发生安全事件（2022 Wormhole/Nomad → 2023 Multichain → 2026 Verus），趋势明确
2. 安全叙事迁移方向：zk-bridge/IBC > federation桥
3. 此类事件在F&G=28恐惧市场中增加负面情绪，但不改变选币/建仓逻辑
4. 如需配置跨链赛道币种，优先选zk-bridge/IBC协议的币，避开federation桥依赖型

## 后续追踪
- [ ] 攻击向量是否在其他federation桥中复现（跟踪1周）
- [ ] 被盗资金后续追踪（$4,200 ETH在链上标记地址）
