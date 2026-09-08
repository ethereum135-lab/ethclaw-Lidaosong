#!/usr/bin/env python3
"""
涨幅榜覆盖复盘工具 (Top Gainers Coverage Review)
每天抓涨幅榜TOP20 → 逐币核验三关：选币库(A2)→信号评分(A3)→交易执行(A4)

用法:
  python3 tools/gainer_coverage_review.py            # 默认实时抓Binance
  python3 tools/gainer_coverage_review.py --cached   # 用已有data/gainer_coverage.json
  python3 tools/gainer_coverage_review.py --top 30   # 查TOP30
  python3 tools/gainer_coverage_review.py --save     # 保存结果供复盘用

输出:
  data/gainer_coverage.json  (保存的结构化数据)
  stdout  (人类可读报告)
"""

import json, os, subprocess, sys, re, tempfile
from collections import defaultdict
from datetime import datetime, timezone, timedelta

BJT = timezone(timedelta(hours=8))
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POOL_PATH = os.path.join(BASE_DIR, "data", "coin_pool.json")
SIGNALS_PATH = os.path.join(BASE_DIR, "data", "signals.json")
TRADES_PATH = os.path.join(BASE_DIR, "audit", "TRADES.md")
OUTPUT_PATH = os.path.join(BASE_DIR, "data", "gainer_coverage.json")

STABLECOINS = {'USDC','BUSD','DAI','FDUSD','TUSD','USDP','GUSD','PAXG','USD1','USDE','EUR','EURC','GBP','USDG','U'}
EXCLUDE_KEYWORDS = ['UP','DOWN','BULL','BEAR','LUNA','LUNA2','WBETH','STETH']


def now_bjt():
    return datetime.now(BJT)


def today_str():
    return now_bjt().strftime('%Y-%m-%d')


def fetch_binance_gainers_aws(top_n=20):
    """AWS fallback (08-11): SOCKS5大响应(ticker/24hr 1.88MB)稳定失败时,
    AWS直连Binance拉全量+在AWS端预筛选TOP N, 只传回小JSON(~5KB)。
    """
    import base64
    aws_script = (
        "import json, subprocess\n"
        "raw = subprocess.check_output(['curl','-s','--max-time','30',"
        "'https://api.binance.com/api/v3/ticker/24hr'])\n"
        "data = json.loads(raw)\n"
        "STABLE = {'USDC','BUSD','DAI','FDUSD','TUSD','USDP','GUSD','PAXG','USD1','USDE','EUR','EURC','GBP','USDG','U'}\n"
        "EXCL = ('UP','DOWN','BULL','BEAR','LUNA','LUNA2','WBETH','STETH')\n"
        "out = []\n"
        "for t in data:\n"
        "    s = t['symbol']\n"
        "    if not s.endswith('USDT'):\n"
        "        continue\n"
        "    sym = s[:-4]\n"
        "    if sym in STABLE:\n"
        "        continue\n"
        "    if any(k in sym for k in EXCL):\n"
        "        continue\n"
        "    out.append({'symbol': sym, 'change_pct': round(float(t['priceChangePercent']), 2),\n"
        "                'volume_24h': float(t['quoteVolume']), 'price': float(t['lastPrice'])})\n"
        "out.sort(key=lambda x: -x['change_pct'])\n"
        "print(json.dumps(out[:%d]))\n" % top_n
    )
    b64 = base64.b64encode(aws_script.encode()).decode()
    cmd = (
        "echo %s | base64 -d > /tmp/gc_prescreen.py && "
        "python3 /tmp/gc_prescreen.py && rm -f /tmp/gc_prescreen.py"
    ) % b64
    try:
        r = subprocess.run(["ssh", "-o", "ConnectTimeout=10", "web4", cmd],
                           capture_output=True, text=True, timeout=70)
        if r.returncode == 0 and r.stdout.strip().startswith('['):
            return json.loads(r.stdout)
        return {"error": f"AWS fallback failed rc={r.returncode}: {r.stderr.strip()[:200]}"}
    except Exception as e:
        return {"error": f"AWS fallback exception: {e}"}


