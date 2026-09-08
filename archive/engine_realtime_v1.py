#!/usr/bin/env python3
"""
ZQ Web 4.0 实时执行引擎 v1.0
430U -> 1M U Phase 1 核心引擎
30分钟节点 | 共振评分 | 三币切换 | 铁律风控

使用方式:
    python3 engine_realtime_v1.py          # 单次执行
    python3 engine_realtime_v1.py --loop   # 持续循环（每30分钟）
"""
import hmac, hashlib, time, requests, json, os, sys

# ─── 配置文件路径 ───
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUTH_PATH = os.path.join(BASE_DIR, "config", "auth.json")
ORACLE_PATH = os.path.join(BASE_DIR, "config", "data_sources", "COMPLETE_50_ORACLE.json")
TRADES_LOG = os.path.join(BASE_DIR, "audit", "TRADES.md")
ERROR_LOG = os.path.join(BASE_DIR, "audit", "ERRORS.md")

# ─── API 核心 ───
def get_auth():
    with open(AUTH_PATH, 'r') as f:
        data = json.load(f)
        return data['binance']['api_key'], data['binance']['api_secret']

def sign_request(params, secret):
    query = '&'.join([f"{k}={v}" for k, v in params.items()])
    signature = hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()
    return signature

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

# ─── 辅助工具 ───
def lot_size_floor(qty, step_size):
    """处理 LOT_SIZE 精度"""
    step = float(step_size)
    precision = len(str(step).split('.')[-1]) if '.' in str(step) else 0
    return float(int(qty / step) * step)

def log_trade(action, coin, qty, price, reason):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    entry = f"| {ts} | {action} | {coin} | {qty:.4f} | {price:.8f} | {reason} |\n"
    os.makedirs(os.path.dirname(TRADES_LOG), exist_ok=True)
    if not os.path.exists(TRADES_LOG):
        with open(TRADES_LOG, 'w') as f:
            f.write("# ZQ 交易日志\n\n| 时间 | 操作 | 币种 | 数量 | 价格 | 原因 |\n| :--- | :--- | :--- | :--- | :--- | :--- |\n")
    with open(TRADES_LOG, 'a') as f:
        f.write(entry)
    print(f"📝 已归档: {action} {coin} {qty} @ {price} ({reason})")

def log_error(context, detail):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    entry = f"\n### {ts}\n**上下文**: {context}\n**详情**: {detail}\n---\n"
    os.makedirs(os.path.dirname(ERROR_LOG), exist_ok=True)
    if not os.path.exists(ERROR_LOG):
        with open(ERROR_LOG, 'w') as f:
            f.write("# ZQ 错误日志\n\n")
    with open(ERROR_LOG, 'a') as f:
        f.write(entry)

# ─── 核心逻辑 ───

def check_ban(status_code, response):
    """检查是否 418 封禁，返回剩余秒数"""
    if status_code == 418:
        retry_after = response.get('retry-after', 300) if isinstance(response, dict) else 300
        print(f"⛔ API 封禁中 (418)，剩余 {retry_after} 秒")
        return int(retry_after)
    return 0

def get_balance():
    """获取实时余额"""
    code, data = call_api('GET', '/api/v3/account')
    if code == 200:
        usdt_free = 0
        holdings = []
        for b in data['balances']:
            free = float(b['free'])
            locked = float(b['locked'])
            if free > 0 or locked > 0:
                if b['asset'] == 'USDT':
                    usdt_free = free + locked
                else:
                    holdings.append({'asset': b['asset'], 'free': free, 'locked': locked})
        return {'usdt': usdt_free, 'holdings': holdings, 'raw': data}
    return {'error': f"HTTP {code}: {data}"}

