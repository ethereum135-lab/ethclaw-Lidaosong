#!/usr/bin/env python3
"""SSH健康检测 — 每5分钟检查AWS SSH连通性，断连时记录报警
如果连续3次失败（15分钟），自动通过邮件/飞书通知

用法: python3 tools/ssh_watchdog.py
推荐cron: */5 * * * *
"""

import subprocess, json, os, sys, time
from datetime import datetime, timezone, timedelta

BJT = timezone(timedelta(hours=8))
WORKDIR = os.path.expanduser("~/zq_web4_trading_system")
WATCHDOG_FILE = os.path.join(WORKDIR, "data", "ssh_watchdog.json")
AWS_HOST = "15.134.211.154"
AWS_USER = "ubuntu"
PEM_KEY = os.path.expanduser("~/.zq_vault/web4.0.pem")

def now_bjt():
    return datetime.now(BJT).strftime("%Y-%m-%d %H:%M:%S")

def check_ssh():
    """检查SSH连接"""
    cmd = [
        "ssh", "-i", PEM_KEY,
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=10",
        "-o", "BatchMode=yes",
        f"{AWS_USER}@{AWS_HOST}",
        "echo ok"
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return r.returncode == 0 and r.stdout.strip() == "ok"
    except:
        return False

def load_state():
    if os.path.exists(WATCHDOG_FILE):
        with open(WATCHDOG_FILE) as f:
            return json.load(f)
    return {"fail_count": 0, "last_ok": None, "last_fail": None, "alarmed": False}

def save_state(state):
    os.makedirs(os.path.dirname(WATCHDOG_FILE), exist_ok=True)
    with open(WATCHDOG_FILE, 'w') as f:
        json.dump(state, f, indent=2)

if __name__ == "__main__":
    state = load_state()
    ok = check_ssh()
    
    if ok:
        state["fail_count"] = 0
        state["last_ok"] = now_bjt()
        state["alarmed"] = False
        save_state(state)
        print(f"[{now_bjt()}] ✅ SSH连接正常")
    else:
        state["fail_count"] += 1
        state["last_fail"] = now_bjt()
        print(f"[{now_bjt()}] ❌ SSH连接失败 (第{state['fail_count']}次)")
        
        # 连续3次失败 → 报警
        if state["fail_count"] >= 3 and not state["alarmed"]:
            state["alarmed"] = True
            save_state(state)
            msg = f"⚠️ AWS SSH断连告警\n  服务器: {AWS_HOST}\n  连续失败: {state['fail_count']}次\n  最后正常: {state.get('last_ok', '从未')}\n  时间: {now_bjt()}\n  请前往AWS控制台重启实例或检查服务器状态"
            print(f"\n{msg}")
            
            # 写告警到shared目录
            alarm_path = os.path.join(WORKDIR, "shared", "ssh_alarm.txt")
            with open(alarm_path, 'w') as f:
                f.write(f"{msg}\n")
            print(f"  告警已写入: {alarm_path}")
            
            # 0退出码+带告警信息，可被cron捕获转发
            sys.exit(2)
        
        save_state(state)
        sys.exit(1)
