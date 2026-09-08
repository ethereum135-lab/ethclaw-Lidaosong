#!/usr/bin/env python3
"""
全市场跟随引擎 v6 — 因果链执行版 (2026-08-16 老李: 策略本身错, 换方向不修补)
=====================================================================
方向: Agent=全市场扫描+跟随不预测 (08-15 老李核心纠正)
不是自创策略 — 是把"为什么涨/为什么跌"的因果链变成执行规则:

买(因果②③): 聪明钱进场后、散户FOMO前
  条件: 全市场24h涨3-15%(刚启动) + 量>$2M + 价>$1 + 价>EMA20(趋势确认)
卖(因果⑥): 大资金出货信号
  ① 高位放量滞涨(近24h高点 + 量放大但价不涨 = 在卖)
  ② 移动止盈(从高点回撤8% = 吃满波段)
  ③ 硬止损(-8% = 认错)
仓位: $30×2 = $60 (集中火力)
"""
import json, urllib.request, urllib.parse, hashlib, hmac, ssl, time, os

# 本地配置文件
LOCAL_CFG = os.path.expanduser('~/.hermes/keys/binance.json')
AWS_CFG = '/home/ubuntu/zq_web4_trading_system/config/auth.json'

def load_cfg():
    for p in [LOCAL_CFG, AWS_CFG]:
        try:
            with open(p) as f:
                d = json.load(f)
            if 'binance' in d:
                d = d['binance']
            if d.get('api_key') and d.get('api_secret'):
                return d
        except:
            continue
    raise Exception("未找到币安API配置")

cfg = load_cfg()
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
BASE = 'https://api.binance.com'
STATE_FILE = os.path.expanduser('~/zq_web4_trading_system/data/follow_engine/state.json')
LOG_FILE = os.path.expanduser('~/zq_web4_trading_system/logs/follow_engine.log')
os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)

POSITION_USDT = 30.0
MAX_POSITIONS = 2
STOP_LOSS_PCT = 0.08
TRAIL_PCT = 0.08
MIN_VOLUME_USD = 2000000
MIN_GAIN = 3.0
MAX_GAIN = 15.0
PRICE_MIN = 1.0

def log(msg):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')

def public(path):
    req = urllib.request.Request(f'{BASE}{path}', headers={'User-Agent': 'M'})
    with urllib.request.urlopen(req, context=CTX, timeout=15) as r:
        return json.loads(r.read())

def signed(path, params=None):
    params = params or {}
    params['timestamp'] = int(time.time() * 1000)
    qs = urllib.parse.urlencode(params)
    sig = hmac.new(cfg['api_secret'].encode(), qs.encode(), hashlib.sha256).hexdigest()
    if path.startswith('/api/v3/order'):
        data = qs.encode() + f'&signature={sig}'.encode()
        req = urllib.request.Request(f'{BASE}{path}', data=data, method='POST',
                                     headers={'X-MBX-APIKEY': cfg['api_key'], 'Content-Type': 'application/x-www-form-urlencoded'})
    else:
        req = urllib.request.Request(f'{BASE}{path}?{qs}&signature={sig}', headers={'X-MBX-APIKEY': cfg['api_key']})
    try:
        with urllib.request.urlopen(req, context=CTX, timeout=15) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {'_error': f'HTTP {e.code}', '_msg': e.read().decode()[:300]}

def ema(vals, period):
    if len(vals) < period: return None
    k = 2 / (period + 1)
    e = sum(vals[:period]) / period
    for v in vals[period:]: e = v * k + e * (1 - k)
    return e

def scan_movers():
    """全市场扫描: 刚启动的币(因果②③)"""
    data = public('/api/v3/ticker/24hr')
    usdt = [d for d in data if d['symbol'].endswith('USDT') and all(ord(c) < 128 for c in d['symbol'])]
    movers = []
    for d in usdt:
        try:
            chg = float(d['priceChangePercent'])
            vol = float(d['quoteVolume'])
            price = float(d['lastPrice'])
            if MIN_GAIN <= chg <= MAX_GAIN and vol >= MIN_VOLUME_USD and price >= PRICE_MIN:
                movers.append((d['symbol'], chg, vol, price))
        except:
            continue
    movers.sort(key=lambda x: x[1], reverse=True)
    return movers

def analyze(symbol):
    """返回: price, ema20, high24, vol_ratio, stalled(出货信号)"""
    try:
        k = public(f'/api/v3/klines?symbol={symbol}&interval=1h&limit=30')
        if not k or len(k) < 25:
            return None
        closes = [float(x[4]) for x in k]
        vols = [float(x[5]) for x in k]
        highs = [float(x[2]) for x in k]
        price = closes[-1]
        e20 = ema(closes, 20)
        if e20 is None:
            return None
        vol_avg = sum(vols[-21:-1]) / 20 if sum(vols[-21:-1]) > 0 else 1
        vol_ratio = vols[-1] / vol_avg
        high24 = max(highs[-24:]) if len(highs) >= 24 else max(highs)
        near_high = price >= high24 * 0.995
        stalled = near_high and vol_ratio >= 1.5 and price <= highs[-1]
        return {'price': price, 'ema20': e20, 'high24': high24,
                'vol_ratio': vol_ratio, 'stalled': stalled}
    except:
        return None

