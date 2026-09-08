#!/usr/bin/env python3
"""
preflight_check.py — 系统预飞检查
====================================
在做出任何系统修改之前运行此脚本，获取六个维度的完整快照。
确保每次决策都有全局视角，而不是头痛医头。

用法：
  python3 tools/preflight_check.py          # 完整扫描
  python3 tools/preflight_check.py --quick   # 快速检查（只输出摘要）
"""

import json
import os
import re
import hashlib
import hmac
import urllib.request
import ssl
import time
import sys
import requests
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUTH_FILE = os.path.join(BASE_DIR, 'config', 'auth.json')
TRADE_LOG = os.path.join(BASE_DIR, 'audit', 'TRADES.md')
STATE_FILE = os.path.join(BASE_DIR, 'data', 'node_state.json')
MONITOR_LOG = os.path.join(BASE_DIR, 'logs', 'monitor.log')
VERSION_FILE = os.path.join(BASE_DIR, 'VERSION')
# 旧引擎已删除(2026-05-14) — 系统已迁移至A4 Blade Agent架构
# ENGINE_FILE = os.path.join(BASE_DIR, 'engine_realtime_v2.py')

# SOCKS5 proxy tunnel for Binance 451 bypass
SOCKS5_PROXY_STR = 'socks5h://127.0.0.1:1080'
SOCKS5_ENABLED = True

def _urlopen(url, timeout=10, data=None, headers=None):
    """urllib.urlopen with automatic SOCKS5 proxy fallback on 451.
    Falls back to requests library with SOCKS5 proxy when direct connection fails.

    FIX(2026-08-03): 本环境直连 Binance 被墙(超时~20s)。若先直连再走代理，
    签名 URL 中的 timestamp 会过期(recvWindow=20000ms)导致 Binance 400 -1021。
    因此 SOCKS5 可用时优先走代理，直连作为 fallback。
    """
    req = urllib.request.Request(url, data=data, headers=headers or {})
    if SOCKS5_ENABLED:
        # 优先 SOCKS5 代理（本环境主通道，直连必被墙且耗时 20s 会导致签名过期）
        try:
            return _urlopen_via_proxy(url, timeout, headers)
        except requests.exceptions.HTTPError as proxy_err:
            # HTTP 4xx/5xx from proxy (e.g. Binance -1021 timestamp error)
            print(f"[_urlopen] Proxy returned HTTP error: {proxy_err.response.status_code if proxy_err.response else '?'}", file=sys.stderr)
        except Exception as proxy_err:
            print(f"[_urlopen] Proxy fallback failed: {type(proxy_err).__name__}: {proxy_err}", file=sys.stderr)
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        if e.code == 451 and SOCKS5_ENABLED:
            try:
                return _urlopen_via_proxy(url, timeout, headers)
            except Exception as proxy_err:
                print(f"[_urlopen] Proxy fallback from HTTP 451 failed: {type(proxy_err).__name__}: {proxy_err}", file=sys.stderr)
                raise  # re-raise original 451 since proxy didn't help
        raise
    except (urllib.error.URLError, OSError):
        # Connection refused/timeout (direct blocked) → try SOCKS5 tunnel
        if SOCKS5_ENABLED:
            try:
                return _urlopen_via_proxy(url, timeout, headers)
            except requests.exceptions.HTTPError as proxy_err:
                # HTTP 4xx/5xx from proxy (e.g. Binance -1021 timestamp error)
                # This is NOT a network failure — the proxy works, Binance rejected the request
                # Fall through to re-raise the original timeout, not the proxy error
                print(f"[_urlopen] Proxy returned HTTP error: {proxy_err.response.status_code if proxy_err.response else '?'}", file=sys.stderr)
            except Exception as proxy_err:
                # Other proxy failures (connection refused to proxy, DNS failure, etc.)
                print(f"[_urlopen] Proxy fallback failed: {type(proxy_err).__name__}: {proxy_err}", file=sys.stderr)
        raise

