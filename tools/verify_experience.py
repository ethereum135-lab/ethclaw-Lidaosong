#!/usr/bin/env python3
"""Verify trade experience system status."""
import sys, os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, 'tools'))

from trade_experience import get_last_exit, analyze_exit, show_master as _sm, load_master, extract_trade_info

TRADES_DIR = os.path.join(BASE_DIR, 'data', 'experience', 'trades')
TRADE_LOG = os.path.join(BASE_DIR, 'audit', 'TRADES.md')

def clean_line(line):
    s = line.replace('**', '')
    for em in ['\U0001f534 ', '\U0001f534', '\U0001f7e2 ', '\U0001f7e2', '\u26a0\ufe0f']:
        s = s.replace(em, ' ')
    return s

def main():
    # 1) Latest real sell
    result = get_last_exit()
    if result and result['sell']:
        s = result['sell']
        b = result['buy']
        analysis = analyze_exit(s, b)
        print(f"最新真实卖出: {s['symbol']} @ {s['time']}")
        print(f"  价格:{s['price']} 数量:{s['qty']} 原因:{s['reason']}")
        print(f"  买入价: ${analysis['buy_price']:.6f}")
        print(f"  P&L: {analysis['pnl_pct']:+.2f}% 质量:{analysis['exit_quality']}")
        if b:
            print(f"  买入时间:{b['time']} 买入价:${b['price']} x {b['qty']}")
    else:
        print("无卖出记录")

    # 2) Check for unanalyzed sells (strict mode)
    with open(TRADE_LOG) as f:
        lines = f.readlines()

    pending_real = []
    for line in reversed(lines):
        stripped = clean_line(line)
        parts_check = [p.strip() for p in stripped.split('|')]
        has_sell = 'SELL' in parts_check
        if has_sell and 'NO TRADE' not in stripped:
            info = extract_trade_info(line)
            if info and info.get('symbol') and info.get('price', '').replace('.', '').replace('-', '').strip():
                # Verify this is a real number price
                try:
                    float(info['price'])
                except ValueError:
                    continue
                ts = info['time'].replace(' ', '_').replace(':', '-')
                fname = f"{ts}_{info['symbol']}.json"
                fpath = os.path.join(TRADES_DIR, fname)
                if not os.path.exists(fpath):
                    pending_real.append(info)
                    print(f"未分析: {info['symbol']} {info['time']} ${info['price']}")

    if not pending_real:
        print("\n所有卖出均已分析完毕，无待处理。")

    # 3) Master summary
    print()
    print(_sm())

    # 4) File count
    analyzed = sorted(os.listdir(TRADES_DIR)) if os.path.exists(TRADES_DIR) else []
    print(f"\n总经验文件: {len(analyzed)}")

if __name__ == '__main__':
    main()
