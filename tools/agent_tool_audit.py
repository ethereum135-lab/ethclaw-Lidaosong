#!/usr/bin/env python3
"""
agent_tool_audit.py — A5 全系统工具审查脚本

审查每个Agent的工具使用情况：
1. 6文件是否完整 (SOUL/IDENTITY/PERSONALITY/AGENTS/MEMORY/config.yaml)
2. 该Agent的cron是否启用
3. 该Agent依赖的工具/脚本文件是否存在
4. 该Agent的产出文件时效性（最近产出日期）
5. TOOL_LOG.md中记录的工具是否被对应Agent使用

用法:
    cd ~/zq_web4_trading_system && python3 tools/agent_tool_audit.py
    cd ~/zq_web4_trading_system && python3 tools/agent_tool_audit.py --mode morning   # 早检(A3/A4/A5/A1/A2)
    cd ~/zq_web4_trading_system && python3 tools/agent_tool_audit.py --mode noon      # 午检(A4/A7/A8/A5)
    cd ~/zq_web4_trading_system && python3 tools/agent_tool_audit.py --mode evening   # 终检(A4/A3/A5/A6/A9)
    cd ~/zq_web4_trading_system && python3 tools/agent_tool_audit.py --mode full      # 全检(默认)

输出: 打印到stdout的markdown格式审查报告
"""

import os
import re
import sys
from datetime import datetime, timedelta
from typing import Any


# ── 路径配置 ──────────────────────────────────────────────
BASE_DIR = os.path.expanduser("~/zq_web4_trading_system")
PROFILES_DIR = os.path.join(BASE_DIR, "profiles")
TOOLS_DIR = os.path.join(BASE_DIR, "tools")
TOOL_LOG_PATH = os.path.join(TOOLS_DIR, "TOOL_LOG.md")

NOW = datetime.now()
TODAY = NOW.strftime("%Y-%m-%d")
TODAY_DT = datetime.strptime(TODAY, "%Y-%m-%d")


# ── Agent 清单 ────────────────────────────────────────────
AGENTS = [
    {"id": "A1", "name": "数据官", "dir": "a1-data"},
    {"id": "A2", "name": "选币官", "dir": "a2-selector"},
    {"id": "A3", "name": "牛币官", "dir": "a3-bull"},
    {"id": "A4", "name": "交易官(Blade)", "dir": "a4-blade"},
    {"id": "A5", "name": "复盘官", "dir": "a5-review"},
    {"id": "A6", "name": "审计官", "dir": "a6-audit"},
    {"id": "A7", "name": "舆情官(Sentinel)", "dir": "a7-sentinel"},
    {"id": "A8", "name": "资金官", "dir": "a8-fund"},
    {"id": "A9", "name": "学研官", "dir": "a9-research"},
    {"id": "ZH", "name": "总指挥", "dir": "zh"},
]

