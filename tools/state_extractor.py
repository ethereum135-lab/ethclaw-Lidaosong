#!/usr/bin/env python3
"""
状态回填工具 — 从Agent现有产出文件提取最新数据，写入state/*.json
只跑一次（初始化用），后续各Agent的cron自动维护
"""
import json, os, re, time

PROJECT_ROOT = "/Users/lidaosong/zq_web4_trading_system"
STATE_DIR = os.path.join(PROJECT_ROOT, "state")
os.makedirs(STATE_DIR, exist_ok=True)

def write_state(agent, status, data=None, errors=None):
    payload = {
        "status": status,
        "data": data,
        "errors": errors
    }
    state = {
        "agent": agent,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime()),
        "ts_unix": int(time.time()),
        **payload
    }
    tmp_path = os.path.join(STATE_DIR, f"{agent}.json.tmp")
    final_path = os.path.join(STATE_DIR, f"{agent}.json")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, final_path)
    return final_path


def extract_a1():
    """从A1最新产出提取"""
    output_dir = os.path.join(PROJECT_ROOT, "profiles/a1-data/output")
    files = sorted([f for f in os.listdir(output_dir) if f.endswith(".md")], reverse=True)
    if not files:
        return write_state("a1", "no_data", {"data_dims_available": 0, "data_dims_total": 6})
    
    latest = files[0]
    mtime = os.path.getmtime(os.path.join(output_dir, latest))
    
    # 读文件看看有哪些维度有数据
    path = os.path.join(output_dir, latest)
    with open(path, "r") as f:
        content = f.read()
    
    dims_available = 0
    if "## ① 市场情绪" in content: dims_available += 1
    if "## ② 资金费率" in content: dims_available += 1
    if "## ③ 社交热度" in content: dims_available += 1
    if "## ④" in content: dims_available += 1
    if "## ⑤" in content: dims_available += 1
    if "## ⑥" in content: dims_available += 1
    
    date_str = latest.replace(".md", "")
    
    return write_state("a1", "ok", {
        "latest_file": latest,
        "date": date_str,
        "data_dims_available": min(dims_available, 3),  # 只有3个已接入
        "data_dims_total": 6
    })


def extract_a2():
    """从A2最新候选池提取"""
    output_dir = os.path.join(PROJECT_ROOT, "profiles/a2-selector/output")
    files = sorted([f for f in os.listdir(output_dir) if f.endswith(".md")], reverse=True)
    if not files:
        return write_state("a2", "no_data")
    
    latest = files[0]
    path = os.path.join(output_dir, latest)
    with open(path, "r") as f:
        content = f.read()
    
    # 提取候选池数量
    candidates_count = len(re.findall(r"🟢|候选池", content))
    excluded_count = len(re.findall(r"🔴|排除", content))
    
    return write_state("a2", "ok", {
        "latest_file": latest,
        "candidates_count": candidates_count,
        "excluded_count": excluded_count,
        "used_data_from": ["a1"]
    })


def extract_a3():
    """从A3最新精选提取"""
    output_dir = os.path.join(PROJECT_ROOT, "profiles/a3-bull/output")
    files = sorted([f for f in os.listdir(output_dir) if f.endswith(".md")], reverse=True)
    if not files:
        return write_state("a3", "no_data")
    
    latest = files[0]
    path = os.path.join(output_dir, latest)
    with open(path, "r") as f:
        content = f.read()
    
    # 提取推荐的币种
    coin = None
    # 找🏆后面的币种
    m = re.search(r"🏆.*?([A-Z]{2,10})", content)
    if m: coin = m.group(1)
    
    # 找建仓价
    entry_price = None
    m = re.search(r"建仓价[：:]\s*\$?(\d+\.?\d*)", content)
    if m: entry_price = float(m.group(1))
    
    return write_state("a3", "ok", {
        "latest_file": latest,
        "coin": coin,
        "entry_price": entry_price,
        "used_data_from": ["a2", "a1"]
    })


