#!/usr/bin/env python3
"""
均值回归策略机器人 v1.0 — RSI + 布林带
策略核心: 在15分钟周期上识别真正的超卖/超买
  - 买入: RSI(14) < 35 且 价格 <= 布林下轨 → 超卖反弹
  - 卖出: RSI(14) >= 65 或 价格 >= 布林中轨 → 回归均值
  - 止损: F&G联动动态 (极度恐惧-9%, 贪婪-4%)
  - 量比过滤: >2.0x不买 (爆量接盘)
  - 仓位: 每笔$40, 最多3个同时持仓
"""
import json, os, time, hmac, hashlib, urllib.request, urllib.parse, ssl, math
from datetime import datetime, timezone, timedelta

BASE = os.path.expanduser('~/zq_web4_trading_system')
CFG = json.load(open(os.path.join(BASE, 'config/auth.json')))['binance']
AK = CFG['api_key']
SK = CFG['api_secret']
LOG = os.path.join(BASE, 'logs/mean_rev.log')
STATE_PATH = os.path.join(BASE, 'data/mean_rev_state.json')
BJT = timezone(timedelta(hours=8))

# ─── 策略参数 ───
SCAN_POOL_SIZE = 20          # 动态获取24h成交量前20名
MIN_24H_VOLUME = 10          # 24h成交额 > $10M (流动性保障)
MAX_PRICE = 500              # 价格 < $500 (确保$40能买够最小单位)
MIN_PRICE = 0.1              # 价格 > $0.1 (排除垃圾币)
EXCLUDE_STABLECOINS = ['USDT', 'USDC', 'FDUSD', 'TUSD', 'BUSD', 'DAI', 'USDP', 'EUR', 'GBP', 'AEUR']
TIMEFRAME = '15m'
RSI_PERIOD = 14
BB_PERIOD = 20
BB_STD = 2.0
RSI_BUY_THRESHOLD = 35      # RSI < 35 才买
RSI_SELL_THRESHOLD = 65     # RSI > 65 就卖
VOLUME_RATIO_MAX = 2.0     # 量比 > 2.0 不买
POSITION_USDT = 40.0        # 每笔 $40
MAX_POSITIONS = 3           # 最多3个同时持仓
STOP_LOSS_DEFAULT = -0.05  # 默认 -5%
FG_API = "https://api.alternative.me/fng/?limit=1"
FG_STOP_MAP = {
    "extreme_greed": -0.03,
    "greed": -0.04,
    "neutral": -0.05,
    "fear": -0.06,
    "extreme_fear": -0.09,
}

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def log(msg):
    ts = datetime.now(BJT).strftime('%m-%d %H:%M:%S')
    line = '[%s] %s' % (ts, msg)
    print(line)
    with open(LOG, 'a') as f:
        f.write(line + '\n')


def signed(path, params, method='GET'):
    params['timestamp'] = int(time.time() * 1000)
    q = urllib.parse.urlencode(params)
    sig = hmac.new(SK.encode(), q.encode(), hashlib.sha256).hexdigest()
    url = 'https://api.binance.com' + path + '?' + q + '&signature=' + sig
    req = urllib.request.Request(url, method=method)
    req.add_header('X-MBX-APIKEY', AK)
    try:
        return json.loads(urllib.request.urlopen(req, timeout=15, context=ctx).read())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode())
        except:
            return {'code': e.code, 'msg': 'HTTP%d' % e.code}
    except Exception as e:
        return {'code': -1, 'msg': str(e)[:120]}


def get_klines(symbol, interval='15m', limit=50):
    url = 'https://api.binance.com/api/v3/klines?symbol=%s&interval=%s&limit=%d' % (symbol, interval, limit)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'mean-rev/1.0'})
        data = json.loads(urllib.request.urlopen(req, timeout=10, context=ctx).read())
        closes = [float(k[4]) for k in data]
        highs = [float(k[2]) for k in data]
        lows = [float(k[3]) for k in data]
        vols = [float(k[5]) for k in data]
        return closes, highs, lows, vols
    except:
        return [], [], [], []


