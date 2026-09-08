#!/usr/bin/env python3
"""从 TRADES.md 回填 behavior 数据到 coin_pool.json

解析 TRADES.md 中的所有 SELL 交易，找到对应的 BUY 价格，
然后调用 coin_pool_manager.py --record-trade 写入 behavior。
"""
import subprocess, sys, os, re
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRADES_PATH = os.path.join(BASE_DIR, 'audit', 'TRADES.md')
MANAGER = os.path.join(BASE_DIR, 'tools', 'coin_pool_manager.py')

def parse_trades():
    """解析 TRADES.md 返回 [(symbol, entry_price, exit_price, hold_min, reason), ...]"""
    
    # Step 1: 读取所有行
    with open(TRADES_PATH) as f:
        lines = f.readlines()
    
    # Step 2: 提取所有 BUY 和 SELL 记录
    # 格式: | 时间 | 操作 | 币种 | 数量 | 价格 | 原因 | 决策数据 |
    # 示例: | 2026-04-29 17:32:27 | SELL | KAT | 37487.0000 | 0.01090699 | 末位淘汰: ... |
    
    buys = {}   # symbol -> (price, timestamp)
    sell_pairs = []  # [(symbol, entry_price, exit_price, hold_min, reason)]
    
    buy_orders = []  # (timestamp, symbol, price)
    
    for line in lines:
        line = line.strip()
        if not line.startswith('|'):
            continue
        
        parts = [p.strip() for p in line.split('|')]
        # parts[0]='', parts[1]=timestamp, parts[2]=操作, parts[3]=币种, parts[4]=数量, parts[5]=价格, parts[6]=原因
        
        if len(parts) < 7:
            continue
        
        timestamp = parts[1]
        action = parts[2].upper()
        symbol = parts[3]
        raw_price = parts[5].replace('$', '').strip()
        
        if symbol in ('-', '', '—'):
            continue
        
        # 只处理有有效价格的 BUY/SELL
        try:
            price = float(raw_price)
        except (ValueError, TypeError):
            continue
        
        if action == 'BUY':
            buy_orders.append((timestamp, symbol, price))
        
        elif action == 'SELL':
            # 找到该币种最近的 BUY
            entry_price = None
            entry_time = None
            for bt, bs, bp in reversed(buy_orders):
                if bs == symbol:
                    entry_price = bp
                    entry_time = bt
                    break
            
            # 计算持仓时间（分钟）
            hold_min = 0
            if entry_time:
                try:
                    fmt = '%Y-%m-%d %H:%M:%S'
                    entry_dt = datetime.strptime(entry_time, fmt)
                    exit_dt = datetime.strptime(timestamp, fmt)
                    hold_min = int((exit_dt - entry_dt).total_seconds() / 60)
                except:
                    hold_min = 0
            
            reason = parts[6] if len(parts) > 6 else ''
            # 简化退出原因
            reason_short = reason.split(':')[0].split(';')[0].strip()[:50]
            
            if entry_price and entry_price > 0:
                sell_pairs.append((symbol, entry_price, price, hold_min, reason_short))
    
    return sell_pairs


def main():
    trades = parse_trades()
    print(f"从 TRADES.md 解析出 {len(trades)} 笔 SELL 交易")
    
    success = 0
    failed = 0
    for symbol, entry, exit_, hold_min, reason in trades:
        cmd = [
            sys.executable, MANAGER,
            '--record-trade', symbol, str(entry), str(exit_), str(hold_min), reason
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=BASE_DIR)
        if result.returncode == 0:
            success += 1
        else:
            failed += 1
            if failed <= 5:
                print(f"  ❌ {symbol}: {result.stderr.strip()}")
    
    print(f"\n=== 回填完成 ===")
    print(f"成功: {success} | 失败: {failed}")
    
    # 显示汇总
    subprocess.run([
        sys.executable, '-c', '''
import json
pool = json.load(open("data/coin_pool.json"))
b = pool.get("behavior", {})
print(f"\\n📊 behaviour 汇总:")
print(f"  覆盖币种: {len(b)} 个")
total_trades = sum(d["total_trades"] for d in b.values())
print(f"  总交易数: {total_trades} 笔")
wins = sum(d["wins"] for d in b.values())
losses = sum(d["losses"] for d in b.values())
print(f"  胜: {wins} | 负: {losses} | 胜率: {wins/max(total_trades,1)*100:.1f}%")
avg_pnls = [d["avg_pnl"] for d in b.values() if d["avg_pnl"] > -100]
print(f"  平均盈亏(过滤异常): {sum(avg_pnls)/len(avg_pnls):+.2f}%")
print(f"\\nTop 10 币种按交易数:")
ranked = sorted(b.items(), key=lambda x: -x[1]["total_trades"])[:10]
for sym, data in ranked:
    print(f"  {sym:8s}: {data['total_trades']:3d}笔 | 胜率{data['win_rate']:5.1f}% | 平均PnL{data['avg_pnl']:+.2f}% | {data['avg_hold_min']:.0f}min")
'''
    ], cwd=BASE_DIR)


if __name__ == '__main__':
    main()
