#!/usr/bin/env python3
# A8 fund flow report parser - 2026-08-03 02:46 snapshot
import json

snap = json.load(open('data/a8/a8_data_snapshot.json'))
sig = json.load(open('data/signals.json'))

print("=== SNAPSHOT META ===")
print("timestamp:", snap.get('timestamp'))
print("date/time:", snap.get('date'), snap.get('time'))
print("data_quality:", snap.get('data_quality'))
errs = snap.get('errors') or []
print("errors:", len(errs))
for e in errs[:5]:
    print("  -", str(e)[:120])

# buy_signals breakdown
bs = snap.get('buy_signals') or []
types = {}
for s in bs:
    types[s.get('type')] = types.get(s.get('type'), 0) + 1
print("buy_signals types:", types)

# INFLOW
inflows = [s for s in bs if s.get('type') == 'INFLOW']
print("\n=== INFLOW (%d) ===" % len(inflows))
by_sym = {}
for inf in inflows:
    parts = str(inf.get('data', '')).split('|')
    if len(parts) >= 8:
        chain, sym, contract, pool, tvol, price, bs_r, chg = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5], parts[6], parts[7]
    else:
        chain, sym = parts[0], parts[1] if len(parts) > 1 else '?'
        bs_r = chg = '?'
    by_sym.setdefault(sym.upper(), []).append((chain, bs_r, chg, parts))
for sym, lst in sorted(by_sym.items()):
    chains = {}
    for chain, bsr, chg, parts in lst:
        chains.setdefault(chain, []).append((bsr, chg))
    print("  %s: %d inflows | chains=%s" % (sym, len(lst), ",".join(chains.keys())))
    for chain, items in chains.items():
        print("      %s: %s" % (chain, items[:6]))

# MONEY_IN
money_in = [s for s in bs if s.get('type') == 'MONEY_IN']
print("\n=== MONEY_IN (%d) ===" % len(money_in))
usdt = usdc = 0
seen = set()
for m in money_in:
    data = str(m.get('data', ''))
    if data in seen:
        continue
    seen.add(data)
    parts = data.split('|')
    if len(parts) >= 3:
        cur = parts[1]
        try:
            amt = float(parts[2])
        except ValueError:
            amt = 0
        if cur == 'USDT':
            usdt += amt
        elif cur == 'USDC':
            usdc += amt
        print("  %s" % data[:80])
print("MONEY_IN deduped: USDT %.0f + USDC %.0f = %.0f (raw=%d, deduped=%d)" % (usdt, usdc, usdt+usdc, len(money_in), len(seen)))

# SUMMARY
summ = [s for s in bs if s.get('type') == 'SUMMARY']
print("\n=== SUMMARY ===")
for s in summ:
    print(" ", str(s.get('data'))[:200])

# whale_signals
ws = snap.get('whale_signals') or []
wtypes = {}
for w in ws:
    wtypes[w.get('type')] = wtypes.get(w.get('type'), 0) + 1
print("\n=== whale_signals types:", wtypes)

# TOKEN entries (CEX inflows) - robust parsing
print("\n=== TOKEN CEX flows ===")
token_in = {}
for w in ws:
    if w.get('type') != 'TOKEN':
        continue
    data = w.get('data')
    if isinstance(data, dict):
        note = str(data.get('symbol') or data.get('token') or data.get('note') or '')
        src = str(data.get('source') or '')
        direction = str(data.get('direction') or '')
        amt = str(data.get('amount') or '')
    else:
        parts = str(data).split('|')
        if len(parts) >= 4:
            src, direction, amt, note = parts[0], parts[1], parts[2], parts[3]
        else:
            continue
    # fake coin filter
    nl = note.lower()
    if any(kw in nl for kw in ['visit', 'claim', 'rewards', 'website', '.org', '.com']):
        print("  [fake-coin filtered] %s|%s|%s|%s" % (src, direction, amt, note[:40]))
        continue
    if direction == 'in':
        token_in.setdefault(note.upper(), []).append((src, amt))
for sym, lst in sorted(token_in.items()):
    print("  %s: %s" % (sym, lst[:6]))

# WALLET ETH flows
print("\n=== WALLET ETH net ===")
net = {}
for w in ws:
    if w.get('type') != 'WALLET':
        continue
    data = w.get('data')
    if isinstance(data, dict):
        continue
    parts = str(data).split('|')
    if len(parts) < 4 or parts[3] != 'ETH':
        continue
    name, direction, amt = parts[0], parts[1], parts[2]
    try:
        a = float(amt)
    except ValueError:
        continue
    key = name
    net[key] = net.get(key, 0) + (a if direction == 'in' else -a)
for k, v in sorted(net.items()):
    print("  {}: {:+,.0f} ETH".format(k, v))
print("  Total: {:+,.0f} ETH".format(sum(net.values())))

# USDT_TX fallback
print("\n=== USDT_TX / others sample ===")
shown = 0
for w in ws:
    if w.get('type') in ('USDT_TX', 'ETH_GAS'):
        d = w.get('data')
        if isinstance(d, dict):
            d = str(d)[:100]
        print("  %s: %s" % (w.get('type'), str(d)[:100]))
        shown += 1
        if shown > 8:
            break

