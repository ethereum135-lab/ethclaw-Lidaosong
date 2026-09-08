#!/usr/bin/env python3
"""
海龟交易法则 — 币安现货做多版 v1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

规则来源：《海龟交易法则》(Curtis Faith)，Richard Dennis & William Eckhardt
完全按原始规则执行，不自创任何逻辑。

时间框架：1小时K线
交易方向：仅做多（不做空）
资金：430 USDT，分3份

入场条件：价格 > 过去20根K线最高价（唐奇安通道上轨突破）
出场条件：价格 < 过去10根K线最低价（唐奇安通道下轨突破）
止损规则：入场价 - 2 × ATR(20)，跟踪止损（只上移不下移）
仓位管理：每笔只用1份（约143U），同时间最多1个持仓

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import json, os, time
import numpy as np
from datetime import datetime, timezone, timedelta

BJT = timezone(timedelta(hours=8))
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 信号输出路径
SIGNAL_PATH = os.path.join(BASE_DIR, "strategies", "data", "turtle_signal.json")
POSITION_PATH = os.path.join(BASE_DIR, "strategies", "data", "turtle_position.json")

# ─── 固定参数（完全按海龟原始规则） ───
ENTRY_PERIOD = 20    # 入场通道周期（根K线）
EXIT_PERIOD = 10     # 出场通道周期（根K线）
ATR_PERIOD = 20      # ATR计算周期
LOSS_MULT = 2.0      # 止损倍数
CAPITAL = 430.0      # 总资金
MAX_POSITIONS = 1    # 同时持仓数
POSITION_RATIO = 1/3 # 每份资金比例


def calc_donchian(highs, period=20):
    """唐奇安通道：过去N根K线的最高价"""
    if len(highs) < period:
        return None
    return max(highs[-period:])


def calc_donchian_low(lows, period=10):
    """唐奇安通道下轨：过去N根K线的最低价"""
    if len(lows) < period:
        return None
    return min(lows[-period:])


def calc_atr(highs, lows, closes, period=20):
    """计算ATR(平均真实波幅)"""
    if len(closes) < period + 1:
        return None
    
    high = np.array(highs[-(period+1):], dtype=float)
    low = np.array(lows[-(period+1):], dtype=float)
    close = np.array(closes[-(period+1):], dtype=float)
    
    prev_close = np.roll(close, 1)
    prev_close[0] = close[0]
    
    tr = np.maximum(high - low,
                    np.maximum(np.abs(high - prev_close),
                               np.abs(low - prev_close)))
    
    return float(np.mean(tr[1:]))


def analyze_symbol(client, symbol, interval='1h', limit=30):
    """分析单个币种的Turtle信号"""
    try:
        klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
        if not klines or len(klines) < 25:
            return None
        
        highs = [float(k[2]) for k in klines]
        lows = [float(k[3]) for k in klines]
        closes = [float(k[4]) for k in klines]
        current_price = closes[-1]
        
        # 唐奇安通道
        upper = calc_donchian(highs, ENTRY_PERIOD)
        lower = calc_donchian_low(lows, EXIT_PERIOD)
        atr = calc_atr(highs, lows, closes, ATR_PERIOD)
        
        if upper is None or lower is None or atr is None:
            return None
        
        # 入场信号：价格突破上轨
        entry_signal = current_price > upper
        
        # 出场信号：价格跌破下轨
        exit_signal = current_price < lower
        
        # 距离通道的百分比（衡量突破强度）
        dist_from_upper = (current_price - upper) / upper * 100 if upper > 0 else 0
        dist_from_lower = (lower - current_price) / lower * 100 if lower > 0 else 0
        
        # ATR百分比（波动率）
        atr_pct = atr / current_price * 100 if current_price > 0 else 0
        
        return {
            'symbol': symbol,
            'price': current_price,
            'upper': upper,
            'lower': lower,
            'atr': atr,
            'atr_pct': round(atr_pct, 2),
            'entry_signal': entry_signal,
            'exit_signal': exit_signal,
            'dist_from_upper': round(dist_from_upper, 2),
            'dist_from_lower': round(dist_from_lower, 2),
            'timestamp': datetime.now(BJT).strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        return None


def check_positions(client, positions):
    """检查当前持仓是否需要出场或止损"""
    signal = {'action': 'HOLD', 'symbol': None, 'reason': ''}
    
    for pos in positions:
        symbol = pos['symbol']
        entry_price = pos['entry_price']
        stop_loss = pos['stop_loss']
        
        try:
            klines = client.get_klines(symbol=symbol, interval='1h', limit=15)
            if not klines:
                continue
            
            current_price = float(klines[-1][4])
            lows = [float(k[3]) for k in klines]
            highs = [float(k[2]) for k in klines]
            closes = [float(k[4]) for k in klines]
            
            # 检查止损（跟踪止损）
            atr = calc_atr(highs, lows, closes, ATR_PERIOD)
            if atr:
                new_stop = max(highs[-11:]) - LOSS_MULT * atr
                new_stop = max(stop_loss, new_stop)  # 只上移不下移
                stop_loss = new_stop
            
            # 止损触发
            if current_price <= stop_loss:
                return {
                    'action': 'SELL',
                    'symbol': symbol,
                    'reason': f'止损(入场{entry_price:.4f}, 止损{stop_loss:.4f}, 当前{current_price:.4f})',
                    'stop_loss': stop_loss,
                    'current_price': current_price
                }
            
            # 出场信号：跌破下轨
            lower = calc_donchian_low(lows, EXIT_PERIOD)
            if lower and current_price < lower:
                return {
                    'action': 'SELL',
                    'symbol': symbol,
                    'reason': f'下轨突破出场(下轨{lower:.4f}, 当前{current_price:.4f})',
                    'stop_loss': stop_loss,
                    'current_price': current_price
                }
            
        except Exception as e:
            pass
    
    return signal


def find_entry(client, watch_symbols=['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT', 'ADAUSDT', 'AVAXUSDT', 'DOTUSDT', 'LINKUSDT', 'SUIUSDT', 'APTUSDT', 'OPUSDT', 'ARBUSDT', 'TIAUSDT']):
    """找入场机会：扫描监控列表，找突破上轨的币"""
    signals = []
    
    for symbol in watch_symbols:
        result = analyze_symbol(client, symbol)
        if result and result['entry_signal']:
            signals.append(result)
    
    if not signals:
        return None
    
    # 同时有多个突破→选突破强度最大的（距离上轨最远）
    signals.sort(key=lambda x: -x['dist_from_upper'])
    best = signals[0]
    
    return {
        'action': 'BUY',
        'symbol': best['symbol'],
        'price': best['price'],
        'upper': best['upper'],
        'atr': best['atr'],
        'atr_pct': best['atr_pct'],
        'dist_from_upper': best['dist_from_upper'],
        'reason': f'唐奇安突破(上轨{best["upper"]:.4f}, 突破{best["dist_from_upper"]:+.2f}%)',
        'entry_price': best['price'],
        'stop_loss': best['price'] - LOSS_MULT * best['atr']
    }


def run_turtle(client):
    """完整跑一轮海龟策略"""
    # 加载当前持仓
    positions = []
    try:
        with open(POSITION_PATH) as f:
            positions = json.load(f).get('positions', [])
    except:
        pass
    
    print(f"\n{'='*50}")
    print(f"  🐢 海龟策略 — {datetime.now(BJT).strftime('%H:%M:%S')}")
    print(f"{'='*50}")
    
    # 1. 检查持仓是否需要出场
    if positions:
        print(f"\n  📦 当前持仓: {len(positions)}个")
        for p in positions:
            print(f"    {p['symbol']}: 入场{p['entry_price']:.4f}, 止损{p['stop_loss']:.4f}")
        
        exit_signal = check_positions(client, positions)
        if exit_signal['action'] == 'SELL':
            print(f"  🔴 出场: {exit_signal['symbol']} — {exit_signal['reason']}")
            positions = [p for p in positions if p['symbol'] != exit_signal['symbol']]
        
    # 2. 找入场机会
    entry_signal = find_entry(client)
    if entry_signal and len(positions) < MAX_POSITIONS:
        print(f"\n  🟢 入场: {entry_signal['symbol']} @ {entry_signal['price']:.4f}")
        print(f"     上轨: {entry_signal['upper']:.4f}, 突破{entry_signal['dist_from_upper']:+.2f}%")
        print(f"     ATR: {entry_signal['atr']:.4f} ({entry_signal['atr_pct']:.2f}%)")
        print(f"     止损: {entry_signal['stop_loss']:.4f}")
        
        positions.append({
            'symbol': entry_signal['symbol'],
            'entry_price': entry_signal['entry_price'],
            'stop_loss': entry_signal['stop_loss'],
            'entry_time': entry_signal.get('timestamp', datetime.now(BJT).strftime('%Y-%m-%d %H:%M:%S')),
            'qty': (CAPITAL * POSITION_RATIO) / entry_signal['entry_price']
        })
    else:
        print(f"\n  ⏸️  无入场信号")
    
    # 3. 保存持仓
    os.makedirs(os.path.dirname(POSITION_PATH), exist_ok=True)
    with open(POSITION_PATH, 'w') as f:
        json.dump({'positions': positions, 'updated': datetime.now(BJT).strftime('%Y-%m-%d %H:%M:%S')}, f, indent=2)
    
    # 4. 保存信号
    signal = {
        'timestamp': datetime.now(BJT).strftime('%Y-%m-%d %H:%M:%S'),
        'entry': entry_signal,
        'positions': positions,
        'exit': exit_signal if positions else None
    }
    os.makedirs(os.path.dirname(SIGNAL_PATH), exist_ok=True)
    with open(SIGNAL_PATH, 'w') as f:
        json.dump(signal, f, indent=2, ensure_ascii=False)
    
    print(f"\n  ✅ 完成")

    return signal


# ─── 独立运行入口 ───
if __name__ == '__main__':
    print("""
    ╔══════════════════════════════════════════════╗
    ║    海龟交易法则 — 币安现货做多版 v1.0        ║
    ║    规则来源：《海龟交易法则》Curtis Faith     ║
    ╚══════════════════════════════════════════════╝
    """)
    
    try:
        from binance.client import Client
        from binance.exceptions import BinanceAPIException
        
        auth_path = os.path.join(BASE_DIR, 'config', 'auth.json')
        if not os.path.exists(auth_path):
            print(f"❌ 找不到auth文件: {auth_path}")
            sys.exit(1)
        
        with open(auth_path) as f:
            auth = json.load(f)
        
        client = Client(auth['binance']['api_key'], auth['binance']['api_secret'])
        
        signal = run_turtle(client)
        
        if signal['entry']:
            print(f"\n✅ 新信号: {signal['entry']['action']} {signal['entry']['symbol']}")
        else:
            print(f"\n⏸️  无操作")
            
    except BinanceAPIException as e:
        print(f"❌ Binance API错误: {e}")
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        print("   pip install python-binance numpy")
    except Exception as e:
        print(f"❌ 未知错误: {e}")
        import traceback
        traceback.print_exc()
