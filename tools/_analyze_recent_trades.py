"""Analyze the 3 latest trades from today (2026-06-27) and record experience."""
import sys
sys.path.insert(0, 'tools')
from trade_experience import *
import json, re, os

# Read TRADES.md
with open('audit/TRADES.md') as f:
    all_text = f.read()

# Define the 3 recent sells from today's summaries
trades = [
    {'symbol': 'NEAR', 'qty': 5.3365, 'pnl_pct': 14.00, 'sell_time': '2026-06-27 08:36 BJT', 'reason': 'A4 Blade止盈—NEAR SELL_ALL +14.00%'},
    {'symbol': 'UNI',  'qty': 1.2238, 'pnl_pct': -15.57, 'sell_time': '2026-06-27 09:08 BJT', 'reason': 'A4 Blade止损—UNI SELL_ALL -15.57%'},
    {'symbol': 'JTO',  'qty': 30.7429, 'pnl_pct': 39.63, 'sell_time': '2026-06-27 09:08 BJT', 'reason': 'A4 Blade止盈—JTO SELL_ALL +39.63%'},
]

results = []

for t in trades:
    sym = t['symbol']
    pnl_pct = t['pnl_pct']
    
    # Build sell info
    # Calculate sell_price from PnL% formula: sell_price = buy_price * (1 + pnl_pct/100)
    # We need to find buy_price first
    
    # Search for buy info in the text: pattern "SYM | QTY | $ENTRY" in position detail tables
    # Look for patterns like "UNI | 1.224 | $3.067"
    pattern = r'\|\s*\*?\.?\*?' + re.escape(sym) + r'\s*\*?\.?\*?\s*\|\s*([\d,.]+)\s*\|\s*\$?([\d,.]+)'
    buy_matches = re.findall(pattern, all_text, re.IGNORECASE)
    
    buy_price_found = None
    buy_qty_found = None
    
    if buy_matches:
        for bq, bp in buy_matches:
            bq = bq.replace(',', '')
            bp = bp.replace(',', '')
            try:
                bq_f = float(bq)
                bp_f = float(bp)
            except:
                continue
            # Check if the qty matches roughly (sell qty should be <= buy qty or close)
            if abs(bq_f - t['qty']) / max(bq_f, 0.001) < 0.5 or abs(bq_f - t['qty']) < 1:
                buy_price_found = bp_f
                buy_qty_found = bq_f
                break
            # Also check if buy_qty is close to sell_qty as a proportion
            if bq_f > t['qty'] * 0.5 and bq_f < t['qty'] * 2:
                buy_price_found = bp_f
                buy_qty_found = bq_f
    
    # Also search for explicit format: "SYM | QTY | $PRICE" in TRADES.md position sections
    if not buy_price_found:
        # Try different formats
        patterns = [
            rf'\|\s*{re.escape(sym)}\s*\|\s*([\d,.]+)\s*\|\s*\$?([\d,.]+)',
            rf'{re.escape(sym)}\s*\|\s*([\d,.]+)\s*\|\s*\$\s*([\d,.]+)',
        ]
        for pat in patterns:
            matches = re.findall(pat, all_text, re.IGNORECASE)
            for bq, bp in matches:
                bq = bq.replace(',', '')
                bp = bp.replace(',', '')
                try:
                    bq_f = float(bq)
                    bp_f = float(bp)
                except:
                    continue
                if 0 < bp_f < 1000 and 0 < bq_f < 100000:
                    buy_price_found = bp_f
                    buy_qty_found = bq_f
                    break
            if buy_price_found:
                break
    
    if buy_price_found and buy_price_found > 0:
        sell_price = buy_price_found * (1 + pnl_pct / 100)
    else:
        # Try deriving from trade context
        # For UNI dust: we saw entry $3.067, qty 1.224
        # For JTO: need to search harder
        sell_price = 0
        buy_price_found = 0
        buy_qty_found = 0
    
    print(f'=== {sym} ===')
    print(f'  Buy qty: {buy_qty_found}, Buy price: {buy_price_found}')
    print(f'  Sell qty: {t["qty"]}, Est sell price: ${sell_price:.4f}' if sell_price else f'  Sell qty: {t["qty"]}, No buy price found')
    
    # Build analysis manually if we have buy price
    if buy_price_found and buy_price_found > 0:
        sell_info = {
            'symbol': sym,
            'time': t['sell_time'],
            'price': str(sell_price),
            'qty': str(t['qty']),
            'reason': t['reason'],
        }
        buy_info = {
            'symbol': sym,
            'time': '2026-06-23 (estimate)',
            'price': str(buy_price_found),
            'qty': str(buy_qty_found),
            'reason': '评分自动执行',
        }
        
        analysis = analyze_exit(sell_info, buy_info)
        analysis['pnl_pct'] = pnl_pct  # override with exact PnL from system
        
        # Recalculate exit_quality based on actual PnL
        if pnl_pct >= 2.99:
            analysis['exit_quality'] = 'correct'
            analysis['lesson'] = f'{sym}卖在盈利位(+{pnl_pct:.1f}%)，信号有效'
        elif pnl_pct > -1:
            analysis['exit_quality'] = 'neutral'
            analysis['lesson'] = f'{sym}平进平出({pnl_pct:+.1f}%)，E2/E3可能误触'
        else:
            analysis['exit_quality'] = 'wrong'
            analysis['lesson'] = f'{sym}亏损{pnl_pct:.1f}%，退出信号过早'
        
        # Override trigger signals based on context
        if pnl_pct > 0:
            analysis['trigger_signals'] = ['止盈']
        else:
            analysis['trigger_signals'] = ['硬止损']
        
        entry = record_trade_experience(analysis)
        if entry:
            print(f'  ✅ 经验已记录: P&L:{pnl_pct:+.1f}% 质量:{analysis["exit_quality"]}')
            results.append(analysis)
        else:
            print(f'  ⏭️ 已存在(跳过重复)')
    else:
        print(f'  ⚠️ 找不到买入信息，跳过')

# Final summary
print(f'\n{"="*50}')
print(f'本轮处理: {len(results)}/{len(trades)} 笔交易')
for r in results:
    print(f'  {r["symbol"]}: P&L{r["pnl_pct"]:+.1f}% | 质量:{r["exit_quality"]} | 信号:{r["trigger_signals"]}')

# Show updated master stats
master = load_master()
print(f'\n总档案更新后:')
print(f'  总分析交易: {master["stats"]["total_trades_analyzed"]}')
print(f'  正确退出: {master["stats"]["correct_exits"]}')
print(f'  错误退出: {master["stats"]["wrong_exits"]}')
print(f'  过早退出: {master["stats"]["too_early_exits"]}')
