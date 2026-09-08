#!/usr/bin/env python3
"""
余额触发诊断 — 每次余额变化时自动分析亏在哪、怎么修。

触发方式：可被cron调用，可被手动运行
输出：亏在哪 → 根因 → 修复建议

用法：
  python3 tools/trigger_diagnosis.py
  
输出到飞书的摘要：亏多少、根因、修复方向
"""

import subprocess
import json
import os
import time
import sys

# === 配置 ===
PROJECT_ROOT = "/Users/lidaosong/zq_web4_trading_system"
AWS_KEY = os.path.expanduser("~/.zq_vault/web4.0.pem")
AWS_HOST = "ubuntu@15.134.211.154"
AUTH_PATH = "/home/ubuntu/zq_web4_trading_system/config/auth.json"
INITIAL_CAPITAL = 430.0  # 初始本金

def run_ssh(script):
    """通过SSH在AWS上执行脚本并返回输出"""
    cmd = [
        "ssh", "-i", AWS_KEY,
        "-o", "ConnectTimeout=5",
        "-o", "StrictHostKeyChecking=no",
        AWS_HOST,
        "cat > /tmp/_diag.py && python3 /tmp/_diag.py"
    ]
    try:
        proc = subprocess.run(cmd, input=script.encode(), capture_output=True, timeout=15)
        return proc.stdout.decode() if proc.returncode == 0 else None
    except Exception:
        return None

def fetch_balance():
    """获取实时余额"""
    script = r'''
import hashlib, hmac, time, json, urllib.request
AUTH_PATH = "''' + AUTH_PATH + r'''"
auth = json.loads(open(AUTH_PATH).read())["binance"]
key = auth["api_key"]; secret = auth["api_secret"]
ts = str(int(time.time() * 1000))
q = "timestamp=" + ts + "&recvWindow=20000"
s = hmac.new(secret.encode(), q.encode(), hashlib.sha256).hexdigest()
req = urllib.request.Request("https://api.binance.com/api/v3/account?" + q + "&signature=" + s)
req.add_header("X-MBX-APIKEY", key)
data = json.loads(urllib.request.urlopen(req, timeout=10).read())
prices = json.loads(urllib.request.urlopen("https://api.binance.com/api/v3/ticker/price", timeout=10).read())
pm = {p["symbol"]: float(p["price"]) for p in prices}
total = 0.0
for b in data["balances"]:
    t = float(b["free"]) + float(b["locked"])
    if t > 0.00001:
        if b["asset"] == "USDT":
            total += t
        else:
            s = b["asset"] + "USDT"
            if s in pm:
                total += t * pm[s]
print("%.2f" % total)
'''
    
    out = run_ssh(script)
    if out:
        try:
            return float(out.strip())
        except:
            pass
    return None

def get_daily_trades():
    """获取今日交易记录"""
    trades_path = os.path.join(PROJECT_ROOT, "audit", "TRADES.md")
    if not os.path.exists(trades_path):
        return None
    
    today = time.strftime("%Y-%m-%d")
    with open(trades_path) as f:
        content = f.read()
    
    # 提取今日交易行
    lines = content.split("\n")
    today_lines = []
    for i, line in enumerate(lines):
        if today in line and "|" in line:
            # 找整行
            start = max(0, i-1)
            end = min(len(lines), i+3)
            today_lines.extend(lines[start:end])
    
    return "\n".join(today_lines[-50:]) if today_lines else None

def get_last_trades():
    """获取最后20笔交易"""
    trades_path = os.path.join(PROJECT_ROOT, "audit", "TRADES.md")
    if not os.path.exists(trades_path):
        return None
    with open(trades_path) as f:
        lines = f.readlines()
    return "".join(lines[-30:])

def get_agent_outputs():
    """获取各Agent最新产出"""
    outputs = {}
    paths = {
        "A1_data_feed": os.path.join(PROJECT_ROOT, "profiles/a1-data/output/data_feed.md"),
        "A3_findings": os.path.join(PROJECT_ROOT, "profiles/a3-bull/output"),
        "A5_feedback": os.path.join(PROJECT_ROOT, "profiles/a5-review/output"),
    }
    for name, path in paths.items():
        if os.path.isdir(path):
            files = sorted(os.listdir(path))
            if files:
                latest = os.path.join(path, files[-1])
                with open(latest) as f:
                    outputs[name] = f.read()[:500]
        elif os.path.isfile(path):
            with open(path) as f:
                outputs[name] = f.read()[:500]
    return outputs


def main():
    print("=" * 50)
    print("【余额触发诊断】%s" % time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
    print("=" * 50)
    print()
    
    # 1. 查实时余额
    print("▶ 查实时余额...")
    balance = fetch_balance()
    if balance is None:
        print("❌ 余额查询失败")
        return
    
    print("  当前余额: $%.2f" % balance)
    loss = INITIAL_CAPITAL - balance
    loss_pct = (loss / INITIAL_CAPITAL) * 100
    print("  初始本金: $%.0f" % INITIAL_CAPITAL)
    print("  已亏损: $%.2f (%.1f%%)" % (loss, loss_pct))
    print()
    
    # 2. 查今日交易
    print("▶ 查今日交易...")
    trades = get_daily_trades()
    if trades:
        print("  今日交易（摘录）:")
        for line in trades.split("\n"):
            if "|" in line and "---" not in line:
                print("    %s" % line.strip())
    else:
        print("  (今日无TRADES.md记录)")
    print()
    
    # 3. 查Agent产出状态
    print("▶ 查各Agent最新产出...")
    outputs = get_agent_outputs()
    for name, content in outputs.items():
        print("  %s: %d字 (%s...)" % (name, len(content), content[:80].replace("\n", " ")))
    print()
    
    # 4. 诊断摘要（给老李看的）
    print("=" * 50)
    print("【诊断摘要】")
    print("=" * 50)
    print()
    print("当前余额: $%.2f" % balance)
    print("累计亏损: $%.2f (%.1f%%)" % (loss, loss_pct))
    print()
    
    # 根据亏损幅度给出建议
    if loss_pct > 20:
        print("🔴 严重亏损 — 超过20%%")
        print("  建议优先方向：")
        print("  ① 检查近3天每笔卖出是否都在亏")
        print("  ② 如果是：暂停交易，先查策略问题")
        print("  ③ 如果某只币亏最多：拉黑该币")
    elif loss_pct > 10:
        print("🟡 中度亏损 — 10-20%%")
        print("  建议方向：")
        print("  ① 查今日交易中哪类退出信号亏最多")
        print("  ② 如果是入场问题：调A2/A3的评分规则")
        print("  ③ 如果是出场问题：调退出参数")
    else:
        print("🟢 轻度亏损 — 10%%以内")
        print("  建议：正常复盘即可")
    
    print()
    print("数据源: Binance API %s CST" % time.strftime("%Y-%m-%d %H:%M:%S"))
    print("数据路径: Mac -> SSH AWS -> Binance /api/v3/account")
    
    # 写入结果文件供其他Agent读取
    out_path = os.path.join(PROJECT_ROOT, "analysis/latest_diagnosis.md")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        f.write("# 余额触发诊断\n")
        f.write("时间: %s CST\n" % time.strftime("%Y-%m-%d %H:%M:%S"))
        f.write("余额: $%.2f\n" % balance)
        f.write("亏损: $%.2f (%.1f%%)\n" % (loss, loss_pct))
        f.write("---\n")

if __name__ == "__main__":
    main()