# dune_whale
dw = snap.get('dune_whale') or []
print("\n=== dune_whale (%d) ===" % len(dw))
dw_types = {}
for d in dw:
    dw_types[d.get('type')] = dw_types.get(d.get('type'), 0) + 1
print("  types:", dw_types)
# USDC whale totals
usdc_tot = 0
usdc_n = 0
cumberland = 0
usdt_tot = 0
usdt_n = 0
eth_tot = 0
eth_n = 0
seen_dw = set()
for d in dw:
    data = str(d.get('data', ''))
    if data in seen_dw:
        continue
    seen_dw.add(data)
    t = d.get('type', '')
    parts = data.split('|')
    try:
        amt = float(parts[0]) if parts else 0
    except ValueError:
        amt = 0
    if t == 'USDC>$500K':
        usdc_tot += amt
        usdc_n += 1
        frm = parts[2] if len(parts) > 2 else ''
        to = parts[3] if len(parts) > 3 else ''
        if '0xbbbbbbbbbb' in frm or '0xbbbbbbbbbb' in to:
            cumberland += amt
    elif t == 'USDT>$500K':
        usdt_tot += amt
        usdt_n += 1
    elif t == 'ETH>100':
        eth_tot += amt
        eth_n += 1
print("  USDC>$500K: %d笔 $%.2fM (Cumberland %.2fM, %.0f%%)" % (usdc_n, usdc_tot/1e6, cumberland/1e6, 100*cumberland/usdc_tot if usdc_tot else 0))
print("  USDT>$500K: %d笔 $%.2fM" % (usdt_n, usdt_tot/1e6))
print("  ETH>100: %d笔 %.0f ETH" % (eth_n, eth_tot))

# ===== signals.json =====
print("\n=== SIGNALS ===")
print("scanned_at:", sig.get('scanned_at'))
print("summary:", json.dumps(sig.get('summary', {}))[:300])
if 'signals' in sig:
    arr, lv = sig['signals'], 'signal_type'
    print("path: signals[] / signal_type")
else:
    arr, lv = sig.get('results', []), 'level'
    print("path: results[] / level")

strong = [r for r in arr if r.get(lv) == 'STRONG']
signal = [r for r in arr if r.get(lv) == 'SIGNAL']
print("STRONG: %d, SIGNAL: %d" % (len(strong), len(signal)))

strong_syms = [r.get('symbol') for r in strong]
signal_syms = [r.get('symbol') for r in signal]

# enrich check
enrich_a8 = [r.get('symbol') for r in strong if 'A8' in (r.get('_enrich_sources') or []) or any('A8' in str(x) for x in (r.get('_enrich_sources') or []))]
print("STRONG with A8 enrich:", enrich_a8)

# ===== CROSSREF =====
print("\n=== T0: STRONG + INFLOW ===")
t0 = []
for sym in strong_syms:
    if sym.upper() in by_sym:
        t0.append(sym)
        lst = by_sym[sym.upper()]
        chains = set(x[0] for x in lst)
        bsrs = set(x[1] for x in lst)
        print("  %s: %d INFLOWs | chains=%s | B/S=%s" % (sym, len(lst), ",".join(sorted(chains)), ",".join(sorted(bsrs))))
if not t0:
    print("  (no INFLOW direct matches)")

# T0 channel B/C: whale TOKEN CEX inflow
print("\n=== T0: STRONG + CEX TOKEN inflow ===")
for sym in strong_syms:
    if sym.upper() in token_in:
        print("  %s: CEX inflows %s" % (sym, token_in[sym.upper()][:4]))

# T0 dex_smallcaps
print("\n=== T0: STRONG + dex buy_sell>1.0 ===")
dex = snap.get('dex_smallcaps') or []
for p in dex:
    s = str(p.get('symbol', '')).upper()
    if s in [x.upper() for x in strong_syms]:
        try:
            bsr = float(p.get('buy_sell_ratio', 0))
        except ValueError:
            bsr = 0
        if bsr > 1.0:
            print("  %s: %s b/s=%sx chg=%s%% vol=%s" % (s, p.get('chain'), p.get('buy_sell_ratio'), p.get('change_24h'), p.get('volume_24h')))

print("\n=== T1: SIGNAL + INFLOW ===")
t1 = []
for sym in signal_syms:
    if sym.upper() in by_sym:
        t1.append(sym)
        lst = by_sym[sym.upper()]
        chains = set(x[0] for x in lst)
        print("  %s: %d INFLOWs | chains=%s" % (sym, len(lst), ",".join(sorted(chains))))
if not t1:
    print("  (no matches)")

print("\n=== T2: INFLOW-only coins (not in STRONG/SIGNAL) ===")
all_ss = set([x.upper() for x in strong_syms + signal_syms])
for sym, lst in sorted(by_sym.items()):
    if sym not in all_ss:
        chains = set(x[0] for x in lst)
        bsrs = set(x[1] for x in lst)
        print("  %s: %d INFLOWs | chains=%s | B/S=%s" % (sym, len(lst), ",".join(sorted(chains)), ",".join(sorted(bsrs))))

print("\n=== STRONG top10 ===")
for r in sorted(strong, key=lambda x: x.get('total_score', 0), reverse=True)[:10]:
    print("  %s (%s分, %+.1f%%)" % (r.get('symbol'), r.get('total_score'), r.get('gain_24h', 0)))
