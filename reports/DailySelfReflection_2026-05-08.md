# ZQ-FK 每日自我反思 · 2026-05-08 21:00

## 今日数据概要

| 指标 | 数值 |
|:---|---:|
| 买入 | **27 笔** |
| 卖出 | **22 笔** |
| 涉及币种 | **20 个** (SOL/DOGE/TAO/BNB/AAVE/XAUT/IO/WLFI/KSM 等) |
| 退出信号分布 | E3(10次) > E4组合(5次) > P1(3次) > P3(2次) > E2(1次) |
| 盈利退出 | **0 笔** — 所有退出均为防御性触发 |

## 今日盈亏判断

**结论：大概率亏损。** 22笔卖出全部由 E3/E4/P3/P1 防御信号触发，无主动止盈退出。最后已知余额 snapshot 为05-06 06:10的 $877.72（含持仓），此后 node_history 和 trend_store 数据写入已停止。

## 最值得改的一个问题

**🔴 数据持久化断裂：node_history.jsonl 和 trend_store.json 自05-06 06:10起停止更新，已静默中断 >62小时。**

后果：Quant 量化分析(23:00)、每日复盘(00:15)、FK风控检查(每35分钟) 全依赖这些结构化数据文件。数据断裂导致：
1. Quant 分析报告基于陈旧数据（截至05-06早的数据），看不到今日22笔退出
2. 组合趋势和TOP5评分无法追踪
3. 无法用结构化方法计算今日精确P&L——只能靠手算TRADES.md

**根因推测：** node_history 写入逻辑在 engine_realtime_v2.py 的 `log_node()` 或 `save_node_snapshot()` 函数中。可能自05-06引擎切换/调整后，该路径未正确触发。

## 明日改进方向

1. **修复 node_history / trend_store 写入** — 查 engine_realtime_v2.py 中写入这两个文件的代码路径，确认是否有条件分支屏蔽了写入
2. **检查引擎当前版本** — root 和 production 两版 engine_realtime_v2.py 的 diff 差异（已知存在不同步风险）
3. **对今日22笔退出做批量经验分析** — 使用 `batch-analyze-sells.py` 补全MASTER_EXPERIENCE.json（当前为0条记录，说明经验分析cron也未正确触发）
4. **追踪WLFI/KSM当前持仓盈亏** — 从 AWS 查 Binance 实时余额确认今日净P&L
