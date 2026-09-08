#!/usr/bin/env python3
"""
A8 资金官 — 数据采集桥接器 v1
通过AWS SSH隧道获取被防火墙封锁的API数据。
用法:
  python3 tools/a8_data_fetch.py          → 采集全部数据
  python3 tools/a8_data_fetch.py --trending → 只采CoinGecko/热门
  python3 tools/a8_data_fetch.py --dex     → 只采DexScreener小市值
  python3 tools/a8_data_fetch.py --whale   → 只采巨鲸/聪明钱信号
"""

import json
import subprocess
import os
import sys
from datetime import datetime, timezone, timedelta

BJT = timezone(timedelta(hours=8))
WORKDIR = os.path.expanduser("~/zq_web4_trading_system")
AWS_KEY = os.path.expanduser("~/.zq_vault/web4.0.pem")
AWS_HOST = "15.134.211.154"
AWS_USER = "ubuntu"
OUTPUT_DIR = os.path.join(WORKDIR, "data", "a8")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def ssh_run(python_code, timeout=60):
    """Run Python code on AWS via SSH and capture stdout"""
    encoded = python_code.replace("'", "'\\''")
    cmd = [
        "ssh", "-i", AWS_KEY,
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=5",
        f"{AWS_USER}@{AWS_HOST}",
        f"python3 -c '{encoded}'"
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            return {"error": f"SSH error {r.returncode}: {r.stderr.strip()[:300]}"}
        return {"data": r.stdout}
    except subprocess.TimeoutExpired:
        return {"error": "SSH timeout"}
    except Exception as e:
        return {"error": str(e)}


def fetch_coingecko_trending():
    """Fetch CoinGecko trending + categories via AWS"""
    code = """
import json, urllib.request, sys

def jget(url, timeout=15):
    try: return json.loads(urllib.request.urlopen(url, timeout=timeout).read())
    except Exception as e: return {"error": str(e)}

# 1. Trending tokens
trending = jget('https://api.coingecko.com/api/v3/search/trending')
if 'error' in trending:
    print(f'CG_TRENDING|ERROR|{trending[\"error\"]}')
else:
    for c in trending.get('coins',[]):
        item = c['item']
        print(f'CG_TRENDING|{item[\"name\"]}|{item[\"symbol\"]}|{item.get(\"market_cap_rank\",\"\")}|{item.get(\"score\",0)}')
    if not trending.get('coins'):
        print('CG_TRENDING|EMPTY|no trending data')

# 2. Categories (hot sectors)
cats = jget('https://api.coingecko.com/api/v3/coins/categories')
if 'error' in cats:
    print(f'CG_CATS|ERROR|{cats[\"error\"]}')
else:
    for cat in cats[:20]:
        name = cat.get('name','')
        mcap = cat.get('market_cap','')
        vol = cat.get('volume_24h','')
        change = cat.get('market_cap_change_24h','')
        print(f'CG_CAT|{name}|{mcap}|{vol}|{change}')
"""
    return ssh_run(code, timeout=60)


def fetch_dex_smallcaps():
    """Fetch small-cap tokens from DexScreener (Solana/ETH DEXes) via AWS"""
    code = """
import json, urllib.request, sys

def jget(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        return json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    except Exception as e:
        return {"error": str(e)}

# Search for small-cap tokens on Solana DEX
queries = ['SOL', 'USDC', 'WETH', 'BONK', 'WIF', 'PEPE', 'DOGE']
seen = set()

for q in queries:
    url = f'https://api.dexscreener.com/latest/dex/search/?q={q}'
    data = jget(url)
    if 'error' in data:
        print(f'DEX|ERROR|{q}: {data[\"error\"]}')
        continue
    pairs = data.get('pairs', [])
    for p in pairs[:10]:
        # Only small cap: price < $20 and some volume
        price = p.get('priceUsd', '0')
        try:
            price_f = float(price)
        except:
            continue
        if price_f > 0 and price_f < 20:
            symbol = p.get('baseToken',{}).get('symbol','?')
            chain = p.get('chainId','?')
            pair_addr = p.get('pairAddress','?')
            key = f"{chain}:{symbol}:{pair_addr[:10]}"
            if key in seen:
                continue
            seen.add(key)
            vol_h24 = p.get('volume',{}).get('h24','0')
            liq = p.get('liquidity',{}).get('usd','0')
            txns_buy = p.get('txns',{}).get('h24',{}).get('buys',0)
            txns_sell = p.get('txns',{}).get('h24',{}).get('sells',0)
            ratio = float(txns_buy)/(float(txns_sell)+1) if float(txns_sell) > 0 else float('inf')
            change_h24 = p.get('priceChange',{}).get('h24','0')
            addr = p.get('baseToken',{}).get('address','')
            print(f'DEX|{chain}|{symbol}|{price}|{vol_h24}|{liq}|{txns_buy}|{txns_sell}|{ratio:.2f}|{change_h24}|{addr}')
"""
    return ssh_run(code, timeout=90)


ETHERSCAN_API_KEY = "4HSI18GIQ7ITWEZR7K7B6U7MUYNIMSG7RX"
SOLSCAN_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjcmVhdGVkQXQiOjE3Nzg4NDY3NTE5MDYsImVtYWlsIjoiZXRoZXJldW0xMzVAZ21haWwuY29tIiwiYWN0aW9uIjoidG9rZW4tYXBpIiwiYXBpVmVyc2lvbiI6InYyIiwiaWF0IjoxNzc4ODQ2NzUxfQ.tyRtL_5HxLKbcS_cNataDilSu21B8LwjoKl1kDAciPI"
DUNE_API_KEY = "T8EqZzZBQejJs8QUl1hBI5IJAlH4DHqc"
DUNE_QUERY_ID = 7508226  # A8_Whale_Alert_v2_correct: ETH>100 + USDT/USDC>$500K 转账监控
HELIUS_API_KEY = "a654435a-9db8-4179-8943-2d17d69f0a36"
BSCSCAN_API_KEY = "95W9PEYIF26HEM4QNQWCZ3WAUF4CCFP16N"
ARBISCAN_API_KEY = "MMJTRRWUJ8SYNGQ2F114Q1KMK63WQCDKGG"


def fetch_solscan_data():
    """Fetch Solscan Pro API data via AWS. Uses 'token' header auth.
    Note: Lite-tier key returns 'upgrade required' on data endpoints.
    Once upgraded to Pro, this will return live Solana on-chain data."""
    code = """import json, urllib.request, sys

def jget(url, headers, timeout=15):
    try:
        req = urllib.request.Request(url, headers=headers)
        return json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    except urllib.request.HTTPError as e:
        return {"error": str(e.code) + ": " + e.read().decode()[:80]}
    except Exception as e:
        return {"error": str(e)}

TOKEN = "__SOLSCAN_KEY__"
AUTH = {"token": TOKEN, "User-Agent": "Mozilla/5.0"}
BASE = "https://pro-api.solscan.io/v2.0"

# 1. Chain info
r = jget(BASE + "/chain/info", AUTH)
if "error" in r:
    print("SOLSCAN|CHAIN|error|" + str(r["error"][:80]))
else:
    print("SOLSCAN|CHAIN|ok|" + str(r.get("result",{}).get("currentSlot","?"))[:50])

# 2. Token trending
r = jget(BASE + "/token/trending?limit=5", AUTH)
if "error" in r:
    print("SOLSCAN|TRENDING|error|" + str(r["error"][:80]))
else:
    items = r.get("data", [])[:5]
    for t in items:
        print("SOLSCAN|TRENDING|" + str(t.get("symbol","?")) + "|" + str(t.get("price","?")) + "|" + str(t.get("priceChange24h","?")))
    if not items:
        print("SOLSCAN|TRENDING|empty")

# 3. Recent account activities (whale tracking)
r = jget(BASE + "/account/tokens?address=2EahF7gADmGC47KvdPRdMjauLuZ1odQ7V4yAp2aLymWV", AUTH)
if "error" in r:
    print("SOLSCAN|ACCOUNT|error|" + str(r["error"][:80]))
else:
    tokens = r.get("data", [])[:5]
    for t in tokens:
        print("SOLSCAN|ACCOUNT|" + str(t.get("tokenAddress","?")[:10]) + "|" + str(t.get("tokenAmount","?")) + "|" + str(t.get("tokenPrice","?")))
    if not tokens:
        print("SOLSCAN|ACCOUNT|empty")
"""
    code = code.replace("__SOLSCAN_KEY__", SOLSCAN_API_KEY)
    return ssh_run(code, timeout=60)


def fetch_solana_rpc():
    """Fetch Solana on-chain data via public RPC (free, no key needed)."""
    code = """import json, urllib.request, sys

def rpc_call(method, params=None):
    try:
        body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params or []}).encode()
        req = urllib.request.Request("https://api.mainnet-beta.solana.com", data=body,
            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
        data = json.loads(urllib.request.urlopen(req, timeout=15).read())
        return data.get("result")
    except Exception as e:
        return {"error": str(e)[:100]}

# 1. Recent block (latest slot)
slot = rpc_call("getSlot")
if isinstance(slot, dict) and "error" in slot:
    print("SOLRPC|SLOT|error|" + str(slot["error"]))
else:
    print("SOLRPC|SLOT|" + str(slot))

# 2. Recent block production rate (network health)
bp = rpc_call("getRecentPerformanceSamples", [5])
if isinstance(bp, dict) and "error" in bp:
    print("SOLRPC|PERF|error|" + str(bp["error"]))
elif bp:
    for s in bp[:3]:
        print("SOLRPC|PERF|" + str(s.get("slot",0)) + "|" + str(s.get("numTransactions",0)) + "|" + str(s.get("samplePeriodSecs",0)))
else:
    print("SOLRPC|PERF|empty")

# 3. Vote accounts (staking overview)
va = rpc_call("getVoteAccounts")
if isinstance(va, dict) and "error" in va:
    print("SOLRPC|VOTES|error|" + str(va["error"]))
elif va:
    current = va.get("current", [])
    print("SOLRPC|VOTES|" + str(len(current)) + "|active_validators")
    top = sorted(current, key=lambda x: float(x.get("activatedStake",0)), reverse=True)[:3]
    for v in top:
        print("SOLRPC|VOTE|" + str(v.get("votePubkey","?")[:12]) + "|stake=" + format(int(v.get("activatedStake",0))/1e9, ".1f") + " SOL")

# 4. Token supply for major tokens
wSOL = "So11111111111111111111111111111111111111112"
ts = rpc_call("getTokenSupply", [wSOL])
if isinstance(ts, dict) and "error" in ts:
    print("SOLRPC|WSUPPLY|error|" + str(ts["error"]))
elif ts:
    v = ts.get("value",{})
    print("SOLRPC|WSUPPLY|" + str(v.get("amount","?")) + "|decimals=" + str(v.get("decimals","?")))

# 5. Recent fees (network congestion)
fees = rpc_call("getRecentPrioritizationFees")
if isinstance(fees, dict) and "error" in fees:
    print("SOLRPC|FEES|error|" + str(fees["error"]))
elif fees:
    avg = sum(float(f.get("prioritizationFee",0)) for f in fees) / len(fees) if fees else 0
    print("SOLRPC|FEES|avg=" + format(avg, ".1f") + "|samples=" + str(len(fees)))
"""
    return ssh_run(code, timeout=60)


def fetch_whale_alerts():
    """Fetch whale/smart-money movements + Etherscan on-chain data via AWS"""
    code = """import json, urllib.request, sys
from concurrent.futures import ThreadPoolExecutor, as_completed

def jget(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        return json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    except Exception as e:
        return {"error": str(e)}

ES_KEY = "__ES_API_KEY__"

# --- 1. Etherscan Gas Tracker (V2 API) ---
try:
    gas = jget('https://api.etherscan.io/v2/api?chainid=1&module=gastracker&action=gasoracle&apikey=' + ES_KEY)
    if 'error' in gas:
        print('ETH|GAS|error')
    else:
        r = gas.get('result', {})
        print('ETH|GAS|' + str(r.get('SafeGasPrice','?')) + '|' + str(r.get('ProposeGasPrice','?')) + '|' + str(r.get('FastGasPrice','?')))
except:
    print('ETH|GAS|not_available')

# --- 2. Etherscan Latest ETH Transfers ---
try:
    eth_tx = jget('https://api.etherscan.io/v2/api?chainid=1&module=account&action=txlist&address=0x742d35Cc6634C0532925a3b844Bc453eB9Aa8F9c&sort=desc&offset=3&apikey=' + ES_KEY)
    if 'error' in eth_tx:
        print('ETH|TX|error|' + str(eth_tx['error']))
    elif eth_tx.get('status') == '1':
        for tx in eth_tx.get('result', [])[:3]:
            print('ETH|TX|' + str(tx.get('from','?')) + '|' + str(tx.get('to','?')) + '|' + str(tx.get('value','0')) + '|' + str(tx.get('hash','?')[:16]))
except:
    print('ETH|TX|not_available')

# --- 3. Etherscan Latest USDT Transfers ---
try:
    usdt_tx = jget('https://api.etherscan.io/v2/api?chainid=1&module=account&action=tokentx&contractaddress=0xdAC17F958D2ee523a2206206994597C13D831ec7&sort=desc&offset=5&apikey=' + ES_KEY)
    if 'error' in usdt_tx:
        print('USDT|TX|error|' + str(usdt_tx['error']))
    elif usdt_tx.get('status') == '1':
        for tx in usdt_tx.get('result', [])[:5]:
            val = int(tx.get('value', '0')) / 1e6
            print('USDT|TX|' + str(tx.get('from','?')) + '|' + str(tx.get('to','?')) + '|' + f"{val:.2f}" + '|' + str(tx.get('hash','?')[:16]))
except:
    print('USDT|TX|not_available')

# --- 4. Tracked wallet addresses (parallel queries via ThreadPoolExecutor) ---
TRACKED_WALLETS = [
    # Exchange wallets — high threshold (>=1000 ETH or >=$1M USDT)
    ("EXCHANGE", "Binance_1", "0x28C6c06298d514Db089934071355E5743bf21d60", 1000, 1000000),
    ("EXCHANGE", "Binance_2", "0xBE0eB53F46cd790Cd13851d5EFf43D12404d33E8", 1000, 1000000),
    ("EXCHANGE", "Bybit", "0x1Db92e2EeBC8E0c075a02BeA49a2935BcD2dFCF4", 1000, 1000000),
    ("EXCHANGE", "OKX", "0x6cC5F688a315f3dC28A7781717a9A798a59fDA7b", 1000, 1000000),
    ("EXCHANGE", "Coinbase", "0x71660c4005BA85c37ccec55d0C4493E66Fe775d3", 1000, 1000000),
    # Whale wallets — medium threshold (>=500 ETH or >=$500K USDT)
    ("WHALE", "JustinSun", "0x3DdF93d20d5AC20D4e89c97d9F7dB787C0CA4Ca8", 500, 500000),
    ("WHALE", "JumpTrading", "0x88671cDC0C27c7C5348479e6aC1542Cf6A3d70C0", 500, 500000),
    ("WHALE", "Alameda", "0x0B7007c13325C8F11E2B8cB7E7c9E5c30Ff8Fb8C", 500, 500000),
    # Treasury — very high threshold (>=10000 ETH or >=$10M USDT)
    ("TREASURY", "TetherTreasury", "0x5754284f345afc66a98fbB0a0Afe71e0F007B949", 10000, 10000000),
]

def check_wallet(addr_type, label, addr, eth_min, usdt_min):
    lines = []
    # ETH transfers — only show top 3 largest
    try:
        url = f'https://api.etherscan.io/v2/api?chainid=1&module=account&action=txlist&address={addr}&sort=desc&offset=5&apikey={ES_KEY}'
        tx_data = jget(url)
        if tx_data.get('status') == '1':
            for tx in tx_data.get('result', []):
                val_eth = int(tx.get('value', '0')) / 1e18
                if val_eth >= eth_min:
                    direction = 'out' if tx.get('from','').lower() == addr.lower() else 'in'
                    lines.append(f'WHALE|WALLET|{label}|{direction}|{val_eth:.0f}|ETH')
    except:
        pass
    # Token transfers — only show top 3 largest
    try:
        url2 = f'https://api.etherscan.io/v2/api?chainid=1&module=account&action=tokentx&address={addr}&sort=desc&offset=5&apikey={ES_KEY}'
        tok_data = jget(url2)
        if tok_data.get('status') == '1':
            for tx in tok_data.get('result', []):
                symbol = tx.get('tokenSymbol', '?')
                decimals = int(tx.get('tokenDecimal', 18))
                val = int(tx.get('value', '0')) / (10 ** decimals)
                if (symbol in ('USDT', 'USDC') and val >= usdt_min) or (symbol not in ('USDT', 'USDC') and val >= eth_min * 2000):
                    direction = 'out' if tx.get('from','').lower() == addr.lower() else 'in'
                    lines.append(f'WHALE|TOKEN|{label}|{direction}|{val:.0f}|{symbol}')
    except:
        pass
    return lines[:6]  # Max 6 signals per wallet (avoid flooding)

with ThreadPoolExecutor(max_workers=8) as pool:
    futures = {pool.submit(check_wallet, t, l, a, e, u): l for t, l, a, e, u in TRACKED_WALLETS}
    for f in as_completed(futures):
        for line in f.result():
            print(line)

"""
    code = code.replace("__ES_API_KEY__", ETHERSCAN_API_KEY)
    return ssh_run(code, timeout=120)

def fetch_smart_money():
    """Detect large buy inflows across all chains via DexScreener + Etherscan.
    Core logic: scan DexScreener for tokens from OUR selection pool (A2) and
    bull coin picks (A3), plus a fallback list of major tokens.
    Records chain/symbol/volume/price as actionable buy signals."""
    
    # --- 1. Read our own selection pool and bull coin picks ---
    queries = set()
    proj_dir = "/Users/lidaosong/zq_web4_trading_system"
    today = datetime.now(BJT).strftime("%Y-%m-%d")
    
    # Read A2 candidate pool (today's or latest) - only top candidate coins
    a2_dir = os.path.join(proj_dir, "profiles/a2-selector/output")
    a2_files = sorted([f for f in os.listdir(a2_dir) if f.endswith(".md")], reverse=True) if os.path.isdir(a2_dir) else []
    for fname in a2_files[:1]:  # only today's
        fpath = os.path.join(a2_dir, fname)
        try:
            with open(fpath) as f:
                content = f.read()
            # Find "候选池" section and extract top coins from the numbered ranking table
            # Table format: | 1 | SYMBOLUSDT | ... | **SCORE** | ... | CHANGE% |
            in_pool_section = False
            for line in content.split("\n"):
                if "候选池" in line and "≥70" in line:
                    in_pool_section = True
                    continue
                if in_pool_section:
                    # Stop at next section (starts with ###)
                    if line.startswith("###") or line.startswith("##"):
                        break
                    # Parse ranking table: | N | COINUSDT | ... | **SCORE** | ...
                    if line.startswith("|") and "USDT" in line:
                        cells = [c.strip() for c in line.split("|")]
                        if len(cells) >= 3:
                            # cells[1] = rank number, cells[2] = symbol
                            sym = cells[2].upper().replace("USDT", "").replace("PERP", "").strip()
                            if sym and len(sym) <= 15 and sym.isascii() and not any(c in sym for c in "|/\\"):
                                queries.add(sym)
        except:
            pass
    
    # Read A3 bull coin report (today's) - only date-named files
    a3_dir = os.path.join(proj_dir, "profiles/a3-bull/output")
    a3_files = sorted([f for f in os.listdir(a3_dir) if f.endswith(".md") and "-" in f and f[0].isdigit()], reverse=True) if os.path.isdir(a3_dir) else []
    for fname in a3_files[:1]:  # only today's
        fpath = os.path.join(a3_dir, fname)
        try:
            with open(fpath) as f:
                content = f.read()
            # Find bull coin pick: look for "选中币种：SYMBOLUSDT" pattern
            for line in content.split("\n"):
                if "选中币种" in line:
                    import re
                    m = re.search(r'选中币种[：:]\s*(\w+)', line)
                    if m:
                        sym = m.group(1).upper().replace("USDT", "").replace("PERP", "").strip()
                        if sym and len(sym) <= 10 and sym.isascii() and not any(c in sym for c in "|/\\"):
                            queries.add(sym)
        except:
            pass
    
    # Fallback: if we got nothing from A2/A3, supplement with major tokens
    if len(queries) < 5:
        queries.update({"BTC", "ETH", "SOL", "XRP", "DOGE", "PEPE", "BNB", "SUI", "LINK", "AAVE"})
    
    queries_list = sorted(queries)[:30]  # Max 30 to stay within rate limits
    
    code = """import json, urllib.request, sys
from concurrent.futures import ThreadPoolExecutor, as_completed

ES_KEY = "__ES_API_KEY__"

def jget(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        return json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    except Exception as e:
        return {"error": str(e)[:80]}

# --- 1. Scan OUR selection pool + bull coins on DexScreener ---
queries = __QUERIES_PLACEHOLDER__
seen = set()
buy_signals = []

for q in queries:
    data = jget(f'https://api.dexscreener.com/latest/dex/search/?q={q}')
    if 'error' in data:
        continue
    for p in data.get('pairs', [])[:10]:
        try:
            price_f = float(p.get('priceUsd', '0'))
        except:
            continue
        # Only tokens we can afford: $430 buys at least some amount
        if price_f > 0 and price_f < 50:
            chain = p.get('chainId', '')
            symbol = p.get('baseToken', {}).get('symbol', '?')
            contract = p.get('baseToken', {}).get('address', '')
            key = f"{chain}:{contract}"
            if key in seen or not contract:
                continue
            seen.add(key)
            try:
                vol = float(p.get('volume', {}).get('h24', 0))
                liq = float(p.get('liquidity', {}).get('usd', 0))
                txns = p.get('txns', {}).get('h24', {})
                buys = int(txns.get('buys', 0))
                sells = int(txns.get('sells', 0))
                ratio = buys / (sells + 1)
                change_h24 = p.get('priceChange', {}).get('h24', '0')

                # KEY METRIC: real volume >= $50K = real money coming in
                if vol >= 50000 and liq >= 5000:
                    buy_signals.append((chain, symbol, contract, vol, liq, price_f, ratio, change_h24))
                    print(f'BUY|INFLOW|{chain}|{symbol}|{contract}|{vol:.0f}|{liq:.0f}|{price_f:.8f}|{ratio:.2f}x|{change_h24}')
            except:
                pass

# --- 2. Also check Etherscan for large USDT/USDC inflows (direct money movements) ---
try:
    usdt_url = f'https://api.etherscan.io/v2/api?chainid=1&module=account&action=tokentx&contractaddress=0xdAC17F958D2ee523a2206206994597C13D831ec7&sort=desc&offset=10&apikey={ES_KEY}'
    usdt_data = jget(usdt_url)
    if usdt_data.get('status') == '1':
        for tx in usdt_data.get('result', []):
            val = int(tx.get('value', '0')) / 1e6
            if val >= 500000:  # $500K+ USDT movement (排除小额转账)
                treasury_addr = '0x5754284f345afc66a98fbb0a0afe71e0f007b949'
                is_treasury = tx.get('from','').lower() == treasury_addr or tx.get('to','').lower() == treasury_addr
                direction = 'treasury' if is_treasury else ('out' if tx.get('from','').lower() == treasury_addr else 'in')
                to_addr = tx.get('to', '?')[:12]
                signal_type = 'TREASURY' if is_treasury else 'MONEY_IN'
                print(f'BUY|{signal_type}|ETH|USDT|{val:.0f}|{direction}|{to_addr}')

    usdc_url = f'https://api.etherscan.io/v2/api?chainid=1&module=account&action=tokentx&contractaddress=0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48&sort=desc&offset=10&apikey={ES_KEY}'
    usdc_data = jget(usdc_url)
    if usdc_data.get('status') == '1':
        for tx in usdc_data.get('result', []):
            val = int(tx.get('value', '0')) / 1e6
            if val >= 500000:  # $500K+ USDC movement
                direction = 'out' if tx.get('from','').lower() in ['0x5754284f345afc66a98fbb0a0afe71e0f007b949'] else 'in'
                to_addr = tx.get('to', '?')[:12]
                print(f'BUY|MONEY_IN|ETH|USDC|{val:.0f}|{direction}|{to_addr}')
except:
    print('BUY|MONEY_IN_ERROR|etherscan_fail')

# --- 3. Summary ---
if buy_signals:
    print(f'BUY|SUMMARY|found_{len(buy_signals)}_high_volume_tokens')
else:
    print('BUY|SUMMARY|none_found')
"""
    code = code.replace("__ES_API_KEY__", ETHERSCAN_API_KEY)
    code = code.replace("__QUERIES_PLACEHOLDER__", str(queries_list))
    return ssh_run(code, timeout=120)


def fetch_dune_whale():
    """Fetch whale alerts from Dune Analytics API (free replacement for Whale Alert $29/mo).
    Uses Dune query ID 7508226: monitors ETH transfers >100 ETH + USDT/USDC >$500K.
    Runs via AWS SSH (same pattern as other data sources)."""
    now = datetime.now(BJT)
    code = """import json, urllib.request, sys, time
DUNE_KEY = "__DUNE_KEY__"
QUERY_ID = __DUNE_QID__
try:
    req = urllib.request.Request(
        f'https://api.dune.com/api/v1/query/{QUERY_ID}/execute',
        method='POST',
        headers={'x-dune-api-key': DUNE_KEY}
    )
    resp = json.loads(urllib.request.urlopen(req, timeout=30).read())
    exec_id = resp.get('execution_id', '')
    if not exec_id:
        print('DUNE|ERROR|no_execution_id')
        sys.exit(0)
    for _ in range(8):
        time.sleep(5)
        req2 = urllib.request.Request(
            f'https://api.dune.com/api/v1/execution/{exec_id}/results',
            headers={'x-dune-api-key': DUNE_KEY}
        )
        result = json.loads(urllib.request.urlopen(req2, timeout=15).read())
        state = result.get('state', '')
        if state == 'QUERY_STATE_COMPLETED':
            rows = result.get('result', {}).get('rows', [])
            print(f'DUNE|SUMMARY|rows={len(rows)}')
            for r in rows[:50]:
                sig = r.get('signal_type', '?')
                amt = r.get('amount', '?')
                sym = r.get('symbol', '?')
                frm = str(r.get('addr_from', '?'))[:16]
                to = str(r.get('addr_to', '?'))[:16]
                tx = str(r.get('tx_hash', '?'))[:18]
                bt = str(r.get('block_time', '?'))[:22]
                print(f'DUNE|{sig}|{amt}|{sym}|{frm}|{to}|{tx}|{bt}')
            break
        elif state == 'QUERY_STATE_FAILED':
            err = result.get('error', {}).get('message', 'unknown')
            print(f'DUNE|ERROR|{err}')
            break
        elif state == 'QUERY_STATE_EXPIRED':
            print('DUNE|ERROR|query_expired')
            break
    else:
        print('DUNE|ERROR|poll_timeout')
except Exception as e:
    print(f'DUNE|ERROR|{str(e)[:120]}')
"""
    code = code.replace("__DUNE_KEY__", DUNE_API_KEY)
    code = code.replace("__DUNE_QID__", str(DUNE_QUERY_ID))
    return ssh_run(code, timeout=120)


def fetch_bsc_data():
    """Fetch BSC chain data via Etherscan V2 API.
    NOTE: BSC (chainid=56) requires a PAID Etherscan API plan on free tier.
    Free API access is NOT supported for BSC chain.
    We try the call anyway and handle the 'not supported' error gracefully."""
    code = """import json, urllib.request, sys

ES_KEY = "__BSC_KEY__"
BASE = "https://api.etherscan.io/v2/api?chainid=56"

def jget(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        return json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    except Exception as e:
        return {"error": str(e)}

# --- 1. BSC Gas price ---
try:
    gas = jget(BASE + '&module=gastracker&action=gasoracle&apikey=' + ES_KEY)
    if 'error' in gas:
        print('BSC|GAS|error|' + str(gas['error']))
    elif gas.get('status') == '1':
        r = gas.get('result', {})
        print('BSC|GAS|' + str(r.get('SafeGasPrice','?')) + '|' + str(r.get('ProposeGasPrice','?')) + '|' + str(r.get('FastGasPrice','?')))
    else:
        msg = gas.get('result', 'unknown')
        if 'Free API' in str(msg) or 'upgrade' in str(msg):
            print('BSC|GAS|not_available|free_tier_not_supported')
        else:
            print('BSC|GAS|error|' + str(msg)[:60])
except:
    print('BSC|GAS|not_available')

# --- 2. BSC USDT (BSC-USD) large transfers ---
try:
    usdt = jget(BASE + '&module=account&action=tokentx&contractaddress=0x55d398326f99059fF775485246999027B3197955&sort=desc&offset=10&apikey=' + ES_KEY)
    if 'error' in usdt:
        print('BSC|USDT|error|' + str(usdt['error']))
    elif usdt.get('status') == '1':
        for tx in usdt.get('result', [])[:8]:
            val = int(tx.get('value', '0')) / 1e18
            if val >= 500000:
                print('BSC|USDT|' + str(tx.get('from','?')) + '|' + str(tx.get('to','?')) + '|' + str(int(val)) + '|' + str(tx.get('hash','?')[:16]))
    else:
        msg = usdt.get('result', '')
        if 'Free API' in str(msg) or 'upgrade' in str(msg):
            print('BSC|USDT|not_available|free_tier_not_supported')
        else:
            print('BSC|USDT|empty')
except:
    print('BSC|USDT|not_available')

# --- 3. BSC latest block ---
try:
    block = jget(BASE + '&module=proxy&action=eth_blockNumber&apikey=' + ES_KEY)
    if 'error' in block:
        print('BSC|BLOCK|error|' + str(block['error']))
    elif 'result' in block:
        print('BSC|BLOCK|' + str(int(block['result'], 16)) if isinstance(block['result'], str) else str(block['result']))
    else:
        print('BSC|BLOCK|not_available')
except:
    print('BSC|BLOCK|not_available')

# --- 4. Summary ---
print('BSC|SUMMARY|done')
"""
    code = code.replace("__BSC_KEY__", BSCSCAN_API_KEY)
    return ssh_run(code, timeout=90)


def fetch_arbiscan_data():
    """Fetch Arbitrum chain data via Etherscan V2 API (unified endpoint).
    V2 API is centralized at api.etherscan.io/v2/api?chainid=N — NOT api.arbiscan.io.
    Arbiscan-specific key works on this unified endpoint.
    Arbitrum chainid=42161. Collects: Gas, USDT/USDC large transfers, latest block."""
    code = """import json, urllib.request, sys

ES_KEY = "__ARBI_KEY__"
BASE = "https://api.etherscan.io/v2/api?chainid=42161"

def jget(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        return json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    except Exception as e:
        return {"error": str(e)}

# --- 1. Arbitrum Gas price ---
try:
    gas = jget(BASE + '&module=gastracker&action=gasoracle&apikey=' + ES_KEY)
    if 'error' in gas:
        print('ARBI|GAS|error|' + str(gas['error']))
    elif gas.get('status') == '1':
        r = gas.get('result', {})
        print('ARBI|GAS|' + str(r.get('SafeGasPrice','?')) + '|' + str(r.get('ProposeGasPrice','?')) + '|' + str(r.get('FastGasPrice','?')))
    else:
        print('ARBI|GAS|error|' + str(gas.get('result','unknown'))[:60])
except:
    print('ARBI|GAS|not_available')

# --- 2. Arbitrum USDT large transfers (>$500K) ---
# USDT on Arbitrum: 0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9 (6 decimals)
try:
    usdt = jget(BASE + '&module=account&action=tokentx&contractaddress=0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9&sort=desc&offset=10&apikey=' + ES_KEY)
    if 'error' in usdt:
        print('ARBI|USDT|error|' + str(usdt['error']))
    elif usdt.get('status') == '1':
        for tx in usdt.get('result', [])[:8]:
            val = int(tx.get('value', '0')) / 1e6
            if val >= 500000:
                print('ARBI|USDT|' + str(tx.get('from','?')) + '|' + str(tx.get('to','?')) + '|' + str(int(val)) + '|' + str(tx.get('hash','?')[:16]))
    else:
        print('ARBI|USDT|empty')
except:
    print('ARBI|USDT|not_available')

# --- 3. Arbitrum USDC large transfers (>$500K) ---
# USDC on Arbitrum: 0xaf88d065e77c8cC2239327C5EDb3A432268e5831 (6 decimals)
try:
    usdc = jget(BASE + '&module=account&action=tokentx&contractaddress=0xaf88d065e77c8cC2239327C5EDb3A432268e5831&sort=desc&offset=10&apikey=' + ES_KEY)
    if 'error' in usdc:
        print('ARBI|USDC|error|' + str(usdc['error']))
    elif usdc.get('status') == '1':
        for tx in usdc.get('result', [])[:8]:
            val = int(tx.get('value', '0')) / 1e6
            if val >= 500000:
                print('ARBI|USDC|' + str(tx.get('from','?')) + '|' + str(tx.get('to','?')) + '|' + str(int(val)) + '|' + str(tx.get('hash','?')[:16]))
    else:
        print('ARBI|USDC|empty')
except:
    print('ARBI|USDC|not_available')

# --- 4. Arbitrum latest block (eth_blockNumber via proxy) ---
try:
    block = jget(BASE + '&module=proxy&action=eth_blockNumber&apikey=' + ES_KEY)
    if 'error' in block:
        print('ARBI|BLOCK|error|' + str(block['error']))
    elif 'result' in block:
        bn = int(block['result'], 16) if isinstance(block['result'], str) and block['result'].startswith('0x') else str(block['result'])
        print('ARBI|BLOCK|' + str(bn))
    else:
        print('ARBI|BLOCK|not_available')
except:
    print('ARBI|BLOCK|not_available')

# --- 5. Summary ---
print('ARBI|SUMMARY|done')
"""
    code = code.replace("__ARBI_KEY__", ARBISCAN_API_KEY)
    return ssh_run(code, timeout=90)


def parse_output(output_text):
    """Parse pipe-delimited output into structured data"""
    data = {
        "coingecko_trending": [],
        "coingecko_categories": [],
        "dex_smallcaps": [],
        "whale_signals": [],
        "buy_signals": [],  # BUY|INFLOW (DEX大额买入), BUY|MONEY_IN (稳定币大额转账)
        "bsc_data": [],     # BSC链数据 (Gas/USDT/BNB大额转账)
        "arbi_data": [],    # Arbitrum链数据 (Gas/USDT/USDC大额转账)
        "solscan_data": [],
        "solana_rpc": [],
        "dune_whale": [],
        "errors": []
    }

    for line in output_text.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("|")
        prefix = parts[0]

        if prefix == "CG_TRENDING":
            if parts[1] == "ERROR":
                data["errors"].append(f"CG Trending: {parts[2]}")
            elif parts[1] != "EMPTY":
                data["coingecko_trending"].append({
                    "name": parts[1], "symbol": parts[2],
                    "rank": parts[3], "score": parts[4]
                })
        elif prefix == "CG_CAT":
            if parts[1] == "ERROR":
                data["errors"].append(f"CG Categories: {parts[2]}")
            else:
                data["coingecko_categories"].append({
                    "name": parts[1], "mcap": parts[2],
                    "volume": parts[3], "change": parts[4]
                })
        elif prefix == "DEX":
            if parts[1] == "ERROR":
                data["errors"].append(f"DEX {parts[2]}")
            else:
                data["dex_smallcaps"].append({
                    "chain": parts[1], "symbol": parts[2],
                    "price": parts[3], "volume_24h": parts[4],
                    "liquidity": parts[5], "txns_buy": parts[6],
                    "txns_sell": parts[7], "buy_sell_ratio": parts[8],
                    "change_24h": parts[9],
                    "contract": parts[10] if len(parts) > 10 else ""
                })
        elif prefix == "WHALE":
            if len(parts) > 2:
                data["whale_signals"].append({"type": parts[1], "data": "|".join(parts[2:])})
        elif prefix == "ETH":
            if len(parts) > 2:
                data["whale_signals"].append({"type": f"ETH_{parts[1]}", "data": "|".join(parts[2:])})
        elif prefix == "USDT":
            if len(parts) > 2:
                data["whale_signals"].append({"type": f"USDT_{parts[1]}", "data": "|".join(parts[2:])})
        elif prefix == "SOLSCAN":
            if len(parts) > 2:
                data["solscan_data"].append({"type": parts[1], "data": "|".join(parts[2:])})
        elif prefix == "SOLRPC":
            if len(parts) > 2:
                data["solana_rpc"].append({"type": parts[1], "data": "|".join(parts[2:])})
        elif prefix == "DUNE":
            if len(parts) >= 2:
                data["dune_whale"].append({"type": parts[1], "data": "|".join(parts[2:])})
        elif prefix == "BSC":
            if len(parts) >= 2:
                data["bsc_data"].append({"type": parts[1], "data": "|".join(parts[2:])})
        elif prefix == "ARBI":
            if len(parts) >= 2:
                data["arbi_data"].append({"type": parts[1], "data": "|".join(parts[2:])})
        elif prefix == "BUY":
            if len(parts) > 2:
                if parts[1] in ("INFLOW", "MONEY_IN", "TREASURY", "MONEY_IN_ERROR", "SUMMARY"):
                    data["buy_signals"].append({"type": parts[1], "data": "|".join(parts[2:])})
                else:
                    data["errors"].append(f"Unknown BUY type: {parts[1]}")

    return data


def save_snapshot(data, source_label):
    """Save structured data to JSON for A8 agent to read"""
    now = datetime.now(BJT)

    snapshot = {
        "timestamp": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M"),
        "source": f"AWS ({AWS_HOST}) → {source_label}",
        "coingecko_trending": data["coingecko_trending"],
        "coingecko_categories": data["coingecko_categories"],
        "dex_smallcaps": data["dex_smallcaps"],
        "whale_signals": data["whale_signals"],
        "bsc_data": data.get("bsc_data", []),
        "arbi_data": data.get("arbi_data", []),
        "solscan_data": data["solscan_data"],
        "solana_rpc": data["solana_rpc"],
        "dune_whale": data.get("dune_whale", []),
        "buy_signals": data.get("buy_signals", []),
        "errors": data["errors"],
        "data_quality": "✅ AWS实时API" if not data["errors"] else f"⚠️ 部分受限({len(data['errors'])}处错误)"
    }

    out_path = os.path.join(OUTPUT_DIR, "a8_data_snapshot.json")
    with open(out_path, "w") as f:
        json.dump(snapshot, f, indent=2, default=str)

    return out_path


def print_summary(data):
    """Print a concise summary"""
    now = datetime.now(BJT)
    print(f"[{now.strftime('%H:%M')}] 🚀 A8 AWS数据采集")

    if data["coingecko_trending"]:
        top5 = [c["name"] for c in data["coingecko_trending"][:5]]
        print(f"  📈 CoinGecko Trending: {', '.join(top5)}")
    else:
        print(f"  📈 CoinGecko Trending: 无数据")

    if data["coingecko_categories"]:
        top3 = [c["name"] for c in data["coingecko_categories"][:3]]
        print(f"  🏷️ 热门赛道: {', '.join(top3)}")

    if data["dex_smallcaps"]:
        buy_pressure = [d for d in data["dex_smallcaps"] if float(d["buy_sell_ratio"]) > 1.5]
        print(f"  🔍 DEX小市值: {len(data['dex_smallcaps'])}个 (高买压: {len(buy_pressure)}个)")
        for d in buy_pressure[:5]:
            print(f"    {d['symbol']} — ${d['price']} | 买卖比: {d['buy_sell_ratio']}x | 24h涨跌: {d['change_24h']}%")
    else:
        print(f"  🔍 DEX小市值: 无数据")

    if data["whale_signals"]:
        eth_gas = [s for s in data["whale_signals"] if s["type"] == "ETH_GAS"]
        usdt_tx = [s for s in data["whale_signals"] if s["type"].startswith("USDT_")]
        eth_tx = [s for s in data["whale_signals"] if s["type"].startswith("ETH_TX")]
        print(f"  🐋 巨鲸/链上信号: {len(data['whale_signals'])}条")
        if eth_gas:
            g = eth_gas[0]["data"].split("|")
            print(f"    ⛽ Gas: 安全={g[0] if len(g)>0 else '?'} | 推荐={g[1] if len(g)>1 else '?'} | 快速={g[2] if len(g)>2 else '?'}")
        if usdt_tx:
            print(f"    💵 USDT大额转账: {len(usdt_tx)}笔")
        if eth_tx:
            print(f"    🔷 ETH转账: {len(eth_tx)}笔")
        wallet_tx = [s for s in data["whale_signals"] if s["type"] in ("WALLET", "TOKEN")]
        if wallet_tx:
            print(f"    👛 钱包大额追踪: {len(wallet_tx)}笔")
            for w in wallet_tx[:8]:
                parts = w["data"].split("|")
                label = parts[0] if len(parts) > 0 else "?"
                direction = parts[1] if len(parts) > 1 else "?"
                amount = parts[2] if len(parts) > 2 else "?"
                symbol = parts[3] if len(parts) > 3 else "?"
                arrow = "←" if direction == "in" else "→"
                print(f"      {label} {arrow} {amount} {symbol}")

    if data["solana_rpc"]:
        slots = [s["data"] for s in data["solana_rpc"] if s["type"] == "SLOT" and s["data"] != "error"]
        fees = [s["data"] for s in data["solana_rpc"] if s["type"] == "FEES"]
        votes = [s["data"] for s in data["solana_rpc"] if s["type"] == "VOTES"]
        print(f"  🔮 Solana链上:")
        if slots:
            print(f"    最新Slot: {slots[0]}")
        if fees:
            print(f"    Network Fees: {fees[0]}")
        if votes:
            print(f"    Validators: {votes[0]}")

    if data["solscan_data"]:
        chain = [s["data"] for s in data["solscan_data"] if s["type"] == "CHAIN"]
        print(f"  🔭 Solscan (等待Key升级Pro):")
        if chain:
            print(f"    {chain[0][:80]}")

    if data.get("dune_whale"):
        eth_sigs = [s for s in data["dune_whale"] if "ETH" in s.get("data","")]
        stable_sigs = [s for s in data["dune_whale"] if s.get("type") == "SUMMARY"]
        print(f"  🌊 Dune大额转账监控: {len(data['dune_whale'])}条 ({len([s for s in data['dune_whale'] if s['type']=='ETH>100'])}笔ETH>100 + {len([s for s in data['dune_whale'] if s['type']!='SUMMARY' and 'USDT' in s.get('type','')])}笔USDT/USDC>$500K)")
        for s in data["dune_whale"][:5]:
            if s["type"] == "SUMMARY":
                continue
            parts = s["data"].split("|")
            amt = parts[0] if len(parts) > 0 else "?"
            sym = parts[1] if len(parts) > 1 else "?"
            frm = parts[2] if len(parts) > 2 else "?"
            to = parts[3] if len(parts) > 3 else "?"
            print(f"    [{s['type']}] {amt} {sym} | {frm}→{to}")

    if data.get("bsc_data"):
        bsc_gas = [s["data"] for s in data["bsc_data"] if s["type"] == "GAS" and s["data"] != "error"]
        bsc_usdt = [s["data"] for s in data["bsc_data"] if s["type"] == "USDT" and s["data"] not in ("empty", "error", "not_available")]
        bsc_bnb = [s["data"] for s in data["bsc_data"] if s["type"] == "BNB"]
        bsc_block = [s["data"] for s in data["bsc_data"] if s["type"] == "BLOCK"]
        print(f"  ⛓️ BSC链上数据:")
        if bsc_block:
            print(f"    最新区块: {bsc_block[0]}")
        if bsc_gas:
            parts = bsc_gas[0].split("|")
            print(f"    ⛽ BSC Gas: 安全={parts[0] if len(parts)>0 else '?'} Gwei")
        if bsc_usdt:
            print(f"    💵 BSC USDT大额转账: {len(bsc_usdt)}笔 (>$500K)")
        if bsc_bnb:
            print(f"    💰 BNB大额转账: {len(bsc_bnb)}笔 (>100 BNB)")
            for b in bsc_bnb[:5]:
                parts = b.split("|")
                label = parts[0] if len(parts) > 0 else "?"
                direction = parts[1] if len(parts) > 1 else "?"
                amount = parts[2] if len(parts) > 2 else "?"
                arrow = "←" if direction == "in" else "→"
                print(f"      {label} {arrow} {amount} BNB")

    if data.get("arbi_data"):
        arbi_gas = [s["data"] for s in data["arbi_data"] if s["type"] == "GAS" and s["data"] != "error"]
        arbi_usdt = [s["data"] for s in data["arbi_data"] if s["type"] == "USDT" and s["data"] not in ("empty", "error", "not_available")]
        arbi_usdc = [s["data"] for s in data["arbi_data"] if s["type"] == "USDC" and s["data"] not in ("empty", "error", "not_available")]
        arbi_block = [s["data"] for s in data["arbi_data"] if s["type"] == "BLOCK"]
        print(f"  ⛓️ Arbitrum链上数据:")
        if arbi_block:
            print(f"    最新区块: {arbi_block[0]}")
        if arbi_gas:
            parts = arbi_gas[0].split("|")
            print(f"    ⛽ ARBI Gas: 安全={parts[0] if len(parts)>0 else '?'} Gwei")
        if arbi_usdt:
            print(f"    💵 Arbitrum USDT大额转账: {len(arbi_usdt)}笔 (>$500K)")
        if arbi_usdc:
            print(f"    💵 Arbitrum USDC大额转账: {len(arbi_usdc)}笔 (>$500K)")

    if data.get("buy_signals"):
        inflows = [s for s in data["buy_signals"] if s["type"] == "INFLOW"]
        money_ins = [s for s in data["buy_signals"] if s["type"] == "MONEY_IN"]
        print(f"  💰 买入信号: {len(inflows)}个大额买入代币, {len(money_ins)}条大额转账")
        for s in inflows[:5]:
            parts = s["data"].split("|")
            sym = parts[1] if len(parts) > 1 else "?"
            ch = parts[0] if len(parts) > 0 else "?"
            vol = parts[3] if len(parts) > 3 else "?"
            print(f"    {sym} ({ch}) 24h量={vol}")
        for s in money_ins[:3]:
            parts = s["data"].split("|")
            chain = parts[0] if len(parts) > 0 else "?"
            coin = parts[1] if len(parts) > 1 else "?"
            amt = parts[2] if len(parts) > 2 else "?"
            print(f"    {coin} {amt} on {chain}")

    if data["errors"]:
        for e in data["errors"]:
            print(f"  ⚠️ {e}")


def _fetch_one(label, fetch_fn, key_map):
    """Run one fetch and return (label, merged_dict, errors_list)"""
    result = fetch_fn()
    if "error" in result:
        return (label, {}, [f"{label}失败: {result['error']}"])
    parsed = parse_output(result["data"])
    merged = {}
    for target_key, source_key in key_map.items():
        merged[target_key] = parsed.get(source_key, [])
    return (label, merged, parsed.get("errors", []))


def main():
    now = datetime.now(BJT)
    print(f"=== A8 数据采集: {now.strftime('%Y-%m-%d %H:%M BJT')} ===\n")

    from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as CTimeoutError

    # (label, fetch_fn, {all_data_key: parsed_key})
    fetchers = [
        ("CoinGecko",    fetch_coingecko_trending, {"coingecko_trending": "coingecko_trending", "coingecko_categories": "coingecko_categories"}),
        ("DEX小市值",    fetch_dex_smallcaps,      {"dex_smallcaps": "dex_smallcaps"}),
        ("巨鲸/链上信号", fetch_whale_alerts,       {"whale_signals": "whale_signals"}),
        ("Solscan",      fetch_solscan_data,       {"solscan_data": "solscan_data"}),
        ("Solana链上",   fetch_solana_rpc,         {"solana_rpc": "solana_rpc"}),
        ("大额买入",     fetch_smart_money,        {"buy_signals": "buy_signals"}),
        ("Dune大额转账", fetch_dune_whale,         {"dune_whale": "dune_whale"}),
        ("BSC链上",      fetch_bsc_data,           {"bsc_data": "bsc_data"}),
        ("Arbitrum链上", fetch_arbiscan_data,      {"arbi_data": "arbi_data"}),
    ]

    all_data = {
        "coingecko_trending": [], "coingecko_categories": [],
        "dex_smallcaps": [], "whale_signals": [],
        "solscan_data": [], "solana_rpc": [],
        "dune_whale": [], "bsc_data": [], "arbi_data": [],
        "buy_signals": [], "errors": []
    }

    print(f"[并行] 同时启动{len(fetchers)}个采集模块...")
    pool = ThreadPoolExecutor(max_workers=9)
    fmap = {pool.submit(_fetch_one, label, fn, km): label for label, fn, km in fetchers}
    try:
        for future in as_completed(fmap, timeout=55):
            label, merged, errors = future.result()
            print(f"  ✓ {label} 完成")
            for k, v in merged.items():
                all_data[k].extend(v) if isinstance(all_data.get(k), list) else None
            all_data["errors"].extend(errors)
    except CTimeoutError:
        all_data["errors"].append("并行采集总超时(>55s)，部分模块可能未完成，已强制结束未完成线程")
        # 已完成的future仍然可以拿到结果
        for f in fmap:
            if f.done():
                try:
                    label, merged, errors = f.result()
                    for k, v in merged.items():
                        all_data[k].extend(v) if isinstance(all_data.get(k), list) else None
                    all_data["errors"].extend(errors)
                except Exception:
                    pass
    finally:
        # 强制退出：不等未完成的线程（如慢的SSH/Dune轮询）
        pool.shutdown(wait=False, cancel_futures=True)

    # Save and print
    path = save_snapshot(all_data, "CoinGecko+DexScreener+Etherscan+Solscan+SolanaRPC+SmartMoney+DuneWhale+BSCScan+Arbiscan")
    print()
    print_summary(all_data)
    print(f"\n✅ 已保存: {path}")

    return 0 if not [e for e in all_data["errors"] if "失败" in e] else 1


if __name__ == "__main__":
    sys.exit(main())
