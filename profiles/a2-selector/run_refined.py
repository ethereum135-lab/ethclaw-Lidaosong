#!/usr/bin/env python3
"""
A2 选币官 — 精细化报告生成
考虑市值约束 + 真实数据标注
"""
import json

with open("/Users/lidaosong/zq_web4_trading_system/data/aws_snapshot.json") as f:
    data = json.load(f)

funding_rates = data.get("funding_rates", {})
trending = data.get("coingecko_trending", [])

trending_symbols = set()
for t in trending:
    trending_symbols.add(t["symbol"].upper())

# Known approximate market caps (from CoinGecko, approximate)
KNOWN_MCAPS = {
    "BTC": 1600000000000, "ETH": 280000000000, "BNB": 100000000000,
    "SOL": 42000000000, "XRP": 82000000000, "DOGE": 17000000000,
    "ADA": 10000000000, "TRX": 31000000000, "LINK": 6700000000,
    "AVAX": 4100000000, "SUI": 3600000000, "TON": 5800000000,
    "LTC": 4400000000, "AAVE": 1500000000, "UNI": 2300000000,
    "TAO": 2500000000, "NEAR": 2100000000, "HBAR": 3500000000,
    "ZEC": 900000000, "ATOM": 830000000, "DASH": 550000000,
    "CRV": 350000000, "PENDLE": 600000000, "WLD": 350000000,
    "ONDO": 600000000, "ENA": 220000000, "TIA": 300000000,
    "FET": 600000000, "INJ": 600000000, "PAXG": 500000000,
    "XAUT": 500000000, "CHIP": None, "SAGA": None, "SPK": None,
    "DYM": None, "VIC": None, "COS": None, "SOLV": None,
    "SAHARA": None, "PENGU": None, "KITE": None, "FF": None,
    "TRUMP": 500000000, "UTK": None, "PEPE": 1800000000,
    "LUNC": 600000000
}

def get_mcap_estimate(base_symbol):
    """Get market cap estimate"""
    if base_symbol in KNOWN_MCAPS:
        return KNOWN_MCAPS[base_symbol]
    # Rough guess based on price for unknown coins
    return None

def mcap_ok(base_symbol):
    """Check if $10M <= mcap <= $1B"""
    mcap = get_mcap_estimate(base_symbol)
    if mcap is None:
        return None  # Unknown
    return 10_000_000 <= mcap <= 1_000_000_000

# Process coins
coins = data.get("binance_top50", [])

STABLE_PAIRS = {"RLUSDUSDT", "EURUSDT", "UUSDT"}

def is_stable(symbol):
    return symbol in STABLE_PAIRS or symbol.replace("USDT", "") in {"USDC", "USDT", "BUSD", "DAI", "FDUSD", "TUSD"}

stage1_results = []
for coin in coins:
    symbol = coin["symbol"]
    base = symbol.replace("USDT", "")
    price = float(coin["price"])
    volume = float(coin["volume"])
    change = float(coin["change_pct"])
    fr = float(funding_rates.get(symbol, {}).get("rate", 0)) if symbol in funding_rates else None
    is_trend = base in trending_symbols
    mcap_est = get_mcap_estimate(base)
    mcap_ok_flag = mcap_ok(base)
    
    stage1_results.append({
        "symbol": symbol, "base": base,
        "price": price, "volume": volume,
        "change_pct": change, "funding_rate": fr,
        "is_trending": is_trend,
        "mcap_estimate": mcap_est,
        "mcap_ok": mcap_ok_flag
    })

# Stage 1 filtering
# Exclude stablecoins, obvious large caps, price fails
STABLECOIN_EXCLUDE = {c["symbol"] for c in stage1_results if is_stable(c["symbol"])}
PRICE_FAIL = {c["symbol"] for c in stage1_results if c["price"] <= 0.001}
LARGE_CAP_EXCLUDE = {c["symbol"] for c in stage1_results if c["mcap_ok"] is not None and not c["mcap_ok"] and c["mcap_estimate"] and c["mcap_estimate"] > 1_000_000_000}
FUNDING_FAIL = {c["symbol"] for c in stage1_results if c["funding_rate"] is not None and not (-0.0001 <= c["funding_rate"] <= 0.0002)}

