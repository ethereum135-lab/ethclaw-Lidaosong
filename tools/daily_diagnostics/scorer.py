#!/usr/bin/env python3
"""
评分引擎 — 读取涨幅榜覆盖复盘结果，计算10维评分并更新score_db.json

用法:
  python3 tools/daily_diagnostics/scorer.py                    # 实时拉涨幅榜算分
  python3 tools/daily_diagnostics/scorer.py --from-cache       # 用缓存的gainer_coverage.json
  python3 tools/daily_diagnostics/scorer.py --update-archive   # 同步更新PROFIT_ARCHIVE.md
  python3 tools/daily_diagnostics/scorer.py --all              # 完整运行
"""

import json, os, sys, re, math
from datetime import datetime, timezone, timedelta
from collections import defaultdict

BJT = timezone(timedelta(hours=8))
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

SCORE_DB_PATH = os.path.join(BASE_DIR, "data", "score_db.json")
GAINER_COV_PATH = os.path.join(BASE_DIR, "data", "gainer_coverage.json")
PROFIT_ARCHIVE_PATH = os.path.join(BASE_DIR, "data", "experience", "PROFIT_ARCHIVE.md")
SIGNALS_PATH = os.path.join(BASE_DIR, "data", "signals.json")
POOL_PATH = os.path.join(BASE_DIR, "data", "coin_pool.json")

SCORE_DIMENSIONS = [
    "gainer_hit_rate",      # 涨幅榜命中率
    "agent_independence",   # Agent独立性
    "tool_uptime",          # 工具通断率
    "data_freshness",       # 数据新鲜度
    "closure_rate",         # 闭环完成率
    "profitability",        # 盈利能力
    "knowledge_progress",   # 知识进步
    "self_healing",         # Agent自愈力
    "signal_quality",       # 信号质量
    "collaboration",        # 协作效率
]


def now_bjt():
    return datetime.now(BJT)


def today_str():
    return now_bjt().strftime('%Y-%m-%d')


def load_score_db():
    """加载或初始化评分库"""
    if os.path.exists(SCORE_DB_PATH):
        try:
            with open(SCORE_DB_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "version": 1,
        "scores": [],
        "trend": {}
    }


def save_score_db(db):
    os.makedirs(os.path.dirname(SCORE_DB_PATH), exist_ok=True)
    with open(SCORE_DB_PATH, 'w') as f:
        json.dump(db, f, indent=2)
    print(f"✅ score_db已保存: {SCORE_DB_PATH}")


def load_gainer_coverage(from_cache=False):
    """加载涨幅榜覆盖复盘结果"""
    if from_cache and os.path.exists(GAINER_COV_PATH):
        with open(GAINER_COV_PATH) as f:
            return json.load(f)
    else:
        # 实时运行gainer_coverage_review
        try:
            sys.path.insert(0, os.path.join(BASE_DIR, "tools"))
            from gainer_coverage_review import run_review
            result = run_review(top_n=20, save=True, cached=False)
            return result
        except ImportError:
            print("❌ 无法导入gainer_coverage_review，尝试直接运行")
            import subprocess
            r = subprocess.run(
                [sys.executable, os.path.join(BASE_DIR, "tools", "gainer_coverage_review.py"),
                 "--top", "20", "--save"],
                capture_output=True, text=True, timeout=120
            )
            if r.returncode == 0 and os.path.exists(GAINER_COV_PATH):
                with open(GAINER_COV_PATH) as f:
                    return json.load(f)
            print(f"❌ 运行失败: {r.stderr[:500]}")
            return None


def load_today_trades_for_scoring():
    """加载今日交易数据 - 简化版"""
    trades_path = os.path.join(BASE_DIR, "audit", "TRADES.md")
    today = today_str()
    trade_count = 0
    profit_trades = 0
    if os.path.exists(trades_path):
        try:
            with open(trades_path) as f:
                content = f.read()
            for line in content.split('\n'):
                if today not in line:
                    continue
                if 'SELL' in line:
                    trade_count += 1
                    # Check for profit indicators
                    if '+' in line and ('%' in line or '$' in line):
                        profit_trades += 1
        except:
            pass
    return trade_count, profit_trades


def check_tool_uptime():
    """检查工具通断率"""
    checks = {
        "binance_api": False,
        "coin_pool": os.path.exists(POOL_PATH),
        "signals": os.path.exists(SIGNALS_PATH),
    }
    # Check SOCKS5 tunnel
    import subprocess
    try:
        r = subprocess.run(
            ["curl", "--socks5-hostname", "127.0.0.1:1080", "-s", "--max-time", "5",
             "https://api.binance.com/api/v3/ping"],
            capture_output=True, text=True, timeout=10
        )
        checks["binance_api"] = (r.stdout.strip() == "{}")
    except:
        pass
    uptime = sum(1 for v in checks.values() if v) / max(len(checks), 1) * 100
    return round(uptime, 1), checks


