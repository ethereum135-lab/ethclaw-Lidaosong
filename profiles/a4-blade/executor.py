#!/usr/bin/env python3
"""
||A4 交易官 — 纯Python执行节点 v3.0 (独立执行架构)
||零LLM依赖，100%确定逻辑，零成本。
||
||核心逻辑：
||  ① 持仓评估（每轮必做）— 止盈>5%/止损>-5%
||  ② A3买入评估（唯一币来源 — A3从选币库扫）
||  ③ 产生信号文件 → SCP到AWS → AWS独立脚本执行
||
||变更(2026-06-04): v3.0 独立执行架构
||  A4只负责信号判断，不负责执行。
||  信号通过SCP到AWS，AWS上 a4_independent.py 独立执行。
||
||变更(2026-05-18): 砍掉RSI+BB自检+全市场背离
||流程：持仓评估→A3买入评估→写信号→SCP→AWS独立执行
"""
import json, os, sys, subprocess, re, time, hmac
from datetime import datetime, timezone, timedelta

# 时区
BJT = timezone(timedelta(hours=8))

# 路径
ZQ_ROOT = "/Users/lidaosong/zq_web4_trading_system"
PATHS = {
    "a3_report": f"{ZQ_ROOT}/profiles/a3-bull/output/{datetime.now(BJT).strftime('%Y-%m-%d')}.md",
    "fk_veto": f"{ZQ_ROOT}/agents/fk/veto.json",
    "trades": f"{ZQ_ROOT}/audit/TRADES.md",
    "errors": f"{ZQ_ROOT}/audit/ERRORS.md",
    "log": f"{ZQ_ROOT}/profiles/a4-blade/logs/daily.log",
    "auth": f"{ZQ_ROOT}/config/auth.json",
    "stop": f"{ZQ_ROOT}/profiles/a4-blade/STOP",
}
SSH_BASTION = "ssh -i ~/.zq_vault/web4.0.pem -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ControlMaster=auto -o ControlPath=/tmp/ssh_mux_%r@%h:%p -o ControlPersist=300 ubuntu@15.134.211.154"
AWS_EXECUTOR = "/home/ubuntu/zq_web4_trading_system/production/engine/aws_executor.py"

# ─── 重复信号去重（2026-07-06 修复：防止同一SELL信号每30分钟无限重发）───
SELL_DEDUP_FILE = f"{ZQ_ROOT}/data/signals/sell_dedup.json"
SELL_DEDUP_HOURS = 6  # 同一币种同一方向信号6小时内不重复

# ─── 连损黑名单（2026-07-17 ZH追加：连损币48h内禁止买入）───
LOSS_BLACKLIST_FILE = f"{ZQ_ROOT}/data/loss_blacklist.json"

def _load_loss_blacklist():
    """加载连损黑名单，返回 {symbol: entry_dict}"""
    try:
        if os.path.exists(LOSS_BLACKLIST_FILE):
            with open(LOSS_BLACKLIST_FILE) as f:
                data = json.load(f)
            return data.get('entries', {})
    except:
        pass
    return {}

def load_sell_dedup():
    """加载去重跟踪文件。返回 {symbol: {action, timestamp_iso}}"""
    try:
        if os.path.exists(SELL_DEDUP_FILE):
            with open(SELL_DEDUP_FILE) as f:
                return json.load(f)
    except:
        pass
    return {}

def save_sell_dedup(tracker):
    """保存去重跟踪"""
    try:
        os.makedirs(os.path.dirname(SELL_DEDUP_FILE), exist_ok=True)
        with open(SELL_DEDUP_FILE, "w") as f:
            json.dump(tracker, f, indent=2)
    except:
        pass

def is_sell_already_sent(symbol, action, now=None):
    """检查同一币种同一方向的SELL信号是否已在SELL_DEDUP_HOURS小时内发过"""
    if now is None:
        now = datetime.now(BJT)
    tracker = load_sell_dedup()
    key = f"{symbol}_{action}"
    prev = tracker.get(key)
    if prev:
        prev_ts = datetime.fromisoformat(prev)
        elapsed = (now - prev_ts).total_seconds() / 3600
        if elapsed < SELL_DEDUP_HOURS:
            return True  # 仍在去重窗口内
    # 不在窗口内或首次：更新
    tracker[key] = now.isoformat()
    save_sell_dedup(tracker)
    return False

# ─── 独立执行架构（2026-06-04）───
# A4只负责信号判断，不负责执行。
# 信号文件由Mac SCP到AWS，AWS上 a4_independent.py 独立执行。
SIGNAL_PATH = f"{ZQ_ROOT}/data/signals/a4_signals.json"
AWS_SIGNAL_PATH = "/home/ubuntu/zq_web4_trading_system/data/signals/a4_signals.json"
AWS_RESULT_PATH = "/home/ubuntu/zq_web4_trading_system/data/signals/execution_results.json"
RESULT_PATH = f"{ZQ_ROOT}/data/signals/execution_results.json"
SIGNAL_SEQ_PATH = f"{ZQ_ROOT}/data/signals/.sequence"  # 单调递增序列号
MIN_BUY_USDT_ON_AWS = 25  # AWS独立执行的最小买入金额（在main()中根据账户规模动态调整）
# 小账户模式：当总权益<$50时自动降低MIN_BUY_USDT_ON_AWS
SMALL_ACCOUNT_THRESHOLD = 50
SMALL_ACCOUNT_MIN_BUY = 5  # 2026-08-31 ZH修订: 8→5。free=$7.81被$8门槛卡死全系统禁买(08-31实案); $5=AWS独立执行硬底(line1056 max(...,5)), 与MIN_NOTIONAL匹配
USDT_CRITICAL_THRESHOLD = 10  # USDT<$10时禁止任何新买入，全力回收资金
GRID_USDT_RESERVE = 30  # 🛡️ 网格资金保留(2026-08-31): ETH网格独占USDT(NAVIGATION.md §二), free<$30禁止A4新买入
# 🔴 2026-08-31: A4山寨引擎开关。主策略=trend_bot(全仓ETH/现金,无中间状态,NAVIGATION.md §二)，
# 账户资金归trend_bot所有 → A4新买入默认关闭(防止两策略抢资金/破坏全仓状态)。
# 开启条件：trend_bot停用 或 老李指示启用多币引擎 → 置True即恢复(profit_engine_v2为主买入源)。
ALTCOIN_ENGINE_ENABLED = False
USDT_EMERGENCY_THRESHOLD = 20  # USDT<$20且持续>3周期时强制出仓

# ─── 跌幅榜崩盘波动检测（2026-07-27 ZH追加）───
# 当>=3个币种24h跌>30%时，降低买入置信度，缩减单币金额
CRASH_WAVE_FILE = f"{ZQ_ROOT}/data/signals/.crash_wave"
CRASH_WAVE_HOURS = 4  # 检测结果4小时内有效

def _detect_crash_wave():
    """检测跌幅榜是否存在崩盘波动（多币种暴跌>30%）。
    返回: ('safe'|'crash', count, max_drop)
    """
    try:
        # 通过SOCKS5拉Binance 24hr ticker
        r = subprocess.run(
            ['curl', '--socks5-hostname', '127.0.0.1:1080', '-s', '--max-time', '15',
             'https://api.binance.com/api/v3/ticker/24hr'],
            capture_output=True, text=True, timeout=20
        )
        if r.returncode != 0 or not r.stdout.strip():
            # SOCKS5失败，读缓存文件
            crash_file = os.path.join(os.path.dirname(CRASH_WAVE_FILE), '.crash_wave_cache.json')
            if os.path.exists(crash_file):
                with open(crash_file) as f:
                    return tuple(json.load(f))
            return ('safe', 0, 0)
        
        data = json.loads(r.stdout)
        exclude = ['UP','DOWN','BULL','BEAR','BUSD','USDC','TUSD','DAI','FDUSD','BRL','TRY']
        coins_neg = [d for d in data if d['symbol'].endswith('USDT') 
                     and not any(x in d['symbol'] for x in exclude)
                     and float(d['priceChangePercent']) < -30]
        count = len(coins_neg)
        max_drop = min(float(d['priceChangePercent']) for d in coins_neg) if coins_neg else 0
        max_drop_name = min(coins_neg, key=lambda d: float(d['priceChangePercent']))['symbol'].replace('USDT','') if coins_neg else ''
        
        if count >= 3:
            result = ('crash', count, max_drop, max_drop_name)
        else:
            result = ('safe', count, max_drop, max_drop_name)
        
        # 缓存检测结果
        try:
            cache_file = os.path.join(os.path.dirname(CRASH_WAVE_FILE), '.crash_wave_cache.json')
            with open(cache_file, 'w') as f:
                json.dump(result, f)
        except:
            pass
        
        return result
    except:
        return ('safe', 0, 0, '')

_sequence_counter = 0

def get_signal_sequence():
    """获取单调递增的信号序列号"""
    global _sequence_counter
    try:
        os.makedirs(os.path.dirname(SIGNAL_SEQ_PATH), exist_ok=True)
        with open(SIGNAL_SEQ_PATH) as f:
            _sequence_counter = int(f.read().strip())
    except:
        _sequence_counter = int(time.time())  # fallback
    _sequence_counter += 1
    try:
        with open(SIGNAL_SEQ_PATH, "w") as f:
            f.write(str(_sequence_counter))
    except:
        pass
    return _sequence_counter

