#!/usr/bin/env python3
"""
process_new_sells.py — Process latest SELL_ALL operations from TRADES.md assessment format.
"""
import sys, re, json, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from trade_experience import analyze_exit, record_trade_experience, load_master

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRADES_FILE = os.path.join(BASE, 'audit', 'TRADES.md')
trades_dir = os.path.join(BASE, 'data', 'experience', 'trades')

with open(TRADES_FILE) as f:
    lines = f.read().split('\n')

# Parse sections
sections = []
current_ts = ''
current_type = ''
current_detail = ''

for line in lines:
    h_match = re.match(r'^###\s+(.*?)\s*\|\s*(\S+)\s*$', line)
    if h_match:
        if current_ts and current_type and current_detail:
            sections.append({'ts': current_ts.strip(), 'type': current_type.strip(), 'detail': current_detail.strip()})
        current_ts = h_match.group(1).strip()
        current_type = h_match.group(2).strip()
        current_detail = ''
    elif current_ts and '|' in line and '\u5b57\u6bb5' not in line and ':---' not in line:
        parts = [p.strip() for p in line.split('|')]
        if len(parts) >= 3 and parts[1] in ('\u8be6\u60c5', '\u64cd\u4f5c'):
            current_detail += parts[2] if len(parts) >= 3 else ''

if current_ts and current_type and current_detail:
    sections.append({'ts': current_ts.strip(), 'type': current_type.strip(), 'detail': current_detail.strip()})

sell_pnl_re = r'([A-Z0-9]+)\s+SELL_ALL\s+\(PnL=([+-]?[0-9.]+)%\)'
signal_qty_re = r'\u5356\u51fa:\s*\[([^\]]+)\]'
signal_buy_re = r'\u4e70\u5165:\s*\[([^\]]+)\]'

# Find latest assessment with SELL_ALL and latest signal with sell qty
latest_sell_data = {}
for s in sections:
    if '\u6301\u4ed3\u8bc4\u4f30' in s['type']:
        sells = {}
        for m in re.finditer(sell_pnl_re, s['detail']):
            sells[m.group(1)] = float(m.group(2))
        if sells:
            latest_sell_data = {'ts': s['ts'], 'type': s['type'], 'sells': sells}

latest_signal_data = {}
for s in sections:
    if '\u4fe1\u53f7\u53d1\u9001' in s['type']:
        sqty = {}
        sm = re.search(signal_qty_re, s['detail'])
        if sm:
            for item in sm.group(1).split(','):
                m2 = re.match(r'([A-Z]+)([0-9.]+)', item.strip())
                if m2:
                    sqty[m2.group(1)] = float(m2.group(2))
        buy_amt = {}
        bm = re.search(signal_buy_re, s['detail'])
        if bm:
            for item in bm.group(1).split(','):
                m2 = re.match(r'([A-Z]+)\$([0-9.]+)', item.strip())
                if m2:
                    buy_amt[m2.group(1)] = float(m2.group(2))
        if sqty:
            latest_signal_data = {'ts': s['ts'], 'type': s['type'], 'sell_qty': sqty, 'buy_amt': buy_amt}

print("Latest assessment sells:", latest_sell_data.get('sells', {}))
print("Latest signal sells:", latest_signal_data.get('sell_qty', {}))

# Record new entries
new_records = 0
for sym, pnl_pct in latest_sell_data.get('sells', {}).items():
    sell_qty = latest_signal_data.get('sell_qty', {}).get(sym, 0)
    buy_amt = latest_signal_data.get('buy_amt', {}).get(sym, 0)

    if sell_qty <= 0 or buy_amt <= 0:
        print(f"SKIP {sym}: missing data (qty={sell_qty}, buy_amt={buy_amt})")
        continue

    buy_price = buy_amt / sell_qty
    sell_price = buy_price * (1 + pnl_pct / 100)

    reason = 'P1 take-profit (SELL_ALL)' if pnl_pct > 5 else 'E3 trend exit (SELL_ALL)'
    if pnl_pct < -20:
        reason = 'E5 stop-loss (SELL_ALL)'

    sell_info = {
        'symbol': sym,
        'time': latest_sell_data['ts'],
        'price': f'{sell_price:.4f}',
        'qty': f'{sell_qty}',
        'reason': reason
    }
    buy_info = {
        'symbol': sym,
        'time': latest_signal_data['ts'],
        'price': f'{buy_price:.4f}',
        'qty': f'{sell_qty}',
        'reason': 'score-based entry'
    }

    analysis = analyze_exit(sell_info, buy_info)
    entry = record_trade_experience(analysis)

    if entry:
        new_records += 1
        print(f"RECORDED {sym}: PnL={pnl_pct:+.1f}% quality={analysis['exit_quality']} buy=${buy_price:.4f} sell=${sell_price:.4f}")
    else:
        print(f"SKIP {sym}: already exists (sell_time check)")

# Also check old pipe-format
print()
from trade_experience import get_last_exit
result = get_last_exit()
if result:
    sell = result['sell']
    buy = result['buy']
    ts_str = sell['time'].replace(':', '-').replace(' ', '_')
    sym = sell['symbol']
    trade_file = os.path.join(trades_dir, f'{ts_str}_{sym}.json')
    if os.path.exists(trade_file):
        print(f"Old-format last sell {sell['symbol']}@{sell['time']}: already recorded")
    else:
        print(f"Old-format last sell {sell['symbol']}@{sell['time']}: NOT yet recorded — would record now")
        analysis = analyze_exit(sell, buy)
        entry = record_trade_experience(analysis)
        if entry:
            new_records += 1
            print(f"  RECORDED {sell['symbol']}: PnL={analysis['pnl_pct']:+.1f}%")
else:
    print("No old-format sells found")

master = load_master()
print(f"\n=== Summary ===")
print(f"New records: {new_records}")
print(f"Master: trades={master['stats']['total_trades_analyzed']}, "
      f"correct={master['stats']['correct_exits']}, "
      f"wrong={master['stats']['wrong_exits']}, "
      f"too_early={master['stats']['too_early_exits']}")
print(f"Last updated: {master.get('last_updated', 'N/A')}")
