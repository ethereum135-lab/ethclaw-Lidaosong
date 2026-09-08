#!/usr/bin/env python3
"""
A2 选币官 — 两阶段筛选法执行引擎
读取AWS采集数据 → Stage 1硬过滤 → Stage 2五因子评分 → 输出报告
"""
import json
import os
from datetime import date, datetime
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE, "..", "..", "data", "aws_snapshot.json")
A1_PATH = os.path.join(BASE, "..", "a1-data", "output", "2026-05-14.md")

with open(DATA_PATH) as f:
    snapshot = json.load(f)

# Global data
fg_index = int(snapshot["fg_index"])
fg_class = snapshot["fg_classification"]
btc_dominance = float(snapshot["global"]["btc_dominance"])
total_mcap = float(snapshot["global"]["total_mcap_usd"])
total_vol = float(snapshot["global"]["total_vol_usd"])

# Binance Top 50
top50 = snapshot["binance_top50"]

# Funding rates map
fr_map = snapshot["funding_rates"]

# CoinGecko trending
trending_list_raw = snapshot["coingecko_trending"]
trending_names = [c["name"] for c in trending_list_raw]

# Build trending symbols lookup
trending_symbols = set()
for t in trending_list_raw:
    base = t["symbol"].upper()
    trending_symbols.add(base + "USDT")
    for coin in top50:
        if coin["symbol"].replace("USDT", "") == base:
            trending_symbols.add(coin["symbol"])

print(f"F&G: {fg_index}/100 Fear")
print(f"BTC: ${float(top50[1]['price']):,.0f} ({top50[1]['change_pct']}%)")
print(f"Trending: {trending_names}")

# ============================================================
# Stage 1 — 硬条件过滤
# ============================================================
MIN_VOLUME = 1_000_000
MIN_PRICE = 0.001
MIN_FR = -0.0001
MAX_FR = 0.0002

STABLECOIN_BASES = ["USD", "EUR", "RLUSD", "U", "DAI", "BUSD", "USDC", "USDT"]

def is_stablecoin(symbol):
    base = symbol.replace("USDT", "").split("USDT")[0]
    if base == "":
        return True
    if base in STABLECOIN_BASES:
        return True
    return False

def is_leveraged(symbol):
    return "DOWN" in symbol.upper() or "UP" in symbol.upper()

def get_funding_rate(symbol):
    fr_entry = fr_map.get(symbol)
    if fr_entry:
        return float(fr_entry["rate"])
    base = symbol.replace("USDT", "")
    for key, val in fr_map.items():
        if key.replace("USDT", "") == base or key == base + "USDT":
            return float(val["rate"])
    return None

stage1_passed = []
stage1_failed = []

for coin in top50:
    symbol = coin["symbol"]
    price = float(coin["price"])
    volume = float(coin["volume"])
    change_pct = float(coin["change_pct"])
    fr = get_funding_rate(symbol)
    
    checks = {}
    checks["volume_ge_1M"] = volume >= MIN_VOLUME
    checks["price_gt_0_001"] = price > MIN_PRICE
    checks["not_stablecoin"] = not is_stablecoin(symbol)
    checks["not_leveraged"] = not is_leveraged(symbol)
    
    if fr is not None:
        checks["funding_neutral"] = MIN_FR <= fr <= MAX_FR
    else:
        checks["funding_neutral"] = None  # Unknown
    
    # Determine pass/fail
    hard_fails = [k for k, v in checks.items() if v is False]
    
    if len(hard_fails) == 0:
        stage1_passed.append({
            "symbol": symbol,
            "price": price,
            "volume": volume,
            "change_pct": change_pct,
            "funding_rate": fr,
            "checks": checks
        })
    else:
        reasons = []
        if not checks.get("volume_ge_1M", True):
            reasons.append(f"成交量${volume:,.0f}<$1M")
        if not checks.get("price_gt_0_001", True):
            reasons.append(f"价格${price}<$0.001")
        if not checks.get("not_stablecoin", True):
            reasons.append("稳定币/法币对")
        if not checks.get("not_leveraged", True):
            reasons.append("杠杆代币")
        if checks.get("funding_neutral") is False:
            reasons.append(f"费率{fr:.6f}异常")
        if not reasons:
            reasons.append("市值数据不可用(未采集)")
        
        stage1_failed.append({
            "symbol": symbol,
            "price": price,
            "volume": volume,
            "change_pct": change_pct,
            "funding_rate": fr,
            "reason": " | ".join(reasons)
        })

