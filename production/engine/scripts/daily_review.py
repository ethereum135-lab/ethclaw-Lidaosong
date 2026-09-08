#!/usr/bin/env python3
"""
ZH 每日复盘聚合脚本（对ZQ交易系统的复盘）
由cron每天00:00执行：TECH_REVIEWS → DAILY_REVIEW → EXPERIENCE_ARCHIVE
"""
import json, os, re, sys
from datetime import datetime, date
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TECH_REVIEW_PATH = os.path.join(BASE_DIR, "audit", "TECH_REVIEWS.md")
DAILY_REVIEW_PATH = os.path.join(BASE_DIR, "../../audit", "DAILY_REVIEW.md")
EXPERIENCE_ARCHIVE_PATH = os.path.join(BASE_DIR, "../../audit", "EXPERIENCE_ARCHIVE.md")
GAINER_COVERAGE_PATH = os.path.join(BASE_DIR, "../../data", "gainer_coverage.json")

today = date.today()
today_str = today.strftime('%Y-%m-%d')
today_prefix = today.strftime('%Y%m%d')

os.makedirs(os.path.dirname(DAILY_REVIEW_PATH), exist_ok=True)

# ─── 读TECH_REVIEWS ───
reviews = []
if os.path.exists(TECH_REVIEW_PATH):
    with open(TECH_REVIEW_PATH) as f:
        lines = f.readlines()
    for line in lines:
        if line.startswith('| T') and today_prefix in line:
            parts = [p.strip() for p in line.split('|')[1:-1]]
            if len(parts) >= 10:
                reviews.append({
                    'id': parts[0],
                    'time': parts[1],
                    'symbol': parts[2],
                    'entry_price': parts[3],
                    'exit_price': parts[4],
                    'pnl_usdt': parts[5],
                    'pnl_pct': parts[6],
                    'nodes': parts[7],
                    'exit_reason': parts[8],
                    'lesson': parts[9],
                })

# ─── 读取涨幅榜覆盖数据 ───
gainer_metrics = None
gainer_missed_list = []
if os.path.exists(GAINER_COVERAGE_PATH):
    try:
        with open(GAINER_COVERAGE_PATH) as f:
            gc = json.load(f)
        gm = gc.get('metrics', {})
        gainer_metrics = {
            'pool_hit_rate_pct': gm.get('pool_hit_rate_pct', 0),
            'strong_rate_pct': gm.get('strong_rate_pct', 0),
            'signal_coverage_pct': gm.get('signal_coverage_pct', 0),
            'trade_rate_pct': gm.get('trade_rate_pct', 0),
            'missed': gm.get('missed', 0),
        }
        for m in gc.get('missed', []):
            gainer_missed_list.append({
                'symbol': m['symbol'],
                'change_pct': m['change_pct'],
                'reason': m.get('miss_reason', '不在池'),
            })
    except Exception as e:
        print(f"⚠️ 读取gainer_coverage.json失败: {e}")

# ─── 统计数据 ───
total = len(reviews)
wins = [r for r in reviews if not r['pnl_usdt'].startswith('$-')]
losses = [r for r in reviews if r['pnl_usdt'].startswith('$-')]
win_rate = len(wins) / total * 100 if total > 0 else 0

total_pnl = 0
for r in reviews:
    try:
        total_pnl += float(r['pnl_usdt'].replace('$', ''))
    except:
        pass

exit_reasons = {}
for r in reviews:
    for code in ['E1', 'E2', 'E3', 'E4', 'E5', 'E6']:
        if code in r['exit_reason']:
            exit_reasons[code] = exit_reasons.get(code, 0) + 1

# 经验教训去重
seen_lessons = set()
if os.path.exists(EXPERIENCE_ARCHIVE_PATH):
    with open(EXPERIENCE_ARCHIVE_PATH) as f:
        seen_lessons = set(line.strip() for line in f if line.startswith('**内容：'))

