#!/usr/bin/env python3
"""快速余额读取 — 带fallback链，所有复盘cron统一调用"""
import json, os, re

PROJECT = "/Users/lidaosong/zq_web4_trading_system"

def get_balance():
    """返回 {equity, source, source_date} 或 None"""
    
    # 源1: total_asset.json (最可靠)
    try:
        ta = json.load(open(os.path.join(PROJECT, 'data/total_asset.json')))
        equity = float(ta.get('total', 0))
        src_date = ta.get('date', '?')
        return {'equity': equity, 'source': 'total_asset.json', 'source_date': src_date}
    except:
        pass
    
    # 源2: shared/global_state.md (可能过期)
    try:
        with open(os.path.join(PROJECT, 'shared/global_state.md')) as f:
            c = f.read()
        ms = re.findall(r'当前余额.*?[\$](\d[\d.,]*)', c, re.M)
        if ms:
            equity = float(ms[0].replace(',',''))
            return {'equity': equity, 'source': 'shared/global_state.md', 'source_date': 'parse'}
    except:
        pass
    
    # 源3: TRADES.md 最后节点 — 估算
    try:
        with open(os.path.join(PROJECT, 'audit/TRADES.md')) as f:
            lines = f.readlines()
        total_val = 0
        for line in reversed(lines[-100:]):
            m = re.search(r'CYCLE_\d+|NODE_CHECK', line)
            if m:
                # 找格式如 SEPOLIA $244.83
                vm = re.search(r'[\$](\d+\.?\d*)', line)
                if vm:
                    total_val = float(vm.group(1))
                    break
        if total_val > 0:
            return {'equity': total_val, 'source': 'TRADES.md', 'source_date': 'latest node'}
    except:
        pass
    
    return None

if __name__ == '__main__':
    result = get_balance()
    if result:
        print(f"EQUITY:{result['equity']:.2f}")
        print(f"SOURCE:{result['source']}")
        print(f"SOURCE_DATE:{result.get('source_date','?')}")
    else:
        print("EQUITY:0")
        print("SOURCE:none")
