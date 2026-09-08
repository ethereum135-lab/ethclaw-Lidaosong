#!/usr/bin/env python3
"""Execute WLD buy order (F&G极恐 - USDT×7.5%)"""
import json, hmac, hashlib, time, urllib.request, urllib.error, os

# Load API keys
AUTH_PATH = os.path.expanduser("~/zq_web4_trading_system/config/auth.json")
with open(AUTH_PATH) as f:
    auth = json.load(f)
API_KEY = auth['binance']['api_key']
API_SECRET = auth['binance']['api_secret']

SYMBOL = "WLDUSDT"
SIDE = "BUY"
TYPE = "MARKET"
USDT_AMOUNT = 17.53  # USDT×7.5% of $233.70

def binance_signed_request(method, endpoint, params=None):
    if params is None:
        params = {}
    params['timestamp'] = int(time.time() * 1000)
    params['recvWindow'] = 5000
    query = '&'.join(f'{k}={v}' for k,v in sorted(params.items()))
    signature = hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()
    params['signature'] = signature
    query = '&'.join(f'{k}={v}' for k,v in sorted(params.items()))
    url = f'https://api.binance.com{endpoint}?{query}'
    req = urllib.request.Request(url, method=method, headers={'X-MBX-APIKEY': API_KEY})
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {'error': f'HTTP {e.code}', 'body': e.read().decode()}

# Test account connectivity
print("=== 测试账户连接 ===")
result = binance_signed_request('GET', '/api/v3/account', {'omitZeroBalances': 'true'})
if 'error' in result:
    print(f"❌ 连接失败: {result}")
    exit(1)
print(f"✅ 账户连接成功, 余额数: {len(result.get('balances',[]))}")

# Execute MARKET BUY
print(f"\n=== 执行买入 {SYMBOL} ===")
print(f"金额: ${USDT_AMOUNT:.2f}")

buy_params = {
    'symbol': SYMBOL,
    'side': SIDE,
    'type': 'MARKET',
    'quoteOrderQty': str(round(USDT_AMOUNT, 2)),
    'newOrderRespType': 'FULL'
}

result = binance_signed_request('POST', '/api/v3/order', buy_params)
if 'error' in result:
    print(f"❌ 买入失败: {result}")
    exit(1)

print(f"✅ 买入成功!")
fills = result.get('fills', [])
total_qty = sum(float(f['qty']) for f in fills)
avg_price = sum(float(f['qty'])*float(f['price']) for f in fills) / total_qty if total_qty > 0 else 0
total_cost = sum(float(f['qty'])*float(f['price']) for f in fills)
commission = sum(float(f.get('commission',0)) for f in fills)

print(f"   数量: {total_qty:.2f} WLD")
print(f"   均价: ${avg_price:.4f}")
print(f"   总花费: ${total_cost:.2f}")
print(f"   手续费: {commission:.6f} WLD")
print(f"   OrderID: {result.get('orderId')}")
print(f"   状态: {result.get('status')}")

# Save result for TRADES.md recording
output = {
    'symbol': SYMBOL,
    'side': SIDE,
    'qty': total_qty,
    'price': avg_price,
    'cost': total_cost,
    'commission': commission,
    'order_id': result.get('orderId'),
    'status': result.get('status'),
    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
}
print(f"\n{json.dumps(output, indent=2)}")

# Save to temp for recording
os.makedirs('/tmp/a4_exec/', exist_ok=True)
with open('/tmp/a4_exec/wld_buy_result.json', 'w') as f:
    json.dump(output, f)
print("\n结果已保存到 /tmp/a4_exec/wld_buy_result.json")
