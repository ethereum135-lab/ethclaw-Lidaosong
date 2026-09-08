#!/usr/bin/env python3
"""
A4 轮动检查 — 判断哪些死仓该轮动，释放资金给更好的机会

每30分钟跑一次，输出到 a4_prep.py 的摘要中。
核心逻辑：所有持仓中，信号弱于40分 + 持有>2h + 非盈利的 → 轮动候选
"""
import json, os, re, sys
from pathlib import Path
from datetime import datetime
import subprocess

BASE = Path(os.environ.get('ZQ_ROOT', '/Users/lidaosong/zq_web4_trading_system'))

def read_json(rel_path):
    p = BASE / rel_path
    if not p.exists(): return None
    try: return json.loads(p.read_text())
    except: return None

def find_last_buys():
    """
    从TRADES.md提取最近的BUY记录（A4格式：|||timestamp|BUY|SYM|QTY|PRICE|REASON）
    只考虑2026-05-18（A4上线日）之后的数据。
    返回 dict: symbol -> {time, qty, price, reason}
    """
    p = BASE / 'audit' / 'TRADES.md'
    if not p.exists():
        return {}
    
    content = p.read_text()
    lines = content.strip().split('\n')
    
    # 从最后往前扫描，找到最近的BUY行
    # A4格式: |||2026-05-21 22:10:00|BUY|WLD|76.10000000|$0.26270000|
    buys = {}
    sells_latest = {}
    
    for line in reversed(lines):
        line = line.strip()
        # Only process "|||" format lines (A4 format)
        if not line.startswith('|||'):
            continue
        
        # Split on |
        parts = [p.strip() for p in line.split('|')]
        # parts[0] = '' (empty before first |)
        # parts[1] = '' (empty from ||)
        # parts[2] = '' (empty from |||)
        # Actually let me just handle startswith ||| properly
        # Format: |||timestamp|BUY|SYM|QTY|PRICE|REASON
        
        # Remove leading empty strings
        parts = [p for p in parts if p != '']
        
        if len(parts) < 5:
            continue
        
        ts = parts[0]
        action = parts[1]
        
        # Only care about A4-era (May 18+)
        if not ts.startswith('2026-05-1') and not ts.startswith('2026-05-2'):
            continue
        # Skip May 18 specifically? Actually include May 18+
        
        if action == 'SELL':
            sym = parts[2]
            # Update latest sell time
            if sym not in sells_latest or ts > sells_latest[sym]:
                sells_latest[sym] = ts
        
        elif action == 'BUY' and len(parts) >= 6:
            sym = parts[2]
            qty = parts[3]
            price = parts[4]
            reason = parts[5] if len(parts) > 5 else '?'
            
            # Only record if this is the most recent BUY for this symbol
            if sym not in buys or ts > buys[sym]['time']:
                buys[sym] = {
                    'time': ts,
                    'qty': qty,
                    'price': price,
                    'reason': reason
                }
    
    # Remove sold positions
    active = {}
    for sym, info in buys.items():
        # Skip if this coin was sold after this buy
        if sym in sells_latest and sells_latest[sym] > info['time']:
            continue
        active[sym] = info
    
    return active

def get_ssh_data():
    """通过SSH获取AWS实时余额"""
    try:
        r = subprocess.run([
            'ssh', '-i', os.path.expanduser('~/.zq_vault/web4.0.pem'),
            '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=8',
            'ubuntu@15.134.211.154',
            "cd /home/ubuntu/zq_web4_trading_system/production/engine && python3 aws_executor.py --check 2>/dev/null || echo 'FAIL'"
        ], capture_output=True, text=True, timeout=20)
        output = r.stdout.strip()
        if output and output != 'FAIL':
            try:
                assets = json.loads(output)
                usdt = 0.0
                positions = {}
                for a in assets:
                    free = float(a.get('free', 0))
                    locked = float(a.get('locked', 0))
                    if a.get('asset') == 'USDT':
                        usdt = free
                    elif free > 0:
                        positions[a['asset']] = {'free': free, 'locked': locked}
                return usdt, positions
            except: pass
    except: pass
    return None, {}

def get_signal_scores():
    """从signals.json获取每个币的当前分数"""
    data = read_json('data/signals.json')
    if not data: return {}
    
    scores = {}
    signals_list = data.get('results') or data.get('signals') or []
    for s in signals_list:
        sym = s.get('symbol', '').upper()
        score = s.get('total_score', 0)
        level = s.get('level', 'PASS')
        cat = s.get('category', '?')
        scores[sym] = {'score': score, 'level': level, 'category': cat}
    return scores

