#!/usr/bin/env python3
"""Parse node_check format trades from TRADES.md and run experience analysis."""
import sys; sys.path.insert(0, 'tools')
import re, json, os
from trade_experience import *

def parse_node_check_line(line):
    raw = line
    line = line.replace('**', '').strip()
    parts = [p.strip() for p in line.split('|')]
    if len(parts) < 4:
        return None
    action_symbol = None
    details = None
    for i, p in enumerate(parts):
        p_clean = p.replace('\U0001f534','').replace('\U0001f7e2','').replace('\u26a0\ufe0f','').strip()
        if re.match(r'^(SELL|BUY)\s+[A-Z0-9]+', p_clean):
            action_symbol = p_clean
            details = parts[i+1] if i+1 < len(parts) else ''
            break
    if not action_symbol:
        return None
    action_parts = action_symbol.split(None, 1)
    if len(action_parts) < 2:
        return None
    action = action_parts[0]
    symbol = action_parts[1]
    qty = ''
    price = ''
    reason = details or ''
    at_match = re.match(r'([\d.]+)\s*@\s*~?\$?([\d.]+)', details)
    if at_match:
        qty = at_match.group(1)
        price = at_match.group(2)
        after_at = details[at_match.end():]
        reason = after_at.strip().lstrip('-— ').strip()
    else:
        num_match = re.match(r'([\d.]+)', details)
        if num_match:
            qty = num_match.group(1)
    return {
        'time': 'TABLE_ROW',
        'action': action,
        'symbol': symbol,
        'qty': qty,
        'price': price,
        'reason': reason,
        'data': '',
        'is_table_format': True,
        '_raw_line': raw
    }

# Check for existing trade experience files to avoid re-analysis
def already_analyzed(symbol):
    """Check if this sell was already analyzed (by looking at recent files)."""
    exp_dir = os.path.join('data', 'experience', 'trades')
    if not os.path.isdir(exp_dir):
        return False
    for fname in os.listdir(exp_dir):
        if symbol in fname:
            return True
    return False

with open('audit/TRADES.md') as f:
    lines = f.readlines()

# Parse all node_check sell lines (not table rows, not NO TRADE)
sells = []
for line in lines:
    stripped = line.replace('**', '').replace('\U0001f534', '').replace('\U0001f7e2', '').replace('\u26a0\ufe0f', '')
    parts_check = [p.strip() for p in stripped.split('|')]
    has_sell = 'SELL' in parts_check or any(p.startswith('SELL ') for p in parts_check)
    if has_sell and 'NO TRADE' not in stripped:
        parsed = parse_node_check_line(line)
        if parsed and parsed.get('symbol') and parsed.get('price', '').replace('.','').replace('-','').strip():
            sells.append(parsed)

# Also use get_last_exit() for any traditional format sells
trad_result = get_last_exit()
if trad_result and trad_result['sell']:
    # Check if already in our node_check sells
    ts = trad_result['sell'].get('symbol', '')
    if not any(s['symbol'] == ts for s in sells):
        sells.append(trad_result['sell'])
        print(f"  [传统格式] 加入: {ts}")

sells.sort(key=lambda s: s.get('time', ''), reverse=True)

if not sells:
    print("本轮无卖出记录")
    sys.exit(0)

# Parse all buy lines
buys = []
for line in lines:
    stripped = line.replace('**', '').replace('\U0001f534', '').replace('\U0001f7e2', '').replace('\u26a0\ufe0f', '')
    parts_check = [p.strip() for p in stripped.split('|')]
    has_buy = 'BUY' in parts_check or any(p.startswith('BUY ') for p in parts_check)
    if has_buy and 'NO TRADE' not in stripped and 'BUY_READY' not in stripped:
        parsed = parse_node_check_line(line)
        if parsed and parsed.get('symbol') and parsed.get('price', '').replace('.','').replace('-','').strip():
            buys.append(parsed)

results = []
for sell in sells[:5]:  # Last 5 sells max
    symbol = sell['symbol']
    if already_analyzed(symbol):
        print(f"  [{symbol}] 已分析过，跳过")
        continue

    # Find corresponding buy (latest buy of same symbol)
    matching = [b for b in buys if b['symbol'] == symbol]
    buy = matching[-1] if matching else None
    
    if buy:
        print(f"\n  === {symbol} ===")
        print(f"    卖出: qty={sell['qty']} @ ${sell['price']}")
        print(f"    买入: qty={buy['qty']} @ ${buy['price']}")
        print(f"    理由: {sell['reason'][:60]}")
        
        analysis = analyze_exit(sell, buy)
        print(f"    P&L: {analysis['pnl_pct']:+.1f}%  | 质量: {analysis['exit_quality']}  | 信号: {analysis['trigger_signals']}")
        
        record_trade_experience(analysis)
        print(f"    -> 经验已记录")
        results.append(analysis)
    else:
        print(f"\n  === {symbol} ===")
        print(f"    卖出: qty={sell['qty']} @ ${sell['price']}")
        print(f"    理由: {sell['reason'][:60]}")
        print(f"    未找到对应买入记录，跳过经验分析")

# Show master
print("\n")
print(show_master())
