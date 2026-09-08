#!/usr/bin/env python3
"""
全局状态聚合器 — 每5分钟跑一次，no_agent模式，零费用

功能：
  ① 读所有Agent状态 → 合并成 global_state.json
  ② 管道健康检查（A1→A2→A3→A4→A5是否通畅）
  ③ 数据维度利用率检测（A1有6维，A2用了几维？）
  ④ 盈利目标诊断点（14:00/20:00检查进度）
  ⑤ 缺口标记（哪个Agent的数据下游没消费）

输出：shared/global_state.json（原子写入，所有人只读）
"""
import json, os, sys, time, subprocess, hashlib, hmac, re

# ========== 配置 ==========
PROJECT_ROOT = "/Users/lidaosong/zq_web4_trading_system"
STATE_DIR = os.path.join(PROJECT_ROOT, "state")
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "shared", "global_state.json")

INITIAL_CAPITAL = 430.0
DAILY_TARGET_PCT = 0.2   # 日目标: 总资×0.2%（0.1~0.3%区间中值，2026-06-21全网数据定案；2%/天=年化730%数学不可行）

AWS_KEY = os.path.expanduser("~/.zq_vault/web4.0.pem")
AWS_HOST = "ubuntu@15.134.211.154"
AUTH_PATH = "/home/ubuntu/zq_web4_trading_system/config/auth.json"

# ========== 工具函数 ==========

