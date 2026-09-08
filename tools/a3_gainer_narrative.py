#!/usr/bin/env python3
"""
A3 涨幅归因分析层 v1.0 — 为什么涨 / 涨多久 / 能不能进
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

功能：
  在A3信号扫描(pure technical)之后，对涨幅榜前20和STRONG信号币做三维分析：
    1. 为什么涨 — 叙亊/赛道/新闻/资金面
    2. 涨多久了 — 日线连涨天数 + 阶段判断
    3. 接盘风险评估 — LOW / MEDIUM / HIGH

用法：
  python3 tools/a3_gainer_narrative.py                    # 默认读signals.json
  python3 tools/a3_gainer_narrative.py --quick            # 只看涨幅榜TOP10
  python3 tools/a3_gainer_narrative.py --output report.md # 输出到文件

输出：
  data/narrative_analysis.json — 结构化数据供下游使用
  data/narrative_report.md    — 人类可读报告

依赖：
  - 本地可访问 signals.json（已从AWS同步）
  - 日线数据走SSH到AWS获取（Binance API）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import json, os, sys, argparse, subprocess
from datetime import datetime, timezone, timedelta

# ─── 路径 ───
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
SIGNALS_PATH = os.path.join(DATA_DIR, "signals.json")
OUTPUT_JSON = os.path.join(DATA_DIR, "narrative_analysis.json")
OUTPUT_MD = os.path.join(DATA_DIR, "narrative_report.md")

BJT = timezone(timedelta(hours=8))
NOW = datetime.now(BJT)

# ├─ 赛道分类映射
SECTOR_MAP = {
    # AI / AI Agent
    "WLD": "AI-Agent-Identity",
    "FET": "AI-Agent-Framework", "AGIX": "AI-Agent", "OCEAN": "AI-Data",
    "AIXBT": "AI-Trading-Agent", "RENDER": "AI-Rendering", "GRT": "AI-Data-Index",
    "PHA": "AI-DePIN-Compute", "IO": "AI-DePIN-Compute",
    "TAO": "AI-Subnet", "NEAR": "AI-Agent", "GOAT": "AI-Meme",
    # DeFi
    "DYDX": "DeFi-Derivatives", "UNI": "DeFi-DEX", "AAVE": "DeFi-Lending",
    "MKR": "DeFi-Stablecoin", "CRV": "DeFi-StableSwap", "COMP": "DeFi-Lending",
    "SUSHI": "DeFi-DEX", "PENDLE": "DeFi-Yield", "ENA": "DeFi-Stablecoin",
    # L1/L2
    "TIA": "Modular-L1", "SOL": "L1-Solana", "ETH": "L1-Ethereum",
    "ARB": "L2-Arbitrum", "OP": "L2-Optimism", "MATIC": "L2-Polygon",
    "AVAX": "L1-Avalanche", "DOT": "L1-Polkadot", "NEAR": "L1-Near",
    # Meme / GameFi
    "HMSTR": "GameFi-Meme", "DOGE": "Meme", "SHIB": "Meme",
    "PEPE": "Meme", "FLOKI": "Meme", "WIF": "Meme", "BONK": "Meme",
    # Payment / Infra
    "REQ": "Payment-Infra", "XRP": "Payment", "XLM": "Payment",
    "ADA": "Infra-Cardano",
    # DeFi / DEX 补充
    "CREAM": "DeFi-Lending", "UTK": "Payment-Infra",
    # Meme / GameFi 补充
    "HMSTR": "GameFi-Meme", "DOGE": "Meme", "SHIB": "Meme",
    "PEPE": "Meme", "FLOKI": "Meme", "WIF": "Meme", "BONK": "Meme",
    "GENIUS": "Meme",
    # L1/L2 补充
    "FF": "DeFi-DEX", "FTM": "L1-Fantom", "S": "L1-Sonic",
    "SEI": "L1-Sei", "SUI": "L1-Sui", "APT": "L1-Aptos",
    "INJ": "L1-Injective",
    # AI / DePIN 补充
    "AKT": "AI-DePIN-Compute", "LPT": "AI-Video-Infra",
    # RWA / 实体资产
    "ONDO": "RWA", "OM": "RWA", "POLYX": "RWA",
    # Privacy
    "ZEC": "Privacy", "DASH": "Privacy", "XMR": "Privacy",
    # Cosmos / IBC
    "OSMO": "DeFi-DEX",
    # On-chain data / 链上解析
    "ARKM": "AI-Data-Index",
    # 其他—可扩展
}

# ├─ 叙亊关键词映射（快速判断）
NARRATIVE_KEYWORDS = {
    "AI-Agent-Identity": "Worldcoin全球身份协议+AI Agent赛道轮动",
    "AI-Agent-Framework": "Fetch.ai AI Agent框架、ASI Alliance生态",
    "AI-Rendering": "Render Network AI渲染算力网络",
    "AI-Data-Index": "The Graph AI数据索引协议",
    "AI-DePIN-Compute": "Phala/IO.net去中心化AI算力网络",
    "AI-Trading-Agent": "AIXBT AI交易Agent叙亊",
    "DeFi-Derivatives": "dYdX V4升级/Perp叙亊回暖",
    "DeFi-Lending": "DeFi借贷赛道全球TVL回升",
    "DeFi-DEX": "DEX交易量回暖、Uniswap V4",
    "Payment-Infra": "Request Network支付基建叙亊",
    "Modular-L1": "Celestia模块化区块链叙亊",
    "GameFi-Meme": "HMSTR TGE后叙亊/GameFi回暖",
    "Meme": "Memecoin赛道轮动/社区Fomo",
    "DeFi-Lending": "DeFi借贷赛道TVL回升、利率回暖",
    "L1-Sonic": "Sonic(S) L1新公链叙亊",
    "L1-Sei": "Sei并行EVM L1叙亊",
    "L1-Sui": "Sui Move生态叙亊",
    "L1-Aptos": "Aptos Move生态叙亊",
    "L1-Injective": "Injective跨链DeFi生态叙亊",
    "L1-Fantom": "Fantom Sonic升级叙亊",
    "AI-Video-Infra": "Livepeer AI视频基础设施叙亊",
    "RWA": "RWA（真实资产上链）赛道叙亊",
    "Privacy": "隐私赛道轮动/匿名叙亊",
    "AI-DePIN-Compute": "Akash/IO.net去中心化AI算力网络",
}

# ├─ 阶段判断阈值
PHASE_THRESHOLDS = {
    "early": {"max_green_days": 2, "max_7d_pump": 15},
    "mid":  {"max_green_days": 4, "max_7d_pump": 40},
    "late": {"max_green_days": 99, "max_7d_pump": 999},
}

# ─── 核心函数 ───

def now_bjt():
    return NOW.strftime("%Y-%m-%d %H:%M:%S")

def ssh_fetch_daily_data(symbol):
    """通过AWS SSH获取日K线（使用已部署的 fetch_daily.py 脚本）"""
    cmd = f"ssh -i ~/.zq_vault/web4.0.pem -o StrictHostKeyChecking=no -o BatchMode=yes -o ConnectTimeout=10 ubuntu@15.134.211.154 'python3 ~/scripts/fetch_daily.py {symbol} 10' 2>/dev/null"
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if not result.stdout.strip():
            return None
        data = json.loads(result.stdout.strip())
        if isinstance(data, dict) and "error" in data:
            return None
        return data
    except Exception as e:
        return None

def analyze_duration(daily_data):
    """分析涨了多久：连涨天数 + 阶段判断"""
    if not daily_data or len(daily_data) < 3:
        return {"days": 0, "green_streak": 0, "phase": "unknown",
                "change_1d": 0, "change_3d": 0, "change_7d": 0, "vol_ratio": 0}
    
    closes = [d["close"] for d in daily_data]
    
    # 连涨天数（从最新往前数）
    green_streak = 0
    for d in reversed(daily_data[-7:]):
        if d["change"] > 0:
            green_streak += 1
        else:
            break
    
    # 最近5天阳线数
    green_5d = sum(1 for d in daily_data[-5:] if d["change"] > 0)
    
    # 涨跌幅
    change_1d = daily_data[-1]["change"]
    change_3d = ((closes[-1] - closes[-3]) / closes[-3] * 100) if len(closes) >= 3 else 0
    change_7d = ((closes[-1] - closes[-7]) / closes[-7] * 100) if len(closes) >= 7 else 0
    
    # 成交量变化
    vols = [d["vol"] for d in daily_data]
    vol_today = vols[-1]
    vol_avg_7 = sum(vols[-7:]) / 7 if len(vols) >= 7 else vol_today
    vol_ratio = vol_today / vol_avg_7 if vol_avg_7 > 0 else 0
    
    # 阶段判断
    if change_7d >= 40 and green_streak >= 5:
        phase = "late"        # 🔴 可能见顶
    elif change_7d >= 15 or green_streak >= 3:
        phase = "mid"         # 🟡 中期上涨中
    elif change_1d > 5 or green_streak >= 1:
        phase = "early"       # 🟢 刚启动
    elif green_streak >= 1 and change_7d < 10:
        phase = "early"       # 🟢 温和上涨
    else:
        phase = "unknown"
    
    return {
        "green_streak": green_streak,
        "green_5d": green_5d,
        "phase": phase,
        "change_1d": round(change_1d, 2),
        "change_3d": round(change_3d, 2),
        "change_7d": round(change_7d, 2),
        "vol_ratio": round(vol_ratio, 2),
    }


def assess_entry_risk(duration, signal_score, volume_24h):
    """评估入场风险：LOW / MEDIUM / HIGH"""
    phase = duration["phase"]
    
    # 🔴 晚期 = 高接盘风险
    if phase == "late":
        return "HIGH", "连涨5天+7日涨超40%，已到末期，不要追"
    
    # 🟢 早期 + 高分 = 低风险
    if phase == "early" and signal_score >= 70:
        return "LOW", "刚启动+高分信号，有空间"
    if phase == "early" and signal_score >= 50:
        return "LOW", "刚启动，有叙亊支撑"
    if phase == "early":
        return "MEDIUM", "刚启动但信号不高，观察"

    # 🟡 中期 + 高分 = 中低风险
    if phase == "mid" and signal_score >= 70:
        # 检查成交量是否萎缩
        if duration["vol_ratio"] < 0.8:
            return "MEDIUM", "中期上涨但量萎缩→可能见顶"
        return "LOW", "中期上涨+量价配合OK"
    if phase == "mid" and signal_score >= 50:
        if duration["vol_ratio"] > 1.5:
            return "MEDIUM", "中期+量放大→可能还在加速中"
        return "MEDIUM", "中期上涨，需评估仓位"
    if phase == "mid":
        return "HIGH", "中期但评分低，不要追"
    
    # unknown
    return "MEDIUM", "数据不足，保守评估"


def get_narrative(symbol, sector, duration, signal_data):
    """生成叙亊分析"""
    sector_narrative = NARRATIVE_KEYWORDS.get(sector, f"{sector}赛道轮动/独立行情")
    
    # 基于成交量的持续性判断
    vol_trend = ""
    if signal_data and signal_data.get("volume_trend", {}).get("score", 0) >= 10:
        vol_trend = signal_data["volume_trend"]["detail"]
    
    # 阶段中文描述
    phase_cn = {"early": "🟢 刚启动/早期", "mid": "🟡 中期/加速中",
                "late": "🔴 晚期/可能见顶", "unknown": "⚪ 数据不足"}
    
    return {
        "sector": sector,
        "narrative": sector_narrative,
        "phase_cn": phase_cn.get(duration["phase"], "未知"),
        "vol_trend": vol_trend,
    }


def main():
    parser = argparse.ArgumentParser(description="A3 涨幅归因分析层")
    parser.add_argument("--quick", action="store_true", help="只看涨幅榜TOP10")
    parser.add_argument("--output", default="md", choices=["md", "json"], help="输出格式")
    parser.add_argument("--input", default=SIGNALS_PATH, help="输入signals.json路径")
    args = parser.parse_args()
    
    # 读信号数据
    if not os.path.exists(args.input):
        print(f"❌ 信号文件不存在: {args.input}")
        print("   请先运行 a3_signal_scanner.py 生成信号")
        sys.exit(1)
    
    with open(args.input) as f:
        signals = json.load(f)
    
    # 整理信号map
    signal_map = {}
    for r in signals.get("results", []):
        signal_map[r["symbol"]] = r
    
    # 涨幅榜优先（从信号中按24h涨幅排序）
    gainer_candidates = []
    for r in signals.get("results", []):
        ms = r.get("signals", {}).get("momentum_surge", {})
        detail = ms.get("detail", "")
        # 从detail中解析24h涨幅
        gain = 0
        if "24h+" in detail:
            try:
                gain_str = detail.split("24h+")[1].split("%")[0]
                gain = float(gain_str.replace("%",""))
                if "🔥" in detail:
                    gain *= 1.5  # 有🔥标记的加权
            except:
                pass
        gainer_candidates.append((gain, r["symbol"], r))
    
    gainer_candidates.sort(key=lambda x: x[0], reverse=True)
    
    # 取TOP
    top_n = 10 if args.quick else 20
    top_gainers = gainer_candidates[:top_n]
    
    # ─── 逐币分析 ───
    analyses = []
    errors = []
    
    print(f"📊 A3 涨幅归因分析 — {now_bjt()}\n")
    print(f"正在分析 {len(top_gainers)} 个币...\n")
    
    for gain, symbol, r_data in top_gainers:
        score = r_data["total_score"]
        level = r_data["level"]
        
        # 赛道识别
        sector = SECTOR_MAP.get(symbol, "Other")
        
        # 日线分析（走AWS SSH）
        daily = ssh_fetch_daily_data(symbol)
        
        # 如果失败，用信号数据推断
        if daily is None:
            # 从momentum_surge推断
            ms = r_data.get("signals", {}).get("momentum_surge", {})
            ms_score = ms.get("score", 0)
            # 从detail推断阶段
            detail = ms.get("detail", "")
            if "🔥" in detail:
                inferred_phase = "mid"
            elif ms_score >= 15:
                inferred_phase = "mid"
            elif ms_score >= 8:
                inferred_phase = "early"
            else:
                inferred_phase = "unknown"
            duration = {
                "green_streak": 0, "green_5d": 0, "phase": inferred_phase,
                "change_1d": gain, "change_3d": 0, "change_7d": 0, "vol_ratio": r_data.get("volume_24h", 1)
            }
        else:
            duration = analyze_duration(daily)
        
        # 入场风险评估
        risk_level, risk_reason = assess_entry_risk(duration, score, r_data.get("volume_24h", 0))
        
        # 叙亊分析
        narrative = get_narrative(symbol, sector, duration, r_data.get("signals", {}))
        
        # 组合
        analysis = {
            "symbol": symbol,
            "price": r_data.get("price", 0),
            "volume_24h": r_data.get("volume_24h", 0),
            "score": score,
            "level": level,
            "sector": sector,
            "narrative": narrative["narrative"],
            "phase": narrative["phase_cn"],
            "duration": duration,
            "risk_level": risk_level,
            "risk_reason": risk_reason,
            "signals_detail": r_data.get("signals", {}),
        }
        analyses.append(analysis)
        
        # 打印进度
        emoji = "🟢" if risk_level == "LOW" else "🟡" if risk_level == "MEDIUM" else "🔴"
        print(f"  {emoji} {symbol:6s} | {level:6s} {score:3d}分 | {narrative['phase_cn']} | 风险: {risk_level}")
    
    # ─── 输出 ───
    output = {
        "analyzed_at": now_bjt(),
        "total": len(analyses),
        "risk_summary": {
            "LOW": sum(1 for a in analyses if a["risk_level"] == "LOW"),
            "MEDIUM": sum(1 for a in analyses if a["risk_level"] == "MEDIUM"),
            "HIGH": sum(1 for a in analyses if a["risk_level"] == "HIGH"),
        },
        "analyses": analyses,
        "errors": errors,
        # A3推荐参考
        "a3_recommendation": {
            "可优先考虑": [a["symbol"] for a in analyses if a["risk_level"] == "LOW" and a["level"] in ("STRONG", "SIGNAL")],
            "谨慎考虑": [a["symbol"] for a in analyses if a["risk_level"] == "MEDIUM" and a["level"] in ("STRONG", "SIGNAL")],
            "规避": [a["symbol"] for a in analyses if a["risk_level"] == "HIGH"],
        },
    }
    
    # JSON
    with open(OUTPUT_JSON, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    # MD
    md_lines = [
        f"# 📊 A3 涨幅归因分析报告",
        f"**分析时间:** {now_bjt()}",
        f"**分析币数:** {len(analyses)} | 🟢 LOW={output['risk_summary']['LOW']} 🟡 MEDIUM={output['risk_summary']['MEDIUM']} 🔴 HIGH={output['risk_summary']['HIGH']}",
        "",
        "## 结论速览",
        ""
    ]
    
    for a in analyses:
        emoji = "🟢" if a["risk_level"] == "LOW" else "🟡" if a["risk_level"] == "MEDIUM" else "🔴"
        md_lines.append(f"### {emoji} {a['symbol']} — {a['risk_level']}风险 | {a['score']}分 {a['level']}")
        md_lines.append(f"- **价格:** ${a['price']:.4f} | 24h量: ${a['volume_24h']:,.0f}")
        md_lines.append(f"- **阶段:** {a['phase']}")
        md_lines.append(f"- **叙亊:** {a['narrative']}")
        md_lines.append(f"- **风险评估:** {a['risk_reason']}")
        
        dur = a.get('duration', {})
        if dur.get('green_streak', 0) > 0:
            md_lines.append(f"- **持续度:** 连涨{dur['green_streak']}天, 近5天{dur['green_5d']}天收阳, 1d+{dur.get('change_1d',0):+.1f}%")
        md_lines.append("")
    
    # A3推荐参考区（在for循环之后）
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("## A3推荐参考")
    md_lines.append("")
    if output["a3_recommendation"]["可优先考虑"]:
        md_lines.append(f"🟢 **可纳入推荐清单** — {' | '.join(output['a3_recommendation']['可优先考虑'])}")
    if output["a3_recommendation"]["谨慎考虑"]:
        md_lines.append(f"🟡 **谨慎纳入（需说明理由）** — {' | '.join(output['a3_recommendation']['谨慎考虑'])}")
    if output["a3_recommendation"]["规避"]:
        md_lines.append(f"🔴 **规避** — {' | '.join(output['a3_recommendation']['规避'])}")
    md_lines.append("")

    md_content = "\n".join(md_lines)
    with open(OUTPUT_MD, "w") as f:
        f.write(md_content)
    
    print(f"\n✅ 分析完成！输出:")
    print(f"   JSON: {OUTPUT_JSON}")
    print(f"   MD:   {OUTPUT_MD}")
    
    # 打印速览
    print(f"\n{'='*50}")
    print(f"速览 — 可入场 ({' | '.join(a['symbol'] for a in analyses if a['risk_level'] == 'LOW')})")
    print(f"观察 — ({' | '.join(a['symbol'] for a in analyses if a['risk_level'] == 'MEDIUM')})")
    print(f"🚫 不追 — ({' | '.join(a['symbol'] for a in analyses if a['risk_level'] == 'HIGH')})")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()
