"""
TrendRider 核心逻辑 — 移植到 ZQ 引擎 v1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

从社区5k+星策略 TrendRiderStrategy 抽取的核心逻辑：

1. 多时间框架趋势方向（1h/4h EMA50/EMA200）
2. 追踪止损（+5%激活，3%回撤止盈）
3. 冷却期（出场后等待20根K线再入场）
4. 多信号入场（回调/EMA支撑/RSI反弹）

来源: https://github.com/freqtrade/freqtrade-strategies
      → user_data/strategies/TrendRiderStrategy.py
"""
import json, os, time
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ─── Binance API ───
def public_get(path, params=None):
    import requests
    url = f'https://api.binance.com{path}'
    try:
        r = requests.get(url, params=params, timeout=15)
        if r.status_code == 200:
            return r.status_code, r.json()
        return r.status_code, None
    except:
        return 0, None

# ─── EMA计算 ───
def ema(data, period):
    """简单EMA计算，无需talib"""
    if len(data) < period:
        return data[-1] if data else 0
    multiplier = 2 / (period + 1)
    result = data[0]
    for i in range(1, len(data)):
        result = (data[i] - result) * multiplier + result
    return result

def ema_series(data, period):
    """返回完整的EMA序列"""
    if len(data) < period:
        return [data[-1]] if data else [0]
    result = data[0]
    emas = [result]
    multiplier = 2 / (period + 1)
    for i in range(1, len(data)):
        result = (data[i] - result) * multiplier + result
        emas.append(result)
    return emas

# ─── RSI计算 ───
def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50
    gains, losses = 0, 0
    for i in range(-period, 0):
        diff = closes[i] - closes[i-1]
        if diff > 0: gains += diff
        else: losses -= diff
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# ─── 趋势计算（系统原有） ───
def calc_trend(closes):
    """趋势评分 -2~+2"""
    if len(closes) < 4:
        return 0
    recent = closes[-4:]
    avg = sum(recent) / 4
    prev = closes[-5] if len(closes) >= 5 else closes[0]
    if avg > prev * 1.005: return 2
    elif avg > prev * 1.001: return 1
    elif avg < prev * 0.995: return -2
    elif avg < prev * 0.999: return -1
    return 0

# ─── 核心功能1：EMA方向过滤 ───
def check_ema_trend(closes):
    """
    TrendRider核心：EMA50 > EMA200 = 牛市
    返回: "bull", "bear", "neutral"
    """
    if len(closes) < 200:
        return "neutral"
    ema50 = ema(closes[-50:], 50) if len(closes) >= 50 else closes[-1]
    ema200 = ema(closes, 200)
    
    current_price = closes[-1]
    
    if current_price > ema50 > ema200:
        return "bull"
    elif current_price < ema50 < ema200:
        return "bear"
    else:
        return "neutral"

# ─── 核心功能2：多信号入场 ───
def check_entry_signals(closes, highs, lows, volumes):
    """
    TrendRider多信号：满足任一即可入场
    
    返回: (should_enter: bool, signal_name: str)
    """
    if len(closes) < 50:
        return False, "数据不足"
    
    current_price = closes[-1]
    ema50_val = ema(closes[-50:], 50)
    rsi_val = calc_rsi(closes, 14)
    
    signals = []
    
    # 信号1：EMA支撑反弹（核心）
    # 价格跌到EMA50附近后反弹收阳
    if len(highs) >= 3 and len(lows) >= 3:
        recent_low = min(lows[-3:])
        if recent_low <= ema50_val * 1.02 and current_price > ema50_val:
            signals.append("EMA支撑反弹")
    
    # 信号2：RSI回调买入
    # RSI从超卖区(30-40)反弹
    if 30 <= rsi_val <= 50:
        signals.append("RSI回调买入")
    
    # 信号3：放量突破
    # 成交量是EMA20的1.3倍以上 + 价格收涨
    if len(volumes) >= 20:
        vol_ema = sum(volumes[-20:]) / 20
        vol_ratio = volumes[-1] / max(vol_ema, 0.01)
        if vol_ratio > 1.3 and current_price > closes[-2] if len(closes) >= 2 else False:
            signals.append("放量突破")
    
    # 信号4：趋势启动（原有系统的改进版）
    trend = calc_trend(closes)
    prev_trend = calc_trend(closes[:-1]) if len(closes) > 5 else 0
    if trend >= 1 and prev_trend <= 0:
        signals.append("趋势启动")
    
    if signals:
        return True, "+".join(signals)
    return False, "无信号"

