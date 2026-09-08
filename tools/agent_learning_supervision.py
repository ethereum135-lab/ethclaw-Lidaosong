#!/usr/bin/env python3
"""
agent_learning_supervision.py — A5 全系统学习监督脚本

检查每个Agent的学习产出质量：
1. 学习笔记是否存在（profiles/*/output/learning_YYYY-MM-DD.md）
2. 最近学习时间
3. 学习笔记是否与Agent的职能匹配（粗略检查关键词）
4. 学习质量（行数、是否有具体内容而不是空模板）

用法:
    cd ~/zq_web4_trading_system && python3 tools/agent_learning_supervision.py

输出: 打印到stdout的markdown格式学习监督报告
"""

import os
import re
import sys
from datetime import datetime, timedelta
from typing import Any, Optional


# ── 路径配置 ──────────────────────────────────────────────
BASE_DIR = os.path.expanduser("~/zq_web4_trading_system")
PROFILES_DIR = os.path.join(BASE_DIR, "profiles")

NOW = datetime.now()
TODAY = NOW.strftime("%Y-%m-%d")
TODAY_DT = datetime.strptime(TODAY, "%Y-%m-%d")


# ── Agent 学习配置 ─────────────────────────────────────────
AGENT_LEARNING_CONFIG = [
    {
        "id": "A1",
        "name": "数据官",
        "dir": "a1-data",
        "职能": "数据采集API/数据可靠性/新数据源",
        "学习主题关键词": [
            "数据采集", "API", "数据源", "数据可靠性", "数据质量",
            "Alternative", "Binance", "CoinGecko", "数据管道",
            "数据验证", "数据清洗", "数据格式", "网络爬虫",
            "数据监控", "数据新鲜度", "数据一致性", "数据备份",
        ],
        "学习频率": "每日（但当前无独立学习cron）",
        "status": "活跃",
    },
    {
        "id": "A2",
        "name": "选币官",
        "dir": "a2-selector",
        "职能": "选币逻辑/市值评估/赛道分析",
        "学习主题关键词": [
            "选币", "选币逻辑", "市值评估", "赛道分析", "赛道轮动",
            "筛选算法", "评分模型", "因子分析", "五因子", "评分",
            "量化筛选", "成交量", "动量", "RSI", "资金费率",
            "板块轮动", "赛道热度", "硬过滤", "Stage",
        ],
        "学习频率": "已暂停（无learning文件）",
        "status": "已暂停",
    },
    {
        "id": "A3",
        "name": "牛币官",
        "dir": "a3-bull",
        "职能": "Paul Tudor Jones/基本面分析/趋势判断/牛币特征/仓位管理",
        "学习主题关键词": [
            "Paul Tudor Jones", "基本面分析", "趋势判断", "牛币特征",
            "仓位管理", "四维精选", "量价分析", "叙事逻辑",
            "风险回报", "F&G", "恐惧环境", "趋势突破",
            "精选", "牛币", "选币策略", "逆势",
        ],
        "学习频率": "已暂停（无learning文件）",
        "status": "已暂停",
    },
    {
        "id": "A4",
        "name": "交易官(Blade)",
        "dir": "a4-blade",
        "职能": "人物交易思维（7天轮换：CZ/V神/徐明星/孙宇晨/索罗斯/巴菲特/利弗莫尔）",
        "学习主题关键词": [
            "交易思维", "CZ", "V神", "徐明星", "孙宇晨",
            "索罗斯", "巴菲特", "利弗莫尔", "交易心理学",
            "执行", "交易执行", "滑点", "风控", "API",
            "仓位管理", "纪律", "四查", "Binance API",
            "市价单", "限价单", "交易策略", "执行质量",
        ],
        "学习频率": "每日08:00（cron: A4-交易官-每日学习）",
        "status": "活跃",
    },
    {
        "id": "A5",
        "name": "复盘官",
        "dir": "a5-review",
        "职能": "交易大师框架/决策质量评估/交易系统失败模式/芒格/工具评估方法/航空调查/量化回测",
        "学习主题关键词": [
            "复盘", "决策质量", "交易系统", "失败模式", "芒格",
            "查理芒格", "工具评估", "航空调查", "量化回测",
            "逆向思维", "心智模型", "监督评估", "交易心理学",
            "经验值", "DQW", "数据质量", "经验档案",
            "archive", "MASTER_EXPERIENCE", "退出信号",
        ],
        "学习频率": "每日08:00（cron: A5-复盘官-每日学习）",
        "status": "活跃（最近学习: 2026-05-13）",
    },
    {
        "id": "A6",
        "name": "审计官",
        "dir": "a6-audit",
        "职能": "审计方法论/交易系统审计/数据审计/合规审计",
        "学习主题关键词": [
            "审计", "审计方法论", "交易系统审计", "数据审计",
            "合规审计", "SRE", "监控", "告警", "可靠性工程",
            "偏差率", "覆盖率", "闭环", "检查清单",
            "审计报告", "偏差分析", "质量控制",
        ],
        "学习频率": "每周二/四08:00（cron: A6-审计官-学习）",
        "status": "活跃",
    },
    {
        "id": "A7",
        "name": "舆情官(Sentinel)",
        "dir": "a7-sentinel",
        "职能": "舆情监控方法/事件驱动交易/社交媒体情绪分析",
        "学习主题关键词": [
            "舆情监控", "事件驱动", "社交媒体情绪", "情绪分析",
            "KOL", "影响力评估", "推特监控", "新闻监控",
            "舆论", "舆情", "告警", "信号过滤",
            "F&G", "恐慌指数", "情绪指标", "噪音过滤",
        ],
        "学习频率": "已暂停（每周三/五08:00，但最近学习05-15）",
        "status": "已暂停",
    },
    {
        "id": "A8",
        "name": "资金官",
        "dir": "a8-fund",
        "职能": "链上数据分析/聪明钱追踪/机构持仓/Whale Alert/DeFi协议分析",
        "学习主题关键词": [
            "链上数据", "聪明钱", "聪明钱包", "机构持仓",
            "Whale Alert", "DeFi协议", "资金流向", "大额转账",
            "地址聚类", "链上分析", "持币分布", "巨鲸",
            "资金监控", "wallet", "onchain", "区块链分析",
        ],
        "学习频率": "已暂停（每周二/五08:00，但最近学习05-15）",
        "status": "已暂停",
    },
    {
        "id": "A9",
        "name": "学研官",
        "dir": "a9-research",
        "职能": "每周全网搜索新工具/新数据源/新策略+学习案例",
        "学习主题关键词": [
            "新工具", "新数据源", "新策略", "学习案例",
            "工具搜索", "策略搜索", "全网扫描", "工具评估",
            "交易工具", "交易策略", "数据API", "量化框架",
            "freqtrade", "回测", "Backtest",
        ],
        "学习频率": "每周一08:00（cron: A9-学研官-每周研究）",
        "status": "活跃（但无learning文件产出）",
    },
    {
        "id": "ZH",
        "name": "总指挥",
        "dir": "zh",
        "职能": "行业研判/系统设计/对标人物学习/赛道研究/市场分析",
        "学习主题关键词": [
            "行业研究", "行业研判", "赛道研究", "市场分析",
            "AI Agent", "DePIN", "对标人物", "CZ", "Dalio",
            "Tudor", "深度学习", "新赛道", "系统设计",
            "交易系统", "策略优化", "Agent调度",
        ],
        "学习频率": "每日15:00（cron: ZH-深度学习-15:00）",
        "status": "活跃",
    },
]


