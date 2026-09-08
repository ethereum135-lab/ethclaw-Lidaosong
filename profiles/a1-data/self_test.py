#!/usr/bin/env python3
"""A1 数据官 self-test — 验证核心文件和目录完整性"""
import os, sys

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROFILE = os.path.join(BASE, "profiles", "a1-data")

errors = []
warnings = []

# 1. 核心文件
required_files = ["SOUL.md", "IDENTITY.md", "PERSONALITY.md", "AGENTS.md", "MEMORY.md", "config.yaml"]
for f in required_files:
    path = os.path.join(PROFILE, f)
    if os.path.exists(path):
        lines = open(path).read().count("\n") + 1
        print(f"✅ {f}: {lines}行")
    else:
        errors.append(f)
        print(f"❌ {f}: 缺失")

# 2. 目录
required_dirs = ["output", "logs", "memories"]
for d in required_dirs:
    path = os.path.join(PROFILE, d)
    if os.path.isdir(path):
        print(f"✅ {d}/")
    else:
        warnings.append(d)
        print(f"⚠️ {d}/: 缺失")

# 3. 配置文件
config_path = os.path.join(PROFILE, "config.yaml")
if os.path.exists(config_path):
    content = open(config_path).read()
    if "temperature: 0.3" in content:
        print("✅ config.yaml: temperature=0.3")
    if "fallback" in content:
        print("✅ config.yaml: 有fallback链")
    if "05:00" in content or "0 5" in content:
        print("✅ config.yaml: 采集cron配置")
    if "08:00" in content or "0 8" in content:
        print("✅ config.yaml: 学习cron配置")
    if "17:00" in content or "0 17" in content:
        print("✅ config.yaml: 自检cron配置")

# 4. 数据报告
output_dir = os.path.join(PROFILE, "output")
if os.path.isdir(output_dir):
    reports = [f for f in os.listdir(output_dir) if f.endswith(".md")]
    if reports:
        print(f"✅ output/: {len(reports)}份报告")
    else:
        warnings.append("output/空")
        print("⚠️ output/: 暂无报告（首次采集未到时间）")

# 5. 日志
log_file = os.path.join(PROFILE, "logs", "daily.log")
if os.path.exists(log_file):
    log_lines = open(log_file).read().count("\n")
    print(f"✅ logs/daily.log: {log_lines}行记录")

# 结果
print(f"\n{'='*40}")
if errors:
    print(f"🔴 失败: {len(errors)}项缺失")
    for e in errors:
        print(f"  - {e}")
elif warnings:
    print(f"🟡 通过（有警告）: {len(warnings)}项")
    for w in warnings:
        print(f"  - {w}")
else:
    print("✅ 全部通过")

sys.exit(0 if not errors else 1)
