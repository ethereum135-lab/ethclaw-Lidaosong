#!/usr/bin/env python3
"""Batch tag A7 sentiment labels to top gainers with clear narratives."""
import subprocess, json

tags = [
    ("CREAMUSDT", {"sentiment":"positive","narrative":"DeFi lending protocol","alert_level":"info"}),
    ("PNTUSDT",   {"sentiment":"positive","narrative":"pNetwork cross-chain bridge","alert_level":"info"}),
    ("PORTALUSDT",{"sentiment":"positive","narrative":"Portal GameFi/Gaming","alert_level":"info"}),
    ("SENTUSDT",  {"sentiment":"positive","narrative":"Sentinel DePIN/VPN","alert_level":"info"}),
    ("EPICUSDT",  {"sentiment":"positive","narrative":"Epic Cash Privacy","alert_level":"info"}),
    ("STGUSDT",   {"sentiment":"positive","narrative":"Stargate Finance DeFi cross-chain","alert_level":"info"}),
    ("KDAUSDT",   {"sentiment":"positive","narrative":"Kadena Layer1","alert_level":"info"}),
    ("UTKUSDT",   {"sentiment":"positive","narrative":"Utrust payments","alert_level":"info"}),
    ("UNIUSDT",   {"sentiment":"positive","narrative":"Uniswap DeFi DEX","alert_level":"info"}),
    ("WLDUSDT",   {"sentiment":"positive","narrative":"Worldcoin AI identity","alert_level":"info"}),
    ("CLVUSDT",   {"sentiment":"positive","narrative":"Clover Layer2 Polkadot","alert_level":"info"}),
    ("WAVESUSDT", {"sentiment":"positive","narrative":"Waves Layer1","alert_level":"info"}),
    ("HMSTRUSDT", {"sentiment":"positive","narrative":"Hamster Kombat GameFi","alert_level":"info"}),
    ("VICUSDT",   {"sentiment":"positive","narrative":"Viction Layer1","alert_level":"info"}),
    ("ELFUSDT",   {"sentiment":"positive","narrative":"aelf Layer1","alert_level":"info"}),
    ("RENUSDT",   {"sentiment":"positive","narrative":"Ren cross-chain","alert_level":"info"}),
    ("UMAUSDT",   {"sentiment":"positive","narrative":"UMA DeFi oracles","alert_level":"info"}),
    ("RIFUSDT",   {"sentiment":"positive","narrative":"RIF RSK Infra BTC ecosystem","alert_level":"info"}),
    ("MEMEUSDT",  {"sentiment":"positive","narrative":"Meme coin","alert_level":"info"}),
    ("CFGUSDT",   {"sentiment":"positive","narrative":"Centrifuge DeFi RWA","alert_level":"info"}),
    ("HIFIUSDT",  {"sentiment":"positive","narrative":"Hifi Finance DeFi RWA","alert_level":"info"}),
    ("ERNUSDT",   {"sentiment":"positive","narrative":"Ethernity NFT collectibles","alert_level":"info"}),
    ("JSTUSDT",   {"sentiment":"positive","narrative":"JUST DeFi TRON","alert_level":"info"}),
]

for symbol, tag in tags:
    tag_json = json.dumps(tag)
    cmd = ["python3", "tools/enrich_coin.py", "--source", "A7", "--symbol", symbol, "--tag", tag_json]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd="/Users/lidaosong/zq_web4_trading_system")
    status = "✅" if r.returncode == 0 else "❌"
    print(f"{status} {symbol}: {r.stdout.strip()[:80] if r.stdout else r.stderr.strip()[:80]}")
