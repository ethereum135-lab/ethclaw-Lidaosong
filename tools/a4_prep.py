#!/usr/bin/env python3
"""A4数据预处理 — 把signals.json/A3报告/direction/TRADES汇总为紧凑摘要

输出: data/a4_input_summary.md (~1KB)
A4每次执行前先跑这个脚本，再读摘要做决策，避免被原始数据撑爆上下文。
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(os.environ.get('ZQ_ROOT', '/Users/lidaosong/zq_web4_trading_system'))
OUTPUT = BASE / 'data' / 'a4_input_summary.md'

def read_json(rel_path):
    p = BASE / rel_path
    if not p.exists():
        return None
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        return None

def read_text(rel_path):
    p = BASE / rel_path
    if not p.exists():
        return None
    try:
        with open(p) as f:
            content = f.read()
            # Try to find the most recent file or the one for today
            return content
        return content
    except Exception:
        return None

def get_recent_sells():
    """Scan TRADES.md for sells within the last 2 hours → cooldown tracker."""
    try:
        from datetime import datetime, timedelta, timezone
        BJT = timezone(timedelta(hours=8))
        now_bjt = datetime.now(BJT)
        cutoff = now_bjt - timedelta(hours=2)
        trades_text = read_text('audit/TRADES.md')
        if not trades_text:
            return None
        lines = trades_text.split('\n')
        sells = []
        import re
        for line in lines:
            if 'SELL' not in line or 'NO TRADE' in line or 'NODE_CHECK' in line:
                continue
            # Match pipe-format SELL lines: ||| 2026-06-15 05:10 BJT | SELL | SYM | ...
            m = re.search(r'((\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}):\d{2}\s*BJT)\s*\|.*?\bSELL\b.*?\|\s*(\w+)\s*\|', line)
            if m:
                ts_str = m.group(1)
                ts = datetime.strptime(f"{m.group(2)} {m.group(3)}", "%Y-%m-%d %H:%M")
                ts = ts.replace(tzinfo=BJT)
                symbol = m.group(4)
                if ts >= cutoff:
                    mins_ago = int((now_bjt - ts).total_seconds() / 60)
                    sells.append((symbol, mins_ago, ts_str))
        if not sells:
            return None
        sells.sort(key=lambda x: x[1])  # Most recent first
        lines_out = []
        lines_out.append("## 🔄 近期卖出（2h冷却监控）")
        for sym, mins, ts in sells:
            status = "❌冷却中" if mins < 120 else "✅可买入"
            lines_out.append(f"- **{sym}** {ts}卖出（{mins}分钟前）→ {status}")
        lines_out.append("")
        return '\n'.join(lines_out)
    except Exception as e:
        return f"## 近期卖出\n⚠️ 查询失败: {e}\n"


def find_latest_a3_report():
    """Find today's A3 reports — both morning and afternoon."""
    today = datetime.now().strftime('%Y-%m-%d')
    out_dir = BASE / 'profiles' / 'a3-bull' / 'output'
    
    morning_p = out_dir / f'{today}.md'
    afternoon_p = out_dir / f'{today}-afternoon.md'
    
    morning_content = None
    afternoon_content = None
    
    if morning_p.exists():
        with open(morning_p) as f:
            morning_content = f.read()
    
    if afternoon_p.exists():
        with open(afternoon_p) as f:
            afternoon_content = f.read()
    
    # Fallback: list recent if no today's report
    if not morning_content and not afternoon_content:
        if out_dir.exists():
            files = sorted(out_dir.glob('*.md'), reverse=True)
            if files:
                with open(files[0]) as f:
                    morning_content = f.read()
    
    return today, morning_content, afternoon_content

def extract_signals_summary(data):
    """从signals.json提取STRONG/SIGNAL信号摘要。"""
    if not data:
        return "## 信号数据\n⚠️ 无信号数据\n"
    
    # The actual key in signals.json is 'results' not 'signals'
    signals_list = data.get('results') or data.get('signals') or []
    scanned_at = data.get('scanned_at', '未知')
    summary = data.get('summary', {})
    
    lines = [f"## 信号数据（扫描时间: {scanned_at}）"]
    if summary:
        lines.append(f"STRONG: {summary.get('strong',0)} | SIGNAL: {summary.get('signal',0)} | WATCH: {summary.get('watch',0)} | PASS: {summary.get('pass',0)}")
    
    if not isinstance(signals_list, list) or len(signals_list) == 0:
        lines.append(f"⚠️ 信号列表为空或格式不识别 (type={type(signals_list).__name__})")
        return '\n'.join(lines)
    
    # STRONG coins
    strong_coins = [s for s in signals_list if s.get('level') == 'STRONG']
    signal_coins = [s for s in signals_list if s.get('level') == 'SIGNAL']
    
    if strong_coins:
        lines.append("\n### STRONG (优先级最高)")
        for c in strong_coins:
            sym = c.get('symbol', '?')
            price = c.get('price', '?')
            cat = c.get('category', '?')
            score = c.get('total_score', '?')
            sigs = c.get('signals', {})
            details = []
            for sig_name, sig_data in sigs.items() if isinstance(sigs, dict) else []:
                if isinstance(sig_data, dict) and sig_data.get('score', 0) >= 10:
                    details.append(f"{sig_name}:{sig_data['score']}pts")
            lines.append(f"- **{sym}** ${price} [{cat}] 总分{score} | {' '.join(details[:3])}")
    
    if signal_coins:
        lines.append(f"\n### SIGNAL ({len(signal_coins)}个)")
        for c in signal_coins[:10]:  # limit to 10
            sym = c.get('symbol', '?')
            price = c.get('price', '?')
            cat = c.get('category', '?')
            score = c.get('total_score', '?')
            sigs = c.get('signals', {})
            details = []
            for sig_name, sig_data in sigs.items() if isinstance(sigs, dict) else []:
                if isinstance(sig_data, dict) and sig_data.get('score', 0) >= 10:
                    details.append(f"{sig_name}:{sig_data['score']}pts")
            lines.append(f"- {sym} ${price} [{cat}] 总分{score} | {' '.join(details[:2])}")
    
    return '\n'.join(lines)