# ── 学习质量评分函数 ──────────────────────────────────────

def find_learning_files(agent_dir: str) -> list[dict]:
    """查找Agent output目录下的所有learning_YYYY-MM-DD.md文件"""
    output_dir = os.path.join(agent_dir, "output")
    learning_files = []

    if not os.path.isdir(output_dir):
        return learning_files

    for fname in os.listdir(output_dir):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(output_dir, fname)
        if not os.path.isfile(fpath):
            continue

        # Match learning_YYYY-MM-DD.md or learning_YYYY-MM-DD-HH.md
        m = re.match(r"learning_(\d{4}-\d{2}-\d{2})(?:-\d{2})?\.md", fname)
        if m:
            date_str = m.group(1)
            try:
                file_dt = datetime.strptime(date_str, "%Y-%m-%d")
                stat_info = os.stat(fpath)
                learning_files.append({
                    "name": fname,
                    "path": fpath,
                    "date": date_str,
                    "datetime": file_dt,
                    "mtime": datetime.fromtimestamp(stat_info.st_mtime),
                    "size": stat_info.st_size,
                })
            except ValueError:
                continue

    # Sort by date descending
    learning_files.sort(key=lambda x: x["date"], reverse=True)
    return learning_files


def analyze_learning_content(filepath: str) -> dict[str, Any]:
    """分析学习笔记的内容质量"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return {"lines": 0, "words": 0, "has_content": False, "is_template": True,
                "quality": "❌", "quality_label": "无法读取"}

    lines = content.strip().split("\n")
    non_empty_lines = [l for l in lines if l.strip()]
    total_lines = len(lines)
    total_chars = len(content)
    total_words = len(content.split())

    # Check if it's essentially empty / template
    has_content = total_chars > 200
    is_template = False

    # Detect template patterns (very short or mostly headers)
    template_indicators = 0
    if total_lines < 10:
        template_indicators += 2
    if total_chars < 500:
        template_indicators += 2
    if not re.search(r"[。，！？、：]", content) and total_chars < 1000:
        template_indicators += 1
    if content.count("待填写") > 0 or content.count("TODO") > 0:
        template_indicators += 2
    if re.search(r"^\s*#+\s*(学习笔记|学习日志|Learning)", content, re.MULTILINE) and total_chars < 800:
        template_indicators += 1

    is_template = template_indicators >= 3 or total_chars < 300

    # Extract keywords/themes from content
    topics_found = []
    topic_patterns = [
        (r"##\s+(.+?)(?:\n|$)", "章节标题"),
        (r"(?:学习主题|今日主题|主题)[：:]\s*(.+?)(?:\n|$)", "主题"),
        (r"(?:核心要点|学到的|关键发现)[：:：]?\s*(.+?)(?:\n|$)", "核心要点"),
        (r"(?:对标|人物|大师)[：:]?\s*(.+?)(?:\n|$)", "对标人物"),
        (r"(?:影响|应用|接入|对.*系统)[：:]?\s*(.+?)(?:\n|$)", "系统影响"),
    ]
    for pat, label in topic_patterns:
        found = re.findall(pat, content)
        for f in found[:3]:
            clean = f.strip()[:60]
            if clean:
                topics_found.append(f"{label}: {clean}")

    # Determine content substance level
    substance_score = 0
    if total_chars > 5000:
        substance_score += 3
    elif total_chars > 2000:
        substance_score += 2
    elif total_chars > 800:
        substance_score += 1

    if len(non_empty_lines) > 50:
        substance_score += 2
    elif len(non_empty_lines) > 20:
        substance_score += 1

    if re.search(r"[。，！？]", content) and total_chars > 1000:
        substance_score += 1

    if re.search(r"(?:---|___|\*\*\*)", content):
        substance_score += 1  # Has structural separators

    # Quality score
    if is_template:
        quality = "❌"
        quality_label = "空模板/无实质内容"
    elif substance_score >= 5:
        quality = "⭐"
        quality_label = "丰富有深度"
    elif substance_score >= 3:
        quality = "✅"
        quality_label = "有具体内容"
    elif substance_score >= 1:
        quality = "⚠️"
        quality_label = "内容简短"
    else:
        quality = "❌"
        quality_label = "几乎无内容"

    return {
        "lines": total_lines,
        "chars": total_chars,
        "words": total_words,
        "non_empty_lines": len(non_empty_lines),
        "has_content": has_content,
        "is_template": is_template,
        "substance_score": substance_score,
        "quality": quality,
        "quality_label": quality_label,
        "topics_found": topics_found[:5],
    }


def check_topic_relevance(content: str, keywords: list[str]) -> dict[str, Any]:
    """检查学习笔记内容与Agent职能关键词的匹配度"""
    content_lower = content.lower()
    matched = []
    missing = []

    for kw in keywords:
        if kw.lower() in content_lower:
            matched.append(kw)
        else:
            missing.append(kw)

    match_rate = len(matched) / len(keywords) * 100 if keywords else 0

    if match_rate >= 30:
        relevance = "✅ 高度匹配"
    elif match_rate >= 10:
        relevance = "🟡 部分匹配"
    elif match_rate > 0:
        relevance = "⚠️ 低度匹配"
    else:
        relevance = "❌ 不匹配"

    return {
        "matched_keywords": matched[:10],
        "missing_keywords_count": len(missing),
        "match_rate": round(match_rate, 1),
        "relevance": relevance,
    }


# ============================================================
#  主监督流程
# ============================================================

def supervise_agent(config: dict) -> dict[str, Any]:
    """监督单个Agent的学习状态"""
    agent_id = config["id"]
    agent_dir = os.path.join(PROFILES_DIR, config["dir"])

    result: dict[str, Any] = {
        "id": agent_id,
        "name": config["name"],
        "职能": config["职能"],
        "学习频率": config["学习频率"],
        "状态": config["status"],
        "learning_files": [],
        "最新学习": None,
        "质量评分": "❌ 缺失",
        "匹配度": "—",
        "建议": [],
    }

    # Find all learning files
    learning_files = find_learning_files(agent_dir)
    result["learning_files"] = learning_files

    # A4特判（2026-08-09 A5审查修复）：A4每日学习产出自2026-05-18起写入 agents/a4/learning_today.md（每日覆盖写），
    # 非 profiles/a4-blade/output/learning_YYYY-MM-DD.md。脚本按旧路径查找永远报「从未学习」= 持久假阳性。
    if not learning_files and agent_id == "A4":
        alt_path = os.path.join(BASE_DIR, "agents", "a4", "learning_today.md")
        if os.path.isfile(alt_path):
            alt_mtime = datetime.fromtimestamp(os.stat(alt_path).st_mtime)
            learning_files.append({
                "name": "learning_today.md",
                "path": alt_path,
                "date": alt_mtime.strftime("%Y-%m-%d"),
                "datetime": alt_mtime.replace(hour=0, minute=0, second=0, microsecond=0),
                "mtime": alt_mtime,
                "size": os.stat(alt_path).st_size,
            })
            result["learning_files"] = learning_files
            result.setdefault("备注", []).append(
                "A4学习产出=agents/a4/learning_today.md(每日覆盖写,按mtime计入),非profiles目录"
            )

    if not learning_files:
        result["最新学习"] = "❌ 从未学习"
        result["质量评分"] = "❌ 缺失"
        result["建议"].append("无任何学习笔记产出，需要建立学习cron和模板")
        return result

    # Latest learning file
    latest = learning_files[0]
    days_since = (TODAY_DT - latest["datetime"]).days
    result["最新学习"] = {
        "date": latest["date"],
        "file": latest["name"],
        "days_ago": days_since,
        "mtime": latest["mtime"].strftime("%Y-%m-%d %H:%M"),
    }

    # Analyze latest learning content
    content_analysis = analyze_learning_content(latest["path"])
    result["content_analysis"] = content_analysis

    # Check topic relevance
    try:
        with open(latest["path"], "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        content = ""

    if content:
        relevance = check_topic_relevance(content, config["学习主题关键词"])
        result["匹配度"] = relevance
    else:
        result["匹配度"] = {"relevance": "❌ 无法读取", "matched_keywords": [], "match_rate": 0}

    # Determine overall quality
    quality = content_analysis["quality"]
    if days_since > 7:
        quality = "❌"
        quality_label = f"已{days_since}天未学习"
        result["建议"].append(f"已{days_since}天未产出学习笔记，学习cron可能已停")
    elif days_since > 3:
        if quality != "❌":
            quality = "⚠️"
        quality_label = f"已{days_since}天未学习"
        result["建议"].append(f"学习停留在{latest['date']}，建议检查cron是否正常运行")
    else:
        quality_label = content_analysis["quality_label"]

    result["质量评分"] = f"{quality} {quality_label}"

    # Add relevance-based suggestions
    if content and result["匹配度"].get("match_rate", 0) < 10:
        result["建议"].append("学习内容与Agent职能关键词匹配度低，建议校准学习方向")

    # Analyze freshness-based quality
    if quality == "⭐" and days_since <= 1:
        result["true_quality"] = "⭐"
    elif quality in ("⭐", "✅") and days_since <= 3:
        result["true_quality"] = "✅"
    elif quality == "⚠️" or days_since <= 7:
        result["true_quality"] = "⚠️"
    else:
        result["true_quality"] = "❌"

    return result


def print_learning_report(all_results: list[dict[str, Any]]):
    """打印完整的Markdown学习监督报告"""
    agent_count = len(all_results)
    active_learners = sum(1 for r in all_results if r.get("true_quality") in ("⭐", "✅"))
    stalled = sum(1 for r in all_results if r.get("true_quality") == "❌")
    warning = sum(1 for r in all_results if r.get("true_quality") == "⚠️")

    print(f"# 📚 ZQ 全系统学习监督报告")
    print()
    print(f"**报告时间:** {NOW.strftime('%Y-%m-%d %H:%M')} BJT")
    print(f"**监督范围:** {agent_count}个Agent")
    print(f"**整体状态:** {active_learners}个正常 / {warning}个注意 / {stalled}个缺失")
    print()

    # ── 总体概览表 ──
    print("## 📊 学习状态总览")
    print()
    print("| Agent | 学习状态 | 最近学习 | 质量评分 | 职能匹配 | 整体 |")
    print("|-------|---------|---------|---------|---------|------|")
    for r in all_results:
        latest_str = r["最新学习"]
        if isinstance(latest_str, dict):
            date_str = latest_str["date"]
            days = latest_str["days_ago"]
            if days == 0:
                latest_display = f"✅ 今日 ({date_str})"
            elif days == 1:
                latest_display = f"🟡 昨日 ({date_str})"
            elif days <= 3:
                latest_display = f"⚠️ {days}天前 ({date_str})"
            else:
                latest_display = f"❌ {days}天前 ({date_str})"
        else:
            latest_display = latest_str

        quality = r["质量评分"]
        match = r["匹配度"]
        if isinstance(match, dict):
            match_display = match["relevance"]
        else:
            match_display = str(match)

        tq = r.get("true_quality", "❌")
        overall = {"⭐": "🟢", "✅": "🟢", "⚠️": "🟡", "❌": "🔴"}.get(tq, "⚪")

        print(f"| {r['id']} {r['name']} | {r['状态']} | {latest_display} | {quality} | {match_display} | {overall} |")
    print()

    # ── 逐Agent详细报告 ──
    print("---")
    print()
    print("## 🔍 逐Agent学习详情")
    print()

    for r in all_results:
        print(f"### {r['id']} — {r['name']}")
        print()
        print(f"**职能:** {r['职能']}")
        print(f"**学习频率:** {r['学习频率']}")
        print(f"**状态:** {r['状态']}")
        print()

        # 最新学习
        latest = r["最新学习"]
        if isinstance(latest, dict):
            days_label = "今天" if latest["days_ago"] == 0 else f"{latest['days_ago']}天前"
            print(f"**最近学习日期:** {latest['date']} ({days_label})")
            print(f"**笔记文件:** {latest['file']}")
        else:
            print(f"**最近学习:** {latest}")
        print()

        # 质量评分
        print(f"**质量评分:** {r['质量评分']}")
        if "content_analysis" in r:
            ca = r["content_analysis"]
            print(f"**笔记详情:** {ca['lines']}行 / {ca['chars']}字符 / {ca['non_empty_lines']}非空行")
            if ca.get("topics_found"):
                print()
                print("**识别到的主题:**")
                for t in ca["topics_found"]:
                    print(f"  - {t}")
        print()

        # 职能匹配度
        match = r["匹配度"]
        if isinstance(match, dict):
            print(f"**职能匹配度:** {match['relevance']}")
            print(f"**关键词匹配率:** {match['match_rate']}%")
            if match.get("matched_keywords"):
                print(f"**匹配关键词:** {', '.join(match['matched_keywords'][:6])}")
        print()

        # 学习笔记文件列表
        if r["learning_files"]:
            print("**历史学习记录:**")
            for lf in r["learning_files"][:5]:  # Show last 5
                print(f"  - {lf['date']}: {lf['name']}")
            if len(r["learning_files"]) > 5:
                print(f"  - ... 还有{len(r['learning_files']) - 5}次更早的记录")
        else:
            print("**历史学习记录:** 无")
        print()

        # 建议
        if r["建议"]:
            print("**建议:**")
            for s in r["建议"]:
                print(f"  - {s}")
        print()

        print("---")
        print()

    # ── 汇总分析 ──
    print("## 📈 整体学习质量分析")
    print()

    # 按质量分组
    star = [r for r in all_results if r.get("true_quality") == "⭐"]
    check = [r for r in all_results if r.get("true_quality") == "✅"]
    warn = [r for r in all_results if r.get("true_quality") == "⚠️"]
    missing = [r for r in all_results if r.get("true_quality") == "❌"]

    if star:
        print("### ⭐ 优秀学习者")
        print()
        for r in star:
            print(f"- **{r['id']} {r['name']}** — {r['质量评分']}")
        print()

    if check:
        print("### ✅ 正常学习者")
        print()
        for r in check:
            print(f"- **{r['id']} {r['name']}** — {r['质量评分']}")
        print()

    if warn:
        print("### ⚠️ 需要注意的学习者")
        print()
        for r in warn:
            print(f"- **{r['id']} {r['name']}** — {r['质量评分']}")
            for s in r["建议"]:
                print(f"  - {s}")
        print()

    if missing:
        print("### ❌ 学习缺失的Agent")
        print()
        for r in missing:
            print(f"- **{r['id']} {r['name']}** — {r['质量评分']}")
            for s in r["建议"]:
                print(f"  - {s}")
        print()

    # ── 整体建议 ──
    print("## 🎯 整体建议")
    print()

    print("### 高优先级")
    print()
    high_priority = [r for r in all_results if r.get("true_quality") == "❌"]
    if high_priority:
        for r in high_priority:
            print(f"1. **{r['id']} {r['name']}**: {r['质量评分']} — {'; '.join(r['建议'])}")
    else:
        print("- 暂无高优先级问题")

    print()
    print("### 中优先级")
    print()
    mid_priority = [r for r in all_results if r.get("true_quality") == "⚠️"]
    if mid_priority:
        for r in mid_priority:
            print(f"1. **{r['id']} {r['name']}**: {r['质量评分']} — {'; '.join(r['建议'])}")
    else:
        print("- 暂无中优先级问题")

    print()
    print("### 学习恢复建议")
    print()
    print("""
