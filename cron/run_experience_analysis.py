#!/usr/bin/env python3
"""
分析TRADES.md中最新的pipe-delimited卖出交易并更新总经验档案。
正确识别：
- pipe-delimited格式（| time | SELL | sym | qty | price | reason |）的实际卖出
- 忽略评估段中的 SELL_ALL 信号重评（非实际卖出）

用法：python3 cron/run_experience_analysis.py
"""
import sys
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, 'tools'))
os.chdir(BASE)

from trade_experience import *

def main():
    result = get_last_exit()
    if not result or not result.get('sell'):
        print("[SILENT]")
        return

    sell = result['sell']
    buy = result['buy']
    symbol = sell.get('symbol', '?')
    sell_time = sell.get('time', '?')

    # Dedup: skip if already analyzed
    ts = sell_time.replace(' ', '_').replace(':', '-')
    trade_file = os.path.join(TRADES_DIR, f"{ts}_{symbol}.json")
    if os.path.exists(trade_file):
        # Also check if the SELL line itself is a re-evaluation
        # (occurs when the parser finds signal-section entries that happen to parse)
        print("[SILENT]")
        return

    # Only process pipe-delimited format sells with proper time/price/reason
    if not sell.get('reason') or sell['reason'] in ('', '?'):
        print("[SILENT]")
        return

    analysis = analyze_exit(sell, buy)
    record_trade_experience(analysis)

    pnl = analysis.get('pnl_pct', 0)
    quality = analysis.get('exit_quality', 'unknown')
    signals = analysis.get('trigger_signals', [])
    lesson = analysis.get('lesson', '')

    print(f"## 经验分析完成: {symbol}")
    print(f"- 时间: {sell_time}")
    print(f"- 盈亏: {pnl:+.1f}%")
    print(f"- 质量评估: {quality}")
    print(f"- 触发信号: {', '.join(signals) if signals else '无'}")
    print(f"- 经验: {lesson}")

    print("\n--- 更新后总档案 ---")
    print(show_master())

if __name__ == '__main__':
    main()
