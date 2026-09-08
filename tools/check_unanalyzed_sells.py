#!/usr/bin/env python3
"""Check all TRADES.md sources for unanalyzed sells."""
import sys, os, json, re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, 'tools'))

from trade_experience import extract_trade_info, load_master

def strip_emojis(text):
    """Remove emojis and special Unicode that might trip security scans."""
    # Remove all emoji and special marker characters
    emoji_pattern = re.compile(
        "[\U0001F300-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF"
        "\U00002702-\U000027B0\U000024C2-\U0001F251"
        "\U0001F600-\U0001F64F\U0001F680-\U0001F6FF"
        "\U00002600-\U000026FF\U0001F1E0-\U0001F1FF"
        "\U0000FE00-\U0000FE0F"
        "]+",
        flags=re.UNICODE,
    )
    return emoji_pattern.sub('', text)

sources = [
    ('audit/TRADES.md', 'audit/TRADES.md'),
    ('data/TRADES.md', 'data/TRADES.md'),
    ('profiles/a4-blade/data/TRADES.md', 'profiles/a4-blade/data/TRADES.md'),
]

all_unanalyzed = []

for label, rel_path in sources:
    path = os.path.join(BASE, rel_path)
    if not os.path.exists(path):
        continue
    with open(path) as f:
        lines = f.readlines()

    sells = []
    for line in lines:
        stripped = strip_emojis(line).replace('**', '')
        if 'SELL' not in stripped or 'NO TRADE' in stripped or 'SELL SIGNAL' in stripped:
            continue
        parts = [p.strip() for p in stripped.split('|')]
        if 'SELL' not in parts:
            continue
        info = extract_trade_info(line)
        if not info or not info.get('symbol'):
            continue
        p = info.get('price', '').replace('$', '').strip()
        if p in ('0.0000', '0', '0.0', ''):
            continue
        if info.get('is_table_format', False):
            continue
        sells.append(info)

    trades_dir = os.path.join(BASE, 'data', 'experience', 'trades')
    existing = os.listdir(trades_dir) if os.path.isdir(trades_dir) else []
    for s in sells:
        ts = s['time'].replace(' ', '_').replace(':', '-')
        sym = s['symbol']
        found = any(ts in f and sym in f for f in existing)
        if not found:
            all_unanalyzed.append((label, s))

if all_unanalyzed:
    print(f'Found {len(all_unanalyzed)} unanalyzed sells:')
    for label, s in all_unanalyzed:
        reason_preview = s.get('reason', '')[:50]
        print(f'  [{label}] {s["symbol"]} @ {s["time"]} price:{s["price"]} reason:{reason_preview}')
else:
    print('All sells across all TRADES sources are already analyzed.')

master = load_master()
print()
print(f'Master experience: {master["stats"]["total_trades_analyzed"]} trades analyzed')
print(f'  Correct exits: {master["stats"].get("correct_exits", 0)}')
print(f'  Wrong exits:   {master["stats"].get("wrong_exits", 0)}')
print(f'  Neutral exits: {master["stats"].get("too_early_exits", 0)}')

print()
print('--- Signal Performance ---')
for sig, perf in sorted(master.get('exit_signal_performance', {}).items()):
    rate = perf['correct'] / perf['total'] * 100 if perf['total'] > 0 else 0
    print(f'  {sig:20s}: {perf["total"]:4d} triggers, {rate:5.1f}% win rate')
