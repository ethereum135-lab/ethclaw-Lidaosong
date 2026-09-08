#!/usr/bin/env python3
"""
batch-analyze-sells.py — Catch up all unanalyzed sell trades
============================================================

The standard analyze-latest-sell.py only processes the most recent sell.
When cron misses runs or the tool was newly deployed, sells accumulate
unanalyzed in TRADES.md. This script scans ALL sells and processes any
that don't yet have a file in data/experience/trades/{ts}_{symbol}.json.

Usage (from project root):
  python3 tools/batch-analyze-sells.py         # process unanalyzed sells
  python3 tools/batch-analyze-sells.py --check  # verify coverage only (no writes)

Output (--check):
  Coverage summary: total sells, analyzed count, gaps, master snapshot

Output (normal):
  Progress lines for each newly analyzed trade
  Summary stats at the end
  Errors listed separately (malformed lines, missing buy matches)

Tirith-safe: no emoji/Unicode in output, all .format() strings.
"""

import sys
import os
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, SCRIPT_DIR)
sys.path.insert(0, PROJECT_ROOT)

from trade_experience import extract_trade_info, analyze_exit, record_trade_experience

TRADES_FILE = os.path.join(PROJECT_ROOT, 'audit', 'TRADES.md')
TRADES_DIR = os.path.join(PROJECT_ROOT, 'data', 'experience', 'trades')
MASTER_FILE = os.path.join(PROJECT_ROOT, 'data', 'experience', 'MASTER_EXPERIENCE.json')


def load_analyzed_keys():
    """Build a set of (timestamp, symbol) for already-analyzed trades."""
    if not os.path.isdir(TRADES_DIR):
        return set()
    keys = set()
    for fname in os.listdir(TRADES_DIR):
        if not fname.endswith('.json'):
            continue
        parts = fname.replace('.json', '').split('_', 2)
        if len(parts) >= 3:
            ts = parts[0] + ' ' + parts[1].replace('-', ':')
            sym = parts[2]
            keys.add((ts, sym))
    return keys


def clean_line(line):
    """Remove orphan leading pipes from TRADES.md lines."""
    raw = line.strip()
    while raw.startswith('|'):
        raw = raw[1:].strip()
    return '| ' + raw


def find_matching_buy(symbol, sell_time, all_buys):
    """Find the most recent buy of symbol before sell_time."""
    candidates = [b for b in all_buys if b['symbol'] == symbol and b['time'] < sell_time]
    if not candidates:
        return None
    return candidates[-1]


def is_valid_sell_entry(info):
    """Check if a parsed sell row looks like a real trade (not a parsing artifact)."""
    sym = info.get('symbol', '')
    if not sym or not sym.isalpha() or not sym.isupper():
        return False
    try:
        float(info.get('price', '').replace('$', '').replace('~', '').strip())
        return True
    except (ValueError, TypeError):
        return False