def ssh_run(cmd, timeout=10):
    """SSH到AWS执行命令"""
    try:
        r = subprocess.run(
            f'{SSH_BASTION} "{cmd}"',
            shell=True, capture_output=True, text=True, timeout=timeout
        )
        if r.returncode == 0:
            return r.stdout.strip()
        return None
    except:
        return None

# ─── 配置参数 ───
MIN_USDT = 15
MAX_EVALUATE_POSITIONS = 10  # 最多评估前10大持仓
PRICE_DEVIATION_PCT = 2.0
TAKE_PROFIT_PCT = 999.0     # 🚫 禁用止盈（2026-06-29 老李纠正：浮动盈利≠要跌了）
TAKE_PROFIT_FULL_PCT = 999.0  # 🚫 禁用止盈（禁止固定止盈线，出场只有P1/量价背离/硬止损/BTC-5%）
STOP_LOSS_PCT = -5.0      # 浮亏<-5% → 止损清仓（有叙事的币放宽到-8%）
STOP_LOSS_NARRATIVE_PCT = -8.0  # 有叙事的币止损线
POSITION_CONCENTRATION = 50.0  # 单一仓位>50% → 强制减仓
DUST_VALUE_THRESHOLD = 25.0   # 尘仓判定：仓位价值<$25视为尘仓
DUST_GAIN_TRIGGER = 3.0       # 尘仓回收：尘仓且24h涨幅>3%时自动卖出回收USDT
DUST_SELL_MIN_NOTIONAL = 5.0  # 币安最小下单额minNotional≈$5：低于此=物理不可成交的尘仓残值(2026-08-31老李确认手动亦无法清仓→定案永久残值)

# ─── FOMC/宏观事件日现金储备（2026-06-17 新增）───
# 宏观事件日（FOMC/CPI/NFP）：当USDT<$5且任一持仓浮盈>FOMC_PROFIT_TRIGGER%，
# 预触发25%部分止盈以创造USDT缓冲，防市场剧烈波动时无弹药抄底/补保证金
FOMC_PROFIT_TRIGGER = 5.0    # 浮盈>5%的部分止盈触发线
FOMC_SELL_RATIO = 0.25       # 触发后卖出该仓位的25%
FOMC_MIN_BUFFER = 5.0        # 至少保留$5 USDT缓冲
# 宏观事件日清单（按公告日自动匹配）
MACRO_EVENT_SYMBOLS = ['FOMC', 'CPI', 'NFP', 'FED']
# 日期格式字符串，用于检查今天是哪个事件日
# 注意：FOMC日为每月预定日期，CPI/NFP为每月固定日期

# ─── BTC市况门（2026-07-09 新增）───
# 当BTC 24h跌幅超过BTC_DEFENSIVE_THRESHOLD时，触发防御模式：
#   - 无新买入信号
#   - 有浮盈的仓位优先减半释放USDT
BTC_API_URL = "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT"
BTC_DEFENSIVE_THRESHOLD = -1.5  # BTC跌超-1.5% → 防御模式
BTC_AGGRESSIVE_THRESHOLD = -3.0 # BTC跌超-3.0% → 全面撤退模式（所有仓位减半）

def get_btc_24h_change():
    """获取BTC 24h涨跌幅。返回(float pct, str mode)，mode='normal'/'defensive'/'retreat'"""
    def _classify(chg):
        if chg <= BTC_AGGRESSIVE_THRESHOLD:
            mode = "retreat"
        elif chg <= BTC_DEFENSIVE_THRESHOLD:
            mode = "defensive"
        else:
            mode = "normal"
        return chg, mode

    try:
        import urllib.request
        resp = urllib.request.urlopen(BTC_API_URL, timeout=15)
        data = json.loads(resp.read().decode())
        chg = float(data.get("priceChangePercent", 0))
        chg, mode = _classify(chg)
        log(f"📊 BTC 24h: {chg:+.2f}% → 模式: {mode}")
        return chg, mode
    except Exception as e:
        # 🔴 2026-08-03 fix: Mac直连Binance被451封锁 → SOCKS5兜底（与_socks5_price_fallback同模式）
        # 修复前：直连失败→静默返回(0,"normal")→BTC市况门形同虚设
        try:
            import subprocess
            r = subprocess.run(
                ['curl', '--socks5-hostname', '127.0.0.1:1080', '-s', '--max-time', '15',
                 'https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT'],
                capture_output=True, text=True, timeout=18
            )
            if r.returncode == 0 and r.stdout.strip():
                data = json.loads(r.stdout)
                chg = float(data.get("priceChangePercent", 0))
                chg, mode = _classify(chg)
                log(f"📊 BTC 24h (SOCKS5): {chg:+.2f}% → 模式: {mode}")
                return chg, mode
        except Exception as e2:
            log(f"⚠️ BTC价格查询失败(直连+SOCKS5均失败): {e2}")
        log(f"⚠️ BTC价格查询失败: {e}")
        return 0, "normal"


def log(msg, file=None):
    """写日志"""
    ts = datetime.now(BJT).strftime("%Y-%m-%d %H:%M BJT")
    line = f"{ts} | {msg}"
    print(line)
    if file:
        try:
            with open(file, "a") as f:
                f.write(line + "\n")
        except:
            pass


def read_file(path):
    """安全读文件"""
    try:
        with open(path) as f:
            return f.read()
    except:
        return None


# ═══════════════════════════════════════════════
# 第一步：持仓评估
# ═══════════════════════════════════════════════

def fetch_positions():
    """从AWS获取当前所有非零持仓（SSH→SOCKS5本地兜底）"""
    result = ssh_run(f"python3 {AWS_EXECUTOR} --check")
    if result:
        try:
            assets = json.loads(result)
            positions = [a for a in assets if a["asset"] != "USDT" and float(a.get("free", 0)) > 0]
            usdt = next((float(a["free"]) for a in assets if a["asset"] == "USDT"), 0.0)
            return positions, usdt
        except:
            pass
    return _socks5_positions_fallback()


def _socks5_positions_fallback():
    """SOCKS5本地查持仓（SSH不可用时兜底）
    🔴 2026-08-03 fix: 原urllib ProxyHandler对socks5不原生支持→TypeError静默吞掉
    → 改为curl --socks5-hostname（已验证模式，同_socks5_price_fallback）"""
    try:
        import subprocess, hmac, hashlib, time
        auth = json.load(open(PATHS["auth"]))
        ak = auth["binance"]["api_key"]
        sec = auth["binance"]["api_secret"]
        ts = int(time.time() * 1000)
        query = f"timestamp={ts}&recvWindow=60000"
        sig = hmac.new(sec.encode(), query.encode(), hashlib.sha256).hexdigest()
        url = f"https://api.binance.com/api/v3/account?{query}&signature={sig}"
        r = subprocess.run(
            ['curl', '--socks5-hostname', '127.0.0.1:1080', '-s', '--max-time', '15',
             '-H', f'X-MBX-APIKEY: {ak}', url],
            capture_output=True, text=True, timeout=18
        )
        if r.returncode == 0 and r.stdout.strip():
            data = json.loads(r.stdout)
            assets = data.get("balances", [])
            positions = [a for a in assets if a["asset"] != "USDT" and float(a.get("free", 0)) + float(a.get("locked", 0)) > 0]
            usdt = next((float(a["free"]) for a in assets if a["asset"] == "USDT"), 0.0)
            return positions, usdt
        return None, f"SOCKS5持仓失败: {(r.stdout or r.stderr)[:80]}"
    except Exception as e:
        return None, f"SOCKS5持仓失败: {str(e)[:80]}"


def get_usdt_total():
    """获取USDT总余额(free+locked)。返回(free, locked)，失败返回(None, None)。
    🔴 2026-08-03: locked USDT是grid_bot锁在ETH网格买单里的资金（如$141），
    计算总权益必须计入，否则A4幻觉"总资$9"→错误触发小账户模式/USDT紧急阈值。
    用curl --socks5-hostname（urllib ProxyHandler不支持socks5原生协议）"""
    try:
        import subprocess, hmac, hashlib, time
        auth = json.load(open(PATHS["auth"]))
        ak = auth["binance"]["api_key"]
        sec = auth["binance"]["api_secret"]
        ts = int(time.time() * 1000)
        query = f"timestamp={ts}&recvWindow=60000"
        sig = hmac.new(sec.encode(), query.encode(), hashlib.sha256).hexdigest()
        url = f"https://api.binance.com/api/v3/account?{query}&signature={sig}"
        r = subprocess.run(
            ['curl', '--socks5-hostname', '127.0.0.1:1080', '-s', '--max-time', '15',
             '-H', f'X-MBX-APIKEY: {ak}', url],
            capture_output=True, text=True, timeout=18
        )
        if r.returncode == 0 and r.stdout.strip():
            data = json.loads(r.stdout)
            usdt = next((b for b in data.get("balances", []) if b["asset"] == "USDT"), None)
            if usdt:
                return float(usdt.get("free", 0)), float(usdt.get("locked", 0))
    except Exception:
        pass
    return None, None


