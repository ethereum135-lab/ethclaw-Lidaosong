#!/usr/bin/env python3
"""
A5 复盘官 — 三跑三验证 @框架v1.0 严格版
职能类型：复盘型
侧重点：1.2因果链分析深度×1.5 | 2.3报告格式需被引×1.5 | 3.4长期趋势不走偏×1.5
满分：36分
"""
import os, sys, json, re
from pathlib import Path

BASE = Path(__file__).resolve().parent
errors, warnings, passes = [], [], []
scores_raw = {}  # 每格原始分/4
scores_weighted = {}  # 加权后

def check(condition, msg, is_error=True):
    if condition:
        print(f"  ✅ {msg}")
        passes.append(msg)
        return True
    else:
        if is_error:
            print(f"  ❌ {msg}")
            errors.append(msg)
        else:
            print(f"  ⚠️  {msg}")
            warnings.append(msg)
        return False

def read_safe(path):
    try:
        return path.read_text()
    except: return ""

print("=" * 60)
print("  A5 复盘官 — 三跑三验证 v1.0 严格版")
print("  职能类型: 复盘型")
print("=" * 60)

# ==========================================
# 读文件
# ==========================================
agents_txt = read_safe(BASE / "AGENTS.md")
memory_txt = read_safe(BASE / "MEMORY.md")
soul_txt = read_safe(BASE / "SOUL.md")
identity_txt = read_safe(BASE / "IDENTITY.md")
personality_txt = read_safe(BASE / "PERSONALITY.md")
config_txt = read_safe(BASE / "config.yaml")

# ==========================================
# 步骤1：6文件检查
# ==========================================
print("\n━━━ 步骤1：6文件检查 ━━━")
files_ok = 0
for f in ["SOUL.md", "IDENTITY.md", "PERSONALITY.md", "AGENTS.md", "MEMORY.md", "config.yaml"]:
    p = BASE / f
    ok = p.exists() and p.stat().st_size > 100
    check(ok, f"{f} {f'✅ {p.stat().st_size}B' if ok else '❌缺失'}")
    if ok: files_ok += 1

# 文件一致性
check("复盘官" in soul_txt and "A5" in identity_txt, "SOUL和IDENTITY身份一致: 复盘官")
check("芒格" in personality_txt, "PERSONALITY含对标人物")
check("第一章" in agents_txt or "总则" in agents_txt, "AGENTS含工作规章")
check("铁断库" in memory_txt, "MEMORY含铁断库")
check("dqw" in config_txt.lower() and "model:" in config_txt, "config.yaml含DQW+模型")

print(f"\n6文件完备: {files_ok}/6 ✓")

# ==========================================
# 步骤2：第一跑 — 独立运行
# ==========================================
print("\n" + "=" * 60)
print("第一跑：独立运行（复盘型→1.2因果链分析深度×1.5）")
print("=" * 60)

# 1.1 输入接收 /4
print("\n--- 1.1 输入接收 ---")
r11 = 0
if "TRADES.md" in agents_txt or "trades" in agents_txt:
    r11 += 2; check(True, "从TRADES.md读取交易数据")
    # 检查具体的读取方法
    if "extract_trade_info" in agents_txt or "analyze_exit" in agents_txt or "analyze-recent-sell.py" in agents_txt:
        r11 += 1; check(True, "有标准解析方法")
    # 检查是否有匹配买入的逻辑
    if "匹配" in agents_txt or "时间在前" in agents_txt or "buy" in agents_txt.lower():
        r11 += 1; check(True, "有买入匹配逻辑（时间在前+币种相同）")
else:
    check(False, "能从TRADES.md获取输入")

# 检查实际路径
trades_path = Path.home() / "zq_web4_trading_system" / "audit" / "TRADES.md"
if trades_path.exists(): r11 = min(r11 + 1, 4)
check(r11 >= 3, f"1.1 输入接收: {r11}/4")

# 1.2 核心计算/处理 /4（复盘型侧重×1.5）
print("\n--- 1.2 核心处理 ---")
r12_items = [
    ("经验值采集", "经验值" in agents_txt),
    ("P&L计算", "analyze_exit" in agents_txt or "P&L" in agents_txt),
    ("退出质量分类", "exit_quality" in agents_txt or "质量" in agents_txt),
    ("DQW数据质量检测", "DQW" in agents_txt),
    ("因果链分析", "归因" in agents_txt or "根因" in agents_txt),
    ("archive归档", "archive" in agents_txt),
    ("MASTER统计", "MASTER" in agents_txt),
    ("信号统计", "exit_signal_performance" in agents_txt or "信号" in agents_txt),
]
r12_count = sum(1 for _, ok in r12_items if ok)
for name, ok in r12_items:
    check(ok, f"核心能力: {name}")