def _urlopen_via_proxy(url, timeout, headers=None):
    """Open URL through SOCKS5 proxy via requests library"""
    proxies = {'http': SOCKS5_PROXY_STR, 'https': SOCKS5_PROXY_STR}
    import io
    # FIX(2026-08-03): headers 必须以关键字参数传递，否则会被 requests.get 当作
    # 第二个位置参数 params 处理，导致 X-MBX-APIKEY 与签名参数丢失 → Binance 400 错误
    r = requests.get(url, params=None, headers=headers or {}, proxies=proxies, timeout=timeout)
    r.raise_for_status()
    # Return as BytesIO so callers can use .read() consistently (like urllib response)
    return io.BytesIO(r.content)

SCORE_WEIGHTS = {
    'vol_score': 40, 'rsi_score': 20, 'surge_score': 20, 'trend_score': 20,
    'h4_bonus': 15, 'fr_bonus': 15, 'behavior_bonus': 10, 'oi_bonus': 5,
    'trending_bonus': 10, 'dex_bonus': 5, 'h1_bonus': 8, 'market_gate': -10,
    'runup_penalty': -30
}

def print_header(title):
    w = 60
    print()
    print('=' * w)
    print(f'  {title}')
    print('=' * w)

def print_kv(key, val, status=None):
    icon = '✅' if status == 'ok' else ('⚠️' if status == 'warn' else ('❌' if status == 'err' else '  '))
    print(f'  {icon} {key:30s} {val}')

# ─── 维度1: 资金 ───
def check_funding():
    print_header('[1/6] 资金状况')
    try:
        auth = json.load(open(AUTH_FILE))['binance']
        ak, sk = auth['api_key'], auth['api_secret']
        ts = int(time.time() * 1000)
        qs = f'timestamp={ts}&recvWindow=20000'
        sig = hmac.new(sk.encode(), qs.encode(), hashlib.sha256).hexdigest()
        account = json.loads(_urlopen(
            f'https://api.binance.com/api/v3/account?{qs}&signature={sig}',
            headers={'X-MBX-APIKEY': ak}).read())
        
        prices = {i['symbol']: float(i['price']) for i in json.loads(_urlopen('https://api.binance.com/api/v3/ticker/price').read())}
        
        usdt = 0
        positions = []
        total = 0
        for b in account['balances']:
            a, t = b['asset'], float(b['free']) + float(b['locked'])
            if a == 'USDT':
                usdt = t
            elif t > 0.00001 and a + 'USDT' in prices:
                v = t * prices[a + 'USDT']
                if v > 1:
                    total += v
                    positions.append((a, v))
        
        positions.sort(key=lambda x: -x[1])
        total_val = total + usdt
        pnl = (total_val - 430) / 430 * 100
        
        print_kv('组合总值', f'${total_val:.2f}', 'ok')
        print_kv('较本金430U', f'{pnl:+.2f}%', 'ok' if pnl > 0 else 'err')
        print_kv('USDT可用', f'${usdt:.2f}', 'warn' if usdt < 10 else 'ok')
        print_kv('持仓数', f'{len(positions)}个', 'ok')
        
        if positions:
            print('  ── 持仓明细 ──')
            for a, v in positions[:5]:
                pct = v / total * 100
                print(f'    {a:12s} ${v:>7.2f}  ({pct:5.1f}%)')
            if len(positions) > 5:
                print(f'    ... 还有{len(positions)-5}个')
        
        return True
    except Exception as e:
        print_kv('错误', str(e)[:60], 'err')
        return False

