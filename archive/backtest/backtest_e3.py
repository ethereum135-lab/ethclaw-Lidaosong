#!/usr/bin/env python3
"""
ZQ E3逻辑对比回测 v1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

对比旧E3(trend<0就退) vs 新E3(-2才退/急跌才退)
用真实历史数据回测，用数据说话

用法:
  python3 tools/backtest_e3.py                    # 默认跑TOP10交易币
  python3 tools/backtest_e3.py --coins NOT,BCH,FIL  # 指定币种
  python3 tools/backtest_e3.py --days 60           # 更长周期
"""
import sys, os, json, time
from datetime import datetime, timedelta
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

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

# ─── 趋势计算（和引擎完全一致） ───
def calc_trend(closes):
    """趋势评分 -2~+2"""
    if len(closes) < 4:
        return 0
    recent = closes[-4:]
    avg = sum(recent) / 4
    prev = closes[-5] if len(closes) >= 5 else closes[0]
    if avg > prev * 1.005:
        return 2
    elif avg > prev * 1.001:
        return 1
    elif avg < prev * 0.995:
        return -2
    elif avg < prev * 0.999:
        return -1
    return 0

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

# ─── E3旧逻辑 ───
def old_e3(trend, prev_trend, is_new):
    if is_new and trend < 0 and trend > -2:
        return False, "新入场保护"
    elif trend < 0:
        return True, f"E3 趋势转跌({trend})"
    return False, "不触发"

# ─── E3新逻辑 ───
def new_e3(trend, prev_trend, is_new):
    if trend == -2:
        return True, f"E3 趋势转跌({trend})"
    elif trend == -1 and prev_trend >= 1:
        return True, f"E3 趋势急跌({prev_trend}→{trend})"
    return False, "不触发"

# ─── 回测单个币 ───
def backtest_coin(symbol, klines, e3_func, label):
    """
    简单的趋势跟踪回测：
    - 入场：30min趋势从0/负变成+1/+2（启动信号）
    - 出场：E3条件触发 或 P1(RSI>70) 或 硬止损-3%
    - 30分钟节点，和目标系统一致
    """
    if not klines or len(klines) < 20:
        return {"trades": 0, "pnl": 0, "win_rate": 0, "label": label}
    
    closes = [float(k[4]) for k in klines]
    highs = [float(k[2]) for k in klines]
    lows = [float(k[3]) for k in klines]
    times = [k[0] for k in klines]
    
    trades = []
    in_position = False
    entry_price = 0
    entry_idx = 0
    prev_trend = 0
    
    for i in range(20, len(closes)):
        lookback = closes[max(0,i-16):i+1]
        trend = calc_trend(lookback)
        rsi = calc_rsi(lookback)
        
        if i > 20:
            prev_trend = calc_trend(closes[max(0,i-17):i])
        
        if not in_position:
            # 入场条件：趋势从≤0变成>0（启动）
            if trend >= 1 and prev_trend <= 0:
                entry_price = closes[i]
                entry_idx = i
                in_position = True
        else:
            # 持仓中
            hold_minutes = (i - entry_idx) * 30
            is_new = hold_minutes < 90  # 新入场90分钟保护
            
            # 计算浮亏
            current_pnl_pct = (closes[i] - entry_price) / entry_price * 100
            
            # 检查出场
            e3_triggered, e3_reason = e3_func(trend, prev_trend, is_new)
            
            # P1: RSI超买(>70)并且不是在保护期
            p1_triggered = rsi > 70 and not is_new
            
            # 硬止损
            stop_triggered = current_pnl_pct < -3
            
            if e3_triggered or p1_triggered or stop_triggered:
                exit_price = closes[i]
                if stop_triggered:
                    # 用最低价算止损（更真实）
                    exit_price = min(closes[i], entry_price * 0.97)
                
                pnl = (exit_price - entry_price) / entry_price * 100
                reasons = []
                if e3_triggered: reasons.append(e3_reason)
                if p1_triggered: reasons.append("P1 RSI超买")
                if stop_triggered: reasons.append("硬止损-3%")
                
                trades.append({
                    "entry_time": str(datetime.utcfromtimestamp(times[entry_idx]/1000)),
                    "exit_time": str(datetime.utcfromtimestamp(times[i]/1000)),
                    "hold_minutes": hold_minutes,
                    "pnl_pct": round(pnl, 2),
                    "reason": "; ".join(reasons),
                })
                in_position = False
    
    # 计算统计
    if not trades:
        return {"trades": 0, "pnl": 0, "win_rate": 0, "label": label, "symbol": symbol}
    
    total_pnl = sum(t["pnl_pct"] for t in trades)
    wins = [t for t in trades if t["pnl_pct"] > 0]
    win_rate = len(wins) / len(trades) * 100
    avg_hold = sum(t["hold_minutes"] for t in trades) / len(trades)
    avg_win = sum(t["pnl_pct"] for t in trades if t["pnl_pct"] > 0) / max(len(wins), 1)
    losses = [t for t in trades if t["pnl_pct"] <= 0]
    avg_loss = sum(t["pnl_pct"] for t in losses) / max(len(losses), 1)
    
    return {
        "label": label,
        "symbol": symbol,
        "trades": len(trades),
        "total_pnl_pct": round(total_pnl, 2),
        "win_rate": round(win_rate, 1),
        "avg_hold_min": round(avg_hold, 0),
        "avg_win_pct": round(avg_win, 2),
        "avg_loss_pct": round(avg_loss, 2),
        "profit_factor": round(abs(sum(t["pnl_pct"] for t in wins) / max(abs(sum(t["pnl_pct"] for t in losses)), 0.01)), 2),
    }

