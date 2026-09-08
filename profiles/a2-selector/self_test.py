#!/usr/bin/env python3
"""
A2 选币官 自检脚本
检查：6份核心文件完整性、目录结构、配置文件可读性
"""
import os
import sys
import yaml
import json

BASE = os.path.dirname(os.path.abspath(__file__))
TOTAL_CHECKS = 0
PASSED_CHECKS = 0

def check(condition, msg):
    global PASSED_CHECKS, TOTAL_CHECKS
    TOTAL_CHECKS += 1
    if condition:
        PASSED_CHECKS += 1
        print(f"  ✅ {msg}")
    else:
        print(f"  ❌ {msg}")

print("=" * 50)
print("A2 选币官 — 自检报告")
print(f"时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 50)

# === 1. 核心文件完整性 ===
print("\n📁 第1关：核心文件完整性")

required_files = [
    "SOUL.md", "IDENTITY.md", "PERSONALITY.md",
    "AGENTS.md", "MEMORY.md", "config.yaml"
]
for f in required_files:
    path = os.path.join(BASE, f)
    check(os.path.isfile(path), f"{f} 存在")
    if os.path.isfile(path):
        size = os.path.getsize(path)
        check(size > 100, f"{f} 大小正常 ({size} bytes)")

# === 2. 目录结构 ===
print("\n📂 第2关：目录结构")
required_dirs = ["output", "logs", "memories"]
for d in required_dirs:
    path = os.path.join(BASE, d)
    check(os.path.isdir(path), f"目录 {d}/ 存在")

# === 3. config.yaml 可读性 ===
print("\n⚙️  第3关：配置文件检查")
config_path = os.path.join(BASE, "config.yaml")
try:
    with open(config_path) as f:
        config = yaml.safe_load(f)
    check(config is not None, "config.yaml 可解析")
    check("model" in config, "model 配置存在")
    check("stage1" in config, "stage1 阈值配置存在")
    check("stage2" in config, "stage2 权重配置存在")
    check("cron" in config, "cron 任务配置存在")
    if "stage2" in config:
        weights = config["stage2"].get("weights", {})
        total_w = sum(weights.values())
        check(abs(total_w - 1.0) < 0.01, f"五因子权重合计={total_w:.2f} (应为1.0)")
except Exception as e:
    check(False, f"config.yaml 解析失败: {e}")

# === 4. SOUL/IDENTITY 禁区一致性 ===
print("\n🔒 第4关：禁区一致性检查")
for fname in ["SOUL.md", "IDENTITY.md", "MEMORY.md"]:
    path = os.path.join(BASE, fname)
    if os.path.isfile(path):
        content = open(path).read()
        has_forbidden = "不做最终买入决定" in content or "不交易" in content
        check(has_forbidden, f"{fname} 包含禁区声明")

# === 5. 两阶段逻辑完整性检查 ===
print("\n🎯 第5关：两阶段筛选法完整性检查")
agents_path = os.path.join(BASE, "AGENTS.md")
if os.path.isfile(agents_path):
    content = open(agents_path).read()
    check("Stage 1" in content, "AGENTS.md 包含Stage 1硬过滤")
    check("Stage 2" in content, "AGENTS.md 包含Stage 2五因子评分")
    check("候选池" in content, "AGENTS.md 包含候选池定义")
    check("待观察池" in content, "AGENTS.md 包含待观察池定义")
    check("排除" in content, "AGENTS.md 包含排除定义")
    check("成交量异常" in content, "AGENTS.md 包含成交量异常因子")
    check("动量结构" in content, "AGENTS.md 包含动量结构因子")
    check("费率健康" in content, "AGENTS.md 包含费率健康因子")
    check("RSI位置" in content, "AGENTS.md 包含RSI位置因子")
    check("热度修正" in content, "AGENTS.md 包含热度修正因子")

# === 6. 人格完整性 ===
print("\n🧠 第6关：人格完整性检查")
personality_path = os.path.join(BASE, "PERSONALITY.md")
if os.path.isfile(personality_path):
    content = open(personality_path).read()
    chapters = ["第一章", "第二章", "第三章", "第四章", "第五章",
                "第六章", "第七章", "第八章", "第九章"]
    for ch in chapters:
        check(ch in content, f"PERSONALITY.md 包含{ch}")

# === 总结 ===
print("\n" + "=" * 50)
print(f"📊 结果: {PASSED_CHECKS}/{TOTAL_CHECKS} 通过")
if PASSED_CHECKS == TOTAL_CHECKS:
    print("🎉 全部通过！A2 选币官可以上岗。")
else:
    print(f"⚠️  有 {TOTAL_CHECKS - PASSED_CHECKS} 项未通过，请检查。")
print("=" * 50)

# 写入日志
log_path = os.path.join(BASE, "logs", "self_check.log")
with open(log_path, "a") as f:
    f.write(f"{__import__('datetime').datetime.now().isoformat()} | {PASSED_CHECKS}/{TOTAL_CHECKS}\n")