def extract_a3_summary(date_str, content):
    """从A3报告提取候选币摘要（适配2026-06格式：🟢 高置信度候选 + 表格）"""
    if not content:
        return "## A3牛币报告\n⚠️ 今日无A3报告\n"
    
    lines = [f"## A3牛币报告（{date_str}）"]
    
    # Flag sections
    in_high = False
    in_medium = False
    in_exec = False
    in_exclude = False
    in_market = False
    
    # Collect high-confidence coins (table format)
    high_coins = []
    medium_coins = []
    exec_refs = []
    market_info = []
    exclude_info = []
    
    for line in content.split('\n'):
        stripped = line.strip()
        
        if '## 🟢 高置信度候选' in stripped:
            in_high = True; in_medium = False; in_exec = False; in_exclude = False; in_market = False
            continue
        if '## 🟡 中等置信度候选' in stripped:
            in_medium = True; in_high = False; in_exec = False; in_exclude = False; in_market = False
            continue
        if '## 📊 A4执行参考' in stripped:
            in_exec = True; in_high = False; in_medium = False; in_exclude = False; in_market = False
            continue
        if '## 🔴 高信号分排除清单' in stripped:
            in_exclude = True; in_high = False; in_medium = False; in_exec = False; in_market = False
            continue
        if '## 市场环境' in stripped:
            in_market = True; in_high = False; in_medium = False; in_exec = False; in_exclude = False
            continue
        
        # Detect section end (next ## section)
        if stripped.startswith('## ') and not stripped.startswith('###'):
            in_high = False; in_medium = False; in_exec = False; in_exclude = False; in_market = False
        
        # Parse high-confidence candidate table rows
        if in_high and stripped.startswith('|') and '**' in stripped:
            parts = [p.strip() for p in stripped.split('|') if p.strip()]
            # Format: | **VIC** | other | **95 STRONG** | **27** | 20 | 🟢 **just_starting** | ...
            if len(parts) >= 3:
                # Extract coin symbol
                coin = parts[0].replace('**', '').strip()
                score_raw = parts[2].replace('**', '').strip() if len(parts) > 2 else ''
                phase_raw = parts[5].replace('**', '').strip() if len(parts) > 5 else ''
                high_coins.append(f"★ {coin} ({score_raw}) — {phase_raw}")
        
        # Parse medium confidence table
        if in_medium and stripped.startswith('|') and '**' in stripped:
            parts = [p.strip() for p in stripped.split('|') if p.strip()]
            if len(parts) >= 3:
                coin = parts[0].replace('**', '').strip()
                score_raw = parts[2].replace('**', '').strip() if len(parts) > 2 else ''
                wait = parts[4].replace('**', '').strip() if len(parts) > 4 else ''
                medium_coins.append(f"○ {coin} ({score_raw}) — {wait[:60]}")
        
        # Market environment
        if in_market and stripped.startswith('-'):
            market_info.append(stripped[:100])
        
        # Execution reference
        if in_exec:
            if stripped.startswith(('1.', '2.', '3.', '4.', '5.')):
                exec_refs.append(f"  {stripped[:100]}")
            elif stripped.startswith('-') and '建议' in stripped or '优先' in stripped:
                exec_refs.append(f"  {stripped[:100]}")
        
        # Exclude list
        if in_exclude and stripped.startswith('|') and '**' in stripped:
            parts = [p.strip() for p in stripped.split('|') if p.strip()]
            if len(parts) >= 3:
                coin = parts[0].replace('**', '').strip()
                exclude_info.append(f"  ⛔ {coin}")
    
    # Output
    if market_info:
        lines.append("市场环境:")
        lines.extend(market_info[:5])
    
    if high_coins:
        lines.append("\n🟢 高置信度候选（A4优先采用）:")
        lines.extend(high_coins)
    
    if medium_coins:
        lines.append("\n🟡 中等置信度:")
        lines.extend(medium_coins[:5])
    
    if exec_refs:
        lines.append("\n📊 执行参考:")
        lines.extend(exec_refs[:8])
    
    if exclude_info:
        lines.append("\n🔴 排除清单（不要追）:")
        lines.extend(exclude_info[:8])
    
    return '\n'.join(lines[:35])

def extract_direction_summary(content):
    """从方向优先级文件提取摘要。"""
    if not content:
        return "## ZH方向优先级\n⚠️ 今日无方向优先级文件\n"
    
    lines = ["## ZH方向优先级"]
    for line in content.split('\n')[:25]:
        stripped = line.strip()
        # Keep section headers, bullet points, bold text, and summary lines
        if stripped.startswith('#') or stripped.startswith('-') or stripped.startswith('|') or '权重' in stripped or '一句话' in stripped:
            if '---' not in stripped:
                lines.append(stripped)
    
    return '\n'.join(lines[:15])

def _extract_live_positions_from_trades():
    """从 data/TRADES.md（A4活跃日志）尾部提取真实持仓数据。

    2026-08-12新增: sync_a4_state只写币名列表 → a4_prep显示0持仓误报。
    A4执行节点每轮写入 `卖出: 无触发 (LINK 1.9684@买8.666+0.6% / BABY ...)`
    格式的真实 qty@entry+pnl。解析最近一轮填充。
    返回 {coin: (qty, entry, pnl_pct)} 或 {}。
    """
    import re as _re
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'TRADES.md')
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            content = f.read()
    except Exception:
        return {}
    # 找最后一行含 `@买` 的卖出评估行（该行含嵌套括号如 BTC$63,747(-0.61%)，无法用括号组匹配）
    last_line = None
    for line in reversed(content.splitlines()):
        if '@买' in line:
            last_line = line
            break
    if not last_line:
        return _extract_positions_new_format(content)
    result = {}
    for sym, qty, entry, pnl in _re.findall(r'([A-Z0-9]{2,12}) ([\d.]+)@买([\d.]+)([+-][\d.]+)%', last_line):
        ep = float(entry)
        result[sym] = (float(qty), ep, float(pnl), ep * (1 + float(pnl) / 100.0))
    if not result:
        result = _extract_positions_new_format(content)
    return result