def resonance_scan():
    """
    共振评分扫描
    如果 REST API 被封，回退到公共行情数据
    """
    print("\n🔍 开始共振评分扫描...")

    # 获取成交额排名
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/24hr", timeout=10)
        if r.status_code != 200:
            print(f"❌ 公共行情返回 {r.status_code}")
            return []
        tickers = r.json()
    except Exception as e:
        print(f"❌ 公共行情请求失败: {e}")
        return []

    # 过滤 USDT 交易对，排除稳定币
    exclude = ['BTCUSDT', 'ETHUSDT', 'USDCUSDT', 'FDUSDUSDT', 'TUSDUSDT', 'DAIUSDT']
    candidates = [t for t in tickers if t['symbol'].endswith('USDT') and t['symbol'] not in exclude]

    # 按成交额排序取前50
    candidates.sort(key=lambda x: float(x['quoteVolume']), reverse=True)
    top50 = candidates[:50]

    print(f"📊 Top 50 币种成交额排名:")
    print(f"{'排名':<4} {'币种':<10} {'成交额(万USDT)':<16} {'24h涨幅%':<10} {'评分':<6}")
    print("-" * 50)

    scores = []
    for i, c in enumerate(top50):
        symbol = c['symbol'].replace('USDT', '')
        vol = float(c['quoteVolume']) / 1e6
        chg = float(c['priceChangePercent'])

        # 基础评分：按成交额排名线性映射 0-100
        rank_score = max(0, 100 - i * 2)
        # 价格变化加分（3-10%涨幅加分，暴涨>20%减分）
        change_score = 0
        if 3 <= chg <= 10:
            change_score = 20
        elif 1 <= chg < 3:
            change_score = 10
        elif -2 <= chg < 1:
            change_score = 0
        elif -5 <= chg < -2:
            change_score = -10
        elif chg < -5:
            change_score = -20
        elif chg > 10:
            change_score = -15  # 已涨太多，高位风险

        final = rank_score + change_score

        scores.append({
            'symbol': symbol,
            'rank': i + 1,
            'volume': vol,
            'change': chg,
            'rank_score': rank_score,
            'change_score': change_score,
            'final_score': final
        })
        print(f"{i+1:<4} {symbol:<10} {vol:<16.2f} {chg:<+10.2f} {final:<6}")

    scores.sort(key=lambda x: x['final_score'], reverse=True)
    return scores

def select_top3(scores):
    """选择 Top 3 币种，按 50/30/20 分配"""
    if len(scores) < 3:
        print("❌ 评分结果不足3个币种，无法执行")
        return None

    top = scores[:3]
    print(f"\n🏆 Top 3 选币结果:")
    for t in top:
        print(f"   #{t['rank']} {t['symbol']} -> 评分 {t['final_score']} (成交额 {t['volume']:.2f}万 | 涨幅 {t['change']:+.2f}%)")
    return top

def execute_trades(top3, usdt_total):
    """
    执行交易
    50/30/20 分配
    """
    if not top3 or usdt_total < 15:
        print(f"\n❌ 资金不足 (USDT: {usdt_total:.2f}) 或无法选币，跳过执行")
        return

    allocations = [0.5, 0.3, 0.2]
    labels = ['Leader', 'Volume', 'Sentiment']

    print(f"\n💰 可用 USDT: {usdt_total:.2f}")
    print(f"📋 执行分配:")
    print(f"{'仓位':<10} {'币种':<10} {'比例':<8} {'金额(USDT)':<12}")
    print("-" * 40)

    for i, (coin, alloc) in enumerate(zip(top3, allocations)):
        amount = usdt_total * alloc
        if amount < 10:
            print(f"  {labels[i]:<10} {coin['symbol']:<10} {alloc*100:<8.0f}% {amount:<12.2f} (❌ 金额<$10，跳过)")
            continue

        print(f"  {labels[i]:<10} {coin['symbol']:<10} {alloc*100:<8.0f}% {amount:<12.2f}")

        # 获取交易对信息（LOT_SIZE）
        symbol = f"{coin['symbol']}USDT"
        try:
            r = requests.get(f"https://api.binance.com/api/v3/exchangeInfo?symbol={symbol}", timeout=5)
            if r.status_code != 200:
                print(f"    ❌ 获取 {symbol} 交易规则失败")
                log_error(f"买入 {symbol}", f"exchangeInfo 返回 {r.status_code}")
                continue

            info = r.json()
            filters = {f['filterType']: f for f in info['symbols'][0]['filters']}
            step_size = filters['LOT_SIZE']['stepSize']
            min_qty = float(filters['LOT_SIZE']['minQty'])
            min_notional = float(filters.get('MIN_NOTIONAL', {}).get('minNotional', 10))

            # 获取当前价格
            price_r = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}", timeout=5)
            if price_r.status_code != 200:
                print(f"    ❌ 获取 {symbol} 价格失败")
                continue
            price = float(price_r.json()['price'])

            qty = amount / price
            if qty < min_qty:
                print(f"    ❌ 数量 {qty:.8f} 小于最小交易量 {min_qty}")
                continue

            qty_floor = lot_size_floor(qty, step_size)
            order_value = qty_floor * price
            if order_value < min_notional:
                print(f"    ❌ 订单价值 {order_value:.2f} 低于最小名义值 {min_notional}")
                continue

            print(f"    现价: {price:.8f} | 数量: {qty_floor:.8f} | 价值: {order_value:.2f} USDT")

            # 市价买入
            code, result = call_api('POST', '/api/v3/order', {
                'symbol': symbol,
                'side': 'BUY',
                'type': 'MARKET',
                'quoteOrderQty': f"{amount:.2f}"  # 按金额买
            })

            if code == 200:
                fills = result.get('fills', [])
                avg_price = sum(float(f['price']) * float(f['qty']) for f in fills) / sum(float(f['qty']) for f in fills) if fills else price
                exec_qty = sum(float(f['qty']) for f in fills)
                print(f"    ✅ 买入成功: {exec_qty:.4f} {coin['symbol']} @ {avg_price:.8f}")
                print(f"    🆔 OrderID: {result.get('orderId')}")
                log_trade('BUY', coin['symbol'], exec_qty, avg_price, f"共振评分 #{coin['rank']}")
            else:
                print(f"    ❌ 买入失败: HTTP {code} -> {result}")
                log_error(f"买入 {symbol}", f"HTTP {code}: {json.dumps(result)[:200]}")

        except Exception as e:
            print(f"    ❌ 买入异常: {e}")
            log_error(f"买入 {symbol}", str(e))

        # 每单间隔 3 秒
        time.sleep(3)

