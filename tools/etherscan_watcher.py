#!/usr/bin/env python3
"""
ZQ Etherscan链上监控器 — 聪明钱数据源
用途：对NBZ候选币做链上验证，监控大额转账和持仓变化

与early_signal_detector的关系：
  early_signal_detector = 发现候选币（价格/成交量信号）
  本工具            = 验证候选币（链上数据——大额转账/鲸鱼活动）

运行频率：每30分钟（配合NBZ早信号周期）
"""

import json
import os
import time
import urllib.request
import ssl
from datetime import datetime, timezone

# ====== 配置 ======
AUTH_PATH = os.path.expanduser("~/zq_web4_trading_system/config/auth.json")
NBZ_FINDINGS = os.path.expanduser("~/zq_web4_trading_system/agents/nbz/findings.md")
OUTPUT_FILE = os.path.expanduser("~/zq_web4_trading_system/agents/nbz/chain_data.md")

ETHERSCAN_API = "https://api.etherscan.io/v2/api"
COINGECKO_API = "https://api.coingecko.com/api/v3"

# 阈值
LARGE_TX_THRESHOLD_USD = 100000  # 大额转账>$100K
WHALE_BALANCE_THRESHOLD = 500000  # 鲸鱼持仓>$500K
TRANSFER_SURGE_THRESHOLD = 2.0   # 转账数翻倍


def log(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{ts}] {msg}")


def get_etherscan_key():
    with open(AUTH_PATH) as f:
        auth = json.load(f)
    return auth.get("etherscan", {}).get("api_key", "")


def fetch_json(url, timeout=10):
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=timeout)
        return json.loads(resp.read().decode())
    except Exception as e:
        log(f"⚠️ 获取失败: {url[:80]} — {e}")
        return None


def get_coin_contract_info(coin_id):
    """查询CoinGecko获取币种合约地址"""
    url = f"{COINGECKO_API}/coins/{coin_id}?localization=false&tickers=false&community_data=false&developer_data=false&sparkline=false"
    data = fetch_json(url)
    if not data:
        return None
    
    # 找Ethereum合约地址
    platforms = data.get("platforms", {}) or {}
    eth_contract = platforms.get("ethereum", "")
    bsc_contract = platforms.get("binance-smart-chain", "")
    
    return {
        "eth_contract": eth_contract,
        "bsc_contract": bsc_contract,
        "categories": data.get("categories", []),
        "description": (data.get("description", {}) or {}).get("en", "")[:200],
    }


def get_erc20_transfer_count(contract_address, api_key):
    """获取ERC-20代币24h转账次数"""
    # 获取最近1000笔转账的时间戳
    url = (
        f"{ETHERSCAN_API}?chainid=1&module=account&action=tokentx"
        f"&contractaddress={contract_address}"
        f"&sort=desc&offset=1000&page=1"
        f"&apikey={api_key}"
    )
    data = fetch_json(url)
    if not data or data.get("status") != "1":
        return None
    
    txs = data.get("result", [])
    if not txs:
        return 0, 0, 0, []
    
    now = time.time()
    # 24h前
    cutoff_24h = now - 86400
    cutoff_48h = now - 172800
    
    count_24h = sum(1 for tx in txs if int(tx.get("timeStamp", 0)) > cutoff_24h)
    count_48h = sum(1 for tx in txs if cutoff_48h < int(tx.get("timeStamp", 0)) <= cutoff_24h)
    
    # 大额转账（>$100K）
    large_txs = []
    for tx in txs:
        ts = int(tx.get("timeStamp", 0))
        if ts <= cutoff_24h:
            break
        value = float(tx.get("value", 0)) / 10 ** int(tx.get("tokenDecimal", 18))
        usd_value = value * 0  # 需要价格，用CoinGecko匹配
        if value > 100000:  # 代币数量大额（非USD）
            large_txs.append({
                "from": tx.get("from", "")[:10] + "...",
                "to": tx.get("to", "")[:10] + "...",
                "value": value,
                "hash": tx.get("hash", "")[:10] + "...",
            })
    
    return count_24h, count_48h, len(large_txs), large_txs


