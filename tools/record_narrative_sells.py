#!/usr/bin/env python3
"""
Record narrative-format sells from TRADES.md into the experience system.
Handles the 2026-06-20 17:07 BJT sells (ORDI, EDEN, MITO) which use
bullet/narrative format that get_last_exit() can't parse.
"""
import sys
sys.path.insert(0, '/Users/lidaosong/zq_web4_trading_system/tools')
sys.path.insert(0, '/Users/lidaosong/zq_web4_trading_system')
import json, os, re
from datetime import datetime
from trade_experience import analyze_exit, record_trade_experience, show_master, load_master, TRADE_LOG

TRADES_FILE = TRADE_LOG if TRADE_LOG else '/Users/lidaosong/zq_web4_trading_system/audit/TRADES.md'
TRADES_DIR = '/Users/lidaosong/zq_web4_trading_system/data/experience/trades'

def is_already_recorded(symbol, sell_time_str):
    """Check if this trade is already in experience DB."""
    os.makedirs(TRADES_DIR, exist_ok=True)
    # Normalize sell time for comparison
    norm_time = sell_time_str.replace(' ', '_').replace(':', '-').replace('BJT', 'BJT')
    for fname in os.listdir(TRADES_DIR):
        if symbol in fname and fname.endswith('.json'):
            try:
                with open(os.path.join(TRADES_DIR, fname)) as f:
                    data = json.load(f)
                existing_sell_time = data.get('analysis', {}).get('sell_time', '')
                # If times overlap enough, skip
                if sell_time_str[:10] in existing_sell_time:
                    return True
            except:
                pass
    return False

def find_narrative_sells():
    """Parse TRADES.md for narrative-format sells (lines like '- ORDI: SL触发(...), 全清 X@$Y=Z')."""
    with open(TRADES_FILE) as f:
        content = f.read()
    
    # Find sell sections: ### ... 止损止盈卖出 ... or ### ... 卖出 ...
    # Pattern 1: `- SYM: REASON, 全清 QTY@$PRICE=TOTAL`
    pattern = r'-\s*(\w+):\s*(.+?),\s*全清\s+([\d.]+)@\$([\d.]+)=?\$?([\d.]+)'
    
    results = []
    for m in re.finditer(pattern, content):
        sym = m.group(1)
        reason = m.group(2).strip()
        qty = float(m.group(3))
        price = float(m.group(4))
        total = float(m.group(5))
        
        # Try to find the section timestamp (look backwards for the closest ### heading)
        pos = m.start()
        prev_section = content.rfind('### ', 0, pos)
        time_ctx = ''
        if prev_section >= 0:
            section_line = content[prev_section:content.find('\n', prev_section)]
            # Extract timestamp like "2026-06-20T17:07BJT"
            tm = re.search(r'(\d{4}-\d{2}-\d{2}T?\d{2}:\d{2})', section_line)
            if tm:
                time_ctx = tm.group(1)
        
        results.append({
            'symbol': sym,
            'time': time_ctx,
            'price': str(price),
            'qty': str(qty),
            'reason': reason,
            'total': total,
            'raw': m.group(0)
        })
    
    return results

