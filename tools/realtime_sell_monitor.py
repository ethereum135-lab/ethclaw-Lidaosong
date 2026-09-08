#!/usr/bin/env python3
"""
realtime_sell_monitor.py — WebSocket实时卖出监听器
==================================================
独立运行，不干扰引擎。
引擎负责买入，监听器只负责卖出。

原理：
- 通过Binance WebSocket实时监听已持仓币种的价格
- 维护滚动价格窗口（每1分钟记录一次）
- 检测急拉、超买、利润回吐等卖出信号
- 信号触发立即通过Binance API执行卖出

启动方式：python3 tools/realtime_sell_monitor.py
后台运行：nohup python3 tools/realtime_sell_monitor.py > logs/monitor.log 2>&1 &
"""

import json
import time
import hashlib
import hmac
import urllib.request
import ssl
import os
import sys
import threading
from collections import deque
from datetime import datetime

# ============================================================
# 配置
# ============================================================
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUTH_FILE = os.path.join(PROJECT_ROOT, 'config', 'auth.json')
STATE_FILE = os.path.join(PROJECT_ROOT, 'data', 'node_state.json')
LOG_DIR = os.path.join(PROJECT_ROOT, 'logs')
CHECK_INTERVAL = 60  # 每60秒检查一次信号（基于价格点）
PRICE_POINTS = 10    # 保留最近10个价格点（10分钟窗口）

# 卖出信号阈值
SIGNALS = {
    'rapid_rise_pct': 8.0,      # 5分钟内急拉超过8%（多根K线总涨幅）
    'rapid_rise_points': 3,     # 需要连续上涨的点数
    'profit_peak_drop': 5.0,    # 从持仓期间最高点回落5%时触发利润保护
    'extreme_drop': 10.0,       # 10分钟内急跌超过10%（止损）
}

# ============================================================
# Binance API 基础
# ============================================================
def load_auth():
    with open(AUTH_FILE) as f:
        return json.load(f)['binance']

def binance_api(method, path, params=None, signed=False):
    """调用Binance REST API（带SOCKS5代理回退，用于451 bypass）"""
    auth = load_auth()
    base = "https://api.binance.com"
    query = ''
    headers = {'X-MBX-APIKEY': auth['api_key']}
    
    if signed:
        # 有签名的请求至少需要timestamp
        sig_params = dict(params) if params else {}
        if 'timestamp' not in sig_params:
            sig_params['timestamp'] = int(time.time() * 1000)
        qs = '&'.join([f'{k}={v}' for k, v in sorted(sig_params.items())])
        sig = hmac.new(auth['api_secret'].encode(), qs.encode(), hashlib.sha256).hexdigest()
        query = f'?{qs}&signature={sig}'
    
    # ─── 尝试直连 ───
    url = f'{base}{path}{query}'
    r = urllib.request.Request(url, headers=headers)
    ctx = ssl.create_default_context()
    try:
        res = urllib.request.urlopen(r, timeout=10, context=ctx)
        return res.status, json.loads(res.read())
    except urllib.error.HTTPError as e:
        body = e.read()
        try:
            err_data = json.loads(body) if body else {'error': str(e)}
        except json.JSONDecodeError:
            err_data = {'error': str(e), 'body': body.decode(errors='replace')}
        # HTTP 451 → SOCKS5 代理重试
        if e.code == 451:
            proxy_result = _binance_via_proxy(method, path, params, signed, auth)
            if proxy_result is not None:
                return proxy_result
        return e.code, err_data
    except (urllib.error.URLError, OSError, ConnectionError, TimeoutError) as e:
        # 连接失败（直连被墙）→ SOCKS5 代理重试
        proxy_result = _binance_via_proxy(method, path, params, signed, auth)
        if proxy_result is not None:
            return proxy_result
        return 0, {'error': str(e)}


SOCKS5_PROXY_STR = 'socks5h://127.0.0.1:1080'
SOCKS5_ENABLED = True  # 通过 launchd 守护的 SSH 隧道