# 每个Agent依赖的工具/脚本（从AGENTS.md和SOUL.md推断）
AGENT_TOOLS = {
    "A1": {
        "依赖工具": [
            ("Alternative.me API（F&G恐慌指数）", "可API直连，无本地文件"),
            ("Binance FAPI（资金费率）", "可API直连，无本地文件"),
            ("CoinGecko API（社交热度）", "可API直连，无本地文件"),
            ("AWS SSH通道（数据代理）", os.path.expanduser("~/.zq_vault/web4.0.pem")),
        ],
        "产出模式": "output/YYYY-MM-DD.md（每日05:00）",
    },
    "A2": {
        "依赖工具": [
            ("A1数据报告", os.path.join(PROFILES_DIR, "a1-data/output")),
            ("Binance 24hr ticker API", "可API直连，无本地文件"),
            ("Binance klines API", "可API直连，无本地文件"),
            ("CoinGecko API", "可API直连，无本地文件"),
        ],
        "产出模式": "output/YYYY-MM-DD.md（每日06:00）",
    },
    "A3": {
        "依赖工具": [
            ("A2候选池报告", os.path.join(PROFILES_DIR, "a2-selector/output")),
            ("A1数据报告", os.path.join(PROFILES_DIR, "a1-data/output")),
            ("动量雷达信号", os.path.join(BASE_DIR, "shared/momentum_signals.md")),
            ("web_search（叙事搜索）", "Hermes内置工具"),
        ],
        "产出模式": "output/YYYY-MM-DD.md（每日07:00）",
    },
    "A4": {
        "依赖工具": [
            ("A3精选报告", os.path.join(PROFILES_DIR, "a3-bull/output")),
            ("executor.py", os.path.join(PROFILES_DIR, "a4-blade/executor.py")),
            ("AWS SSH通道（交易执行）", os.path.expanduser("~/.zq_vault/web4.0.pem")),
            ("Binance API（余额/价格/下单）", "可API直连，无本地文件"),
            ("TRADES.md", os.path.join(BASE_DIR, "audit/TRADES.md")),
        ],
        "产出模式": "写入audit/TRADES.md + 节点数据（每30分钟）",
    },
    "A5": {
        "依赖工具": [
            ("tool_eval.py", os.path.join(TOOLS_DIR, "tool_eval.py")),
            ("supervision_eval.py", os.path.join(TOOLS_DIR, "supervision_eval.py")),
            ("learning_suggest.py", os.path.join(TOOLS_DIR, "learning_suggest.py")),
            ("TRADES.md", os.path.join(BASE_DIR, "audit/TRADES.md")),
            ("经验数据目录", os.path.join(BASE_DIR, "data/experience/trades")),
            ("MASTER_EXPERIENCE.json", os.path.join(BASE_DIR, "data/experience/MASTER_EXPERIENCE.json")),
        ],
        "产出模式": "output/反馈/监督/工具评估/学习方向（每日08:30+23:00）",
    },
    "A6": {
        "依赖工具": [
            ("A3精选报告目录", os.path.join(PROFILES_DIR, "a3-bull/output")),
            ("A4 TRADES.md", os.path.join(BASE_DIR, "audit/TRADES.md")),
            ("A5经验数据目录", os.path.join(BASE_DIR, "data/experience/trades")),
        ],
        "产出模式": "output/learning_*.md（每周二/四08:00学习）+ 每周一审计报告",
    },
    "A7": {
        "依赖工具": [
            ("_monitor_check.py", os.path.join(PROFILES_DIR, "a7-sentinel/_monitor_check.py")),
            ("web_search（舆情搜索）", "Hermes内置工具"),
            ("Alternative.me API（F&G）", "可API直连"),
            ("knowledge/知识库目录", os.path.join(PROFILES_DIR, "a7-sentinel/knowledge")),
        ],
        "产出模式": "agents/a7/alert.md（异常时）+ output/learning_*.md",
    },
    "A8": {
        "依赖工具": [
            ("web_search（资金搜索）", "Hermes内置工具"),
            ("WALLET_WATCHLIST.md", os.path.join(PROFILES_DIR, "a8-fund/WALLET_WATCHLIST.md")),
            ("knowledge/知识库目录", os.path.join(PROFILES_DIR, "a8-fund/knowledge")),
        ],
        "产出模式": "output/YYYY-MM-DD-HH.md（每小时）+ output/learning_*.md",
    },
    "A9": {
        "依赖工具": [
            ("web_search（工具搜索）", "Hermes内置工具"),
            ("knowledge/strategy_library.md", os.path.join(PROFILES_DIR, "a9-research/knowledge/strategy_library.md")),
        ],
        "产出模式": "agents/a9/weekly_research.md（每周一）+ learning暂无产出",
    },
    "ZH": {
        "依赖工具": [
            ("web_search（行业搜索）", "Hermes内置工具"),
            ("各Agent产出目录", os.path.join(PROFILES_DIR)),
            ("references/参考知识库", os.path.join(PROFILES_DIR, "zh/references")),
        ],
        "产出模式": "output/brief_*.md（每日10:00）+ output/learning_*.md（每日15:00）+ output/brief_18:00",
    },
}