def _extract_positions_new_format(content):
    """2026-08-25 ZH: A4新格式（@买旧格式已不再出现）——合并两模式恢复qty/entry/pnl：
    持仓状态行 `ZEC 0.041897@$841.56=$35.26 / HBAR 211.588@$0.07948=$16.82`（qty+现价）
    + 决策理由行 `ZEC avg$843.26现$848.65(+0.64%)`（avg成本+盈亏%）。
    返回 {coin: (qty, entry, pnl_pct, current_price)} 或 {}。
    """
    import re as _re
    qty_map = {}
    avg_map = {}
    for line in content.splitlines():
        for sym, qty, cur in _re.findall(r'([A-Z0-9]{2,12}) ([\d,]+\.?\d*)@\$?([\d.eE\-]+)=', line):
            try:
                qf = float(qty.replace(',', ''))
                cf = float(cur)
                if 0 < cf < 1000000:
                    qty_map[sym] = (qf, cf)  # 后写覆盖=取最新一轮
            except ValueError:
                continue
        for sym, entry, cur, pnl in _re.findall(r'([A-Z0-9]{2,12}) avg\$([\d.]+)现\$([\d.]+)\(([+-][\d.]+)%\)', line):
            try:
                ef = float(entry)
                if 0.000001 < ef < 1000000:
                    avg_map[sym] = (ef, float(cur), float(pnl))
            except ValueError:
                continue
        # 2026-08-29 A5修复: A4引擎"持仓API实核: ENA 49.34601@0.1639 现价0.1607(-1.9%)"格式
        # （12:00-16:00每轮写入；16:05后引擎误写"已清"——此格式是恢复真实持仓认知的关键）
        for sym, qty, entry, cur, pnl in _re.findall(
                r'([A-Z0-9]{2,12}) ([\d.]+)@([\d.]+) 现价([\d.]+)\(([+-][\d.]+)%\)', line):
            try:
                qf = float(qty); ef = float(entry); cf = float(cur)
                if qf > 0 and 0.000001 < ef < 1000000 and 0 < cf < 1000000:
                    qty_map[sym] = (qf, cf)
                    avg_map[sym] = (ef, cf, float(pnl))
            except ValueError:
                continue
    result = {}
    for sym, (qty, cur) in qty_map.items():
        entry, _cur, pnl = avg_map.get(sym, (0.0, 0.0, 0.0))
        result[sym] = (qty, entry, pnl, cur)
    return result

def _api_real_positions():
    """Binance API实核真实持仓（2026-08-29 A5修复）。

    根因: state/a4.json的active_positions只有币名列表(qty=0) → a4_prep渲染
    "ENA 0.0000@0 → $0.00" → A4引擎16:05起误判"ENA已清仓"，实际在账$7.7，
    止损监控中断7小时。API是权威来源，成功时直接覆盖qty/现价/价值。
    返回 {sym: (qty, price)}（非稳定币估值>= $5，排除ETH/BNB等非A4管理资产）。
    """
    try:
        import hmac as _hmac
        import hashlib as _hl
        import time as _time
        auth = read_json('config/auth.json')
        if not auth or 'binance' not in auth:
            return {}
        ak = auth['binance']['api_key']
        sec = auth['binance']['api_secret']
        r0 = subprocess.run(
            ['curl', '--socks5-hostname', '127.0.0.1:1080', '-s', '--max-time', '8',
             'https://api.binance.com/api/v3/time'],
            capture_output=True, text=True, timeout=12)
        if r0.returncode != 0 or not r0.stdout.strip():
            return {}
        st = json.loads(r0.stdout).get('serverTime')
        ts = int(st) + 500  # serverTime校准，避免-1021
        q = f"timestamp={ts}&recvWindow=60000"
        sig = _hmac.new(sec.encode(), q.encode(), _hl.sha256).hexdigest()
        url = f"https://api.binance.com/api/v3/account?{q}&signature={sig}"
        r = subprocess.run(
            ['curl', '--socks5-hostname', '127.0.0.1:1080', '-s', '--max-time', '12',
             '-H', f'X-MBX-APIKEY: {ak}', url],
            capture_output=True, text=True, timeout=15)
        if r.returncode != 0 or not r.stdout.strip():
            return {}
        d = json.loads(r.stdout)
        A4_NON_MANAGED = ('USDT', 'USDC', 'BUSD', 'FDUSD', 'TUSD', 'DAI',
                          'ETH', 'BNB', 'WBETH', 'LDETH', 'LDBNB')
        non_stable = [b['asset'] for b in d.get('balances', [])
                      if (float(b.get('free', 0)) > 0 or float(b.get('locked', 0)) > 0)
                      and b['asset'] not in A4_NON_MANAGED]
        if not non_stable:
            return {}
        # 2026-08-29 A5修复: 过滤非ASCII资产名（如"币安人生"）+ LD理财前缀
        # （LDSUI/LDSHIB2等无USDT现货交易对→-1121整体失败）——symbols批量接口
        # 任一无效symbol即整体-1121（08-29实案: ETHWUSDT已下架）；且json.dumps
        # 默认", "带空格违反Binance symbols正则 → separators=(",",":")
        valid_syms = [f"{a}USDT" for a in non_stable
                      if a.isascii() and a.isupper() and not a.startswith('LD')]
        if not valid_syms:
            return {}
        syms = json.dumps(valid_syms, separators=(',', ':'))
        r2 = subprocess.run(
            ['curl', '--socks5-hostname', '127.0.0.1:1080', '-s', '--max-time', '20',
             '-G', 'https://api.binance.com/api/v3/ticker/price',
             '--data-urlencode', f'symbols={syms}'],
            capture_output=True, text=True, timeout=25)
        prices = {}
        try:
            for p in json.loads(r2.stdout):
                prices[p['symbol']] = float(p['price'])
        except Exception:
            prices = {}
        if not prices:
            # 2026-08-29 A5修复: 批量含未知下架symbol（如ETHW）→整体-1121 →
            # 回退全量ticker/price（~600KB，实测~15s，sync_a4_state同款路径08-28验证）
            r3 = subprocess.run(
                ['curl', '--socks5-hostname', '127.0.0.1:1080', '-s', '--max-time', '60',
                 'https://api.binance.com/api/v3/ticker/price'],
                capture_output=True, text=True, timeout=65)
            try:
                for p in json.loads(r3.stdout):
                    prices[p['symbol']] = float(p['price'])
            except Exception:
                prices = {}
        if not prices:
            return {}
        bal = {b['asset']: float(b['free']) for b in d.get('balances', [])}
        result = {}
        for a in non_stable:
            px = prices.get(f"{a}USDT")
            qty = bal.get(a, 0)
            if px and qty * px >= 5.0:  # MIN_NOTIONAL级: <$5为尘仓不占A4仓位上限
                result[a] = (qty, px)
        return result
    except Exception:
        return {}

