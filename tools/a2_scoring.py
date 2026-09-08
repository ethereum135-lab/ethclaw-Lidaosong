#!/usr/bin/env python3
"""
A2 选币官 — 两阶段筛选评分脚本

替换LLM驱动的A2选币流程。
直接从 aws_snapshot.json + data_feed.md 读取数据，精确计算评分。
同数据输入 → 同评分输出（无LLM漂移）。

使用方法：
  python3 tools/a2_scoring.py                     # 使用最新 snapshot
  python3 tools/a2_scoring.py --snapshot <path>   # 指定 snapshot 文件

输出：profiles/a2-selector/output/YYYY-MM-DD.md

依赖：无（纯 Python 标准库 + json）
"""

import json
import os
import sys
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ==================== 配置 ====================

BJT = timezone(timedelta(hours=8))
BASE_DIR = Path(__file__).resolve().parent.parent
SNAPSHOT_PATH = BASE_DIR / "data" / "aws_snapshot.json"
DATA_FEED_PATH = BASE_DIR / "profiles" / "a1-data" / "output" / "data_feed.md"
OUTPUT_DIR = BASE_DIR / "profiles" / "a2-selector" / "output"
AGENTS_DIR = BASE_DIR / "profiles" / "a2-selector"

STAGE1_CONFIG = {
    "min_volume": 1_000_000,      # $1M 最低成交额
    "min_price": 0.001,            # $0.001 最低价格
    "stablecoin_symbols": ["BUSD", "DAI", "USDC", "EUR", "GBP", "AUD", "CAD", "JPY"],
    "lev_patterns": ["DOWN", "UP", "BEAR", "BULL", "2L", "2S", "3L", "3S"],
    "funding_rate_max": 0.0002,    # ±0.02% 费率范围（放宽版）
    "funding_rate_min": -0.0002,
    "crash_threshold": -20,        # 24h跌幅>20%视为暴跌
    "rebound_threshold": 10,       # 当前反弹>10%视为有效反弹
}

# Stage2 权重
W_VOLUME = 0.30
W_MOMENTUM = 0.25
W_FUNDING = 0.20
W_RSI = 0.15
W_HEAT = 0.10

# 小资金不交易巨盘币（参考用，不给A3选）
MEGACAP_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
SECTOR_MAP = {
    "AI": ["FET", "AGIX", "OCEAN", "RNDR", "AKT", "TAO", "AI", "NEAR", "LPT", "AIGENSYN"],
    "DePIN": ["HNT", "IOT", "FIL", "AR", "STORJ", "ANKR", "CFX"],
    "RWA": ["ONDO", "OM", "MPL", "CFG", "RIO", "XRP"],
    "DeFi": ["UNI", "AAVE", "COMP", "MKR", "CRV", "CAKE", "PENDLE", "INJ", "LINK"],
    "Meme": ["DOGE", "SHIB", "PEPE", "FLOKI", "BONK", "WIF", "DOGS", "NEIRO"],
    "L1/L2": ["BTC", "ETH", "SOL", "ADA", "AVAX", "DOT", "MATIC", "ARB", "OP", "SUI", "APT", "TIA", "BNB"],
    "GameFi": ["AXS", "SAND", "MANA", "GALA", "ENJ"],
}

# ==================== 赛道热度加载（来自 hot_sectors.md）====================

HOT_SECTORS_PATH = BASE_DIR / "shared" / "hot_sectors.md"

def load_hot_sectors():
    """
    解析 shared/hot_sectors.md，返回：
      sector_heat: {sector_name: heat_score}
      coin_to_sector: {SYMBOL: sector_name}  (来自核心币种列)
    """
    sector_heat = {}
    coin_to_sector = {}
    
    p = HOT_SECTORS_PATH
    if not p.exists():
        return sector_heat, coin_to_sector
    
    text = p.read_text()
    
    # 查找赛道排行表
    in_table = False
    for line in text.split("\n"):
        line_stripped = line.strip()
        
        # 检测表头行
        if "排名 | 赛道 | 热度分" in line_stripped:
            in_table = True
            continue
        if "|:----:|:-----|:------:" in line_stripped:
            in_table = True
            continue
        
        if not in_table or not line_stripped.startswith("|"):
            continue
        
        parts = [p.strip() for p in line_stripped.split("|")]
        if len(parts) >= 7:
            # 解析: | 排名 | 赛道 | 热度分 | 档位 | 趋势 | 核心币种 | 24h表现 |
            sector_name = parts[2].strip()
            # 热度分格式: "**67**" 或 "67"
            heat_raw = parts[3].strip().replace("**", "").replace("*", "")
            try:
                heat = int(heat_raw)
                sector_heat[sector_name] = heat
            except ValueError:
                continue
            
            # 解析核心币种列
            coins_raw = parts[6].strip()
            # 提取所有大写币种符号
            import re
            coin_symbols = re.findall(r'[A-Z]{2,10}', coins_raw)
            for sym in coin_symbols:
                if sym not in coin_to_sector:
                    coin_to_sector[sym] = sector_name
    
    return sector_heat, coin_to_sector

