#!/usr/bin/env python3
"""
ZQ Web 4.0 方向判断器 v1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

解决的问题：
  系统只过滤（什么能进）不判断方向（什么能涨）。
  结果是"高频接盘→微亏止损→换一个→再微亏止损"的死循环。

解决方案：
  在引擎的入场/出场两层各插一道方向判断：

  Layer 1（入场前）：市场级方向门
    - 如果大盘（BTC/ETH/BNB）趋势往下 → 不进场（空仓等待）
    - 如果大盘趋势往上 → 允许进场，但优先选方向共振的币

  Layer 2（出场前）：趋势持有信号
    - 如果4h/1h趋势仍然向上 → 无视所有卖出信号，只允许P1(RSI超买)和-5%硬止损通过
    - E2/E3/E4已禁用（1474笔验证正确率<3%，系统-58%的根因）

数据来源：
  从Binance API读取K线数据判断多时间框架趋势。
  不依赖引擎的评分系统（独立判断）。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import json, os, time
from datetime import datetime, timezone, timedelta

BJT = timezone(timedelta(hours=8))

# ─── 配置 ───
MARKET_BAROMETERS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']  # 大盘风向标
TREND_TIMEFRAMES = {'4h': 96, '1h': 24, '30m': 6}      # 各时间框架取多少根K线

# ─── 向信号输出 ───
SIGNAL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "direction_signal.json")

# ─── 工具函数 ───

def get_trend_from_klines(klines, lookback=8):
    """
    从K线序列判断趋势方向。
    用EMA8和价格位置判断：连续上升=涨，连续下降=跌，横盘=平。
    返回: 1(涨), 0(平), -1(跌), -2(大跌)
    """
    if not klines or len(klines) < lookback:
        return 0
    
    closes = [float(k[4]) for k in klines[-lookback:]]
    
    # 方向得分：最近N根K线的收盘价对比
    up_count = 0
    down_count = 0
    for i in range(1, len(closes)):
        if closes[i] > closes[i-1]:
            up_count += 1
        elif closes[i] < closes[i-1]:
            down_count += 1
    
    net = up_count - down_count
    
    # 趋势强度
    if net >= 4:
        return 1   # 强势上涨
    elif net >= 2:
        return 1   # 温和上涨
    elif net <= -4:
        return -2  # 强势下跌
    elif net <= -2:
        return -1  # 温和下跌
    else:
        return 0   # 横盘/震荡

def get_market_direction(client):
    """
    判断整个市场的大方向。
    用三大风向标的4小时趋势综合判断。
    返回: {direction, confidence, detail}
    """
    results = {}
    overall = 0
    
    for symbol in MARKET_BAROMETERS:
        try:
            klines = client.get_klines(symbol=symbol, interval='4h', limit=48)
            trend_4h = get_trend_from_klines(klines, 12)   # 12根4hK线=48小时
            trend_1h = get_trend_from_klines(klines[-24:], 8)  # 近8根
            trend_30m = get_trend_from_klines(klines[-6:], 4)  # 近4根
            
            # 综合得分：4h权重3，1h权重2，30m权重1
            score = trend_4h * 3 + trend_1h * 2 + trend_30m * 1
            results[symbol] = {
                'trend_4h': trend_4h,
                'trend_1h': trend_1h,
                'trend_30m': trend_30m,
                'score': score
            }
            overall += score
        except Exception as e:
            results[symbol] = {'error': str(e)}
    
    # 整体方向判断
    max_possible = 6 * 3 * 3  # 3个币，每个最高6分
    confidence = overall / max_possible if max_possible > 0 else 0
    
    if overall >= 9:
        direction = 'bullish'    # 强烈看多
    elif overall >= 3:
        direction = 'mild_bull'  # 温和看多
    elif overall <= -9:
        direction = 'bearish'    # 强烈看空
    elif overall <= -3:
        direction = 'mild_bear'  # 温和看空
    else:
        direction = 'neutral'    # 震荡
    
    return {
        'direction': direction,
        'overall_score': overall,
        'confidence': round(confidence, 2),
        'detail': results,
        'timestamp': datetime.now(BJT).strftime('%Y-%m-%d %H:%M:%S')
    }

def should_enter(market_dir, coin_score, coin_trend):
    """
    判断该不该进场。
    市场方向 + 币种方向共振才进。
    
    返回: (True/False, 理由)
    """
    market = market_dir['direction']
    
    # 市场强烈看空 → 不进场
    if market == 'bearish':
        return False, f"大盘看空({market_dir['overall_score']})，不宜开新仓"
    
    if market == 'mild_bear':
        # 温和看空 → 只进方向共振极好的币
        if coin_trend < 1:
            return False, f"大盘偏空({market})，币种趋势{coin_trend}无法共振"
        return True, f"大盘偏空但币种强{coin_trend}，谨慎进场"
    
    # 中性/看多 → 允许进场
    return True, f"大盘{market}({market_dir['overall_score']})，允许进场"

def should_hold(coin_symbol, client, hold_minutes, entry_price, current_price):
    """
    判断该不该继续持有。
    4h/1h趋势向上且不是极端情况 → 持有不卖。
    
    返回: (True/False, 理由)
    """
    try:
        # 读4h K线
        klines_4h = client.get_klines(symbol=coin_symbol, interval='4h', limit=24)
        klines_1h = client.get_klines(symbol=coin_symbol, interval='1h', limit=24)
        
        trend_4h = get_trend_from_klines(klines_4h, 12)
        trend_1h = get_trend_from_klines(klines_1h, 8)
        
        current_price_4h = float(klines_4h[-1][4])
        avg_price_4h = sum(float(k[4]) for k in klines_4h[-12:]) / 12
        
        # 计算盈亏
        pnl_pct = (current_price - entry_price) / entry_price * 100 if entry_price > 0 else 0
        
        reasons = []
        hold = True
        
        # 4h趋势向上 → 持有
        if trend_4h >= 1:
            reasons.append(f"4h趋势{trend_4h}向上(看多)")
        elif trend_4h == 0:
            reasons.append(f"4h趋势横盘(观望)")
            # 横盘但1h向上 → 仍可持有
            if trend_1h >= 1:
                reasons.append("1h趋势向上→持有等待")
            else:
                reasons.append("1h无方向→考虑减仓")
                hold = False
        elif trend_4h <= -1:
            reasons.append(f"4h趋势{trend_4h}向下→不宜持有")
            hold = False
        
        # 已经盈利 → 允许趋势跑
        if pnl_pct > 3 and trend_4h >= 1:
            reasons.append(f"盈利{pnl_pct:.1f}%+趋势向上→让利润跑")
        
        # 价格在EMA上方 → 趋势健康
        if current_price_4h > avg_price_4h:
            reasons.append("价格在4h均线上方→趋势健康")
        else:
            reasons.append("价格跌破4h均线→趋势走弱")
            if not any("向下" in r for r in reasons):
                hold = False
        
        return hold, "; ".join(reasons) if reasons else "方向不明→保守持有"
        
    except Exception as e:
        return True, f"无法判断方向({e})→按原规则执行"

def save_signal(signal):
    """保存方向信号到文件，供引擎读取"""
    os.makedirs(os.path.dirname(SIGNAL_PATH), exist_ok=True)
    with open(SIGNAL_PATH, 'w') as f:
        json.dump(signal, f, indent=2, ensure_ascii=False)

def load_signal():
    """读取最新的方向信号"""
    if os.path.exists(SIGNAL_PATH):
        with open(SIGNAL_PATH) as f:
            return json.load(f)
    return {'direction': 'neutral', 'timestamp': 'unknown'}


# ─── 独立运行接口（供引擎每30分钟调用） ───

def run_direction_check(client):
    """
    完整的方向检查流程：
    1. 判断大盘方向
    2. 保存信号文件
    3. 返回是否允许进场
    
    引擎在Layer 1（数据扫描）结束后调用此函数。
    """
    print(f"\n{'='*50}")
    print("  📡 方向判断器 — 市场扫描")
    print(f"{'='*50}")
    
    market = get_market_direction(client)
    print(f"  大盘方向: {market['direction']} (得分{market['overall_score']})")
    for sym, det in market['detail'].items():
        if 'error' not in det:
            print(f"    {sym}: 4h={det['trend_4h']:+d} 1h={det['trend_1h']:+d} 30m={det['trend_30m']:+d} 总分={det['score']:+d}")
    
    can_trade, reason = should_enter(market, 0, 0)
    print(f"  进场决策: {'✅ 允许' if can_trade else '❌ 禁止'} ({reason})")
    
    signal = {
        'market': market,
        'can_enter': can_trade,
        'enter_reason': reason,
        'timestamp': datetime.now(BJT).strftime('%Y-%m-%d %H:%M:%S')
    }
    save_signal(signal)
    return signal


if __name__ == '__main__':
    # 独立测试模式
    print("""
    ╔══════════════════════════════════════════════╗
    ║       ZQ 方向判断器 — 独立模式              ║
    ╚══════════════════════════════════════════════╝
    """)
    
    try:
        from binance.client import Client
        auth = json.load(open('config/auth.json'))
        client = Client(auth['binance']['api_key'], auth['binance']['api_secret'])
        signal = run_direction_check(client)
        print(f"\n✅ 方向信号已保存到 {SIGNAL_PATH}")
    except Exception as e:
        print(f"❌ 方向判断失败: {e}")
        print("（如果是config路径问题，请从项目根目录运行）")
