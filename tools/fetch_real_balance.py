#!/usr/bin/env python3
"""
实事求是采集工具 — 从Binance API物理直查实时余额。

使用方式：
  python3 tools/fetch_real_balance.py

输出：实时余额 + USDT估值（Binance API原始数据）
用途：每次汇报系统数据前，先跑这个。不允许用记忆替代实时数据。

铁律：必须物理验证，不随口不出随机。
"""

import subprocess
import sys
import os

# === 配置 ===
AWS_HOST = "ubuntu@15.134.211.154"
AWS_KEY = os.path.expanduser("~/.zq_vault/web4.0.pem")
AUTH_PATH = "/home/ubuntu/zq_web4_trading_system/config/auth.json"

REMOTE_SCRIPT = '''
import hashlib, hmac, time, json, urllib.request

AUTH_PATH = "{auth_path}"
auth = json.loads(open(AUTH_PATH).read())["binance"]
key = auth["api_key"]
secret = auth["api_secret"]

ts = str(int(time.time() * 1000))
query = "timestamp=" + ts + "&recvWindow=20000"
sig = hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()

req = urllib.request.Request(
    "https://api.binance.com/api/v3/account?" + query + "&signature=" + sig
)
req.add_header("X-MBX-APIKEY", key)
data = json.loads(urllib.request.urlopen(req, timeout=10).read())

try:
    syms = [b["asset"] + "USDT" for b in data["balances"]
            if b["asset"] != "USDT" and (float(b["free"]) + float(b["locked"])) > 0.00001]
    import urllib.parse
    q = urllib.parse.urlencode({{"symbols": json.dumps(syms)}})
    prices = json.loads(
        urllib.request.urlopen("https://api.binance.com/api/v3/ticker/price?" + q, timeout=10).read()
    )
except Exception:
    # 含无效symbol(如LDSHIB2)时定向请求整体报错 → 回退全量拉取
    prices = json.loads(
        urllib.request.urlopen("https://api.binance.com/api/v3/ticker/price", timeout=20).read()
    )
price_map = {{p["symbol"]: float(p["price"]) for p in prices}}

now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

print("=== 实时余额 (Binance API 物理直查) ===")
print("数据源: Binance /api/v3/account + /api/v3/ticker/price")
print("查询路径: Mac -> SSH AWS -> Binance API")
print("查询时间: %s CST" % now)
print("")

# 按估值排序
items = []
usdt_bal = 0.0
refined = []

for b in data["balances"]:
    total = float(b["free"]) + float(b["locked"])
    if total > 0.00001:
        if b["asset"] == "USDT":
            usdt_bal = total
        else:
            sym = b["asset"] + "USDT"
            if sym in price_map:
                val = total * price_map[sym]
                refined.append((val, b["asset"], total, price_map[sym]))

refined.sort(reverse=True)
total_usdt = usdt_bal + sum(it[0] for it in refined)

print("USDT现金: $%.2f" % usdt_bal)
print("")

main_items = [it for it in refined if it[0] > 1.0]
dust_count = len(refined) - len(main_items)

if main_items:
    print("主要持仓（>$1）：")
    for val, asset, qty, price in main_items:
        print("  %-8s %10.4f x $%-8.4f = $%7.2f" % (asset, qty, price, val))
    print("")

print("小余额（<$1）: %d种" % dust_count)
print("")
print("** 总权益: $%.2f **" % total_usdt)
'''.format(auth_path=AUTH_PATH)


def run():
    ssh_cmd = [
        "ssh", "-i", AWS_KEY,
        "-o", "ConnectTimeout=5",
        "-o", "StrictHostKeyChecking=no",
        AWS_HOST,
        "cat > /tmp/_fetch_balance.py && python3 /tmp/_fetch_balance.py"
    ]

    try:
        proc = subprocess.run(
            ssh_cmd,
            input=REMOTE_SCRIPT.encode(),
            capture_output=True,
            timeout=15
        )

        if proc.returncode != 0:
            print("ERROR: SSH或脚本执行失败", file=sys.stderr)
            err = proc.stderr.decode()[:500]
            if err:
                print(err, file=sys.stderr)
            return False

        output = proc.stdout.decode()
        print(output)
        return True

    except subprocess.TimeoutExpired:
        print("ERROR: 查询超时（>15s）。AWS可能不通。", file=sys.stderr)
        return False
    except Exception as e:
        print("ERROR: %s" % str(e), file=sys.stderr)
        return False


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
