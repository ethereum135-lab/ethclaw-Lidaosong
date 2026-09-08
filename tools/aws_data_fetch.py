#!/usr/bin/env python3
"""AWS数据采集桥接器 v2 — 通过AWS VPS获取Binance/CoinGecko实时数据
在MAC端运行，通过SSH远程采集。

用法：
  python3 tools/aws_data_fetch.py          → 采集全部数据
  python3 tools/aws_data_fetch.py --top50  → 只采Binance Top50
  python3 tools/aws_data_fetch.py --rates  → 只采费率
  python3 tools/aws_data_fetch.py --trend  → 只采Trending
"""
import json
import subprocess
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

BJT = timezone(timedelta(hours=8))
WORKDIR = os.path.expanduser("~/zq_web4_trading_system")
AWS_KEY = os.path.expanduser("~/.zq_vault/web4.0.pem")
AWS_HOST = "15.134.211.154"
AWS_USER = "ubuntu"
# SOCKS5 fallback (2026-08-19): AWS SSH 被远端关闭时走本地隧道 ssh -D 1080 -N web4
SOCKS_PROXY = "127.0.0.1:1080"
CURL = "/usr/bin/curl"


def socks_curl(url, timeout=40):
    """Fetch JSON via local SOCKS5 tunnel. Returns parsed JSON or {'error': ...}"""
    try:
        r = subprocess.run(
            [CURL, "-s", "--socks5-hostname", SOCKS_PROXY, "--max-time", str(timeout), url],
            capture_output=True, text=True, timeout=timeout + 10
        )
        if r.returncode != 0:
            return {"error": f"curl exit {r.returncode}: {r.stderr.strip()[:150]}"}
        if not r.stdout.strip():
            return {"error": "empty response"}
        return json.loads(r.stdout)
    except json.JSONDecodeError as e:
        return {"error": f"json parse: {e}"}
    except Exception as e:
        return {"error": str(e)}


def fetch_all_local_socks():
    """Fetch all market data locally via SOCKS5 tunnel (SSH-down fallback).
    Emits the same FG|BIN|FR|CG|GLOBAL pipe format as the AWS version."""
    lines = []

    # 1. F&G
    fg = socks_curl("https://api.alternative.me/fng/?limit=1")
    if "error" not in fg and fg.get("data"):
        lines.append(f'FG|{fg["data"][0]["value"]}|{fg["data"][0]["value_classification"]}')
    else:
        lines.append(f'FG|ERROR|{fg.get("error", "no data")}')

    # 2. Binance Top200 (filter identical to AWS version)
    bdata = socks_curl("https://api.binance.com/api/v3/ticker/24hr", timeout=60)
    if "error" not in bdata and isinstance(bdata, list):
        top = sorted(bdata, key=lambda x: float(x.get("quoteVolume", 0)), reverse=True)
        count = 0
        for d in top:
            s = d.get("symbol", "")
            if s.endswith("USDT") and "UP" not in s and "DOWN" not in s and "BIDR" not in s and "IDRT" not in s and "USDC" not in s and "FDUSD" not in s and "USD1" not in s:
                lines.append(f'BIN|{s}|{d.get("lastPrice","")}|{d.get("quoteVolume","")}|{d.get("priceChangePercent","")}|{d.get("highPrice","")}|{d.get("lowPrice","")}')
                count += 1
                if count >= 200:
                    break
    else:
        lines.append(f'BIN|ERROR|{bdata.get("error", "bad shape")}')

    # 3. Funding rates
    fr = socks_curl("https://fapi.binance.com/fapi/v1/premiumIndex", timeout=40)
    if "error" not in fr and isinstance(fr, list):
        for item in fr:
            s = item.get("symbol", "")
            if s.endswith("USDT"):
                lines.append(f'FR|{s}|{item.get("lastFundingRate","0")}|{item.get("markPrice","0")}')
    else:
        lines.append(f'FR|ERROR|{fr.get("error", "bad shape")}')

    # 4. CoinGecko Trending
    cg = socks_curl("https://api.coingecko.com/api/v3/search/trending", timeout=40)
    if "error" not in cg and cg.get("coins"):
        for c in cg["coins"]:
            item = c.get("item", {})
            lines.append(f'CG|{item.get("name","")}|{item.get("symbol","")}|{item.get("market_cap_rank","")}|{item.get("score",0)}')
    else:
        lines.append(f'CG|ERROR|{cg.get("error", "no coins")}')

    # 5. Global market data (with retry)
    mg = None
    for attempt in range(3):
        mg = socks_curl("https://api.coingecko.com/api/v3/global", timeout=40)
        if "error" not in mg and mg.get("data"):
            break
        import time
        time.sleep(2)
    if mg and "error" not in mg and mg.get("data"):
        d = mg["data"]
        lines.append(f'GLOBAL|{d.get("market_cap_percentage",{}).get("btc","")}|{d.get("total_market_cap",{}).get("usd","")}|{d.get("total_volume",{}).get("usd","")}')
    else:
        lines.append(f'GLOBAL|ERROR|{mg.get("error","429 retry failed") if mg else "no response"}')

    return {"data": "\n".join(lines)}