def evaluate_position(position, current_price, entry_price=None):
    """评估单个持仓的处置方案"""
    free = float(position.get("free", 0))
    if free <= 0:
        return None

    cost = entry_price or 0
    pnl_pct = ((current_price - cost) / cost * 100) if cost > 0 else 0

    symbol = position["asset"]
    value = free * current_price

    action = "HOLD"
    reason = None

    # ① 止盈逻辑
    if pnl_pct >= TAKE_PROFIT_FULL_PCT:
        action = "SELL_ALL"
        reason = f"止盈全出: +{pnl_pct:.2f}% ≥ +{TAKE_PROFIT_FULL_PCT}%"
    elif pnl_pct >= TAKE_PROFIT_PCT:
        action = "SELL_HALF"
        reason = f"止盈半出: +{pnl_pct:.2f}% ≥ +{TAKE_PROFIT_PCT}%"

    # ② 止损逻辑（优先级高于止盈半出）
    if pnl_pct <= STOP_LOSS_PCT:
        action = "SELL_ALL"
        reason = f"止损清仓: {pnl_pct:.2f}% ≤ {STOP_LOSS_PCT}%"

    # ③ 尘仓机会性回收（2026-07-08 新增）
    # 当USDT<$50且仓位价值<$25时为尘仓。若该尘仓当日上涨>3%，自动卖出回收USDT
    # 目标：释放被尘仓锁住的资金，让系统有弹药买入新候选
    # 2026-08-31 定案：价值<$5(币安minNotional)的尘仓=物理不可清残值(47+连发REJECTED+老李手动验证)，
    # 永不生成SELL信号、不做任何回收尝试；价值≥$5才允许机会性回收（仍受下方$10 MIN_NOTIONAL防护约束）
    if value < DUST_VALUE_THRESHOLD:
        if value < DUST_SELL_MIN_NOTIONAL:
            action = "HOLD"
            reason = f"尘仓残值${value:.2f}<${DUST_SELL_MIN_NOTIONAL:.0f}(minNotional) 币安不可成交 → 放弃回收"
        elif pnl_pct > DUST_GAIN_TRIGGER:
            action = "SELL_ALL"
            reason = f"尘仓回收: 价值=${value:.2f}<${DUST_VALUE_THRESHOLD:.0f} +{pnl_pct:.2f}% >+{DUST_GAIN_TRIGGER:.0f}% → 释放USDT"
        elif entry_price is None and value > 5:
            # 无买入价但仓位价值>$5且为正浮亏：保守卖出（可能在TRADES.md格式变更前买入）
            action = "SELL_ALL"
            reason = f"尘仓回收(无买入价): 价值=${value:.2f}, 未知P&L → 释放USDT"

    return {
        "symbol": symbol,
        "free": free,
        "current_price": current_price,
        "cost_price": cost,
        "pnl_pct": round(pnl_pct, 2),
        "value": round(value, 2),
        "action": action,
        "reason": reason,
    }


def get_entry_price_from_trades(symbol):
    """从TRADES.md反查最近一次买入价，支持新旧两种格式"""
    text = read_file(PATHS["trades"])
    if not text:
        return None
    lines = text.split("\n")
    # 方法1：搜索旧格式 — | 币种 | SYMBOL | → | 执行价 | $X |
    for i in range(len(lines) - 1, -1, -1):
        m = re.search(r'\|\s*币种\s*\|\s*' + re.escape(symbol) + r'\s*\|', lines[i])
        if m:
            for j in range(i, min(len(lines), i+10)):
                pm = re.search(r'\|\s*执行价\s*\|\s*\$?([\d.]+)', lines[j])
                if pm:
                    return float(pm.group(1))
            for j in range(max(0, i-5), i):
                pm = re.search(r'\|\s*执行价\s*\|\s*\$?([\d.]+)', lines[j])
                if pm:
                    return float(pm.group(1))
    # 方法2：搜索持仓表格式 — | SYMBOL | qty | $entry | $current | $value | P&L | 判定 |
    # 先找NODE标题（倒序），在其后找持仓表
    node_headers = [idx for idx, line in enumerate(lines) if re.match(r'^## A4 NODE', line)]
    for node_start in reversed(node_headers):
        # 在当前节点到下一个节点之间搜索
        node_end = min(len(lines), node_start + 30)
        for i in range(node_start, node_end):
            # 匹配持仓表行：| SYMBOL | qty | $entry | ...
            m = re.search(
                r'^\|\s*' + re.escape(symbol) + r'\s*\|\s*[\d,]+\.?\d*\s*\|\s*\$?([\d.]+)',
                lines[i]
            )
            if m:
                price = float(m.group(1))
                if 0.000001 < price < 100000:
                    return price
    # 方法3：搜索叙事格式 — **BUY SYMBOL** qty×$price=total
    esc = re.escape(symbol)
    for i in range(len(lines) - 1, -1, -1):
        # **BUY SYM** qty×$price 或 ✅ **BUY SYM** qty×$price
        m = re.search(
            r'\*\*BUY\s+' + esc + r'\*\*.*?(\d+\.?\d*)\s*[×x]\s*\$?(\d+\.?\d*)',
            lines[i]
        )
        if m:
            return float(m.group(2))
        # 管道格式：| BUY | SYM | qty | $price |
        m = re.search(
            r'\|\s*(?:BUY|买入)\s*\|\s*' + esc + r'\s*\|\s*([\d.]+)\s*\|\s*\$?([\d.]+)',
            lines[i]
        )
        if m:
            return float(m.group(2))
    # 方法4：Executor信号格式 — 买入: [SYM$amt, ...]
    # 新A4 Blade节点格式，A3买入评估段
    for i in range(len(lines) - 1, -1, -1):
        esc = re.escape(symbol)
        # 匹配 买入: [NEAR$25, WIF$25, EIGEN$25]
        m = re.search(r'买入\s*:\s*\[(?:[^\]]*?)' + esc + r'\$(\d+\.?\d*)(?:[^\]]*?)\]', lines[i])
        if m:
            buy_amt = float(m.group(1))
            # 搜索同节点卖出信号的反推买入价
            # 格式: 卖出: [EIGEN104.4151, ...]
            for j in range(max(0, i-3), min(len(lines), i+5)):
                sm = re.search(r'卖出\s*:\s*\[.*?' + esc + r'(\d+\.?\d*).*?\]', lines[j])
                if sm:
                    sell_qty = float(sm.group(1))
                    if sell_qty > 0:
                        return round(buy_amt / sell_qty, 8)
            # 无卖出信号时保留None，让调用方处理
            break
    return None