def run_check():
    """Print a comprehensive coverage status report without writing anything."""
    if not os.path.exists(TRADES_FILE):
        print("ERROR: TRADES.md not found at {path}".format(path=TRADES_FILE))
        return

    analyzed_keys = load_analyzed_keys()

    with open(TRADES_FILE) as f:
        raw_lines = f.readlines()

    all_buys = []
    all_sells_raw = []
    total_sells = 0
    valid_sells = 0
    invalid_sells = 0

    for line in raw_lines:
        info = extract_trade_info(clean_line(line))
        if not info:
            continue
        action = info.get('action', '')
        if action == 'SELL' and 'NO TRADE' not in line:
            total_sells += 1
            if is_valid_sell_entry(info):
                valid_sells += 1
                key = (info['time'], info['symbol'])
                all_sells_raw.append((key, info))
            else:
                invalid_sells += 1
        elif action == 'BUY' and 'NO TRADE' not in line:
            all_buys.append(info)

    unanalyzed = []
    for key, info in all_sells_raw:
        if key not in analyzed_keys:
            buy = find_matching_buy(info['symbol'], info['time'], all_buys)
            unanalyzed.append((info, buy))

    print("=== TRADE EXPERIENCE COVERAGE ===")
    print("  TRADES.md lines:       {n}".format(n=len(raw_lines)))
    print("  Total SELL rows:       {n}".format(n=total_sells))
    print("  Valid sell entries:    {n}".format(n=valid_sells))
    print("  Invalid/noise rows:    {n}".format(n=invalid_sells))
    print("  Analyzed (keys):       {n}".format(n=len(analyzed_keys)))

    if unanalyzed:
        print("  UNANALYZED GAPS:       {n}".format(n=len(unanalyzed)))
        for info, buy in unanalyzed[:10]:
            status = "NO_BUY" if not buy else "has buy"
            line_out = "    {time} {sym:8s} @ {price}  {reason}  [{status}]"
            print(line_out.format(
                time=info['time'][:16], sym=info['symbol'],
                price=info['price'], reason=info.get('reason', '?'),
                status=status))
        if len(unanalyzed) > 10:
            print("    ... and {n} more".format(n=len(unanalyzed) - 10))
    else:
        print("  UNANALYZED GAPS:       0")
        print()
        print("  [CLEAN] All {n} valid sells analyzed, zero gaps.".format(n=valid_sells))

    # Master snapshot
    print()
    try:
        with open(MASTER_FILE) as f:
            master = json.load(f)
        stats = master.get('stats', {})
        sig_perf = master.get('exit_signal_performance', {})
        print("=== MASTER EXPERIENCE SNAPSHOT ===")
        print("  Total analyzed:     {n}".format(n=stats.get('total_trades_analyzed', 0)))
        print("  Correct exits:      {n}  ({pct:.1f}%)".format(
            n=stats.get('correct_exits', 0),
            pct=(stats.get('correct_exits', 0) / max(stats.get('total_trades_analyzed', 1), 1)) * 100))
        print("  Wrong exits:        {n}".format(n=stats.get('wrong_exits', 0)))
        print("  Neutral exits:      {n}".format(n=stats.get('too_early_exits', 0)))
        print()
        print("  Signal performance:")
        for sig in sorted(sig_perf.keys()):
            p = sig_perf[sig]
            rate = p['correct'] / p['total'] * 100 if p['total'] > 0 else 0
            line_out = "    {sig:4s}: {n:3d} triggers, correct={c:3d} wrong={w:3d} neutral={m:3d}  [{rate:.0f}%]"
            print(line_out.format(sig=sig, n=p['total'], c=p['correct'],
                                  w=p['wrong'], m=p['neutral'], rate=rate))
        rules = master.get('rules', [])
        if rules:
            print()
            print("  Last 3 verified rules:")
            for r in rules[-3:]:
                print("    [{sig}] {cond} = {eff}".format(
                    sig=r.get('signal', '?'),
                    cond=r.get('condition', '?'),
                    eff=r.get('effectiveness', '?')))
        print()
        print("  Last updated: {ts}".format(ts=master.get('last_updated', '?')))
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print("  MASTER_EXPERIENCE.json: {err}".format(err=e))


def main():
    args = sys.argv[1:]

    if '--check' in args:
        run_check()
        return

    if not os.path.exists(TRADES_FILE):
        print("ERROR: TRADES.md not found at {path}".format(path=TRADES_FILE))
        return

    analyzed = load_analyzed_keys()
    print("MASTER: {n} already analyzed".format(n=len(analyzed)))

    with open(TRADES_FILE) as f:
        raw_lines = f.readlines()

    all_buys = []
    sells = []
    for line in raw_lines:
        info = extract_trade_info(clean_line(line))
        if not info:
            continue
        action = info.get('action', '')
        if action == 'SELL' and 'NO TRADE' not in line:
            key = (info['time'], info['symbol'])
            if key not in analyzed:
                sells.append(info)
        elif action == 'BUY' and 'NO TRADE' not in line:
            all_buys.append(info)

    if not sells:
        print("DONE: No unanalyzed sells found")
        return

    print("UNANALYZED: {n} sells to process".format(n=len(sells)))

    recorded = 0
    skipped = 0
    errors = []

    valid_sells = []
    rejected = 0
    for s in sells:
        if not is_valid_sell_entry(s):
            rejected += 1
            continue
        valid_sells.append(s)

    if rejected:
        print("FILTERED: {n} non-standard entries skipped (bad symbol or price)".format(n=rejected))

    for sell in valid_sells:
        buy = find_matching_buy(sell['symbol'], sell['time'], all_buys)
        if not buy:
            errors.append("{time} {sym}: no matching buy".format(
                time=sell['time'], sym=sell['symbol']))
            continue

        try:
            analysis = analyze_exit(sell, buy)
            entry = record_trade_experience(analysis)
            if entry:
                msg = "  [+] {time} {sym:8s} P&L:{pnl:+.2f}%  {quality}"
                print(msg.format(
                    time=sell['time'][:16], sym=sell['symbol'],
                    pnl=analysis['pnl_pct'], quality=analysis['exit_quality']))
                recorded += 1
            else:
                skipped += 1
        except Exception as e:
            errors.append("{time} {sym}: {err}".format(
                time=sell['time'], sym=sell['symbol'], err=e))

    print()
    summary = "SUMMARY: recorded={rec} skipped={skp} errors={err}"
    print(summary.format(rec=recorded, skp=skipped, err=len(errors)))
    for err in errors:
        print("  ERROR: {err}".format(err=err))


if __name__ == '__main__':
    main()
