#!/usr/bin/env python3
"""
A3 牛币官 — 量价/趋势/RR评分脚本

计算A3四维分析中的可计算部分（80%权重），留给LLM只做叙事判断（20%）。
同数据输入 → 同评分输出（无LLM漂移）。

使用方法：
  python3 tools/a3_scoring.py
  python3 tools/a3_scoring.py --candidates BTCUSDT,ETHUSDT,DOGEUSDT

输出：profiles/a3-bull/output/dim_scores_{date}.json  → A3 LLM读此文件做叙事判断

维度权重：
  量价结构(40%) + 趋势位置(25%) + RR比(15%) = 80%  → 脚本计算
  叙事逻辑(20%) → LLM判断
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

BJT = timezone(timedelta(hours=8))
BASE_DIR = Path(__file__).resolve().parent.parent
SNAPSHOT_PATH = BASE_DIR / "data" / "aws_snapshot.json"
A2_OUTPUT_DIR = BASE_DIR / "profiles" / "a2-selector" / "output"
OUTPUT_DIR = BASE_DIR / "profiles" / "a3-bull" / "output"

def load_snapshot():
    p = SNAPSHOT_PATH
    if not p.exists():
        print(f"❌ snapshot not found: {p}")
        return None
    with open(p) as f:
        return json.load(f)

def get_coin_data(snapshot, symbol):
    """从snapshot中提取特定币种的行情数据"""
    for c in snapshot.get("binance_top200", snapshot.get("binance_top50", [])):
        if c["symbol"] == symbol:
            return c
    return None

def get_funding_rate(snapshot, symbol):
    fr = snapshot.get("funding_rates", {})
    item = fr.get(symbol, {})
    if isinstance(item, dict):
        return float(item.get("rate", 0))
    return 0

# ==================== 维度1: 量价结构 (40%) ====================

def score_volume_price(coin, all_coins):
    """
    量价结构评分 0-100
    基于：量比(成交量排名)、涨幅、量价关系
    """
    price = float(coin["price"])
    volume = float(coin["volume"])
    change_pct = float(coin["change_pct"])
    high = float(coin["high"])
    low = float(coin["low"])
    
    # 成交量排名得分（在Top50中的位置）
    sorted_by_vol = sorted(all_coins, key=lambda c: float(c.get("volume", 0)), reverse=True)
    rank = next(i for i, c in enumerate(sorted_by_vol) if c["symbol"] == coin["symbol"]) + 1
    vol_score = max(0, 100 - (rank - 1) * 2)  # 第1名100分，第50名2分
    
    # 价格在24h范围中的位置
    range_pos = (price - low) / (high - low) * 100 if high > low else 50
    
    # 量价关系判断
    is_rising = change_pct > 0
    is_volume_high = rank <= 15  # Top15算高量
    is_range_low = range_pos < 40  # 价格在低位
    
    if change_pct > 5 and rank <= 10:
        return 100  # 放量大涨 优秀
    elif change_pct > 3 and rank <= 15:
        return 90   # 放量上涨
    elif is_volume_high and not is_rising and abs(change_pct) < 2:
        return 75   # 放量不涨 = 吸筹
    elif not is_rising and is_range_low and abs(change_pct) < 3:
        return 65   # 缩量低位 = 健康整理
    elif change_pct < -5 and rank <= 15:
        return 10   # 放量下跌 = 资金出逃
    elif is_rising and not is_volume_high:
        return 45   # 缩量上涨 = 跟风不足
    elif not is_rising and change_pct < -3:
        return 20   # 放量下跌 = 危险
    else:
        return 50   # 中性

# ==================== 维度2: 趋势位置 (25%) ====================

def score_trend(coin):
    """
    趋势位置评分 0-100
    基于：24h涨跌幅、价格在范围内位置
    """
    price = float(coin["price"])
    change_pct = float(coin["change_pct"])
    high = float(coin["high"])
    low = float(coin["low"])
    
    range_pos = (price - low) / (high - low) * 100 if high > low else 50
    
    # 启点初期：小幅上涨+价格在范围低位
    if 0 < change_pct <= 5 and range_pos <= 50:
        return 95  # 最佳窗口
    # 趋势中段：持续上涨+价格在范围中位
    elif change_pct > 0 and 40 <= range_pos <= 65:
        return 70  # 可入
    # 底部整理：微跌或微涨+价格在范围低位
    elif -3 <= change_pct <= 0 and range_pos <= 40:
        return 80  # 埋伏
    # 趋势末期：大幅上涨+价格在高位
    elif change_pct > 5 and range_pos > 70:
        return 20  # 不追
    # 深度超卖：大幅下跌+价格在极低位
    elif change_pct < -5 and range_pos < 20:
        return 60  # 关注反弹
    # 下跌趋势
    elif change_pct < -3:
        return 30  # 动量弱
    else:
        return 50  # 中性

# ==================== 维度4: RR比 (15%) ====================

def estimate_rr(coin):
    """
    RR比估算 0-100
    基于24h高低点计算潜在的支撑阻力
    """
    price = float(coin["price"])
    high = float(coin["high"])
    low = float(coin["low"])
    change_pct = float(coin["change_pct"])
    
    # 简单估算支撑和阻力
    support = low * 0.98  # 略低于24h低点
    resistance = high * 1.02  # 略高于24h高点
    
    potential_gain = (resistance - price) / price * 100  # %
    potential_loss = (price - support) / price * 100     # %
    
    if potential_loss <= 0:
        return 50  # 数据异常
    
    rr_ratio = potential_gain / potential_loss
    
    if rr_ratio >= 3.0:
        return 100  # 优质
    elif rr_ratio >= 2.0:
        return 75   # 可接受
    elif rr_ratio >= 1.5:
        return 50   # 一般
    elif rr_ratio >= 1.0:
        return 30   # 差
    else:
        return 10   # 放弃

# ==================== 主流程 ====================

def main():
    today = datetime.now(BJT).strftime("%Y-%m-%d")
    
    # 1. 加载数据
    snapshot = load_snapshot()
    if not snapshot:
        return
    
    # 2. 读取A2候选池，确定今天评价哪些币
    a2_report_path = A2_OUTPUT_DIR / f"{today}.md"
    candidate_symbols = []
    
    if a2_report_path.exists():
        text = a2_report_path.read_text()
        # 从报告中提取候选池币种
        in_candidates = False
        for line in text.split("\n"):
            if "### 🟢 候选池" in line:
                in_candidates = True
                continue
            if in_candidates:
                if "###" in line:
                    break
                if "|" in line and line.count("|") >= 3:
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 3 and parts[1] and parts[1] != "排名" and not parts[1].startswith(":"):
                        # 格式: | 排名 | 币种 | 赛道 | 总分 | ...
                        if parts[2].strip():
                            candidate_symbols.append(parts[2].strip())
    
    # 如果没有从A2解析到，用命令行参数或默认
    if not candidate_symbols:
        for arg in sys.argv[1:]:
            if arg.startswith("--candidates="):
                candidate_symbols = arg.split("=")[1].split(",")
    
    if not candidate_symbols:
        candidate_symbols = ["BTCUSDT", "ETHUSDT", "DOGEUSDT"]  # 兜底默认
    
    all_coins = snapshot.get("binance_top200", snapshot.get("binance_top50", []))
    
    # 3. 对每个候选币计算三维度评分
    results = []
    for symbol in candidate_symbols:
        coin = get_coin_data(snapshot, symbol)
        if not coin:
            continue
        
        vp_score = score_volume_price(coin, all_coins)
        trend_score = score_trend(coin)
        rr_score = estimate_rr(coin)
        
        # 三层加权汇总（80%权重）
        weighted_80 = vp_score * 0.40 + trend_score * 0.25 + rr_score * 0.15
        # 折算到80%满分
        weighted_80 = weighted_80 / 0.80
        
        # 估算LLM叙事后可能的综合分
        # 如果叙事好（打80分）则：composite = weighted_80 * 0.80 + 80 * 0.20
        if_strong_narrative = round(weighted_80 * 0.80 + 80 * 0.20, 1)
        if_weak_narrative = round(weighted_80 * 0.80 + 30 * 0.20, 1)
        
        results.append({
            "symbol": symbol,
            "price": float(coin["price"]),
            "change_24h": float(coin["change_pct"]),
            "volume_rank_in_top50": next((i+1 for i, c in enumerate(sorted(all_coins, key=lambda x: float(x.get("volume",0)), reverse=True)) if c["symbol"] == symbol), 50),
            # 维度1: 量价结构 (40%)
            "vp_score": vp_score,
            "vp_label": "放量上涨" if vp_score >= 80 else ("吸筹" if vp_score >= 65 else ("健康整理" if vp_score >= 50 else ("危险" if vp_score < 30 else "中性"))),
            # 维度2: 趋势位置 (25%)
            "trend_score": trend_score,
            "trend_label": "最佳窗口" if trend_score >= 85 else ("埋伏" if trend_score >= 70 else ("可入" if trend_score >= 60 else ("不追" if trend_score < 30 else "中性"))),
            # 维度3: 叙事 (20%) → LLM判断，留空
            "narrative_score": None,
            "narrative_label": "待LLM判断",
            # 维度4: RR比 (15%)
            "rr_score": rr_score,
            "rr_label": "优质" if rr_score >= 80 else ("可接受" if rr_score >= 60 else ("一般" if rr_score >= 40 else ("放弃" if rr_score < 30 else "差"))),
            # 综合（80%权重已算，叙事部分由LLM补充）
            "composite_80pct": round(weighted_80, 1),
            "if_strong_narrative": if_strong_narrative,
            "if_weak_narrative": if_weak_narrative,
        })
    
    # 4. 输出JSON供A3 LLM读取
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"dim_scores_{today}.json"
    output_data = {
        "date": today,
        "generated_at": datetime.now(BJT).strftime("%H:%M BJT"),
        "note": "量价(40%)+趋势(25%)+RR(15%)=80%已脚本精确计算。叙事(20%)需LLM填入填入后补齐最终综合分",
        "data_source": "aws_snapshot.json (AWS→Binance API)",
        "market": {
            "fg_value": snapshot.get("fg_index", "?"),
            "fg_label": snapshot.get("fg_classification", "?"),
            "btc_price": f"${next((c['price'] for c in snapshot.get('binance_top200', snapshot.get('binance_top50',[])) if c['symbol']=='BTCUSDT'),'?')}",
        },
        "candidates": results,
    }
    
    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    # 打印摘要
    print(f"✅ A3维度评分完成 — {today}")
    print(f"数据源: {snapshot.get('source','?')}")
    for r in results:
        print(f"  {r['symbol']}: 量价{r['vp_score']} | 趋势{r['trend_score']} | RR{r['rr_score']} | 综合80%={r['composite_80pct']}")
        print(f"    叙事强→综合{r['if_strong_narrative']} 叙事弱→综合{r['if_weak_narrative']}")
    print(f"输出: {output_path}")
    print(f"提示: 量价(40%)+趋势(25%)+RR(15%)已脚本化，剩下叙事(20%)需A3 LLM填入dim_scores.json后补齐最终分")

if __name__ == "__main__":
    main()