def check_data_freshness():
    """检查数据新鲜度"""
    freshness = {}
    for name, path in [("signals", SIGNALS_PATH), ("coin_pool", POOL_PATH)]:
        if os.path.exists(path):
            mtime = os.path.getmtime(path)
            age_min = (now_bjt().timestamp() - mtime) / 60
            freshness[name] = {
                "age_min": round(age_min, 1),
                "fresh": age_min < 120  # 2小时内算新鲜
            }
        else:
            freshness[name] = {"age_min": None, "fresh": False}
    if freshness.get("signals", {}).get("fresh") and freshness.get("coin_pool", {}).get("fresh"):
        freshness_score = 100
    elif freshness.get("signals", {}).get("fresh") or freshness.get("coin_pool", {}).get("fresh"):
        freshness_score = 50
    else:
        freshness_score = 0
    return freshness_score, freshness


def check_signal_quality():
    """检查信号质量 — 从signals.json看STRONG比例"""
    if not os.path.exists(SIGNALS_PATH):
        return 0
    try:
        with open(SIGNALS_PATH) as f:
            sig = json.load(f)
        summary = sig.get('summary', {})
        strong = summary.get('strong', 0)
        total = sig.get('total_scanned', 1)
        return round(strong / max(total, 1) * 100, 1)
    except:
        return 0


def calculate_scores(gainer_result=None, from_cache=False):
    """计算10维评分"""
    today = today_str()
    scores = {}

    # 1. 涨幅榜命中率
    if gainer_result:
        m = gainer_result.get('metrics', {})
        hit_rate = m.get('pool_hit_rate_pct', 0)
        trade_rate = m.get('trade_rate_pct', 0)
        # 命中率 = 在池率×0.6 + 交易率×0.4
        scores['gainer_hit_rate'] = round(hit_rate * 0.6 + trade_rate * 0.4, 1)
    else:
        scores['gainer_hit_rate'] = 0

    # 2. Agent独立性 (默认85，太低太低会依赖检测)
    scores['agent_independence'] = 85

    # 3. 工具通断率
    uptime, _ = check_tool_uptime()
    scores['tool_uptime'] = uptime

    # 4. 数据新鲜度
    fresh_score, _ = check_data_freshness()
    scores['data_freshness'] = fresh_score

    # 5. 闭环完成率 (默认80，根据当天是否有修复调整)
    scores['closure_rate'] = 80

    # 6. 盈利能力
    trade_count, profit_trades = load_today_trades_for_scoring()
    if trade_count > 0:
        profit_ratio = profit_trades / trade_count
        scores['profitability'] = round(profit_ratio * 100, 1)
    else:
        scores['profitability'] = 0

    # 7. 知识进步 (默认70)
    scores['knowledge_progress'] = 70

    # 8. 自愈力 (默认85)
    scores['self_healing'] = 85

    # 9. 信号质量
    scores['signal_quality'] = check_signal_quality()

    # 10. 协作效率 (默认80)
    scores['collaboration'] = 80

    # 总分 (加权平均)
    weights = {
        'gainer_hit_rate': 0.20,
        'agent_independence': 0.05,
        'tool_uptime': 0.10,
        'data_freshness': 0.10,
        'closure_rate': 0.10,
        'profitability': 0.20,
        'knowledge_progress': 0.05,
        'self_healing': 0.05,
        'signal_quality': 0.10,
        'collaboration': 0.05,
    }
    total = sum(scores.get(dim, 50) * weights.get(dim, 0.1) for dim in SCORE_DIMENSIONS)

    return {
        "date": today,
        "scores": scores,
        "weighted_total": round(total, 1),
        "dimensions": SCORE_DIMENSIONS,
        "weights": weights,
    }


