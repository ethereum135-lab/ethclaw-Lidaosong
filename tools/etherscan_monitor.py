#!/usr/bin/env python3
"""
etherscan_monitor.py — 链上大额转账监控
=======================================
通过Etherscan API监控链上大额转账，提供卖出参考信号。
大额转账进交易所 = 潜在抛压
大额转账出交易所 = 潜在吸筹

用法：
  python3 tools/etherscan_monitor.py              # 运行监控
  python3 tools/etherscan_monitor.py --check     # 单次查询
"""

import json
import os
import urllib.request
import ssl
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUTH_FILE = os.path.join(PROJECT_ROOT, 'config', 'auth.json')

# 已知交易所热钱包地址（部分）
EXCHANGE_WALLETS = {
    'binance_hot': '0x28C6c06298d514Db089934071355E5743bf883d9',
    'binance_cold': '0x3f5CE5FBFe3E9af3971dD833D26bA9b5C936f0bE',
    'coinbase_hot': '0x71660c4005BA85c37ccec55d0C4493E66Fe775d3',
    'okx_hot': '0x6cc5F688a315f3dC28A7781717a9A798a59fDA7b',
    'bybit_hot': '0x1Db92e2EeBC8E0c075a02BeA49a2935BcD2dFCF4',
}

def get_auth():
    with open(AUTH_FILE) as f:
        return json.load(f).get('etherscan', {}).get('api_key', '')

def etherscan_api(params):
    """调用Etherscan V2 API"""
    key = get_auth()
    if not key:
        return {'error': 'No API key'}
    
    base = 'https://api.etherscan.io/v2/api'
    params['chainid'] = 1
    params['apikey'] = key
    qs = '&'.join([f'{k}={v}' for k, v in params.items()])
    url = f'{base}?{qs}'
    
    ctx = ssl.create_default_context()
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        res = urllib.request.urlopen(req, timeout=15, context=ctx)
        return json.loads(res.read())
    except Exception as e:
        return {'error': str(e)}

def get_eth_balance(address):
    """查地址ETH余额"""
    data = etherscan_api({
        'module': 'account',
        'action': 'balance',
        'address': address
    })
    if data.get('status') == '1':
        return int(data['result']) / 1e18
    return 0

def get_large_tx(address, min_eth=100):
    """查地址的大额交易"""
    data = etherscan_api({
        'module': 'account',
        'action': 'txlist',
        'address': address,
        'sort': 'desc',
        'limit': 20
    })
    
    txs = []
    if data.get('status') == '1' and isinstance(data.get('result'), list):
        for tx in data['result'][:10]:
            value = int(tx.get('value', 0)) / 1e18
            if value >= min_eth:
                txs.append({
                    'hash': tx['hash'][:10],
                    'from': tx['from'][:10],
                    'to': tx['to'][:10],
                    'value_eth': round(value, 2),
                    'time': datetime.fromtimestamp(int(tx.get('timeStamp', 0))).isoformat()
                })
    return txs

def main():
    key = get_auth()
    if not key:
        print('❌ 没有Etherscan API key')
        return
    
    print(f'=== Etherscan 链上监控 ===')
    print(f'API Key: {key[:10]}...')
    
    # 测试连接
    data = etherscan_api({'module': 'stats', 'action': 'ethprice'})
    if data.get('status') == '1':
        eth_usd = json.loads(data['result'])['ethusd'] if isinstance(data['result'], str) else data['result'].get('ethusd', '?')
        print(f'✅ 连接成功 | ETH: ${eth_usd}')
    else:
        print(f'❌ 连接失败: {data}')
        return
    
    # 查交易所热钱包大额转账
    print(f'\n=== 交易所热钱包大额转账（>= 100 ETH） ===')
    for name, addr in EXCHANGE_WALLETS.items():
        txs = get_large_tx(addr, min_eth=100)
        if txs:
            for tx in txs[:3]:
                tv = tx['value_eth']
                tt = tx['time']
                direction = '⬆️ 转出' if tx['to'] != addr[:10] else '⬇️ 转入'
                print(f'  {name:15s} {direction} {tv:>8.0f} ETH @ {tt}')
        else:
            print(f'  {name:15s} 最近无大额转账')
    
    # 查当前最热的大额转账
    print(f'\n=== 最近大额转账示例 ===')
    whale_addrs = ['0xF977814e90dA44bFA03b6295A0616a897441aceC',  # Binance 7
                   '0xbe0eb53f46cd790cd13851d5eff43d12404d33e8']
    for addr in whale_addrs[:1]:
        bal = get_eth_balance(addr)
        print(f'  地址{addr[:10]}... ETH余额: {bal:.2f}')

if __name__ == '__main__':
    main()