def run_position_evaluation(sell_signals):
    """持仓评估主函数 — 收集止盈/止损卖出信号，不直接执行"""
    # ─── BTC市况门检查（2026-07-09 新增）───
    # 当BTC跌超阈值时，自动触发防御/撤退模式
    btc_chg, btc_mode = get_btc_24h_change()
    is_defensive = (btc_mode != "normal")
    is_retreat = (btc_mode == "retreat")

    positions, usdt = fetch_positions()
    if positions is None:
        log(f"⚠️ 持仓查询失败: {usdt}", PATHS["log"])
        return [], usdt

    if not positions:
        log("无持仓", PATHS["log"])
        return [], usdt

    meaningful = [p for p in positions if float(p.get("free", 0)) >= 0.01]
    if not ALTCOIN_ENGINE_ENABLED:
        # 主策略trend_bot全仓持有ETH → 排除ETH，避免集中度>50%规则误触发真实卖单
        meaningful = [p for p in meaningful if p["asset"].upper() != "ETH"]
    trades_text = read_file(PATHS["trades"])
    known_symbols = set()
    if trades_text:
        for m in re.finditer(r'\|\s*币种\s*\|\s*(\w+)', trades_text):
            known_symbols.add(m.group(1).upper())

    known_positions = [p for p in meaningful if p["asset"].upper() in known_symbols]
    other_positions = [p for p in meaningful if p["asset"].upper() not in known_symbols]
    other_positions.sort(key=lambda p: float(p.get("free", 0)), reverse=True)
    meaningful = known_positions + other_positions
    meaningful = meaningful[:MAX_EVALUATE_POSITIONS]
    skipped = len(positions) - len(meaningful)
    log(f"持仓{len(positions)}个({skipped}个dust跳过), USDT=${usdt:.2f}", PATHS["log"])
    results = []

    for pos in meaningful:
        sym = pos["asset"]
        free = float(pos.get("free", 0))
        if free <= 0:
            continue

        price, _ = check_price_tool(sym)
        if price is None:
            log(f"⚠️ {sym}价格查询失败, 跳过评估", PATHS["log"])
            continue

        entry_price = get_entry_price_from_trades(sym)
        eval_result = evaluate_position(pos, price, entry_price)
        if not eval_result:
            continue

        results.append(eval_result)
        action = eval_result["action"]
        pnl = eval_result["pnl_pct"]
        value = eval_result["value"]

        # ─── 仓位集中度检查（2026-07-09 新增）───
        # 计算总持仓价值（含USDT）来判断集中度
        total_position_value = usdt + sum(r.get("value", 0) for r in results)
        if total_position_value > 0 and value / total_position_value * 100 > POSITION_CONCENTRATION:
            if action == "HOLD":
                action = "SELL_HALF"
                eval_result["action"] = "SELL_HALF"
                eval_result["reason"] = f"仓位集中度>50%: {value/total_position_value*100:.0f}% > {POSITION_CONCENTRATION:.0f}% → 减半"
                eval_result["concentration_forced"] = True
                log(f"  ⚠️ {sym}仓位集中{value/total_position_value*100:.0f}% > {POSITION_CONCENTRATION:.0f}% → 强制减半", PATHS["log"])

        # ─── BTC撤退模式：浮盈仓位优先释放USDT（2026-07-09 新增）───
        if is_retreat and pnl > 3 and action == "HOLD":
            action = "SELL_HALF"
            eval_result["action"] = "SELL_HALF"
            eval_result["reason"] = f"BTC撤退模式: +{pnl:.2f}%盈利仓减半释放USDT"
            log(f"  🔴 BTC撤退模式: {sym} PnL={pnl:+.2f}% → 强制减半释放USDT", PATHS["log"])
        elif is_defensive and pnl > 5 and action == "HOLD":
            action = "SELL_HALF"
            eval_result["action"] = "SELL_HALF"
            eval_result["reason"] = f"BTC防御模式: +{pnl:.2f}%盈利仓减半"
            log(f"  🟡 BTC防御模式: {sym} PnL={pnl:+.2f}% → 减半", PATHS["log"])

        if action == "HOLD":
            log(f"  {sym} PnL={pnl:+.2f}% → HOLD", PATHS["log"])
        else:
            # 🔴 重复信号去重：同一币种同一方向信号6小时内不重复发
            if is_sell_already_sent(sym, action):
                log(f"  ⏭ {sym} PnL={pnl:+.2f}% → {action}已发({SELL_DEDUP_HOURS}h内), 去重跳过", PATHS["log"])
                # 覆盖action为HOLD，阻止信号追加
                eval_result["action"] = "HOLD"
                continue
            qty = round(free / 2 if action == "SELL_HALF" else free, 4)
            # 🔴 MIN_NOTIONAL防护（2026-07-11 新增）：若卖出价值<$10，Binance会REJECT
            # 跳过信号生成并注册到去重表（短窗口），价格恢复后可重新评估
            sell_value = qty * price
            if sell_value < 10 and qty > 0 and action in ("SELL_ALL", "SELL_HALF"):
                log(f"  ⏭ {sym} 卖出价值=${sell_value:.2f}<$10(MIN_NOTIONAL), 跳过", PATHS["log"])
                # 注册到去重表（使用6小时窗口=SELL_DEDUP_HOURS），价格恢复后可重试
                tracker = load_sell_dedup()
                tracker[f"{sym}_{action}"] = (datetime.now(BJT) + timedelta(hours=SELL_DEDUP_HOURS)).isoformat()
                save_sell_dedup(tracker)
                continue
            sell_signals.append({
                "coin": sym,
                "quantity": qty,
                "reason": eval_result["reason"],
                "pnl_pct": pnl,
                "current_price": price,
            })
            log(f"  {'🟡' if action == 'SELL_HALF' else '🔴'} {sym} PnL={pnl:+.2f}% → 信号: {action} {qty}", PATHS["log"])

    # ─── FOMC宏观事件日现金储备检查（2026-06-17 新增）───
    # 当USDT<$5且持仓有浮盈>FOMC_PROFIT_TRIGGER%，预触发部分止盈
    if usdt < FOMC_MIN_BUFFER:
        is_macro_event_day = False
        today_str = datetime.now(BJT).strftime("%Y-%m-%d")
        # 可用简单检测：今天如果是星期三且市场缩量（FOMC特征），认定为FOMC日
        # 更精确的实现可用经济日历API，但先使用简单启发式
        # 2026年FOMC日期: 1/28, 3/18, 5/6, 6/17, 7/29, 9/16, 11/4, 12/16
        fomc_dates_2026 = ["2026-01-28", "2026-03-18", "2026-05-06", "2026-06-17",
                           "2026-07-29", "2026-09-16", "2026-11-04", "2026-12-16"]
        if today_str in fomc_dates_2026:
            is_macro_event_day = True

        if is_macro_event_day:
            # 找浮盈最大的持仓
            best_profit_pos = None
            for res in results:
                pnl = res.get("pnl_pct", 0)
                if pnl >= FOMC_PROFIT_TRIGGER:
                    if best_profit_pos is None or pnl > best_profit_pos["pnl_pct"]:
                        best_profit_pos = {"symbol": res["symbol"], "pnl_pct": pnl,
                                           "value": res.get("value", 0),
                                           "free": res.get("free", 0),
                                           "current_price": res.get("current_price", 0)}

            if best_profit_pos:
                # 计算25%卖出数量
                sell_qty = round(best_profit_pos["free"] * FOMC_SELL_RATIO, 4)
                sell_value = sell_qty * best_profit_pos["current_price"]
                sell_signals.append({
                    "coin": best_profit_pos["symbol"],
                    "quantity": sell_qty,
                    "reason": f"FOMC日预止盈(USDT=${usdt:.2f}<$5, 缓冲${sell_value:.2f})",
                    "pnl_pct": best_profit_pos["pnl_pct"],
                    "current_price": best_profit_pos["current_price"],
                })
                log(f"  📅 FOMC日现金储备: {best_profit_pos['symbol']} 卖{sell_qty}(~${sell_value:.2f}) 创造USDT缓冲",
                    PATHS["log"])
            else:
                log(f"  📅 FOMC日现金储备: 无浮盈>={FOMC_PROFIT_TRIGGER}%持仓，跳过", PATHS["log"])

    # ─── 币种事件日保护（2026-08-24 新增）───
    # 持仓币种24h内有重大事件(ETF上市/大额解锁)且事件已部分定价(24h涨幅≥5%)且浮盈>0
    # → 减仓50%落袋，防sell-the-news。先例: BTC现货ETF 2024-01-10上市后~21%回撤。
    # 与FOMC协议(2026-06-17)同哲学：事件风险对冲，非固定止盈。
    # 事件日当天或前一天触发；事件后自动失效。
    try:
        COIN_EVENT_DATES = {
            "2026-08-25": ["ZEC"],   # Grayscale ZEC ETF 上市
        }
        COIN_EVENT_CHG_TRIGGER = 5.0  # 24h涨幅≥5%视为事件已定价
        today_d = datetime.now(BJT).date()
        event_coins = set()
        for ev_date, coins in COIN_EVENT_DATES.items():
            ev_d = datetime.strptime(ev_date, "%Y-%m-%d").date()
            if (ev_d - today_d).days in (0, 1):
                event_coins.update(coins)
        if event_coins:
            for res in results:
                sym = res.get("symbol", "")
                if sym not in event_coins:
                    continue
                if res.get("pnl_pct", 0) <= 0:
                    continue
                chg24 = 0.0
                pullback_pct = 0.0
                try:
                    r = subprocess.run(
                        ['curl', '--socks5-hostname', '127.0.0.1:1080', '-s', '--max-time', '10',
                         f'https://api.binance.com/api/v3/ticker/24hr?symbol={sym}USDT'],
                        capture_output=True, text=True, timeout=12)
                    if r.returncode == 0 and r.stdout.strip():
                        t24 = json.loads(r.stdout)
                        chg24 = float(t24.get("priceChangePercent", 0))
                        h24 = float(t24.get("highPrice", 0))
                        l24 = float(t24.get("lastPrice", 0))
                        if h24 > 0:
                            pullback_pct = (h24 - l24) / h24 * 100
                except Exception:
                    pass
                # 2026-08-25 ZH升级: 巨幅浮盈(>100%)事件币，24h转跌或距24h高点回撤≥3%即减半
                # 原条件"24h涨≥5%"有盲区: 事件定价后24h转跌(-1%)但距24h高点回撤4.5%(ZEC ETF上市日实案)，
                # 巨幅浮盈币(BTC ETF 2024-01先例-21%回撤)需在回撤时锁盈而非等24h重新转涨。
                # ZEC 08-25实况: avg$843.26现$832(浮盈-1.3%无盈利可锁) → 规则不触发, 正确行为=硬止损$801
                pnl_pct = res.get("pnl_pct", 0)
                big_profit = pnl_pct > 100.0
                trigger = (chg24 >= COIN_EVENT_CHG_TRIGGER) or (big_profit and (chg24 < 0 or pullback_pct >= 3.0))
                if trigger:
                    qty = round(res.get("free", 0) / 2, 4)
                    ev_label = [d for d, cs in COIN_EVENT_DATES.items() if sym in cs][0]
                    sell_value = qty * res.get("current_price", 0)
                    trig_desc = f"24h涨{chg24:.1f}%已定价" if chg24 >= COIN_EVENT_CHG_TRIGGER else f"巨幅浮盈+{pnl_pct:.0f}%回撤{pullback_pct:.1f}%"
                    if sell_value >= 10:  # MIN_NOTIONAL防护
                        sell_signals.append({
                            "coin": sym,
                            "quantity": qty,
                            "reason": f"币种事件日保护: {sym}事件({ev_label})临近+{trig_desc}+浮盈{pnl_pct:.1f}% → 减半落袋",
                            "pnl_pct": pnl_pct,
                            "current_price": res.get("current_price", 0),
                        })
                        log(f"  📅 币种事件日保护: {sym} {trig_desc} 事件({ev_label}) → 卖{qty}(~${sell_value:.2f})", PATHS["log"])
                    else:
                        log(f"  📅 币种事件日保护: {sym} 卖出价值${sell_value:.2f}<$10 MIN_NOTIONAL, 跳过", PATHS["log"])
    except Exception as e:
        log(f"⚠️ 币种事件日检查失败: {e}", PATHS["log"])

    return results, usdt, btc_mode


