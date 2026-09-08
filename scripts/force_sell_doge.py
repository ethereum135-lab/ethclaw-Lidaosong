#!/usr/bin/env python3
"""紧急硬止损：卖出 DOGE（P&L -3.19%，超过 -2% 硬止损线）"""
import hmac, hashlib, time, requests, json, os, sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUTH_PATH = os.path.join(BASE_DIR, "config", "auth.json")
TRADES_LOG = os.path.join(BASE_DIR, "audit", "TRADES.md")
TRACE_LOG = os.path.join(BASE_DIR, "audit", "EXECUTION_TRACE.log")

def get_auth():
    with open(AUTH_PATH, 'r') as f:
        data = json.load(f)
        return data['binance']['api_key'], data['binance']['api_secret']

def sign_request(params, secret):
    query = '&'.join([f"{k}={v}" for k, v in params.items()])
    return hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()

def call_api(method='GET', path='', params={}):
    ak, sk = get_auth()
    base = "https://api.binance.com"
    params['timestamp'] = int(time.time() * 1000)
    params['recvWindow'] = 60000
    params['signature'] = sign_request(params, sk)
    headers = {'X-MBX-APIKEY': ak}
    url = f"{base}{path}"
    try:
        if method == 'GET':
            r = requests.get(url, headers=headers, params=params, timeout=10)
        else:
            r = requests.post(url, headers=headers, params=params, timeout=10)
        return r.status_code, r.json()
    except Exception as e:
        return 0, {"error": str(e)}

def lot_size_floor(qty, step_size):
    step = float(step_size)
    precision = len(str(step).split('.')[-1]) if '.' in str(step) else 0
    return float(int(qty / step) * step)

print("=" * 60)
print("  DOGE 硬止损强行卖出")
print(f"  时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

# Step 1: Check current balance
print("\n📋 步骤1: 查询持仓...")
code, bal = call_api('GET', '/api/v3/account')
if code != 200:
    print(f"❌ 余额查询失败 HTTP {code}: {bal}")
    sys.exit(1)

doge_free = 0
for b in bal['balances']:
    if b['asset'] == 'DOGE':
        doge_free = float(b['free'])
        break

print(f"   DOGE 可用: {doge_free}")

# Step 2: Get exchange info for LOT_SIZE
print("\n📋 步骤2: 获取交易对规则...")
r = requests.get("https://api.binance.com/api/v3/exchangeInfo?symbol=DOGEUSDT", timeout=10)
info = r.json()
step_size = "1"
for f in info['symbols'][0]['filters']:
    if f['filterType'] == 'LOT_SIZE':
        step_size = f['stepSize']
        print(f"   LOT_SIZE stepSize: {step_size}")

qty = lot_size_floor(min(doge_free, 1909), step_size)
print(f"   卖出数量: {qty} DOGE")

# Step 3: Get current price
print("\n📋 步骤3: 获取当前市价...")
r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=DOGEUSDT", timeout=10)
px = float(r.json()['price'])
print(f"   当前价: ${px}")

# Step 4: Execute sell
print("\n📋 步骤4: 执行市价卖出...")
params = {
    'symbol': 'DOGEUSDT',
    'side': 'SELL',
    'type': 'MARKET',
    'quantity': qty
}
code, result = call_api('POST', '/api/v3/order', params)

if code == 200:
    print(f"✅ 卖出成功!")
    print(f"   OrderID: {result.get('orderId', 'N/A')}")
    fills = result.get('fills', [])
    if fills:
        avg_price = sum(float(f['price']) * float(f['qty']) for f in fills) / sum(float(f['qty']) for f in fills)
        total_qty = sum(float(f['qty']) for f in fills)
        total_quote = sum(float(f['price']) * float(f['qty']) for f in fills)
        print(f"   成交均价: ${avg_price:.8f}")
        print(f"   成交数量: {total_qty}")
        print(f"   成交金额: ${total_quote:.2f}")
    
    # Log trade
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    entry = f"| {ts} | SELL | DOGE | {total_qty:.4f} | {avg_price:.8f} | 硬止损: P&L -3.19% < -2% |\n"
    os.makedirs(os.path.dirname(TRADES_LOG), exist_ok=True)
    if not os.path.exists(TRADES_LOG):
        with open(TRADES_LOG, 'w') as f:
            f.write("# ZQ 交易日志\n\n| 时间 | 操作 | 币种 | 数量 | 价格 | 原因 |\n| :--- | :--- | :--- | :--- | :--- | :--- |\n")
    with open(TRADES_LOG, 'a') as f:
        f.write(entry)
    print(f"📝 已归档到 TRADES.md")
    
    # Update trace
    trace_line = f"[{ts}] HARD_STOP_SELL | DOGE | qty={total_qty} @ ${avg_price:.4f} | P&L -3.19% reached -2% hard stop | OrderID: {result.get('orderId', 'N/A')}\n"
    with open(TRACE_LOG, 'a') as f:
        f.write(trace_line)
    print(f"📝 已归档到 EXECUTION_TRACE.log")
    
else:
    print(f"❌ 卖出失败 HTTP {code}")
    print(f"   错误: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
print(f"\n{'=' * 60}")
print("  DOGE 卖出流程完成")
print(f"{'=' * 60}")