def get_top_coins():
    """动态获取24h成交额前20的币种（排除稳定币）"""
    try:
        url = 'https://api.binance.com/api/v3/ticker/24hr'
        req = urllib.request.Request(url, headers={'User-Agent': 'mean-rev/1.0'})
        data = json.loads(urllib.request.urlopen(req, timeout=15, context=ctx).read())
        coins = []
        for t in data:
            sym = t.get('symbol', '')
            if not sym.endswith('USDT'):
                continue
            base = sym[:-4]
            if base in EXCLUDE_STABLECOINS:
                continue
            price = float(t.get('lastPrice', 0))
            quote_vol = float(t.get('quoteVolume', 0))
            if price < MIN_PRICE or price > MAX_PRICE:
                continue
            if quote_vol < MIN_24H_VOLUME * 1e6:
                continue
            change_24h = float(t.get('priceChangePercent', 0))
            coins.append({
                'symbol': sym,
                'coin': base,
                'price': price,
                'volume_m': quote_vol / 1e6,
                'change_24h': change_24h,
            })
        coins.sort(key=lambda x: x['volume_m'], reverse=True)
        top = coins[:SCAN_POOL_SIZE]
        log('动态扫描池: %d个币 (从%d个候选中筛选)' % (len(top), len(coins)))
        return top
    except Exception as e:
        log('动态币种获取失败: %s, 回退到默认列表' % str(e)[:80])
        return [
            {'symbol': 'SOLUSDT', 'coin': 'SOL', 'price': 100, 'volume_m': 500, 'change_24h': 0},
            {'symbol': 'AVAXUSDT', 'coin': 'AVAX', 'price': 7, 'volume_m': 300, 'change_24h': 0},
            {'symbol': 'LINKUSDT', 'coin': 'LINK', 'price': 12, 'volume_m': 200, 'change_24h': 0},
        ]


def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50.0
    gains = []
    losses = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def calc_bb(closes, period=20, std_mult=2.0):
    if len(closes) < period:
        return None, None, None
    slice_c = closes[-period:]
    sma = sum(slice_c) / period
    variance = sum((x - sma) ** 2 for x in slice_c) / period
    std = math.sqrt(variance)
    return sma + std_mult * std, sma, sma - std_mult * std


def calc_volume_ratio(vols):
    if len(vols) < 21:
        return 1.0
    current = vols[-1]
    avg = sum(vols[-21:-1]) / 20
    if avg <= 0:
        return 1.0
    return current / avg


def fetch_fear_greed():
    try:
        req = urllib.request.Request(FG_API, headers={'User-Agent': 'mean-rev/1.0'})
        data = json.loads(urllib.request.urlopen(req, timeout=8, context=ctx).read())
        d = data.get('data', [{}])[0]
        return int(d.get('value', 50)), d.get('value_classification', 'Neutral')
    except:
        return None, None


def get_dynamic_stop():
    fg_val, fg_label = fetch_fear_greed()
    if fg_val is None:
        return STOP_LOSS_DEFAULT
    if fg_val > 75:
        key = 'extreme_greed'
    elif fg_val > 55:
        key = 'greed'
    elif fg_val > 45:
        key = 'neutral'
    elif fg_val > 25:
        key = 'fear'
    else:
        key = 'extreme_fear'
    stop = FG_STOP_MAP[key]
    log('F&G=%d(%s) → 止损%.1f%%' % (fg_val, fg_label, stop * 100))
    return stop


def load_state():
    try:
        return json.load(open(STATE_PATH))
    except:
        return {'positions': [], 'daily_pnl': 0, 'date': datetime.now(BJT).strftime('%Y-%m-%d')}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    json.dump(state, open(STATE_PATH, 'w'), indent=2)


def get_precision(symbol):
    try:
        url = 'https://api.binance.com/api/v3/exchangeInfo?symbol=' + symbol
        d = json.loads(urllib.request.urlopen(url, timeout=10, context=ctx).read())
        step = None
        minnot = 5.0
        for f in d['symbols'][0]['filters']:
            if f['filterType'] == 'LOT_SIZE':
                step = float(f['stepSize'])
            elif f['filterType'] == 'NOTIONAL':
                minnot = float(f['minNotional'])
        step_dec = len(str(step).rstrip('0').split('.')[-1]) if '.' in str(step) else 0
        return step_dec, minnot
    except:
        return 6, 5.0


def get_balance():
    acct = signed('/api/v3/account', {})
    bal = {}
    if 'balances' in acct:
        for b in acct['balances']:
            v = float(b['free'])
            if v > 0.0001:
                bal[b['asset']] = v
    return bal


def get_price(symbol):
    try:
        url = 'https://api.binance.com/api/v3/ticker/price?symbol=' + symbol
        t = json.loads(urllib.request.urlopen(url, timeout=5, context=ctx).read())
        return float(t['price'])
    except:
        return None