# ═══════════════════════════════════════════════
# 第二步：A3买入评估
# ═══════════════════════════════════════════════

def parse_a3_report(text):
    """从A3报告解析候选币列表——支持多币表格格式和精选格式"""
    if not text:
        return None

    result = {}
    lines = text.split("\n")

    # 策略1: 解析"高置信度候选"表格（最新A3格式）
    coins = []
    in_high_conf = False
    in_medium_conf = False
    for i, line in enumerate(lines):
        if "高置信度候选" in line or "候选币逐一分析" in line:
            in_high_conf = True
            in_medium_conf = False
            continue
        if "中等置信度候选" in line or "待观察" in line:
            in_high_conf = False
            in_medium_conf = True
            continue
        if in_high_conf and line.strip().startswith("| **"):
            m = re.match(r'\|\s*\*\*(\w+)\*\*', line)
            if m:
                coins.append(m.group(1))
        if in_medium_conf and line.strip().startswith("| **"):
            m = re.match(r'\|\s*\*\*(\w+)\*\*', line)
            if m:
                coins.append(m.group(1))
        if line.startswith("## ") and ("置信度" not in line):
            in_high_conf = False
            in_medium_conf = False

    if coins:
        result["coins"] = coins
        result["is_multi"] = True
        return result

    # 策略2: 解析通用表格（| 币种 | ... | 格式）
    coins = []
    in_table = False
    for line in lines:
        if "| 币种" in line and ("| 判定" in line or "| 类型" in line or "| 赛道" in line):
            in_table = True
            continue
        if in_table and "|:----" in line:
            continue
        if in_table and line.strip().startswith("|"):
            m = re.search(r'\|\s*\*+\s*(\w+)\s*\*+\s*\|', line)
            if m:
                coins.append(m.group(1))
        if in_table and not line.strip().startswith("|"):
            break

    if coins:
        result["coins"] = coins
        result["is_multi"] = True
        return result

    # 策略3: 单币精选格式（旧）
    m = re.search(r'\*\*选中币种[：:]\s*\*\*(\w+)', text) or \
        re.search(r'🏆\s*今日精选.*?\*\*(\w+)\*\*', text)
    if m:
        result["coin"] = m.group(1)
        result["is_multi"] = False
        prices = {"建仓价": None, "加仓价": None, "止损价": None, "止盈价": None}
        for key in prices:
            pm = re.search(rf'{key}\s*[|]\s*\$?([\d.]+)', text)
            if pm: prices[key] = float(pm.group(1))
        result["prices"] = prices
        cm = re.search(r'置信度\s*[|]\s*(\d+)/10', text)
        if cm: result["confidence"] = int(cm.group(1))
        return result

    # 策略4: 从"优先级排序"的表格找第一个推荐
    m = re.search(r'第1优先[—\-–]+\s*\*{0,2}(\w+)', text)
    if m:
        result["coin"] = m.group(1)
        result["is_multi"] = False
        prices = {"建仓价": None, "加仓价": None, "止损价": None, "止盈价": None}
        for key in prices:
            pm = re.search(rf'{key}\s*[|]\s*\$?([\d.]+)', text)
            if pm: prices[key] = float(pm.group(1))
        result["prices"] = prices
        return result

    return None


def check_fk():
    """检查FK风控"""
    content = read_file(PATHS["fk_veto"])
    if not content:
        return "通过", "FK文件不存在，视为通过"
    try:
        data = json.loads(content)
        if data.get("veto") is True:
            return "否决", f"FK否决: {data.get('reason', '无理由')}"
        return "通过", "veto=false"
    except:
        return "通过", "FK解析失败，视为通过"


def check_balance_tool():
    """查USDT余额"""
    result = ssh_run(f"python3 {AWS_EXECUTOR} --check")
    if not result:
        return 0, "SSH失败"
    try:
        assets = json.loads(result)
        for a in assets:
            if a["asset"] == "USDT":
                return float(a["free"]), "OK"
        return 0, "无USDT"
    except:
        return 0, f"解析失败: {result[:100]}"


def check_price_tool(coin):
    """查单个币种价格（SSH→SOCKS5本地兜底）"""
    result = ssh_run(f"python3 {AWS_EXECUTOR} --price {coin}")
    if result:
        m = re.search(r'[\d.]+', result.split("$")[-1] if "$" in result else result)
        if m:
            return float(m.group()), "OK"
    # SSH失败或解析失败 → SOCKS5本地兜底
    return _socks5_price_fallback(coin)


def _socks5_price_fallback(coin):
    """SOCKS5本地查价格（SSH不可用时兜底）"""
    try:
        r = subprocess.run(
            ['curl', '--socks5-hostname', '127.0.0.1:1080', '-s', '--max-time', '10',
             f'https://api.binance.com/api/v3/ticker/price?symbol={coin}USDT'],
            capture_output=True, text=True, timeout=12
        )
        if r.returncode == 0 and r.stdout.strip():
            data = json.loads(r.stdout)
            return float(data['price']), "SOCKS5"
    except:
        pass
    return None, "SOCKS5失败"


def format_entry(result):
    """输出TRADES.md格式"""
    ts = datetime.now(BJT).strftime("%Y-%m-%d %H:%M BJT")

    if result.get("mode") == "position_eval":
        return f"""### {ts} | 持仓评估
| 字段 | 值 |
|:-----|:---|
| 持仓数 | {result.get('position_count', 0)} |
| USDT | ${result.get('usdt', 0):.2f} |
| 操作 | {result.get('action_summary', '无')} |
| 详情 | {result.get('details', '-')} |
"""
    elif result.get("mode") == "signal_sent":
        return f"""### {ts} | 信号发送
| 字段 | 值 |
|:-----|:---|
| 信号ID | {result.get('signal_id', '-')} |
| 买入信号 | {result.get('buy_count', 0)}个 |
| 卖出信号 | {result.get('sell_count', 0)}个 |
| 详情 | {result.get('details', '-')} |
| 状态 | ✅ 已推送至AWS |
"""
    elif result.get("status") == "skip":
        return f"""### {ts} | 巡检
| 字段 | 值 |
|:-----|:---|
| 指令来源 | A3 牛币官 |
| 币种 | {result.get("coin", "-")} |
| 方向 | - |
| FK风控 | {result.get("fk_status", "?")} |
| 余额 | ${result.get("balance", 0):.2f} |
| 价格偏离 | {result.get("price_deviation", "?")} |
| 状态 | ⏳ 跳过 |
| 原因 | {result.get("reason", "无")} |
"""
    else:
        return f"""### {ts} | 执行
| 字段 | 值 |
|:-----|:---|
| 指令来源 | A3 牛币官 |
| 币种 | {result["coin"]} |
| 方向 | BUY |
| A3建仓价 | ${result.get("target_price", 0):.4f} |
| 执行价 | ${result.get("exec_price", 0):.4f} |
| 执行量 | ${result.get("amount", 0):.2f} USDT |
| FK风控 | {result.get("fk_status", "?")} |
| 余额 | ${result.get("balance", 0):.2f} |
| 状态 | ✅ 信号已推送 |
"""


def write_entry(result):
    """写TRADES.md"""
    entry = format_entry(result)
    try:
        with open(PATHS["trades"], "a") as f:
            f.write(entry + "\n")
    except:
        pass


# ═══════════════════════════════════════════════
# 信号文件管理
# ═══════════════════════════════════════════════

def write_signal_file(buy_signals, sell_signals, position_eval_result, usdt_balance):
    """写入信号文件"""
    seq = get_signal_sequence()
    now = datetime.now(BJT)
    signal_id = f"sig_{now.strftime('%Y%m%d_%H%M')}_{seq}"
    ts = now.strftime("%Y-%m-%d %H:%M BJT")
    
    # 检测跌幅榜崩盘波动（调用缓存，不重复拉API）
    crash_mode, crash_count, crash_max_drop, crash_coin = _detect_crash_wave()

    signal = {
        "signal_id": signal_id,
        "generated_at": now.isoformat(),
        "a4_cycle": ts,
        "sequence": seq,
        "buy_signals": buy_signals,
        "sell_signals": sell_signals,
        "position_eval": {
            "positions_count": position_eval_result.get("count", 0) if position_eval_result else 0,
            "usdt_balance": usdt_balance,
            "action_summary": position_eval_result.get("summary", "无") if position_eval_result else "无",
        },
        "tags_context": {
            # 传递标签上下文给AWS执行层
            "a3_report_date": now.strftime("%Y-%m-%d"),
        },
        "market_context": {
            # 跌幅榜崩盘波动检测（2026-07-27 ZH追加）
            "crash_detected": crash_mode == "crash",
            "crash_count": crash_count,
            "crash_max_drop": crash_max_drop,
            "crash_worst_coin": crash_coin,
            "detected_at": now.isoformat(),
        },
    }

    # 写入本地信号文件
    os.makedirs(os.path.dirname(SIGNAL_PATH), exist_ok=True)
    with open(SIGNAL_PATH, "w") as f:
        json.dump(signal, f, indent=2, default=str)
    log(f"📝 信号文件已写入: {signal_id}", PATHS["log"])

    return signal_id, SIGNAL_PATH


