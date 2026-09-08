#!/usr/bin/env python3
"""
ZQ Trading Strategy Framework — 受 QuantDinger 启发
==================================================
设计原则：
1. 指标层 → 信号层 → 风险配置层，三层分离
2. 策略 = 一句话可执行的规则，不是条件矩阵
3. 任何新策略必须先回测再上实盘
"""
import json, os, sys
from datetime import datetime, timezone, timedelta
from typing import Optional

BJT = timezone(timedelta(hours=8))
DATA_DIR = os.path.expanduser("~/zq_web4_trading_system/data")

# === 策略基类 ===

class Strategy:
    """策略基类 — 所有策略继承此接口"""
    name = "base"
    description = ""
    
    # 默认风险配置（引擎读取）
    stop_loss_pct = 0.05      # -5% 硬止损
    take_profit_pct = 0.0     # 0 = 无止盈（让赢家跑）
    trailing_activate = 0.05  # 浮盈5%后启动跟踪
    trailing_stop = 0.03      # 跟踪距离3%
    max_position_pct = 0.15   # 单笔最大15%资金
    trade_direction = "long"  # long|short|both
    
    def indicators(self, df):
        """Step 1: 计算指标 — 返回带指标列的df"""
        return df
    
    def signals(self, df):
        """Step 2: 生成信号 — 设置 df['buy'] 和 df['sell'] 布尔列"""
        df['buy'] = False
        df['sell'] = False
        return df
    
    def run(self, df):
        """完整运行管线"""
        df = self.indicators(df)
        df = self.signals(df)
        return df


# === 内建策略 1: 涨幅榜动量策略 ===