# ─── 核心功能3：追踪止损 ───
class TrailingStop:
    """
    TrendRider追踪止损：盈利>5%后激活，回撤3%止盈
    
    用法:
        ts = TrailingStop(entry_price=1.0)
        ts.update(current_price=1.08) → returns (should_exit, reason)
    """
    def __init__(self, entry_price, trail_activate=0.05, trail_distance=0.03):
        self.entry_price = entry_price
        self.highest_price = entry_price
        self.trail_activate = trail_activate    # +5%激活
        self.trail_distance = trail_distance    # 回撤3%卖出
        self.activated = False
        self.entry_time = datetime.now()
    
    def update(self, current_price):
        """更新价格，返回 (should_exit, reason, exit_price)"""
        pnl_pct = (current_price - self.entry_price) / self.entry_price
        
        # 更新最高价
        if current_price > self.highest_price:
            self.highest_price = current_price
        
        # 检查是否激活追踪
        if not self.activated and pnl_pct >= self.trail_activate:
            self.activated = True
        
        # 如果已激活，检查回撤
        if self.activated:
            peak_to_current = (self.highest_price - current_price) / self.highest_price
            if peak_to_current >= self.trail_distance:
                exit_price = self.highest_price * (1 - self.trail_distance)
                return True, f"追踪止盈(从{self.entry_price:.4f}到{exit_price:.4f})"
        
        # 硬止损 -3%
        if pnl_pct <= -0.03:
            return True, f"硬止损({pnl_pct*100:.1f}%)"
        
        return False, "持有"

# ─── 核心功能4：冷却期 ───
class CooldownManager:
    """
    TrendRider冷却期：卖出后等待N根K线再入场
    避免频繁换仓（我们系统的致命问题）
    
    TrendRider原版：stop_duration_candles=20 (1h框架下=20h)
    ZQ版：stop_duration_minutes=120 (30m框架下=4根K线)
    """
    def __init__(self, stop_duration_minutes=120):
        self.cooldowns = {}  # symbol -> cool_until (datetime)
        self.stop_duration = timedelta(minutes=stop_duration_minutes)
    
    def add_cooldown(self, symbol):
        """卖出后添加冷却"""
        self.cooldowns[symbol] = datetime.now() + self.stop_duration
    
    def can_enter(self, symbol):
        """检查是否可以入场"""
        if symbol not in self.cooldowns:
            return True
        return datetime.now() >= self.cooldowns[symbol]

# ─── 集成函数：引擎调用入口 ───
def trendrider_advice(symbol, closes, highs, lows, volumes,
                      trailing_stop=None, cooldown=None):
    """
    整合TrendRider所有逻辑，供引擎调用
    
    返回: {
        "should_enter": bool,
        "enter_signal": str,
        "should_exit": bool,
        "exit_reason": str,
        "ema_trend": str,
        "confidence": float  # 0-100
    }
    """
    result = {
        "should_enter": False,
        "enter_signal": "",
        "should_exit": False,
        "exit_reason": "",
        "ema_trend": "neutral",
        "confidence": 0,
    }
    
    if len(closes) < 50:
        return result
    
    # 1. EMA方向判断
    result["ema_trend"] = check_ema_trend(closes)
    
    # 2. 入场信号（只在牛市或中性时入场）
    if result["ema_trend"] != "bear":
        if cooldown is None or cooldown.can_enter(symbol):
            should_enter, signal = check_entry_signals(closes, highs, lows, volumes)
            result["should_enter"] = should_enter
            result["enter_signal"] = signal
    
    # 3. 出场信号（追踪止损）
    if trailing_stop:
        should_exit, reason = trailing_stop.update(closes[-1])
        result["should_exit"] = should_exit
        result["exit_reason"] = reason
    
    # 4. 置信度评分
    confidence = 0
    if result["ema_trend"] == "bull": confidence += 30
    if result["should_enter"]: confidence += 40
    if result["enter_signal"]:
        signal_count = result["enter_signal"].count("+") + 1
        confidence += min(signal_count * 15, 30)
    result["confidence"] = min(confidence, 100)
    
    return result

if __name__ == '__main__':
    # 测试
    print("Testing TrendRider integration...")
    
    # 拉取BTC数据测试
    _, klines = public_get('/api/v3/klines', {'symbol': 'BTCUSDT', 'interval': '1h', 'limit': 300})
    if klines and len(klines) > 200:
        closes = [float(k[4]) for k in klines]
        highs = [float(k[2]) for k in klines]
        lows = [float(k[3]) for k in klines]
        vols = [float(k[5]) for k in klines]
        
        print(f"BTC EMA趋势: {check_ema_trend(closes)}")
        
        ts = TrailingStop(entry_price=closes[-50])
        for i in range(-49, 0):
            should_exit, reason = ts.update(closes[i])
        
        advice = trendrider_advice("BTC", closes, highs, lows, vols, ts)
        print(f"TrendRider建议: {json.dumps(advice, indent=2)}")
    else:
        print(f"BTC数据获取失败")
