#!/usr/bin/env python3
"""
ZQ Web 4.0 市况判断器 v1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

解决的问题：
  系统同时使用均值回归和趋势跟踪两种逻辑，结果互相矛盾。
  震荡市用趋势跟踪 = 假突破亏钱
  趋势市用均值回归 = 过早止盈

解决方案：
  用ADX判断当前市况，基于市况切换策略逻辑。

数据来源：
  从CoinGecko或Binance获取Top币种的K线数据，计算ADX和ATR。
  不依赖引擎的评分系统（独立判断）。

用法：
  from market_regime import get_regime
  regime = get_regime(snapshots, threshold=25)
  # 返回 'trending' 或 'ranging'
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import numpy as np
import json, os
from datetime import datetime, timezone, timedelta

BJT = timezone(timedelta(hours=8))

# ─── 配置 ───
REGIME_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "regime_signal.json")

# 默认阈值
ADX_TRENDING_THRESHOLD = 25   # ADX > 25 = 趋势市
ADX_RANGING_THRESHOLD = 20    # ADX < 20 = 震荡市


def calc_adx(highs, lows, closes, period=14):
    """
    计算ADX（平均趋向指数）。
    ADX > 25 = 强趋势
    ADX < 20 = 弱趋势（震荡）
    20-25 = 过渡区
    
    返回: adx_value (float)
    """
    if len(closes) < period * 2:
        return 0.0
    
    # TR (True Range)
    high = np.array(highs[-period*2:], dtype=float)
    low = np.array(lows[-period*2:], dtype=float)
    close = np.array(closes[-period*2:], dtype=float)
    
    prev_close = np.roll(close, 1)
    prev_close[0] = close[0]
    
    tr = np.maximum(high - low, 
                    np.maximum(np.abs(high - prev_close), 
                               np.abs(low - prev_close)))
    
    # 方向波动
    up_move = high[1:] - high[:-1]
    down_move = low[:-1] - low[1:]
    
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
    
    # 平滑
    def ema(arr, period):
        alpha = 2 / (period + 1)
        result = np.zeros_like(arr)
        result[0] = arr[0]
        for i in range(1, len(arr)):
            result[i] = arr[i] * alpha + result[i-1] * (1 - alpha)
        return result
    
    tr_smoothed = ema(tr[1:], period)
    plus_di = 100 * ema(plus_dm, period) / tr_smoothed
    minus_di = 100 * ema(minus_dm, period) / tr_smoothed
    
    # DX = |+DI - -DI| / (+DI + -DI) * 100
    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
    
    # ADX = EMA of DX
    adx = ema(dx, period)
    
    return float(adx[-1])


def calc_atr(highs, lows, closes, period=14):
    """
    计算ATR（平均真实波幅）。
    用于判断波动率大小。
    """
    if len(closes) < period + 1:
        return 0.0
    
    high = np.array(highs[-(period+1):], dtype=float)
    low = np.array(lows[-(period+1):], dtype=float)
    close = np.array(closes[-(period+1):], dtype=float)
    
    prev_close = np.roll(close, 1)
    prev_close[0] = close[0]
    
    tr = np.maximum(high - low, 
                    np.maximum(np.abs(high - prev_close), 
                               np.abs(low - prev_close)))
    
    atr = np.mean(tr[1:])  # 简单平均
    return float(atr)


def get_regime_from_klines(klines_4h, klines_1h=None, adx_threshold=25):
    """
    从K线数据判断市况。
    
    参数:
        klines_4h: 4小时K线列表（用于ADX判断）
        klines_1h: 1小时K线列表（可选，用于短期确认）
        adx_threshold: ADX阈值，>此值为趋势市
        
    返回:
        {
            'regime': 'trending' | 'ranging' | 'transition',
            'adx': float,
            'atr_pct': float (ATR/价格*100，波动率百分比),
            'details': str
        }
    """
    if not klines_4h or len(klines_4h) < 28:
        return {'regime': 'unknown', 'adx': 0, 'atr_pct': 0, 'details': '数据不足'}
    
    highs = [float(k[2]) for k in klines_4h[-28:]]
    lows = [float(k[3]) for k in klines_4h[-28:]]
    closes = [float(k[4]) for k in klines_4h[-28:]]
    current_price = closes[-1] if closes else 0
    
    adx = calc_adx(highs, lows, closes, period=14)
    atr = calc_atr(highs, lows, closes, period=14)
    atr_pct = (atr / current_price * 100) if current_price > 0 else 0
    
    # 判断市况
    if adx >= adx_threshold:
        regime = 'trending'
        details = f"ADX={adx:.1f}≥{adx_threshold}，强趋势市场"
    elif adx <= adx_threshold - 5:  # 20以下
        regime = 'ranging'
        details = f"ADX={adx:.1f}<{adx_threshold-5}，震荡市场"
    else:
        regime = 'transition'
        details = f"ADX={adx:.1f}在{adx_threshold-5}-{adx_threshold}，过渡区"
    
    # 波动率附加信息
    if atr_pct > 5:
        details += f"，高波动(ATR={atr_pct:.1f}%)"
    elif atr_pct < 1:
        details += f"，低波动(ATR={atr_pct:.1f}%)"
    
    return {
        'regime': regime,
        'adx': round(adx, 1),
        'atr_pct': round(atr_pct, 2),
        'details': details,
        'timestamp': datetime.now(BJT).strftime('%Y-%m-%d %H:%M:%S')
    }


def get_market_regime(client, symbol='BTCUSDT', adx_threshold=25):
    """
    从交易所获取BTC K线数据判断市场整体市况。
    
    参数:
        client: Binance client
        symbol: 用于判断的币种（默认BTC）
        adx_threshold: ADX阈值
        
    返回: get_regime_from_klines()的结果
    """
    try:
        klines_4h = client.get_klines(symbol=symbol, interval='4h', limit=30)
        return get_regime_from_klines(klines_4h, adx_threshold=adx_threshold)
    except Exception as e:
        return {'regime': 'unknown', 'adx': 0, 'atr_pct': 0, 'details': f'获取失败: {e}'}


def get_strategy_for_regime(regime):
    """
    根据市况返回推荐的策略配置。
    
    震荡市(ranging): 
        - 入场: RSI+布林带均值回归（低买高卖）
        - 出场: P1(RSI超买) + 硬止损
        - 禁用: E2, E3, E4（1474笔验证正确率<3%）
        
    趋势市(trending):
        - 入场: 唐奇安通道突破（追涨）
        - 出场: 反向突破 + P1(RSI过热保护)
        - 启用: E3(趋势转跌在趋势市是有效信号)
        
    过渡区(transition):
        - 保守模式：两者混合，降低仓位
    """
    strategies = {
        'ranging': {
            'name': '均值回归',
            'entry': 'RSI<25或价格<布林下轨时买入',
            'exit': 'P1(RSI>70)或E2(量萎缩)',
            'disabled_exits': ['E3', 'E4', 'P3'],
            'position_size': '正常(100%)',
            'suitable_for': '低波动横盘'
        },
        'trending': {
            'name': '趋势跟踪',
            'entry': '价格突破N日高点时买入',
            'exit': '价格跌破N日低点或P1(过热)',
            'disabled_exits': ['E4', 'P3'],  # E3在趋势市内保留
            'position_size': '正常(100%)',
            'suitable_for': '强趋势单边'
        },
        'transition': {
            'name': '保守混合',
            'entry': '评分前3+趋势向上',
            'exit': 'E2或P1',
            'disabled_exits': ['E3', 'E4', 'P3'],
            'position_size': '减半(50%)',
            'suitable_for': '方向不明'
        }
    }
    return strategies.get(regime, strategies['transition'])


def save_regime(signal):
    """保存市况判断信号到文件"""
    os.makedirs(os.path.dirname(REGIME_PATH), exist_ok=True)
    with open(REGIME_PATH, 'w') as f:
        json.dump(signal, f, indent=2, ensure_ascii=False)


def load_regime():
    """读取最新的市况判断信号"""
    try:
        with open(REGIME_PATH) as f:
            return json.load(f)
    except:
        return {'regime': 'unknown', 'timestamp': 'unknown'}


# ─── 独立运行入口 ───
if __name__ == '__main__':
    print("""
    ╔══════════════════════════════════════════════╗
    ║       ZQ 市况判断器 — 独立测试模式           ║
    ╚══════════════════════════════════════════════╝
    """)
    
    try:
        from binance.client import Client
        auth = json.load(open('config/auth.json'))
        client = Client(auth['binance']['api_key'], auth['binance']['api_secret'])
        
        print("📡 获取BTC 4h K线...")
        regime = get_market_regime(client)
        print(f"  ADX: {regime['adx']}")
        print(f"  ATR: {regime['atr_pct']}%")
        print(f"  市况: {regime['regime']}")
        print(f"  详情: {regime['details']}")
        
        strategy = get_strategy_for_regime(regime['regime'])
        print(f"\n  推荐策略: {strategy['name']}")
        print(f"  入场: {strategy['entry']}")
        print(f"  出场: {strategy['exit']}")
        
        save_regime(regime)
        print(f"\n✅ 市况信号已保存到 {REGIME_PATH}")
        
    except Exception as e:
        print(f"❌ 获取失败: {e}")
        print("（请从项目根目录运行）")