def fetch_binance_gainers(top_n=20):
    """通过SOCKS5获取Binance 24hr ticker, 返回涨幅TOP N; SOCKS5大响应失败时AWS fallback"""
    url = "https://api.binance.com/api/v3/ticker/24hr"
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as f:
        tmpfile = f.name
    try:
        subprocess.run(
            ["curl", "--socks5-hostname", "127.0.0.1:1080", "--compressed", "-s",
             "--max-time", "60", url],
            stdout=open(tmpfile, 'w'), stderr=subprocess.DEVNULL,
            timeout=65, check=True
        )
        with open(tmpfile) as f:
            all_data = json.load(f)
    except Exception as e:
        if os.path.exists(tmpfile):
            os.unlink(tmpfile)
        print(f"⚠️ SOCKS5大响应失败({str(e)[:80]}), 切换到AWS fallback...")
        return fetch_binance_gainers_aws(top_n)
    finally:
        if os.path.exists(tmpfile):
            os.unlink(tmpfile)

    results = []
    for t in all_data:
        sym_raw = t['symbol']
        if not sym_raw.endswith('USDT'):
            continue
        sym = sym_raw.replace('USDT', '')
        if sym in STABLECOINS:
            continue
        if any(kw in sym for kw in EXCLUDE_KEYWORDS):
            continue
        pct = float(t['priceChangePercent'])
        vol = float(t['quoteVolume'])
        price = float(t['lastPrice'])
        results.append({
            'symbol': sym,
            'change_pct': round(pct, 2),
            'volume_24h': vol,
            'price': price,
        })

    results.sort(key=lambda x: -x['change_pct'])
    return results[:top_n]


def load_coin_pool():
    """加载选币库 (coin_pool.json), 返回 symbol->info dict"""
    if not os.path.exists(POOL_PATH):
        return {}
    try:
        with open(POOL_PATH) as f:
            pool = json.load(f)
        return {c['symbol']: c for c in pool.get('pool', [])}
    except Exception:
        return {}


def load_signals():
    """加载信号评分 (signals.json), 返回 symbol->info dict"""
    if not os.path.exists(SIGNALS_PATH):
        return {}
    try:
        with open(SIGNALS_PATH) as f:
            sig = json.load(f)
        return {r['symbol']: r for r in sig.get('results', [])}
    except Exception:
        return {}


def load_today_trades():
    """从TRADES.md解析今天的交易记录"""
    if not os.path.exists(TRADES_PATH):
        return set(), set()
    today = today_str()
    bought_today = set()
    sold_today = set()
    try:
        with open(TRADES_PATH) as f:
            content = f.read()
        # 匹配各种格式的BUY/SELL行
        for line in content.split('\n'):
            if today not in line:
                continue
            # 匹配 ||| 格式 (A4 Blade)
            m = re.search(r'\|\|\|.*?BUY.*?\|\|\|\s*(\w+)\s*\|', line)
            if m:
                bought_today.add(m.group(1).upper())
                continue
            m = re.search(r'\|\|\|.*?SELL.*?\|\|\|\s*(\w+)\s*\|', line)
            if m:
                sold_today.add(m.group(1).upper())
                continue
            # 匹配旧引擎格式 | 2026-06-03 ... BUY ... SYMBOL |
            m = re.search(r'\|.*?' + re.escape(today) + r'.*?\|\s*BUY\s*\|\s*(\w+)\s*\|', line)
            if m:
                bought_today.add(m.group(1).upper())
                continue
            m = re.search(r'\|.*?' + re.escape(today) + r'.*?\|\s*SELL\s*\|\s*(\w+)\s*\|', line)
            if m:
                sold_today.add(m.group(1).upper())
                continue
        # 也查NODE叙事格式 (A4 narrative)
        for match in re.finditer(rf'({re.escape(today)}.*?)##', content, re.DOTALL):
            today_section = match.group(1)
            for m in re.finditer(r'BUY\s+(\w+)', today_section):
                bought_today.add(m.group(1).upper())
            for m in re.finditer(r'卖.*?(\w+)', today_section):
                sold_today.add(m.group(1).upper())
    except Exception:
        pass
    return bought_today, sold_today


