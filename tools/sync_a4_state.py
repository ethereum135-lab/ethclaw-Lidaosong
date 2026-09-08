#!/usr/bin/env python3
"""
A4状态同步器 — 从TRADES.md提取最新A4状态，写入state/a4.json

背景：A4引擎运行在AWS（独立部署），本地state/a4.json会过期。
本脚本每5分钟随state_aggregator.py跑一次，从TRADES.md解析最新
A4活动状态，确保global_state.json显示正确。

输出：state/a4.json（含真实ts_unix、持仓数、USDT余额、信号ID）
"""
import json, os, re, time

PROJECT_ROOT = "/Users/lidaosong/zq_web4_trading_system"
TRADES_PATH = os.path.join(PROJECT_ROOT, "audit", "TRADES.md")
STATE_PATH = os.path.join(PROJECT_ROOT, "state", "a4.json")
NODE_HISTORY = os.path.join(PROJECT_ROOT, "data", "node_history.jsonl")


# ═══ 新「执行节点」格式解析（2026-08-08 修复：A4引擎迁移后state长期陈旧根因）═══
# A4引擎自08-06起写 data/TRADES.md 的「执行节点 (信号模式 · 30min周期)」格式，
# 旧sync_a4_state.py只解析audit/TRADES.md的「持仓评估/信号发送」旧格式 →
# 每5分钟解析失败 → state/a4.json永久停留旧数据 → a4_prep输入摘要报错/下游误判。
# 修复：优先读data/TRADES.md并解析新格式；旧格式解析保留为fallback。
NEW_TRADES_PATH = os.path.join(PROJECT_ROOT, "data", "TRADES.md")