def buy(coin, usdt_amount):
    symbol = coin + 'USDT'
    price = get_price(symbol)
    if not price:
        return None
    step_dec, minnot = get_precision(symbol)
    qty = round(usdt_amount / price, step_dec)
    if qty * price < minnot:
        log('  %s 金额太小 $%.2f < 最小$%.1f' % (coin, qty * price, minnot))
        return None
    r = signed('/api/v3/order', {
        'symbol': symbol, 'side': 'BUY', 'type': 'MARKET',
        'quoteOrderQty': str(round(usdt_amount, 2)),
    }, method='POST')
    if r.get('orderId'):
        fills = r.get('fills', [])
        exec_price = float(fills[0]['price']) if fills else price
        exec_qty = sum(float(f['qty']) for f in fills) if fills else qty
        log('  ✅ 买入 %s $%.2f @ $%.4f (qty=%s)' % (coin, usdt_amount, exec_price, exec_qty))
        return {'entry_price': exec_price, 'qty': exec_qty, 'time': datetime.now(BJT).isoformat()}
    else:
        log('  ❌ 买入失败 %s: %s' % (coin, r.get('msg', r)))
        return None


def sell(coin, qty):
    symbol = coin + 'USDT'
    step_dec, _ = get_precision(symbol)
    qty = round(qty, step_dec)
    r = signed('/api/v3/order', {
        'symbol': symbol, 'side': 'SELL', 'type': 'MARKET',
        'quantity': str(qty),
    }, method='POST')
    if r.get('orderId'):
        fills = r.get('fills', [])
        exec_price = float(fills[0]['price']) if fills else get_price(symbol)
        log('  ✅ 卖出 %s qty=%s @ $%.4f' % (coin, qty, exec_price))
        return exec_price
    else:
        log('  ❌ 卖出失败 %s: %s' % (coin, r.get('msg', r)))
        return None