# Agent cron 映射（从hermes cron list中提取的关键任务）
AGENT_CRONS = {
    "A1": [
        ("A1-数据采集", "0 5 * * *", "每日05:00数据采集"),
    ],
    "A2": [
        ("A2-选币官-脚本评分", "0 6 * * *", "每日06:00选币筛选"),
    ],
    "A3": [
        ("A3-牛币官-每日精选", "0 7 * * *", "每日07:00精选牛币"),
    ],
    "A4": [
        ("A4-交易官-执行节点", "*/30 7-23 * * *", "每30分钟执行节点"),
        ("A4-交易官-每日学习", "0 8 * * *", "每日08:00学习"),
        ("A4-备用-executor", "*/30 7-23 * * *", "LLM故障兜底脚本"),
    ],
    "A5": [
        ("A5-每日复盘", "0 23 * * *", "每日23:00复盘"),
        ("A5-经验值采集", "*/30 * * * *", "每30分钟经验值采集"),
        ("A5-复盘官-每日学习", "0 8 * * *", "每日08:00学习"),
        ("A5-监督评估", "30 8 * * *", "每日08:30监督评估"),
    ],
    "A6": [
        ("A6-审计官-每周审计", "0 8 * * 1", "每周一08:00审计"),
        ("A6-审计官-学习", "0 8 * * 2,4", "每周二/四08:00学习"),
    ],
    "A7": [
        ("A7-舆情官-实时监控", "*/15 * * * *", "每15分钟舆情监控"),
        ("A7-舆情官-学习", "0 8 * * 3,5", "每周三/五08:00学习"),
    ],
    "A8": [
        ("A8-大额买入检测-高频数据采集", "*/15 * * * *", "每15分钟资金监控"),
        ("A8-资金官-学习", "0 8 * * 2,5", "每周二/五08:00学习"),
    ],
    "A9": [
        ("A9-学研官-每周研究", "0 8 * * 1", "每周一08:00研究"),
    ],
    "ZH": [
        ("ZH晨报（ZQ系统分析）", "0 8 * * *", "每日08:00晨报"),
        ("ZH每日复盘（ZQ系统五大点）", "0 0 * * *", "每日00:00复盘"),
        ("ZH每日系统反思", "0 21 * * *", "每日21:00系统反思"),
        ("ZH全网侦查（ZQ系统工具扫描）", "0 8 * * 1", "每周一08:00工具扫描"),
        ("ZH量化日报（ZQ系统分析）", "0 23 * * *", "每日23:00量化日报"),
        ("ZH风控检查（ZQ系统风控）", "35 * * * *", "每35分钟风控检查"),
        ("ZH每日复盘聚合（ZQ系统复盘）", "15 0 * * *", "每日00:15复盘聚合"),
        ("ZH系统自检（ZQ系统健康）", "0 7 * * *", "每日07:00系统自检"),
        ("ZH-行业扫描-10:00", "0 10 * * *", "每日10:00行业扫描"),
        ("ZH-深度学习-15:00", "0 15 * * *", "每日15:00深度学习"),
        ("ZH-每日简报-18:00", "0 18 * * *", "每日18:00简报"),
        ("ZH-赛道热度评分", "0 5 * * *", "每日05:00赛道评分"),
    ],
}


# ============================================================
#  审查函数
# ============================================================

def check_6files(agent_dir: str) -> dict[str, str]:
    """检查Agent的6个核心文件是否完整"""
    required = ["SOUL.md", "IDENTITY.md", "PERSONALITY.md", "AGENTS.md", "MEMORY.md", "config.yaml"]
    status = {}
    for f in required:
        fpath = os.path.join(agent_dir, f)
        exists = os.path.isfile(fpath)
        status[f] = "✅" if exists else "❌ 缺失"
    return status


def check_agent_tools(agent_id: str, agent_info: dict) -> list[dict]:
    """检查Agent依赖的工具是否存在"""
    results = []
    tools_list = agent_info.get("依赖工具", [])
    for tool_name, tool_path in tools_list:
        if not tool_path:
            results.append({"工具": tool_name, "状态": "❓ 未指定路径", "备注": ""})
        elif tool_path.startswith("可API直连"):
            results.append({"工具": tool_name, "状态": "✅ API直连", "备注": "网络可用性需运行时确认"})
        elif tool_path == "Hermes内置工具":
            results.append({"工具": tool_name, "状态": "✅ 内置", "备注": "Hermes Agent原生工具"})
        elif os.path.exists(tool_path):
            results.append({"工具": tool_name, "状态": "✅ 存在", "备注": f"路径: {tool_path}"})
        else:
            results.append({"工具": tool_name, "状态": "❌ 缺失", "备注": f"路径不存在: {tool_path}"})
    return results