def parse_sig_format() -> dict:
    """解析 data/TRADES.md 的 `## sig_YYYYMMDD_HHMM_seqNNN (HOLD)` bullet 格式（2026-08-10新增）。

    A4引擎自08-09改用此格式（替代 `### ... BJT | 执行节点` 表格格式），旧解析器
    每5分钟匹配失败 → state/a4.json 永久停留旧数据。本函数提取最新sig块的关键字段。
    """
    if not os.path.exists(NEW_TRADES_PATH):
        return None
    with open(NEW_TRADES_PATH, "r", encoding="utf-8") as f:
        text = f.read()

    # 匹配所有 sig 块标题，取最后一个（2026-08-14二次修复：A4标题三格式
    #   A. `## sig_YYYYMMDD_HHMM_seqN (HOLD)` 旧bullet格式
    #   B. `## YYYY-MM-DD HH:MM BJT (sig_YYYYMMDD_HHMM_seqN) | HOLD` 日期BJT格式（08-14 04:30起）
    #   C. `## YYYY-MM-DD HH:MM (A4 seqN) — HOLD` 日期(A4 seq)格式（08-14 16:00起, 无sig_前缀）
    #   原双格式正则漏C → 16:00后新块全部漏掉，state永远停在最后一个B格式块(15:00)
    #   2026-08-28三次修复：08-25 17:30起A4引擎标题再次演变，原三格式全部失配 →
    #   state停在08-25 17:00(sig_1725, 假5持仓)。新增格式D/E/F：
    #   D. `### YYYY-MM-DD HH:MM BJT — A4节点信号 (seq N)`（08-25 17:30 ~ 08-28 00:30）
    #   E. `## sig_YYYYMMDD_HHMM_seqN | YYYY-MM-DD HH:MM BJT | A4`（08-28 01:00起）
    #   F. `## A4节点 YYYY-MM-DD HH:MM BJT (seq N)` / `## A4 YYYY-MM-DD HH:MM (seq N) — 动作`
    #      / `## YYYY-MM-DD HH:MM A4节点 (seq N)`（08-28 07:00起）
    sig_headers = list(re.finditer(
        r'^#{2,3} (?:'
        r'sig_(\d{8})_(\d{4})_(\d+) \(([A-Z]+)\)|'
        r'\d{4}-\d{2}-\d{2} \d{2}:\d{2} BJT \(sig_(\d{8})_(\d{4})_(\d+)\) \| ([A-Z]+)|'
        r'(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}) \(A4 (\d+)\) [—\-] ([A-Z]+)|'
        r'(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}) BJT [—\-] A4节点信号 \(seq (\d+)\)|'
        r'sig_(\d{8})_(\d{4})_(\d+) \| (\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}) BJT \| A4(?: \|.*)?|'
        r'(?:A4节点 |A4 )?(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2})(?: BJT)?(?: A4节点)? \((?:seq )?(\d+)\)(?: [—\-] ([^\n]+))?'
        r')',
        text, re.MULTILINE
    ))
    if not sig_headers:
        return None
    last = sig_headers[-1]
    if last.group(1):  # 格式A
        ymd, hhmm, seq, action = last.group(1), last.group(2), last.group(3), last.group(4)
    elif last.group(5):  # 格式B
        ymd, hhmm, seq, action = last.group(5), last.group(6), last.group(7), last.group(8)
    elif last.group(9):  # 格式C
        ymd = last.group(9) + last.group(10) + last.group(11)
        hhmm = last.group(12) + last.group(13)
        seq, action = last.group(14), last.group(15)
    elif last.group(16):  # 格式D
        ymd = last.group(16) + last.group(17) + last.group(18)
        hhmm = last.group(19) + last.group(20)
        seq, action = last.group(21), "A4节点信号"
    elif last.group(22):  # 格式E
        ymd, hhmm, seq = last.group(22), last.group(23), last.group(24)
        action = "A4"
    else:              # 格式F
        ymd = last.group(30) + last.group(31) + last.group(32)
        hhmm = last.group(33) + last.group(34)
        seq = last.group(35)
        action = (last.group(36) or "A4节点").strip()
    # 块内容：标题行之后到下一个 `## ` 或文件末尾
    block_end = sig_headers[-1].end()
    nxt = re.search(r'^## ', text[block_end:], re.MULTILINE)
    body = text[block_end:block_end + (nxt.start() if nxt else len(text) - block_end)]

    ts_str = f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:8]} {hhmm[:2]}:{hhmm[2:]}"
    ts_unix = int(time.mktime(time.strptime(ts_str, "%Y-%m-%d %H:%M")))

    result = {
        "agent": "a4",
        "status": "ok",
        "data": {
            "positions_count": 0,
            "usdt_balance": 0.0,
            "last_action": action,
            "last_signal_id": f"sig_{ymd}_{hhmm}_{seq}",
            "buy_signals": 0,
            "sell_signals": 0,
            "active_positions": [],
            "push_status": "未知",
            "fng_value": None,
        },
        "errors": None,
        "timestamp": f"{ts_str}:00+08:00",
        "ts_unix": ts_unix,
    }

    # USDT free: `USDT free $0.96` / `free仅$0.96` / `USDT: free $7.79` / `USDT买力$9.39`(格式C)
    # 2026-08-28三次修复: 新格式 `free USDT=$1.04(API 07:10:24核实)` — USDT=前缀变体
    u = re.search(r'USDT(?: free|: free| free仅| free=|=\$?|买力)\$?([0-9.]+)', body) \
        or re.search(r'free仅\$([0-9.]+)', body)
    if u:
        result["data"]["usdt_balance"] = float(u.group(1))

    # 持仓: 支持三种格式（2026-08-12修复：A4新格式「活跃A4持仓N个(...)」解析失败 → 持仓恒0）
    #   旧格式: `交易仓4/4满员(TST+PEPE+BROCCOLI714+BOME)`
    #   新格式: `活跃A4持仓4个(CRCLB+BABY+LINK+HOME=4仓上限)` / `持仓4币平稳(LINK+1.33%/HOME+2.63%/...)`
    p = (re.search(r'活跃A4持仓(\d+)个\(([^)]*)\)', body)
         or re.search(r'交易仓(\d+)/\d+满员\(([^)]*)\)', body)
         or re.search(r'交易仓(\d+)/\d+=([^;\n]+)', body)
         or re.search(r'持仓(\d+)币平稳\(([^)]*)\)', body)
         or re.search(r'持仓(\d+)/\d+超限', body))
    if p:
        result["data"]["positions_count"] = int(p.group(1))
        coins = []
        # 超限格式无币种列表（`持仓5/4超限`），positions_count仍有效
        if p.lastindex is not None and p.lastindex >= 2:
            if '%' in p.group(2):
                # 2026-08-12修复: 新格式「持仓N币平稳(LINK+0.6%/HOME+0.9%/CRCLB+0.4%/BABY-0.9%)」
                # 币种与涨跌%混用 + 分隔，旧split('+')把 `0.6%/HOME` 拆成无效片段 →
                # active_positions 只剩首币(LINK)，a4_prep/a4_input_summary/A8报告全部读错持仓。
                # 涨跌格式: 币种([A-Z][A-Z0-9]*)后紧跟 [+-]数字%
                coins = re.findall(r'([A-Z][A-Z0-9]*?)(?=[+\-][\d.]+%)', p.group(2))
                # 2026-08-16修复: `交易仓4/4=LINK≈$15.17(均价...)+MOVR≈$4.78(-4.2%)+...` 变体
                # 币种后跟 ≈$价格，findall(涨跌%)提取不到 → 用 ≈$ 锚定提取
                if not coins:
                    coins = re.findall(r'([A-Z][A-Z0-9]*?)≈\$', p.group(2))
            else:
                # 纯币名列表格式: `TST+PEPE+BROCCOLI714+BOME` / `CRCLB+BABY+LINK+HOME=4仓上限`
                for c in p.group(2).split('+'):
                    c = c.strip()
                    if not c:
                        continue
                    # 新格式币种可能带 `=4仓上限` 后缀（`HOME=4仓上限`）→ 取=前
                    sym = c.split('=')[0].strip()
                    if re.match(r'^[A-Z0-9]{2,12}$', sym):
                        coins.append(sym)
            result["data"]["active_positions"] = coins
    else:
        # 2026-08-28三次修复: 新bullet格式持仓行（旧格式p全部失配 → 持仓恒0）
        #   `- 持仓(07:10实价): ZEC@858.19(入场843.26,+1.77%...) + PROM@4.847(...) + UNI@4.615(...) 3/4`
        #   `- 持仓: ZEC +1.77% HOLD(...) | PROM +19.9% HOLD(...) | UNI -0.28% HOLD(...)`
        p_new = re.search(r'持仓(?:\([^)]*\))?:\s*(.+?)(?:\s+(\d+)/\d+)?\s*$', body, re.MULTILINE)
        if p_new:
            seg = p_new.group(1)
            coins = re.findall(r'([A-Z][A-Z0-9]*)(?=@)', seg)  # 格式1: 币种后跟@价格
            if not coins:
                coins = re.findall(r'([A-Z][A-Z0-9]*)(?=\s*[+\-][\d.]+%)', seg)  # 格式2: 币种后跟涨跌%
            if coins:
                result["data"]["positions_count"] = len(coins) if p_new.group(2) is None else int(p_new.group(2))
                result["data"]["active_positions"] = coins

    # FNG
    f = re.search(r'FNG=(\d+)', body)
    if f:
        result["data"]["fng_value"] = int(f.group(1))

    # push_status
    ps = re.search(r'a4_signals\.json 已推送AWS并验证(?: \(| 已推送AWS并验证)', body) \
        or re.search(r'已推送AWS并验证', body)
    if ps:
        result["data"]["push_status"] = "✅已推送AWS并验证"

    return result


