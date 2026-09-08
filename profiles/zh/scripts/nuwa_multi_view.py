#!/usr/bin/env python3
"""Nuwa多视角市场分析 — 每日07:35执行"""
import json, os, glob, re
from pathlib import Path
from datetime import date

BASE = Path("/Users/lidaosong/zq_web4_trading_system")
A1_DIR = BASE / "profiles" / "a1-data" / "output"
A2_DIR = BASE / "profiles" / "a2-selector" / "output"
STATE_DIR = BASE / "state"
SHARED_DIR = BASE / "shared"
OUTPUT_DIR = BASE / "profiles" / "zh" / "output"

today = date.today().isoformat()

def read_market_data():
    data = {}

    # A1 outputs — latest files
    a1_files = sorted(A1_DIR.glob("*.json") + A1_DIR.glob("*.md") + A1_DIR.glob("*.txt"), reverse=True)
    a1_texts = []
    for f in a1_files[:5]:
        try:
            a1_texts.append(f"=== {f.name} ===\n" + f.read_text(encoding="utf-8", errors="replace")[:3000])
        except:
            pass
    data["a1"] = "\n\n".join(a1_texts)

    # A2 selector pool
    a2_files = sorted(A2_DIR.glob("*.json") + A2_DIR.glob("*.md") + A2_DIR.glob("*.txt"), reverse=True)
    a2_texts = []
    for f in a2_files[:3]:
        try:
            a2_texts.append(f"=== {f.name} ===\n" + f.read_text(encoding="utf-8", errors="replace")[:3000])
        except:
            pass
    data["a2"] = "\n\n".join(a2_texts)

    # state/a3.json
    a3_path = STATE_DIR / "a3.json"
    if a3_path.exists():
        data["a3"] = a3_path.read_text(encoding="utf-8", errors="replace")

    # persona_today.txt
    p_path = STATE_DIR / "persona_today.txt"
    if p_path.exists():
        data["persona_today"] = p_path.read_text(encoding="utf-8", errors="replace").strip()

    # ZH direction priority
    zh_files = sorted(SHARED_DIR.glob("direction_priority_*.md"), reverse=True)
    zh_texts = []
    for f in zh_files[:2]:
        try:
            zh_texts.append(f"=== {f.name} ===\n" + f.read_text(encoding="utf-8", errors="replace")[:3000])
        except:
            pass
    data["zh_direction"] = "\n\n".join(zh_texts)

    return data

data = read_market_data()

# Print market context for the model
print("=== A1 市场数据 ===")
print(data.get("a1", "N/A"))
print("\n=== A2 候选池 ===")
print(data.get("a2", "N/A"))
print("\n=== A3 信号 ===")
print(data.get("a3", "N/A"))
print("\n=== 今日轮训人物 ===")
print(data.get("persona_today", "N/A"))
print("\n=== ZH方向融合输出 ===")
print(data.get("zh_direction", "N/A"))