def buy(symbol, usdt_amount):
    price = float(public(f'/api/v3/ticker/price?symbol={symbol}')['price'])
    if price <= 0 or price < PRICE_MIN: return None, "价格过低"
    qty = usdt_amount / price
    info = public(f'/api/v3/exchangeInfo?symbol={symbol}')
    step = 1.0
    for s in info['symbols']:
        for f in s['filters']:
            if f['filterType'] == 'LOT_SIZE':
                step = float(f['stepSize']); break
    if step >= 1:
        qty = int(qty // step) * step
        q_str = str(int(qty))
    else:
        decimals = len(str(step).split('.')[-1])
        qty = int(qty / step) * step
        q_str = f"{qty:.{decimals}f}"
    r = signed('/api/v3/order', {'symbol': symbol, 'side': 'BUY', 'type': 'MARKET', 'quantity': q_str})
    if 'orderId' in r:
        return qty, f"买入{q_str}@{price}"
    return None, r.get('_msg', r)

def sell(symbol, qty):
    info = public(f'/api/v3/exchangeInfo?symbol={symbol}')
    step = 1.0; min_notional = 5.0
    for s in info['symbols']:
        for f in s['filters']:
            if f['filterType'] == 'LOT_SIZE': step = float(f['stepSize'])
            if f['filterType'] == 'NOTIONAL': min_notional = float(f['minNotional'])
    if step >= 1:
        q_str = str(int(qty))
    else:
        decimals = len(str(step).split('.')[-1])
        q_str = f"{float(qty):.{decimals}f}"
    r = signed('/api/v3/order', {'symbol': symbol, 'side': 'SELL', 'type': 'MARKET', 'quantity': q_str})
    if 'orderId' in r:
        return True, f"卖出{q_str}"
    price = float(public(f'/api/v3/ticker/price?symbol={symbol}')['price'])
    total_val = price * qty
    if total_val < min_notional:
        return False, f"仓位${total_val:.2f}<最小${min_notional}"
    r2 = signed('/api/v3/order', {'symbol': symbol, 'side': 'SELL', 'type': 'MARKET', 'quoteOrderQty': f"{total_val:.2f}"})
    if 'orderId' in r2:
        return True, f"金额卖出${total_val:.2f}"
    return False, r2.get('_msg', r2)

def main():
    state = {'positions': [], 'closed': []}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f: state = json.load(f)
        except: pass

    log("=" * 50)
    log("全市场跟随引擎 v6 启动 (因果链执行)")
    positions = state['positions']

    # 1. 持仓管理: 三卖出信号(因果⑥)
    for p in positions[:]:
        sym = p['symbol']
        a = analyze(sym)
        if not a: continue
        cur = a['price']
        high = max(p.get('high', p['buy_price']), cur)
        p['high'] = high
        pnl_pct = (cur - p['buy_price']) / p['buy_price']
        reason = None
        if a['stalled']:
            reason = f"⑥出货(高位放量滞涨) pnl={pnl_pct*100:+.1f}%"
        elif cur <= p['buy_price'] * (1 - STOP_LOSS_PCT):
            reason = f"止损(-8%) pnl={pnl_pct*100:+.1f}%"
        elif cur <= high * (1 - TRAIL_PCT):
            reason = f"移动止盈(回撤8%) pnl={pnl_pct*100:+.1f}%"
        if reason:
            ok, msg = sell(sym, p['qty'])
            if ok:
                profit = (cur - p['buy_price']) * p['qty']
                log(f"🛑 卖出 {sym}: {reason} 盈亏${profit:+.2f}")
                state['closed'].append({'symbol': sym, 'buy': p['buy_price'], 'sell': cur,
                                        'pnl': profit, 'reason': reason,
                                        'time': time.strftime('%Y-%m-%d %H:%M')})
                positions.remove(p)
            else:
                log(f"❌ 卖出失败 {sym}: {msg}")

    # 2. 全市场扫描+跟随(因果②③)
    if len(positions) < MAX_POSITIONS:
        acc = signed('/api/v3/account')
        usdt_free = 0
        for b in acc['balances']:
            if b['asset'] == 'USDT': usdt_free = float(b['free'])
        movers = scan_movers()
        log(f"📡 扫描: {len(movers)}个启动币, USDT可用${usdt_free:.2f}")
        for sym, chg, vol, price in movers:
            if len(positions) >= MAX_POSITIONS: break
            if any(p['symbol'] == sym for p in positions): continue
            a = analyze(sym)
            if not a: continue
            if a['price'] > a['ema20'] and usdt_free >= POSITION_USDT:
                qty, msg = buy(sym, POSITION_USDT)
                if qty:
                    log(f"✅ 买入 {sym}: {msg} 24h涨{chg:+.1f}% ← 因果②③(启动+趋势)")
                    positions.append({'symbol': sym, 'qty': qty, 'buy_price': a['price'],
                                      'buy_time': time.strftime('%Y-%m-%d %H:%M'), 'high': a['price']})
                    usdt_free -= POSITION_USDT
                else:
                    log(f"❌ 买入失败 {sym}: {msg}")
            else:
                log(f"🔍 {sym} 涨{chg:+.1f}% 但价<EMA20, 不跟")

    state['positions'] = positions
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)
    log(f"当前持仓: {len(positions)} | 累计平仓: {len(state['closed'])}")

if __name__ == '__main__':
    main()
