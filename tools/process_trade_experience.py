#!/usr/bin/env python3
"""
process_trade_experience.py v2 — 从TRADES.md评估摘要中解析最新卖出并更新经验档案
解析「持仓评估」块中的 SELL_ALL (PnL=±X%) 事件。
"""
import json, os, re, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from trade_experience import analyze_exit, record_trade_experience, load_master

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRADE_LOG = os.path.join(BASE_DIR, 'audit', 'TRADES.md')
TRADES_DIR = os.path.join(BASE_DIR, 'data', 'experience', 'trades')

def parse_eval_sells(lines):
    """解析持仓评估块中的 SELL_ALL (PnL=±X%) 事件"""
    eval_sells = []
    for i, line in enumerate(lines):
        if "持仓评估" in line:
            ts_match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})', line)
            ts = ts_match.group(1) if ts_match else None
            # Look ahead up to 10 lines for the detail row
            for j in range(i, min(i + 10, len(lines))):
                if "详情" in lines[j] and "SELL_ALL" in lines[j]:
                    sells = re.findall(r'(\w+)\s+SELL_ALL\s*\(PnL=([+-]\d+\.?\d*)%?\)', lines[j])
                    for sym, pnl in sells:
                        eval_sells.append({'symbol': sym, 'pnl_pct': float(pnl), 'time': ts})
                    break
    return eval_sells

def is_analyzed(sym, time_str, existing_files):
    """Check if a trade for this symbol is ALREADY recorded for today.
    
    Pitfall #27 fix: SELL_ALL per symbol happens at most once per day.
    Previous dedup (time_prefix + symbol) allowed 30-min evaluation cycles
    to create duplicate files for the same position. Now we check if ANY
    file exists for this symbol from today.
    """
    if not time_str:
        return False
    today = time_str[:10]  # '2026-06-29' (keep hyphens, matches actual filenames like '2026-07-04_11-22_FIL.json')
    for f in existing_files:
        # Match: any file starting with today's date and containing the symbol
        if f.startswith(today) and ('_' + sym + '.json') in f:
            return True
    return False

def main():
    with open(TRADE_LOG) as f:
        lines = f.readlines()

    sells = parse_eval_sells(lines)
    if not sells:
        print("本轮无新卖出需要分析。")
        return

    existing_files = set(os.listdir(TRADES_DIR)) if os.path.isdir(TRADES_DIR) else set()
    unanalyzed = [s for s in sells if not is_analyzed(s['symbol'], s['time'], existing_files)]

    if not unanalyzed:
        print(f"本轮无新卖出需要分析（{len(sells)}笔都已分析）。")
        return

    # Pitfall #27 bis: Dedup to 1-per-symbol-per-day — same position reported every 30 min.
    # Only keep the FIRST unanalyzed occurrence per symbol per day.
    seen_sym_day = set()
    deduped = []
    for s in unanalyzed:
        key = (s['symbol'], s['time'][:10] if s['time'] else 'unknown')
        if key not in seen_sym_day:
            seen_sym_day.add(key)
            deduped.append(s)
    unanalyzed = deduped

    print(f"发现 {len(unanalyzed)} 笔未分析卖出（去重后，原始{len([s for s in sells if not is_analyzed(s['symbol'], s['time'], existing_files)])}笔）:")
    
    # Find the latest buy prices for each symbol from the table-format rows
    buy_prices = {}
    for line in lines:
        if '| BUY ' in line or ' | BUY ' in line:
            parts = [p.strip() for p in line.split('|')]
            for idx in range(1, len(parts) - 2):
                if parts[idx].upper() == 'BUY':
                    sym = parts[idx + 1]
                    qty_str = parts[idx + 2]
                    price_str = parts[idx + 3].replace('$', '')
                    reason = parts[idx + 4] if idx + 4 < len(parts) else ''
                    try:
                        price = float(price_str)
                        qty = float(qty_str) if qty_str else 0
                        if price > 0 and sym:
                            # Store the latest buy for each symbol
                            if sym not in buy_prices or True:  # take the last one found
                                buy_prices[sym] = {'price': price, 'qty': qty, 'reason': reason}
                    except:
                        pass

    results = []
    for s in unanalyzed:
        sym = s['symbol']
        pnl = s['pnl_pct']
        ts = s['time']
        exit_reason = "P1 take-profit (SELL_ALL)" if pnl > 0 else "止损 (stop-loss SELL_ALL)"

        # Get buy price from trade history
        bp_data = buy_prices.get(sym, None)
        if bp_data:
            buy_price = bp_data['price']
            sell_price = buy_price * (1 + pnl / 100)
        else:
            print(f"  ⚠️ {sym} @ {ts}: 无买入价格记录，跳过")
            continue

        qty = bp_data['qty'] if bp_data else 1

        # Build sell_info and buy_info dicts for analyze_exit
        sell_info = {
            'symbol': sym,
            'time': ts,
            'price': str(sell_price),
            'qty': str(qty),
            'reason': exit_reason
        }
        buy_info = {
            'symbol': sym,
            'time': ts,
            'price': str(buy_price),
            'qty': str(qty),
            'reason': '评分自动执行'
        }

        try:
            analysis = analyze_exit(sell_info, buy_info)
            entry = record_trade_experience(analysis)
            if entry:
                print(f"  ✅ {sym} @ {ts}: PnL={pnl:+.2f}% 质量={analysis['exit_quality']} 信号={analysis.get('trigger_signals', [])}")
                results.append(analysis)
            else:
                print(f"  ⏭️ {sym} @ {ts}: 已存在（去重跳过）")
        except Exception as e:
            print(f"  ❌ {sym} @ {ts}: {e}")

    # Summary
    master = load_master()
    stats = master.get('stats', {})
    print(f"\n=== 经验档案更新完毕 ===")
    print(f"总分析交易: {stats.get('total_trades_analyzed', 0)}")
    print(f"正确退出: {stats.get('correct_exits', 0)}")
    print(f"错误退出: {stats.get('wrong_exits', 0)}")
    print(f"过早退出: {stats.get('too_early_exits', 0)}")
    if results:
        print(f"\n本批记录:")
        for r in results:
            sigs = ','.join(r.get('trigger_signals', []))
            print(f"  {r['symbol']}: {r['pnl_pct']:+.1f}% | {r['exit_quality']} | 信号={sigs}")
    print(f"last_updated: {master.get('last_updated', '?')}")

if __name__ == '__main__':
    main()
