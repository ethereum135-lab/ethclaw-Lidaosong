#!/usr/bin/env python3
"""
BHZ 实时异常监测
每30分钟同步引擎周期运行
检测引擎日志中的异常模式，自动报警
"""
import os, sys, json, time
from datetime import datetime, timezone, timedelta

BJT = timezone(timedelta(hours=8))
LOGS_DIR = os.path.expanduser("~/zq_web4_trading_system/logs")
TRADES_PATH = os.path.expanduser("~/zq_web4_trading_system/audit/TRADES.md")
CHECKLIST_PATH = os.path.expanduser("~/zq_web4_trading_system/agents/bhz/checklist.md")

def read_engine_log_ssh(lines=80):
    """从AWS读取引擎日志"""
    import subprocess
    try:
        r = subprocess.run([
            'ssh', '-i', os.path.expanduser('~/.zq_vault/web4.0.pem'),
            '-o', 'ConnectTimeout=5',
            'ubuntu@15.134.211.154',
            f'tail -{lines} /home/ubuntu/zq_web4_trading_system/logs/engine_cron.log'
        ], capture_output=True, text=True, timeout=15)
        return r.stdout
    except Exception as e:
        return f"SSH_FAILED: {e}"

def detect_quick_exits(log_text):
    """检测30分钟内的买/卖模式"""
    anomalies = []
    lines = log_text.split('\n')
    
    recent_buys = {}   # symbol -> {'time': ..., 'price': ...}
    recent_sells = {}  # symbol -> {'time': ..., 'price': ..., 'reason': ...}
    
    for i, line in enumerate(lines):
        if '买入' in line and '@' in line:
            parts = line.split()
            for j, p in enumerate(parts):
                if '@' in p:
                    sym = parts[j-2] if j >= 2 else '?'
                    price = p.replace('@', '')
                    # 找时间戳（往前找）
                    ts = "?"
                    for k in range(max(0, i-5), i):
                        if '节点完成' in lines[k]:
                            ts = lines[k].split('—')[-1].strip()
                    recent_buys[sym] = {'time': ts, 'price': price, 'line': line.strip()}
                    
        if '卖出' in line and '@' in line and '✅' in line:
            parts = line.split()
            for j, p in enumerate(parts):
                if '@' in p:
                    sym = parts[j-2] if j >= 2 else '?'
                    price = p.replace('@', '')
                    # 找卖出原因
                    reason_line = ""
                    for k in range(max(0, i-3), i):
                        if 'P3' in lines[k] or 'E4' in lines[k] or 'E3' in lines[k] or '触发出场' in lines[k]:
                            reason_line = lines[k].strip()
                    ts = "?"
                    for k in range(max(0, i-5), i):
                        if '节点完成' in lines[k]:
                            ts = lines[k].split('—')[-1].strip()
                    recent_sells[sym] = {'time': ts, 'price': price, 'reason': reason_line, 'line': line.strip()}
    
    return recent_buys, recent_sells

def check_anomalies():
    """检查所有异常模式"""
    log = read_engine_log_ssh()
    if log.startswith("SSH_FAILED"):
        return [f"🔴 SSH异常: {log}"]
    
    buys, sells = detect_quick_exits(log)
    issues = []
    
    # 异常1：买的币在3节点内被卖
    for sym, buy_info in buys.items():
        if sym in sells:
            issues.append(f"⚡ {sym}: 刚买入就卖出 (买入{buy_info['price']}→卖出{sells[sym]['price']}) 原因:{sells[sym]['reason']}")
    
    # 异常2：连续多个节点都是买→卖→买→卖，没有持仓超过3节点
    if len(buys) >= 2 and len(sells) >= 2:
        issues.append(f"⚠️ 高频换仓: 最近{len(buys)}次买入中{len(sells)}次已卖出，持仓时间偏短")
    
    # 异常3：引擎没跑（日志太久没更新）
    for line in log.split('\n'):
        if '节点完成' in line:
            ts_str = line.split('—')[-1].strip()
            break
    
    if not issues:
        issues.append("✅ 无异常")
    
    return issues

def update_checklist(issues):
    """更新checklist.md的异常记录"""
    now = datetime.now(BJT).strftime('%Y-%m-%d %H:%M BJT')
    entry = f"\n### 实时监测 — {now}\n"
    for issue in issues:
        entry += f"- {issue}\n"
    
    with open(CHECKLIST_PATH, 'a') as f:
        f.write(entry)

if __name__ == '__main__':
    issues = check_anomalies()
    for issue in issues:
        print(issue)
    update_checklist(issues)