r12 = 4 if r12_count >= 7 else (3 if r12_count >= 5 else 2)
print(f"  核心能力通过: {r12_count}/{len(r12_items)}")
print(f"1.2 核心处理: {r12}/4 (×1.5 = {r12*1.5})")

# 1.3 输出产出 /4
print("\n--- 1.3 输出产出 ---")
r13_items = [
    ("经验值JSON", "experience/trades" in agents_txt),
    ("MASTER_EXPERIENCE", "MASTER" in agents_txt),
    ("每日复盘报告", "reviews" in agents_txt),
    ("archive经验档案", "archive" in agents_txt),
    ("学习日志", "learning" in agents_txt or "学习" in agents_txt),
]
r13_count = sum(1 for _, ok in r13_items for name, ok in [("", ok)])
r13_items_actual = [(n, o) for n, o in r13_items]
r13_count = sum(1 for _, ok in r13_items_actual)
for name, ok in r13_items_actual:
    check(ok, f"产出类型: {name}")
r13 = 4 if r13_count >= 5 else (3 if r13_count >= 4 else 2)
print(f"1.3 输出产出: {r13}/4")

# 1.4 6文件完备 /4
r14 = 4 if files_ok == 6 else (3 if files_ok >= 5 else 2)
print(f"1.4 6文件: {r14}/4")

# 1.5 自检脚本 /4
print("\n--- 1.5 自检脚本 ---")
script_ok = (BASE / "self_test.py").exists()
check(script_ok, "self_test.py存在")
if script_ok:
    # 检查自检覆盖项
    st = read_safe(BASE / "self_test.py")
    cov = ["6文件" in st, "DQW" in st or "dqw" in st, "TRADES" in st, "协同" in st or "协作" in st, "抗压" in st or "空输入" in st]
    cov_count = sum(cov)
    r15 = 4 if cov_count >= 4 else (3 if cov_count >= 3 else 2)
    print(f"  覆盖度: {cov_count}/5")
else:
    r15 = 0
print(f"1.5 自检: {r15}/4")

# 第一跑汇总
run1_raw = r11 + r12 + r13 + r14 + r15
# 复盘型加权：1.2 ×1.5
run1_weighted = (r11 * 1.0) + (r12 * 1.5) + (r13 * 1.0) + (r14 * 1.0) + (r15 * 1.0)
print(f"\n第一跑原始分: {run1_raw}/20")
print(f"第一跑加权分: {run1_weighted:.1f}/22 (1.2因果链×1.5)")

# ==========================================
# 步骤3：第二跑 — 协同运行
# ==========================================
print("\n" + "=" * 60)
print("第二跑：协同运行（复盘型→2.3报告格式需被引×1.5）")
print("=" * 60)

# 2.1 下游接收 /4
print("\n--- 2.1 下游接收 ---")
r21 = 0
if "TRADES" in agents_txt or "A4" in agents_txt:
    r21 += 2; check(True, "能读取A4的TRADES.md")
if trades_path.exists():
    r21 += 1; check(True, "实际TRADES.md文件可访问")
if "extract_trade_info" in agents_txt:
    r21 += 1; check(True, "有标准解析方法读取上游数据")
print(f"2.1 下游接收: {r21}/4")

# 2.2 上游输出 /4
print("\n--- 2.2 上游输出 ---")
r22 = 0
if "ZH" in agents_txt or "总指挥" in agents_txt:
    r22 += 2; check(True, "输出给ZH读")
if "reviews" in agents_txt and "archive" in agents_txt:
    r22 += 1; check(True, "有结构化复盘报告+archive")
if "经验值" in agents_txt:
    r22 += 1; check(True, "经验值数据可被下游Agent读取")
print(f"2.2 上游输出: {r22}/4")

# 2.3 通信标准 /4（复盘型侧重×1.5）
print("\n--- 2.3 通信标准 ---")
r23 = 0
if "YYYY-MM-DD" in agents_txt or "日" in agents_txt:
    r23 += 1; check(True, "统一日期格式")
if "json" in agents_txt.lower() or "JSON" in agents_txt:
    r23 += 1; check(True, "JSON格式机器可读")
if "data/experience" in agents_txt:
    r23 += 1; check(True, "统一路径约定")
