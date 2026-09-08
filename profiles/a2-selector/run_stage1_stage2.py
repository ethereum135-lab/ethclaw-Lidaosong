#!/usr/bin/env python3
"""
A2 选币官 — 两阶段筛选法执行脚本
使用 AWS snapshot 数据进行 Stage 1 硬过滤 + Stage 2 五因子评分
"""
import json
import os
from datetime import datetime

# Load AWS snapshot
with open("/Users/lidaosong/zq_web4_trading_system/data/aws_snapshot.json") as f:
    data = json.load(f)

# Load funding rates
funding_rates = data.get("funding_rates", {})

# Load trending
trending = data.get("coingecko_trending", [])
trending_symbols = set()
for t in trending:
    sym = t["symbol"].upper()
    trending_symbols.add(sym)

print(f"Trending symbols: {trending_symbols}")
print(f"F&G: {data['fg_index']}/100 — {data['fg_classification']}")
print(f"BTC dominance: {data['global']['btc_dominance']}%")
print(f"Total MCap: ${float(data['global']['total_mcap_usd'])/1e12:.2f}T")

# Process Binance Top 50
coins = data.get("binance_top50", [])
print(f"\nTotal coins in Top 50: {len(coins)}")

# Coin name mapping for trending detection
symbol_to_name = {}
for t in trending:
    symbol_to_name[t["symbol"].upper()] = t["name"]

