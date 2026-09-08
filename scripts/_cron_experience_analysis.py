"""Experience analysis cron job - process latest sell trade and update archive."""
import sys
sys.path.insert(0, '/Users/lidaosong/zq_web4_trading_system/tools')
from trade_experience import analyze_exit, record_trade_experience

TRADES_PATH = '/Users/lidaosong/zq_web4_trading_system/audit/TRADES.md'

with open(TRADES_PATH) as f:
    lines = f.readlines()

# Find the most recent SELL (supporting both pipe formats)
recent_sell = None
recent_sell_idx = -1

for i in range(len(lines) - 1, -1, -1):
    line = lines[i]
    if 'SELL' in line and 'NO TRADE' not in line:
        parts = [p.strip() for p in line.split('|')]
        symbol = None
        time_str = None
        price_str = None
        qty_str = None

        for idx, p in enumerate(parts):
            if p == 'SELL':
                if idx + 1 < len(parts):
                    symbol = parts[idx + 1]
                if idx - 1 >= 0:
                    time_str = parts[idx - 1]
                if idx + 2 < len(parts):
                    qty_str = parts[idx + 2]
                if idx + 3 < len(parts):
                    price_str = parts[idx + 3].replace('$', '')
                break

        if symbol and symbol:
            recent_sell = {
                'symbol': symbol,
                'time': time_str,
                'price': price_str,
                'qty': qty_str
            }
            recent_sell_idx = i
            break

if not recent_sell:
    print('[SILENT]')
    sys.exit(0)

symbol = recent_sell['symbol']
sell_time = recent_sell['time']

# Find corresponding BUY (scan backwards from sell)
buy_record = None
for i in range(recent_sell_idx - 1, -1, -1):
    line = lines[i]
    if 'BUY' in line and symbol.upper() in line.upper():
        parts = [p.strip() for p in line.split('|')]
        for idx, p in enumerate(parts):
            if p == 'BUY' and idx + 1 < len(parts) and parts[idx + 1] == symbol:
                buy_time = parts[idx - 1] if idx - 1 >= 0 else None
                buy_qty = parts[idx + 2] if idx + 2 < len(parts) else None
                buy_price = parts[idx + 3].replace('$', '') if idx + 3 < len(parts) else None
                buy_record = {
                    'symbol': symbol,
                    'time': buy_time,
                    'price': buy_price,
                    'qty': buy_qty
                }
                break
        if buy_record:
            break

if not buy_record:
    print(f'未找到{symbol}的买入记录')
    sys.exit(0)

# Run analysis
analysis = analyze_exit(recent_sell, buy_record)
record_trade_experience(analysis)

pnl = analysis.get('pnl_pct', 0)
quality = analysis.get('exit_quality', 'unknown')
exit_reason = analysis.get('exit_reason', 'N/A')
hold_time = analysis.get('hold_time', 'N/A')

print(f'[经验分析] {symbol} | P&L:{pnl:+.1f}% | 质量:{quality} | 持有:{hold_time} | 原因:{exit_reason}')
print(f'  卖出: {sell_time} @ ${recent_sell["price"]}')
print(f'  买入: {buy_record["time"]} @ ${buy_record["price"]}')
print(f'  P&L: {analysis.get("pnl_abs", 0):+.2f}')
