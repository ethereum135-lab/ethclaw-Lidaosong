# Blade 独立记忆

## 执行流程
1. 接收指令（来自Commander）
2. 检查 `agents/fk/veto.json` → 有否决则返回"FK阻止"
3. 检查USDT余额 → 不足返回"资金不足"
4. 检查API连接 → 不通返回"API异常"
5. 执行市价单
6. 记录TRADES.md + TECH_REVIEWS.md

## 交易对格式
- Binance标准：`SYMBOLUSDT`
- 买入用`quoteOrderQty`（USDT金额）
- 卖出用`quantity`（币数量）