def _binance_via_proxy(method, path, params=None, signed=False, auth=None):
    """通过 SOCKS5 代理调用 Binance API"""
    if not SOCKS5_ENABLED:
        return None
    try:
        import requests
    except ImportError:
        print('[错误] requests 未安装，无法使用 SOCKS5 代理')
        return None
    base = "https://api.binance.com"
    proxies = {'http': SOCKS5_PROXY_STR, 'https': SOCKS5_PROXY_STR}
    url = f'{base}{path}'
    headers = {'X-MBX-APIKEY': auth['api_key']}
    req_params = dict(params) if params else {}
    try:
        if signed:
            if 'timestamp' not in req_params:
                req_params['timestamp'] = int(time.time() * 1000)
            qs = '&'.join([f'{k}={v}' for k, v in sorted(req_params.items())])
            sig = hmac.new(auth['api_secret'].encode(), qs.encode(), hashlib.sha256).hexdigest()
            req_params['signature'] = sig
        if method == 'GET':
            res = requests.get(url, headers=headers, params=req_params, proxies=proxies, timeout=15)
        else:
            res = requests.post(url, headers=headers, json=req_params, proxies=proxies, timeout=15)
        return res.status_code, res.json()
    except Exception as e:
        print(f'[代理错误] SOCKS5 代理请求失败: {e}')
        return None

# ============================================================
# WebSocket 连接
# ============================================================
class BinanceWebSocket:
    """
    通过HTTP轮询模拟WebSocket效果（避免依赖websocket库）
    每10秒拉一次最新价格
    等验证通过后可以换成真正的WebSocket（更快）
    """
    
    def __init__(self):
        self.symbols = []  # 当前监听的币种
        self.prices = {}   # symbol -> deque of prices
        self.highs = {}    # symbol -> 持仓期间最高价
        self.running = False
        self.callback = None
    
    def set_callback(self, callback):
        self.callback = callback
    
    def update_symbols(self, symbols):
        """更新监听列表"""
        self.symbols = symbols
        for sym in symbols:
            if sym not in self.prices:
                self.prices[sym] = deque(maxlen=PRICE_POINTS)
                self.highs[sym] = None
    
    def poll_once(self):
        """一次轮询所有监听币种的价格（每次都查实时数据）"""
        for sym in self.symbols:
            try:
                url = f'https://api.binance.com/api/v3/ticker/price?symbol={sym}USDT'
                req = urllib.request.Request(url)
                res = urllib.request.urlopen(req, timeout=5)
                data = json.loads(res.read())
                price = float(data['price'])
                
                self.prices[sym].append({
                    'price': price,
                    'time': time.time()
                })
                
                # 更新持仓期间最高价
                if self.highs[sym] is None or price > self.highs[sym]:
                    self.highs[sym] = price
                
                if self.callback:
                    self.callback(sym, price, self.prices[sym], self.highs[sym])
                    
            except Exception as e:
                pass  # 单个币失败不影响其他币

# ============================================================
# 信号检测
# ============================================================
def check_signals(symbol, price, price_points, high_price):
    """检查所有卖出信号，返回触发的信号列表"""
    signals = []
    
    if len(price_points) < 2:
        return signals
    
    prices_list = [p['price'] for p in price_points]
    oldest_price = prices_list[0]
    
    # 信号1：急拉检测（最近5分钟相对5分钟前涨幅 > X%）
    recent_rise = (price - oldest_price) / oldest_price * 100
    if recent_rise > SIGNALS['rapid_rise_pct']:
        signals.append({
            'type': 'rapid_rise',
            'message': f'{symbol} 急拉 {recent_rise:.1f}%（{len(price_points)}个点，{round((price_points[-1]["time"]-price_points[0]["time"])/60)}分钟）',
            'trigger_price': price,
            'signal_strength': min(100, int(recent_rise / SIGNALS['rapid_rise_pct'] * 100))
        })
    
    # 信号2：利润保护（从持仓最高点回落 > X%）
    if high_price and high_price > price:
        drop_from_peak = (high_price - price) / high_price * 100
        if drop_from_peak > SIGNALS['profit_peak_drop']:
            signals.append({
                'type': 'profit_peak_drop',
                'message': f'{symbol} 从高点\${high_price:.4f}回落 {drop_from_peak:.1f}%',
                'trigger_price': price,
                'signal_strength': min(100, int(drop_from_peak / SIGNALS['profit_peak_drop'] * 100))
            })
    
    # 信号3：急跌止损（10分钟内跌>X%）
    recent_drop = (oldest_price - price) / oldest_price * 100
    if recent_drop > SIGNALS['extreme_drop']:
        signals.append({
            'type': 'extreme_drop',
            'message': f'{symbol} 急跌 {recent_drop:.1f}%',
            'trigger_price': price,
            'signal_strength': min(100, int(recent_drop / SIGNALS['extreme_drop'] * 100))
        })
    
    return signals