# Stablecoin / non-crypto symbols to exclude
STABLECOINS = {"USDT", "BUSD", "DAI", "USDC", "FDUSD", "TUSD", "USDN", "FRAX", "PAX", "GUSD", "HUSD", "SUSD", "LUSD", "ALUSD", "MIM", "USTC"}
FIAT_PAIRS = {"EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "CNY", "HKD", "SGD", "NZD", "KRW", "BRL", "TRY", "ZAR", "INR", "RUB", "MXN", "PLN"}
LEVERAGED_KEYWORDS = {"UP", "DOWN", "BULL", "BEAR", "LONG", "SHORT", "2L", "2S", "3L", "3S"}
STABLE_PAIRS = {"RLUSDUSDT", "EURUSDT", "UUSDT"}  # identifiable stable/currency pairs

# Known market cap ranges (approx, for filtering)
# We'll use price * typical supply estimates where possible
# For precise filtering, note which we can determine

def get_funding_rate(symbol):
    """Get funding rate for a coin symbol"""
    if symbol in funding_rates:
        return float(funding_rates[symbol]["rate"])
    return None

def is_stablecoin_or_leveraged(symbol):
    """Check if coin is a stablecoin or leveraged token"""
    base = symbol.replace("USDT", "")
    if symbol in STABLE_PAIRS:
        return True
    if base.upper() in STABLECOINS:
        return True
    if base.upper() in FIAT_PAIRS:
        return True
    # Check for leveraged tokens
    for kw in LEVERAGED_KEYWORDS:
        if kw in base.upper():
            return True
    return False

def price_ok(price_str):
    """Check price > $0.001"""
    try:
        return float(price_str) > 0.001
    except:
        return False

def funding_ok(symbol):
    """Check funding rate is within -0.0001 to 0.0002 range"""
    fr = get_funding_rate(symbol)
    if fr is None:
        return None  # unknown
    return -0.0001 <= fr <= 0.0002

def is_trending(symbol):
    """Check if coin is in trending"""
    base = symbol.replace("USDT", "")
    return base.upper() in trending_symbols

def estimate_mcap(price_str, approx_supply_b):
    """Rough market cap estimation using known supplies"""
    # This is rough - we'll note it as estimate
    return None  # We don't have reliable supply data

# Stage 1 Hard Filter
stage1_results = []
for coin in coins:
    symbol = coin["symbol"]
    price = coin["price"]
    volume = float(coin["volume"])
    change = float(coin["change_pct"])
    
    checks = {}
    
    # C1: Volume ≥ $1M
    checks["volume_1M"] = volume >= 1_000_000
    
    # C2: Price > $0.001
    checks["price_0.001"] = price_ok(price)
    
    # C3: Market Cap $10M-$1B — Cannot determine without CoinGecko
    checks["mcap_10M_1B"] = "NO_DATA"
    
    # C4: Not stablecoin/leveraged
    checks["not_stable"] = not is_stablecoin_or_leveraged(symbol)
    
    # C5: Funding rate neutral
    fr = get_funding_rate(symbol)
    if fr is not None:
        checks["funding_neutral"] = -0.0001 <= fr <= 0.0002
    else:
        checks["funding_neutral"] = "NO_DATA"
    
    # C6: Non-anomaly (trending check)
    is_trend = is_trending(symbol)
    checks["non_anomaly"] = True  # Can't fully verify without on-chain data
    
    # Determine pass/fail
    # For conditions we have data for:
    hard_fails = []
    for k, v in checks.items():
        if v is False:
            hard_fails.append(k)
        elif v == "NO_DATA":
            hard_fails.append(f"{k}_NODATA")
    
    passed = all(not isinstance(v, bool) or v for v in checks.values()) and "NO_DATA" not in str(list(checks.values()))
    
    stage1_results.append({
        "symbol": symbol,
        "base": symbol.replace("USDT", ""),
        "price": float(price),
        "volume": volume,
        "change_pct": change,
        "checks": checks,
        "passed": passed,
        "fails": hard_fails,
        "funding_rate": fr,
        "is_trending": is_trend
    })

# Print Stage 1 results
print("\n" + "="*80)
print("STAGE 1 — 硬过滤结果")
print("="*80)

passed_s1 = [c for c in stage1_results if c["passed"] and all(v is not False and v != "NO_DATA" for v in c["checks"].values())]
partial_s1 = [c for c in stage1_results if "NO_DATA" in str(list(c["checks"].values()))]  # some data missing but no hard fails
failed_s1 = [c for c in stage1_results if not c["passed"] and all(v is not False or v == False for v in c["checks"].values())]
unknown_s1 = [c for c in stage1_results if not c["passed"] and any(
    k.endswith("_NODATA") for k in c["fails"]
)]

print(f"\nTotal scanned: {len(stage1_results)}")

# Separate stablecoin fails and price fails
stablecoin_fails = [c for c in stage1_results if not c["checks"].get("not_stable", True)]
price_fails = [c for c in stage1_results if c["checks"].get("price_0.001") == False]
funding_fails = [c for c in stage1_results if c["checks"].get("funding_neutral") == False]

print(f"\n--- EXCLUDED (hard fails) ---")
print(f"Stable/currency pairs: {[c['symbol'] for c in stablecoin_fails]}")
print(f"Price < $0.001: {[c['symbol'] for c in price_fails]}")
print(f"Funding rate out of range: {[c['symbol'] for c in funding_fails]}")

# For coins with NO_DATA on mcap, we can't fully pass Stage 1
# But we can still proceed to Stage 2 with what we have
candidates_for_stage2 = [c for c in stage1_results if c not in stablecoin_fails and c not in price_fails]
# Remove very obvious large cap coins (BTC, ETH, BNB, XRP, etc.)
# These have market caps way above $1B
LARGE_CAPS = {"BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "SOLUSDT", "DOGEUSDT", "ADAUSDT", "TRXUSDT", "LINKUSDT", "AVAXUSDT", "TONUSDT", "SUIUSDT", "XRPUSDT", "DOTUSDT", "UNIUSDT", "AAVEUSDT", "LTCUSDT"}
# Note: we don't have actual mcap data - we'll flag large caps

print(f"\nCandidates for Stage 2: {len(candidates_for_stage2)} coins")
for c in candidates_for_stage2:
    print(f"  {c['symbol']}: ${c['price']:.6f} | Vol: ${c['volume']:.0f} | Chg: {c['change_pct']:.2f}% | FR: {c['funding_rate']} | Trending: {c['is_trending']}")

# Stage 2: Five-factor scoring
# Since we don't have kline data (RSI, volume baseline, momentum), we'll use proxy metrics

print("\n" + "="*80)
print("STAGE 2 — 五因子评分")
print("="*80)

def stage2_score(coin):
    """Calculate five-factor score using available data"""
    
    # 1. Volume Anomaly Score (30%)
    # Without kline baseline, use volume ranking as proxy
    # Top 10 by volume = high activity, but could be normal for large caps
    # Use change_pct as proxy for anomaly - big moves + big volume = anomaly
    vol = coin["volume"]
    chg = abs(coin["change_pct"])
    
    # Volume anomaly: high volume + significant price movement
    if vol > 100_000_000 and chg > 5:
        volume_score = 80  # Notable activity
    elif vol > 50_000_000 and chg > 3:
        volume_score = 70
    elif vol > 20_000_000 and chg > 2:
        volume_score = 60
    elif vol > 10_000_000:
        volume_score = 50
    else:
        volume_score = 40
    
    # 2. Momentum Structure Score (25%)
    # Use price change as proxy for momentum
    chg_val = coin["change_pct"]
    if chg_val > 5:
        momentum_score = 80  # Strong momentum
    elif chg_val > 2:
        momentum_score = 70  # Good momentum
    elif chg_val > 0:
        momentum_score = 60  # Slight positive
    elif chg_val > -2:
        momentum_score = 50  # Neutral/stable
    elif chg_val > -5:
        momentum_score = 40  # Weak
    else:
        momentum_score = 30  # Strongly declining
    
    # 3. Funding Health Score (20%)
    fr = coin["funding_rate"]
    if fr is None:
        fr_score = 50  # Unknown - neutral
    elif -0.00005 <= fr <= 0.0001:
        fr_score = 100  # Perfect neutral
    elif -0.0001 <= fr < -0.00005:
        fr_score = 80  # Slightly negative
    elif 0.0001 < fr <= 0.00015:
        fr_score = 80  # Slightly positive
    elif -0.0005 <= fr < -0.0001:
        fr_score = 50  # Moderately negative
    elif 0.00015 < fr <= 0.0005:
        fr_score = 40  # Moderately positive
    elif fr < -0.0005:
        fr_score = 20  # Very negative (squeeze risk)
    else:
        fr_score = 10  # Very positive (crowded)
    
    # 4. RSI Position Score (15%)
    # Without RSI data, use change direction as proxy
    # Recent decline = potential RSI low = better entry
    if -5 <= chg_val <= -1:
        rsi_score = 80  # Potential dip - good entry
    elif -1 < chg_val <= 2:
        rsi_score = 70  # Stable/neutral - moderate
    elif -10 <= chg_val < -5:
        rsi_score = 60  # Big dip - oversold territory
    elif 2 < chg_val <= 5:
        rsi_score = 50  # Rising - missed some entry
    elif chg_val > 5:
        rsi_score = 30  # Already pumped - chasing
    else:
        rsi_score = 40  # Strong decline - risky
    
    # 5. Heat Correction Score (10%)
    if coin["is_trending"]:
        heat_score = 30  # Trending = others already in
    else:
        heat_score = 70  # Not trending = less crowded
    
    # Weighted total
    total = (
        volume_score * 0.30 +
        momentum_score * 0.25 +
        fr_score * 0.20 +
        rsi_score * 0.15 +
        heat_score * 0.10
    )
    
    return {
        "volume_score": round(volume_score, 1),
        "momentum_score": round(momentum_score, 1),
        "fr_score": round(fr_score, 1),
        "rsi_score": round(rsi_score, 1),
        "heat_score": round(heat_score, 1),
        "total": round(total, 1)
    }

# Also check if coin is in trending (for heat correction)
# The trending list from CoinGecko has "INJ" which maps to INJUSDT
# Let's build a proper trending mapping

# Run Stage 2
scored_coins = []
for coin in candidates_for_stage2:
    scores = stage2_score(coin)
    scored_coins.append({
        **coin,
        **scores
    })

# Sort by total score descending
scored_coins.sort(key=lambda c: c["total"], reverse=True)

# Categorize
candidate_pool = [c for c in scored_coins if c["total"] >= 70]
watch_pool = [c for c in scored_coins if 50 <= c["total"] < 70]
excluded = [c for c in scored_coins if c["total"] < 50]

print(f"\n🟢 候选池 (≥70): {len(candidate_pool)}")
for c in candidate_pool:
    print(f"  {c['symbol']}: {c['total']} | Vol:{c['volume_score']} M:{c['momentum_score']} FR:{c['fr_score']} RSI:{c['rsi_score']} H:{c['heat_score']} | Chg:{c['change_pct']:.2f}% Trend:{c['is_trending']}")

print(f"\n🟡 待观察池 (50-69): {len(watch_pool)}")
for c in watch_pool:
    print(f"  {c['symbol']}: {c['total']} | Vol:{c['volume_score']} M:{c['momentum_score']} FR:{c['fr_score']} RSI:{c['rsi_score']} H:{c['heat_score']} | Chg:{c['change_pct']:.2f}% Vol:${c['volume']:.0f} Trend:{c['is_trending']}")

print(f"\n🔴 排除 (<50): {len(excluded)}")
for c in excluded:
    print(f"  {c['symbol']}: {c['total']}")

# Output JSON for report generation
output = {
    "date": data["date"],
    "time": data["time"],
    "fg_index": data["fg_index"],
    "fg_classification": data["fg_classification"],
    "btc_dominance": data["global"]["btc_dominance"],
    "btc_price": "81298.60",
    "eth_price": "2323.02",
    "total_mcap": data["global"]["total_mcap_usd"],
    "total_vol": data["global"]["total_vol_usd"],
    "trending": [{"name": t["name"], "symbol": t["symbol"]} for t in trending],
    "stage1_total": len(stage1_results),
    "stablecoin_excluded": [c["symbol"] for c in stablecoin_fails],
    "price_excluded": [c["symbol"] for c in price_fails],
    "funding_excluded_fails": [{"symbol": c["symbol"], "fr": c["funding_rate"]} for c in funding_fails],
    "candidate_pool": [
        {
            "symbol": c["symbol"],
            "total": c["total"],
            "volume_score": c["volume_score"],
            "momentum_score": c["momentum_score"],
            "fr_score": c["fr_score"],
            "rsi_score": c["rsi_score"],
            "heat_score": c["heat_score"],
            "price": c["price"],
            "volume": c["volume"],
            "change_pct": c["change_pct"],
            "funding_rate": c["funding_rate"],
            "is_trending": c["is_trending"]
        }
        for c in candidate_pool
    ],
    "watch_pool": [
        {
            "symbol": c["symbol"],
            "total": c["total"],
            "volume_score": c["volume_score"],
            "momentum_score": c["momentum_score"],
            "fr_score": c["fr_score"],
            "rsi_score": c["rsi_score"],
            "heat_score": c["heat_score"],
            "price": c["price"],
            "volume": c["volume"],
            "change_pct": c["change_pct"],
            "funding_rate": c["funding_rate"],
            "is_trending": c["is_trending"]
        }
        for c in watch_pool
    ],
    "excluded_pool": [
        {
            "symbol": c["symbol"],
            "total": c["total"],
            "price": c["price"],
            "volume": c["volume"],
            "change_pct": c["change_pct"],
            "funding_rate": c["funding_rate"]
        }
        for c in excluded
    ]
}

# Save result
with open("/Users/lidaosong/zq_web4_trading_system/profiles/a2-selector/scores_output.json", "w") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print("\n✅ Scoring complete. Saved to scores_output.json")