def run():
    log('═══ 均值回归机器人 v1.0 启动 ═══')
    state = load_state()
    today = datetime.now(BJT).strftime('%Y-%m-%d')
    if state.get('date') != today:
        state['date'] = today
        state['daily_pnl'] = 0

    bal = get_balance()
    usdt_free = bal.get('USDT', 0)
    log('余额: USDT=$%.2f' % usdt_free)

    dynamic_stop = get_dynamic_stop()
    positions = state.get('positions', [])
    active_count = len(positions)

    # ─── 1. 检查持仓 → 是否该卖 ───
    for pos in positions[:]:
        coin = pos['coin']
        symbol = coin + 'USDT'
        price = get_price(symbol)
        if not price:
            continue
        entry = pos['entry_price']
        pnl_pct = (price - entry) / entry
        pnl_usd = (price - entry) * pos['qty']
        pos['current_price'] = price
        pos['pnl_pct'] = pnl_pct
        pos['pnl_usd'] = pnl_usd

        # 获取RSI和BB判断是否该卖
        closes, _, _, _ = get_klines(symbol, TIMEFRAME, 50)
        if not closes:
            continue
        rsi = calc_rsi(closes, RSI_PERIOD)
        _, bb_mid, _ = calc_bb(closes, BB_PERIOD, BB_STD)

        should_sell = False
        reason = ''
        if pnl_pct <= dynamic_stop:
            should_sell = True
            reason = '止损 %.1f%% ≤ %.1f%%' % (pnl_pct * 100, dynamic_stop * 100)
        elif rsi >= RSI_SELL_THRESHOLD:
            should_sell = True
            reason = 'RSI超买 %.0f ≥ %d' % (rsi, RSI_SELL_THRESHOLD)
        elif bb_mid and price >= bb_mid:
            should_sell = True
            reason = '价格回到布林中轨 $%.4f ≥ $%.4f' % (price, bb_mid)
        elif pnl_pct >= 0.03:
            should_sell = True
            reason = '盈利3%%+主动止盈 %.1f%%' % (pnl_pct * 100)

        if should_sell:
            log('📤 卖出信号 %s: %s (PnL=%.2f%% $%.2f)' % (coin, reason, pnl_pct * 100, pnl_usd))
            exec_price = sell(coin, pos['qty'])
            if exec_price:
                realized_pnl = (exec_price - entry) * pos['qty']
                state['daily_pnl'] += realized_pnl
                positions.remove(pos)
                active_count -= 1
                log('  已实现盈亏: $%.2f (今日累计: $%.2f)' % (realized_pnl, state['daily_pnl']))

    # ─── 2. 扫描币种 → 是否该买 ───
    if active_count < MAX_POSITIONS and usdt_free >= POSITION_USDT:
        scan_pool = get_top_coins()
        log('扫描 %d 个币种寻找超卖信号...' % len(scan_pool))
        signals = []
        for item in scan_pool:
            coin = item['coin']
            symbol = item['symbol']
            closes, highs, lows, vols = get_klines(symbol, TIMEFRAME, 50)
            if len(closes) < 25:
                continue
            rsi = calc_rsi(closes, RSI_PERIOD)
            bb_upper, bb_mid, bb_lower = calc_bb(closes, BB_PERIOD, BB_STD)
            vol_ratio = calc_volume_ratio(vols)
            price = closes[-1]

            # 检查是否已持有
            if any(p['coin'] == coin for p in positions):
                continue

            signal = False
            reasons = []

            if rsi < RSI_BUY_THRESHOLD:
                signal = True
                reasons.append('RSI=%.0f<%d' % (rsi, RSI_BUY_THRESHOLD))

            if bb_lower and price <= bb_lower:
                signal = True
                reasons.append('价格$%.4f≤布林下轨$%.4f' % (price, bb_lower))

            if vol_ratio > VOLUME_RATIO_MAX:
                signal = False
                reasons.append('量比%.1fx>%.0fx(爆量不买)' % (vol_ratio, VOLUME_RATIO_MAX))

            pnl_potential = 0
            if bb_mid:
                pnl_potential = (bb_mid - price) / price

            # 只输出有信号的或RSI<45的（减少日志量）
            if signal or rsi < 45:
                log('  %s: RSI=%.0f 价格=$%.4f BB下=$%.4f 中=$%.4f 量比=%.2fx 24h=%+.1f%% %s' % (
                    coin, rsi, price, bb_lower or 0, bb_mid or 0, vol_ratio,
                    item['change_24h'], '→ 信号!' if signal else ''))
            if signal:
                fg_val, _ = fetch_fear_greed()
                if fg_val is not None and fg_val < 25:
                    log('  ⛔ F&G=%d 极度恐惧, 不开新仓' % fg_val)
                    continue
                signals.append({
                    'coin': coin,
                    'rsi': rsi,
                    'price': price,
                    'bb_lower': bb_lower,
                    'bb_mid': bb_mid,
                    'vol_ratio': vol_ratio,
                    'pnl_potential': pnl_potential,
                    'reason': ', '.join(reasons),
                })

        # 按RSI从低到高排序，最超卖的先买
        signals.sort(key=lambda x: x['rsi'])
        for sig in signals:
            if active_count >= MAX_POSITIONS:
                break
            if usdt_free < POSITION_USDT:
                break
            log('📥 买入信号 %s: %s (预期盈利空间%.1f%%)' % (
                sig['coin'], sig['reason'], sig['pnl_potential'] * 100))
            result = buy(sig['coin'], POSITION_USDT)
            if result:
                positions.append({
                    'coin': sig['coin'],
                    'entry_price': result['entry_price'],
                    'qty': result['qty'],
                    'time': result['time'],
                    'rsi_at_entry': sig['rsi'],
                    'bb_lower_at_entry': sig['bb_lower'],
                    'bb_mid_at_entry': sig['bb_mid'],
                })
                active_count += 1
                usdt_free -= POSITION_USDT
    else:
        if active_count >= MAX_POSITIONS:
            log('持仓已满 %d/%d, 不开新仓' % (active_count, MAX_POSITIONS))
        elif usdt_free < POSITION_USDT:
            log('USDT不足 $%.2f < $%.2f' % (usdt_free, POSITION_USDT))

    state['positions'] = positions
    save_state(state)

    # ─── 总结 ───
    total_pnl = sum(p.get('pnl_usd', 0) for p in positions)
    log('持仓: %d/%d | 浮盈: $%.2f | 今日已实现: $%.2f' % (
        active_count, MAX_POSITIONS, total_pnl, state.get('daily_pnl', 0)))
    for p in positions:
        log('  %s: 入场$%.4f 现价$%.4f PnL=%.2f%% ($%.2f)' % (
            p['coin'], p['entry_price'], p.get('current_price', 0),
            p.get('pnl_pct', 0) * 100, p.get('pnl_usd', 0)))
    log('═══ 循环完成 ═══')


if __name__ == '__main__':
    run()