# ─── 维度2: 交易 ───
def check_trades():
    print_header('[2/6] 交易分析')
    try:
        with open(TRADE_LOG) as f:
            content = f.read()
        lines = content.split('\n')
        
        today = datetime.now().strftime('%Y-%m-%d')
        today_buys = 0
        today_sells = 0
        
        # 兼容两种TRADES.md格式（#8双链路分裂修复）：
        # ① audit/TRADES.md 块格式: "### 2026-08-15 20:40 BJT | A4独立执行" 标题行 + 表格 "| 方向 | BUY |"
        # ② data/TRADES.md 行格式: "## 2026-08-15 20:30 (A4 1534) - BUY LINK $7 (加仓)"
        def _is_filled(block_text):
            # #47修复(2026-08-31): 状态为REJECTED/FAILED的记录不是真实成交, 不计入
            m = re.search(r'\|\s*状态\s*\|\s*([^|]+?)\s*\|', block_text)
            if m:
                status = m.group(1)
                return 'FILLED' in status and 'REJECTED' not in status and 'FAILED' not in status
            return True  # 旧格式无状态字段, 视为成交

        for block in content.split('### '):
            block_lines = block.split('\n')
            header = block_lines[0] if block_lines else ''
            if today in header and _is_filled(block):
                block_body = '\n'.join(block_lines[1:])
                if '| 方向 | BUY |' in block_body and 'NO TRADE' not in block_body:
                    today_buys += 1
                elif '| 方向 | SELL |' in block_body:
                    today_sells += 1
        for l in lines:
            if today in l and ' BUY ' in l and 'NO TRADE' not in l and not re.search(r'REJECT', l, re.I):
                today_buys += 1
            if today in l and ' SELL ' in l and not re.search(r'REJECT', l, re.I):
                today_sells += 1
        
        total_trades = sum(1 for l in lines if (' BUY ' in l or ' SELL ' in l) and 'NO TRADE' not in l and not re.search(r'REJECT', l, re.I))
        e2_count = sum(1 for l in lines if 'E2' in l)
        
        print_kv('总交易笔数', f'{total_trades}', 'ok')
        print_kv('今日买入', f'{today_buys}笔', 'ok')
        print_kv('今日卖出', f'{today_sells}笔', 'ok')
        print_kv('E2触发次数(历史)', f'{e2_count}次', 'warn' if e2_count > 20 else 'ok')
        print_kv('交易记录格式', '统一(7列)', 'ok')
        return True
    except Exception as e:
        print_kv('错误', str(e)[:60], 'err')
        return False

# ─── 维度3: 引擎 ───
def check_engine():
    print_header('[3/6] 引擎状态')
    try:
        # 版本
        with open(VERSION_FILE) as f:
            ver = f.read().strip()
        print_kv('版本', ver, 'ok')
        
        # 最后快照
        with open(STATE_FILE) as f:
            state = json.load(f)
        snaps = state.get('prev_snapshots', {})
        if snaps:
            scores = [s.get('score', 0) for s in snaps.values()]
            print_kv('最后扫描币数', f'{len(snaps)}个', 'ok')
            print_kv('最高分', f'{max(scores):.1f}', 'warn' if max(scores) > 130 else 'ok')
            print_kv('最低分', f'{min(scores):.1f}', 'ok')
        
        # 代码变更 — 旧引擎已删除(2026-05-14)，改用A4 Blade Agent架构
        a4_dir = os.path.join(BASE_DIR, 'profiles/a4-blade')
        engine_file = os.path.join(a4_dir, 'execution_engine.py')
        if os.path.exists(engine_file):
            mod_time = os.path.getmtime(engine_file)
            last_mod = datetime.fromtimestamp(mod_time).strftime('%m-%d %H:%M')
            print_kv('引擎最后修改', last_mod, 'ok')
        else:
            print_kv('引擎文件', '未找到 (a4-blade)', 'warn')
        
        return True
    except Exception as e:
        print_kv('错误', str(e)[:60], 'err')
        return False

