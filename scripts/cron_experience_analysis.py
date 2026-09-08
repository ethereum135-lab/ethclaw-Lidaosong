#!/usr/bin/env python3
"""
cron_experience_analysis.py — 定时经验分析
每轮cron运行：检查最新卖出并更新经验档案
"""
import sys
import os
import re
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, 'tools'))
os.chdir(BASE)

from trade_experience import get_last_exit, analyze_exit, record_trade_experience, show_master, generate_daily_summary, load_master

TRADES_MD = os.path.join(BASE, 'audit', 'TRADES.md')
EXPERIENCE_DIR = os.path.join(BASE, 'data', 'experience', 'trades')
DAILY_DIR = os.path.join(BASE, 'data', 'experience', 'daily')

def parse_new_format_sells():
    """解析新格式(SELL_ALL汇总)中是否包含未分析记录"""
    with open(TRADES_MD) as f:
        lines = f.readlines()

    new_sells = []
    for i, line in enumerate(lines):
        stripped = line.replace('**', '').replace('`', '').strip()
        if 'SELL_ALL' in stripped and 'PnL' in stripped:
            m = re.search(r'(\w+)\s+SELL_ALL\s*\(PnL=([+-]?[\d.]+)%\)', stripped)
            if m:
                sym = m.group(1)
                pnl = float(m.group(2))
                # Get timestamp from nearest section header (gap can be 6-8 lines)
                ts = 'unknown'
                for j in range(max(0, i-12), i):
                    h = re.match(r'^#+?\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})', lines[j])
                    if h:
                        ts = h.group(1)
                        break
                new_sells.append({'symbol': sym, 'pnl': pnl, 'time': ts, 'line': i+1})
    
    return new_sells

def check_unanalyzed_sells(new_sells):
    """检查新格式记录是否已被分析"""
    if not os.path.isdir(EXPERIENCE_DIR):
        return new_sells
    
    existing = os.listdir(EXPERIENCE_DIR)
    unanalyzed = []
    for ns in new_sells:
        ts_clean = ns['time'].replace(' ', '_').replace(':', '-') if ns['time'] != 'unknown' else 'unknown'
        matched = any(ns['symbol'] in ef and ts_clean[:10] in ef for ef in existing)
        if not matched:
            unanalyzed.append(ns)
    return unanalyzed

def main():
    print(f"【经验分析】{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Step 1: 管道格式解析
    result = get_last_exit()
    new_entry = False

    if result and result['sell']:
        sell = result['sell']
        buy = result['buy']
        print(f"📄 最新管道格式卖出: {sell['symbol']} @ {sell['price']} ({sell['time']})")
        
        if buy:
            analysis = analyze_exit(sell, buy)
            entry = record_trade_experience(analysis)
            if entry:
                new_entry = True
                print(f"  ✅ 经验已记录: P&L:{analysis['pnl_pct']:+.1f}% 质量:{analysis['exit_quality']}")
            else:
                print(f"  ⏭️  已存在(跳过)")
        else:
            print(f"  ⚠️  未找到买入记录")
    else:
        print("📄 管道格式: 无可解析的新SELL记录")

    # Step 2: 新格式检查
    print()
    new_sells = parse_new_format_sells()
    unanalyzed = check_unanalyzed_sells(new_sells)
    
    if unanalyzed:
        print(f"⚠️  新格式未分析记录 ({len(unanalyzed)}笔):")
        for ns in unanalyzed:
            print(f"  ❌ {ns['symbol']:6s} PnL={ns['pnl']:+.1f}% @ {ns['time']} (行{ns['line']})")
    else:
        print("✅ 新格式: 全部已分析")

    # Step 3: 每日汇总
    today = datetime.now().strftime('%Y-%m-%d')
    summary = generate_daily_summary(today)
    print(f"\n📊 今日汇总 ({today})")
    print(summary)

    # Step 4: 总档案快照
    master = load_master()
    stats = master.get('stats', {})
    total = stats.get('total_trades_analyzed', 0)
    correct = stats.get('correct_exits', 0)
    wrong = stats.get('wrong_exits', 0)
    neutral = stats.get('too_early_exits', 0)
    rate = (correct / total * 100) if total > 0 else 0
    
    print(f"\n📈 总档案: {total}笔 | 正确{correct}({rate:.1f}%) | 错误{wrong} | 中性{neutral}")
    
    # Step 5: 关键信号表现
    signals = master.get('exit_signal_performance', {})
    notable = {k: v for k, v in signals.items() if v.get('total', 0) >= 5}
    if notable:
        print("\n🔑 主力信号表现:")
        for sig in sorted(notable, key=lambda s: -notable[s]['total']):
            p = notable[sig]
            r = p['correct'] / p['total'] * 100 if p['total'] > 0 else 0
            bar = '█' * int(r / 5) + '░' * (20 - int(r / 5))
            print(f"  {sig:20s} {p['total']:4d}次 | 正确率{r:5.1f}% |{bar}")

if __name__ == '__main__':
    main()