print("=== EXCLUDED ===")
print(f"Stablecoins: {STABLECOIN_EXCLUDE}")
print(f"Price ≤ $0.001: {PRICE_FAIL}")
print(f"Mcap > $1B (large caps): {sorted(LARGE_CAP_EXCLUDE)}")
print(f"Funding out of range: {FUNDING_FAIL}")

for f_sym in FUNDING_FAIL:
    c = next(c for c in stage1_results if c["symbol"] == f_sym)
    print(f"  {f_sym}: FR = {c['funding_rate']:.8f}")

# Eligible for Stage 2
eligible = [c for c in stage1_results 
    if c["symbol"] not in STABLECOIN_EXCLUDE
    and c["symbol"] not in PRICE_FAIL
    and c["symbol"] not in LARGE_CAP_EXCLUDE
    and c["symbol"] not in FUNDING_FAIL]

# Also flag unknown-mcap coins
unknown_mcap = [c for c in eligible if c["mcap_ok"] is None]
known_good_mcap = [c for c in eligible if c["mcap_ok"] is True]
large_cap_but_passed = [c for c in eligible if c["mcap_ok"] is False and c["mcap_estimate"] and c["mcap_estimate"] <= 1_000_000_000]

print(f"\n=== ELIGIBLE for Stage 2: {len(eligible)} ===")
print(f"Known $10M-$1B: {len(known_good_mcap)} coins")
for c in known_good_mcap:
    print(f"  {c['symbol']}: mcap=${c['mcap_estimate']/1e6:.0f}M")
print(f"\nUnknown mcap (no data): {len(unknown_mcap)} coins")
for c in unknown_mcap:
    print(f"  {c['symbol']}: ${c['price']:.6f} | Vol: ${c['volume']:.0f} | Chg: {c['change_pct']:.2f}% | FR: {c['funding_rate']}")

# Stage 2 scoring
def compute_score(c):
    vol = c["volume"]
    chg = c["change_pct"]
    chg_abs = abs(chg)
    fr = c["funding_rate"]
    
    # 1. Volume Anomaly (30%)
    if chg_abs > 10 and vol > 20_000_000:
        v_score = 85  # Major move + high volume
    elif chg_abs > 5 and vol > 10_000_000:
        v_score = 75
    elif chg_abs > 3 and vol > 10_000_000:
        v_score = 65
    elif vol > 30_000_000:
        v_score = 60
    elif vol > 10_000_000:
        v_score = 50
    else:
        v_score = 40
    
    # 2. Momentum (25%)
    if chg > 10:
        m_score = 90  # Explosive
    elif chg > 5:
        m_score = 80
    elif chg > 2:
        m_score = 70
    elif chg > 0:
        m_score = 60
    elif chg > -3:
        m_score = 50  # Sideways/dip
    elif chg > -8:
        m_score = 40  # Weak
    else:
        m_score = 30  # Freefall
    
    # 3. Funding Health (20%)
    if fr is None:
        f_score = 50
    elif -0.00005 <= fr <= 0.0001:
        f_score = 100
    elif -0.0001 <= fr < -0.00005:
        f_score = 85
    elif 0.0001 < fr <= 0.00015:
        f_score = 85
    elif -0.0003 <= fr < -0.0001:
        f_score = 60
    elif 0.00015 < fr <= 0.0003:
        f_score = 50
    elif fr < -0.0003:
        f_score = 30
    else:
        f_score = 20
    
    # 4. RSI Proxy (15%) - using price change as proxy
    if -5 <= chg <= -1:
        r_score = 90  # Best entry: recent dip
    elif -1 < chg <= 2:
        r_score = 80  # Good: neutral
    elif -10 <= chg < -5:
        r_score = 70  # Oversold
    elif -20 <= chg < -10:
        r_score = 50  # Deep oversold (risky)
    elif 2 < chg <= 5:
        r_score = 60  # Rising, some entry missed
    elif 5 < chg <= 10:
        r_score = 40  # Already running
    elif chg > 10:
        r_score = 20  # Fully pumped
    else:
        r_score = 30  # Crashing
    
    # 5. Heat Correction (10%)
    if c["is_trending"]:
        h_score = 30
    else:
        h_score = 70
    
    total = v_score * 0.30 + m_score * 0.25 + f_score * 0.20 + r_score * 0.15 + h_score * 0.10
    return round(total, 1), {
        "vol": round(v_score, 1),
        "mom": round(m_score, 1),
        "fr": round(f_score, 1),
        "rsi": round(r_score, 1),
        "heat": round(h_score, 1)
    }