def extract_positions_summary(content):
    """从 state/a4.json 读真实持仓，不解析TRADES.md历史记录。"""
    state = read_json('state/a4.json')
    if not state or 'data' not in state:
        return "## 持仓数据\n⚠️ state/a4.json不可读，回退TRADES.md"
    
    d = state['data']
    # 2026-08-12修复: sync_a4_state写入的是 active_positions(币名列表)+positions_count，
    # 旧代码只读 positions(详细数组, 不存在) → 恒0持仓/总权益$0.00 误报。
    # 优先详细数组，缺失时用 active_positions 币名列表重建摘要。
    positions = d.get('positions', [])
    active_names = d.get('active_positions', [])
    if not positions and active_names:
        positions = [{'coin': c, 'qty': 0, 'entry': 0, 'current': 0, 'value': 0, 'pnl_pct': 0} for c in active_names]
        # 2026-08-12修复: sync_a4_state只写币名列表(qty=0) → a4_input_summary误报
        # 「LINK 0.0000@0 → $0.00」。从 data/TRADES.md(A4活跃日志, 非陈旧audit)尾部
        # 提取真实 `SYM qty@买price+pct%` 数据填充，消除0持仓/0价值误报。
        _qty_price_map = _extract_live_positions_from_trades()
        if _qty_price_map:
            for pos in positions:
                coin = pos.get('coin')
                if coin in _qty_price_map:
                    q, e, pnl, cur = _qty_price_map[coin]
                    pos['qty'] = q
                    pos['entry'] = e
                    pos['pnl_pct'] = pnl
                    if e > 0:
                        pos['current'] = round(e * (1 + pnl / 100.0), 8)
                    else:
                        pos['current'] = cur
                    pos['value'] = round(q * pos['current'], 4)
    # 2026-08-29 A5修复: qty=0渲染"0.0000@0→$0.00"导致A4引擎16:05起误判"ENA已清仓"
    # （实际在账≈$7.7，止损监控中断7h）。API实核是权威：state漏币→补齐；
    # state有币但qty/现价提取失败→填真实值；尘仓(<$5)过滤。
    api_pos = _api_real_positions()
    if api_pos:
        _known = {p.get('coin') for p in positions}
        for pos in positions:
            coin = pos.get('coin')
            if coin in api_pos:
                _q, _px = api_pos[coin]
                if not pos.get('qty') or not pos.get('current'):
                    pos['qty'] = _q
                    pos['current'] = _px
                    pos['value'] = round(_q * _px, 4)
                    if pos.get('entry'):
                        pos['pnl_pct'] = round((_px / pos['entry'] - 1) * 100, 2)
        for _sym, (_q, _px) in api_pos.items():
            if _sym not in _known:
                positions.append({'coin': _sym, 'qty': _q, 'entry': 0,
                                  'current': _px, 'value': round(_q * _px, 4),
                                  'pnl_pct': 0})
        positions = [p for p in positions if p.get('value', 0) > 0]
    dust = d.get('dust', [])
    usdt_bal = d.get('usdt_balance', {})
    if isinstance(usdt_bal, dict):
        usdt_free = usdt_bal.get('free', 0)
    elif isinstance(usdt_bal, (int, float)):
        usdt_free = usdt_bal
    else:
        usdt_free = 0
    total_equity = d.get('total_equity', 0)

    # 2026-08-12: sync_a4_state(parse_sig_format路径)不写total_equity → a4_prep显示总权益$0.00。
    # 回退到 data/signals/a4_signals.json 的 position_eval.total_equity_approx (AWS实盘验证值)。
    if not total_equity:
        sig = read_json('data/signals/a4_signals.json')
        pe = (sig or {}).get('position_eval') or {}
        eq = pe.get('total_equity_approx', 0) or 0
        if eq:
            total_equity = eq
    # total_equity缺失时按 USDT+仓位价值估算（仓位价值已知则加总）
    if not total_equity:
        pos_val = sum(p.get('value', 0) for p in positions if p.get('value'))
        if pos_val > 0 or usdt_free > 0:
            total_equity = pos_val + usdt_free
    
    result = ["## 持仓数据（来自state/a4.json — 真实Binance余额）"]
    result.append(f"总权益: ${total_equity:.2f} | USDT空闲: ${usdt_free:.2f} | 活跃持仓: {len(positions)}个")
    
    for p in positions:
        sym = p.get('coin', '?')
        qty = p.get('qty', 0)
        entry = p.get('entry', 0)
        curr = p.get('current', 0)
        val = p.get('value', 0)
        pnl = p.get('pnl_pct', 0)
        momo = p.get('momentum_5m', '')
        # 2026-08-29 A5修复: qty/价值未知时严禁渲染"$0.00"（A4会误判"已清仓"）
        if not qty or not val:
            result.append(f"- ⚠️ **{sym}** 持仓数量待实核（勿判已清仓）| {momo[:40]}")
            continue
        # pnl_pct might be string like "+17.5%" or "-3.2%" or number
        if isinstance(pnl, str):
            pnl_str = pnl.strip().replace('%', '').replace('+', '')
            pnl_num = float(pnl_str) if pnl_str else 0.0
        else:
            pnl_num = float(pnl)
        icon = '✅' if pnl_num >= 0 else '❌'
        result.append(f"- {icon} **{sym}** {qty:.4f}@{entry} → ${curr} = ${val:.2f} (PnL {pnl_num:+.2f}%) | {momo[:40]}")
    
    if dust:
        dust_val = sum(d.get('value', 0) for d in dust)
        result.append(f"- 💤 尘仓: {len(dust)}个 ~${dust_val:.2f} ({', '.join(d['coin'] for d in dust[:5])})")
    
    return '\n'.join(result)