def get_category_pool(pool_coins, gainer_symbol):
    """从coin_pool获取币的赛道"""
    c = pool_coins.get(gainer_symbol, {})
    return c.get('category', '?')


def get_pool_status(pool_coins, gainer_symbol):
    """从coin_pool获取状态"""
    c = pool_coins.get(gainer_symbol, {})
    return c.get('status', '不在池')


def get_signal_info(sig_map, gainer_symbol):
    """从signals获取评分"""
    r = sig_map.get(gainer_symbol)
    if r:
        return {
            'score': r.get('total_score'),
            'level': r.get('level'),
            'gain': r.get('gain_24h'),
        }
    return None


def check_in_pool(pool_coins, symbol):
    """是否在选币库"""
    return symbol in pool_coins


def classify_miss_reason(pool_coins, sig_map, symbol, gainers_map):
    """分类为什么没抓到这个涨幅币"""
    g = gainers_map.get(symbol, {})
    change = g.get('change_pct', 0)
    vol = g.get('volume_24h', 0)
    price = g.get('price', 0)

    reasons = []

    if symbol not in pool_coins:
        reasons.append("不在选币库")
    else:
        status = pool_coins[symbol].get('status', '?')
        if status == 'warning':
            reasons.append(f"状态warning(可能日涨幅仍在旧快照中)")
        elif status == 'removed':
            reasons.append(f"已被排除(removed)")

    if symbol in pool_coins:
        sig = sig_map.get(symbol)
        if not sig:
            reasons.append("无信号评分")
        elif sig.get('level') == 'PASS':
            reasons.append(f"信号评分PASS(score={sig.get('total_score')})")

    # 根据涨幅大小归类
    if change > 30:
        reasons.append(f"🔥 大幅拉升(+{change}%)可能已过高")
    elif change > 15:
        reasons.append(f"⚠️ +{change}% 属较高涨幅，研究能否在+5-10%区间识别")

    # 检查成交量
    if vol < 100000:
        reasons.append(f"成交量低(${vol:.0f})")

    return ' | '.join(reasons) if reasons else '待深入研究'


