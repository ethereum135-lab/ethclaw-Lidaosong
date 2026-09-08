#!/usr/bin/env python3
"""A3 牛币官 自检脚本 — 验证6文件完整性+目录结构"""
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
FILES = ["SOUL.md", "IDENTITY.md", "PERSONALITY.md", "AGENTS.md", "MEMORY.md", "config.yaml"]
DIRS = ["logs", "memories", "output"]

errors = []
warnings = []

print("=" * 50)
print("A3 牛币官 - 自检脚本")
print("=" * 50)

# 1. 检查6份核心文件
print("\n[1/3] 检查6份核心文件...")
for f in FILES:
    path = os.path.join(BASE, f)
    if os.path.exists(path):
        with open(path) as fp:
            lines = len(fp.readlines())
        print(f"  ✅ {f} ({lines}行)")
    else:
        errors.append(f"缺失: {f}")
        print(f"  ❌ 缺失: {f}")

# 2. 检查目录结构
print("\n[2/3] 检查目录结构...")
for d in DIRS:
    path = os.path.join(BASE, d)
    if os.path.isdir(path):
        print(f"  ✅ {d}/")
    else:
        warnings.append(f"目录不存在: {d}")
        print(f"  ⚠️ 不存在: {d}/")

# 3. 检查配置文件
print("\n[3/3] 检查配置文件...")
config_path = os.path.join(BASE, "config.yaml")
if os.path.exists(config_path):
    with open(config_path) as fp:
        content = fp.read()
    checks = {
        "cron配置": "cron:" in content,
        "路径配置": "paths:" in content,
        "四维权重": "weights:" in content,
        "R/R阈值": "risk_reward:" in content,
        "量价阈值": "volume_price:" in content,
    }
    for name, ok in checks.items():
        print(f"  {'✅' if ok else '❌'} {name}")

# 结果
print("\n" + "=" * 50)
if errors:
    print(f"❌ 失败: {len(errors)}个错误")
    for e in errors:
        print(f"   - {e}")
    sys.exit(1)
else:
    print(f"✅ 全部通过 ({len(FILES)}文件 + {len(DIRS)}目录)")
    if warnings:
        for w in warnings:
            print(f"  ⚠️ {w}")
    sys.exit(0)
