import hmac
import hashlib
import time
import requests
import json
from datetime import datetime

# 核心：430U -> 1M U Phase 1 落地引擎
AUTH_PATH = "/Users/lidaosong/zq_web4_trading_system/config/auth.json"

def get_auth():
    with open(AUTH_PATH, 'r') as f:
        data = json.load(f)
        return data['binance']['api_key'], data['binance']['api_secret']

def hunter_loop():
    ak, sk = get_auth()
    while True:
        try:
            # 1. 抓取 Top 50 流量币
            resp = requests.get("https://api.binance.com/api/v3/ticker/24hr", timeout=5).json()
            exclude = ['BTCUSDT', 'ETHUSDT', 'USDCUSDT', 'FDUSDUSDT']
            top_50 = sorted([i for i in resp if i['symbol'].endswith('USDT') and i['symbol'] not in exclude], 
                            key=lambda x: float(x['quoteVolume']), reverse=True)[:50]
            
            # 2. 同步服务器时间并检查余额
            srv_time = requests.get("https://api.binance.com/api/v3/time").json()['serverTime']
            q_acc = f"timestamp={srv_time}"
            s_acc = hmac.new(sk.encode(), q_acc.encode(), hashlib.sha256).hexdigest()
            acc = requests.get(f"https://api.binance.com/api/v3/account?{q_acc}&signature={s_acc}", 
                               headers={'X-MBX-APIKEY': ak}, timeout=5).json()
            
            usdt = next((float(b['free']) for b in acc['balances'] if b['asset'] == 'USDT'), 0)
            
            if usdt >= 10:
                for c in top_50:
                    symbol = c['symbol']
                    # 3. 监控 1min 极短线黄金坑
                    kl = requests.get(f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=2", timeout=2).json()
                    if len(kl) < 2: continue
                    drop = (float(kl[-1][4]) - float(kl[-2][4])) / float(kl[-2][4])
                    
                    if drop < -0.01: # 跌幅 > 1%
                        # 4. 立即落地执行
                        p_order = {
                            'symbol': symbol, 'side': 'BUY', 'type': 'MARKET', 
                            'quoteOrderQty': round(usdt, 2), 'timestamp': srv_time, 'recvWindow': 5000
                        }
                        q_order = '&'.join([f"{k}={v}" for k, v in p_order.items()])
                        s_order = hmac.new(sk.encode(), q_order.encode(), hashlib.sha256).hexdigest()
                        res = requests.post(f"https://api.binance.com/api/v3/order?{q_order}&signature={s_order}", 
                                            headers={'X-MBX-APIKEY': ak}, timeout=5).json()
                        print(f"[{datetime.now()}] 🎯 成交: {symbol} | 结果: {json.dumps(res)}")
                        time.sleep(10) # 冷却
                        break
            
            time.sleep(5) # 5秒一扫，绝不空转
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(30)

if __name__ == "__main__":
    hunter_loop()
