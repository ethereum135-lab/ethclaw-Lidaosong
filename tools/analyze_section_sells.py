#!/usr/bin/env python3
"""
Analyze section-format sells from TRADES.md and record new trade experiences.
Handles the format transition from pipe-table trades to section-based format.
"""
import sys, os, re, json
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, 'tools'))

from trade_experience import analyze_exit, record_trade_experience, load_master, TRADES_DIR, TRADE_LOG

TRADES_FILE = TRADE_LOG
os.makedirs(TRADES_DIR, exist_ok=True)

def parse_section_sells(content):
    """Parse section-based '信号发送' blocks to extract sell symbols+price."""
    section_pattern = r'###\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\s*BJT)\s*\|\s*信号发送'
    sections = list(re.finditer(section_pattern, content))
    
    sells = []
    for sm in sections:
        section_time = sm.group(1).strip()
        # Find the 详情 line in this section (within next 10 lines)
        section_start = sm.end()
        section_block = content[section_start:section_start+1500]
        
        detail_match = re.search(r'\|\s*详情\s*\|\s*[^|]*?卖出:\s*\[([^\]]*)\]', section_block)
        if detail_match:
            items_str = detail_match.group(1).strip()
            for item in re.split(r',\s*', items_str):
                item = item.strip()
                if not item:
                    continue
                # Extract symbol and price: FIL0.9868 or NEAR13.102 or UNI1.2238
                m = re.match(r'([A-Za-z]+)([\d.]+)', item)
                if m:
                    sym = m.group(1)
                    price = float(m.group(2))
                    sells.append({
                        'symbol': sym,
                        'price': price,
                        'time': section_time,
                        'raw_item': item,
                        'section_time': section_time,
                    })
    return sells

def is_analyzed(symbol, price, sell_time):
    """Check if a trade is already in the experience DB, considering price."""
    for fname in os.listdir(TRADES_DIR):
        if symbol in fname and fname.endswith('.json'):
            try:
                with open(os.path.join(TRADES_DIR, fname)) as f:
                    data = json.load(f)
                a = data.get('analysis', {})
                # Same symbol + very close price (~1% tolerance) = already analyzed
                if a.get('symbol') == symbol and abs(a.get('sell_price', 0) - price) / max(price, 0.001) < 0.01:
                    return True
            except:
                pass
    return False

def find_buy(content, symbol, sell_time_str):
    """Find the buy info for a symbol from TRADES.md section format."""
    # Look in 持仓评估 sections for entry prices
    section_pattern = r'###\s+(\d{4}-\d{2}-\d{2}T?\d{2}:\d{2}[^|]*)\|'
    sections = list(re.finditer(section_pattern, content))
    
    buys = []
    # Try to find in pipe-format BUY rows (older format)
    buy_pipe = re.finditer(r'\|\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s*\|\s*BUY\s*\|\s*' + symbol + r'\s*\|\s*([\d.]+)\s*\|\s*\$?([\d.]+)', content)
    for m in buy_pipe:
        buy_time = m.group(1).strip()
        buy_qty = float(m.group(2))
        buy_price = float(m.group(3))
        if buy_time < sell_time_str:
            buys.append({'time': buy_time, 'price': buy_price, 'qty': buy_qty})
    
    # Also look for BUY in section format: BUY SYM QTY@$PRICE=TOTAL
    buy_narr = re.finditer(r'BUY\s+' + symbol + r'\s+([\d.]+)@\$?([\d.]+)', content)
    for m in buy_narr:
        buy_qty = float(m.group(1))
        buy_price = float(m.group(2))
        # Find timestamp context
        pos = m.start()
        prev_sec = content.rfind('### ', 0, pos)
        if prev_sec >= 0:
            sec_line = content[prev_sec:content.find('\n', prev_sec)]
            tm = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})', sec_line)
            if tm:
                buy_time = tm.group(1)
                if buy_time < sell_time_str:
                    buys.append({'time': buy_time, 'price': buy_price, 'qty': buy_qty})
    
    if buys:
        buys.sort(key=lambda x: x['time'], reverse=True)
        return buys[0]
    return None

def backfill_buy_from_pnl(sell_price, pnl_str):
    """Back-calculate buy price from PnL percentage string."""
    m = re.search(r'([+-]?\d+\.?\d*)%', pnl_str)
    if m:
        pnl_pct = float(m.group(1))
        return sell_price / (1 + pnl_pct / 100)
    return None