| 已暂停Agent | 建议 | 触发恢复条件 |
|-------------|------|-------------|
| A2 选币官 | 选币逻辑随市场变化需持续优化 | A3反馈候选池质量下降时 |
| A3 牛币官 | 精选方法论需跟踪最前沿量化策略 | A5推荐准确率<40%时 |
| A7 舆情官 | 舆情监控方法需跟上社交媒体变化 | 重大新闻漏报时 |
| A8 资金官 | 链上分析工具快速迭代 | A5复盘发现资金流向数据不足时 |
""".strip())
    print()
    print("### 优秀学习案例")
    print()
    print("以下Agent的学习笔记质量较高，可作为模板参考：")
    for r in star:
        if isinstance(r["最新学习"], dict):
            print(f"- **{r['id']} {r['name']}** ({r['最新学习']['date']}): {r['content_analysis']['lines']}行笔记, 主题匹配度{r['匹配度']['match_rate']}%")
    print()

    print("---")
    print(f"*监督完毕: {agent_count}个Agent, ⭐{len(star)}优秀, ✅{len(check)}正常, ⚠️{len(warn)}注意, ❌{len(missing)}缺失*")


# ============================================================
#  Main
# ============================================================

def main():
    results = []
    for config in AGENT_LEARNING_CONFIG:
        result = supervise_agent(config)
        results.append(result)
    print_learning_report(results)


if __name__ == "__main__":
    main()
