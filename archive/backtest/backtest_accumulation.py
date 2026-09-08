#!/usr/bin/env python3
"""
ZQ Web 4.0 吸筹策略回测 v1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

测试核心问题：
  吸筹排序（新逻辑） vs 成交量排序（旧逻辑）
  哪个选出的币后续走势更好？

方法：
  1. 取过去7天所有30m K线
  2. 在每个30m节点计算两种排序
  3. 各取Top3模拟买入
  4. 持4小时(8根K线)后看盈亏
  5. 对比胜率、平均收益、最大回撤

结果解读：
  - 胜率高+收益正 = 策略有效
  - 胜率低+收益负 = 策略无效
  - 胜率不高但平均收益高 = 能抓到大的
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import json, os, sys, time
from datetime import datetime, timezone, timedelta
import numpy as np
from collections import defaultdict

BJT = timezone(timedelta(hours=8))
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def fetch_klines(client, symbol, interval='30m', days=7):
    """获取历史K线"""
    all_klines = []
    end_time = int(time.time() * 1000)
    start_time = end_time - days * 86400 * 1000
    
    while start_time < end_time:
        klines = client.get_klines(
            symbol=symbol, interval=interval,
            startTime=start_time, limit=500
        )
        if not klines:
            break
        all_klines.extend(klines)
        start_time = klines[-1][0] + 1
        time.sleep(0.15)
    
    return all_klines

def rsi(closes, period=14):
    """简化RSI计算"""
    if len(closes) < period + 1:
        return 50
    gains = 0
    losses = 0
    for i in range(len(closes) - period, len(closes)):
        diff = closes[i] - closes[i-1]
        if diff > 0:
            gains += diff
        else:
            losses += abs(diff)
    if losses == 0:
        return 100 if gains > 0 else 50
    rs = gains / losses
    return 100 - 100 / (1 + rs)

def calc_accumulation_score(closes, vols):
    """
    吸筹评分（同 coin_pool_manager.py 的计算）
    分数越高 = 蓄力越好 = 值得关注
    """
    score = 0
    details = {}
    
    if len(closes) < 5 or len(vols) < 5:
        return 0, {}
    
    # 量比
    prev3 = sum(vols[-4:-1]) / 3 if len(vols) >= 4 else 1
    vol_ratio = vols[-1] / prev3 if prev3 > 0 else 1
    
    # 4h趋势（从8根30m K线估算）
    if len(closes) >= 12:
        trend_4h = sum(1 for j in range(1, 9) if closes[-j] > closes[-j-1]) - sum(1 for j in range(1, 9) if closes[-j] < closes[-j-1])
        trend_4h = max(-2, min(2, trend_4h // 3))
    else:
        trend_4h = 0
    
    # RSI
    rsi_val = rsi(closes, 14)
    
    # 24h涨幅
    if len(closes) >= 48:
        change_24h = (closes[-1] - closes[-48]) / closes[-48] * 100
    else:
        change_24h = 0
    
    # 近24h高低点
    lookback = min(48, len(closes))
    high_24 = max(closes[-lookback:])
    low_24 = min(closes[-lookback:])
    curr = closes[-1]
    pos = (curr - low_24) / (high_24 - low_24) if (high_24 - low_24) > 0 else 0.5
    
    # 量比评分
    if 0.8 <= vol_ratio <= 1.5:
        score += 25
    elif vol_ratio <= 2.0:
        score += 10
    elif vol_ratio > 2.0:
        score -= 10
    else:
        score -= 5
    
    # 趋势评分
    if trend_4h >= 1:
        score += 20
    elif trend_4h == 0:
        score += 5
    else:
        score -= 20
    
    # RSI评分
    if 30 <= rsi_val <= 50:
        score += 25
    elif 50 < rsi_val <= 60:
        score += 15
    elif 60 < rsi_val <= 70:
        score += 5
    elif rsi_val > 70:
        score -= 10
    else:
        score -= 5
    
    # 涨幅评分
    if -3 <= change_24h <= 3:
        score += 20
    elif 3 < change_24h <= 8:
        score += 10
    elif 8 < change_24h <= 15:
        score -= 5
    elif change_24h > 15:
        score -= 15
    elif -8 <= change_24h < -3:
        score += 5
    else:
        score -= 5
    
    # 价格位置评分
    if pos < 0.3:
        score += 15
    elif pos < 0.5:
        score += 10
    elif pos > 0.7:
        score -= 10
    
    return score, {
        'vol_ratio': round(vol_ratio, 2),
        'trend_4h': trend_4h,
        'rsi': round(rsi_val, 1),
        'change_24h': round(change_24h, 2),
        'pos': round(pos, 2)
    }

def run_backtest():
    """跑完整回测"""
    print("=" * 70)
    print("  📊 ZQ 吸筹策略回测")
    print("=" * 70)
    
    # 连接Binance
    from binance.client import Client
    auth = json.load(open(os.path.join(BASE, 'config', 'auth.json')))
    client = Client(auth['binance']['api_key'], auth['binance']['api_secret'])
    
    # 读取选币库获取master池
    pool = json.load(open(os.path.join(BASE, 'data', 'coin_pool.json')))
    master_coins = [c['symbol'] + 'USDT' for c in pool['pools']['master'][:50]]
    
    print(f"\n  回测币种: {len(master_coins)}个 (master池Top50)")
    print(f"  时间范围: 过去7天 (30m K线)")
    
    # 拉取所有币的历史数据
    coin_data = {}
    total = len(master_coins)
    
    for i, symbol in enumerate(master_coins):
        print(f"  [{i+1}/{total}] {symbol}...", end=' ')
        try:
            klines = fetch_klines(client, symbol, '30m', 7)
            if klines and len(klines) > 48:
                coin_data[symbol] = klines
                print(f"{len(klines)}根K线")
            else:
                print("数据不足")
        except Exception as e:
            print(f"失败: {e}")
        time.sleep(0.1)
    
    # 找出所有共有的时间戳
    # 按时间戳对齐所有币的数据
    print(f"\n  数据获取完成: {len(coin_data)}个币有完整数据")
    
    # 构建时间线
    # 每根K线的open time作为节点
    time_nodes = []
    for sym, klines in coin_data.items():
        for k in klines:
            ts = k[0]
            if ts not in time_nodes:
                time_nodes.append(ts)
    time_nodes.sort()
    
    print(f"  总节点数: {len(time_nodes)}个 (约{len(time_nodes)//48}天)")
    
    # ============ 回测主逻辑 ============
    vol_trades = []   # 成交量排序的交易记录
    acc_trades = []   # 吸筹排序的交易记录
    
    # 每4小时采样一次（8根30m K线）
    step = 8
    
    for idx in range(48, len(time_nodes) - step, step):
        current_ts = time_nodes[idx]
        future_ts = time_nodes[idx + step]
        
        # 在current_ts这个时间点，计算所有币的两种排序
        vol_scores = []     # (symbol, volume_24h, score)
        acc_scores = []     # (symbol, accumulation_score, details)
        
        for sym, klines in coin_data.items():
            # 找到离current_ts最近的K线
            prices_at_time = [k for k in klines if k[0] <= current_ts]
            if len(prices_at_time) < 48:
                continue
            
            k = prices_at_time[-1]
            closes = [float(c[4]) for c in prices_at_time[-48:]]
            vols = [float(c[5]) for c in prices_at_time[-48:]]
            current_price = float(k[4])
            
            # 成交量（近似24h成交量）
            vol_24h = sum(float(c[5]) for c in prices_at_time[-48:])
            
            vol_scores.append((sym, vol_24h, current_price))
            
            # 吸筹评分
            acc_sc, details = calc_accumulation_score(closes, vols)
            acc_scores.append((sym, acc_sc, current_price, details))
        
        if len(vol_scores) < 10 or len(acc_scores) < 10:
            continue
        
        # 成交量排序取Top3
        vol_top3 = sorted(vol_scores, key=lambda x: -x[1])[:3]
        # 吸筹排序取Top3
        acc_top3 = sorted(acc_scores, key=lambda x: -x[1])[:3]
        
        # 模拟买入，持8根K线(4小时)后看结果
        for sym, _, entry_price in vol_top3:
            future_klines = [k for k in coin_data.get(sym, []) if k[0] > current_ts and k[0] <= future_ts]
            if future_klines:
                exit_price = float(future_klines[-1][4])
                ret = (exit_price - entry_price) / entry_price * 100
                vol_trades.append({
                    'time': datetime.fromtimestamp(current_ts/1000, BJT).strftime('%m-%d %H:%M'),
                    'symbol': sym,
                    'entry': entry_price,
                    'exit': exit_price,
                    'return': round(ret, 2)
                })
        
        for sym, _, entry_price, details in acc_top3:
            future_klines = [k for k in coin_data.get(sym, []) if k[0] > current_ts and k[0] <= future_ts]
            if future_klines:
                exit_price = float(future_klines[-1][4])
                ret = (exit_price - entry_price) / entry_price * 100
                acc_trades.append({
                    'time': datetime.fromtimestamp(current_ts/1000, BJT).strftime('%m-%d %H:%M'),
                    'symbol': sym,
                    'entry': entry_price,
                    'exit': exit_price,
                    'return': round(ret, 2),
                    'details': details
                })
    
    # ============ 结果分析 ============
    print(f"\n{'='*70}")
    print("  📊 回测结果")
    print(f"{'='*70}")
    
    for name, trades in [('📗 成交量排序（旧逻辑）', vol_trades), ('📘 吸筹排序（新逻辑）', acc_trades)]:
        if not trades:
            continue
        
        returns = [t['return'] for t in trades]
        wins = [t for t in trades if t['return'] > 0]
        losses = [t for t in trades if t['return'] <= 0]
        
        print(f"\n  {name}")
        print(f"  {'─'*50}")
        print(f"  总交易: {len(trades)}笔")
        print(f"  盈利: {len(wins)}笔 ({len(wins)/len(trades)*100:.1f}%)")
        print(f"  亏损: {len(losses)}笔 ({len(losses)/len(trades)*100:.1f}%)")
        print(f"  平均收益: {np.mean(returns):+.2f}%")
        print(f"  中位数收益: {np.median(returns):+.2f}%")
        print(f"  最大收益: {max(returns):+.2f}%")
        print(f"  最大亏损: {min(returns):+.2f}%")
        print(f"  收益>2%: {len([t for t in trades if t['return']>2])}笔")
        print(f"  亏损>2%: {len([t for t in trades if t['return']<-2])}笔")
        
        # 收益分布
        print(f"  收益分布:")
        for bucket, label in [(-5, '<-5%'), (-2, '-5%~-2%'), (0, '-2%~0'), (2, '0~2%'), (5, '2%~5%'), (99, '>5%')]:
            count = len([t for t in trades if t['return'] < bucket])
            if label == '<-5%':
                pass  # handled below
        # Manual distribution
        ranges = [(-99, -5, '<-5%'), (-5, -2, '-5%~-2%'), (-2, 0, '-2%~0%'), (0, 2, '0%~2%'), (2, 5, '2%~5%'), (5, 99, '>5%')]
        for lo, hi, label in ranges:
            count = len([t for t in trades if lo < t['return'] <= hi])
            if count > 0:
                bar = '█' * count
                print(f"    {label:>8}: {count:3d}笔 {bar}")
        
        # Top3最佳和最差
        top3 = sorted(trades, key=lambda x: -x['return'])[:3]
        worst3 = sorted(trades, key=lambda x: x['return'])[:3]
        best_str = ', '.join([f'{t["symbol"]}({t["return"]:+.2f}%)' for t in top3])
        worst_str = ', '.join([f'{t["symbol"]}({t["return"]:+.2f}%)' for t in worst3])
        print(f"  最佳3笔: {best_str}")
        print(f"  最差3笔: {worst_str}")
    
    # 对比总结
    print(f"\n{'='*70}")
    print("  🎯 对比总结")
    print(f"{'='*70}")
    
    vol_ret = [t['return'] for t in vol_trades] if vol_trades else []
    acc_ret = [t['return'] for t in acc_trades] if acc_trades else []
    
    if vol_ret and acc_ret:
        vol_win_rate = len([r for r in vol_ret if r > 0]) / len(vol_ret) * 100
        acc_win_rate = len([r for r in acc_ret if r > 0]) / len(acc_ret) * 100
        
        print(f"\n  {'指标':<20} {'成交量排序':>12} {'吸筹排序':>12} {'差值':>10}")
        print(f"  {'─'*56}")
        print(f"  {'胜率':<20} {vol_win_rate:>10.1f}% {acc_win_rate:>10.1f}% {(acc_win_rate-vol_win_rate):>+9.1f}%")
        print(f"  {'平均收益':<20} {np.mean(vol_ret):>+10.2f}% {np.mean(acc_ret):>+10.2f}% {(np.mean(acc_ret)-np.mean(vol_ret)):>+9.2f}%")
        print(f"  {'中位数收益':<20} {np.median(vol_ret):>+10.2f}% {np.median(acc_ret):>+10.2f}% {(np.median(acc_ret)-np.median(vol_ret)):>+9.2f}%")
        
        acc_gt2 = len([r for r in acc_ret if r > 2])
        vol_gt2 = len([r for r in vol_ret if r > 2])
        print(f"  {'捕捉大涨(>2%)':<20} {vol_gt2:>10d}笔 {acc_gt2:>10d}笔 {(acc_gt2-vol_gt2):>+9d}")
        
        conclusion = ""
        if acc_win_rate > vol_win_rate and np.mean(acc_ret) > np.mean(vol_ret):
            conclusion = "✅ 吸筹策略在所有维度上优于成交量策略"
        elif acc_win_rate > vol_win_rate:
            conclusion = "✅ 吸筹策略胜率更高，可继续优化"
        elif np.mean(acc_ret) > np.mean(vol_ret):
            conclusion = "⚠️ 吸筹策略平均收益更高但胜率略低，能抓到大的"
        else:
            conclusion = "❌ 吸筹策略当前未优于成交量策略，需调整参数"
        
        print(f"\n  {conclusion}")


if __name__ == '__main__':
    run_backtest()
