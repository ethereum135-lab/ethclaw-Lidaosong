#!/usr/bin/env python3
"""Analyze the latest sell from TRADES.md (markdown node format) and record to experience archive."""
import sys, re, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from trade_experience import analyze_exit, record_trade_experience, load_master

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRADES_FILE = os.path.join(BASE, 'audit', 'TRADES.md')
TRADES_DIR = os.path.join(BASE, 'data', 'experience', 'trades')

with open(TRADES_FILE) as f:
    text = f.read()

MULT = '\u00d7'

# Find all SELL lines in markdown format
sells = []
for line in text.split('\n'):
    if 'SELL ' not in line:
        continue
    stripped = line.replace('**', '')
    # Pattern: SELL SYM QTY×$PRICE=$VALUE
    match = re.search(r'SELL\s+(\w+)\s+([0-9.]+)' + re.escape(MULT) + r'\$([0-9.]+)=\$([0-9.]+)', stripped)
    if not match:
        continue
    sym = match.group(1)
    qty = float(match.group(2))
    sell_price = float(match.group(3))
    
    # Extract reason (text after the value)
    line_end = match.end()
    rest = stripped[line_end:]
    reason_match = re.search(r'[\u2014\u2013\u2015\-]{1,2}\s*(.+)', rest)
    reason = reason_match.group(1).strip() if reason_match else rest.strip()
    if not reason:
        reason = 'swap/exit'

    # Find the node header closest above this line
    line_start = text.find(line)
    before = text[:line_start]
    node_matches = list(re.finditer(r'###\s+([0-9:]+)\s*BJT', before))
    sell_time = node_matches[-1].group(1) + ' BJT' if node_matches else 'unknown'

    sells.append({'symbol': sym, 'time': sell_time, 'price': sell_price,
                  'qty': qty, 'reason': reason, 'pos': line_start})

if not sells:
    print('NO_SELL_FOUND')
    sys.exit(0)

# Most recent = last in file
sells.sort(key=lambda x: x['pos'])
latest = sells[-1]

# Check if already analyzed
existing = [f for f in os.listdir(TRADES_DIR) if latest['symbol'] in f]
if existing:
    print('ALREADY_ANALYZED:%s:%s' % (latest['symbol'], '|'.join(existing)))
    sys.exit(0)

# Try to find buy price from holdings table
buy_price = None
for m in re.finditer(r'\|\s*' + re.escape(latest['symbol']) + r'\s*\|\s*([0-9.]+|N/A)\s*\|\s*\$([0-9.]+)', text):
    if m.start() < latest['pos']:
        buy_price = float(m.group(2))

# Construct sell_info and buy_info
sell_info = {
    'symbol': latest['symbol'],
    'time': latest['time'],
    'price': str(latest['price']),
    'qty': str(latest['qty']),
    'reason': latest['reason']
}
buy_info = None
if buy_price:
    buy_info = {
        'symbol': latest['symbol'],
        'time': latest['time'].replace('BJT', 'prev BJT'),
        'price': str(buy_price),
        'qty': str(latest['qty']),
        'reason': 'holding from previous node'
    }

analysis = analyze_exit(sell_info, buy_info)
entry = record_trade_experience(analysis)

if entry:
    print('RECORDED:%s:P&L=%+.1f%%:quality=%s:signals=%s:%s' % (
        latest['symbol'], analysis['pnl_pct'], analysis['exit_quality'],
        analysis['trigger_signals'], analysis['lesson']))
else:
    print('SKIPPED:%s:already_exists' % latest['symbol'])

master = load_master()
stats = master.get('stats', {})
print('MASTER:trades=%d:correct=%d:wrong=%d:neutral=%d' % (
    stats.get('total_trades_analyzed', 0),
    stats.get('correct_exits', 0),
    stats.get('wrong_exits', 0),
    stats.get('too_early_exits', 0)))