def parse_new_format(text: str) -> dict:
    """解析 data/TRADES.md 的「执行节点」块格式（2026-08-08新增）"""
    block_pattern = (
        r'### (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) BJT \| 执行节点[^\n]*\n'
        r'\| 字段 \| 值 \|\n'
        r'\|:-----\|:---\|\n'
        r'((?:\|[^\n]*\|\n)+)'
    )
    blocks = re.findall(block_pattern, text)
    if not blocks:
        return None
    ts_str, body = blocks[-1]  # 最后一组 = 最新

    result = {
        "agent": "a4",
        "status": "ok",
        "data": {
            "positions_count": 0,
            "usdt_balance": 0.0,
            "last_action": "无操作",
            "last_signal_id": None,
            "buy_signals": 0,
            "sell_signals": 0,
            "active_positions": [],
            "push_status": "未知",
        },
        "errors": None,
        "timestamp": None,
        "ts_unix": 0,
    }
    ts_unix = int(time.mktime(time.strptime(ts_str, "%Y-%m-%d %H:%M")))
    result["timestamp"] = f"{ts_str}:00+08:00"
    result["ts_unix"] = ts_unix

    action_m = re.search(r'\| 本次动作 \| ([^|]+) \|', body)
    if action_m:
        action = action_m.group(1).strip()
        result["data"]["last_action"] = action
        buys = re.search(r'\((\d+)买(\d+)卖\)', action)
        if buys:
            result["data"]["buy_signals"] = int(buys.group(1))
            result["data"]["sell_signals"] = int(buys.group(2))

    pos_m = re.search(r'\| 持仓状态 \| ([^|]*?) \| USDT free=\$([0-9.]+)[^|]*\| 总权益[约≈]\$([0-9.]+)', body)
    if pos_m:
        pos_text = pos_m.group(1)
        # 持仓计数：形如 "NEAR 9.3236@1.5950($14.87, 浮亏-$0.05) + MMT ..." 按 "+" 分割非空段
        parts = [p.strip() for p in pos_text.split("+") if p.strip() and "@" in p]
        result["data"]["positions_count"] = len(parts)
        result["data"]["active_positions"] = [p.split()[0] for p in parts if p.split()]
        result["data"]["usdt_balance"] = float(pos_m.group(2))
        total_eq = float(pos_m.group(3))
        result["data"]["total_equity"] = total_eq
        result["data"]["total_source"] = "data/TRADES.md执行节点"

    sig_m = re.search(r'\| a4_signals.json \| (sig_\S+) → ([^|]+) \|', body)
    if sig_m:
        result["data"]["last_signal_id"] = sig_m.group(1)
        result["data"]["push_status"] = sig_m.group(2).strip()

    fng_m = re.search(r'\| FNG \| (\d+)', body)
    if fng_m:
        result["data"]["fng_value"] = int(fng_m.group(1))

    return result