class GainMomentumStrategy(Strategy):
    """
    一句话策略：涨幅榜3-15% + 量比≥1.5x + RSI(4h)<70 → 买入
    止损：-5%硬止损 | 出场：RSI>85 或 跟踪止损3%
    """
    name = "gain_momentum"
    description = "涨幅榜动量策略 — 抄涨不抄顶"
    
    # 可调参数
    min_gain = 3.0
    max_gain = 15.0
    min_vol_ratio = 1.5
    max_rsi = 70
    rsi_sell = 85
    
    def indicators(self, df):
        """计算RSI和量比"""
        if len(df) < 20:
            return df
        
        # RSI计算
        delta = df['close'].diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()
        rs = avg_gain / avg_loss.replace(0, 1e-10)
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 量比（当前量 / 过去20根均值）
        df['vol_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
        
        # 涨跌幅（相对前一根close）
        df['pct_change'] = df['close'].pct_change(fill_method=None)
        
        return df
    
    def signals(self, df):
        df['buy'] = False
        df['sell'] = False
        
        if len(df) < 20:
            return df
        
        last = df.iloc[-1]
        
        # 买入条件：24h涨幅在3-15%之间 + 量比≥1.5 + RSI<70
        gain_ok = self.min_gain <= last.get('pct_change_24h', 0) <= self.max_gain
        vol_ok = last.get('vol_ratio', 0) >= self.min_vol_ratio
        rsi_ok = last.get('rsi', 50) < self.max_rsi
        
        if gain_ok and vol_ok and rsi_ok:
            df.iloc[-1, df.columns.get_loc('buy')] = True
        
        # 卖出条件：RSI>85 或 无持仓用False
        if last.get('rsi', 0) >= self.rsi_sell:
            df.iloc[-1, df.columns.get_loc('sell')] = True
        
        return df


# === 内建策略 2: 超跌反弹策略 ===

class OversoldBounceStrategy(Strategy):
    """
    一句话策略：连跌3天 + RSI<30 + 量缩 → 买入
    止损：-3% | 止盈：+6% 或 跟踪止损
    """
    name = "oversold_bounce"
    description = "超跌反弹策略 — 恐慌买入"
    
    min_consecutive_loss = 3
    rsi_floor = 30
    stop_loss_pct = 0.03
    take_profit_pct = 0.06
    
    def indicators(self, df):
        if len(df) < 20:
            return df
        
        delta = df['close'].diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()
        rs = avg_gain / avg_loss.replace(0, 1e-10)
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 连跌天数
        df['consecutive_down'] = 0
        down_count = 0
        for i in range(len(df)):
            if i > 0 and df.iloc[i]['close'] < df.iloc[i-1]['close']:
                down_count += 1
            else:
                down_count = 0
            df.iloc[i, df.columns.get_loc('consecutive_down')] = down_count
        
        return df
    
    def signals(self, df):
        df['buy'] = False
        df['sell'] = False
        if len(df) < 20:
            return df
        last = df.iloc[-1]
        if last['consecutive_down'] >= self.min_consecutive_loss and last['rsi'] < self.rsi_floor:
            df.iloc[-1, df.columns.get_loc('buy')] = True
        return df


# === 策略注册表 ===

STRATEGIES = {
    "gain_momentum": GainMomentumStrategy,
    "oversold_bounce": OversoldBounceStrategy,
}

def get_strategy(name: str) -> Optional[Strategy]:
    cls = STRATEGIES.get(name)
    return cls() if cls else None


# === 简易回测引擎（受 QuantDinger 回测设计启发） ===

def backtest(strategy_name: str, klines: list, initial_capital: float = 1000.0):
    """
    简易回测 — 验证策略是否赚钱
    返回：资金曲线、交易记录、胜率、最大回撤
    """
    import pandas as pd
    
    # 构建DataFrame
    df = pd.DataFrame([{
        'time': k[0],
        'open': float(k[1]),
        'high': float(k[2]),
        'low': float(k[3]),
        'close': float(k[4]),
        'volume': float(k[5])
    } for k in klines])
    
    # 计算24h涨跌幅（模拟涨幅榜数据）
    if len(df) >= 24:  # 4h K-line, 24根 = 4天数据
        df['pct_change_24h'] = df['close'].pct_change(6, fill_method=None) * 100  # 6根4h=24h
    
    strategy = get_strategy(strategy_name)
    if not strategy:
        return {"error": f"Unknown strategy: {strategy_name}"}
    
    df = strategy.run(df)
    
    # 模拟交易
    capital = initial_capital
    position = 0.0
    entry_price = 0.0
    trades = []
    equity_curve = []
    
    for i in range(1, len(df)):
        row = df.iloc[i]
        
        # 记录净值
        pos_value = position * row['close'] if position > 0 else 0
        equity_curve.append({"time": row['time'], "equity": capital + pos_value})
        
        # 卖出
        if position > 0 and row['sell']:
            exit_val = position * row['close']
            pnl = exit_val - (position * entry_price)
            trades.append({
                "type": "sell",
                "time": row['time'],
                "price": row['close'],
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl / (position * entry_price) * 100, 2)
            })
            capital += exit_val
            position = 0.0
        
        # 买入
        elif position == 0 and row['buy'] and capital > 10:
            pos_size = capital * strategy.max_position_pct
            position = pos_size / row['close']
            entry_price = row['close']
            capital -= pos_size
            trades.append({
                "type": "buy",
                "time": row['time'],
                "price": row['close'],
                "amount": round(pos_size, 2)
            })
    
    # 平仓剩余持仓
    if position > 0:
        exit_val = position * df.iloc[-1]['close']
        pnl = exit_val - (position * entry_price)
        trades.append({
            "type": "sell_final",
            "time": df.iloc[-1]['time'],
            "price": df.iloc[-1]['close'],
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl / (position * entry_price) * 100, 2)
        })
        capital += exit_val
    
    # 统计
    wins = [t for t in trades if t.get('pnl', 0) > 0]
    losses = [t for t in trades if t.get('pnl', 0) < 0]
    total_pnl = capital - initial_capital
    
    # 最大回撤
    peak = initial_capital
    max_dd = 0
    for e in equity_curve:
        if e['equity'] > peak:
            peak = e['equity']
        dd = (peak - e['equity']) / peak
        if dd > max_dd:
            max_dd = dd
    
    return {
        "strategy": strategy_name,
        "initial_capital": initial_capital,
        "final_capital": round(capital, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl / initial_capital * 100, 2),
        "total_trades": len(trades),
        "win_trades": len(wins),
        "loss_trades": len(losses),
        "win_rate": round(len(wins) / len(trades) * 100, 1) if trades else 0,
        "max_drawdown": round(max_dd * 100, 2),
        "trades": trades[-20:],  # 最近20笔
        "avg_win": round(sum(t.get('pnl', 0) for t in wins) / len(wins), 2) if wins else 0,
        "avg_loss": round(sum(t.get('pnl', 0) for t in losses) / len(losses), 2) if losses else 0,
    }


# === 命令行 ===

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "backtest":
        strategy = sys.argv[2] if len(sys.argv) > 2 else "gain_momentum"
        print(f"📊 回测策略: {strategy}")
        print("使用方法: 传入K线数据或从Binance API拉取")
        print("示例: python3 strategy_framework.py backtest gain_momentum")
    
    elif len(sys.argv) > 1 and sys.argv[1] == "list":
        print("📋 可用策略:")
        for name, cls in STRATEGIES.items():
            s = cls()
            print(f"  {name}: {s.description}")
    
    else:
        print("🧊 ZQ 策略框架 v1")
        print(f"  已注册策略: {len(STRATEGIES)} 个")
        print("  用法: python3 strategy_framework.py list")
        print("        python3 strategy_framework.py backtest <strategy_name>")
