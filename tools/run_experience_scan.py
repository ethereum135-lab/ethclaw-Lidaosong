#!/usr/bin/env python3
"""Scan new unanalyzed sells and update experience archive."""
import sys, os, json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, 'tools'))

from trade_experience import get_last_exit, analyze_exit, record_trade_experience, load_master, extract_trade_info

TRADES_DIR = os.path.join(BASE_DIR, 'data', 'experience', 'trades')
TRADE_LOG = os.path.join(BASE_DIR, 'audit', 'TRADES.md')

os.makedirs(TRADES_DIR, exist_ok=True)

def show_master():
    master = load_master()
    lines = ["\n=== 总经验档案 ==="]
    s = master.get('stats', {})
    lines.append(f"分析交易数: {s.get('total_trades_analyzed', 0)}")
    lines.append(f"正确退出: {s.get('correct_exits', 0)}")
    lines.append(f"错误退出: {s.get('wrong_exits', 0)}")
    lines.append(f"中性退出: {s.get('too_early_exits', 0)}")
    lines.append("")
    lines.append("--- 信号表现 ---")
    for sig, perf in sorted(master.get('exit_signal_performance', {}).items()):
        rate = perf['correct'] / perf['total'] * 100 if perf['total'] > 0 else 0
        lines.append(f"  {sig}: {perf['total']}次触发, 正确率{rate:.0f}%")
    lines.append("")
    lines.append("--- 最新经验规则 ---")
    for rule in master.get('rules', [])[-5:]:
        lines.append(f"  信号{rule['signal']} + {rule.get('condition','')} = {rule.get('effectiveness','')}")
    return '\n'.join(lines)

def clean_line(line):
    s = line.replace('**', '')
    for em in ['\U0001f534 ', '\U0001f534', '\U0001f7e2 ', '\U0001f7e2', '\u26a0\ufe0f']:
        s = s.replace(em, ' ')
    return s

# List already analyzed
analyzed = sorted(os.listdir(TRADES_DIR)) if os.path.exists(TRADES_DIR) else []
print(f"已分析交易总数: {len(analyzed)}")

# Scan recent sells for unanalyzed ones
with open(TRADE_LOG) as f:
    lines = f.readlines()

pending = []
for line in reversed(lines):
    stripped = clean_line(line)
    # Strict match: 'SELL' must be a standalone action field (not part of 'SELL_GENIUS+BUY_ZEC')
    pipe_parts = stripped.split('|')
    sell_action = False
    for pp in pipe_parts:
        if pp.strip() == 'SELL':
            sell_action = True
            break
    if not sell_action:
        continue
    if 'NO TRADE' in stripped:
        continue
    info = extract_trade_info(line)
    if info and info.get('symbol') and info.get('price', '').replace('.', '').replace('-', '').strip():
            ts = info['time'].replace(' ', '_').replace(':', '-')
            fname = f"{ts}_{info['symbol']}.json"
            fpath = os.path.join(TRADES_DIR, fname)
            if not os.path.exists(fpath):
                pending.append({'info': info, 'fname': fname})
            else:
                # Already analyzed, may want to still show in summary
                pass

print(f"待分析新卖出: {len(pending)}")
if pending:
    for p in pending[:10]:
        info = p['info']
        print(f"  {info['symbol']:8s} {info['time']:22s} ${info['price']:10s} {info['reason'][:40]:40s}")

# Process each pending sell
added = 0
for p in pending:
    sell = p['info']
    print(f"\n--- 分析: {sell['symbol']} @ {sell['time']} ---")

    # Find corresponding buy
    buys = []
    for line in lines:
        stripped = clean_line(line)
        if 'BUY' in stripped and 'NO TRADE' not in stripped:
            info_b = extract_trade_info(line)
            if info_b and info_b['symbol'] == sell['symbol'] and info_b['time'] < sell['time']:
                buys.append(info_b)

    buy = max(buys, key=lambda x: x['time']) if buys else None
    if buy:
        print(f"  买入: {buy['time']} $ {buy['price']} x {buy['qty']}")
    else:
        print(f"  WARNING: 未找到对应买入记录")

    analysis = analyze_exit(sell, buy)
    entry = record_trade_experience(analysis)

    if entry:
        added += 1
        print(f"  >> P&L: {analysis['pnl_pct']:+.2f}% | ${analysis['pnl_usd']:+.2f}")
        print(f"  质量: {analysis['exit_quality']}")
        print(f"  信号: {analysis['trigger_signals']}")
        print(f"  经验: {analysis['lesson']}")
    else:
        print(f"  >> 已存在(跳过)")

if not pending and not added:
    print("无新卖出需要分析。")

print(show_master())
print(f"\n本轮: 发现{len(pending)}笔待分析, 新增{added}条经验")
