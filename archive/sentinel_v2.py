import hmac
import hashlib
import time
import requests
import json
from datetime import datetime

# 严禁硬编码！从 auth.json 实时动态加载
AUTH_PATH = "/Users/lidaosong/zq_web4_trading_system/config/auth.json"

def get_auth():
    with open(AUTH_PATH, 'r') as f:
        data = json.load(f)
        return data['binance']['api_key'], data['binance']['api_secret']

def call_api(path, method='GET', params={}):
    ak, sk = get_auth()
    base_url = 'https://api.binance.com'
    params['timestamp'] = int(time.time() * 1000)
    query = '&'.join([f"{k}={v}" for k, v in params.items()])
    signature = hmac.new(sk.encode(), query.encode(), hashlib.sha256).hexdigest()
    url = f"{base_url}{path}?{query}&signature={signature}"
    headers = {'X-MBX-APIKEY': ak}
    if method == 'GET':
        return requests.get(url, headers=headers, timeout=5).json()
    return requests.post(url, headers=headers, timeout=5).json()

def sync_and_report():
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🚀 实时监控心跳已激活")
    
    # 1. 实时抓取余额
    account = call_api('/api/v3/account')
    if 'balances' not in account:
        print("❌ API 鉴权失效，无法实时获取余额")
        return
        
    balances = {b['asset']: float(b['free']) + float(b['locked']) for b in account['balances'] if float(b['free']) > 0 or float(b['locked']) > 0}
    usdt = balances.get('USDT', 0.0)
    
    print(f"💰 实时 USDT: {usdt:.2f}")
    
    # 2. 扫描实时持仓成本与盈亏
    print(f"{'币种':<8} | {'实时持仓':<10} | {'成本':<10} | {'现价':<10} | {'盈亏%':<8}")
    print("-" * 55)
    
    for asset, qty in balances.items():
        if asset == 'USDT' or qty < 0.0001: continue
        
        symbol = f"{asset}USDT"
        # 实时价
        price_data = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}").json()
        now_price = float(price_data.get('price', 0))
        
        # 实时拉取最后一次成交作为参考成本
        trades = call_api('/api/v3/myTrades', params={'symbol': symbol, 'limit': 1})
        cost = 0.0
        if isinstance(trades, list) and len(trades) > 0:
            cost = float(trades[0]['price'])
        
        pnl = ((now_price - cost) / cost * 100) if cost > 0 else 0.0
        
        print(f"{asset:<8} | {qty:<10.4f} | {cost:<10.4f} | {now_price:<10.4f} | {pnl:>+6.2f}%")

if __name__ == "__main__":
    while True:
        try:
            sync_and_report()
        except Exception as e:
            print(f"ERROR: {e}")
        time.sleep(30) # 每 30 秒强制抓一次真实数据