def main():
    print(f"\n{'='*50}")
    print(f"  ZQ Web 4.0 实时执行引擎 v1.0")
    print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")

    # 步骤 1：获取余额
    print(f"\n{'─'*40}")
    print(f"步骤 1/4: 获取实时余额")
    print(f"{'─'*40}")
    bal = get_balance()
    if 'error' in bal:
        print(f"❌ 余额获取失败: {bal['error']}")
        usdt = 0
        print("⏳ 继续使用公共行情扫描（跳过交易执行）")
    else:
        usdt = bal['usdt']
        print(f"💰 USDT 可用: {usdt:.2f}")
        if bal['holdings']:
            print(f"📦 当前持仓:")
            for h in bal['holdings']:
                print(f"   {h['asset']}: {h['free']:.6f} (锁定: {h['locked']:.6f})")
        else:
            print(f"📦 当前持仓: 无")
    print(f"💰 USDT 可用: {usdt:.2f}")

    # 步骤 2：共振评分
    print(f"\n{'─'*40}")
    print(f"步骤 2/4: 共振评分扫描")
    print(f"{'─'*40}")
    scores = resonance_scan()
    if not scores:
        print("❌ 评分失败")
        return

    # 步骤 3：选币
    print(f"\n{'─'*40}")
    print(f"步骤 3/4: 选币与分配")
    print(f"{'─'*40}")
    top3 = select_top3(scores)

    # 步骤 4：退出检查（暂略，下一版实现）
    print(f"\n{'─'*40}")
    print(f"步骤 4/4: 退出检查")
    print(f"{'─'*40}")
    if bal['holdings']:
        for h in bal['holdings']:
            symbol = f"{h['asset']}USDT"
            try:
                r = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}", timeout=5)
                if r.status_code == 200:
                    price = float(r.json()['price'])
                    print(f"   {h['asset']}: {price:.8f}")
            except:
                pass
    else:
        print("   无持仓，跳过退出检查")

    # 执行交易
    if top3 and usdt >= 30:
        print(f"\n{'─'*40}")
        print(f"⚡ 执行交易")
        print(f"{'─'*40}")
        execute_trades(top3, usdt)
    else:
        if usdt < 30:
            print(f"\n⏸️ USDT ({usdt:.2f}) < $30，跳过买入，等待持仓释放资金")

    print(f"\n{'='*50}")
    print(f"  ✅ 执行完毕")
    print(f"{'='*50}")

if __name__ == '__main__':
    if '--loop' in sys.argv:
        print("🔄 循环模式启动，每30分钟执行一次")
        while True:
            main()
            print(f"\n⏳ 等待 30 分钟... ({time.strftime('%H:%M:%S')})")
            time.sleep(1800)
    else:
        main()
