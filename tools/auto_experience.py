#!/usr/bin/env python3
"""自动分析最新卖出交易并更新总经验档案"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from trade_experience import analyze_exit, record_trade_experience

def parse_trade_line(line):
    """Parse a trade line from TRADES.md — handles both || and ||||||| leading pipe formats."""
    parts = [p.strip() for p in line.split('|')]
    # Remove leading empty strings from pipes
    parts = [p for p in parts if p != '']
    if len(parts) < 5:
        return None
    # Now: parts[0]=date, parts[1]=type(BUY/SELL), parts[2]=symbol, parts[3]=qty, parts[4]=price
    trade_type = parts[1].upper()
    if trade_type not in ('BUY', 'SELL'):
        return None
    price_str = parts[4].replace('$', '').replace(',', '')
    try:
        price = float(price_str)
        qty = float(parts[3])
    except ValueError:
        return None
    reason = parts[5] if len(parts) > 5 else '-'
    return {
        'type': trade_type,
        'time': parts[0],
        'symbol': parts[2],
        'qty': qty,
        'price': price,
        'reason': reason,
    }


def main():
    trades_path = os.path.join(os.path.dirname(__file__), '..', 'audit', 'TRADES.md')
    with open(trades_path) as f:
        lines = f.readlines()
    
    # Find latest SELL (skip header, NO TRADE lines)
    sells = []
    for i, line in enumerate(lines):
        trade = parse_trade_line(line)
        if trade and trade['type'] == 'SELL':
            sells.append((i, trade))
    
    if not sells:
        print('本轮无卖出')
        return
    
    # Find the latest sell by time
    sells.sort(key=lambda x: x[1]['time'], reverse=True)
    sell_idx, sell = sells[0]
    
    # Find corresponding BUY (same symbol, earlier time)
    buys = []
    for i in range(sell_idx - 1, -1, -1):
        trade = parse_trade_line(lines[i])
        if trade and trade['type'] == 'BUY' and trade['symbol'] == sell['symbol']:
            buys.append(trade)
    
    if not buys:
        # Also search forward from beginning
        for i, line in enumerate(lines[:sell_idx]):
            trade = parse_trade_line(line)
            if trade and trade['type'] == 'BUY' and trade['symbol'] == sell['symbol']:
                buys.append(trade)
    
    if not buys:
        print(f'未找到{sell["symbol"]}的买入记录')
        return
    
    # Use the last buy before this sell
    buy = buys[-1]  # last buy entry before sell
    
    print(f'最新卖出: {sell["symbol"]}')
    # Try to extract entry price from sell reason to handle new format
    print(f'  买入: {buy["time"]} ($列={buy["price"]:.8f} reason={buy["reason"][:60]})')
    print(f'  卖出: {sell["time"]} ($列={sell["price"]:.8f} reason={sell["reason"][:100]})')
    
    analysis = analyze_exit(sell, buy)
    record_trade_experience(analysis)
    print(f'✅ 经验已记录: {sell["symbol"]} P&L:{analysis["pnl_pct"]:+.2f}% 质量:{analysis["exit_quality"]}')


if __name__ == '__main__':
    main()