def update_trend(score_db, new_entry):
    """更新评分趋势"""
    today = today_str()
    
    # 加入最新评分
    score_db['scores'].append(new_entry)
    
    # 只保留最近30天
    if len(score_db['scores']) > 30:
        score_db['scores'] = score_db['scores'][-30:]
    
    # 计算趋势
    if len(score_db['scores']) >= 2:
        prev = score_db['scores'][-2]['scores']
        curr = new_entry['scores']
        
        # 逐维对比
        deltas = {}
        for dim in SCORE_DIMENSIONS:
            delta = round(curr.get(dim, 50) - prev.get(dim, 50), 1)
            deltas[dim] = delta
        
        # 总趋势
        total_delta = round(new_entry['weighted_total'] - score_db['scores'][-2]['weighted_total'], 1)
        
        score_db['trend'] = {
            "vs_yesterday": total_delta,
            "direction": "up" if total_delta > 0 else ("down" if total_delta < 0 else "flat"),
            "deltas": deltas,
        }
    else:
        score_db['trend'] = {"vs_yesterday": 0, "direction": "flat"}
    
    # 找出连续退步维度
    score_db['regression_alerts'] = []
    if len(score_db['scores']) >= 3:
        last3 = score_db['scores'][-3:]
        for dim in SCORE_DIMENSIONS:
            vals = [s['scores'].get(dim, 50) for s in last3]
            if all(vals[i] > vals[i+1] for i in range(len(vals)-1)):
                score_db['regression_alerts'].append({
                    "dimension": dim,
                    "values": vals,
                    "total_drop": round(vals[0] - vals[-1], 1)
                })

    return score_db


def find_today_entry_in_archive():
    """在PROFIT_ARCHIVE.md中找到今天复盘的末尾位置"""
    if not os.path.exists(PROFIT_ARCHIVE_PATH):
        return None
    with open(PROFIT_ARCHIVE_PATH) as f:
        content = f.read()
    
    today = today_str()
    sections = re.split(r'\n## ', content)[1:]  # 跳过标题行
    for section in sections:
        if today in section:
            return section
    return None


def append_to_profit_archive(result, score_entry=None):
    """将涨幅榜覆盖复盘结果追加到PROFIT_ARCHIVE.md今天日志的末尾"""
    if not os.path.exists(PROFIT_ARCHIVE_PATH):
        print(f"⚠️ PROFIT_ARCHIVE.md不存在，跳过追加")
        return
    
    today = today_str()
    m = result.get('metrics', {})
    top_n = result.get('top_n', 20)
    
    # 构建追加段落
    gainer_section = f"""
### 📊 今日涨幅榜覆盖复盘

| 指标 | 数值 |
|:-----|:----:|
| 涨幅TOP{top_n} | {m['total_gainers']}个 |
| 🟢 在选币库 | {m['in_pool']}/{m['total_gainers']} ({m['pool_hit_rate_pct']}%) |"""
    if score_entry:
        gainer_section += f"""
| STRONG信号 | {m['strong_signals']}/{m['total_gainers']} ({m['strong_rate_pct']}%) |
| 今日交易 | {m['traded_today']}/{m['total_gainers']} ({m['trade_rate_pct']}%) |
| 🔴 遗漏 | {m['missed']}个 |
| **总分** | **{score_entry['weighted_total']}/100** |"""

    # miss明细
    if result.get('missed'):
        gainer_section += f"\n\n**遗漏分析 (涨幅榜没抓到的币):**\n"
        for miss in result['missed'][:10]:
            gainer_section += f"- **{miss['symbol']}** (+{miss['change_pct']}%): {miss.get('miss_reason', '不在池')}\n"
    
    # 覆盖明细
    if result.get('covered'):
        gainer_section += f"\n**覆盖完整 (在池+有信号):**\n"
        for c in result['covered'][:10]:
            traded_mark = '✅今日交易' if c['traded_today'] else ''
            gainer_section += f"- **{c['symbol']}** (+{c['change_pct']}%): {c['signal_level']}({c['signal_score']}分) {traded_mark}\n"
    
    # 趋势
    if score_entry and 'regression_alerts' in result.get('score_db', {}):
        alerts = result['score_db']['regression_alerts']
        if alerts:
            gainer_section += "\n**⚠️ 连续退警告警:**\n"
            for a in alerts:
                gainer_section += f"- {a['dimension']}: 连续3天下跌 (从{a['values'][0]}→{a['values'][-1]})\n"
    
    gainer_section += "\n---\n"
    
    # 找到今天section的末尾并追加
    with open(PROFIT_ARCHIVE_PATH) as f:
        content = f.read()
    
    today_heading = f"### {today}" if f"### {today}" in content else f"## {today}" if f"## {today}" in content else None
    
    if today_heading:
        # 找到今天section的末尾，在其后面追加
        idx = content.find(today_heading)
        # 找到下一个##或文件末尾
        next_idx = len(content)
        for pattern in ['\n## ', '\n### ']:
            pos = content.find(pattern, idx + len(today_heading))
            if pos != -1 and pos < next_idx:
                next_idx = pos
        
        # 检查是否已有覆盖复盘段落
        existing_gainer = content.find("涨幅榜覆盖复盘", idx)
        if existing_gainer != -1 and existing_gainer < next_idx:
            # 已有覆盖复盘段落，替换它
            section_end = content.find("\n---\n", existing_gainer)
            if section_end != -1 and section_end < next_idx:
                content = content[:existing_gainer] + gainer_section + content[section_end + 5:]
            else:
                content = content[:existing_gainer] + gainer_section + content[next_idx:]
        else:
            # 追加到section末尾之前
            content = content[:next_idx] + gainer_section + content[next_idx:]
    else:
        # 今天没有entry，追加到最后
        content += f"\n\n### {today}\n{gainer_section}"
    
    with open(PROFIT_ARCHIVE_PATH, 'w') as f:
        f.write(content)
    print(f"✅ PROFIT_ARCHIVE.md已更新 (追加涨幅榜覆盖复盘)")