def parse_latest_from_trades() -> dict:
    """从TRADES.md解析最新的A4状态（优先新格式，fallback旧格式）"""
    # 首选：data/TRADES.md（新活跃日志，A4引擎当前写入路径）
    if os.path.exists(NEW_TRADES_PATH):
        with open(NEW_TRADES_PATH, "r", encoding="utf-8") as f:
            text = f.read()
        result = parse_new_format(text)
        if result:
            return result
    # fallback：旧路径 audit/TRADES.md 旧格式
    if not os.path.exists(TRADES_PATH):
        return None

    with open(TRADES_PATH, "r", encoding="utf-8") as f:
        text = f.read()

    # 提取所有信号发送区块
    signal_pattern = (
        r'### (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) BJT \| 信号发送\n'
        r'\| 字段 \| 值 \|\n'
        r'\|:-----\|:---\|\n'
        r'\| 信号ID \| (\S+) \|\n'
        r'\| 买入信号 \| (\d+)个 \|\n'
        r'\| 卖出信号 \| (\d+)个 \|\n'
        r'\| 详情 \| 买入: \[([^\]]*)\] 卖出: \[([^\]]*)\] \|\n'
        r'\| 状态 \| (.+) \|'
    )
    signals = re.findall(signal_pattern, text)

    # 提取所有持仓评估区块
    eval_pattern = (
        r'### (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) BJT \| 持仓评估\n'
        r'\| 字段 \| 值 \|\n'
        r'\|:-----\|:---\|\n'
        r'\| 持仓数 \| (\d+) \|\n'
        r'\| USDT \| \$([0-9.]+) \|\n'
        r'\| 操作 \| (.+) \|\n'
        r'\| 详情 \| (.*) \|'
    )
    evals = re.findall(eval_pattern, text)

    if not signals and not evals:
        return None

    # ========== 构建状态 ==========
    result = {
        "agent": "a4",
        "status": "ok",
        "data": {
            "positions_count": 0,
            "usdt_balance": 0.0,
            "last_action": "无操作",
            "last_signal_id": None,
            "buy_signals": 0,
            "sell_signals": 0,
            "active_positions": []
        },
        "errors": None,
        "timestamp": None,
        "ts_unix": 0
    }

    # 解析最新持仓评估 (最后一组 = 最新)
    if evals:
        latest_eval = evals[-1]
        ts_str = latest_eval[0]
        ts_unix = int(time.mktime(time.strptime(ts_str, "%Y-%m-%d %H:%M")))
        result["timestamp"] = f"{ts_str}:00+08:00"
        result["ts_unix"] = ts_unix
        result["data"]["positions_count"] = int(latest_eval[1])
        result["data"]["usdt_balance"] = float(latest_eval[2])
        result["data"]["last_action"] = latest_eval[3]

    # 解析最新信号
    if signals:
        latest_sig = signals[-1]
        sig_ts = latest_sig[0]
        sig_unix = int(time.mktime(time.strptime(sig_ts, "%Y-%m-%d %H:%M")))

        result["data"]["last_signal_id"] = latest_sig[1]
        result["data"]["buy_signals"] = int(latest_sig[2])
        result["data"]["sell_signals"] = int(latest_sig[3])

        buy_raw = latest_sig[4].strip()
        sell_raw = latest_sig[5].strip()
        result["data"]["signals_detail"] = {
            "buy": [x.strip() + ")" for x in buy_raw.split(")") if x.strip()] if buy_raw else [],
            "sell": [x.strip() + ")" for x in sell_raw.split(")") if x.strip()] if sell_raw else []
        }
        result["data"]["push_status"] = latest_sig[6]

        # 使用更活跃的时间戳 (信号 或 评估中较新的)
        if sig_unix > result.get("ts_unix", 0):
            result["timestamp"] = f"{sig_ts}:00+08:00"
            result["ts_unix"] = sig_unix

    # 从node_history.jsonl补充余额数据
    try:
        with open(NODE_HISTORY, "r") as f:
            lines = f.readlines()
            if lines:
                last_line = json.loads(lines[-1].strip())
                total = last_line.get("total", 0)
                if total > 0:
                    result["data"]["total_equity"] = total
                    result["data"]["total_source"] = "node_history.jsonl"
    except Exception:
        pass

    return result