# ==================== 数据加载 ====================

def load_snapshot(path=None):
    """加载 aws_snapshot.json"""
    p = Path(path) if path else SNAPSHOT_PATH
    with open(p) as f:
        return json.load(f)

def parse_data_feed(path=None):
    """解析 data_feed.md，提取结构化数据"""
    p = Path(path) if path else DATA_FEED_PATH
    if not p.exists():
        return {"trending": [], "error": "data_feed.md not found"}
    
    text = p.read_text()
    result = {"trending": []}
    
    # 提取TRENDING
    in_trending = False
    for line in text.split("\n"):
        if "## TRENDING" in line:
            in_trending = True
            continue
        if in_trending and line.startswith("##"):
            break
        if in_trending and re.match(r'^\d+\.\s+', line):
            name = re.sub(r'^\d+\.\s+', '', line).strip()
            result["trending"].append(name)
    
    return result

def get_today_str():
    return datetime.now(BJT).strftime("%Y-%m-%d")

# ==================== Stage 1 硬过滤 ====================

def stage1_filter(coin):
    """
    6条硬条件过滤，返回 (passed, reason, is_crash_rebound)
    """
    symbol = coin["symbol"].upper().replace("USDT", "")
    price = float(coin["price"])
    volume = float(coin["volume"])
    change_pct = float(coin["change_pct"])
    
    checks = {}
    
    # 1. 最低成交量
    checks["volume_24h"] = volume >= STAGE1_CONFIG["min_volume"]
    
    # 2. 价格检查 + 暴跌反弹豁免
    checks["price"] = price > STAGE1_CONFIG["min_price"]
    
    # 3. 排除稳定币/法币对（仅检查base资产，不是"USDT"后缀本身）
    base_asset = coin["symbol"].upper().replace("USDT", "").replace("USDC", "").strip()
    is_stable = base_asset in ["EUR", "GBP", "AUD", "CAD", "JPY", "RLUSD", "DAI",
                                "BUSD", "TUSD", "FDUSD", "USDP", "GUSD", "PAX",
                                "U", "SUSD", "LUSD", "FRAX", "CRVUSD"]
    checks["not_stablecoin"] = not is_stable
    
    # 4. 排除杠杆代币
    is_lev = False
    for p in STAGE1_CONFIG["lev_patterns"]:
        if p in coin["symbol"].upper():
            is_lev = True
            break
    checks["not_leveraged"] = not is_lev
    
    # 5. 费率中性 — 跳过（在stage2中处理，因为需要外部费率数据）
    checks["funding_rate"] = True  # 将在stage2检查
    
    # 6. 暴跌反弹检测
    is_crash = change_pct < STAGE1_CONFIG["crash_threshold"]
    is_rebounding = change_pct > STAGE1_CONFIG["rebound_threshold"]
    checks["crash_rebound"] = not (is_crash and not is_rebounding)
    
    # 7. 非USDT对（只交易USDT对的币）
    checks["is_usdt_pair"] = coin["symbol"].endswith("USDT")
    
    passed = all(checks.values())
    
    # 构建排除原因
    reasons = []
    for k, v in checks.items():
        if not v:
            labels = {
                "volume_24h": f"成交量${volume/1e6:.1f}M<$1M",
                "price": f"价格${price}<$0.001",
                "not_stablecoin": "稳定币/法币对",
                "not_leveraged": "杠杆代币",
                "funding_rate": "费率异常",
                "crash_rebound": f"暴跌{change_pct:.1f}%未有效反弹",
                "is_usdt_pair": "非USDT交易对",
            }
            reasons.append(labels.get(k, k))
    
    return passed, " | ".join(reasons) if reasons else "通过", is_crash and is_crash

