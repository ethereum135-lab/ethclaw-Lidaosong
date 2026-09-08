#!/usr/bin/env python3
"""Analyze narrative-format sells from TRADES.md and record as experience."""
import sys, os, json, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from trade_experience import analyze_exit, record_trade_experience, show_master

TRADES_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'audit', 'TRADES.md')
with open(TRADES_FILE) as f:
    content = f.read()

# Pattern: **SELL SYM** QTY@$PRICE=$TOTAL — REASON
pattern = r'\*\*SELL\s+(\w+)\*\*\s+([\d.]+)@\$?([\d.]+)=\$?([\d.]+)\s*[—–-]+\s*(.+)'
sells = []
for m in re.finditer(pattern, content):
    sym = m.group(1)
    qty = float(m.group(2))
    price = float(m.group(3))
    total = float(m.group(4))
    reason = m.group(5).strip()
    sells.append({
        'symbol': sym, 'qty': qty, 'price': price,
        'total': total, 'reason': reason,
        'pos': m.start()
    })

print(f'找到 {len(sells)} 笔叙事格式卖出')
analyzed = 0

for s in sells:
    pos = s['pos']
    # Get time context from section heading
    heading_pos = content.rfind('## 节点时间', 0, pos)
    time_ctx = ''
    if heading_pos >= 0:
        heading_line = content[heading_pos:content.find('\n', heading_pos)]
        tm = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})', heading_line)
        if tm:
            time_ctx = tm.group(1)

    print(f'\n--- {s["symbol"]} ---')
    print(f'  卖出: {s["qty"]}@{s["price"]}={s["total"]:.2f} 原因: {s["reason"]}')
    print(f'  时间: {time_ctx}')

    # Check if already recorded
    trade_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'experience', 'trades')
    already = False
    if os.path.isdir(trade_dir):
        for fname in os.listdir(trade_dir):
            if s['symbol'] in fname and fname.endswith('.json'):
                try:
                    with open(os.path.join(trade_dir, fname)) as f:
                        data = json.load(f)
                    existing_time = data.get('analysis', {}).get('sell_time', '')
                    if time_ctx[:10] in existing_time:
                        already = True
                        break
                except:
                    pass
    if already:
        print(f'  -> 已在经验库中，跳过')
        continue

    # Find entry price from position tables
    buy_price = None
    buy_qty = None
    lines = content[:pos].split('\n')
    for line in reversed(lines):
        stripped = line.strip()
        if not stripped.startswith('|'):
            continue
        cells = [c.strip() for c in stripped.split('|')]
        if len(cells) < 4:
            continue
        if cells[1] == s['symbol'] or cells[1].strip() == s['symbol']:
            try:
                buy_qty_val = float(cells[2])
                buy_price_str = cells[3].replace('$', '').replace(',', '')
                buy_price_val = float(buy_price_str)
                buy_price = buy_price_val
                buy_qty = buy_qty_val
                break
            except (ValueError, IndexError):
                pass

    # Try simpler table format (the current session format)
    if not buy_price:
        for line in reversed(lines):
            stripped = line.strip()
            cells = [c.strip() for c in stripped.split('|')]
            if len(cells) >= 4 and (s['symbol'] in cells[1] or s['symbol'] in cells[0]):
                try:
                    for ci in range(min(4, len(cells))):
                        val = cells[ci].replace('$', '').replace(',', '').strip()
                        if val and val.replace('.', '').isdigit():
                            buy_price = float(val)
                            break
                except:
                    pass
                if buy_price:
                    break

    if buy_price and buy_price > 0:
        sell_info = {
            'symbol': s['symbol'],
            'time': time_ctx if time_ctx else '2026-06-20',
            'price': str(s['price']),
            'qty': str(s['qty']),
            'reason': s['reason'],
        }
        buy_info = {
            'symbol': s['symbol'],
            'time': '未知',
            'price': str(buy_price),
            'qty': str(buy_qty or s['qty']),
            'reason': '前期买入',
        }
        print(f'  入场价: {buy_price}')

        analysis = analyze_exit(sell_info, buy_info)
        entry = record_trade_experience(analysis)
        if entry:
            print(f'  ✅ 经验已记录: P&L={analysis["pnl_pct"]:+.1f}% 质量={analysis["exit_quality"]}')
            print(f'     经验: {analysis["lesson"]}')
            analyzed += 1
        else:
            print(f'  ➖ 跳过(已存在)')
    else:
        print(f'  ❌ 未找到入场价')
        # Still record with 0% P&L estimate
        sell_info = {
            'symbol': s['symbol'],
            'time': time_ctx if time_ctx else '2026-06-20',
            'price': str(s['price']),
            'qty': str(s['qty']),
            'reason': s['reason'],
        }
        analysis = analyze_exit(sell_info, sell_info)  # same buy/sell = 0% P&L
        entry = record_trade_experience(analysis)
        if entry:
            print(f'  ⚠️ 已记录(默认P&L=0%): 质量={analysis["exit_quality"]}')
            analyzed += 1
        else:
            print(f'  ➖ 跳过(已存在)')

print(f'\n共分析 {analyzed} 笔新交易')
print(show_master())
