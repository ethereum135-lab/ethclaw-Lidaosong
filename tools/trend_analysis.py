#!/usr/bin/env python3
"""
ZQ 三层趋势方向分析框架 v1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

老李定义：
  趋势方向分析不是"30分钟trend是+1还是-1"
  而是三件事：
    1. 发现吸筹（启动前就发现它）
    2. 确认启动（第一根阳线时进场）
    3. 趋势持有（让利润奔跑，不被洗出去）

数据支撑：
  从NOT案例（5/2-5/8涨87%）和BCH案例（持475分钟赚+3.29%）总结
"""

import json, os, sys
from datetime import datetime, timedelta
from collections import deque

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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

# ═══════════════════════════════════════════════════
# Layer 1: 吸筹期检测
# ═══════════════════════════════════════════════════

class AccumulationDetector:
    """
    检测币种是否处于"吸筹期"——大资金在悄悄买入，还没拉盘。
    
    NOT 案例验证（5/1-5/2）:
    - 价格在 $0.000378-$0.000390 之间窄幅震荡（振幅3%）
    - 成交量维持在2000-7000万，无异常量跳
    - 高低差逐步收窄 → 筹码集中
    
    评分: 0-100, >60 = 可能处于吸筹期
    """
    
    @staticmethod
    def analyze(closes, highs, lows, volumes):
        if len(closes) < 24:
            return {"score": 0, "signals": []}
        
        signals = []
        score = 0
        
        # ---- 信号1: 价格窄幅震荡 ----
        recent_high = max(highs[-24:])
        recent_low = min(lows[-24:])
        amplitude = (recent_high - recent_low) / recent_low * 100
        if amplitude < 5:
            score += 20
            signals.append(f"窄幅震荡({amplitude:.1f}%)")
        elif amplitude < 10:
            score += 10
            signals.append(f"小幅震荡({amplitude:.1f}%)")
        
        # ---- 信号2: 成交量稳定（不放量也不缩量） ----
        vol_recent = sum(volumes[-24:]) / 24
        vol_prev = sum(volumes[-48:-24]) / 24 if len(volumes) >= 48 else vol_recent
        vol_ratio = vol_recent / max(vol_prev, 0.01)
        if 0.8 <= vol_ratio <= 1.5:
            score += 20
            signals.append(f"量稳定(比{vol_ratio:.1f}x)")
        
        # ---- 信号3: 价格不创新低 ----
        lowest_12h = min(lows[-24:])
        lowest_24h = min(lows[-48:]) if len(lows) >= 48 else lowest_12h
        if lowest_12h >= lowest_24h * 0.99:
            score += 15
            signals.append("不创新低")
        
        # ---- 信号4: 高低差收窄（吸筹末期特征） ----
        if len(highs) >= 48:
            range_early = max(highs[-48:-24]) - min(lows[-48:-24])
            range_late = max(highs[-24:]) - min(lows[-24:])
            if range_late < range_early:
                score += 15
                signals.append("高低差收窄")
        
        # ---- 信号5: 底部放量（吸筹特征） ----
        # 偶尔出现1.5-3x的量跳但价格不涨（大单吃货）
        moderate_surges = sum(1 for i in range(-24, 0) if len(volumes) > abs(i) and 
                             volumes[i] > sum(volumes[-48:-24])/24 * 1.5
                             and volumes[i] < sum(volumes[-48:-24])/24 * 3)
        if moderate_surges >= 3:
            score += 20
            signals.append(f"吸筹放量({moderate_surges}次)")
        
        # ---- 信号6: EMA趋势 ----
        if len(closes) >= 50:
            ema50 = sum(closes[-50:]) / 50
            if closes[-1] > ema50 * 0.98:  # 价格在EMA50附近或以上
                score += 10
                signals.append("EMA50附近")
        
        return {
            "score": min(score, 100),
            "is_accumulating": score >= 50,
            "signals": signals,
            "amplitude_pct": round(amplitude, 2),
            "vol_ratio": round(vol_ratio, 2),
        }

# ═══════════════════════════════════════════════════
# Layer 2: 启动确认
# ═══════════════════════════════════════════════════