def read_state(agent: str) -> dict:
    """读取单个Agent状态"""
    path = os.path.join(STATE_DIR, f"{agent}.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"agent": agent, "timestamp": None, "status": "no_data", "data": None, "errors": "无数据"}

def fetch_balance():
    """从AWS→Binance获取实时余额（同原脚本逻辑）"""
    script = (
        "import hashlib, hmac, time, json, urllib.request\n"
        "auth=json.loads(open('/home/ubuntu/zq_web4_trading_system/config/auth.json').read())['binance']\n"
        "key=auth['api_key'];secret=auth['api_secret']\n"
        "ts=str(int(time.time()*1000))\n"
        "q='timestamp='+ts+'&recvWindow=20000'\n"
        "s=hmac.new(secret.encode(),q.encode(),hashlib.sha256).hexdigest()\n"
        "req=urllib.request.Request('https://api.binance.com/api/v3/account?'+q+'&signature='+s)\n"
        "req.add_header('X-MBX-APIKEY',key)\n"
        "data=json.loads(urllib.request.urlopen(req,timeout=10).read())\n"
        "prices=json.loads(urllib.request.urlopen('https://api.binance.com/api/v3/ticker/price',timeout=10).read())\n"
        "pm={p['symbol']:float(p['price']) for p in prices}\n"
        "total=0.0\n"
        "holdings=[]\n"
        "for b in data['balances']:\n"
        "    t=float(b['free'])+float(b['locked'])\n"
        "    if t>0.00001:\n"
        "        if b['asset']=='USDT': total+=t\n"
        "        else:\n"
        "            s=b['asset']+'USDT'\n"
        "            if s in pm:\n"
        "                val=t*pm[s]\n"
        "                if val>1.0: holdings.append(f\"{b['asset']}:${val:.2f}\")\n"
        "                total+=val\n"
        "print(f'BALANCE:{total:.2f}')\n"
        "if holdings: print('HOLDINGS:'+'|'.join(holdings))\n"
    )
    cmd = ["ssh", "-i", AWS_KEY, "-o", "ConnectTimeout=5", "-o", "StrictHostKeyChecking=no",
           AWS_HOST, "cat > /tmp/_agg_state.py && python3 /tmp/_agg_state.py"]
    try:
        proc = subprocess.run(cmd, input=script.encode(), capture_output=True, timeout=15)
        if proc.returncode == 0:
            lines = proc.stdout.decode().strip().split("\n")
            bal, holdings = None, []
            for l in lines:
                if l.startswith("BALANCE:"): bal = float(l[8:])
                elif l.startswith("HOLDINGS:"): holdings = l[9:].split("|") if l[9:] else []
            return bal, holdings
    except: pass
    # 2026-08-19 ZH: SSH断连时本地Binance API直连(SOCKS5)回退 —— 避免余额永久None
    # 注意: urllib不支持socks5协议，必须用curl --socks5-hostname（已验证2026-08-19）
    try:
        import hmac as _hmac, hashlib as _hl
        auth = json.load(open(os.path.join(PROJECT_ROOT, "config", "auth.json")))["binance"]
        ts = str(int(time.time() * 1000))
        q = "timestamp=" + ts + "&recvWindow=20000"
        s = _hmac.new(auth["api_secret"].encode(), q.encode(), _hl.sha256).hexdigest()
        acc_url = "https://api.binance.com/api/v3/account?" + q + "&signature=" + s
        ra = subprocess.run(
            ["curl", "--socks5-hostname", "127.0.0.1:1080", "-s", "--max-time", "20",
             "-H", f"X-MBX-APIKEY: {auth['api_key']}", acc_url],
            capture_output=True, text=True)
        data = json.loads(ra.stdout)
        rp = subprocess.run(
            ["curl", "--socks5-hostname", "127.0.0.1:1080", "-s", "--max-time", "20",
             "https://api.binance.com/api/v3/ticker/price"],
            capture_output=True, text=True)
        pr = json.loads(rp.stdout)
        pm = {p["symbol"]: float(p["price"]) for p in pr}
        total, holdings = 0.0, []
        for b in data["balances"]:
            t = float(b["free"]) + float(b["locked"])
            if t > 0.00001:
                if b["asset"] == "USDT":
                    total += t
                else:
                    sy = b["asset"] + "USDT"
                    if sy in pm:
                        val = t * pm[sy]
                        if val > 1.0:
                            holdings.append(f"{b['asset']}:${val:.2f}")
                        total += val
        if total > 0:
            return round(total, 2), holdings
    except Exception:
        pass
    return None, []

def check_pipeline_health(states: dict) -> dict:
    """
    管道健康检查
    追踪数据是否真正流通：A1→A2→A3→A4→A5
    """
    now = time.time()
    today = time.strftime("%Y-%m-%d")
    
    health = {}
    
    # A1 是否有今日产出
    a1 = states.get("a1", {})
    a1_ts = a1.get("ts_unix", 0)
    a1_has_today = time.strftime("%Y-%m-%d", time.localtime(a1_ts)) == today if a1_ts else False
    health["a1_has_output"] = f"{'✅' if a1_has_today else '❌'} {time.strftime('%Y-%m-%d %H:%M', time.localtime(a1_ts)) if a1_ts else '无数据'}"
    
    # A2 是否有今日产出
    a2 = states.get("a2", {})
    a2_ts = a2.get("ts_unix", 0)
    a2_has_today = time.strftime("%Y-%m-%d", time.localtime(a2_ts)) == today if a2_ts else False
    health["a2_has_output"] = f"{'✅' if a2_has_today else '❌'} {time.strftime('%Y-%m-%d %H:%M', time.localtime(a2_ts)) if a2_ts else '无数据'}"
    
    # A1→A2链路：A2是否在A1之后运行
    if a1_ts and a2_ts:
        health["a1_to_a2"] = "✅" if a2_ts > a1_ts else "⚠️ A2比A1早跑"
    else:
        health["a1_to_a2"] = "❌ 断链"
    
    # A3 是否有今日产出
    a3 = states.get("a3", {})
    a3_ts = a3.get("ts_unix", 0)
    a3_has_today = time.strftime("%Y-%m-%d", time.localtime(a3_ts)) == today if a3_ts else False
    health["a3_has_output"] = f"{'✅' if a3_has_today else '❌'} {time.strftime('%Y-%m-%d %H:%M', time.localtime(a3_ts)) if a3_ts else '无数据'}"
    
    # A2→A3链路：A3是否在A2之后运行
    if a2_ts and a3_ts:
        health["a2_to_a3"] = "✅" if a3_ts > a2_ts else "⚠️ A3比A2早跑（可能是旧数据）"
    else:
        health["a2_to_a3"] = "❌ 断链"
    
    # A4 最新节点时间
    a4 = states.get("a4", {})
    a4_ts = a4.get("ts_unix", 0)
    a4_recent = (now - a4_ts) < 3600 if a4_ts else False  # 1小时内算活跃
    health["a4_recent_active"] = "✅ 活跃" if a4_recent else ("⚠️ 超过1小时未更新" if a4_ts else "❌ 无数据")
    
    # A3→A4链路：A4是否执行了A3的推荐
    a3_coin = a3.get("data", {}).get("coin") if a3.get("data") else None
    a4_coin = a4.get("data", {}).get("action") if a4.get("data") else None
    if a3_coin and a4_coin:
        health["a3_to_a4"] = "✅ A4已响应A3推荐"
    elif a3_coin:
        health["a3_to_a4"] = "⚠️ A3推荐了币但A4未执行"
    else:
        health["a3_to_a4"] = "⏳ 暂无A3推荐或A4数据"
    
    # A5今日复盘
    a5 = states.get("a5", {})
    a5_ts = a5.get("ts_unix", 0)
    a5_has_today = time.strftime("%Y-%m-%d", time.localtime(a5_ts)) == today if a5_ts else False
    health["a5_today_review"] = "✅ 已出" if a5_has_today else "❌ 未出"
    
    # A6/A9是否为本周
    a6 = states.get("a6", {})
    a9 = states.get("a9", {})
    a6_ts = a6.get("ts_unix", 0)
    a9_ts = a9.get("ts_unix", 0)
    health["a6_weekly"] = f"{'✅ 本周已跑' if a6_ts and (now - a6_ts) < 7*86400 else '⏳ 待下周一'}"
    health["a9_weekly"] = f"{'✅ 本周已跑' if a9_ts and (now - a9_ts) < 7*86400 else '⏳ 待下周一'}"
    
    # A7/A8是否活跃
    a7 = states.get("a7", {})
    a8 = states.get("a8", {})
    a7_ts = a7.get("ts_unix", 0)
    a8_ts = a8.get("ts_unix", 0)
    a7_active = (now - a7_ts) < 3600 if a7_ts else False
    a8_active = (now - a8_ts) < 7200 if a8_ts else False
    health["a7_sentinel"] = "✅ 活跃监控中" if a7_active else ("⚠️ 超过1小时无数据" if a7_ts else "⏳ 等待激活")
    health["a8_fund"] = "✅ 活跃监控中" if a8_active else ("⚠️ 超过2小时无数据" if a8_ts else "⏳ 等待激活")
    
    # ZH简报
    zh = states.get("zh", {})
    zh_ts = zh.get("ts_unix", 0)
    zh_has_today = time.strftime("%Y-%m-%d", time.localtime(zh_ts)) == today if zh_ts else False
    health["zh_brief_today"] = "✅ 已出" if zh_has_today else "❌ 未出"
    
    return health


def check_data_dimensions(states: dict) -> list:
    """
    数据维度利用率检测
    A1有6维数据，下游Agent用了几维？
    """
    gaps = []
    
    a1 = states.get("a1", {})
    a1_data = a1.get("data", {}) if a1.get("data") else {}
    a1_dims = a1_data.get("data_dims_available", 0)
    a1_total = a1_data.get("data_dims_total", 6)
    
    if a1_total > 0:
        used_pct = (a1_dims / a1_total) * 100
        if used_pct < 100:
            gaps.append(f"A1有{a1_total}维数据，实际采集到{a1_dims}维（{used_pct:.0f}%），{a1_total - a1_dims}维待接入")
    
    # 这里可以扩展更多维度检查
    # 比如A2有没有用到A1的F&G数据
    
    return gaps


def load_prev_close(today: str):
    """昨日收盘基准：优先 data/total_asset.json（日期!=今天）；
    兜底 data/TRADES.md 中今天之前最后一条 总资/总权益 记录。"""
    # 优先 total_asset.json
    try:
        with open(os.path.join(PROJECT_ROOT, "data", "total_asset.json"), "r", encoding="utf-8") as f:
            ta = json.load(f)
        if ta.get("date") and ta["date"] != today and ta.get("total"):
            return float(ta["total"])
    except Exception:
        pass
    # 兜底 TRADES.md 带日期记录（按行解析，两种格式都认）
    try:
        with open(os.path.join(PROJECT_ROOT, "data", "TRADES.md"), "r", encoding="utf-8") as f:
            lines = f.read().split("\n")
        cur_date = None
        prev = None
        for ln in lines:
            m = re.search(r"#{2,3}\s+(\d{4}-\d{2}-\d{2})", ln)
            if m:
                cur_date = m.group(1)
                continue
            if cur_date is None or cur_date >= today:
                continue
            m1 = re.search(r"(?:总权益|总资)\s*(?:[=~:：]+\s*|\$)\s*\*{0,2}\s*~?\$?(\d+\.\d+)", ln)
            m2 = re.search(r"\|\s*(?:总资|净值)\s*\|\s*\$?(\d+\.\d+)", ln)
            val = None
            if m1:
                val = float(m1.group(1))
            elif m2:
                val = float(m2.group(1))
            if val is not None:
                prev = val
        return prev
    except Exception:
        return None


def compute_daily_target():
    """
    每日盈利目标追踪 + 诊断点
    """
    now = time.localtime()
    today_str = time.strftime("%Y-%m-%d")
    hour = now.tm_hour
    minute = now.tm_min
    
    prev_close = load_prev_close(today_str)
    baseline = prev_close if prev_close else INITIAL_CAPITAL
    daily_target_amount = baseline * (1 + DAILY_TARGET_PCT / 100)
    expected_daily_profit = baseline * DAILY_TARGET_PCT / 100
    
    # 获余额
    balance, holdings = fetch_balance()
    
    result = {
        "date": today_str,
        "initial_capital": INITIAL_CAPITAL,
        "prev_close": round(baseline, 2),
        "daily_target_pct": DAILY_TARGET_PCT,
        "daily_target_amount": round(daily_target_amount, 2),
        "expected_profit_today": round(expected_daily_profit, 2),
        "check_time": f"{hour:02d}:{minute:02d}",
    }
    
    if balance is not None:
        profit = balance - baseline
        profit_pct = (profit / baseline) * 100
        progress_pct = (profit / expected_daily_profit) * 100 if expected_daily_profit != 0 else 0
        
        result["current_balance"] = round(balance, 2)
        result["profit_today"] = round(profit, 2)
        result["profit_pct"] = round(profit_pct, 2)
        result["target_progress_pct"] = round(progress_pct, 1)
        result["holdings"] = holdings
        result["balance_source"] = "Binance API (实时)"
        
        # 诊断点判断
        result["diagnosis"] = {}
        
        # 14:00-14:30 检查：过半时间过去了，目标完成了多少？
        if hour == 14 and minute <= 30:
            if progress_pct < 50:
                result["diagnosis"]["14:00"] = f"🔴 诊断点：时间过半({hour}:{minute})，目标仅完成{progress_pct:.0f}%，严重落后。建议立即排查→"
            else:
                result["diagnosis"]["14:00"] = f"🟢 诊断点：时间过半，目标完成{progress_pct:.0f}%，在轨道上"
        
        # 20:00-20:30 检查：交易日尾声，能补救吗？
        if hour == 20 and minute <= 30:
            if progress_pct < 100:
                result["diagnosis"]["20:00"] = f"🔴 诊断点：交易日尾声({hour}:{minute})，目标完成{progress_pct:.0f}%，今日无法达标。记录经验→"
            else:
                result["diagnosis"]["20:00"] = f"🟢 诊断点：交易日尾声，目标已达成{progress_pct:.0f}%"
        
        # 每次检查都记录状态
        if profit < 0:
            result["risk_level"] = "🔴 亏损中"
        elif progress_pct >= 100:
            result["risk_level"] = "🟢 达标"
        elif progress_pct >= 50:
            result["risk_level"] = "🟡 进展中"
        else:
            result["risk_level"] = "🔴 落后"
    else:
        result["current_balance"] = None
        result["profit_today"] = None
        result["balance_source"] = "❌ 余额查询失败"
        result["risk_level"] = "⚠️ 数据不可达"
    
    return result


def check_system_alerts(states: dict, pipeline: dict, dim_gaps: list, target: dict) -> list:
    """
    系统告警汇总
    只报告真正需要人关注的问题
    """
    alerts = []
    
    # 1. 管道断链
    for key, val in pipeline.items():
        if val.startswith("❌"):
            alerts.append({"severity": "🔴", "type": "管道断链", "detail": f"{key}: {val}"})
        elif val.startswith("⚠️"):
            alerts.append({"severity": "🟡", "type": "管道异常", "detail": f"{key}: {val}"})
    
    # 2. 数据缺口
    for g in dim_gaps:
        alerts.append({"severity": "🟡", "type": "数据缺口", "detail": g})
    
    # 3. 盈利风险
    risk = target.get("risk_level", "")
    if "亏损" in risk:
        alerts.append({"severity": "🔴", "type": "盈利风险", "detail": f"当前{risk}，累计{target.get('profit_today')}，目标{target.get('expected_profit_today')}"})
    
    # 4. Agent异常
    for agent_name, state in states.items():
        if state.get("status") == "error":
            alerts.append({"severity": "🔴", "type": "Agent异常", "detail": f"{agent_name}: {state.get('errors', '未知错误')}"})
    
    return alerts


def aggregate():
    """主函数：聚合所有数据 → 输出 global_state.json"""
    
    # 1. 读所有Agent状态
    agents = ["a1", "a2", "a3", "a4", "a5", "a6", "a7", "a8", "a9", "zh"]
    states = {name: read_state(name) for name in agents}
    
    # 2. 管道健康
    pipeline = check_pipeline_health(states)
    
    # 3. 数据维度利用率
    dim_gaps = check_data_dimensions(states)
    
    # 4. 盈利目标
    target = compute_daily_target()
    
    # 5. 系统告警
    alerts = check_system_alerts(states, pipeline, dim_gaps, target)
    
    # 6. 合并输出
    global_state = {
        "global": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
            "ts_unix": int(time.time()),
            "version": "v1.0",
            "alerts_count": len(alerts)
        },
        "pipeline_health": pipeline,
        "data_dimension_gaps": dim_gaps,
        "daily_target": target,
        "alerts": alerts,
        "agents": states
    }
    
    # 7. 原子写入
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    tmp_path = OUTPUT_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(global_state, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, OUTPUT_PATH)
    
    # 8. 记录到 node_history.jsonl（每5分钟一次的总资产快照）
    node_history_path = os.path.join(PROJECT_ROOT, "data", "node_history.jsonl")
    try:
        record = {
            "t": time.strftime("%Y-%m-%d %H:%M:%S"),
            "usdt": round(target.get("current_balance", 0), 2),
            "total": round(target.get("current_balance", 0), 2),
            "holdings": target.get("holdings", []),
            "pipeline_health": pipeline,
            "alerts_count": len(alerts)
        }
        with open(node_history_path, "a") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"⚠️ node_history写入失败: {e}")
    
    # 9. 打印摘要（会被cron stdout捕获并可选发送）
    alert_emojis = "".join(a["severity"] for a in alerts[:5]) if alerts else "✅"
    target_status = target.get("risk_level", "⚠️")
    bal = target.get("current_balance", "N/A")
    
    print(f"【状态聚合】{target.get('check_time')} | 余额${bal} | 目标{target.get('target_progress_pct','N/A')}% | {target_status} | 告警{alerts}条 | {alert_emojis}")
    if alerts:
        for a in alerts[:3]:
            print(f"  {a['severity']} {a['type']}: {a['detail'][:80]}")
    
    return global_state


if __name__ == "__main__":
    aggregate()