def find_recent_buys(symbol, sell_time_str, content):
    """Find the most recent buy for a symbol before the sell time."""
    # Pattern 1: `BUY SYM QTY@$PRICE=TOTAL` (narrative)
    pattern_buy_narr = r'BUY\s+' + re.escape(symbol) + r'\s+([\d.]+)@\$([\d.]+)=?\$?([\d.]+)'
    
    # Pattern 2: pipe format
    pattern_buy_pipe = r'\|?\s*BUY\s*\|\s*' + re.escape(symbol) + r'\s*\|\s*([\d.]+)\s*\|\s*\$?([\d.]+)'
    
    buys = []
    
    for m in re.finditer(pattern_buy_narr, content):
        qty = float(m.group(1))
        price = float(m.group(2))
        total = float(m.group(3)) if len(m.groups()) >= 3 else qty * price
        
        # Get position
        pos = m.start()
        prev_section = content.rfind('### ', 0, pos)
        buy_time = ''
        if prev_section >= 0:
            section_line = content[prev_section:content.find('\n', prev_section)]
            tm = re.search(r'(\d{4}-\d{2}-\d{2}T?\d{2}:\d{2})', section_line)
            if tm:
                buy_time = tm.group(1)
        
        if buy_time and buy_time < sell_time_str:
            buys.append({'time': buy_time, 'price': price, 'qty': qty})
    
    # Also check position tables for entry price
    # Pattern: | SYM | QTY | ENTRY_PRICE | ...
    table_pattern = r'\|[\s]*' + re.escape(symbol) + r'[\s]*\|[\s]*([\d.]+)[\s]*\|[\s]*\$?([\d.]+)[\s]*\|'
    
    for m in re.finditer(table_pattern, content):
        qty = float(m.group(1))
        entry_price = float(m.group(2))
        
        pos = m.start()
        prev_section = content.rfind('### ', 0, pos)
        buy_time = ''
        if prev_section >= 0:
            section_line = content[prev_section:content.find('\n', prev_section)]
            tm = re.search(r'(\d{4}-\d{2}-\d{2}T?\d{2}:\d{2})', section_line)
            if tm:
                buy_time = tm.group(1)
        
        if buy_time and buy_time < sell_time_str:
            buys.append({'time': buy_time, 'price': entry_price, 'qty': qty})
    
    # Return the most recent buy
    if buys:
        buys.sort(key=lambda x: x['time'], reverse=True)
        return buys[0]
    return None

def main():
    print("=" * 60)
    print(f"叙事格式卖出分析 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    with open(TRADES_FILE) as f:
        content = f.read()
    
    sells = find_narrative_sells()
    
    if not sells:
        print("\n未找到叙事格式的卖出记录。")
        return
    
    print(f"\n找到 {len(sells)} 笔叙事格式卖出:\n")
    
    for s in sells:
        print(f"  {s['symbol']}: {s['qty']}@${s['price']}=${s['total']:.2f}")
        print(f"    时间: {s['time']}")
        print(f"    原因: {s['reason']}")
        
        # Check if already recorded
        sell_time_key = s['time'] if s['time'] else s['reason'][:20]
        if is_already_recorded(s['symbol'], sell_time_key):
            print(f"    → 已在经验库中，跳过")
            continue
        
        # Find buy
        buy = find_recent_buys(s['symbol'], s['time'] if s['time'] else '9999-99-99', content)
        
        # Build trade info dicts for analyze_exit
        sell_info = {
            'symbol': s['symbol'],
            'time': s['time'] if s['time'] else datetime.now().strftime('%Y-%m-%d %H:%M'),
            'price': s['price'],
            'qty': s['qty'],
            'reason': s['reason'],
        }
        
        if buy:
            buy_info = {
                'symbol': s['symbol'],
                'time': buy['time'],
                'price': str(buy['price']),
                'qty': str(buy['qty']),
                'reason': '前期买入',
            }
            print(f"    对应买入: {buy['qty']}@${buy['price']} ({buy['time']})")
        else:
            buy_info = None
            print(f"    ⚠️ 未找到对应的买入记录")
            # Use P&L from reason to back-calculate
            pnl_match = re.search(r'([+-]?\d+\.?\d*)%', s['reason'])
            if pnl_match:
                pnl = float(pnl_match.group(1))
                implied_buy = float(s['price']) / (1 + pnl/100)
                buy_info = {
                    'symbol': s['symbol'],
                    'time': '未知(从P&L反推)',
                    'price': str(implied_buy),
                    'qty': s['qty'],
                    'reason': '从P&L反推买入价',
                }
                print(f"    → 从P&L反推买入价: ${implied_buy:.6f}")
        
        try:
            analysis = analyze_exit(sell_info, buy_info)
            entry = record_trade_experience(analysis)
            if entry:
                print(f"    ✅ 经验已记录: P&L={analysis['pnl_pct']:+.1f}% 质量={analysis['exit_quality']}")
                print(f"      经验: {analysis['lesson']}")
            else:
                print(f"    ➖ 跳过(已存在)")
        except Exception as e:
            print(f"    ❌ 分析失败: {e}")
        
        print()
    
    # Show updated master summary
    print("=" * 60)
    print(show_master())

if __name__ == '__main__':
    main()