def get_ssh_portfolio():
    """尝试SSH到AWS获取实时持仓。"""
    try:
        result = subprocess.run([
            'ssh', '-i', os.path.expanduser('~/.zq_vault/web4.0.pem'),
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'ConnectTimeout=5',
            'ubuntu@15.134.211.154',
            'cd /home/ubuntu/zq_web4_trading_system && '
            'python3 production/engine/aws_executor.py --check 2>/dev/null || '
            'echo "SSH_CHECK_FAILED"'
        ], capture_output=True, text=True, timeout=15)
        output = result.stdout.strip()
        if output and 'SSH_CHECK_FAILED' not in output:
            return output
    except Exception:
        pass
    return None

def main():
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Gather all data
    signals_data = read_json('data/signals.json')
    a3_date, a3_morning_content, a3_afternoon_content = find_latest_a3_report()
    direction_content = read_text(f'shared/direction_priority_{a3_date or datetime.now().strftime("%Y-%m-%d")}.md')
    trades_content = read_text('audit/TRADES.md')
    
    # Try to get today's direction first
    today = datetime.now().strftime('%Y-%m-%d')
    today_direction = read_text(f'shared/direction_priority_{today}.md')
    if today_direction:
        direction_content = today_direction
    
    # Get SSH portfolio
    portfolio = get_ssh_portfolio()
    
    # Build summary
    lines = [
        f"# A4输入摘要 — {now}",
        f"> 由 a4_prep.py 自动生成，数据来源: signals.json + A3报告 + ZH方向 + TRADES + AWS",
        "",
        "## 🔴 铁律规则（每日目标+信号质量优先）",
        "- **规则1：每笔交易为了盈利** — 金额不是问题，信号质量才是",
        "- **规则2：强信号(≥60pts)应重仓45%**，中信号(40-59pts)轻仓25%，弱信号(<40pts)=不买",
        "- **规则3：不分3个$10小仓**，集中到1笔有意义的仓位",
        "- **规则4：目标日盈利 = 总资产×2%/天**（$430→$1M复利）",
        "- **规则5：每天自检** — 今天为什么盈/为什么亏？",
        "",
    ]
    
    # Section 1: directions
    lines.append(extract_direction_summary(direction_content))
    lines.append("")
    
    # Section 2: signals (compact)
    lines.append(extract_signals_summary(signals_data))
    lines.append("")
    
    # Section 2b: recent sells cooldown tracker
    cooldown_text = get_recent_sells()
    if cooldown_text:
        lines.append(cooldown_text)
        lines.append("")
    
    # Section 3: A3 report (morning)
    lines.append(extract_a3_summary(a3_date or 'unknown', a3_morning_content))
    lines.append("")
    
    # Section 3b: A3 afternoon report (if exists)
    if a3_afternoon_content:
        afternoon_summary = extract_a3_summary(f"{a3_date} 午后精选", a3_afternoon_content)
        # Prefix to distinguish from morning
        afternoon_lines = afternoon_summary.split('\n')
        afternoon_summary = '\n'.join(afternoon_lines)
        lines.append(afternoon_summary)
        lines.append("")
    
    # Section 4: positions
    lines.append(extract_positions_summary(trades_content))
    lines.append("")
    
    # Section 5: SSH portfolio
    if portfolio:
        lines.append("## AWS实时持仓")
        lines.append(f"```\n{portfolio[:500]}\n```")
    else:
        lines.append("## AWS实时持仓")
        lines.append("⚠️ SSH不可用，使用TRADES.md持仓数据")
        lines.append("")
    
    # Section 5b: Shuffle check
    try:
        shuffle_result = subprocess.run(
            [sys.executable, str(BASE / 'tools' / 'a4_shuffle_check.py')],
            capture_output=True, text=True, timeout=30
        )
        if shuffle_result.returncode == 0 and shuffle_result.stdout:
            # Extract just the shuffle section
            out_lines = shuffle_result.stdout.strip().split('\n')
            shuffle_section = []
            in_shuffle = False
            for l in out_lines:
                if l.startswith('## 轮动检查'):
                    in_shuffle = True
                if l.startswith('--- a4_shuffle_check') and in_shuffle:
                    break
                if in_shuffle:
                    shuffle_section.append(l)
            if shuffle_section:
                lines.append('\n'.join(shuffle_section))
    except Exception:
        lines.append("## 轮动检查\n⚠️ 轮动检查执行失败\n")
    
    # Section 6: quick summary (for A4's easy reference)
    lines.append("## 快速参考")
    
    # Direction match map: build from direction priority file
    dir_match = {}
    cat_map = {
        'privacy': ['privacy', '隐私'],
        'rwa': ['rwa', '资产代币化'],
        'l1': ['l1', '基础设施', 'layer1'],
        'meme': ['meme'],
        'gamefi': ['gamefi', '游戏', '元宇宙'],
        'defi': ['defi'],
        'ai': ['ai'],
        'payment': ['payment', '支付'],
        'depin': ['depin', '算力'],
        'storage': ['storage', '存储'],
        'crosschain': ['crosschain', '跨链'],
        'other': ['other', '其他'],
    }
    
    if direction_content:
        in_avoid = False
        for line in direction_content.split('\n'):
            stripped = line.strip()
            if '不关注' in stripped or '减仓信号' in stripped:
                in_avoid = True
                continue
            # Main direction lines: "1. 🔥 **Privacy赛道** (权重40%)"
            if not in_avoid and stripped.startswith(('1.', '2.', '3.', '4.', '5.')) and '**' in stripped:
                parts = stripped.split('**')
                for i, p in enumerate(parts):
                    # Find the bolded part that contains the direction name (not "权重" etc.)
                    if i % 2 == 1 and len(p) < 30 and '权重' not in p and 'BTC' not in p:
                        dir_name = p.strip().lower()
                        for cat, keywords in cat_map.items():
                            if any(kw in dir_name for kw in keywords):
                                mark = '❌' if '❌' in stripped else '✅'
                                # Store under both the cat_map key and any alternate category names
                                dir_match[cat] = mark
                                for kw in keywords:
                                    if kw != cat and len(kw) > 2:
                                        dir_match[kw] = mark
            # Avoid section: "- ❌ **Meme赛道**"
            if in_avoid and stripped.startswith('- ❌') and '**' in stripped:
                parts = stripped.split('**')
                for i, p in enumerate(parts):
                    if '赛道' in p:
                        avoid_name = p.replace('赛道', '').strip().lower()
                        for cat, keywords in cat_map.items():
                            if any(kw in avoid_name for kw in keywords):
                                dir_match[cat] = '❌'
                                for kw in keywords:
                                    if kw != cat and len(kw) > 2:
                                        dir_match[kw] = '❌'
    
    if signals_data:
        signals_list = signals_data.get('results') or signals_data.get('signals') or []
        if isinstance(signals_list, list):
            strong = [s for s in signals_list if s.get('level') == 'STRONG']
            signal = [s for s in signals_list if s.get('level') == 'SIGNAL']
        else:
            strong = []
            signal = []
        
        strong_str = []
        for s in strong[:5]:
            sym = s.get('symbol','?')
            cat = s.get('category','?').lower()
            match = dir_match.get(cat, '?')
            score = s.get('total_score', '?')
            strong_str.append(f"{sym}[{cat}{match}{score}pts]")
        lines.append(f"STRONG: {' '.join(strong_str)}")
        
        signal_str = []
        for s in signal[:5]:
            sym = s.get('symbol','?')
            cat = s.get('category','?').lower()
            match = dir_match.get(cat, '?')
            score = s.get('total_score', '?')
            signal_str.append(f"{sym}[{cat}{match}{score}pts]")
        lines.append(f"SIGNAL: {' '.join(signal_str)}")
    
    # Section 6b: 周末极恐模式检查
    now = datetime.now()
    is_weekend = now.weekday() >= 5  # 5=Sat, 6=Sun
    
    # Get live FNG from ZH direction_priority (most authoritative — produced 05:30 daily)
    fng_value = 50
    dir_path = f'shared/direction_priority_{now.strftime("%Y-%m-%d")}.md'
    dir_content = read_text(dir_path)
    if dir_content:
        import re as re_fng
        fng_m = re_fng.search(r'F[&＆]?G[:=：\s]*\*{0,2}(\d+)', dir_content[:3000])
        if fng_m:
            fng_value = int(fng_m.group(1))
    # Fallback: node_state.json
    if fng_value == 50:
        fng_data = read_json('data/node_state.json')
        if fng_data:
            snaps = fng_data.get('prev_snapshots', {})
            for _k, _v in snaps.items():
                if 'fear_greed' in _v:
                    fg = _v['fear_greed']
                    if isinstance(fg, (int, float)) and 1 <= fg <= 100:
                        fng_value = int(fg)
                    break
    
    if is_weekend and fng_value < 25:
        lines.append("")
        lines.append("## ⚠️ 周末极恐模式")
        lines.append(f"- 周末({['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][now.weekday()]}) + F&G={fng_value}(极恐)")
        lines.append(f"- 建议：持仓≤3个减仓至合理水平，USDT保留≥50%待周一")
        lines.append(f"- 周末新买门槛提升：仅接受STRONG≥90的just_starting信号")
        lines.append(f"- 暂缓轮动操作，除非有已触发止损的强制清仓")
        lines.append("")
    
    # Section 6: fast_scan K线候选
    fast_scan = read_json('data/fast_scan_candidates.json')
    if fast_scan and 'candidates' in fast_scan:
        cands = fast_scan['candidates']
        lines.append("")
        scan_time = fast_scan.get('scan_time', fast_scan.get('scanned_at', '?'))
        eng_ver = fast_scan.get('engine_version', 'v2.1')
        lines.append(f"## Fast Scan K线候选（{scan_time} engine:{eng_ver}）")
        lines.append(f"候选数: {len(cands)}个")
        lines.append("")
        top_cands = cands[:6]
        for c in top_cands:
            sym = c.get('symbol', '?').replace('USDT','')
            # v3.0 fields
            chg_1h = c.get('chg_1h', 0)
            chg_24h = c.get('chg_24h', c.get('change_24h', 0))
            vol_surge = c.get('vol_surge', c.get('vol_ratio', 1))
            conf = c.get('confidence', '?')
            sigs = c.get('signal_count', 0)
            vol = c.get('volume_24h', 0)
            score = c.get('total_score', 0)
            rp = c.get('range_pos', 50)
            hi = '⬆高位' if rp >= 85 else ('⬇低位' if rp < 30 else '')
            lines.append(f"- {'🟢' if conf in ('超高','高') else '🟡'} **{sym}** score{score} 1h{chg_1h:+.2f}% 24h{chg_24h:+.1f}% vol{vol_surge:.1f}x 量${vol/1e6:.2f}M range{rp:.0f}% {conf} {sigs}信号{hi}")
        if not top_cands:
            lines.append("  ⚠️ 当前无A级候选")
        lines.append("")
    
    # Section 7: position sizing recommendation (code-level, LLM建议)
    lines.append("")
    lines.append("## 仓位建议（代码计算，非LLM判断）")
    
    # Get USDT from state/a4.json (fallback from dead SSH)
    usdt_for_sizing = None
    usdt_match = None
    sizing_state = read_json('state/a4.json')
    if sizing_state and 'data' in sizing_state:
        usdt_bal = sizing_state['data'].get('usdt_balance', {})
        if isinstance(usdt_bal, dict):
            usdt_for_sizing = usdt_bal.get('free') or usdt_bal.get('total', 0)
        elif isinstance(usdt_bal, (int, float)):
            usdt_for_sizing = usdt_bal
        else:
            usdt_for_sizing = 0
        total_eq = sizing_state['data'].get('total_equity', 0)
        if total_eq and usdt_for_sizing:
            idle_rate = usdt_for_sizing / total_eq
            # NAV.md §三 FNG风控：FNG<20单仓7.5%，FNG≥20单仓10%
            nav_max_pos = total_eq * 0.075  # 保守估计FNG<20
            if idle_rate > 0.5:
                if total_eq < 50:
                    per_pos = total_eq * 0.7 / 3  # 小账户<$50: 跳过FNG上限，突破MIN_NOTIONAL锁死
                    lines.append(f"[FNG风控覆写] 闲置{idle_rate*100:.0f}%>50%+小账户{total_eq:.0f}<$50 -> 跳过FNG上限, 每仓${per_pos:.0f} (>$5 MIN_NOTIONAL)")
                else:
                    per_pos = min(total_eq * 0.7 / 3, nav_max_pos)
                    lines.append(f"[FNG风控] 闲置{idle_rate*100:.0f}%>50% -> 每仓约${per_pos:.0f} (FNG上限${nav_max_pos:.0f})")
    else:
        # fallback to SSH portfolio parse
        portfolio_text = portfolio or ""
        import re as re_module
        usdt_match = re_module.search(r'USDT.*?free.*?([\d.]+)', portfolio_text)
    if usdt_match:
        usdt_for_sizing = float(usdt_match.group(1))
    
    if usdt_for_sizing and usdt_for_sizing > 0:
        # Recommend concentration
        all_sigs = signals_data.get('results') or signals_data.get('signals') or [] if signals_data else []
        strong_scores = []
        if isinstance(all_sigs, list):
            for s in all_sigs:
                if s.get('level') == 'STRONG':
                    strong_scores.append((s.get('total_score', 0), s.get('symbol', '?')))
        strong_scores.sort(reverse=True)
        
        if strong_scores and strong_scores[0][0] >= 60:
            best = strong_scores[0]
            # 不超过FNG风控上限（FNG<20: 7.5%）
            fng_cap = min(usdt_for_sizing, total_eq * 0.075) if total_eq else usdt_for_sizing * 0.075
            elite_size = min(usdt_for_sizing * 0.45, fng_cap)
            strong_size = min(usdt_for_sizing * 0.25, fng_cap)
            lines.append(f"- 可用USDT: ${usdt_for_sizing:.2f}")
            lines.append(f"- 最强信号: {best[1]} ({best[0]}pts)")
            lines.append(f"- 建议: 如果买{best[1]} → ${elite_size:.0f} (FNG上限${fng_cap:.0f})")
            lines.append(f"- ⚠️ 如果分3笔各$10 = 碎片化，不如集中1笔${elite_size:.0f}")
        else:
            lines.append(f"- 可用USDT: ${usdt_for_sizing:.2f}")
            lines.append(f"- 无≥60pts的STRONG信号 → 等待，不强行买入")
    else:
        lines.append("- 可用USDT: 未知（SSH不可用）")
        lines.append("- 建议依据轮动检查释放资金判断")
    lines.append("")
    content = '\n'.join(lines)
    
    with open(OUTPUT, 'w') as f:
        f.write(content)
    
    # 🔧 Fix: overwrite state/a4.json with real data from node_history (SSH→AWS source)
    try:
        fix_state_from_node_history()
    except Exception as e:
        print(f"⚠️ state/a4.json修正失败: {e}")
    
    # Print to stdout for context_from consumption
    print(content)
    print(f"\n--- a4_prep.py done, wrote {OUTPUT} ({len(content)} bytes) ---")