# ==================== Stage 2 五因子评分 ====================

def classify_sector(symbol, coin_to_sector=None):
    """根据symbol判断赛道，优先使用 hot_sectors.md 的实时映射"""
    upper = symbol.upper().replace("USDT", "")
    # 优先使用实时数据
    if coin_to_sector and upper in coin_to_sector:
        return coin_to_sector[upper]
    # 降级到静态映射
    for sector, tokens in SECTOR_MAP.items():
        for t in tokens:
            if t in upper or upper in t:
                return sector
    return "其他"


def score_sector_heat(sector_name, sector_heat):
    """
    赛道热度加分 (0~+5 bonus)
    赛道热度≥60 的币种得到加分，引导系统优先关注热门赛道
    """
    if not sector_heat:
        return 0
    heat = sector_heat.get(sector_name, 0)
    if heat >= 70:
        return 5  # 🔥热门赛道加分
    elif heat >= 60:
        return 3  # ⚡关注赛道加分
    elif heat >= 40:
        return 1  # 温和加分
    return 0


# ==================== 方向优先级加载（来自 direction_priority.md）====================

DIRECTION_PRIORITY_PATH = BASE_DIR / "shared"

def get_direction_priority_path():
    """返回今天的 direction_priority 文件路径"""
    today = datetime.now(BJT).strftime("%Y-%m-%d")
    return DIRECTION_PRIORITY_PATH / f"direction_priority_{today}.md"

def load_direction_priority():
    """
    解析 shared/direction_priority_YYYY-MM-DD.md，返回：
      sector_weight: {sector_name: weight_pct} (如 {"AI": 40, "RWA": 30})
    """
    sector_weight = {}
    p = get_direction_priority_path()
    if not p.exists():
        return sector_weight
    
    text = p.read_text()
    
    # 解析方向排序中的权重行
    # 格式: 1. 🔥 **赛道名** (权重40%) — 理由
    in_sorting = False
    for line in text.split("\n"):
        stripped = line.strip()
        
        # 找到"方向排序"章节
        if "方向排序" in stripped:
            in_sorting = True
            continue
        # 找到下一个二级标题则结束
        if in_sorting and stripped.startswith("## ") and "方向排序" not in stripped:
            in_sorting = False
            continue
        
        if not in_sorting:
            continue
        
        # 解析: 1. 🔥 **赛道名** (权重40%)
        import re
        m = re.search(r'\*\*([^*]+)\*\*\s*\(权重(\d+)%\)', stripped)
        if m:
            sector = m.group(1).strip().rstrip('*').strip()
            weight = int(m.group(2))
            sector_weight[sector] = weight
    
    return sector_weight


def score_direction_priority(sector_name, direction_weights):
    """
    方向优先级加分 (0~+5 bonus)
    根据ZH的融合层方向权重，高权重赛道加分
    """
    if not direction_weights:
        return 0
    
    weight = direction_weights.get(sector_name, 0)
    if weight >= 30:
        return 5
    elif weight >= 20:
        return 3
    elif weight >= 10:
        return 1
    return 0


def score_volume(coin, all_coins):
    """
    成交量异常得分 (0-100)
    使用相对排名作为代理：Top50中排名越靠前 = 成交量越大
    """
    volume = float(coin["volume"])
    # 在Top50中的排名（按成交量降序）
    sorted_coins = sorted(all_coins, key=lambda c: float(c.get("volume", 0)), reverse=True)
    rank = next(i for i, c in enumerate(sorted_coins) if c["symbol"] == coin["symbol"]) + 1
    
    # 得分基于排名位置
    if rank <= 5:
        return 100  # Top5 = 巨量
    elif rank <= 10:
        return 80
    elif rank <= 20:
        return 60
    elif rank <= 30:
        return 40
    elif rank <= 40:
        return 20
    else:
        return 10

def score_momentum(coin):
    """
    动量结构得分 (0-100)
    基于24h涨跌幅和价格位置
    """
    change_pct = float(coin["change_pct"])
    price = float(coin["price"])
    high = float(coin["high"])
    low = float(coin["low"])
    
    # 利用24h范围内的相对位置
    if high > low:
        range_pos = (price - low) / (high - low) * 100  # 0-100
    else:
        range_pos = 50
    
    # 趋势判断
    if change_pct > 3 and range_pos > 60:
        return 100  # 强势上涨
    elif change_pct > 0 and range_pos > 50:
        return 75   # 温和上涨
    elif -2 <= change_pct <= 2:
        if range_pos > 50:
            return 60   # 横盘偏强
        else:
            return 40   # 横盘偏弱
    elif -5 <= change_pct < -2:
        return 30   # 小幅下跌
    else:
        return 10   # 大幅下跌