# ─── 主函数 ───
def main():
    # 获取系统实际交易过的币种（从TRADES.md）
    trades_file = os.path.join(BASE_DIR, 'audit', 'TRADES.md')
    traded_coins = set()
    if os.path.exists(trades_file):
        with open(trades_file) as f:
            for line in f:
                if 'BUY' in line and 'USDT' not in line:
                    parts = line.split('|')
                    if len(parts) >= 4:
                        coin = parts[3].strip()
                        if coin and coin != '-':
                            traded_coins.add(coin)
        # 去掉稳定币和无效币
        exclude = ['XUSD', 'USDT', 'USDC', 'FDUSD']
        traded_coins = [c for c in traded_coins if c not in exclude]
    
    # 如果命令行指定了就优先
    if '--coins' in sys.argv:
        idx = sys.argv.index('--coins')
        traded_coins = [c.strip().upper() for c in sys.argv[idx+1].split(',')]
    
    if not traded_coins:
        traded_coins = ['NOT', 'BCH', 'TRX', 'SOL', 'NEAR', 'DOGE', 'AAVE', 'BNB', 'XLM', 'ADA']
    
    days_back = 30
    if '--days' in sys.argv:
        idx = sys.argv.index('--days')
        days_back = int(sys.argv[idx+1])
    
    print(f"\n{'='*70}")
    print(f"  E3逻辑回测对比 — {days_back}天历史数据")
    print(f"  回测币种: {', '.join(traded_coins[:15])}{'...' if len(traded_coins)>15 else ''}")
    print(f"{'='*70}\n")
    
    old_results = []
    new_results = []
    
    for coin in traded_coins[:15]:  # 最多15个币
        symbol = f"{coin}USDT"
        print(f"  📥 拉取 {coin} 数据...", end=' ')
        
        # 拉取30分钟K线
        limit = days_back * 48  # 30分钟 * 48 = 1天
        _, klines = public_get('/api/v3/klines', {'symbol': symbol, 'interval': '30m', 'limit': limit})
        
        if not klines or len(klines) < 30:
            print(f"❌ 数据不足")
            continue
        
        print(f"{len(klines)}根K线")
        
        # 旧E3回测
        old_result = backtest_coin(coin, klines, old_e3, "旧E3(trend<0就退)")
        old_result['symbol'] = coin
        old_results.append(old_result)
        
        # 新E3回测
        new_result = backtest_coin(coin, klines, new_e3, "新E3(-2/急跌才退)")
        new_result['symbol'] = coin
        new_results.append(new_result)
    
    # ─── 输出结果 ───
    print(f"\n{'='*70}")
    print(f"  对比结果")
    print(f"{'='*70}")
    print(f"{'币种':<8}{'旧E3-交易':<10}{'旧E3-总盈亏':<14}{'旧E3-胜率':<10}{'新E3-交易':<10}{'新E3-总盈亏':<14}{'新E3-胜率':<10}")
    print("-"*70)
    
    total_old_pnl, total_new_pnl = 0, 0
    for o, n in zip(old_results, new_results):
        old_pnl = o.get('total_pnl_pct', 0)
        new_pnl = n.get('total_pnl_pct', 0)
        total_old_pnl += old_pnl
        total_new_pnl += new_pnl
        print(f"{o['symbol']:<8}{o.get('trades',0):<10}{old_pnl:>+8.2f}%{'':<5}{n.get('trades',0):<10}{new_pnl:>+8.2f}%{'':<5}{n.get('win_rate',0):<8}%")
    
    print("-"*70)
    print(f"{'合计':<8}{'':<10}{total_old_pnl:>+8.2f}%{'':<5}{'':<10}{total_new_pnl:>+8.2f}%")
    
    # 详细总结
    print(f"\n{'='*70}")
    print(f"  旧E3 平均 | 交易:{sum(o.get('trades',0) for o in old_results)}次 | "
          f"胜率:{sum(o.get('win_rate',0) for o in old_results)/max(len(old_results),1):.1f}% | "
          f"平均持仓:{sum(o.get('avg_hold_min',0) for o in old_results)/max(len(old_results),1):.0f}min")
    print(f"  新E3 平均 | 交易:{sum(n.get('trades',0) for n in new_results)}次 | "
          f"胜率:{sum(n.get('win_rate',0) for n in new_results)/max(len(new_results),1):.1f}% | "
          f"平均持仓:{sum(n.get('avg_hold_min',0) for n in new_results)/max(len(new_results),1):.0f}min")
    print(f"{'='*70}")
    
    # 保存结果
    result = {
        "date": str(datetime.utcnow()),
        "days_back": days_back,
        "old_e3": {
            "total_trades": sum(o.get('trades',0) for o in old_results),
            "total_pnl": round(total_old_pnl, 2),
            "avg_win_rate": round(sum(o.get('win_rate',0) for o in old_results)/max(len(old_results),1), 1),
        },
        "new_e3": {
            "total_trades": sum(n.get('trades',0) for n in new_results),
            "total_pnl": round(total_new_pnl, 2),
            "avg_win_rate": round(sum(n.get('win_rate',0) for n in new_results)/max(len(new_results),1), 1),
        },
    }
    
    result_path = os.path.join(BASE_DIR, 'data', 'backtest_e3_result.json')
    with open(result_path, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"\n✅ 结果已保存到 {result_path}")

if __name__ == '__main__':
    main()
