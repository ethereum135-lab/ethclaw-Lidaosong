#!/usr/bin/env python3
"""
自动修复脚本 — 所有复盘cron的第一步
功能：
  1. 检查SOCKS5隧道，断了就自动重连
  2. 检查signals.json新鲜度（<30min），过期触发扫描
  3. 验证TRADES.md可读且含昨日收盘
  4. 读余额验证系统通不通
输出：一行状态 JSON
"""
import json, os, subprocess, sys, time, re

BASE = "/Users/lidaosong/zq_web4_trading_system"
SOCKS5_PORT = 1080
SSH_HOST = "web4"

def run(cmd, timeout=15):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except Exception as e:
        return -1, "", str(e)

def fix_socks5():
    """检查SOCKS5隧道，断了就重连"""
    rc, out, _ = run("lsof -ti :%d 2>/dev/null" % SOCKS5_PORT)
    if rc == 0 and out:
        # 隧道进程在，验证能否ping Binance
        rc2, out2, _ = run("curl --socks5-hostname 127.0.0.1:%d -s --connect-timeout 5 'https://api.binance.com/api/v3/ping'" % SOCKS5_PORT)
        if rc2 == 0 and out2 == "{}":
            return True, "SOCKS5正常"
    
    # 隧道断了或失活 → 杀掉旧进程重连
    if out:
        run("kill -9 %s 2>/dev/null" % out.strip())
        time.sleep(1)
    
    # 试重连
    rc3, _, _ = run("ssh -D %d -N -f %s 2>/dev/null" % (SOCKS5_PORT, SSH_HOST), timeout=10)
    time.sleep(2)
    
    # 验证
    rc4, out4, _ = run("curl --socks5-hostname 127.0.0.1:%d -s --connect-timeout 5 'https://api.binance.com/api/v3/ping'" % SOCKS5_PORT)
    if rc4 == 0 and out4 == "{}":
        return True, "SOCKS5已重连成功"
    return False, "SOCKS5重连失败"

def check_signals():
    """检查signals.json新鲜度，过期触发扫描"""
    path = os.path.join(BASE, "data/signals.json")
    if not os.path.exists(path):
        # 触发一次扫描
        run("cd %s && bash ~/.hermes/scripts/a3_signal_scanner.sh 2>/dev/null" % BASE, timeout=60)
        return False, "signals.json不存在，已触发扫描"
    
    try:
        data = json.load(open(path))
        scanned = data.get("scanned_at", "")
        if not scanned:
            return False, "signals.json无scanned_at"
        
        # 解析时间
        now = time.time()
        try:
            t = time.mktime(time.strptime(scanned[:19], "%Y-%m-%d %H:%M:%S"))
            age_min = (now - t) / 60
        except:
            return False, "signals.json时间戳解析失败"
        
        if age_min > 30:
            # 过期了，触发刷新
            run("cd %s && bash ~/.hermes/scripts/a3_signal_scanner.sh 2>/dev/null" % BASE, timeout=60)
            return False, "signals.json过期%.0f分钟，已触发刷新" % age_min
        return True, "signals.json新鲜(%d分钟)" % int(age_min)
    except:
        return False, "signals.json读取失败"

def check_trades():
    """验证TRADES.md含昨日收盘和当前总权益"""
    path = os.path.join(BASE, "audit/TRADES.md")
    if not os.path.exists(path):
        return False, "TRADES.md不存在"
    
    text = open(path).read()
    has_equity = bool(re.search(r'总权益[=~]+\$?[\d.]+', text))
    has_close = bool(re.search(r'今日目标.*?总资\$?[\d.]+\s*[×x]\s*0?\.?2%', text))
    
    issues = []
    if not has_equity:
        issues.append("缺总权益")
    if not has_close:
        issues.append("缺昨日收盘")
    
    if issues:
        return False, "TRADES.md: " + ", ".join(issues)
    return True, "TRADES.md数据完整"

def main():
    results = {}
    
    # 1. SOCKS5隧道
    ok, msg = fix_socks5()
    results["socks5"] = {"ok": ok, "msg": msg}
    
    # 2. 信号新鲜度
    ok, msg = check_signals()
    results["signals"] = {"ok": ok, "msg": msg}
    
    # 3. TRADES.md完整性
    ok, msg = check_trades()
    results["trades"] = {"ok": ok, "msg": msg}
    
    # 4. 余额（快速验证系统通不通）
    rc, out, _ = run("cd %s && python3 tools/true_daily_pnl.py 2>/dev/null" % BASE)
    if rc == 0:
        results["balance"] = {"ok": True, "msg": out}
    else:
        rc2, out2, _ = run("cd %s && python3 tools/quick_balance.py 2>/dev/null" % BASE)
        if rc2 == 0:
            results["balance"] = {"ok": True, "msg": "quick_balance: " + out2.split('\n')[0]}
        else:
            results["balance"] = {"ok": False, "msg": "余额无法读取"}
    
    # 总状态
    all_ok = all(v["ok"] for v in results.values())
    
    output = json.dumps({
        "all_ok": all_ok,
        "checks": results
    }, ensure_ascii=False)
    print(output)
    
    # 简短人类可读版本（带--report时）
    if "--report" in sys.argv:
        print("---")
        if all_ok:
            print("✅ 全部正常")
        else:
            for k, v in results.items():
                emoji = "✅" if v["ok"] else "❌"
                print(f"{emoji} {k}: {v['msg']}")
    
    sys.exit(0 if all_ok else 1)

if __name__ == "__main__":
    main()