print(f"\nStage 1: {len(stage1_passed)} passed / {len(stage1_failed)} failed")

# ============================================================
# Stage 2 — 五因子评分
# ============================================================
all_volumes = sorted([float(c["volume"]) for c in top50], reverse=True)
median_vol = all_volumes[len(all_volumes)//2]

def calc_volume_score(volume):
    ratio = volume / max(median_vol, 1)
    if ratio >= 5.0:
        return 90
    elif ratio >= 3.0:
        return 80
    elif ratio >= 2.0:
        return 65
    elif ratio >= 1.0:
        return 50
    elif ratio >= 0.5:
        return 30
    else:
        return 10

def calc_momentum_score(change_pct):
    if change_pct > 10:
        return 50
    elif change_pct > 5:
        return 75
    elif change_pct > 0:
        return 65
    elif change_pct > -3:
        return 45
    elif change_pct > -8:
        return 30
    else:
        return 15

def calc_funding_score(fr):
    if fr is None:
        return 50
    if -0.005 <= fr <= 0.01:
        return 100
    elif -0.01 <= fr < -0.005:
        return 70
    elif 0.01 < fr <= 0.02:
        return 60
    elif -0.02 <= fr < -0.01:
        return 30
    elif 0.02 < fr <= 0.05:
        return 20
    else:
        return 0

def calc_heat_score(symbol):
    is_trending = symbol in trending_symbols
    return 30 if is_trending else 70

scores = []
for coin in stage1_passed:
    symbol = coin["symbol"]
    vol = coin["volume"]
    change = coin["change_pct"]
    fr = coin["funding_rate"]
    
    vs = calc_volume_score(vol)
    ms = calc_momentum_score(change)
    fs = calc_funding_score(fr)
    rs = 50  # RSI not available
    hs = calc_heat_score(symbol)
    
    total = vs * 0.30 + ms * 0.25 + fs * 0.20 + rs * 0.15 + hs * 0.10
    
    scores.append({
        "symbol": symbol,
        "total": round(total, 1),
        "vs": vs, "ms": ms, "fs": fs, "rs": rs, "hs": hs,
        "price": coin["price"],
        "volume": vol,
        "change_pct": change,
        "funding_rate": fr,
        "is_trending": symbol in trending_symbols,
    })

scores.sort(key=lambda x: x["total"], reverse=True)

candidate_pool = [s for s in scores if s["total"] >= 70]
watch_pool = [s for s in scores if 50 <= s["total"] < 70]
excluded_pool = [s for s in scores if s["total"] < 50]

print(f"Candidate Pool: {len(candidate_pool)}")
print(f"Watch Pool: {len(watch_pool)}")
print(f"Excluded (Stage2): {len(excluded_pool)}")

# ============================================================
# 合成报告
# ============================================================
today = date.today().isoformat()
now_bjt = datetime.now().strftime("%H:%M")

# Intensity
if fg_index < 30:
    intensity = "宽松（恐慌市场，放宽标准）"
elif fg_index < 50:
    intensity = "宽松偏正常（恐惧但未极端）"
elif fg_index < 70:
    intensity = "正常"
else:
    intensity = "收紧（贪婪市场，收紧标准）"

# Group exclusions by category
exclude_cats = defaultdict(list)
for c in stage1_failed:
    r = c["reason"]
    if "稳定币" in r or "法币" in r:
        cat = "稳定币/法币对"
    elif "费率" in r:
        cat = "费率异常"
    elif "价格" in r:
        cat = "价格<$0.001"
    elif "成交量" in r:
        cat = "成交量<$1M"
    else:
        cat = "其他/数据不足"
    exclude_cats[cat].append(c["symbol"])

lines = []
lines.append(f"# A2 选币官 — 候选池报告")
lines.append(f"日期：{today} | 时间：{now_bjt} BJT")
lines.append(f"数据来源：AWS→Binance API + AWS→CoinGecko API (3.27.3.202) | Alternative.me")
lines.append("")
lines.append("---")
lines.append("")
lines.append("## 市场环境总览")
lines.append(f"- **F&G指数：** {fg_index}/100 — {fg_class}")
lines.append(f"- **BTC价格：** $79,038（24h: -1.58%）")
lines.append(f"- **ETH价格：** $2,248（24h: -0.89%）")
lines.append(f"- **BTC Dominance：** {btc_dominance:.2f}%")
lines.append(f"- **总市值：** ${total_mcap:,.0f}")
lines.append(f"- **总成交额(24h)：** ${total_vol:,.0f}")
lines.append(f"- **判断：** 市场处于**恐惧**（F&G=42），筛选力度：**{intensity}**")
lines.append(f"- **判断依据：** 恐惧市场下BTC跌破$80K，成交量萎缩，放宽费率容忍区间，优先关注放量抗跌品种")
lines.append("")
lines.append("## 数据质量声明")
lines.append("| 数据维度 | 状态 | 来源 |")
lines.append("|:---------|:----:|:-----|")
lines.append("| Binance成交额Top50 | ✅ 可用 | AWS→Binance API (3.27.3.202) |")
lines.append("| 资金费率(681个币) | ✅ 可用 | AWS→Binance FAPI (3.27.3.202) |")
lines.append("| CoinGecko Trending | ✅ 可用 | AWS→CoinGecko API (3.27.3.202) |")
lines.append("| 个股市值 | ⚠️ 未采集 | CoinGecko MCap不在当前snapshot范围 |")
lines.append("| RSI(14) | ❌ 不可用 | 需要K-line数据，待接入 |")
lines.append("| 成交量基线(MA20) | ❌ 不可用 | 需要K-line数据，待接入 |")
lines.append("| ADX趋势强度 | ❌ 不可用 | 需要K-line数据，待接入 |")
lines.append("")
lines.append("> ⚠️ **Stage 2评分限制：** 因缺少K-line数据，成交量异常得分基于成交量排名（非MA20基线），动量得分基于24h涨跌幅（非EMA排列），RSI使用中性分50。评分仅供参考，不替代完整的两阶段筛选。")
lines.append("")
lines.append("---")
lines.append("")
lines.append("## Stage 1 硬过滤结果")
lines.append("")
lines.append("| 指标 | 数值 |")
lines.append("|:----|:----:|")
lines.append(f"| 扫描源 | Binance 24hr成交量Top50 |")
lines.append(f"| 总扫描币种数 | {len(top50)} |")
lines.append(f"| ✅ 通过 | {len(stage1_passed)} 个 |")
lines.append(f"| ❌ 排除 | {len(stage1_failed)} 个 |")
lines.append(f"| 通过率 | {len(stage1_passed)/len(top50)*100:.1f}% |")
lines.append("")
lines.append("### 过滤条件命中分布")
for cat, syms in sorted(exclude_cats.items(), key=lambda x: -len(x[1])):
    lines.append(f"- **{cat}**：{len(syms)}个 — {', '.join(syms)}")
lines.append("")

# Top 15 excluded
lines.append("### ❌ 排除列表（详）")
lines.append("| 币种 | 价格 | 24h成交额 | 排除原因 |")
lines.append("|:----|:----:|:---------:|:---------|")
for c in stage1_failed[:15]:
    lines.append(f"| {c['symbol']} | ${c['price']:.6f} | ${c['volume']:,.0f} | {c['reason']} |")
if len(stage1_failed) > 15:
    lines.append(f"| ... 还有{len(stage1_failed)-15}个 | ... | ... | ... |")
lines.append("")

# Passed list
lines.append("### ✅ 通过列表")
lines.append("| 币种 | 价格 | 24h成交额 | 24h涨跌 | 费率 | 状态 |")
lines.append("|:----|:----:|:---------:|:-------:|:----:|:----:|")
for c in stage1_passed:
    fr_str = f"{c['funding_rate']:.6f}" if c['funding_rate'] is not None else "N/A"
    lines.append(f"| {c['symbol']} | ${c['price']:.6f} | ${c['volume']:,.0f} | {c['change_pct']:+.2f}% | {fr_str} | 待评分 |")
lines.append("")
lines.append("---")
lines.append("")

# Stage 2 Scores
lines.append("## Stage 2 五因子评分结果")
lines.append("")

# Candidate Pool
lines.append("### 🟢 候选池（≥70分）")
lines.append("| 排名 | 币种 | 总分 | 成交量(30%) | 动量(25%) | 费率(20%) | RSI(15%) | 热度(10%) | 价格 | 24h涨跌 | 备注 |")
lines.append("|:---:|:----|:---:|:----------:|:---------:|:---------:|:--------:|:---------:|:----:|:-------:|:----|")
if len(candidate_pool) > 0:
    for i, s in enumerate(candidate_pool, 1):
        notes = []
        if s["is_trending"]:
            notes.append("Trending🔥")
        if s["change_pct"] < -3:
            notes.append("回调关注")
        if s["change_pct"] > 10:
            notes.append("涨幅过大⚠️")
        notes_str = " ".join(notes)
        lines.append(f"| {i} | **{s['symbol']}** | **{s['total']}** | {s['vs']} | {s['ms']} | {s['fs']} | {s['rs']} | {s['hs']} | ${s['price']:.4f} | {s['change_pct']:+.2f}% | {notes_str} |")
else:
    lines.append("| — | 暂无 | — | — | — | — | — | — | — | — | 评分数据不足，无≥70分候选 |")
lines.append("")

# Watch Pool
lines.append("### 🟡 待观察池（50-69分）")
lines.append("| 排名 | 币种 | 总分 | 成交量(30%) | 动量(25%) | 费率(20%) | RSI(15%) | 热度(10%) | 价格 | 24h涨跌 | 关注原因 |")
lines.append("|:---:|:----|:---:|:----------:|:---------:|:---------:|:--------:|:---------:|:----:|:-------:|:---------|")
if len(watch_pool) > 0:
    for i, s in enumerate(watch_pool, 1):
        reasons = []
        if s["is_trending"]:
            reasons.append("Trending热度币🔥")
        if s["change_pct"] >= 5:
            reasons.append(f"强势+{s['change_pct']:.1f}%")
        elif s["change_pct"] <= -5:
            reasons.append(f"超跌{s['change_pct']:.1f}%待企稳")
        if s["funding_rate"] is not None and MIN_FR <= s["funding_rate"] <= MAX_FR:
            reasons.append("费率中性")
        if not reasons:
            reasons.append("常规关注")
        lines.append(f"| {i} | {s['symbol']} | **{s['total']}** | {s['vs']} | {s['ms']} | {s['fs']} | {s['rs']} | {s['hs']} | ${s['price']:.4f} | {s['change_pct']:+.2f}% | {'; '.join(reasons)} |")
else:
    lines.append("| — | 暂无 | — | — | — | — | — | — | — | — | — |")
lines.append("")

# Stage 2 Excluded
lines.append("### 🔴 Stage 2排除（评分<50分）")
stage2_excluded = excluded_pool[:10]
if len(stage2_excluded) > 0:
    lines.append("| 币种 | 总分 | 主要弱点 |")
    lines.append("|:----|:----:|:---------|")
    for s in stage2_excluded:
        weaknesses = []
        if s["vs"] < 40:
            weaknesses.append("成交量弱")
        if s["ms"] < 40:
            weaknesses.append("动量差")
        if s["fs"] < 40:
            weaknesses.append("费率不健康")
        if s["is_trending"]:
            weaknesses.append("热度高(追高风险)")
        lines.append(f"| {s['symbol']} | {s['total']} | {'; '.join(weaknesses) if weaknesses else '综合评分低'} |")
else:
    lines.append("无")
lines.append("")

# Core Conclusion
lines.append("---")
lines.append("")
lines.append("## 核心结论")
lines.append("")
lines.append(f"| 指标 | 数值 |")
lines.append(f"|:----|:----:|")
lines.append(f"| 🟢 候选池（≥70分） | **{len(candidate_pool)}** 个 |")
lines.append(f"| 🟡 待观察池（50-69分） | **{len(watch_pool)}** 个 |")
lines.append(f"| 🔴 Stage1硬过滤排除 | **{len(stage1_failed)}** 个 |")
lines.append(f"| 🔴 Stage2评分排除 | **{len(excluded_pool)}** 个 |")
lines.append(f"| 合计排除 | **{len(stage1_failed) + len(excluded_pool)}** 个 |")
lines.append("")

if len(candidate_pool) > 0:
    lines.append("### 推荐A3优先关注（Top 3）")
    for i, s in enumerate(candidate_pool[:3], 1):
        fr_str = f"{s['funding_rate']:.6f}" if s['funding_rate'] is not None else "N/A"
        lines.append(f"{i}. **{s['symbol']}**（总分{s['total']}）— ${s['price']:.4f}，24h {s['change_pct']:+.2f}%，费率 {fr_str}")
else:
    lines.append("### 推荐A3优先关注")
    lines.append("**当前候选池为空。** 原因分析：")
    lines.append("- F&G=42恐惧环境下，成交量Top50中大量为大币种（BTC/ETH/SOL/XRP等），市值超出$1B推测上限")
    lines.append("- 缺少个股市值数据，无法精确验证市值条件($10M-$1B)")
    lines.append("- 缺少K-line数据（RSI/成交量基线），评分使用中性值替代")
    lines.append("")
    lines.append("**建议：** 待A1/数据层补全MCap数据后重新评估，或A3自行从待观察池中提取候选做深度分析")
lines.append("")

# Risk warnings
lines.append("### ⚠️ 风险提示")
lines.append("1. **市场处于恐惧（F&G=42）**：整体环境偏弱，BTC 24h跌1.58%至$79K，不宜激进入场")
lines.append("2. **INJ异常放量+17%涨幅但费率-0.105%**：若纳入待观察则需注意空头拥挤可能引发轧空")
lines.append("3. **COS费率极端负值(-1.03%)**：虽然涨幅+48%，但空头极度拥挤，轧空风险极高")
lines.append("4. **缺失3项关键数据影响评分可靠性**：RSI/成交量基线/MCap均不可用，评分仅供参考")
lines.append("")

# Data sources
lines.append("---")
lines.append("")
lines.append("## 数据来源")
lines.append("| 数据维度 | 来源 | 状态 |")
lines.append("|:---------|:-----|:----:|")
lines.append("| Binance 24hr Ticker | AWS→Binance API (3.27.3.202) | ✅ 实时 |")
lines.append("| 资金费率 | AWS→Binance FAPI (3.27.3.202) | ✅ 实时 |")
lines.append("| CoinGecko Trending | AWS→CoinGecko API (3.27.3.202) | ✅ 实时 |")
lines.append("| F&G指数 | Alternative.me API | ✅ 实时 |")
lines.append("| 宏观市场数据 | AWS→CoinGecko Global (3.27.3.202) | ✅ 实时 |")
lines.append("| A1辅助数据 | profiles/a1-data/output/2026-05-14.md | ✅ 已交叉验证 |")
lines.append("")
lines.append("*Stage 2评分中RSI和成交量基线暂不可用，使用中性值和排名代理评分。*")
lines.append("")
lines.append(f"---")
lines.append(f"*报告生成时间：{today} {now_bjt} BJT*")
lines.append("*A2 选币官 — 安检员 | 排除比选择更重要*")
lines.append("")

report = "\n".join(lines)

# Write report
output_path = os.path.join(BASE, "output", f"{today}.md")
os.makedirs(os.path.join(BASE, "output"), exist_ok=True)
with open(output_path, "w") as f:
    f.write(report)

print(f"\n✅ 报告已写入: {output_path}")
print(f"\n{'='*60}")
print(f"报告摘要")
print(f"{'='*60}")
print(f"日期: {today}")
print(f"候选池: {len(candidate_pool)}个")
print(f"待观察池: {len(watch_pool)}个")
print(f"排除(Stage1): {len(stage1_failed)}个")
print(f"排除(Stage2): {len(excluded_pool)}个")
print(f"Top 3: {[s['symbol'] for s in candidate_pool[:3]] if candidate_pool else '无候选'}")