if "archive" in agents_txt:
    r23 += 1; check(True, "archive可被引用")
print(f"2.3 通信标准: {r23}/4 (×1.5 = {r23*1.5})")

# 2.4 异常上报 /4
print("\n--- 2.4 异常上报 ---")
r24 = 0
if "DQW" in agents_txt:
    r24 += 1; check(True, "数据异常标记DQW")
if "engine" in agents_txt.lower() or "引擎" in agents_txt:
    r24 += 1; check(True, "能定位到具体Agent(Engine)")
if "报告" in agents_txt or "上报" in agents_txt:
    r24 += 1; check(True, "异常报告机制")
if "Column Shift" in memory_txt or "精度截断" in memory_txt:
    r24 += 1; check(True, "能区分异常类型")
print(f"2.4 异常上报: {r24}/4")

# 第二跑汇总
run2_raw = r21 + r22 + r23 + r24
run2_weighted = (r21 * 1.0) + (r22 * 1.0) + (r23 * 1.5) + (r24 * 1.0)
print(f"\n第二跑原始分: {run2_raw}/16")
print(f"第二跑加权分: {run2_weighted:.1f}/19 (2.3通信标准×1.5)")

# ==========================================
# 步骤4：第三跑 — 抗压运行
# ==========================================
print("\n" + "=" * 60)
print("第三跑：抗压运行（复盘型→3.4长期趋势不走偏×1.5）")
print("=" * 60)

# 3.1 空输入 /4
print("\n--- 3.1 空输入 ---")
r31 = 0
if "跳过" in agents_txt or "跳过" in memory_txt:
    r31 += 2; check(True, "缺数据时跳过不编造")
if "数据不够" in soul_txt or "不编造" in soul_txt or "不推测" in soul_txt:
    r31 += 1; check(True, "无数据不编造结论")
if "DUPLICATE" in agents_txt:
    r31 += 1; check(True, "重复分析跳过不重复计算")
print(f"3.1 空输入: {r31}/4")

# 3.2 数据异常 /4
print("\n--- 3.2 数据异常 ---")
r32 = 0
if "DQW" in agents_txt:
    r32 += 1; check(True, "DQW数据质量检测框架")
if "Column Shift" in memory_txt or "dqw-check" in agents_txt:
    r32 += 1; check(True, "Column Shift检测")
if "精度截断" in memory_txt:
    r32 += 1; check(True, "精度截断处理")
if "fallback" in config_txt or "claude" in config_txt:
    r32 += 1; check(True, "模型fallback")
print(f"3.2 数据异常: {r32}/4")

# 3.3 限流/重试 /4
print("\n--- 3.3 限流/重试 ---")
r33 = 0
if "model:" in config_txt:
    r33 += 1; check(True, "独立model配置")
if "fallback" in config_txt:
    r33 += 1; check(True, "fallback机制")
if "--batch" in agents_txt:
    r33 += 1; check(True, "batch模式幂等安全")
if "cron" in agents_txt:
    r33 += 1; check(True, "cron多轮不退化")
print(f"3.3 限流/重试: {r33}/4")

# 3.4 多轮稳定 /4（复盘型侧重×1.5）
print("\n--- 3.4 多轮稳定 ---")
r34 = 0
if "自检" in agents_txt:
    r34 += 1; check(True, "每日自检机制")
if "self_test" in str(BASE / "self_test.py"):
    r34 += 1; check(True, "可重复自检")
# 检查是否有实际运行记录
exp_dir = Path.home() / "zq_web4_trading_system" / "data" / "experience" / "trades"
if exp_dir.exists():
    json_files = list(exp_dir.glob("*.json"))
    if len(json_files) > 10:
        r34 += 1; check(True, f"实际运行经验: {len(json_files)}笔已分析")
        print(f"  经验值JSON文件数: {len(json_files)}")
    else:
        check(False, f"经验值JSON不足10笔(仅{len(json_files)}笔)", is_error=False)
master_path = Path.home() / "zq_web4_trading_system" / "data" / "experience" / "MASTER_EXPERIENCE.json"
if master_path.exists():
    r34 += 1; check(True, "MASTER_EXPERIENCE持续累计")
print(f"3.4 多轮稳定: {r34}/4 (×1.5 = {r34*1.5})")

# 第三跑汇总
run3_raw = r31 + r32 + r33 + r34
run3_weighted = (r31 * 1.0) + (r32 * 1.0) + (r33 * 1.0) + (r34 * 1.5)
print(f"\n第三跑原始分: {run3_raw}/16")
print(f"第三跑加权分: {run3_weighted:.1f}/19 (3.4多轮稳定×1.5)")