def score_funding(coin, funding_rates):
    """
    费率健康得分 (0-100)
    """
    symbol = coin["symbol"]
    fr = funding_rates.get(symbol, {})
    try:
        rate = float(fr.get("rate", 0)) if isinstance(fr, dict) else 0
    except (ValueError, TypeError):
        rate = 0
    
    # 费率打分
    if -0.005 <= rate <= 0.01:
        return 100  # 完美中性
    elif -0.01 <= rate < -0.005:
        return 70   # 略负
    elif 0.01 < rate <= 0.02:
        return 60   # 略正
    elif -0.02 <= rate < -0.01:
        return 30   # 偏负
    elif 0.02 < rate <= 0.05:
        return 20   # 偏正
    else:
        return 0    # 极端

def score_rsi(coin):
    """
    RSI近似得分 (0-100)
    使用24h范围内的价格位置作为RSI的近似
    """
    price = float(coin["price"])
    high = float(coin["high"])
    low = float(coin["low"])
    
    if high <= low:
        return 50  # 异常数据
    
    # 计算价格在24h范围中的位置（0-100）
    range_pos = (price - low) / (high - low) * 100
    
    # 映射到RSI类似得分
    # 价格在30%-50%量程 = 最佳买入区间
    if 30 <= range_pos <= 50:
        return 100
    elif 50 < range_pos <= 60:
        return 70
    elif 20 <= range_pos < 30:
        return 60
    elif 60 < range_pos <= 70:
        return 40
    elif range_pos < 20:
        return 30
    else:  # > 70
        return 0

def score_heat(coin, trending_names):
    """
    热度修正得分 (0-100)
    """
    symbol = coin["symbol"].upper().replace("USDT", "")
    change_pct = float(coin["change_pct"])
    
    # 检查是否在trending中（粗略匹配）
    is_trending = any(
        t.lower() in symbol.lower() or symbol.lower() in t.lower()
        for t in trending_names
    )
    
    if is_trending and change_pct > 5:
        return 70   # 强者恒强
    elif is_trending and change_pct > 0:
        return 50   # 正常关注
    elif is_trending and change_pct < 0:
        return 30   # 出货盘
    else:
        return 50   # 不热不冷

# ==================== 报告生成 ====================

