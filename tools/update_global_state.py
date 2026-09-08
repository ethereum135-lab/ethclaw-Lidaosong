#!/usr/bin/env python3
"""
更新全局共享状态 — 把最新余额+亏损+目标写入 shared/global_state.md

每次执行后，所有Agent在下一次运行时自动读到最新状态。
"""

import subprocess, json, os, time, hashlib, hmac

PROJECT_ROOT = "/Users/lidaosong/zq_web4_trading_system"
AWS_KEY = os.path.expanduser("~/.zq_vault/web4.0.pem")
AWS_HOST = "ubuntu@15.134.211.154"
AUTH_PATH = "/home/ubuntu/zq_web4_trading_system/config/auth.json"
INITIAL = 430.0
DAILY_TARGET_PCT = 2.1465
SHARED_PATH = os.path.join(PROJECT_ROOT, "shared/global_state.md")

def fetch_balance():
    """从AWS→Binance API获取实时余额"""
    AUTH_ESC = AUTH_PATH.replace("\\", "\\\\").replace("'", "'\\''")
    script = (
        "AUTH_PATH='" + AUTH_ESC + "'\n"
        + "import hashlib, hmac, time, json, urllib.request\n"
        + "auth=json.loads(open(AUTH_PATH).read())['binance']\n"
        + "key=auth['api_key'];secret=auth['api_secret']\n"
        + "ts=str(int(time.time()*1000))\n"
        + "q='timestamp='+ts+'&recvWindow=20000'\n"
        + "s=hmac.new(secret.encode(),q.encode(),hashlib.sha256).hexdigest()\n"
        + "req=urllib.request.Request('https://api.binance.com/api/v3/account?'+q+'&signature='+s)\n"
        + "req.add_header('X-MBX-APIKEY',key)\n"
        + "data=json.loads(urllib.request.urlopen(req,timeout=10).read())\n"
        + "prices=json.loads(urllib.request.urlopen('https://api.binance.com/api/v3/ticker/price',timeout=10).read())\n"
        + "pm={p['symbol']:float(p['price']) for p in prices}\n"
        + "total=0.0\n"
        + "holdings=[]\n"
        + "for b in data['balances']:\n"
        + "    t=float(b['free'])+float(b['locked'])\n"
        + "    if t>0.00001:\n"
        + "        if b['asset']=='USDT':\n"
        + "            total+=t\n"
        + "        else:\n"
        + "            s=b['asset']+'USDT'\n"
        + "            if s in pm:\n"
        + "                val=t*pm[s]\n"
        + "                if val>1.0:\n"
        + "                    holdings.append(b['asset']+':$'+'%.2f'%val)\n"
        + "                total+=val\n"
        + "print('BALANCE:%.2f'%total)\n"
        + "print('HOLDINGS:'+'|'.join(holdings[:6]))\n"
    )
    
    cmd = [
        "ssh", "-i", AWS_KEY,
        "-o", "ConnectTimeout=5", "-o", "StrictHostKeyChecking=no",
        AWS_HOST,
        "cat > /tmp/_update_state.py && python3 /tmp/_update_state.py"
    ]
    try:
        proc = subprocess.run(cmd, input=script.encode(), capture_output=True, timeout=15)
        if proc.returncode == 0:
            lines = proc.stdout.decode().strip().split("\n")
            for l in lines:
                if l.startswith("BALANCE:"):
                    return float(l[8:]), lines
        return None, None
    except:
        return None, None

def update():
    balance, raw_lines = fetch_balance()
    if balance is None:
        print("❌ 余额查询失败")
        return
    
    now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    loss = INITIAL - balance
    loss_pct = (loss / INITIAL) * 100
    day_target = INITIAL * (1 + DAILY_TARGET_PCT / 100)
    gap = balance - day_target
    
    # 解析持仓
    holdings_str = ""
    if raw_lines:
        for l in raw_lines:
            if l.startswith("HOLDINGS:"):
                items = l[9:].split("|")
                for item in items[:6]:
                    if item:
                        holdings_str += f"  - {item}\n"
    
    # 风险等级
    if loss_pct > 25:
        risk_level = "🔴 严重亏损"
    elif loss_pct > 15:
        risk_level = "🟡 中度亏损"
    else:
        risk_level = "🟢 轻度亏损"
    
    target_status = "✅ 达标" if balance >= day_target else "❌ 未达标"
    gap_text = "$%+.2f" % gap
    
    content = f"""# 🔴 全局共享状态 — 死命令：每日盈利必须达标
更新时间: {now} CST

## 🔴 死命令：每日盈利目标
- 目标: $430 → $1,000,000（1年）
- 每日需增长: **+2.1465%**
- 今日目标金额: ${day_target:.2f}
- 当前余额: ${balance:.2f}
- 距目标: {gap_text}
- 状态: {target_status}
- 累计亏损: ${loss:.2f} ({loss_pct:.1f}%)

## 最新余额
- 余额: ${balance:.2f}
- 累计亏损: ${loss:.2f} ({loss_pct:.1f}%)
- 风险等级: {risk_level}
- 数据源: Binance API

## 当前主要持仓
{holdings_str}
## 各Agent行动指令（基于目标）
- A2选币官: 当前{'亏损严重' if loss_pct > 20 else '亏损中'}，选币必须保守+高确定性
- A3牛币官: 风控权重加高，新推荐必须确保上涨空间
- A4交易官: 首要止损保护本金，其次新开仓
- A5复盘官: 重点找出这段亏损的卖出信号模式
- A6审计官: 检查亏损根因是否已修复，反馈是否闭环

数据源: Binance API
"""
    
    os.makedirs(os.path.dirname(SHARED_PATH), exist_ok=True)
    with open(SHARED_PATH, "w") as f:
        f.write(content)
    
    print(f"✅ 全局状态已更新: ${balance:.2f} | 亏损{loss_pct:.1f}% | {target_status}")
    print(f"   → {SHARED_PATH}")

if __name__ == "__main__":
    update()