scored = []
for c in eligible:
    total, breakdown = compute_score(c)
    scored.append({
        "symbol": c["symbol"],
        "base": c["base"],
        "price": c["price"],
        "volume": c["volume"],
        "change_pct": c["change_pct"],
        "funding_rate": c["funding_rate"],
        "is_trending": c["is_trending"],
        "mcap_estimate": c["mcap_estimate"],
        "mcap_ok": c["mcap_ok"],
        "total": total,
        **breakdown
    })

scored.sort(key=lambda x: x["total"], reverse=True)

candidate = [s for s in scored if s["total"] >= 70]
watch = [s for s in scored if 50 <= s["total"] < 70]
excluded_s2 = [s for s in scored if s["total"] < 50]

print(f"\n\n{'='*80}")
print(f"FINAL RESULTS")
print(f"{'='*80}")
print(f"🟢 候选池 (≥70): {len(candidate)}")
for s in candidate:
    print(f"  {s['symbol']}: {s['total']} | Vol:{s['vol']} M:{s['mom']} FR:{s['fr']} RSI:{s['rsi']} H:{s['heat']} | ${s['price']:.4f} | Chg:{s['change_pct']:.2f}% | Vol:${s['volume']:.0f}")

print(f"\n🟡 待观察池 (50-69): {len(watch)}")
for s in watch:
    print(f"  {s['symbol']}: {s['total']:5.1f} | ${s['price']:.4f} | Chg:{s['change_pct']:7.2f}% | Vol:${s['volume']:.0f} | FR:{s['funding_rate']} | Trend:{s['is_trending']} | Mcap:{s['mcap_estimate']}")

print(f"\n🔴 排除 (<50): {len(excluded_s2)}")
for s in excluded_s2:
    print(f"  {s['symbol']}: {s['total']}")

# Save refined data
output = {
    "market_env": {
        "fg_index": data["fg_index"],
        "fg_classification": data["fg_classification"],
        "btc_price": "81298.60",
        "eth_price": "2323.02",
        "btc_dominance": data["global"]["btc_dominance"],
        "total_mcap": data["global"]["total_mcap_usd"]
    },
    "stage1_exclusions": {
        "stablecoins": sorted(list(STABLECOIN_EXCLUDE)),
        "price_fails": sorted(list(PRICE_FAIL)),
        "large_caps": sorted(list(LARGE_CAP_EXCLUDE)),
        "funding_fails": [{"symbol": s, "fr": next(c["funding_rate"] for c in stage1_results if c["symbol"] == s)} for s in sorted(FUNDING_FAIL)]
    },
    "candidate_pool": candidate,
    "watch_pool": watch,
    "excluded_pool": excluded_s2,
    "trending": [{"name": t["name"], "symbol": t["symbol"]} for t in trending]
}

with open("/Users/lidaosong/zq_web4_trading_system/profiles/a2-selector/scored_refined.json", "w") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print("\n✅ Saved refined results")