new_lessons = []
for r in reviews:
    lesson = r['lesson'].strip()
    if lesson and lesson not in seen_lessons:
        new_lessons.append(lesson)
        seen_lessons.add(lesson)

# ─── 写入DAILY_REVIEW ───
review_section = f"""
## {today_str} 每日复盘

### 交易统计
| 指标 | 数值 |
|:---|:---:|
| 交易笔数 | {total} |
| 盈利笔数 | {len(wins)} |
| 亏损笔数 | {len(losses)} |
| 胜率 | {win_rate:.1f}% |
| 总盈亏 | ${total_pnl:+.2f} |
"""

if exit_reasons:
    review_section += """
### 出场原因分布
| 原因 | 次数 |
|:---|:---:|
"""
    for code in sorted(exit_reasons.keys()):
        cnt = exit_reasons[code]
        review_section += f"| {code} | {cnt} |\n"

# ─── 涨幅榜覆盖复盘 ───
if gainer_metrics:
    review_section += """
### 涨幅榜覆盖复盘
| 指标 | 数值 |
|:---|:---:|
| 涨幅榜在池率 | {pool_hit}% |
| STRONG信号率 | {strong}% |
| 信号覆盖率 | {signal_cov}% |
| 今日交易率 | {trade_rate}% |
| 遗漏币种 | {missed}个 |
""".format(
        pool_hit=gainer_metrics['pool_hit_rate_pct'],
        strong=gainer_metrics['strong_rate_pct'],
        signal_cov=gainer_metrics['signal_coverage_pct'],
        trade_rate=gainer_metrics['trade_rate_pct'],
        missed=gainer_metrics['missed'],
    )
    if gainer_missed_list:
        review_section += "\n**遗漏分析：**\n"
        for m in gainer_missed_list[:5]:
            review_section += f"- {m['symbol']} (+{m['change_pct']}%): {m['reason'][:50]}\n"

review_section += """
### 逐笔复盘
| 复盘ID | 币种 | 盈亏 | 持有节点 | 出场原因 | 经验教训 |
|:---|:---|:---:|:---:|:---|---:|
"""

for r in reviews:
    review_section += f"| {r['id']} | {r['symbol']} | {r['pnl_usdt']} | {r['nodes']} | {r['exit_reason'][:30]} | {r['lesson'][:50]} |\n"

# 追加或新建
if os.path.exists(DAILY_REVIEW_PATH):
    mode = 'a'
else:
    mode = 'w'
    review_section = f"# ZH 每日复盘 — ZQ系统复盘\n\n自动生成的每日交易复盘汇总（ZH对ZQ系统的复盘）。\n\n---\n{review_section}"

with open(DAILY_REVIEW_PATH, mode) as f:
    f.write(review_section)

print(f"✅ DAILY_REVIEW更新完成 ({today_str})")

# ─── 更新EXPERIENCE_ARCHIVE ───
if new_lessons:
    existing = []
    if os.path.exists(EXPERIENCE_ARCHIVE_PATH):
        with open(EXPERIENCE_ARCHIVE_PATH) as f:
            existing = f.readlines()

    # 找到最后一个经验编号
    last_num = 0
    for line in existing:
        m = re.search(r'经验 #(\d+)', line)
        if m:
            last_num = max(last_num, int(m.group(1)))

    with open(EXPERIENCE_ARCHIVE_PATH, 'a') as f:
        for lesson in new_lessons:
            last_num += 1
            f.write(f"""
### 经验 #{last_num:03d} — {lesson[:60]}
**来源：** {today_str} 技术复盘
**内容：** {lesson}
**证据：** 来自当日交易复盘数据
**验证状态：** ⚠️ 待验证
""")
    print(f"✅ EXPERIENCE_ARCHIVE新增 {len(new_lessons)} 条经验")
else:
    print("ℹ️ 无新增经验")

print(f"\n{'='*40}")
print(f"  复盘完成 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{'='*40}")