def generate_report(coins, results, fg_value, fg_label, btc_price, eth_price, 
                    btc_dominance, total_mcap, snapshot_time, sector_heat=None):
    """生成A2完整报告"""
    today = get_today_str()
    
    # 分类
    # 候选池（排除巨盘币，小资金不交易）
    candidates = [r for r in results if r["total"] >= 70 and not r.get("is_megacap", False)]
    megacap_refs = [r for r in results if r["total"] >= 70 and r.get("is_megacap", False)]
    watch_list = [r for r in results if 50 <= r["total"] < 70]
    eliminated = [r for r in results if r["total"] < 50]
    stage1_fail = [r for r in results if not r["stage1_passed"]]
    stage1_pass = [r for r in results if r["stage1_passed"]]
    
    # 判断市场环境
    fg = int(fg_value) if fg_value else 50
    if fg <= 40:
        market_judgment = f"F&G={fg} — Fear，筛选力度：宽松（恐慌中找机会）"
    elif fg <= 60:
        market_judgment = f"F&G={fg} — Neutral，筛选力度：正常"
    else:
        market_judgment = f"F&G={fg} — Greed，筛选力度：收紧（警惕追高）"
    
    lines = []
    lines.append(f"# A2 选币官 — 候选池报告")
    lines.append(f"日期：{today} | 时间：{datetime.now(BJT).strftime('%H:%M BJT')}")
    lines.append(f"数据来源：aws_snapshot.json (AWS→Binance API) | Alternative.me")
    lines.append(f"评分模式: 脚本精确计算 (非LLM推理)")
    lines.append(f"")
    lines.append(f"## 市场环境总览")
    lines.append(f"- F&G指数：{fg_value}/100 — {fg_label}")
    lines.append(f"- BTC价格：${btc_price} | ETH价格：${eth_price}")
    lines.append(f"- BTC Dominance：{btc_dominance}%")
    # 自动判断数量级：万亿用T, 十亿用B
    try:
        mcap_val = float(total_mcap.replace("$","").replace(",",""))
        if mcap_val >= 1:
            mcap_unit = "T"
        else:
            mcap_unit = "B"
    except:
        mcap_unit = "?"
    lines.append(f"- 总市值：${total_mcap}{mcap_unit}")
    lines.append(f"- **判断：{market_judgment}**")
    lines.append(f"- 数据快照：{snapshot_time}")
    lines.append(f"")
    lines.append(f"## Stage 1 硬过滤结果")
    scan_label = f"Binance Top{len(coins)} by 24h成交量"
    lines.append(f"总扫描币种数：{len(coins)} ({scan_label})")
    lines.append(f"通过：{len(stage1_pass)} 个")
    lines.append(f"排除：{len(stage1_fail)} 个")
    lines.append(f"")
    
    # 排除详情
    if stage1_fail:
        lines.append(f"### 排除详情")
        lines.append(f"| 币种 | 价格 | 成交量 | 24h涨幅 | 排除原因 |")
        lines.append(f"|:----|:----:|:------:|:-------:|:---------|")
        for r in sorted(stage1_fail, key=lambda x: float(x.get("volume", 0)), reverse=True)[:20]:
            p = r.get("price", "?")
            v = f"${float(r.get('volume',0))/1e6:.1f}M"
            ch = f"{r.get('change_pct','?')}%"
            lines.append(f"| {r['symbol']} | {p} | {v} | {ch} | {r['stage1_reason']} |")
        lines.append(f"")
    
    # 赛道热度覆盖检查
    if sector_heat and len(candidates) > 0:
        lines.append("## 赛道热度覆盖")
        lines.append("| 赛道 | 热度分 | 档位 | 候选中数量 | 候选币种 |")
        lines.append("|:----|:-----:|:----:|:----------:|:---------|")
        for sector_name in sorted(sector_heat.keys(), key=lambda s: sector_heat.get(s, 0), reverse=True):
            heat = sector_heat.get(sector_name, 0)
            # 档位
            if heat >= 70:
                level = "🔥"
            elif heat >= 40:
                level = "⚡"
            else:
                level = "💤"
            # 统计该赛道的候选币
            sector_coins = [r['symbol'] for r in candidates if r.get('sector', '') == sector_name]
            count = len(sector_coins)
            coins_str = ', '.join(sector_coins[:3]) if count > 0 else '—'
            lines.append(f"| {sector_name} | {heat} | {level} | {count} | {coins_str} |")
        lines.append("")
    
    # Stage2 评分结果
    lines.append(f"## Stage 2 五因子评分结果")
    lines.append(f"")
    
    # 候选池
    lines.append(f"### 🟢 候选池（≥70分）—— {len(candidates)} 个")
    if candidates:
        lines.append(f"| 排名 | 币种 | 赛道 | 总分 | 成交额(30%) | 动量(25%) | 费率(20%) | RSI约(15%) | 热度(10%) | 涨幅24h |")
        lines.append(f"|:---:|:----|:----:|:---:|:----------:|:---------:|:---------:|:----------:|:---------:|:-------:|")
        for i, r in enumerate(sorted(candidates, key=lambda x: x["total"], reverse=True), 1):
            lines.append(
                f"| {i} | {r['symbol']} | {r['sector']} | "
                f"**{r['total']}** | {r['v_score']} | {r['m_score']} | "
                f"{r['f_score']} | {r['r_score']} | {r['h_score']} | "
                f"{r['change_pct']}% |"
            )
    else:
        lines.append(f"无")
    lines.append(f"")
    
    # 巨盘参考（小资金不交易，仅作大盘风向标）
    if megacap_refs:
        lines.append(f"### 📊 巨盘参考（小资金不交易）")
        lines.append(f"| 币种 | 赛道 | 总分 | 24h涨幅 | 说明 |")
        lines.append(f"|:----|:----:|:---:|:-------:|:-----|")
        for r in sorted(megacap_refs, key=lambda x: x["total"], reverse=True):
            lines.append(
                f"| {r['symbol']} | {r['sector']} | {r['total']} | "
                f"{r['change_pct']}% | 大盘风向标，不纳入选币 |"
            )
        lines.append(f"")
    
    # 待观察池
    lines.append(f"### 🟡 待观察池（50-69分）—— {len(watch_list)} 个")
    if watch_list:
        lines.append(f"| 币种 | 总分 | 关注原因 | 缺点 |")
        lines.append(f"|:----|:---:|:---------|:-----|")
        for r in sorted(watch_list, key=lambda x: x["total"], reverse=True):
            weakness = ""
            if r["v_score"] < 50:
                weakness += "成交量弱 "
            if r["m_score"] < 40:
                weakness += "动量弱 "
            if r["f_score"] < 50:
                weakness += "费率异常 "
            lines.append(f"| {r['symbol']} | {r['total']} | 评分接近70 | {weakness} |")
        lines.append(f"")
    else:
        lines.append(f"无")
        lines.append(f"")
    
    # 排除列表
    eliminated_pass = [r for r in eliminated if r["stage1_passed"]]
    if eliminated_pass:
        lines.append(f"### 🔴 Stage2 排除（评分<50）—— {len(eliminated_pass)} 个")
        lines.append(f"| 币种 | 总分 | 原因 |")
        lines.append(f"|:----|:---:|:-----|")
        for r in sorted(eliminated_pass, key=lambda x: x["total"], reverse=True):
            weakness = ""
            if r["v_score"] < 30:
                weakness += "量差 "
            if r["m_score"] < 25:
                weakness += "动量差 "
            if r["r_score"] < 30:
                weakness += "RSI偏高/低 "
            lines.append(f"| {r['symbol']} | {r['total']} | {weakness} |")
        lines.append(f"")
    
    # 全市场宽度扫描
    lines.append(f"## 📡 全市场宽度扫描")
    lines.append(f"### 涨幅异常（24h >+10%且成交量>$10M）")
    unusual_ups = [c for c in coins if float(c.get("change_pct", 0)) > 10 and float(c.get("volume", 0)) > 10_000_000]
    if unusual_ups:
        for c in unusual_ups:
            label = "暴涨正常上涨" if float(c["change_pct"]) < 20 else "⚠️暴跌反弹"
            lines.append(f"- **{c['symbol']}**: +{c['change_pct']}% | 成交量${float(c['volume'])/1e6:.1f}M | {label}")
    else:
        lines.append("今日无涨幅>10%的币")
    lines.append(f"")
    
    lines.append(f"### 跌幅异常（24h <-10%且成交量>$10M）")
    unusual_downs = [c for c in coins if float(c.get("change_pct", 0)) < -10 and float(c.get("volume", 0)) > 10_000_000]
    if unusual_downs:
        for c in unusual_downs:
            lines.append(f"- **{c['symbol']}**: {c['change_pct']}% | 成交量${float(c['volume'])/1e6:.1f}M")
    else:
        lines.append("今日无跌幅>10%的币")
    lines.append(f"")
    
    # 核心结论
    lines.append(f"## 核心结论")
    lines.append(f"- 总候选池：{len(candidates)} 个币")
    lines.append(f"- 总待观察池：{len(watch_list)} 个币")
    if candidates:
        top3 = sorted(candidates, key=lambda x: x["total"], reverse=True)[:3]
        lines.append(f"- 推荐A3优先关注：{', '.join([r['symbol'] for r in top3])}")
        lines.append(f"- 当前最佳：**{top3[0]['symbol']}** ({top3[0]['total']}分)")
    else:
        lines.append(f"- 候选池为空 — 当前市场环境下无满足条件的币")
    lines.append(f"- 评分模式：脚本精确计算（五因子加权）✅")
    lines.append(f"- ⚠️ 注：RSI为基于24h价格范围的近似值（无K线API），费率为实时数据")
    lines.append(f"")
    
    content = "\n".join(lines)
    return content