class LaunchDetector:
    """
    检测币种是否"刚刚启动"——第一根放量阳线。
    
    NOT 案例:
    5/2 14:00 — 量2.2x, 涨+2.31%, 突破横盘区间$0.000390→$0.000399
    5/2 15:00 — 量6x, 涨+1.00%, 最高$0.000407
    
    两个信号互相验证：先量跳确认，再价格突破确认。
    """
    
    @staticmethod
    def analyze(closes, highs, lows, opens, volumes):
        if len(closes) < 24:
            return {"is_launching": False, "confidence": 0, "signals": []}
        
        signals = []
        confidence = 0
        current_price = closes[-1]
        
        # 基线：前24根K线的均值
        baseline_vol = sum(volumes[-25:-1]) / 24 if len(volumes) >= 25 else sum(volumes) / len(volumes)
        baseline_price = sum(closes[-25:-1]) / 24 if len(closes) >= 25 else sum(closes) / len(closes)
        
        # ---- 信号A: 成交量突变 ----
        vol_surge = volumes[-1] / max(baseline_vol, 0.01)
        if vol_surge >= 3:
            confidence += 35
            signals.append(f"量爆{vol_surge:.1f}x")
        elif vol_surge >= 2:
            confidence += 25
            signals.append(f"量跳{vol_surge:.1f}x")
        elif vol_surge >= 1.5:
            confidence += 10
            signals.append(f"量增{vol_surge:.1f}x")
        
        # ---- 信号B: 价格突破 ----
        # 当前价格是否突破了横盘区间
        recent_high = max(highs[-24:-1]) if len(highs) > 24 else max(highs[:-1])
        price_breakout = (current_price - recent_high) / recent_high * 100
        if price_breakout > 2:
            confidence += 35
            signals.append(f"突破{price_breakout:+.1f}%")
        elif price_breakout > 1:
            confidence += 25
            signals.append(f"小突破{price_breakout:+.1f}%")
        
        # ---- 信号C: 当前K线收阳 ----
        if closes[-1] > opens[-1] if len(opens) > 0 else False:
            confidence += 10
            signals.append("收阳")
        
        # ---- 信号D: 多根连续放量 ----
        surges = sum(1 for i in range(-3, 0) if 
                    volumes[i] > baseline_vol * 1.5)
        if surges >= 2:
            confidence += 20
            signals.append(f"连续放量({surges}根)")
        
        return {
            "is_launching": confidence >= 50,
            "confidence": min(confidence, 100),
            "signals": signals,
            "vol_surge": round(vol_surge, 2),
            "price_breakout_pct": round(price_breakout, 2),
        }

# ═══════════════════════════════════════════════════
# Layer 3: 趋势持有（让利润奔跑）
# ═══════════════════════════════════════════════════

class TrendHolder:
    """
    趋势持有框架 — 解决"30分钟就卖"的致命问题。
    
    核心原则：
    1. 进场的唯一理由消失了才卖（不是机械条件触发就卖）
    2. 追踪止损保护利润（TrendRider的+5%激活，3%回撤）
    3. 硬止损保护本金（-3%无条件退出）
    
    NOT案例: 5/2进场→5/8卖出应该持有7天
    BCH案例: 持有475分钟（8小时），赚+3.29%
    """
    
    def __init__(self, entry_price, entry_time=None):
        self.entry_price = entry_price
        self.entry_time = entry_time or datetime.now()
        self.highest_price = entry_price
        self.highest_time = entry_time or datetime.now()
        self.consecutive_loss = 0  # 连续亏损次数
        
        # 追踪止损参数
        self.trail_activate = 0.05    # +5%激活
        self.trail_distance = 0.03    # 回撤3%止盈
        self.trail_activated = False
        
        # 硬止损
        self.hard_stop = -0.03        # -3%无条件割
    
    def update(self, current_price, current_time=None):
        """
        更新价格，返回 (should_exit, exit_reason, exit_price)
        
        退出优先级：
        1. 硬止损 (-3%)
        2. 追踪止损 (盈利>5%后回撤3%)
        3. E3趋势转跌（仅当趋势真正坏了才退）
        """
        pnl_pct = (current_price - self.entry_price) / self.entry_price * 100
        
        # 更新最高价
        if current_price > self.highest_price:
            self.highest_price = current_price
            self.highest_time = current_time or datetime.now()
        
        # 1. 硬止损（最高优先级）
        if pnl_pct <= self.hard_stop * 100:
            return True, f"硬止损({pnl_pct:.1f}%)", current_price
        
        # 2. 追踪止损
        if pnl_pct >= self.trail_activate * 100:
            self.trail_activated = True
        
        if self.trail_activated:
            drawdown = (self.highest_price - current_price) / self.highest_price * 100
            if drawdown >= self.trail_distance * 100:
                exit_price = self.highest_price * (1 - self.trail_distance)
                return True, f"追踪止盈(最高{self.highest_price:.4f},回撤{drawdown:.1f}%)", exit_price
        
        return False, "持有", current_price