def parse_position_eval_pnl(content, symbol, sell_time_str):
    """Find PnL from 持仓评估 section for a given symbol."""
    # Look for: SYM SELL_ALL (PnL=±XX.XX%)
    section_end = content.find('###', content.find(sell_time_str) + 1)
    if section_end < 0:
        section_end = len(content)
    scope = content[max(0, content.find(sell_time_str)-200):section_end+200]
    
    m = re.search(symbol + r'\s+SELL_ALL\s*\(PnL=([+-]?\d+\.?\d*)%\)', scope)
    if m:
        return float(m.group(1))
    return None

def main():
    print("=" * 60)
    print(f"Section-format 卖出分析 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    with open(TRADES_FILE) as f:
        content = f.read()
    
    sells = parse_section_sells(content)
    print(f"\n找到 {len(sells)} 笔信号发送卖出项")
    
    # Filter: only the latest occurrence for each symbol
    latest_by_sym = {}
    for s in sells:
        key = s['symbol']
        if key not in latest_by_sym or s['time'] > latest_by_sym[key]['time']:
            latest_by_sym[key] = s
    
    print(f"\n--- 每币种最新信号 ---")
    for sym, s in sorted(latest_by_sym.items()):
        already = is_analyzed(sym, s['price'], s['time'])
        check = "✅ 已分析" if already else "⏳ 新信号"
        pnl = parse_position_eval_pnl(content, sym, s['time'])
        pnl_str = f" PnL={pnl:+.2f}%" if pnl else ""
        print(f"  {sym:6s} @ ${s['price']:<8.4f} [{s['time']}]{pnl_str}  {check}")
    
    print(f"\n--- 分析新卖出 ---")
    added = 0
    skipped = 0
    failed = 0
    
    for s in sorted(latest_by_sym.values(), key=lambda x: x['time'], reverse=True):
        if is_analyzed(s['symbol'], s['price'], s['time']):
            skipped += 1
            continue
        
        print(f"\n处理: {s['symbol']} @ ${s['price']} [{s['time']}]")
        
        # Find buy
        buy = find_buy(content, s['symbol'], s['time'])
        
        # Try PnL backfill
        pnl_val = parse_position_eval_pnl(content, s['symbol'], s['time'])
        if not buy and pnl_val is not None:
            implied_buy = backfill_buy_from_pnl(s['price'], str(pnl_val))
            if implied_buy:
                buy = {'time': '未知(从PnL反推)', 'price': implied_buy, 'qty': 0}
                print(f"  -> 从PnL反推买入价: ${implied_buy:.4f}")
        elif buy:
            print(f"  -> 对应买入: {buy['qty']}@${buy['price']} [{buy['time']}]")
        else:
            print(f"  -> ⚠️ 未找到对应买入")
        
        # Build trade info dicts
        sell_info = {
            'symbol': s['symbol'],
            'time': s['time'],
            'price': str(s['price']),
            'qty': '0',
            'reason': f'信号卖出 @${s["price"]}',
        }
        
        buy_info = None
        if buy:
            buy_info = {
                'symbol': s['symbol'],
                'time': buy['time'],
                'price': str(buy['price']),
                'qty': str(buy['qty']),
                'reason': '前期买入',
            }
        
        try:
            analysis = analyze_exit(sell_info, buy_info)
            entry = record_trade_experience(analysis)
            if entry:
                added += 1
                print(f"  ✅ 新经验: P&L={analysis['pnl_pct']:+.2f}% 质量={analysis['exit_quality']}")
                print(f"     经验: {analysis['lesson']}")
                print(f"     信号: {analysis['trigger_signals']}")
            else:
                skipped += 1
                print(f"  ➖ 跳过(已存在)")
        except Exception as e:
            failed += 1
            print(f"  ❌ 失败: {e}")
    
    print(f"\n{'='*60}")
    print(f"结果: +{added}条新经验 | {skipped}跳过 | {failed}失败")
    
    # Show updated master
    master = load_master()
    s = master.get('stats', {})
    print(f"\n总经验档案:")
    print(f"  分析交易数: {s.get('total_trades_analyzed', 0)}")
    print(f"  正确退出:   {s.get('correct_exits', 0)}")
    print(f"  错误退出:   {s.get('wrong_exits', 0)}")
    print(f"  中性退出:   {s.get('too_early_exits', 0)}")
    
    print("\n--- 信号表现 ---")
    for sig, perf in sorted(master.get('exit_signal_performance', {}).items()):
        rate = perf['correct'] / perf['total'] * 100 if perf['total'] > 0 else 0
        print(f"  {sig:20s}: {perf['total']:4d}次 正确率{rate:5.1f}%")

if __name__ == '__main__':
    main()