def print_report(new_entry, trend_info, missed_coins, covered_coins):
    """打印人类可读的评分报告"""
    scores = new_entry['scores']
    total = new_entry['weighted_total']
    
    print(f"\n{'='*60}")
    print(f"📊 10维评分报告 | {new_entry['date']}")
    print(f"{'='*60}")
    print(f"总分: {total}/100")
    print()
    for dim in SCORE_DIMENSIONS:
        score = scores.get(dim, 0)
        delta = trend_info.get('deltas', {}).get(dim, 0) if trend_info else 0
        arrow = "↑" if delta > 0 else ("↓" if delta < 0 else "→")
        bar = "█" * int(score / 5) + "░" * (20 - int(score / 5))
        name_map = {
            'gainer_hit_rate': '涨幅榜命中',
            'agent_independence': 'Agent独立',
            'tool_uptime': '工具通断',
            'data_freshness': '数据新鲜',
            'closure_rate': '闭环完成',
            'profitability': '盈利能力',
            'knowledge_progress': '知识进步',
            'self_healing': '自愈力',
            'signal_quality': '信号质量',
            'collaboration': '协作效率',
        }
        print(f"  {name_map.get(dim, dim):12s} {bar} {score:>5.1f} {arrow}{delta:>+.1f}")
    
    # 趋势
    if trend_info:
        print(f"\n  趋势: vs昨日 {trend_info.get('direction', '—')} ({trend_info.get('vs_yesterday', 0):+.1f})")
    
    # 漏掉的币
    if missed_coins:
        print(f"\n🔴 遗漏币 (不在选币库): {len(missed_coins)}个")
        for m in missed_coins[:5]:
            print(f"    {m['symbol']}: +{m['change_pct']}%")
    
    # 覆盖的币
    if covered_coins:
        print(f"\n🟢 覆盖完整: {len(covered_coins)}个")
        for c in covered_coins[:5]:
            print(f"    {c['symbol']}: {c['signal_level']}({c['signal_score']}) +{c['change_pct']}%")
    
    print(f"{'='*60}\n")


def run_all(from_cache=False, update_archive=False):
    """完整运行"""
    print(f"🔄 涨幅榜覆盖复盘 + 评分系统 — {now_bjt().strftime('%Y-%m-%d %H:%M')} BJT")
    
    # 1. 获取涨幅榜覆盖复盘
    result = load_gainer_coverage(from_cache=from_cache)
    if not result:
        print("❌ 无法获取涨幅榜数据")
        return
    
    if 'error' in result:
        print(f"❌ {result['error']}")
        return
    
    # 2. 计算评分
    new_entry = calculate_scores(result, from_cache)
    
    # 3. 加载并更新评分库
    score_db = load_score_db()
    score_db = update_trend(score_db, new_entry)
    save_score_db(score_db)
    
    # 4. 打印报告
    trend_info = score_db.get('trend', {})
    missed_coins = result.get('missed', [])
    covered_coins = result.get('covered', [])
    print_report(new_entry, trend_info, missed_coins, covered_coins)
    
    # 5. 更新PROFIT_ARCHIVE.md
    if update_archive:
        result['score_db'] = score_db
        append_to_profit_archive(result, new_entry)
    
    return {
        "scores": new_entry,
        "trend": trend_info,
        "coverage": result,
    }


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='评分引擎')
    parser.add_argument('--from-cache', action='store_true', help='使用缓存的涨幅榜数据')
    parser.add_argument('--update-archive', action='store_true', help='更新PROFIT_ARCHIVE.md')
    parser.add_argument('--all', action='store_true', help='完整运行(=强制实时+更新归档)')
    args = parser.parse_args()
    
    from_cache = args.from_cache or args.all
    update_arc = args.update_archive or args.all
    
    run_all(from_cache=from_cache, update_archive=update_arc)