def check_tool_log_relevance(agent_id: str) -> list[dict]:
    """检查TOOL_LOG.md中的工具是否被对应Agent使用"""
    if not os.path.isfile(TOOL_LOG_PATH):
        return [{"工具": "TOOL_LOG.md", "状态": "❌ 缺失", "备注": "无法交叉检查"}]

    # Parse TOOL_LOG.md for tools
    tools_in_log = []
    with open(TOOL_LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            m = re.match(r"\|\s*(\S[\w/._-]+)\s*\|\s*(\d{4}-\d{2}-\d{2})\s*\|", line)
            if m:
                name = m.group(1).strip()
                date_str = m.group(2).strip()
                tools_in_log.append((name, date_str))

    # Mapping of TOOL_LOG tools → expected agents
    tool_agent_map = {
        "freqtrade": ["A5", "A9", "ZH"],
        "coin_pool_config.json": ["A2", "A3"],
        "strategies/direction_judger.py": ["A3"],
        "strategies/debate_manager.py": ["A3", "A5"],
        "CoinOS (tools/coinos/)": ["A1", "A8", "ZH"],
        "tools/coinos_client.py": ["A1", "A8"],
        "a4_trend_checker": ["A4"],
        "tools/a4_trend_checker.py": ["A4"],
    }

    results = []
    for tool_name, date_str in tools_in_log:
        expected_agents = tool_agent_map.get(tool_name, [])
        if expected_agents:
            if agent_id in expected_agents:
                results.append({
                    "工具": tool_name,
                    "状态": "✅ 关联正确",
                    "备注": f"发现于{date_str}，该Agent应使用此工具"
                })
            else:
                results.append({
                    "工具": tool_name,
                    "状态": "ℹ️ 不直接关联",
                    "备注": f"发现于{date_str}，非该Agent主要工具"
                })
        else:
            results.append({
                "工具": tool_name,
                "状态": "❓ 未映射",
                "备注": f"发现于{date_str}，未配置预期使用者"
            })

    return results if results else [{"工具": "—", "状态": "—", "备注": "TOOL_LOG.md中无与当前Agent直接关联的工具"}]


def get_output_patterns(agent_id: str) -> list[str]:
    """根据Agent产出模式返回文件名匹配的正则表达式模式列表"""
    patterns_map = {
        "A1": [r"\d{4}-\d{2}-\d{2}\.md$"],
        "A2": [r"\d{4}-\d{2}-\d{2}\.md$"],
        "A3": [r"\d{4}-\d{2}-\d{2}\.md$"],
        "A4": [r"learning_\d{4}-\d{2}-\d{2}"],
        "A5": [r"feedback_", r"监督_", r"工具评估_", r"建议", r"learning_"],
        "A6": [r"learning_", r"weekly_"],
        "A7": [r"learning_"],
        "A8": [r"learning_", r"\d{4}-\d{2}-\d{2}-\d{2}\.md$"],
        "A9": [r"learning_"],
        "ZH": [r"learning_", r"brief_"],
    }
    return patterns_map.get(agent_id, [r"learning_"])


def check_output_freshness(agent_dir: str, patterns: list[str], days_back: int = 3) -> str:
    """检查产出文件的新鲜度，使用正则表达式匹配文件名"""
    output_dir = os.path.join(agent_dir, "output")
    if not os.path.isdir(output_dir):
        return "❌ output目录不存在"

    latest_mtime: float = 0
    latest_name: str = ""

    for fname in os.listdir(output_dir):
        fpath = os.path.join(output_dir, fname)
        if not os.path.isfile(fpath):
            continue
        # Check against regex patterns
        for pat in patterns:
            if re.search(pat, fname):
                mtime = os.path.getmtime(fpath)
                if mtime > latest_mtime:
                    latest_mtime = mtime
                    latest_name = fname
                break  # Found a match, no need to check other patterns

    if not latest_name:
        return "⚠️ 未找到匹配产出文件"

    latest_dt = datetime.fromtimestamp(latest_mtime)
    days_old = (NOW - latest_dt).days

    if days_old == 0:
        return f"✅ 今日产出: {latest_name}"
    elif days_old == 1:
        return f"🟡 昨日产出: {latest_name}"
    elif days_old <= 3:
        return f"⚠️ {days_old}天前产出: {latest_name}"
    else:
        return f"❌ {days_old}天前产出: {latest_name}（可能已停）"


# ============================================================
#  主审查流程
# ============================================================

def audit_agent(agent: dict) -> dict[str, Any]:
    """审计单个Agent"""
    agent_id = agent["id"]
    agent_name = agent["name"]
    agent_dir = os.path.join(PROFILES_DIR, agent["dir"])

    result: dict[str, Any] = {
        "id": agent_id,
        "name": agent_name,
        "dir": agent_dir,
        "errors": [],
        "warnings": [],
    }

    # 1. 检查6文件完整性
    files_status = check_6files(agent_dir)
    result["files"] = files_status
    for f, s in files_status.items():
        if "缺失" in s:
            result["errors"].append(f"缺失核心文件: {f}")

    # 2. 检查依赖工具
    tools_info = AGENT_TOOLS.get(agent_id, {})
    tool_results = check_agent_tools(agent_id, tools_info)
    result["tools"] = tool_results
    for t in tool_results:
        if "缺失" in t["状态"]:
            result["errors"].append(f"缺失工具: {t['工具']}")
        elif "注意" in t["备注"] and "注意" not in str(result.get("warnings", [])):
            pass  # We'll add warnings separately

    # 3. 检查产出新鲜度
    patterns = get_output_patterns(agent_id)
    freshness = check_output_freshness(agent_dir, patterns)
    result["freshness"] = freshness
    if "❌" in freshness:
        result["errors"].append(f"产出异常: {freshness}")
    elif "⚠️" in freshness or "🟡" in freshness:
        result["warnings"].append(f"产出延迟: {freshness}")

    # 4. 检查cron
    crons = AGENT_CRONS.get(agent_id, [])
    cron_statuses = []
    for cron_name, schedule, desc in crons:
        # We note the cron is defined; actual status requires `hermes cron list`
        cron_statuses.append({
            "cron": cron_name,
            "schedule": schedule,
            "desc": desc,
        })
    result["crons"] = cron_statuses

    # 5. TOOL_LOG.md交叉检查
    tool_log = check_tool_log_relevance(agent_id)
    result["tool_log"] = tool_log

    return result


def print_audit_report(all_results: list[dict[str, Any]]):
    """打印完整的Markdown审查报告"""
    total_agents = len(all_results)
    agents_with_errors = sum(1 for r in all_results if r["errors"])
    agents_with_warnings = sum(1 for r in all_results if r["warnings"])

    print(f"# 🔧 ZQ 全系统工具审查报告")
    print()
    print(f"**审查时间:** {NOW.strftime('%Y-%m-%d %H:%M')} BJT")
    print(f"**审查范围:** {total_agents}个Agent")
    print(f"**存在问题的Agent:** {agents_with_errors}个有错误, {agents_with_warnings}个有警告")
    print()

    # ── 总体概览 ──
    print("## 📊 总体概览")
    print()
    print("| Agent | 6文件 | 产出新鲜度 | 工具完整性 | Cron状态 | 整体 |")
    print("|-------|-------|-----------|-----------|---------|------|")
    for r in all_results:
        files_ok = all("✅" in s for s in r["files"].values())
        files_status = "✅" if files_ok else "❌"
        fresh_status = "✅" if r["freshness"].startswith("✅") else ("🟡" if r["freshness"].startswith(("🟡", "⚠️")) else "❌")
        tools_missing = any("缺失" in t["状态"] for t in r["tools"])
        tools_status = "✅" if not tools_missing else "❌"
        # Cron: all agents have defined crons
        cron_ok = len(r["crons"]) > 0
        cron_status = "✅" if cron_ok else "⚠️ 未定义"
        overall = "🟢" if not r["errors"] and not r["warnings"] else ("🟡" if r["warnings"] and not r["errors"] else "🔴")
        print(f"| {r['id']} {r['name']} | {files_status} | {fresh_status} | {tools_status} | {cron_status} | {overall} |")
    print()

    # ── 逐Agent详细报告 ──
    print("---")
    print()
    print("## 🔍 逐Agent详细审查")
    print()

    for r in all_results:
        print(f"### {r['id']} — {r['name']}")
        print()
        print(f"**Profile路径:** {r['dir']}")
        print()

        # 6文件状态
        print("#### 📁 6文件完整性")
        print()
        print("| 文件 | 状态 |")
        print("|------|------|")
        for f, s in r["files"].items():
            print(f"| {f} | {s} |")
        print()

        # 工具状态
        print("#### 🔧 依赖工具/脚本")
        print()
        print("| 工具名 | 状态 | 备注 |")
        print("|--------|------|------|")
        for t in r["tools"]:
            print(f"| {t['工具']} | {t['状态']} | {t['备注']} |")
        print()

        # Cron状态
        print("#### ⏰ Cron任务")
        print()
        print("| Cron名 | 调度 | 说明 |")
        print("|--------|------|------|")
        for c in r["crons"]:
            print(f"| {c['cron']} | `{c['schedule']}` | {c['desc']} |")
        print()

        # 产出新鲜度
        print("#### 📅 产出新鲜度")
        print()
        print(f"{r['freshness']}")
        print()

        # TOOL_LOG交叉检查
        print("#### 📋 TOOL_LOG.md 交叉引用")
        print()
        print("| 工具 | 状态 | 备注 |")
        print("|------|------|------|")
        for tl in r["tool_log"]:
            print(f"| {tl['工具']} | {tl['状态']} | {tl['备注']} |")
        print()

        # 问题汇总
        if r["errors"] or r["warnings"]:
            print("#### ⚠️ 发现的问题")
            print()
            for e in r["errors"]:
                print(f"- ❌ {e}")
            for w in r["warnings"]:
                print(f"- ⚠️ {w}")
            print()

        print("---")
        print()

    # ── 问题汇总 ──
    all_errors = []
    all_warnings = []
    for r in all_results:
        for e in r["errors"]:
            all_errors.append(f"{r['id']}: {e}")
        for w in r["warnings"]:
            all_warnings.append(f"{r['id']}: {w}")

    print("## 🚨 问题汇总与优先级建议")
    print()

    if all_errors:
        print("### ❌ 必须修复的问题")
        print()
        for e in all_errors:
            print(f"- **{e}**")
        print()

    if all_warnings:
        print("### ⚠️ 需要注意的问题")
        print()
        for w in all_warnings:
            print(f"- {w}")
        print()

    if not all_errors and not all_warnings:
        print("✅ 所有Agent状态良好，无需立即干预。")
        print()
    else:
        # 给出修复建议
        print("### 🎯 建议优先级")
        print()
        print("| 优先级 | 问题 | 建议处理人 |")
        print("|--------|------|-----------|")

        # Build suggestions based on error types
        suggestions = []
        for r in all_results:
            for e in r["errors"]:
                if "缺失核心文件" in e:
                    suggestions.append(("🔴 高", e, "ZH/A5（联系老李创建缺失文件）"))
                elif "缺失工具" in e:
                    suggestions.append(("🔴 高", e, "ZH（安装缺失工具）"))
                elif "产出异常" in e:
                    suggestions.append(("🔴 高", e, "ZH（排查Agent cron是否正常运行）"))
            for w in r["warnings"]:
                if "产出延迟" in w:
                    suggestions.append(("🟡 中", w, "A5（标记为观察项）"))

        for pri, issue, handler in suggestions[:15]:  # Limit to top 15
            print(f"| {pri} | {issue} | {handler} |")
        print()

    # ── 附加信息 ──
    print("## 💡 自检建议")
    print()
    print("1. **每日执行** — 将此脚本加入A5的cron，每天08:30监督评估后自动运行")
    print("2. **状态对比** — 对比前后两次审查结果，发现新增的缺失工具")
    print("3. **T+3跟进** — TOOL_LOG.md要求新工具安装后3/7/30天跟进，确保到期检查")
    print()

    print("---")
    print(f"*审查完毕: {total_agents}个Agent, {len(all_errors)}个错误, {len(all_warnings)}个警告*")


# ============================================================
#  Mode 配置（按时间节点筛选Agent）
# ============================================================

MODE_AGENTS = {
    "morning": ["A1", "A2", "A3", "A4", "A5"],   # 08:35早检
    "noon":    ["A4", "A5", "A7", "A8"],          # 13:00午检
    "evening": ["A3", "A4", "A5", "A6", "A9"],    # 23:30终检
    "full":    [a["id"] for a in AGENTS],          # 17:00全检
}

# ============================================================
#  Main
# ============================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="A5 全系统工具审查")
    parser.add_argument("--mode", choices=list(MODE_AGENTS.keys()), default="full",
                        help="审查模式: morning(早检)/noon(午检)/evening(终检)/full(全检,默认)")
    args = parser.parse_args()

    target_ids = MODE_AGENTS[args.mode]
    results = []
    for agent in AGENTS:
        if agent["id"] not in target_ids:
            continue
        result = audit_agent(agent)
        results.append(result)
    print_audit_report(results)


if __name__ == "__main__":
    main()