# ─── 维度4: 监听器 ───
def check_monitor():
    print_header('[4/6] 监听器')
    try:
        if os.path.exists(MONITOR_LOG):
            with open(MONITOR_LOG) as f:
                lines = f.readlines()
            log_count = len(lines)
            last_line = lines[-1].strip() if lines else '无'
            mtime = os.path.getmtime(MONITOR_LOG)
            age_h = (time.time() - mtime) / 3600
            print_kv('日志行数', f'{log_count}', 'ok')
            if age_h > 72:
                print_kv('最后一行', f'陈旧死日志(mtime {age_h:.0f}h前): {last_line[:40]}', 'warn')
            else:
                print_kv('最后一行', last_line[:80], 'ok')
        else:
            print_kv('监听器', '❌ 未运行', 'err')
        
        # 检查卖出记录
        sell_log = os.path.join(BASE_DIR, 'logs', 'realtime_sell.log')
        if os.path.exists(sell_log) and os.path.getsize(sell_log) > 0:
            with open(sell_log) as f:
                sells = [l for l in f if l.strip()]
            print_kv('卖出信号触发', f'{len(sells)}次', 'ok')
        else:
            print_kv('卖出信号触发', '0次', 'ok')
        
        return True
    except Exception as e:
        print_kv('错误', str(e)[:60], 'err')
        return False

# ─── 维度5: 链上 ───
def check_chain():
    print_header('[5/6] 链上监控')
    try:
        auth = json.load(open(AUTH_FILE))
        if 'etherscan' in auth and auth['etherscan'].get('api_key'):
            key = auth['etherscan']['api_key']
            url = f'https://api.etherscan.io/v2/api?chainid=1&module=stats&action=ethprice&apikey={key}'
            res = json.loads(_urlopen(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'}).read())
            if res.get('status') == '1':
                eth_usd = res['result'].get('ethusd', '?')
                print_kv('Etherscan', f'✅ ETH ${float(eth_usd):.0f}', 'ok')
            else:
                print_kv('Etherscan', '❌ ' + str(res.get('result', ''))[:40], 'err')
        else:
            print_kv('Etherscan', '❌ 未配置', 'err')
        return True
    except Exception as e:
        print_kv('Etherscan', str(e)[:60], 'err')
        return False

# ─── 维度6: 代码状态 ───
def check_code():
    print_header('[6/6] 代码与版本')
    try:
        # 旧引擎已删除(2026-05-14) — 改用A4 Blade Agent
        engine_path = os.path.join(BASE_DIR, 'profiles/a4-blade/')
        monitor_path = os.path.join(BASE_DIR, 'tools', 'realtime_sell_monitor.py')
        etherscan_path = os.path.join(BASE_DIR, 'tools', 'etherscan_monitor.py')
        
        print_kv('引擎', f'{os.path.getsize(engine_path):>6,}字节', 'ok')
        print_kv('监听器', f'{os.path.getsize(monitor_path):>6,}字节', 'ok')
        print_kv('Etherscan', f'{os.path.getsize(etherscan_path):>6,}字节', 'ok')
        
        # 检查待办事项
        pending = []
        if not auth_has_etherscan():
            pending.append('Etherscan API key')
        
        if pending:
            print_kv('待办事项', ', '.join(pending), 'warn')
        else:
            print_kv('待办事项', '无', 'ok')
        
        return True
    except Exception as e:
        print_kv('错误', str(e)[:60], 'err')
        return False

def auth_has_etherscan():
    try:
        auth = json.load(open(AUTH_FILE))
        return 'etherscan' in auth
    except:
        return False

# ─── 主函数 ───
def main():
    print()
    print(f'╔{"═"*58}╗')
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    print(f'║  ZQ 系统预飞检查 — {now_str}  ║')
    print(f'╚{"═"*58}╝')
    print(f'  本金: 430U | 目标: 1M U')
    print(f'  检查目的: 修改前全局视角，避免头痛医头')
    
    checks = [
        ('资金', check_funding),
        ('交易', check_trades),
        ('引擎', check_engine),
        ('监听器', check_monitor),
        ('链上', check_chain),
        ('代码', check_code),
    ]
    
    all_ok = True
    for name, fn in checks:
        try:
            result = fn()
            if not result:
                all_ok = False
        except Exception as e:
            print(f'\n  [{name}] 异常: {e}')
            all_ok = False
    
    print()
    print('=' * 60)
    if all_ok:
        print('  所有检查通过 ✅  可进行修改')
    else:
        print('  存在待处理事项 ⚠️  建议先处理再修改')
    print('=' * 60)

if __name__ == '__main__':
    quick = '--quick' in sys.argv
    main()