def write_state(data: dict):
    """原子写入state/a4.json"""
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    tmp = STATE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
    os.replace(tmp, STATE_PATH)


def main():
    # 2026-08-19 ZH修复: 优先解析 ### 执行节点 当前格式(parse_latest_from_trades)，
    # 再fallback到 ## sig_ 遗留格式(parse_sig_format)。
    # 原顺序(parse_sig_format or parse_latest_from_trades)导致匹配到08-16陈旧## sig_块短路，
    # state/a4.json永久停留08-16(USDT$8.35/4僵尸仓)，A4误判"无资金+4/4占位"拒绝一切买入。
    # 2026-08-28三次修复: 08-25 17:30起A4引擎改bullet格式(### A4节点信号/## sig_|A4/## A4节点)，
    # parse_latest_from_trades仅匹配旧`### | 执行节点`表格格式→停在08-25 17:00(sig_1725假5持仓)。
    # 改双解析取最新ts_unix，不再依赖固定优先级。
    a4_state = None
    for cand in (parse_latest_from_trades(), parse_sig_format()):
        if cand and (a4_state is None or cand.get("ts_unix", 0) > a4_state.get("ts_unix", 0)):
            a4_state = cand
    if a4_state:
        # 2026-08-19 ZH: Binance API直连(SOCKS5)覆盖余额/持仓 —— SSH断连期间的真实数据源
        a4_state = apply_api_balance(a4_state)
        write_state(a4_state)
        ts_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(a4_state["ts_unix"]))
        print(f"[sync_a4_state] ✅ 更新 A4 状态: "
              f"持仓{a4_state['data']['positions_count']} | "
              f"USDT${a4_state['data']['usdt_balance']} | "
              f"信号{a4_state['data'].get('last_signal_id', 'N/A')} | "
              f"时间{ts_str} | 余额源: {a4_state['data'].get('balance_source', 'TRADES.md')}")
    else:
        print("[sync_a4_state] ⚠️ 未从TRADES.md找到A4数据，保留原状态")


