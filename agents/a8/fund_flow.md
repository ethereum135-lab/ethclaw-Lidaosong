# A8 资金信号报告

- 快照 09-04 10:17 BJT | ✅ data_quality正常(AWS实时API) errors=0 | coin_pool 667池 05:00刷新(enrich_last 10:17) | ⚠️部分链受限(Solscan 404/401+BSC区块na, 同常态; ARBI块限速但gas有数据)
- 🔴 signals等级层 08-31 12:04(≈94h过时, 与上轮同位) STRONG 119/SIGNAL 153 | smart滚动层 10:13刷新(265币) | A8本轮新打标=0(signals enrich全空)
- 持仓(A4): 0仓·HOLD | USDT $168.39 总权益$218.52(Binance直连10:21, 与上轮$218.59持平) | 无active持仓

## T0 — STRONG→INFLOW验证
- 零命中: INFLOW 16笔6币(BTC×1/LINK×5/PEPE×1/SOL×1/SUI×2/XRP×6, 构成与上轮同) ∩ 119 STRONG=0; 6币等级层 BTC=WATCH, LINK/SOL/SUI/XRP/PEPE=PASS(与上轮同)
- smart方向(10:13): BTC BUY / LINK·XRP·SOL BIAS_LONG / SUI BIAS_LONG→**BIAS_SHORT(转空)** / PEPE BIAS_SHORT(连续2轮空); XRP上轮转空→本轮回多

## T1 — SIGNAL→资金流入
- 零直连命中: 153个SIGNAL无一获本轮INFLOW验证; A8打标=0
- SIGNAL级smart BUY 15个(含GIGGLE/FF/PUNDIX/SIGN/STRK/EDU/MAV/CHIP/WIF/ICP/KNC/AR等), 均无INFLOW关联

## T2 — coin_pool异常资金(667池)
- LINK(池内·PASS·5链): 4实链≈**$174万**(上轮$170万≈持平): ethereum $659K/polygon $652K/arbitrum $320K/base $113K; ratio 0.80/0.79/0.75/**1.55x**(base唯一买盘侧且增强, 上轮1.51x); 24h +6.3~6.8%; robinhood伪池(价0.00054失真, -24.5%)
- XRP(池内·PASS·6池): bsc $160万 0.98x +6.4% / solana 5池≈$165万 ratio 0.67~1.00x → 量多但B/S全≤1卖压侧(0.67x池 -4.5%)
- SUI(池内·PASS): solana 2池≈$32万(上轮$39万→缩) 0.92x/0.98x 中性
- BTC/PEPE/SOL(池内): robinhood伪池存疑(BTC 0.99x -86.7% / PEPE 1.32x -77.9% / SOL 0.98x +9778%失真, 非真信号)

## MONEY_IN汇总
- 2笔全in ≈ **$561万**(上轮5笔$484万 → +16%): 全ETH链 USDT 2笔($61万+$500万), USDC本轮归零(上轮3笔$330.7万); USDT较上轮$153.6万放量≈3.7x
- whale 27条(上轮27持平): TetherTreasury in$5.35亿/out$2.45亿(**连续第4轮完全同额=存量回环, 非新异动**); Binance_1 ETH净流出≈10,001枚(上轮净入2,677 → 方向反转) + USDT入所$338.65万 + ANKR 1,792万枚/SPELL 962万枚入所(上轮PEPE 296.8亿/SHIB 3.2亿出, 标的换新); Binance_2 XAICAT 16亿+PIPECAT 2,200万枚(记忆币不在池); Coinbase KEI 3.12亿/BIRB 4亿/MON 6,000万/INNBC 1.01亿入所(均不在池, 含假币claim 2条伪PEPE/SHIB scam); ETH_GAS 0.30~0.56gwei(上轮0.21微升, 仍低活跃)
- dune 40行(09:18~10:09 BJT新窗口, 上轮08:16~09:12): ETH>100 20笔共22,869枚(上轮17,985 → +27%, 最大11,456单腿vs上轮2,681) | USDC>$500K 13行 gross≈**$3.76亿**, txid去重8笔≈$2.41亿(含镜像1对$9,265万) | USDT>$500K 7行回归 gross≈$1.50亿(上轮0行), 去重5笔≈$1.13亿(含镜像1对$3,020万)