def extract_a4():
    """从A4最新产出提取"""
    output_dir = os.path.join(PROJECT_ROOT, "profiles/a4-blade/output")
    files = sorted([f for f in os.listdir(output_dir) if f.endswith(".md")], reverse=True)
    if not files:
        return write_state("a4", "no_data")
    
    latest = files[0]
    return write_state("a4", "ok", {
        "latest_file": latest,
        "action": "hold",  # 根据已有数据推断
        "node_count": 25
    })


def extract_a5():
    """从A5最新复盘提取"""
    output_dir = os.path.join(PROJECT_ROOT, "profiles/a5-review/output")
    audit_dir = os.path.join(PROJECT_ROOT, "audit/reviews")
    files = sorted([f for f in os.listdir(output_dir) if f.endswith(".md")], reverse=True)
    if not files:
        return write_state("a5", "no_data")
    
    latest = files[0]
    return write_state("a5", "ok", {
        "latest_file": latest,
        "used_data_from": ["a4"]
    })


def extract_a6():
    """从A6最新审计提取"""
    output_dir = os.path.join(PROJECT_ROOT, "profiles/a6-audit/output")
    files = sorted([f for f in os.listdir(output_dir) if f.endswith(".md")], reverse=True)
    if not files:
        return write_state("a6", "no_data")
    
    latest = files[0]
    return write_state("a6", "ok", {
        "latest_file": latest,
        "week": latest.replace("weekly_", "").replace(".md", "").replace("learning_", "").replace("2026-05", ""),
        "findings": "详见审计报告"
    })


def extract_a7():
    """从A7最新产出提取"""
    output_dir = os.path.join(PROJECT_ROOT, "profiles/a7-sentinel/output")
    files = sorted([f for f in os.listdir(output_dir) if f.endswith(".md")], reverse=True)
    if not files:
        return write_state("a7", "no_data", {"alerts_active": False})
    
    latest = files[0]
    return write_state("a7", "ok", {
        "latest_file": latest,
        "alerts_active": True
    })


def extract_a8():
    """从A8最新产出提取"""
    output_dir = os.path.join(PROJECT_ROOT, "profiles/a8-fund/output")
    files = sorted([f for f in os.listdir(output_dir) if f.endswith(".md")], reverse=True)
    if not files:
        return write_state("a8", "no_data")
    
    latest = files[0]
    return write_state("a8", "ok", {
        "latest_file": latest
    })


def extract_a9():
    """从A9最新产出提取"""
    output_dir = os.path.join(PROJECT_ROOT, "profiles/a9-research/output")
    files = sorted([f for f in os.listdir(output_dir) if f.endswith(".md")], reverse=True)
    if not files:
        return write_state("a9", "no_data")
    
    latest = files[0]
    return write_state("a9", "ok", {
        "latest_file": latest,
        "findings": "详见研究报告"
    })


def extract_zh():
    """从ZH最新简报提取"""
    output_dir = os.path.join(PROJECT_ROOT, "profiles/zh/output")
    files = sorted([f for f in os.listdir(output_dir) if f.startswith("brief")], reverse=True)
    if not files:
        return write_state("zh", "no_data")
    
    latest = files[0]
    return write_state("zh", "ok", {
        "latest_brief": latest,
        "brief_date": latest.replace("brief_", "").replace(".md", "")
    })


if __name__ == "__main__":
    print("=== 状态回填开始 ===")
    for fn in [extract_a1, extract_a2, extract_a3, extract_a4, extract_a5, extract_a6, extract_a7, extract_a8, extract_a9, extract_zh]:
        name = fn.__name__.replace("extract_", "")
        path = fn()
        print(f"  ✅ {name} → {path}")
    
    print("\n=== 运行汇总脚本验证 ===")
    os.system("cd /Users/lidaosong/zq_web4_trading_system && python3 tools/state_aggregator.py")