# ==================== 主流程 ====================

def main():
    # 解析参数
    snapshot_path = None
    if "--snapshot" in sys.argv:
        idx = sys.argv.index("--snapshot")
        if idx + 1 < len(sys.argv):
            snapshot_path = sys.argv[idx + 1]
    
    # 1. 加载数据
    snapshot = load_snapshot(snapshot_path)
    feed = parse_data_feed()
    
    coins = snapshot.get("binance_top200", snapshot.get("binance_top50", []))
    funding_rates = snapshot.get("funding_rates", {})
    fg_value = snapshot.get("fg_index", "50")
    fg_label = snapshot.get("fg_classification", "Neutral")
    snapshot_time = snapshot.get("time", "?")
    
    global_data = snapshot.get("global", {})
    btc_price = "?"
    eth_price = "?"
    btc_dominance = global_data.get("btc_dominance", "?")
    total_mcap = global_data.get("total_mcap_usd", "0")
    
    # 找到BTC和ETH价格
    for c in coins:
        if c["symbol"] == "BTCUSDT":
            btc_price = c["price"]
        if c["symbol"] == "ETHUSDT":
            eth_price = c["price"]
    
    # 2. 做市值估算（用成交量作为代理，因为snapshot没有市值）
    # 实际上我们跳过市值过滤，因为缺乏数据
    
    # 3. 加载赛道热度数据
    sector_heat, coin_to_sector = load_hot_sectors()
    
    # 3b. 加载方向优先级
    direction_weights = load_direction_priority()
    if direction_weights:
        print(f"   方向优先级: {len(direction_weights)} 个赛道")
    else:
        print(f"   方向优先级: 未加载（文件不存在）")
    
    # 4. Stage 1 + Stage 2 处理每个币
    trending_names = feed.get("trending", [])
    results = []
    
    for coin in coins:
        symbol = coin["symbol"]
        change_pct = coin["change_pct"]
        volume = float(coin["volume"])
        
        # Stage 1
        passed, reason, is_crash_rebound = stage1_filter(coin)
        
        # 通过Stage1才做Stage2
        if passed:
            v_score = score_volume(coin, coins)
            m_score = score_momentum(coin)
            f_score = score_funding(coin, funding_rates)
            r_score = score_rsi(coin)
            h_score = score_heat(coin, trending_names)
            
            total = round(
                v_score * W_VOLUME +
                m_score * W_MOMENTUM +
                f_score * W_FUNDING +
                r_score * W_RSI +
                h_score * W_HEAT,
                1
            )
            
            # 赛道热度加分
            sector = classify_sector(symbol, coin_to_sector)
            heat_bonus = score_sector_heat(sector, sector_heat)
            
            # 方向优先级加分（来自ZH方向融合）
            dir_bonus = score_direction_priority(sector, direction_weights)
            
            total_with_bonus = round(total + heat_bonus + dir_bonus, 1)
            if total_with_bonus > 100:
                total_with_bonus = 100.0
        else:
            v_score = 0
            m_score = 0
            f_score = 0
            r_score = 0
            h_score = 0
            total = 0
            total_with_bonus = 0
            sector = classify_sector(symbol, coin_to_sector)
            heat_bonus = 0
        
        # 小资金不交易巨盘币（参考用，不给A3选）
        is_megacap = symbol in MEGACAP_SYMBOLS
        
        results.append({
            "symbol": symbol,
            "sector": sector,
            "sector_heat_bonus": heat_bonus,
            "is_megacap": is_megacap,
            "price": coin["price"],
            "volume": volume,
            "change_pct": change_pct,
            "stage1_passed": passed,
            "stage1_reason": reason,
            "v_score": v_score,
            "m_score": m_score,
            "f_score": f_score,
            "r_score": r_score,
            "h_score": h_score,
            "total": total_with_bonus,
        })
    
    # 4. 生成报告
    report = generate_report(
        coins, results,
        fg_value, fg_label,
        btc_price, eth_price,
        btc_dominance,
        f"{float(total_mcap)/1e12:.2f}" if total_mcap != "0" else "?",
        snapshot_time,
        sector_heat
    )
    
    # 5. 输出目录
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    today = get_today_str()
    output_path = OUTPUT_DIR / f"{today}.md"
    output_path.write_text(report)
    
    print(f"✅ A2评分完成")
    print(f"   数据来源: {snapshot.get('source', '?')}")
    print(f"   快照时间: {snapshot.get('date', '?')} {snapshot_time}")
    print(f"   扫描币种: {len(coins)}")
    candidates = [r for r in results if r["stage1_passed"] and r["total"] >= 70]
    watch = [r for r in results if r["stage1_passed"] and 50 <= r["total"] < 70]
    print(f"   候选池: {len(candidates)}, 待观察: {len(watch)}")
    if candidates:
        top = sorted(candidates, key=lambda x: x["total"], reverse=True)[0]
        print(f"   最佳: {top['symbol']} ({top['total']}分)")
    print(f"   输出: {output_path}")

if __name__ == "__main__":
    main()
