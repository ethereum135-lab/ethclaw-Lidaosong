#!/usr/bin/env python3
"""卖出 KAT 持仓，释放资金用于 Top 3 买入"""
import hmac, hashlib, time, requests, json, os

BASE_DIR = "/Users/lidaosong/zq_web4_trading_system"
AUTH_PATH = os.path.join(BASE_DIR, "config", "auth.json")
TRADES_LOG = os.path.join(BASE_DIR, "audit", "TRADES.md")
ERROR_LOG = os.path.join(BASE_DIR, "audit", "ERRORS.md")

def get_auth():
    with open(AUTH_PATH, 'r') as f:
        data = json.load(f)
        return data['binance']['api_key'], data['binance']['api_secret']

# 使用与引擎完全相同的签名函数（不排序）
def sign_request(params, secret):
    query = '&'.join([f"{k}={v}" for k, v in params.items()])
    signature = hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()
    return signature

def call_signed(method, path, params={}):
    ak, sk = get_auth()
    base = "https://api.binance.com"
    p = params.copy()
    p['timestamp'] = int(time.time() * 1000)
    p['recvWindow'] = 60000
    p['signature'] = sign_request(p, sk)
    headers = {'X-MBX-APIKEY': ak}
    url = f"{base}{path}"
    if method == 'GET':
        r = requests.get(url, headers=headers, params=p, timeout=10)
    else:
        r = requests.post(url, headers=headers, params=p, timeout=10)
    return r.status_code, r.json()

def log_trade(action, coin, qty, price, reason):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    entry = f"| {ts} | {action} | {coin} | {qty:.4f} | {price:.8f} | {reason} |\n"
    os.makedirs(os.path.dirname(TRADES_LOG), exist_ok=True)
    if not os.path.exists(TRADES_LOG):
        with open(TRADES_LOG, 'w') as f:
            f.write("# ZQ 交易日志\n\n| 时间 | 操作 | 币种 | 数量 | 价格 | 原因 |\n| :--- | :--- | :--- | :--- | :--- | :--- |\n")
    with open(TRADES_LOG, 'a') as f:
        f.write(entry)
    print(f"📝 已归档: {action} {coin} {qty} @ {price:.8f} ({reason})")

def log_error(context, detail):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    entry = f"\n### {ts}\n**上下文**: {context}\n**详情**: {detail}\n---\n"
    os.makedirs(os.path.dirname(ERROR_LOG), exist_ok=True)
    if not os.path.exists(ERROR_LOG):
        with open(ERROR_LOG, 'w') as f:
            f.write("# ZQ 错误日志\n\n")
    with open(ERROR_LOG, 'a') as f:
        f.write(entry)

print("=" * 60)
print("  ZQ Web 4.0 — 退出执行 (卖出 KAT)")
print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

# 步骤1：获取余额
print("\n📡 获取实时余额...")
code, bal = call_signed('GET', '/api/v3/account')
print(f"   HTTP {code}")

if code == 418:
    retry = bal.get('retry-after', 300) if isinstance(bal, dict) else 300
    print(f"⛔ 418 封禁，等待 {retry} 秒...")
    time.sleep(int(retry) + 2)
    print("重试中...")
    code, bal = call_signed('GET', '/api/v3/account')
    print(f"   重试 HTTP {code}")

if code != 200:
    print(f"❌ 无法获取余额: HTTP {code} -> {json.dumps(bal)[:300]}")
    log_error("卖出 KAT 阶段1", f"获取余额失败 HTTP {code}: {json.dumps(bal)[:200]}")
    exit(1)

# 解析余额
kat_free = 0
usdt_free = 0
for b in bal['balances']:
    free = float(b['free'])
    locked = float(b['locked'])
    if free > 0 or locked > 0:
        if b['asset'] == 'USDT':
            usdt_free = free
        elif b['asset'] == 'KAT':
            kat_free = free
            kat_locked = locked

print(f"💰 USDT: {usdt_free:.2f}")
print(f"📦 KAT: 可用 {kat_free:.4f}")

if kat_free < 1:
    print("❌ KAT 可用余额不足，无需卖出")
    exit(0)

# 步骤2：执行卖出
print("\n" + "─" * 40)
print("⚡ 市价卖出 KAT")
print("─" * 40)

qty = int(kat_free)  # LOT_SIZE step=1
print(f"数量: {qty} KAT (可用 {kat_free:.4f} 取整)")

# 参考价格
price_r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=KATUSDT", timeout=5)
ref_price = float(price_r.json()['price'])
estimated_value = qty * ref_price
print(f"参考价: ${ref_price:.8f} → 预计释放 ~${estimated_value:.2f}")

code, result = call_signed('POST', '/api/v3/order', {
    'symbol': 'KATUSDT',
    'side': 'SELL',
    'type': 'MARKET',
    'quantity': str(qty)
})

print(f"卖出结果: HTTP {code}")
if code == 200:
    fills = result.get('fills', [])
    if fills:
        total_qty = sum(float(f['qty']) for f in fills)
        total_cost = sum(float(f['qty']) * float(f['price']) for f in fills)
        avg_price = total_cost / total_qty if total_qty > 0 else ref_price
        print(f"\n✅ 卖出成功!")
        print(f"   数量: {total_qty:.4f} KAT")
        print(f"   均价: ${avg_price:.8f}")
        print(f"   价值: ${total_cost:.2f} USDT")
        print(f"   🆔 OrderID: {result.get('orderId')}")
        log_trade('SELL', 'KAT', total_qty, avg_price, '末位淘汰: 共振评分#50(-8), 单币重仓, 强制切换')

        # 确认新余额
        print("\n📡 确认新余额...")
        time.sleep(2)
        code2, bal2 = call_signed('GET', '/api/v3/account')
        if code2 == 200:
            for b in bal2['balances']:
                if b['asset'] == 'USDT':
                    print(f"💰 USDT 新可用: {float(b['free']):.2f}")
    else:
        print(f"✅ 订单成功 (无fills): {json.dumps(result)[:200]}")
        log_trade('SELL', 'KAT', qty, ref_price, '末位淘汰')
else:
    print(f"❌ 卖出失败:")
    print(json.dumps(result, indent=2)[:500])
    log_error("卖出 KAT", f"HTTP {code}: {json.dumps(result)[:300]}")

print("\n" + "=" * 60)
print("  退出执行完毕")
print("=" * 60)