def run_review(top_n=20, save=False, cached=False):
    """执行涨幅榜覆盖复盘"""
    ts = now_bjt()

    # 1. 获取涨幅数据
    if cached and os.path.exists(OUTPUT_PATH):
        try:
            with open(OUTPUT_PATH) as f:
                prev = json.load(f)
                gainers = prev.get('gainers', [])
                print(f"📂 使用缓存数据 ({prev.get('scanned_at', '?')})")
        except Exception:
            gainers = fetch_binance_gainers(top_n)
    else:
        gainers = fetch_binance_gainers(top_n)

    if isinstance(gainers, dict) and 'error' in gainers:
        print(f"❌ {gainers['error']}")
        return

    # 2. 加载各种数据
    pool_coins = load_coin_pool()
    sig_map = load_signals()
    bought_today, sold_today = load_today_trades()

    # 3. 构建涨幅榜symbol->data映射
    gainers_map = {g['symbol']: g for g in gainers}

    # 4. 逐币分析
    covered = []      # 在池+有信号
    partial = []      # 在池但信号弱/无
    missed = []       # 不在池
    traded = []       # 今日交易过

    for g in gainers:
        sym = g['symbol']
        in_pool = check_in_pool(pool_coins, sym)
        signal_info = get_signal_info(sig_map, sym)
        category = get_category_pool(pool_coins, sym)
        status = get_pool_status(pool_coins, sym)
        miss_reason = classify_miss_reason(pool_coins, sig_map, sym, gainers_map) if not in_pool or (in_pool and not signal_info) else None
        was_traded = sym in bought_today or sym in sold_today

        entry = {
            'rank': gainers.index(g) + 1,
            'symbol': sym,
            'change_pct': g['change_pct'],
            'volume': g['volume_24h'],
            'price': g['price'],
            'in_pool': in_pool,
            'pool_status': status,
            'category': category,
            'signal_score': signal_info['score'] if signal_info else None,
            'signal_level': signal_info['level'] if signal_info else None,
            'traded_today': was_traded,
            'miss_reason': miss_reason,
        }

        if in_pool and signal_info and signal_info['level'] in ('STRONG', 'SIGNAL'):
            covered.append(entry)
        elif in_pool:
            partial.append(entry)
        else:
            missed.append(entry)

        if was_traded:
            traded.append(entry)

    # 5. 计算覆盖率指标
    total = len(gainers)
    total_in_pool = len(covered) + len(partial)
    total_traded = len(traded)
    pool_hit_rate = round(total_in_pool / total * 100, 1) if total else 0
    strong_rate = round(len([c for c in covered if c['signal_level'] == 'STRONG']) / total * 100, 1) if total else 0
    signal_coverage = round(len(covered) / total * 100, 1) if total else 0
    trade_rate = round(total_traded / total * 100, 1) if total else 0

    # 赛道分布
    sector_counts = defaultdict(int)
    for g in gainers:
        cat = get_category_pool(pool_coins, g['symbol'])
        sector_counts[cat] += 1

    # 6. 构建输出
    result = {
        'scanned_at': ts.strftime('%Y-%m-%d %H:%M:%S'),
        'date': today_str(),
        'top_n': top_n,
        'metrics': {
            'total_gainers': total,
            'in_pool': total_in_pool,
            'pool_hit_rate_pct': pool_hit_rate,
            'strong_signals': len([c for c in covered if c['signal_level'] == 'STRONG']),
            'strong_rate_pct': strong_rate,
            'signal_coverage_pct': signal_coverage,
            'traded_today': total_traded,
            'trade_rate_pct': trade_rate,
            'covered': len(covered),
            'partial': len(partial),
            'missed': len(missed),
        },
        'sector_distribution': dict(sector_counts),
        'gainers': gainers,
        'covered': covered,
        'partial': partial,
        'missed': missed,
        'traded': traded,
    }

    if save:
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        with open(OUTPUT_PATH, 'w') as f:
            json.dump(result, f, indent=2)

    # 7. 打印人类可读报告
    print(f"\n{'='*60}")
    print(f"📊 涨幅榜覆盖复盘 | {ts.strftime('%Y-%m-%d %H:%M')} BJT")
    print(f"{'='*60}")
    print(f"涨幅TOP{top_n} | 在池: {total_in_pool}/{total} ({pool_hit_rate}%)")
    print(f"STRONG信号: {len([c for c in covered if c['signal_level'] == 'STRONG'])}/{total} ({strong_rate}%)")
    print(f"今日交易: {total_traded}/{total} ({trade_rate}%)")
    print(f"赛道分布: {', '.join(f'{k}={v}' for k,v in sorted(sector_counts.items(), key=lambda x:-x[1]))}")
    print(f"\n{'='*60}")

    print(f"\n{'─'*60}")
    print(f"🟢 覆盖完整 (在池+有信号) — {len(covered)}个")
    print(f"{'─'*60}")
    if covered:
        print(f"  {'排':>3} {'币':6} {'涨幅':>7} {'评分':>4} {'级别':8} {'赛道':12} {'今日交易':8}")
        print(f"  {'─'*55}")
        for c in sorted(covered, key=lambda x: -x['change_pct']):
            traded_mark = '✅' if c['traded_today'] else '  '
            print(f"  {c['rank']:>3} {c['symbol']:6} +{c['change_pct']:>5.1f}% {c['signal_score'] or 0:>4} {c['signal_level']:8} {c['category']:12} {traded_mark}")
    else:
        print(f"  (无)")

    print(f"\n{'─'*60}")
    print(f"🟡 部分覆盖 (在池但信号弱/无) — {len(partial)}个")
    print(f"{'─'*60}")
    if partial:
        print(f"  {'排':>3} {'币':6} {'涨幅':>7} {'状态':12} {'赛道':12} {'今日交易':8}")
        print(f"  {'─'*55}")
        for p in sorted(partial, key=lambda x: -x['change_pct']):
            traded_mark = '✅' if p['traded_today'] else '  '
            print(f"  {p['rank']:>3} {p['symbol']:6} +{p['change_pct']:>5.1f}% {p['pool_status']:12} {p['category']:12} {traded_mark}")
    else:
        print(f"  (无)")

    print(f"\n{'─'*60}")
    print(f"🔴 遗漏 (不在选币库) — {len(missed)}个")
    print(f"{'─'*60}")
    if missed:
        print(f"  {'排':>3} {'币':8} {'涨幅':>7} {'原因分析'}")
        print(f"  {'─'*55}")
        for m in sorted(missed, key=lambda x: -x['change_pct']):
            reason = (m.get('miss_reason') or '不在池')[:40]
            print(f"  {m['rank']:>3} {m['symbol']:8} +{m['change_pct']:>5.1f}%  {reason}")
    else:
        print(f"  (无)")

    print(f"\n{'═'*60}")
    print(f"📋 A2视角：为什么没选上涨的币？")

    # 逐一分析遗漏原因
    if missed:
        for m in sorted(missed, key=lambda x: -x['change_pct']):
            print(f"  {m['symbol']:6} +{m['change_pct']:>5.1f}% → {m.get('miss_reason', '不在池')}")
    else:
        print(f"  ✅ 所有涨幅榜币都在选币库中")

    print(f"\n📋 A3视角：信号评分覆盖了什么？")
    if partial:
        for p in sorted(partial, key=lambda x: -x['change_pct']):
            print(f"  {p['symbol']:6} +{p['change_pct']:>5.1f}% → 在池{'(status='+p['pool_status']+')'} 但无信号评分")
    else:
        print(f"  ✅ 所有在池币都有信号覆盖")

    print(f"\n📋 A4视角：今天交易了涨幅榜上的币吗？")
    if traded:
        for t in sorted(traded, key=lambda x: -x['change_pct']):
            print(f"  ✅ {t['symbol']:6} +{t['change_pct']:>5.1f}% → 今日有交易")
    else:
        print(f"  ⚠️ 今日涨幅榜币均无交易记录")

    print(f"\n{'═'*60}")

    if save:
        print(f"✅ 已保存: {OUTPUT_PATH}")

    return result