def main():
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    active = find_last_buys()
    signal_scores = get_signal_scores()
    ssh_usdt, ssh_positions = get_ssh_data()
    
    if not active:
        print(f"## 轮动检查 ({now})")
        print("⚠️ 未检测到活跃持仓")
        return
    
    rotation = []
    strong = []
    
    for sym, info in sorted(active.items()):
        sig = signal_scores.get(sym, {})
        score = sig.get('score', 0)
        level = sig.get('level', '?')
        cat = sig.get('category', '?')
        
        should_rotate = False
        reasons = []
        
        # Parse buy time for age check
        buy_time_str = info.get('time', '')
        buy_age_hours = 24  # default old
        try:
            buy_dt = datetime.strptime(buy_time_str[:16], '%Y-%m-%d %H:%M')
            buy_age_hours = (datetime.now() - buy_dt).total_seconds() / 3600
        except:
            pass
        
        if not sig:
            reasons.append(f"无信号")
            should_rotate = True
        elif score < 40:
            reasons.append(f"信号{score}<40 ({level})")
            should_rotate = True
        elif 40 <= score < 50 and level in ('WATCH', 'PASS'):
            reasons.append(f"信号{score}/{level}, 弱信号")
            should_rotate = True
        elif 40 <= score < 50 and level == 'SIGNAL' and buy_age_hours > 6:
            reasons.append(f"信号{score}/SIGNAL, 持{buy_age_hours:.0f}h无改善")
            should_rotate = True
        elif 50 <= score < 60 and buy_age_hours > 24:
            reasons.append(f"信号{score}/{level}, 持超24h")
            should_rotate = True
        
        # Always skip very recent positions (< 2h old)
        if should_rotate and buy_age_hours < 2:
            should_rotate = False
            reasons = []
        
        # Check if position is too small to matter
        buy_price_str = info.get('price', '0').replace('$', '')
        buy_qty_str = info.get('qty', '0')
        try:
            buy_price = float(buy_price_str) if buy_price_str else 0
            buy_qty = float(buy_qty_str) if buy_qty_str else 0
            pos_value = buy_price * buy_qty
        except:
            pos_value = 0
        
        if should_rotate:
            rotation.append({
                'symbol': sym,
                'score': score,
                'level': level,
                'reasons': '; '.join(reasons[:2]),
                'value_est': pos_value,
                'buy_time': info['time']
            })
        else:
            if score >= 60:
                strong.append(f"{sym}({score}pts/{level})")
    
    # Calculate freed capital
    if ssh_usdt is not None:
        freed = sum(c['value_est'] for c in rotation if c['value_est'] > 0)
        # Conservative: min between value_est and $20 per position
        freed_conservative = sum(max(15, min(c['value_est'], 40)) for c in rotation if c['value_est'] > 0)
        total_deployable = usdt_balance = ssh_usdt + freed_conservative
    else:
        usdt_balance = freed = freed_conservative = total_deployable = 0
    
    # Limit to top rotation candidates by value
    rotation.sort(key=lambda c: c['value_est'], reverse=True)
    
    lines = [
        f"## 轮动检查 ({now})",
        ""
    ]
    
    if rotation:
        # Show only positions that are worth rotating
        meaningful_rotation = [c for c in rotation if c['value_est'] > 10]
        if not meaningful_rotation:
            meaningful_rotation = rotation[:5]
        
        freed_show = sum(c['value_est'] for c in meaningful_rotation)
        lines.append(f"### 🟡 建议轮动 ({len(meaningful_rotation)}个, 可释放~${freed_show:.0f})")
        for c in meaningful_rotation[:8]:
            if c['value_est'] > 0:
                lines.append(f"- **{c['symbol']}** ~${c['value_est']:.0f} | 信号{c['score']}/{c['level']} | {c['reasons']}")
            else:
                lines.append(f"- **{c['symbol']}** | 信号{c['score']}/{c['level']} | {c['reasons']}")
    else:
        lines.append("### 🟢 无轮动候选 — 所有持仓信号健康")
    
    if strong:
        lines.append(f"\n### 强势持仓: {' '.join(strong[:6])}")
    
    if ssh_usdt is not None:
        lines.append(f"\n### 资金概况")
        lines.append(f"- USDT可用: ${ssh_usdt:.2f}")
        if freed_conservative > 0:
            lines.append(f"- 轮动释放: ~${freed_conservative:.0f}")
            lines.append(f"- 总可部署: ~${total_deployable:.0f}")
    
    # List all current positions for reference
    lines.append(f"\n### 当前持仓 ({len(active)}个)")
    for sym, info in sorted(active.items()):
        sig = signal_scores.get(sym, {})
        score = sig.get('score', '?')
        lines.append(f"- {sym} @{info['price']} | 信号{score} | {info['time'][:16]}")
    
    output = '\n'.join(lines)
    print(output)
    print(f"\n--- a4_shuffle_check.py done ---")

if __name__ == '__main__':
    main()