def get_current_findings_coins():
    """从NBZ findings.md提取当前候选币列表"""
    if not os.path.exists(NBZ_FINDINGS):
        return []
    
    with open(NBZ_FINDINGS) as f:
        content = f.read()
    
    import re
    coins = set()
    # 找 ### 行（币名）
    for match in re.finditer(r'### [📈⚡]+\s+(\S+)', content):
        coin = match.group(1).strip()
        if coin:
            coins.add(coin.lower())
    
    return list(coins)


def generate_chain_report(chain_data):
    """生成链上数据报告"""
    lines = []
    lines.append("## ⛓️ 链上数据验证（Etherscan）")
    lines.append("")
    lines.append(f"*更新: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*")
    lines.append("")
    
    if not chain_data:
        lines.append("*候选币非ERC-20代币或Etherscan无法查询*")
        lines.append("")
        return "\n".join(lines)
    
    for coin, data in chain_data.items():
        if not data:
            continue
        
        lines.append(f"### {coin.upper()}")
        
        contract = data.get("eth_contract", "")
        if contract:
            lines.append(f"- 合约: `{contract[:15]}...{contract[-5:]}`")
        else:
            lines.append("- ❌ 非ERC-20代币")
            continue
        
        transfers = data.get("transfers", {})
        if transfers:
            count_24h = transfers.get("count_24h", 0)
            count_48h = transfers.get("count_48h", 0)
            large_count = transfers.get("large_tx_count", 0)
            
            change = ""
            if count_48h > 0:
                ratio = count_24h / count_48h if count_48h > 0 else 0
                if ratio > TRANSFER_SURGE_THRESHOLD:
                    change = f" ⚡转账数翻{ratio:.1f}x!"
            
            lines.append(f"- 转账: {count_24h}/24h | {count_48h}/48h{change}")
            if large_count > 0:
                lines.append(f"- 🐋 大额转账({large_count}笔)")
                for ltx in transfers.get("large_txs", [])[:3]:
                    lines.append(f"  - {ltx['from']} → {ltx['to']}: {ltx['value']:,.0f} 枚")
        
        lines.append("")
    
    return "\n".join(lines)


def main():
    log("⛓️ NBZ链上验证启动")
    
    api_key = get_etherscan_key()
    if not api_key:
        log("❌ 无Etherscan API Key")
        return
    
    # 1. 获取候选币列表
    coins = get_current_findings_coins()
    log(f"📋 当前候选币: {coins}")
    
    if not coins:
        log("💤 无候选币，跳过链上验证")
        return
    
    # 2. 逐个查询链上数据（每次间隔1.5秒避免限流）
    chain_data = {}
    for i, coin in enumerate(coins):
        if i > 0:
            time.sleep(1.5)
        
        log(f"🔎 查询 {coin}的链上数据...")
        
        # 获取合约信息
        info = get_coin_contract_info(coin)
        if not info:
            continue
        
        eth_contract = info.get("eth_contract", "")
        if not eth_contract:
            log(f"   {coin} 非ERC-20代币")
            chain_data[coin] = {"eth_contract": None}
            continue
        
        log(f"   合约: {eth_contract[:15]}...{eth_contract[-5:]}")
        
        # 获取转账统计
        time.sleep(1.5)  # Etherscan限流
        tx_data = get_erc20_transfer_count(eth_contract, api_key)
        
        transfers = None
        if tx_data:
            count_24h, count_48h, large_count, large_txs = tx_data
            transfers = {
                "count_24h": count_24h,
                "count_48h": count_48h,
                "large_tx_count": large_count,
                "large_txs": large_txs[:5],
            }
            log(f"   转账: {count_24h}/24h, 大额: {large_count}笔")
        
        chain_data[coin] = {
            "eth_contract": eth_contract,
            "categories": info.get("categories", []),
            "transfers": transfers,
        }
    
    # 3. 生成报告，追加到findings.md
    report = generate_chain_report(chain_data)
    log(f"✅ 链上验证完成")
    log(report)
    
    # 追加到findings.md
    os.makedirs(os.path.dirname(NBZ_FINDINGS), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        f.write(report)
    
    log(f"   报告: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