def apply_api_balance(a4_state: dict) -> dict:
    """Binance API直连(SOCKS5)覆盖余额/持仓 —— SSH断连时(AWS不可达)的真实数据源。

    2026-08-19 ZH新增: A4引擎的USDT余额原依赖SSH→AWS→Binance链路，SSH断连后
    state停留陈旧值($8.35)，实际free=$34.08。此处用本地SOCKS5直连Binance API
    获取真实余额+真实持仓(估值>$1)，覆盖TRADES.md解析出的僵尸数据。
    失败时保留解析值并在balance_source标注。
    """
    import subprocess, hmac, hashlib
    try:
        creds = json.load(open(os.path.join(PROJECT_ROOT, "config", "auth.json")))
        api_key = creds['binance']['api_key']
        api_secret = creds['binance']['api_secret']
        ts = int(time.time() * 1000)
        qs = f"timestamp={ts}"
        sig = hmac.new(api_secret.encode(), qs.encode(), hashlib.sha256).hexdigest()
        url = f"https://api.binance.com/api/v3/account?{qs}&signature={sig}"
        r = subprocess.run(
            ['curl', '--socks5-hostname', '127.0.0.1:1080', '-s', '--max-time', '20',
             '-H', f'X-MBX-APIKEY: {api_key}', url],
            capture_output=True, text=True)
        acc = json.loads(r.stdout)
        if 'balances' not in acc:
            a4_state['data']['balance_source'] = f"API响应异常({str(acc)[:60]})，保留TRADES.md值"
            return a4_state
        # 价格表(估算持仓价值用) — 2026-08-24 冲刺修复: 全量ticker(~2500币)经SOCKS5 20s超时截断
        # → prices近乎为空 → 真实持仓全被误判为"不存在/尘仓"(real_pos=[], 权益只剩USDT, 曾误报幽灵仓)。
        # 方案: ①定向查账户非零币种(秒回); ②若含无效symbol(如LDSHIB2)整体报错 → 回退全量拉取(60s, 实测~15s)。
        non_zero_assets = [b['asset'] for b in acc['balances']
                           if float(b['free']) > 0 or float(b['locked']) > 0]
        syms_json = json.dumps([f"{a}USDT" for a in non_zero_assets
                                if a not in ('USDT', 'USDC', 'BUSD', 'FDUSD', 'TUSD', 'DAI')])
        prices = {}
        r2 = subprocess.run(
            ['curl', '--socks5-hostname', '127.0.0.1:1080', '-s', '--max-time', '25',
             '-G', 'https://api.binance.com/api/v3/ticker/price',
             '--data-urlencode', f'symbols={syms_json}'],
            capture_output=True, text=True)
        try:
            for p in json.loads(r2.stdout):
                prices[p['symbol']] = float(p['price'])
        except Exception:
            prices = {}
        if not prices:
            # 回退: 全量拉取(60s足够, 实测~15s)
            r3 = subprocess.run(
                ['curl', '--socks5-hostname', '127.0.0.1:1080', '-s', '--max-time', '60',
                 'https://api.binance.com/api/v3/ticker/price'],
                capture_output=True, text=True)
            try:
                for p in json.loads(r3.stdout):
                    prices[p['symbol']] = float(p['price'])
            except Exception:
                prices = {}
        if not prices:
            a4_state['data']['price_fetch_failed'] = True
        bal = {b['asset']: float(b['free']) for b in acc['balances']}
        locked = {b['asset']: float(b['locked']) for b in acc['balances']}
        free_usdt = bal.get('USDT', 0.0)
        locked_usdt = locked.get('USDT', 0.0)
        # 真实持仓: 估值>= $5的非稳定币（MIN_NOTIONAL级，< $5为不可交易尘仓不占A4仓位上限）
        # 2026-08-19 ZH: 排除ETH/BNB —— 网格/历史遗留仓，A4从不管理，计入会误占4仓上限
        A4_NON_MANAGED = ('ETH', 'BNB', 'WBETH', 'LDETH', 'LDBNB')
        real_pos = []
        for asset, qty in bal.items():
            if asset in ('USDT', 'USDC', 'BUSD', 'FDUSD', 'TUSD', 'DAI'):
                continue
            if asset in A4_NON_MANAGED:
                continue
            px = prices.get(f"{asset}USDT")
            if px and qty * px >= 5.0:
                real_pos.append(asset)
        # 尘仓清单(估值<$5)留档供参考
        dust_list = []
        for asset, qty in bal.items():
            if asset in ('USDT', 'USDC', 'BUSD', 'FDUSD', 'TUSD', 'DAI'):
                continue
            px = prices.get(f"{asset}USDT")
            if px and 0 < qty * px < 5.0:
                dust_list.append(f"{asset}~${qty*px:.1f}")
        a4_state['data']['usdt_balance'] = free_usdt
        a4_state['data']['usdt_locked_api'] = locked_usdt
        a4_state['data']['active_positions'] = real_pos
        a4_state['data']['positions_count'] = len(real_pos)
        a4_state['data']['dust_holdings'] = dust_list
        # 真实总权益: free/locked USDT + 全部币种估值(含网格) —— 替代TRADES.md节点的陈旧"state口径"
        total_eq = free_usdt + locked_usdt
        for b in acc['balances']:
            asset = b['asset']
            if asset == 'USDT':
                continue
            qty = float(b['free']) + float(b['locked'])
            if qty <= 0:
                continue
            px = prices.get(f"{asset}USDT")
            if px:
                total_eq += qty * px
        a4_state['data']['total_equity'] = round(total_eq, 2)
        a4_state['data']['total_equity_source'] = "Binance API直连(全账户含网格)"
        a4_state['data']['balance_source'] = "Binance API直连(SOCKS5)"
        a4_state['data']['balance_checked_at'] = time.strftime("%Y-%m-%d %H:%M:%S")
        return a4_state
    except Exception as e:
        a4_state['data']['balance_source'] = f"API失败({str(e)[:60]})，保留TRADES.md值"
        return a4_state


if __name__ == "__main__":
    main()