def scp_signal_to_aws():
    """SCP信号文件到AWS"""
    try:
        r = subprocess.run(
            f'scp -i ~/.zq_vault/web4.0.pem -o StrictHostKeyChecking=no -o ConnectTimeout=10 {SIGNAL_PATH} ubuntu@15.134.211.154:{AWS_SIGNAL_PATH}',
            shell=True, capture_output=True, text=True, timeout=15
        )
        if r.returncode == 0:
            log(f"📤 信号已推送至AWS", PATHS["log"])
            return True
        else:
            log(f"⚠️ SCP失败: {r.stderr.strip()[:100]}", PATHS["log"])
            return False
    except Exception as e:
        log(f"⚠️ SCP异常: {e}", PATHS["log"])
        return False


def pull_results_from_aws():
    """从AWS拉回执行结果"""
    try:
        r = subprocess.run(
            f'scp -i ~/.zq_vault/web4.0.pem -o StrictHostKeyChecking=no -o ConnectTimeout=10 ubuntu@15.134.211.154:{AWS_RESULT_PATH} {RESULT_PATH}',
            shell=True, capture_output=True, text=True, timeout=15
        )
        if r.returncode == 0:
            try:
                with open(RESULT_PATH) as f:
                    results = json.load(f)
                log(f"📥 AWS执行结果已拉回: {results.get('status', '?')}", PATHS["log"])
                return results
            except:
                return None
        return None
    except:
        return None


# ═══════════════════════════════════════════════
# ②-a 主策略：profit_engine_v2（2026-08-31 重写）
# ═══════════════════════════════════════════════

def engine_v2_buys():
    """运行 profit_engine_v2 live 并解析买入候选。
    引擎内部自带：BTC市况门 / EMA50趋势 / RSI回撤 / 突破前高确认 /
    硬止损-5% / 止盈+8% / 时间止损48h / 连亏冷却48h / 风险预算1%权益。
    任何异常/超时/市况门不通过 → 返回[]（A3兜底保持可用）。
    """
    ev2 = os.path.join(ZQ_ROOT, "tools", "profit_engine_v2.py")
    out = os.path.join(ZQ_ROOT, "data", "signals", "engine_v2_buys.json")
    try:
        r = subprocess.run(
            [sys.executable, ev2, "live", "--days", "3", "--top", "30", "--out", out],
            capture_output=True, text=True, timeout=180, cwd=ZQ_ROOT)
    except Exception as e:
        log(f"⚠️ engine_v2执行异常: {e}", PATHS["log"])
        return []
    if r.returncode != 0:
        log(f"⚠️ engine_v2异常退出: {(r.stderr or r.stdout)[-200:]}", PATHS["log"])
        return []
    try:
        with open(out) as f:
            doc = json.load(f)
    except Exception:
        log("⚠️ engine_v2输出解析失败", PATHS["log"])
        return []
    if doc.get("regime") != "LONG":
        log(f"⏭ engine_v2市况门={doc.get('regime')} (BTC 24h {doc.get('btc_24h_chg')}%) — 无买入", PATHS["log"])
        return []
    buys = doc.get("buy_signals", [])
    log(f"🎯 engine_v2: 市况LONG, {len(buys)}个买入候选", PATHS["log"])
    return buys


# ═══════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════