def ssh_run(python_code, timeout=45):
    """Run Python code on AWS via SSH and capture stdout"""
    encoded = python_code.replace("'", "'\\''")
    cmd = [
        "ssh", "-i", AWS_KEY,
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=10",
        f"{AWS_USER}@{AWS_HOST}",
        f"python3 -c '{encoded}'"
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            return {"error": f"SSH error {r.returncode}: {r.stderr.strip()[:200]}"}
        return {"data": r.stdout}
    except subprocess.TimeoutExpired:
        return {"error": "SSH timeout"}
    except Exception as e:
        return {"error": str(e)}


def fetch_all():
    """Fetch all market data in one SSH call"""
    code = """import json, urllib.request, sys
def jget(url, timeout=15):
    try: return json.loads(urllib.request.urlopen(url, timeout=timeout).read())
    except Exception as e: return {"error": str(e)}

# 1. F&G
try:
    fg = jget('https://api.alternative.me/fng/')
    if 'error' not in fg:
        print(f'FG|{fg["data"][0]["value"]}|{fg["data"][0]["value_classification"]}')
    else:
        print(f'FG|ERROR|{fg["error"]}')
except: print('FG|ERROR|exception')

# 2. Binance Top
try:
    bdata = jget('https://api.binance.com/api/v3/ticker/24hr')
    if 'error' not in bdata:
        top = sorted(bdata, key=lambda x: float(x['quoteVolume']), reverse=True)
        count = 0
        for d in top:
            s = d['symbol']
            if s.endswith('USDT') and 'UP' not in s and 'DOWN' not in s and 'BIDR' not in s and 'IDRT' not in s and 'USDC' not in s and 'FDUSD' not in s and 'USD1' not in s:
                print(f'BIN|{s}|{d["lastPrice"]}|{d["quoteVolume"]}|{d["priceChangePercent"]}|{d["highPrice"]}|{d["lowPrice"]}')
                count += 1
                if count >= 200:
                    break
    else:
        print(f'BIN|ERROR|{bdata["error"]}')
except: print('BIN|ERROR|exception')

# 3. Funding rates
try:
    fr = jget('https://fapi.binance.com/fapi/v1/premiumIndex')
    if 'error' not in fr:
        for item in fr:
            s = item['symbol']
            if s.endswith('USDT'):
                fr_val = item.get('lastFundingRate','0')
                mp = item.get('markPrice','0')
                print(f'FR|{s}|{fr_val}|{mp}')
    else:
        print(f'FR|ERROR|{fr["error"]}')
except: print('FR|ERROR|exception')

# 4. CoinGecko Trending
try:
    cg = jget('https://api.coingecko.com/api/v3/search/trending')
    if 'error' not in cg:
        for c in cg.get('coins',[]):
            item = c['item']
            print(f'CG|{item["name"]}|{item["symbol"]}|{item.get("market_cap_rank","")}|{item.get("score",0)}')
    else:
        print(f'CG|ERROR|{cg["error"]}')
except: print('CG|ERROR|exception')

# 5. Global market data (with retry)
try:
    mg = None
    for attempt in range(3):
        mg = jget('https://api.coingecko.com/api/v3/global')
        if 'error' not in mg or '429' not in str(mg):
            break
        import time; time.sleep(2)
    if mg and 'error' not in mg:
        d = mg['data']
        print(f'GLOBAL|{d.get("market_cap_percentage",{}).get("btc","")}|{d.get("total_market_cap",{}).get("usd","")}|{d.get("total_volume",{}).get("usd","")}')
    else:
        print(f'GLOBAL|ERROR|{mg.get("error","429 retry failed")}')
except: print('GLOBAL|ERROR|exception')
"""
    result = ssh_run(code, timeout=60)
    return result


def parse_output(output_text):
    """Parse the pipe-delimited output into structured data"""
    data = {
        "fg_index": None,
        "fg_classification": None,
        "binance_top200": [],
        "funding_rates": {},
        "coingecko_trending": [],
        "global": {},
        "errors": []
    }

    for line in output_text.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("|")
        prefix = parts[0]

        if prefix == "FG":
            data["fg_index"] = parts[1]
            data["fg_classification"] = parts[2]
        elif prefix == "BIN":
            if parts[1] == "ERROR":
                data["errors"].append(f"Binance: {parts[2]}")
            else:
                data["binance_top200"].append({
                    "symbol": parts[1], "price": parts[2],
                    "volume": parts[3], "change_pct": parts[4],
                    "high": parts[5], "low": parts[6]
                })
        elif prefix == "FR":
            if parts[1] == "ERROR":
                data["errors"].append(f"Funding: {parts[2]}")
            else:
                data["funding_rates"][parts[1]] = {
                    "rate": parts[2], "mark_price": parts[3]
                }
        elif prefix == "CG":
            if parts[1] == "ERROR":
                data["errors"].append(f"Trending: {parts[2]}")
            else:
                data["coingecko_trending"].append({
                    "name": parts[1], "symbol": parts[2],
                    "rank": parts[3], "score": parts[4]
                })
        elif prefix == "GLOBAL":
            if parts[1] == "ERROR":
                data["errors"].append(f"Global: {parts[2]}")
            else:
                data["global"] = {
                    "btc_dominance": parts[1],
                    "total_mcap_usd": parts[2],
                    "total_vol_usd": parts[3] if len(parts) > 3 else ""
                }

    return data


def save_snapshot(data, source_note=None):
    """Save structured data to JSON for A1/A2 to read"""
    now = datetime.now(BJT)

    if source_note:
        src = source_note
        dq = "\u26a0\ufe0f SOCKS5本地fallback（AWS SSH断连）" if not data["errors"] else "\u26a0\ufe0f SOCKS5本地fallback，部分数据缺失"
    else:
        src = "AWS (15.134.211.154) \u2192 Binance API + CoinGecko"
        dq = "\u2705 \u6765\u81eaAWS\u5b9e\u65f6API" if not data["errors"] else "\u26a0\ufe0f \u90e8\u5206\u6570\u636e\u7f3a\u5931"

    snapshot = {
        "timestamp": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M"),
        "source": src,
        "fg_index": data["fg_index"],
        "fg_classification": data["fg_classification"],
        "binance_top200": data["binance_top200"],
        "funding_rates": data["funding_rates"],
        "coingecko_trending": data["coingecko_trending"],
        "global": data["global"],
        "errors": data["errors"],
        "data_quality": dq
    }

    out_path = os.path.join(WORKDIR, "data", "aws_snapshot.json")
    os.makedirs(os.path.join(WORKDIR, "data"), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(snapshot, f, indent=2, default=str)

    return out_path


def main():
    now = datetime.now(BJT)
    print(f"[{now.strftime('%H:%M')}] \U0001f680 AWS\u6570\u636e\u91c7\u96c6...")
    print(f"  SSH\u2192 ubuntu@{AWS_HOST}")

    result = fetch_all()
    used_fallback = False

    if "error" in result:
        print(f"  \u274c SSH\u91c7\u96c6\u5931\u8d25: {result['error']}")
        print(f"  \U0001f6e0\ufe0f SOCKS5\u672c\u5730fallback\u2026 (127.0.0.1:1080)")
        result = fetch_all_local_socks()
        if "error" in result:
            print(f"  \u274c SOCKS5 fallback\u4e5f\u5931\u8d25: {result['error']}")
            sys.exit(1)
        used_fallback = True

    data = parse_output(result["data"])

    # Print summary
    print(f"  F&G: {data['fg_index']}/100 \u2014 {data['fg_classification']}")
    btc_p = next((c['price'] for c in data['binance_top200'] if c['symbol']=='BTCUSDT'), 'N/A')
    eth_p = next((c['price'] for c in data['binance_top200'] if c['symbol']=='ETHUSDT'), 'N/A')
    print(f"  BTC: ${btc_p}")
    print(f"  ETH: ${eth_p}")
    print(f"  Binance Top200: {len(data['binance_top200'])}个币")
    print(f"  Funding Rates: {len(data['funding_rates'])}个币")
    trending = data.get('coingecko_trending', [])
    print(f"  Trending: {', '.join([c['name'] for c in trending[:5]])}")
    print(f"  BTC Dominance: {data['global'].get('btc_dominance','N/A')}%")

    if data["errors"]:
        for e in data["errors"]:
            print(f"  \u26a0\ufe0f {e}")

    if used_fallback:
        path = save_snapshot(data, source_note="\u672c\u5730SOCKS5\u9690\u9053(127.0.0.1:1080) \u2192 Binance API + CoinGecko (AWS SSH\u65ad\u8fdefallback)")
    else:
        path = save_snapshot(data)
    print(f"\n\u2705 \u5df2\u4fdd\u5b58: {path}")


if __name__ == "__main__":
    main()