# ============================================================
# 执行卖出
# ============================================================
def execute_sell(symbol, signal):
    """通过Binance API执行卖出"""
    print(f'[执行] {symbol} 卖出触发: {signal["message"]}')
    
    # 先查持仓量
    code, account = binance_api('GET', '/api/v3/account', signed=True)
    if code != 200:
        print(f'[错误] 查持仓失败: {account}')
        return False
    
    # 找该币的持仓
    asset_info = None
    for bal in account.get('balances', []):
        if bal['asset'] == symbol:
            free = float(bal['free'])
            locked = float(bal['locked'])
            if free + locked > 0:
                asset_info = bal
            break
    
    if not asset_info:
        print(f'[跳过] {symbol} 无持仓')
        return False
    
    free_qty = float(asset_info['free'])
    print(f'[持仓] {symbol}: {free_qty}')
    
    if free_qty <= 0:
        print(f'[跳过] {symbol} 可用余额为0')
        return False
    
    # 决定卖出比例 — 根据信号强度
    strength = signal.get('signal_strength', 50)
    if strength >= 80:
        sell_pct = 1.0  # 全卖
    elif strength >= 50:
        sell_pct = 0.6  # 卖60%
    else:
        sell_pct = 0.3  # 卖30%
    
    qty = round(free_qty * sell_pct, 4)
    if qty <= 0:
        return False
    
    print(f'[下单] 卖出 {qty} {symbol}（{sell_pct*100:.0f}%）')
    
    # 获取精度
    code, info = binance_api('GET', '/api/v3/exchangeInfo', {'symbol': f'{symbol}USDT'})
    if code == 200:
        for f in info.get('symbols', []):
            if f['symbol'] == f'{symbol}USDT':
                for t in f.get('filters', []):
                    if t['filterType'] == 'LOT_SIZE':
                        step = float(t['stepSize'])
                        qty = int(qty / step) * step
                        qty = round(qty, 8)
    
    params = {
        'symbol': f'{symbol}USDT',
        'side': 'SELL',
        'type': 'MARKET',
        'quantity': qty
    }
    
    code, result = binance_api('POST', '/api/v3/order', params, signed=True)
    if code == 200:
        executed_qty = float(result.get('executedQty', 0))
        cum_quote = float(result.get('cummulativeQuoteQty', 0))
        avg_price = cum_quote / executed_qty if executed_qty > 0 else 0
        print(f'[成功] 卖出 {executed_qty} {symbol} @ ~\${avg_price:.4f}，收回 \${cum_quote:.2f}')
        
        # 记录日志
        log_entry = {
            'time': datetime.now().isoformat(),
            'action': 'SELL',
            'symbol': symbol,
            'qty': executed_qty,
            'price': avg_price,
            'value': cum_quote,
            'signal_type': signal['type'],
            'signal_msg': signal['message']
        }
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(os.path.join(LOG_DIR, 'realtime_sell.log'), 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        
        return True
    else:
        print(f'[失败] 卖出错误: {result}')
        return False

# ============================================================
# 主循环
# ============================================================
def get_current_holdings():
    """从Binance获取当前持仓（快速版）
    - 一次性获取所有价格（ticker/price轻量 ~5KB）
    - 不调用exchangeInfo（太重 ~100KB）
    - 过滤：排除USDT/LD/尘币
    """
    code, account = binance_api('GET', '/api/v3/account', signed=True)
    if code != 200:
        print(f'查持仓失败: {account}')
        return []
    
    # 一次性获取所有USDT价格
    all_prices = {}
    try:
        req = urllib.request.Request('https://api.binance.com/api/v3/ticker/price')
        res = urllib.request.urlopen(req, timeout=10)
        for item in json.loads(res.read()):
            sym = item['symbol']
            if sym.endswith('USDT'):
                base = sym[:-4]
                all_prices[base] = float(item['price'])
    except:
        pass  # 无价格也能继续，只是不按价值过滤
    
    holdings = []
    skip_prefixes = ('LD', 'LDD')
    
    for bal in account.get('balances', []):
        asset = bal['asset']
        total = float(bal['free']) + float(bal['locked'])
        
        if asset == 'USDT' or asset == 'USDC' or asset == 'BUSD':
            continue
        if any(asset.startswith(p) for p in skip_prefixes):
            continue
        if total < 0.00001:
            continue
        
        # 有价格信息的才加（必须是USDT交易对）
        if asset in all_prices:
            value = total * all_prices[asset]
            if value >= 1.0:
                holdings.append(asset)
    
    # 缓存价格供后续使用
    global _price_cache
    _price_cache = all_prices
    
    return holdings

_price_cache = {}  # 全局价格缓存

# ============================================================
# 历史高点持久化
# ============================================================
HIGHS_FILE = os.path.join(PROJECT_ROOT, 'data', 'monitor_highs.json')

def load_highs():
    """从文件加载历史高点"""
    try:
        with open(HIGHS_FILE) as f:
            return json.load(f)
    except:
        return {}

def save_highs(highs):
    """保存历史高点到文件"""
    try:
        with open(HIGHS_FILE, 'w') as f:
            json.dump(highs, f)
    except:
        pass

def load_engine_holdings():
    """从引擎的状态文件加载当前持仓（辅助）"""
    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
        # node_state.json现在的结构可能不直接存持仓
        # 先用API查
        return get_current_holdings()
    except:
        return get_current_holdings()

def main():
    print('=' * 50)
    print('实时卖出监听器 v0.1')
    print(f'启动时间: {datetime.now().isoformat()}')
    print('=' * 50)
    
    ws = BinanceWebSocket()
    
    def on_price(symbol, price, points, high):
        """每次收到价格更新时调用"""
        signals = check_signals(symbol, price, points, high)
        signal_time = datetime.now().strftime('%H:%M:%S')
        
        for sig in signals:
            strength_bar = '█' * (sig['signal_strength'] // 10) + '░' * (10 - sig['signal_strength'] // 10)
            print(f'[{signal_time}] ⚠️  {sig["message"]} | 信号强度: {strength_bar} {sig["signal_strength"]}%')
            
            # 强度>50的自动执行
            if sig['signal_strength'] >= 50:
                print(f'[{signal_time}] 🔔 信号强度≥50%，自动执行卖出...')
                execute_sell(symbol, sig)
    
    ws.set_callback(on_price)
    
    # 加载历史高点到ws
    highs = load_highs()
    for sym in highs:
        ws.highs[sym] = highs[sym]
    if highs:
        print(f'[加载] 历史高点: {highs}')
    
    print('\n[等待] 获取当前持仓...')
    holdings = load_engine_holdings()
    print(f'[持仓] {holdings if holdings else "无持仓（等待引擎买入..."}')
    
    if holdings:
        ws.update_symbols(holdings)
    
    cycle = 0
    while True:
        try:
            # 每5分钟刷新一次持仓列表（引擎可能新买了币）
            if cycle % 5 == 0 and cycle > 0:
                new_holdings = load_engine_holdings()
                if new_holdings != ws.symbols:
                    print(f'\n[更新] 持仓变化: {ws.symbols} → {new_holdings}')
                    ws.update_symbols(new_holdings)
            
            # 轮询价格
            if ws.symbols:
                ws.poll_once()
                # 保存历史高点（持久化）
                save_highs(ws.highs)
                now = datetime.now().strftime('%H:%M:%S')
                prices_str = ', '.join([f'{s}:${ws.prices.get(s, [{"price":0}])[-1]["price"]:.4f}' 
                                       for s in ws.symbols if ws.prices.get(s)])
                if prices_str:
                    print(f'[{now}] 📊 {prices_str}')
            else:
                # 没持仓就等
                now = datetime.now().strftime('%H:%M:%S')
                holdings = load_engine_holdings()
                if holdings:
                    print(f'[{now}] ✅ 发现新持仓: {holdings}')
                    ws.update_symbols(holdings)
            
            cycle += 1
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            print('\n[停止] 监听器关闭')
            break
        except Exception as e:
            print(f'[错误] {e}')
            time.sleep(5)

if __name__ == '__main__':
    # 快速测试：检查交易所连接
    auth = load_auth()
    print(f'API Key: {auth["api_key"][:10]}...')
    code, account = binance_api('GET', '/api/v3/account', signed=True)
    if code == 200:
        usdt_bal = 0
        for b in account.get('balances', []):
            if b['asset'] == 'USDT':
                usdt_bal = float(b['free']) + float(b['locked'])
        print(f'✅ Binance连接成功 | USDT余额: ${usdt_bal:.2f}')
        
        # 显示当前持仓
        holdings = get_current_holdings()
        if holdings:
            print(f'📦 当前持仓: {holdings}')
        else:
            print('📦 当前无持仓')
    else:
        print(f'❌ Binance连接失败: {account}')
        sys.exit(1)
    
    main()
