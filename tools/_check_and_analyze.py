#!/usr/bin/env python3
"""检查最近所有卖出是否都已被分析"""
import sys, os, json
sys.path.insert(0, 'tools')
from trade_experience import get_last_exit, analyze_exit, record_trade_experience, extract_trade_info

TRADES_DIR = 'data/experience/trades'
TRADE_LOG = 'audit/TRADES.md'

# 读取所有卖出记录
with open(TRADE_LOG) as f:
    lines = f.readlines()

sells = []
for line in lines:
    stripped = line.replace('**', '').replace('🔴 ', '').replace('🔴', ' ').replace('🟢 ', '').replace('🟢', ' ').replace('⚠️', '')
    parts_check = [p.strip() for p in stripped.split('|')]
    has_sell = 'SELL' in parts_check
    if has_sell and 'NO TRADE' not in stripped:
        info = extract_trade_info(line)
        if info and info.get('symbol') and info.get('price', '').replace('.', '').replace('-', '').strip():
            sells.append(info)

print(f"共找到 {len(sells)} 笔卖出交易")

# 检查哪些已经有经验文件
already_analyzed = set()
if os.path.isdir(TRADES_DIR):
    for fname in os.listdir(TRADES_DIR):
        if fname.endswith('.json'):
            try:
                with open(os.path.join(TRADES_DIR, fname)) as f:
                    entry = json.load(f)
                    sym = entry.get('analysis', {}).get('symbol', '')
                    ts = entry.get('analysis', {}).get('sell_time', '')
                    if sym and ts:
                        already_analyzed.add(f"{sym}|{ts}")
            except:
                pass

print(f"已有经验记录: {len(already_analyzed)} 条")

unanalyzed = []
for s in sells:
    key = f"{s['symbol']}|{s['time']}"
    if key not in already_analyzed:
        unanalyzed.append(s)

if unanalyzed:
    print(f"\n未分析卖出: {len(unanalyzed)} 笔")
    for s in unanalyzed:
        print(f"  {s['symbol']} @ {s['time']} price={s['price']} reason={s['reason']}")
        
        # 找对应买入
        buy_info = None
        for line in lines:
            stripped = line.replace('**', '').replace('🔴 ', '').replace('🔴', ' ').replace('🟢 ', '').replace('🟢', ' ').replace('⚠️', '')
            parts_check = [p.strip() for p in stripped.split('|')]
            has_buy = 'BUY' in parts_check
            if has_buy and 'NO TRADE' not in stripped:
                info = extract_trade_info(line)
                if info and info['symbol'] == s['symbol'] and info['time'] < s['time']:
                    buy_info = info
        if buy_info:
            analysis = analyze_exit(s, buy_info)
            entry = record_trade_experience(analysis)
            if entry:
                print(f"    -> 分析完成: P&L:{analysis['pnl_pct']:+.1f}% 质量:{analysis['exit_quality']} 信号:{analysis['trigger_signals']}")
            else:
                print(f"    -> 已分析过(去重)")
        else:
            print(f"    -> 未找到买入记录")
else:
    print(f"\n所有 {len(sells)} 笔卖出均已分析完毕!")