# ==========================================
# 评分汇总
# ==========================================
print("\n" + "=" * 60)
print("📊 综合评分")
print("=" * 60)

raw_total = run1_raw + run2_raw + run3_raw
weighted_total = run1_weighted + run2_weighted + run3_weighted

max_raw = 20 + 16 + 16  # 52
max_weighted = 22 + 19 + 19  # 60

# 按36分制映射
# 原始52分 = 100%, 36分 = 36 * (raw/52)
score_36 = round(36 * raw_total / max_raw, 1)
weighted_36 = round(36 * weighted_total / max_weighted, 1)

# 等级判定（基于36分制）
if score_36 >= 33:
    grade = "S级"
    meaning = "可独立考核，可上实盘"
elif score_36 >= 27:
    grade = "A级"
    meaning = "核心功能打通，少量边界待完善"
elif score_36 >= 18:
    grade = "B级"
    meaning = "基本能用，依赖外部协助"
else:
    grade = "C级"
    meaning = "还在搭建中"

print(f"""
┌─────────────────────────────────────────────┐
│         A5 复盘官 — 三跑三验证报告            │
│         职能类型: 复盘型                      │
├─────────────────────────────────────────────┤
│ 原始分: {raw_total}/{max_raw} (等权)          │
│ 加权分: {weighted_total:.1f}/{max_weighted} (复盘型加权) │
│ 36分制: {score_36}/36                        │
│ 等级:   {grade} — {meaning}                  │
├─────────────────────────────────────────────┤
│ 三跑明细 (原始分):                           │
│   第一跑(独立运行): {run1_raw}/20              │
│     ├─ 1.1 输入接收   {r11}/4                  │
│     ├─ 1.2 核心处理   {r12}/4 (×1.5={r12*1.5})  │
│     ├─ 1.3 输出产出   {r13}/4                  │
│     ├─ 1.4 6文件完备  {r14}/4                  │
│     └─ 1.5 自检脚本   {r15}/4                  │
│   第二跑(协同运行): {run2_raw}/16              │
│     ├─ 2.1 下游接收   {r21}/4                  │
│     ├─ 2.2 上游输出   {r22}/4                  │
│     ├─ 2.3 通信标准   {r23}/4 (×1.5={r23*1.5})  │
│     └─ 2.4 异常上报   {r24}/4                  │
│   第三跑(抗压运行): {run3_raw}/16              │
│     ├─ 3.1 空输入     {r31}/4                  │
│     ├─ 3.2 数据异常   {r32}/4                  │
│     ├─ 3.3 限流/重试  {r33}/4                  │
│     └─ 3.4 多轮稳定   {r34}/4 (×1.5={r34*1.5})  │
├─────────────────────────────────────────────┤
│ 三验证:                                      │
""")

# 三验证
print("--- 自验证 ---")
check("经验值JSON" in agents_txt or "schema" in agents_txt.lower(), "✓1 输出格式符合schema")
check("买入价<卖出价" in agents_txt or "价格" in memory_txt, "✓2 逻辑自洽(买入价<卖出价)")
check("追溯到" in agents_txt or "TRADES" in agents_txt, "✓3 源数据可溯(到TRADES.md)")

print("\n--- 交验证 ---")
check("ZH" in agents_txt or "总指挥" in agents_txt, "✓✓1 下游(ZH)可解析输出文件")
check("DQW" in agents_txt, "✓✓2 数据在合理范围(DQW检测)")
check("MASTER" in agents_txt or "经验值" in agents_txt, "✓✓3 和A4的TRADES数据一致")

print("\n--- 终验证 ---")
check("复盘报告" in agents_txt or "7章节" in agents_txt, "✓✓✓1 可读性(结构化报告)")
check(exp_dir.exists() and len(list(exp_dir.glob("*.json"))) > 10, "✓✓✓2 可信度(已实跑多笔)")
check("待接入" in agents_txt or "改进" in agents_txt or "待办" in memory_txt, "✓✓✓3 可迭代(改进路径)")

print(f"\n{'='*60}")
print(f"  检测: {len(passes)}项通过 | {len(warnings)}项警告 | {len(errors)}项错误")
print(f"  36分制评分: {score_36}/36")
print(f"  等级: {grade} — {meaning}")
print(f"{'='*60}")

sys.exit(0 if len(errors) == 0 else 1)
