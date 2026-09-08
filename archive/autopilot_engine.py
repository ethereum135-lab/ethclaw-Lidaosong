import hmac
import hashlib
import time
import requests
import json
from datetime import datetime

# ==========================================
# ZQ Web 4.0 战时自动驾驶引擎 (P1 阶段)
# 驱动原则：数据 -> 逻辑 -> 执行 -> 反馈 -> 归档
# ==========================================

AUTH_PATH = "/Users/lidaosong/zq_web4_trading_system/config/auth.json"
LOG_PATH = "/Users/lidaosong/zq_web4_trading_system/strategy_execution.log"

def get_auth():
    with open(AUTH_PATH, 'r') as f:
        data = json.load(f)
        return data['binance']['api_key'], data['binance']['api_secret']

def log_action(msg):
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    with open(LOG_PATH, 'a') as f:
        f.write(line + "\n")

def get_market_signals():
    """
    数据驱动：扫描全网 Top 50 流量币
    """
    try:
        resp = requests.get("https://api.binance.com/api/v3/ticker/24hr", timeout=5).json()
        exclude = ['BTCUSDT', 'ETHUSDT', 'USDCUSDT', 'FDUSDUSDT']
        # 筛选: 成交额排序
        top_50 = sorted([i for i in resp if i['symbol'].endswith('USDT') and i['symbol'] not in exclude], 
                        key=lambda x: float(x['quoteVolume']), reverse=True)[:50]
        
        signals = []
        for c in top_50:
            symbol = c['symbol']
            # 获取 15m RSI
            kl = requests.get(f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=15m&limit=14", timeout=2).json()
            closes = [float(k[4]) for k in kl]
            diff = [closes[i]-closes[i-1] for i in range(1, len(closes))]
            up = sum(d for d in diff if d > 0); down = abs(sum(d for d in diff if d < 0))
            rsi = 100 - (100 / (1 + (up/down if down!=0 else 100)))
            
            # 数据阈值：RSI < 30 (深度超卖) 
            if rsi < 30:
                signals.append({'symbol': symbol, 'rsi': rsi})
        return signals
    except Exception as e:
        log_action(f"数据读取异常: {e}")
        return []

def autonomous_run():
    ak, sk = get_auth()
    log_action("🔥 全自动驾驶引擎已接管，数据驱动中...")
    
    while True:
        try:
            # 1. 检测余额
            ts = int(time.time() * 1000)
            s_acc = hmac.new(sk.encode(), f"timestamp={ts}".encode(), hashlib.sha256).hexdigest()
            acc = requests.get(f"https://api.binance.com/api/v3/account?timestamp={ts}&signature={s_acc}", 
                               headers={'X-MBX-APIKEY': ak}).json()
            usdt = next((float(b['free']) for b in acc['balances'] if b['asset'] == 'USDT'), 0)
            
            # 2. 扫描机会
            signals = get_market_signals()
            
            if usdt >= 10 and signals:
                # 3. 执行: 只要数据达标，直接开火，不问老李
                target = signals[0] # 选 RSI 最低的
                symbol = target['symbol']
                log_action(f"🚀 数据确认! {symbol} RSI={target['rsi']:.1f}. 立即切入 $40 (或最大余额).")
                
                trade_qty = min(usdt * 0.98, 40.0) # 单笔上限40U或剩余全仓
                srv_time = requests.get("https://api.binance.com/api/v3/time").json()['serverTime']
                p = {'symbol': symbol, 'side': 'BUY', 'type': 'MARKET', 'quoteOrderQty': round(trade_qty, 2), 'timestamp': srv_time, 'recvWindow': 5000}
                q = '&'.join([f"{k}={v}" for k, v in p.items()])
                s = hmac.new(sk.encode(), q.encode(), hashlib.sha256).hexdigest()
                res = requests.post(f"https://api.binance.com/api/v3/order?{q}&signature={s}", headers={'X-MBX-APIKEY': ak}).json()
                
                if 'orderId' in res:
                    log_action(f"✅ 执行成功! 订单号: {res['orderId']}")
                else:
                    log_action(f"❌ 执行失败! 原因: {res.get('msg')}")
            
            # 持仓监控与自动化收割 (止盈止损)
            # ... 此处后续接入 PNL 模块 ...
            
            time.sleep(60) # 每分钟强制扫描全网一次
            
        except Exception as e:
            log_action(f"循环异常: {e}")
            time.sleep(30)

if __name__ == "__main__":
    autonomous_run()