def main():
    log("⚡ A4 v3.0 信号节点启动（A4只做信号判断，AWS独立执行）")

    # 0. 检查紧急停止
    if os.path.exists(PATHS["stop"]):
        log("ZH紧急停止中，跳过所有执行", PATHS["log"])
        return {"status": "skip", "reason": "ZH紧急停止"}

    # 初始化信号收集
    buy_signals = []
    sell_signals = []

    # ═══ ① 持仓评估（每轮必做）═══
    log("── ① 持仓评估 ──")
    eval_results, usdt_balance, btc_mode = run_position_evaluation(sell_signals)

    action_summary = "无操作"
    if eval_results:
        actions = [r["action"] for r in eval_results]
        sells = [a for a in actions if a != "HOLD"]
        if sells:
            action_summary = f"止盈/止损: {len(sells)}笔信号"
        position_eval_result = {
            "count": len(eval_results),
            "summary": action_summary,
        }
        write_entry({
            "mode": "position_eval",
            "position_count": len(eval_results),
            "usdt": usdt_balance,
            "action_summary": action_summary,
            "details": "; ".join(
                f"{r['symbol']} {r['action']} (PnL={r['pnl_pct']:+.2f}%)"
                for r in eval_results if r["action"] != "HOLD"
            )
        })
    else:
        position_eval_result = {"count": 0, "summary": "无持仓"}

    # ═══ 🔵 小账户模式: 动态调整MIN_BUY_USDT_ON_AWS ═══
    # 当总权益<$50时，降低最小买入金额以突破MIN_NOTIONAL锁死
    # 🔴 2026-08-03 fix: 总权益必须含locked USDT（grid_bot锁在ETH买单里的$141）
    #    否则A4幻觉"总资$9"→错误触发小账户模式（真实总资≈$220）
    usdt_free2, usdt_locked = get_usdt_total()
    usdt_total = usdt_balance + (usdt_locked or 0)
    if usdt_free2 is not None and usdt_locked is not None and usdt_free2 != usdt_balance:
        usdt_total = usdt_free2 + usdt_locked
    estimated_total = usdt_total + sum(
        float(p.get("value", 0)) for p in (eval_results or []) if isinstance(p, dict)
    ) if eval_results else usdt_total
    global MIN_BUY_USDT_ON_AWS
    if estimated_total < SMALL_ACCOUNT_THRESHOLD:
        old_min = MIN_BUY_USDT_ON_AWS
        MIN_BUY_USDT_ON_AWS = max(SMALL_ACCOUNT_MIN_BUY, usdt_balance * 0.3)
        MIN_BUY_USDT_ON_AWS = round(min(MIN_BUY_USDT_ON_AWS, usdt_balance * 0.5), 0)
        # 🔴 2026-07-16 fix: 小账户MIN_BUY不能低于AWS最小执行额$5
        MIN_BUY_USDT_ON_AWS = max(MIN_BUY_USDT_ON_AWS, 5)
        if MIN_BUY_USDT_ON_AWS != old_min:
            log(f"🔵 小账户模式激活: MIN_BUY从${old_min}降至${MIN_BUY_USDT_ON_AWS:.0f} (总资${estimated_total:.0f})", PATHS["log"])
    elif MIN_BUY_USDT_ON_AWS < 25:
        MIN_BUY_USDT_ON_AWS = 25
        log("🟢 恢复标准MIN_BUY=$25", PATHS["log"])
    if usdt_locked:
        log(f"💰 总权益≈${estimated_total:.0f} (USDT自由${usdt_balance:.2f}+锁定${usdt_locked:.2f}+持仓${estimated_total-usdt_total:.2f})", PATHS["log"])

    # ═══ BTC市况门：防御模式不产生新买入信号（2026-07-09 新增）═══
    if btc_mode == "retreat":
        log(f"🔴 BTC撤退模式({BTC_AGGRESSIVE_THRESHOLD}%): 跳过所有买入信号，优先保护资金")
        a3 = None  # 跳过A3买入评估
    elif btc_mode == "defensive":
        log(f"🟡 BTC防御模式({BTC_DEFENSIVE_THRESHOLD}%): 买入减半")
        # 防御模式下继续但降低买入金额
        MIN_BUY_USDT_ON_AWS = min(MIN_BUY_USDT_ON_AWS, max(8, usdt_balance * 0.15))

    # ═══ 🔴 USDT紧急阈值: 资金枯竭时禁止新买入，强制回收 ═══
    # 2026-07-13 新增：USDT<$10时任何买入都是尘(赚不到手续费)，必须优先回收资金
    usdt_critical = usdt_balance < USDT_CRITICAL_THRESHOLD
    if usdt_critical:
        log(f"🔴 USDT紧急阈值: ${usdt_balance:.2f}<${USDT_CRITICAL_THRESHOLD} — 禁止新买入，强制回收资金", PATHS["log"])
        # 保留持仓止盈/止损信号（sell_signals），但清空已产生的买入信号
        buy_signals = []

    # ═══ 🛡️ 网格资金保留: ETH网格独占USDT（NAVIGATION.md §二），free<$30禁止A4新买入 ═══
    if usdt_balance < GRID_USDT_RESERVE:
        log(f"🛡️ 网格资金保留: free=${usdt_balance:.2f}<${GRID_USDT_RESERVE} — 禁止A4新买入, USDT留给ETH网格", PATHS["log"])
        buy_signals = []

    # ═══ 🔴 USDT紧急回收割: 资金枯竭持续>3周期 → 强制卖最差持仓 ═══
    # 当USDT<$20且持续多周期无改善时，主动卖持仓回收资金
    if usdt_balance > 0 and usdt_balance < USDT_EMERGENCY_THRESHOLD and not usdt_critical:
        # 检查是否连续多周期都处于低资金状态
        emergency_file = f"{ZQ_ROOT}/data/signals/.usdt_emergency_counter"
        try:
            emergency_count = 0
            if os.path.exists(emergency_file):
                with open(emergency_file) as f:
                    emergency_count = int(f.read().strip())
            emergency_count += 1
            with open(emergency_file, "w") as f:
                f.write(str(emergency_count))
        except:
            emergency_count = 0
        
        if emergency_count >= 3 and eval_results:
            # 找最差持仓（浮亏最大的非HOLD仓位）
            emerg_sell_candidates = [
                r for r in eval_results if isinstance(r, dict) 
                and r.get("action") in ("HOLD",) and r.get("pnl_pct", 0) < -1
                and r.get("value", 0) > 2  # 只卖有回收价值的
            ]
            if emerg_sell_candidates:
                worst = min(emerg_sell_candidates, key=lambda r: r.get("pnl_pct", 0))
                emerg_qty = worst.get("free", worst.get("qty", 0)) * 1.0  # 全仓卖出
                if emerg_qty > 0:
                    log(f"🔴 USDT紧急回收割: force-sell {worst['symbol']}(PnL={worst['pnl_pct']:+.2f}%) 回收${worst.get('value',0):.1f}", PATHS["log"])
                    sell_signals.append({
                        "coin": worst["symbol"],
                        "quantity": emerg_qty,
                        "reason": f"USDT紧急回收割: {worst['symbol']}(P&L{worst['pnl_pct']:+.2f}%) USDT长期<${USDT_EMERGENCY_THRESHOLD}",
                        "pnl_pct": worst["pnl_pct"],
                        "current_price": worst.get("current_price", 0),
                    })
                    # 重置计数器
                    try:
                        with open(emergency_file, "w") as f:
                            f.write("0")
                    except:
                        pass

    # ═══ ② A3买入评估 ═══
    # ②-a 主策略：profit_engine_v2（2026-08-31 重写，回测60天+11.44%/胜率53.7%）
    # 只有engine_v2无信号时才走A3兜底——旧链路14层过滤+反复接飞刀是亏损根因
    log("── ② 买入评估（engine_v2主策略 + A3兜底）──")
    a3 = None
    if not ALTCOIN_ENGINE_ENABLED:
        log("⏸ A4山寨引擎暂停: ALTCOIN_ENGINE_ENABLED=False（主策略=trend_bot全仓ETH/现金，无中间状态）", PATHS["log"])
    elif usdt_balance >= MIN_BUY_USDT_ON_AWS:
        engine_buys = engine_v2_buys()
        for b in engine_buys:
            if usdt_balance < MIN_BUY_USDT_ON_AWS:
                log(f"  余额不足 ${usdt_balance:.2f} < MIN_BUY ${MIN_BUY_USDT_ON_AWS:.0f}，停止engine_v2买入", PATHS["log"])
                break
            buy_signals.append({
                "coin": b["coin"],
                "usdt_amount": b["usdt_amount"],
                "confidence": b.get("confidence", 7),
                "tags": b.get("tags", ["engine_v2"]),
                "a3_recommend_price": b.get("a3_recommend_price"),
                "entry_reason": b.get("entry_reason", "engine_v2主策略"),
            })
            usdt_balance -= b["usdt_amount"]
        if engine_buys:
            log(f"🎯 engine_v2主策略: {len(engine_buys)}个候选, 通过资金门槛{len(buy_signals)}个", PATHS["log"])
    else:
        log(f"  余额${usdt_balance:.2f}<MIN_BUY${MIN_BUY_USDT_ON_AWS:.0f}, 跳过engine_v2扫描", PATHS["log"])
    if not buy_signals:
        a3_text = read_file(PATHS["a3_report"])
        a3 = parse_a3_report(a3_text)

    if a3:
        if a3.get("is_multi") and a3.get("coins"):
            coins = a3["coins"]
            log(f"A3推荐{len(coins)}个币: {', '.join(coins[:5])}...", PATHS["log"])
            
            # 🔴 跌幅榜崩盘波动检测（2026-07-27 ZH追加）
            crash_mode, crash_count, crash_max_drop, crash_coin = _detect_crash_wave()
            if crash_mode == "crash":
                crash_confidence = max(5, 7 - 2)  # 崩盘波动降2分置信度
                crash_buy_mult = 0.6  # 崩盘波动买入金额缩减40%
                log(f"🔴 跌幅榜崩盘波动: {crash_count}个币跌>{crash_max_drop:.0f}%({crash_coin}) — 买入置信度降至{crash_confidence}，金额缩减40%", PATHS["log"])
            else:
                crash_confidence = 7
                crash_buy_mult = 1.0
            
            for coin in coins:
                # 🔴 连损黑名单检查（2026-07-17 ZH追加）：连损币48h内禁止买入
                loss_bl = _load_loss_blacklist()
                if coin.upper() in loss_bl:
                    entry_data = loss_bl[coin.upper()]
                    flag = entry_data.get('flag', '连损黑名单')
                    log(f"  🔴 {coin} 被连损黑名单拦截: {flag}", PATHS["log"])
                    continue
                if usdt_balance < MIN_USDT:
                    log(f"  余额不足，跳过{coin}", PATHS["log"])
                    break
                price, price_msg = check_price_tool(coin)
                if price:
                    # 崩盘波动时缩减买入金额
                    buy_amount = max(MIN_BUY_USDT_ON_AWS * crash_buy_mult, 5)
                    buy_amount = round(buy_amount, 0)
                    tags = ["A3多币推荐"]
                    if crash_mode == "crash":
                        tags.append("崩盘波动")
                    log(f"  {coin}当前价: ${price:.4f} → 产生买入信号 ${buy_amount:.0f} (置信度{crash_confidence})")
                    buy_signals.append({
                        "coin": coin.upper(),
                        "usdt_amount": buy_amount,
                        "confidence": crash_confidence,
                        "tags": tags,
                        "a3_recommend_price": price,
                        "entry_reason": "A3推荐·多币模式" + ("·崩盘保守" if crash_mode == "crash" else ""),
                    })
                    usdt_balance -= buy_amount
                else:
                    log(f"  ❌ {coin} 无价格: {price_msg}")
                if usdt_balance < MIN_BUY_USDT_ON_AWS:
                    break
        else:
            coin = a3.get("coin")
            entry = a3.get("prices", {}).get("建仓价")
            stop = a3.get("prices", {}).get("止损价")
            take = a3.get("prices", {}).get("止盈价")
            log(f"A3推荐: {coin}, 建仓${entry}", PATHS["log"])

            no_entry = all(v is None for v in a3["prices"].values()) if a3.get("prices") else True
            if no_entry or not entry:
                log(f"A3推荐{coin}但四档价格不完整", PATHS["log"])
            else:
                result = {
                    "coin": coin,
                    "target_price": entry,
                    "status": "skip",
                    "balance": usdt_balance,
                }
                fk_status, fk_reason = check_fk()
                result["fk_status"] = fk_status
                if fk_status != "否决":
                    if usdt_balance >= MIN_BUY_USDT_ON_AWS:
                        price, price_msg = check_price_tool(coin)
                        if price:
                            log(f"✅ {coin}当前价: ${price:.4f}")
                            lower = entry * (1 - PRICE_DEVIATION_PCT / 100)
                            upper = entry * (1 + PRICE_DEVIATION_PCT / 100)
                            deviation = (price - entry) / entry * 100
                            result["price_deviation"] = f"{deviation:+.2f}%"
                            if lower <= price <= upper:
                                log(f"🟢 四查通过，产生买入信号 {coin} ${MIN_BUY_USDT_ON_AWS}")
                                buy_signals.append({
                                    "coin": coin.upper(),
                                    "usdt_amount": MIN_BUY_USDT_ON_AWS,
                                    "confidence": a3.get("confidence", 7),
                                    "tags": ["A3精选推荐"],
                                    "a3_recommend_price": entry,
                                    "entry_reason": f"A3精选·建仓价${entry}·置信度{a3.get('confidence', '?')}/10",
                                    "stop_loss": stop,
                                    "take_profit": take,
                                })
                                result["status"] = "signal_generated"
                                result["exec_price"] = price
                                result["amount"] = MIN_BUY_USDT_ON_AWS
                                log(f"✅ 信号已产生! 币种{coin} 金额${MIN_BUY_USDT_ON_AWS} 当前价${price:.4f}")
                            else:
                                log(f"❌ 价格偏离 {deviation:+.2f}%")
                                result["reason"] = f"价格偏离{deviation:+.2f}%"
                            write_entry(result)
                        else:
                            log(f"❌ API不通: {price_msg}")
                            result["reason"] = f"API不通: {price_msg}"
                            write_entry(result)
                    else:
                        log(f"❌ 余额不足: ${usdt_balance:.2f}")
                else:
                    log(f"❌ FK否决: {fk_reason}")
                    result["reason"] = f"FK否决: {fk_reason}"
                    write_entry(result)
    else:
        log("A3今日无推荐 — A4等待A3推荐", PATHS["log"])
        # ═══ ③-b 加仓fallback: USDT闲置>50%时加好仓 ═══
        # 铁律3（NAVIGATION.md §六）：USDT>20%闲置→无候选→加好仓
        estimated_total = usdt_balance + sum(
            float(p.get("value", 0)) for p in eval_results if isinstance(p, dict)
        ) if eval_results else usdt_balance * 3
        usdt_ratio = usdt_balance / max(estimated_total, 1)
        if not buy_signals and usdt_ratio > 0.50 and not sell_signals and eval_results:
            # 找浮盈最大+BULLISH信号的仓位
            best_add = None
            for res in eval_results:
                pnl = res.get("pnl_pct", 0)
                if pnl > 0 and action_summary == "无操作":
                    if best_add is None or pnl > best_add.get("pnl_pct", -999):
                        best_add = res
            if best_add and best_add.get("pnl_pct", 0) > 0:
                symbol = best_add["symbol"]
                add_amount = min(usdt_balance * 0.10, usdt_balance - 5)
                if add_amount >= 10:
                    log(f"  📌 铁律3激活: {symbol} 加仓${add_amount:.1f} (USDT闲置{usdt_ratio*100:.0f}%>50%)", PATHS["log"])
                    buy_signals.append({
                        "coin": symbol.upper(),
                        "usdt_amount": round(add_amount, 0),
                        "confidence": 6,
                        "tags": ["加仓", "铁律3-USDT闲置部署"],
                        "a3_recommend_price": None,
                        "entry_reason": f"铁律3加仓: {symbol}浮盈+{best_add['pnl_pct']:.2f}%+BULLISH, USDT闲置{usdt_ratio*100:.0f}%",
                    })
                    usdt_balance -= add_amount

    # ═══ ②-b 主动轮换: F&G<20 + USDT闲置>50% + 持仓全亏 + 有A3高置信候选 ═══
    # 当系统满仓但所有持仓浮亏,USDT闲置>50%时，轮换最差持仓到最佳候选
    if not sell_signals and usdt_balance > 100 and a3 and a3.get("coins"):
        # 检查是否有浮亏>=-2%的持仓
        weak_positions = [r for r in (eval_results or []) if isinstance(r, dict) and r.get("pnl_pct", 0) <= -2]
        # 检查A3候选中有没有当前未持有的高置信币
        current_symbols = set(r.get("symbol","") for r in (eval_results or []) if isinstance(r, dict))
        fresh_candidates = [c for c in a3.get("coins",[]) if c.upper() not in current_symbols]
        if weak_positions and fresh_candidates:
            worst = min(weak_positions, key=lambda r: r.get("pnl_pct", 0))
            log(f"  🔄 主动轮换: {worst['symbol']}(PnL={worst['pnl_pct']:+.2f}%) → {fresh_candidates[0]} (USDT闲置{usdt_balance:.0f})", PATHS["log"])
            sell_signals.append({
                "coin": worst["symbol"],
                "quantity": worst.get("free", 0) * 0.5,  # 先轮换50%
                "reason": f"主动轮换出{worst['symbol']} PnL={worst['pnl_pct']:+.2f}% → {fresh_candidates[0]} (F&G<20轮换优化)",
                "pnl_pct": worst["pnl_pct"],
                "current_price": worst.get("current_price", 0),
            })
            # 为最佳候选产生买入信号
            price, _ = check_price_tool(fresh_candidates[0])
            if price:
                buy_signals.append({
                    "coin": fresh_candidates[0].upper(),
                    "usdt_amount": MIN_BUY_USDT_ON_AWS,
                    "confidence": 8,
                    "tags": ["A3高置信", "主动轮换"],
                    "a3_recommend_price": price,
                    "entry_reason": f"主动轮换: 出{worst['symbol']}(P&L{worst['pnl_pct']:+.2f}%)→入{fresh_candidates[0]}, F&G<20优化",
                })
                usdt_balance -= MIN_BUY_USDT_ON_AWS

    # ═══ ②-c FALLBACK: A3无推荐 + USDT闲置>50% → 从fast_scan取最佳候选 ═══
    # 系统闲置但又无可加仓盈利仓位时，直接从fast_scan的高置信候选买入
    # 🔴 2026-07-16 修复v2: 双保护 — eval_results必须有真实估值 + USDT余额>=真有意义
    # 之前: 仅eval_results guard。但API超时时价格=0→估值=0→estimated_total≈USDT余额→
    # ratio虚高68%→FALLBACK仍产生废单($3>$2.37不可执行)。加USDT>=10硬门槛。
    if not buy_signals and not sell_signals:
        usdt_ratio_after = usdt_balance / max(estimated_total, 1)
        if usdt_ratio_after > 0.50 and usdt_balance >= MIN_BUY_USDT_ON_AWS \
           and usdt_balance >= 10:  # 必须有真实闲置资金才能FALLBACK买入
            # 🔴 2026-08-02 ZH追加: 崩盘模式下禁止FALLBACK买入
            # 背景: 07-27崩盘检测只作用于A3推荐路径(line 1005-1013),
            # FALLBACK路径无保护 → 08-02崩盘日(16币跌>30%, NFP -66%)
            # 仍FALLBACK买入RIF=用旧数据接刀
            crash_mode, crash_count, crash_max_drop, crash_coin = _detect_crash_wave()
            if crash_mode == "crash":
                log(f"🔴 崩盘模式({crash_count}币跌>{crash_max_drop:.0f}%): 禁止FALLBACK买入", PATHS["log"])
                return
            fast_scan_path = f"{ZQ_ROOT}/data/fast_scan_candidates.json"
            if os.path.exists(fast_scan_path):
                # 🔴 2026-08-02 ZH追加: fast_scan数据过期>48h禁止FALLBACK买入
                # 背景: 08-02实测fast_scan_candidates.json为07-25数据(过期8天),
                # FALLBACK仍取high_candidates[0]买入RIF — 用过期候选接刀
                fs_age_h = (time.time() - os.path.getmtime(fast_scan_path)) / 3600
                if fs_age_h > 48:
                    log(f"🔴 fast_scan数据过期{fs_age_h:.0f}h(>{48}h): 禁止FALLBACK买入", PATHS["log"])
                    return
                try:
                    with open(fast_scan_path) as f:
                        fs = json.load(f)
                    high_candidates = [c for c in fs.get("candidates", []) 
                                      if c.get("confidence") in ("超高", "高")]
                    if high_candidates:
                        # 🔴 黑名单过滤：FALLBACK也不能买入黑名单币
                        loss_bl = _load_loss_blacklist()
                        filtered = []
                        for c in high_candidates:
                            s = c.get("symbol", "").replace("USDT", "").upper()
                            if s in loss_bl:
                                flag = loss_bl[s].get('flag', '连损黑名单')
                                log(f"  🔴 FALLBACK跳过黑名单币 {s}: {flag}", PATHS["log"])
                                continue
                            filtered.append(c)
                        high_candidates = filtered
                        if not high_candidates:
                            log(f"  ❌ FALLBACK无候选: 全部被黑名单过滤", PATHS["log"])
                            return
                        target = high_candidates[0]
                        sym = target.get("symbol", "").replace("USDT", "")
                        amount = MIN_BUY_USDT_ON_AWS
                        log(f"  📌 FALLBACK: 从fast_scan取{target['confidence']}候选 {sym}  ${amount:.0f} (USDT闲置{usdt_ratio_after*100:.0f}%)", PATHS["log"])
                        buy_signals.append({
                            "coin": sym.upper(),
                            "usdt_amount": amount,
                            "confidence": 7,
                            "tags": ["FALLBACK", "fast_scan-闲置部署"],
                            "a3_recommend_price": target.get("price"),
                            "entry_reason": f"FALLBACK买入: {sym}({target.get('total_score','?')}pts) USDT闲置{usdt_ratio_after*100:.0f}%部署",
                        })
                        usdt_balance -= amount
                except Exception as e:
                    log(f"  ❌ fast_scan fallback失败: {e}", PATHS["log"])

    # ═══ ③ 产生信号文件 → SCP到AWS ═══
    log("── ③ 产生信号并推送AWS ──")
    if buy_signals or sell_signals:
        signal_id, signal_path = write_signal_file(buy_signals, sell_signals, position_eval_result, usdt_balance)

        # 记录信号详情到TRADES.md
        buy_details = ", ".join(f"{b['coin']}${b['usdt_amount']}" for b in buy_signals)
        sell_details = ", ".join(f"{s['coin']}{s['quantity']}" for s in sell_signals)
        write_entry({
            "mode": "signal_sent",
            "signal_id": signal_id,
            "buy_count": len(buy_signals),
            "sell_count": len(sell_signals),
            "details": f"买入: [{buy_details}] 卖出: [{sell_details}]",
        })

        # SCP到AWS
        scp_ok = scp_signal_to_aws()
        if scp_ok:
            log(f"✅ 信号{signal_id}已推送至AWS，等待独立执行", PATHS["log"])

        # 拉回上次执行结果
        previous_results = pull_results_from_aws()
        if previous_results:
            exec_summary = previous_results.get("summary", {})
            log(f"📋 上次执行结果: 成交{exec_summary.get('filled', 0)}/失败{exec_summary.get('failed', 0)}", PATHS["log"])
    else:
        log("本周期无交易信号", PATHS["log"])

    log("✅ 本轮执行完成", PATHS["log"])
    return {
        "status": "done",
        "signal_count": len(buy_signals) + len(sell_signals),
        "buy_signals": len(buy_signals),
        "sell_signals": len(sell_signals),
    }


if __name__ == "__main__":
    try:
        r = main()
        print(f"\n决策: {r.get('status')} | 信号: {r.get('signal_count', 0)}个")
    except Exception as e:
        log(f"❌ 未捕获异常: {e}", PATHS.get("log"))
        import traceback
        traceback.print_exc()
