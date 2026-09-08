#!/usr/bin/env python3
"""A4节点快照 — 快速记录总资产到node_history.jsonl"""
import json, os, subprocess, sys
from datetime import datetime, timezone, timedelta

BJT = timezone(timedelta(hours=8))
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY = os.path.join(BASE, "data", "node_history.jsonl")

def now_str():
    return datetime.now(BJT).strftime("%Y-%m-%d %H:%M:%S")

def main():
    # 通过一次SSH调用获取所有资产（awx_executor.py --check 返回完整JSON）
    r = subprocess.run(
        ["ssh", "-o", "ConnectTimeout=10", "web4",
         "python3 /home/ubuntu/zq_web4_trading_system/production/engine/aws_executor.py --check 2>/dev/null"],
        capture_output=True, text=True, timeout=25
    )
    out = r.stdout.strip()
    if not out:
        print("❌ SSH失败")
        sys.exit(1)
    
    try:
        data = json.loads(out)
    except:
        print("❌ JSON解析失败")
        sys.exit(1)
    
    usdt = 0.0
    holdings = []
    
    for item in data:
        asset = item.get('asset','')
        free = float(item.get('free', 0))
        locked = float(item.get('locked', 0))
        total = free + locked
        
        if total <= 0:
            continue
        if asset == 'USDT':
            usdt = total
        elif asset in ('LTC','ETH','BNB','TRX','XRP','ADA','DOGE','SOL'):
            continue  # 不计数尘仓资产价值（太多散仓）
        elif total * 0.01 > 1:  # 价值>$1的才记录
            holdings.append({"s": asset, "q": round(total, 4)})
    
    # 总资产估算（不做逐币查价，用A4报告的值）
    total_value = usdt + sum(h.get('q',0) for h in holdings)
    
    record = {
        "t": now_str(),
        "usdt": round(usdt, 2),
        "holdings": [h for h in holdings if h['q'] > 0][:10]
    }
    
    os.makedirs(os.path.dirname(HISTORY), exist_ok=True)
    with open(HISTORY, 'a') as f:
        f.write(json.dumps(record) + '\n')
    
    print(f"✅ node_history: USDT=${usdt:.2f} 持仓{len(holdings)}个")

if __name__ == '__main__':
    main()
