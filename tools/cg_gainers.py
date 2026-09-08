#!/usr/bin/env python3
"""
CoinGecko Top Gainers Fetcher
通过AWS SSH拉取CoinGecko涨幅榜，发现不在Binance Top200中的活跃币种。
输出: data/cg_gainers.json

用法:
  python3 tools/cg_gainers.py
"""
import json, subprocess, os, re, sys
from datetime import datetime, timezone, timedelta

BJT = timezone(timedelta(hours=8))
WORKDIR = os.path.expanduser("~/zq_web4_trading_system")
AWS_KEY = os.path.expanduser("~/.zq_vault/web4.0.pem")
AWS_HOST = "15.134.211.154"
AWS_USER = "ubuntu"

SSH_CODE = """import json, urllib.request
d = json.loads(urllib.request.urlopen(
    'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=volume_desc&per_page=250&page=1&sparkline=false&price_change_percentage=24h',
    timeout=20).read())
stable = {'USDT','USDC','DAI','FDUSD','USD1','USDE','EUR','EURC','GBP','USDG','U','BUSD','TUSD'}
for c in d:
    sym = c.get('symbol','').upper()
    chg = c.get('price_change_percentage_24h') or 0
    vol = c.get('total_volume') or 0
    mcap = c.get('market_cap') or 0
    price = c.get('current_price') or 0
    if sym not in stable and vol > 10000000 and mcap > 10000000 and (chg > 5 or chg < -5):
        print(f"{sym}|{price}|{chg}|{vol}|{mcap}")
"""

def ssh_run(code, timeout=30):
    encoded = code.replace("'", "'\\''")
    cmd = ["ssh", "-i", AWS_KEY, "-o", "StrictHostKeyChecking=no",
           "-o", "ConnectTimeout=10", f"{AWS_USER}@{AWS_HOST}",
           f"python3 -c '{encoded}'"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            return {"error": f"SSH error: {r.stderr.strip()[:200]}"}
        return {"data": r.stdout}
    except Exception as e:
        return {"error": str(e)}

def main():
    now = datetime.now(BJT)
    print(f"[{now.strftime('%H:%M')}] 🚀 CoinGecko Top Gainers...")
    
    result = ssh_run(SSH_CODE)
    if "error" in result:
        print(f"  ❌ {result['error']}")
        return
    
    lines = result["data"].strip().split("\n")
    gainers = []
    for line in lines:
        parts = line.split("|")
        if len(parts) >= 5:
            gainers.append({
                "symbol": parts[0] + "USDT",
                "price": parts[1],
                "change_pct": parts[2],
                "volume": parts[3],
                "mcap": parts[4],
                "source": "coingecko"
            })
    
    out = {
        "timestamp": now.isoformat(),
        "count": len(gainers),
        "gainers": gainers
    }
    
    out_dir = os.path.join(WORKDIR, "data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "cg_gainers.json")
    
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    
    print(f"  ✅ {len(gainers)}个币 (涨幅>+5% 成交量>$10M)")
    for g in sorted(gainers, key=lambda x: -float(x["volume"]))[:10]:
        print(f"    {g['symbol']:15s} chg={float(g['change_pct']):+.1f}% vol=${float(g['volume'])/1e6:.0f}M")
    print(f"\n✅ 已保存: {out_path}")

if __name__ == "__main__":
    main()