def summarize_to_text(result):
    """生成适合PROFIT_ARCHIVE.md追加的摘要文本"""
    m = result['metrics']
    text = f"""
### 涨幅榜全覆盖复盘 ({result['date']})
| 指标 | 数值 |
|:-----|:----:|
| 涨幅TOP{m['top_n']} | {m['total_gainers']}个 |
| 🟢 在选币库 | {m['in_pool']}/{m['total_gainers']} ({m['pool_hit_rate_pct']}%) |
| 🟢 STRONG信号 | {m['strong_signals']}/{m['total_gainers']} ({m['strong_rate_pct']}%) |
| 🟡 有信号覆盖 | {m['signal_coverage_pct']}% |
| ✅ 今日交易 | {m['traded_today']}/{m['total_gainers']} ({m['trade_rate_pct']}%) |
| 🔴 遗漏 | {m['missed']}个 |
"""
    if result.get('missed'):
        text += f"\n**遗漏分析:**\n"
        for miss in result['missed'][:10]:
            text += f"- {miss['symbol']} (+{miss['change_pct']}%): {miss['miss_reason']}\n"
    return text


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='涨幅榜覆盖复盘工具')
    parser.add_argument('--top', type=int, default=20, help='涨幅榜TOP N (默认20)')
    parser.add_argument('--save', action='store_true', help='保存结果到data/gainer_coverage.json')
    parser.add_argument('--cached', action='store_true', help='使用缓存数据 (不重新抓取)')
    parser.add_argument('--text', action='store_true', help='只输出文本摘要 (供PROFIT_ARCHIVE追加)')
    args = parser.parse_args()

    result = run_review(top_n=args.top, save=args.save, cached=args.cached)
    if args.text and result:
        print("\n\n=== 复盘摘要文本 ===\n")
        print(summarize_to_text(result))