def fix_state_from_node_history():
    """Read latest node_history.jsonl entry (verified via SSH→AWS) and write to state/a4.json.

    This fixes the problem where A4 reads state/a4.json (written via broken SOCKS5 proxy)
    and sees only partial holdings, while node_history.jsonl has the full correct data.
    🔴 2026-08-08 fix: ghost过滤逻辑原本会把所有有持仓价值的币误判为ghost清空
    (if ghost_value > 0 无条件触发)，导致 state/a4.json 显示0持仓/$2.66，
    与AWS实测4持仓/$45.09不符。现在只过滤 qty=0 的明确幽灵仓。
    """
    import json as _json

    nh_path = BASE / 'data' / 'node_history.jsonl'
    if not nh_path.exists():
        print("⚠️ fix_state: node_history.jsonl not found, skipping")
        return

    # Read the last entry
    with open(nh_path) as f:
        lines = [l.strip() for l in f if l.strip()]
    if not lines:
        return
    latest = _json.loads(lines[-1])

    total = latest.get('total', 0)
    usdt = latest.get('usdt', 0)
    holdings_raw = latest.get('holdings', [])

    if not total and not holdings_raw:
        return  # no real data to fix with

    # Build positions list from holdings strings like "NEAR:$39.72"
    # 🔴 2026-08-29 A5修复: ①排除非管理资产(ETH/BNB/WBETH等网格仓, 08-19 ZH规定A4从不管理
    # ——误算会占4仓上限+误导A4认知) ②旧标准val>=1即持仓把$1-5尘仓(NFP$1.25)误算持仓
    # → 改为>=5(MIN_NOTIONAL级), <$5统一归dust
    A4_NON_MANAGED = ('ETH', 'BNB', 'WBETH', 'LDETH', 'LDBNB')
    positions = []
    for h in holdings_raw:
        if ':$' in h:
            coin, val_str = h.split(':$', 1)
            try:
                val = float(val_str)
            except:
                val = 0
            if coin in A4_NON_MANAGED:
                continue
            if val >= 5.0:
                positions.append({"coin": coin, "qty": 0, "entry": 0, "current": 0, "value": val, "pnl_pct": 0})
            # else: <$5为尘仓，统一归下方dust段

    # Build dust list (anything < $5 or not in positions)
    dust = []
    for h in holdings_raw:
        if ':$' in h:
            coin, val_str = h.split(':$', 1)
            try:
                val = float(val_str)
            except:
                val = 0
            if coin in A4_NON_MANAGED:
                continue
            if 0 < val < 5.0:
                dust.append({"coin": coin, "value": val})

    # 🔴 2026-08-08 fix: 不再把所有持仓移入dust。
    # 旧逻辑 `if ghost_value > 0` 会清空所有positions → state/a4.json显示0持仓。
    # 只过滤明确标记 qty=0 的幽灵仓（node_history holdings无qty信息，全部保留）。
    # ghost positions are only those explicitly marked in node data with qty=0 AND value=0
    positions = [p for p in positions if p.get('value', 0) > 0 or p.get('qty', 0) > 0]

    # 🔴 2026-08-08 fix: USDT自由资金优先从Binance API实时获取（socks5模式，同executor.get_usdt_total），
    # 避免 node_history 推导把 locked USDT($89.30)误算为自由资金（141 vs 真实45.09）。
    # 🔴 2026-08-08 fix2: 必须用serverTime校准时间戳——Mac本机时钟比Binance服务器快~2s，
    # 直接用本地时间戳签名会触发 -1021 Timestamp ahead of server time。
    api_free = api_locked = None
    try:
        import hmac as _hmac, hashlib as _hl, time as _time
        auth = read_json('config/auth.json')
        if auth and 'binance' in auth:
            ak = auth['binance']['api_key']
            sec = auth['binance']['api_secret']
            # Step 1: 获取服务器时间
            r0 = subprocess.run(
                ['curl', '--socks5-hostname', '127.0.0.1:1080', '-s', '--max-time', '8',
                 'https://api.binance.com/api/v3/time'],
                capture_output=True, text=True, timeout=12
            )
            if r0.returncode == 0 and r0.stdout.strip():
                st = _json.loads(r0.stdout).get('serverTime')
                ts = int(st) + 500  # 服务器时间 + 半秒缓冲
                q = f"timestamp={ts}&recvWindow=60000"
                sig = _hmac.new(sec.encode(), q.encode(), _hl.sha256).hexdigest()
                url = f"https://api.binance.com/api/v3/account?{q}&signature={sig}"
                r = subprocess.run(
                    ['curl', '--socks5-hostname', '127.0.0.1:1080', '-s', '--max-time', '12',
                     '-H', f'X-MBX-APIKEY: {ak}', url],
                    capture_output=True, text=True, timeout=15
                )
                if r.returncode == 0 and r.stdout.strip():
                    d = _json.loads(r.stdout)
                    usdt_b = next((b for b in d.get('balances', []) if b['asset'] == 'USDT'), None)
                    if usdt_b:
                        api_free = float(usdt_b.get('free', 0))
                        api_locked = float(usdt_b.get('locked', 0))
    except Exception:
        pass

    # Calculate USDT free from total - sum(positions value)
    pos_value = sum(p.get('value', 0) for p in positions)
    if api_free is not None:
        usdt_free = api_free
        usdt_locked = api_locked or 0
        source = "Binance API (socks5 实时)"
    else:
        usdt_free = max(0, total - pos_value)
        usdt_locked = 0
        source = "node_history.jsonl (SSH→AWS→Binance, API不可用时fallback)"

    # Construct state/a4.json
    # 🔴 2026-08-29 A5修复: 补写 active_positions/positions_count —— 原fix_state只写
    # positions数组，覆盖sync_a4_state后A4的持仓上限判断(条件③≤4)失去数据源
    new_state = {
        "data": {
            "positions": positions,
            "active_positions": [p.get('coin') for p in positions],
            "positions_count": len(positions),
            "dust": dust,
            "usdt_balance": {"free": usdt_free, "locked": usdt_locked, "total": usdt_free + usdt_locked},
            "total_equity": total,
            "source": source,
            "updated_at": latest.get('t', '')
        }
    }

    state_path = BASE / 'state' / 'a4.json'
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with open(state_path, 'w') as f:
        _json.dump(new_state, f, indent=2)

    print(f"✅ state/a4.json fixed: total=${total:.2f}, usdt_free=${usdt_free:.2f}, usdt_locked=${usdt_locked:.2f}, {len(positions)} positions, {len(dust)} dust | source={source}")

if __name__ == '__main__':
    main()
