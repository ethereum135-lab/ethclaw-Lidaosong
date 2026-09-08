#!/usr/bin/env bash
# cron_analyze_exits.sh — 分析最新卖出并更新总经验档案
cd ~/zq_web4_trading_system
python3 << 'PYEOF'
import sys; sys.path.insert(0, 'tools')
from trade_experience import *

result = get_last_exit()
if result and result.get('sell') and result.get('buy'):
    analysis = analyze_exit(result['sell'], result['buy'])
    entry = record_trade_experience(analysis)
    print(f"OK: {analysis['symbol']} P&L:{analysis['pnl_pct']:+.2f}% ($ {analysis['pnl_usd']:+.2f}) quality:{analysis['exit_quality']} signals:{analysis['trigger_signals']}")
    print(f"  lesson: {analysis['lesson']}")
elif result and result.get('sell'):
    print(f"SELL_FOUND_NO_BUY: {result['sell']['symbol']} but no matching buy record")
else:
    print("NO_SELL")
PYEOF