# ═══════════════════════════════════════════════════
# 完整趋势方向分析
# ═══════════════════════════════════════════════════

def full_trend_analysis(symbol, closes, highs, lows, opens, volumes):
    """
    三合一趋势方向分析——供引擎调用
    
    返回: {
        "accumulation": {...},  # Layer 1 吸筹
        "launch": {...},        # Layer 2 启动
        "overall": str,         # "accumulating" | "launching" | "trending" | "no_signal"
        "recommendation": str,  # 建议动作
    }
    """
    # Layer 1
    acc = AccumulationDetector.analyze(closes, highs, lows, volumes)
    
    # Layer 2
    launch = LaunchDetector.analyze(closes, highs, lows, opens, volumes)
    
    # 综合判断
    overall = "no_signal"
    recommendation = "等待"
    
    if launch["is_launching"]:
        overall = "launching"
        recommendation = f"🚀 启动信号({'+'.join(launch['signals'])})"
    elif acc["is_accumulating"]:
        overall = "accumulating"
        recommendation = f"📦 吸筹期({acc['score']}分,{','.join(acc['signals'])})"
    elif len(closes) > 50:
        ema50 = sum(closes[-50:]) / 50
        if closes[-1] > ema50:
            overall = "trending"
            recommendation = "📈 趋势中"
    
    return {
        "symbol": symbol,
        "accumulation": acc,
        "launch": launch,
        "overall": overall,
        "recommendation": recommendation,
    }

def main():
    """测试：用NOT数据验证三层框架"""
    import sys
    
    coins = sys.argv[1:] if len(sys.argv) > 1 else ["NOT"]
    
    for coin in coins:
        print(f"\n{'='*60}")
        print(f"  {coin} 趋势方向分析")
        print(f"{'='*60}")
        
        _, klines = public_get(f'/api/v3/klines?symbol={coin}USDT&interval=30m&limit=200')
        if not klines or len(klines) < 50:
            print(f"  ❌ 数据不足")
            continue
        
        closes = [float(k[4]) for k in klines]
        highs = [float(k[2]) for k in klines]
        lows = [float(k[3]) for k in klines]
        opens = [float(k[1]) for k in klines]
        volumes = [float(k[5]) for k in klines]
        
        # 分析每个时间点
        print(f"\n  {'时间':<20}{'吸筹分':<8}{'启动确信':<10}{'状态':<16}{'推荐'}")
        print(f"  {'-'*60}")
        
        for i in range(48, len(closes), 4):  # 每2小时采样一次
            sub_closes = closes[:i+1]
            sub_highs = highs[:i+1]
            sub_lows = lows[:i+1]
            sub_opens = opens[:i+1]
            sub_vols = volumes[:i+1]
            
            result = full_trend_analysis(coin, sub_closes, sub_highs, sub_lows, sub_opens, sub_vols)
            ts = datetime.utcfromtimestamp(klines[i][0]/1000).strftime("%m-%d %H:%M")
            
            acc_score = result['accumulation']['score']
            launch_conf = result['launch']['confidence']
            
            print(f"  {ts:<20}{acc_score:<8}{launch_conf:<10}{result['overall']:<16}{result['recommendation'][:30]}")

if __name__ == '__main__':
    main()
