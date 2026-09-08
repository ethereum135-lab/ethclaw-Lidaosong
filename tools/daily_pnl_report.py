#!/usr/bin/env python3
"""
AWS本地每日成交报告 — 21:00生成, 复盘只需读文件不需SSH审批
输出: /home/ubuntu/zq_web4_trading_system/data/daily_pnl_report.json
"""
import json, urllib.request, urllib.parse, hashlib, hmac, ssl, time, os
from datetime import datetime, timezone, timedelta

cfg = json.load(open('/home/ubuntu/zq_web4_trading_system/config/auth.json'))['binance']
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
BASE = 'https://api.binance.com'
def signed(path, params=None):
    params = params or {}
    params['timestamp'] = int(time.time() * 1000)
    qs = urllib.parse.urlencode(params)
    sig = hmac.new(cfg['api_secret'].encode(), qs.encode(), hashlib.sha256).hexdigest()
    req = urllib.request.Request(f'{BASE}{path}?{qs}&signature={sig}', headers={'X-MBX-APIKEY': cfg['api_key']})
    with urllib.request.urlopen(req, context=CTX, timeout=15) as r:
        return json.loads(r.read())
def public(path):
    req = urllib.request.Request(f'{BASE}{path}', headers={'User-Agent': 'M'})
    with urllib.request.urlopen(req, context=CTX, timeout=15) as r:
        return json.loads(r.read())

# ===== 1. 总资产 =====
acc = signed('/api/v3/account')
tickers = {x['symbol']: float(x['price']) for x in public('/api/v3/ticker/price')}
usdt = 0; total = 0
holdings = []
for b in acc['balances']:
    qty = float(b['free']) + float(b['locked'])
    if qty <= 0: continue
    if b['asset'] == 'USDT': usdt = qty
    else:
        sym = f'{b["asset"]}USDT'
        if sym in tickers:
            v = qty * tickers[sym]; total += v
            if v > 0.5: holdings.append({'asset': b['asset'], 'value': round(v,2)})
total += usdt

# ===== 2. 24h成交 =====
day_start = int((time.time() - 24*3600) * 1000)
buys = 0; sells = 0; sell_usd = 0.0; buy_usd = 0.0; fee_usd = 0.0
sells_detail = []
# myTrades需要symbol, 遍历所有持仓币+网格币
symbols_to_check = list(set([f'{h["asset"]}USDT' for h in holdings] + ['ETHUSDT']))
# 加上跟随引擎持仓币
try:
    with open('/home/ubuntu/zq_web4_trading_system/data/follow_engine/state.json') as f:
        st0 = json.load(f)
    for p in st0.get('positions', []):
        symbols_to_check.append(p['symbol'])
except:
    pass
for sym in set(symbols_to_check):
    try:
        trades = signed('/api/v3/myTrades', {'symbol': sym, 'limit': 50})
    except:
        continue
    for t in trades:
        if t['time'] < day_start: continue
        q = float(t['quoteQty'])
        fee = float(t['commission'])
        fee_usd += fee * (tickers.get(f'{t["commissionAsset"]}USDT', 1) if t['commissionAsset'] != 'USDT' else 1)
        if t['isBuyer']:
            buys += 1; buy_usd += q
        else:
            sells += 1; sell_usd += q
            sells_detail.append({'sym': t['symbol'], 'qty': t['qty'], 'price': t['price'],
                                 't': time.strftime('%H:%M', time.localtime(t['time']/1000))})

# ===== 3. 跟随引擎state =====
follow = {'positions': 0, 'today_closed': []}
try:
    with open('/home/ubuntu/zq_web4_trading_system/data/follow_engine/state.json') as f:
        st = json.load(f)
    follow['positions'] = len(st.get('positions', []))
    today_str = time.strftime('%Y-%m-%d')
    for c in st.get('closed', []):
        if c.get('time', '').startswith(today_str):
            follow['today_closed'].append({'sym': c['symbol'], 'pnl': round(c.get('pnl', 0), 2),
                                           'reason': c.get('reason', '')})
except Exception as e:
    follow['error'] = str(e)

# ===== 4. 网格挂单 =====
orders = signed('/api/v3/openOrders')
grid_buys = [o for o in orders if o['side'] == 'BUY']
grid_sells = [o for o in orders if o['side'] == 'SELL']


# ===== 5. 雷达信号评估 (2026-08-29 接入) =====
radar_report = {'signals_today': 0, 'pending': 0, 'hits': 0, 'misses': 0, 'hit_rate': None, 'detail': []}
RADAR_HIST = '/home/ubuntu/zq_web4_trading_system/data/radar/history.json'
if os.path.exists(RADAR_HIST):
    try:
        rh = json.load(open(RADAR_HIST))
        radar_report['signals_today'] = sum(1 for h in rh if h['time'].startswith(time.strftime('%Y-%m-%d')))
        now_ms = time.time() * 1000
        for h in rh:
            if now_ms - h['ts'] * 1000 < 24 * 3600000:
                radar_report['pending'] += 1
                continue
            sym, p0 = h['sym'], h['price']
            try:
                end = int(h['ts'] * 1000 + 24 * 3600000)
                url = (f'https://api.binance.com/api/v3/klines?symbol={sym}&interval=1h'
                       f'&startTime={int(h["ts"]*1000)}&endTime={end}&limit=30')
                kk = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=15).read())
                if kk:
                    p24 = float(kk[-1][4])
                    chg = (p24 / p0 - 1) * 100
                    hit = chg > 3
                    radar_report['hits' if hit else 'misses'] += 1
                    radar_report['detail'].append({'sym': sym, 'sig_price': p0, 'chg24': round(chg, 1), 'hit': hit})
            except Exception:
                pass
        tot = radar_report['hits'] + radar_report['misses']
        if tot > 0:
            radar_report['hit_rate'] = round(radar_report['hits'] / tot * 100, 1)
    except Exception:
        pass

report = {
    'generated_utc': time.strftime('%Y-%m-%d %H:%M:%S'),
    'total_asset': round(total, 2),
    'usdt': round(usdt, 2),
    'holdings': holdings,
    'today_24h': {'buys': buys, 'sells': sells,
                  'buy_usd': round(buy_usd, 2), 'sell_usd': round(sell_usd, 2),
                  'fee_est': round(fee_usd, 2),
                  'sells_detail': sells_detail[-10:]},
    'follow_engine': follow,
    'radar': radar_report,
    'grid': {'buy_orders': len(grid_buys), 'sell_orders': len(grid_sells),
             'buy_range': [float(o['price']) for o in grid_buys],
             'sell_range': [float(o['price']) for o in grid_sells]},
}

with open('/home/ubuntu/zq_web4_trading_system/data/daily_pnl_report.json', 'w') as f:
    json.dump(report, f, indent=2)

print(f"✅ 报告生成: TOTAL=${total:.2f} USDT=${usdt:.2f} 24h: BUY{buys} SELL{sells} 卖额${sell_usd:.2f}")
print(f"   跟随: {len(follow.get('today_closed', []))}笔平仓 网格: {len(grid_buys)}买/{len(grid_sells)}卖")
if radar_report['hit_rate'] is not None:
    print(f"   雷达: 今日{radar_report['signals_today']}信号 累计命中率{radar_report['hit_rate']}% ({radar_report['hits']}hit/{radar_report['misses']}miss)")
