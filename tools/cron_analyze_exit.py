#!/usr/bin/env python3
"""Cron job: analyze latest exit and update experience master"""
import sys
sys.path.insert(0, '/Users/lidaosong/zq_web4_trading_system/tools')
from trade_experience import *
import json

exit_data = get_last_exit()
if not exit_data:
    print('NO_SELL')
    sys.exit(0)

sell_info = exit_data['sell']
buy_info = exit_data['buy']

if not buy_info:
    print(f'NO_BUY_FOUND: {sell_info["symbol"]}')
    sys.exit(0)

analysis = analyze_exit(sell_info, buy_info)
entry = record_trade_experience(analysis)

if entry:
    a = entry['analysis']
    signals = '+'.join(a['trigger_signals']) if a['trigger_signals'] else 'none'
    print(f"RECORDED|{a['symbol']}|{a['pnl_pct']:+.1f}%|${a['pnl_usd']:+.2f}|{a['exit_quality']}|{signals}")
    print(f"DETAIL|buy={a['buy_price']:.4f}|sell={a['sell_price']:.4f}|{a['lesson']}")
else:
    print(f"SKIPPED|{sell_info['symbol']}@{sell_info['time']}")

master = load_master()
total = master['stats'].get('total_trades_analyzed', 0)
correct = master['stats'].get('correct_exits', 0)
wrong = master['stats'].get('wrong_exits', 0)
neutral = master['stats'].get('too_early_exits', 0)
winrate = correct / max(total, 1) * 100

print(f"MASTER|trades={total}|correct={correct}|wrong={wrong}|neutral={neutral}|winrate={winrate:.0f}%")
print("SIGNALS|" + ','.join(
    f"{sig}:{p['total']}t:{p['correct']}c:{p['wrong']}w:{p['neutral']}n:{p['correct']/max(p['total'],1)*100:.0f}%"
    for sig, p in sorted(master.get('exit_signal_performance', {}).items())
))
for rule in master.get('rules', [])[-3:]:
    print(f"RULE|{rule['signal']}|{rule.get('condition','')}|{rule['effectiveness']}")
