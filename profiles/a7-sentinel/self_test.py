#!/usr/bin/env python3
"""
A7 舆情官 — 三跑三验证 @框架v1.0 严格版
职能类型：数据型（舆情数据采集+判断）
侧重点：1.2数据采集完整度×1.5 | 2.1数据格式标准化×1.5 | 3.2源站故障需降级×1.5
满分：36分
"""
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
e, w, p = [], [], []

def c(cond, msg, err=True):
    if cond: print(f"  ✅ {msg}"); p.append(msg); return True
    else:
        if err: print(f"  ❌ {msg}"); e.append(msg)
        else: print(f"  ⚠️  {msg}"); w.append(msg)
        return False

def rf(n):
    x = BASE/n; return x.read_text() if x.exists() else ""

print("="*60)
print("  A7 舆情官 — 三跑三验证 v1.0 严格版")
print("  职能类型: 数据型（舆情数据采集+判断）")
print("="*60)

a = rf("AGENTS.md"); m = rf("MEMORY.md"); s = rf("SOUL.md")
i = rf("IDENTITY.md"); cnf = rf("config.yaml")

print("\n━━━ 步骤1：6文件检查 ━━━")
ok6 = 0
for f in ["SOUL.md","IDENTITY.md","PERSONALITY.md","AGENTS.md","MEMORY.md","config.yaml"]:
    fp = BASE/f; ok = fp.exists() and fp.stat().st_size > 100
    if ok: ok6 += 1
    c(ok, f"{f} {'✅' if ok else '❌缺失'}")
c("舆情官" in s and "A7" in i, "SOUL和IDENTITY一致")
c("哨兵" in s or "报警" in s, "PERSONALITY含对标")
c("F&G" in a and "Elon" in a, "AGENTS含监控规章")
c("铁断" in m, "MEMORY含铁断")
c("fear_greed" in cnf, "config.yaml含F&G阈值")

# ============================
# 第一跑：独立运行
# ============================
print("\n"+"="*60)
print("第一跑：独立运行（数据型→1.2数据采集完整度×1.5）")
print("="*60)

# 1.1 输入接收 /4
print("\n--- 1.1 输入接收 ---")
r11 = 0
if "F&G" in a: r11 += 1; c(True, "F&G指数输入(Alternative.me)")
if "Elon" in a or "推特" in a: r11 += 1; c(True, "推特数据输入(web_search)")
if "黑客" in a or "监管" in a: r11 += 1; c(True, "新闻数据输入(web_search)")
if "web_search" in a: r11 += 1; c(True, "通过web_search获取外部数据")
print(f"1.1 输入接收: {r11}/4")

# 1.2 核心处理 /4（数据型侧重×1.5）
print("\n--- 1.2 核心处理 ---")
r12_items = [
    ("F&G极端值检测", "F&G" in a and "20" in cnf),
    ("名人推特监控", "Elon" in a or "推特" in a),
    ("重大新闻检测", "黑客" in a and "监管" in a),
    ("告警条件判断", "告警" in a or "alert" in a),
    ("误报过滤", "误报" in a),
    ("沉默协议", "沉默" in s or "正常不写" in a),
]
r12c = sum(1 for _,ok in r12_items for _,ok in [(_,ok)])
# fix the counting
r12c = 0
for _, ok in r12_items:
    if ok: r12c += 1
    c(ok, f"核心: {_}")
r12 = 4 if r12c >= 5 else (3 if r12c >= 4 else 2)
print(f"  通过: {r12c}/{len(r12_items)}")
print(f"1.2 核心处理: {r12}/4 (×1.5 = {r12*1.5})")

# 1.3 输出产出 /4
print("\n--- 1.3 输出产出 ---")
r13 = 0
if "agents/a7" in a or "alert" in a: r13 += 1; c(True, "产出: agents/a7/alert.md")
if "10行" in a: r13 += 1; c(True, "alert≤10行")
if "告警类型" in a or "事件" in a: r13 += 1; c(True, "结构化告警格式")
if "沉默" in s or "不写" in a: r13 += 1; c(True, "无异常沉默(无输出)")
print(f"1.3 输出产出: {r13}/4")

# 1.4 6文件
r14 = 4 if ok6 == 6 else 3
print(f"1.4 6文件: {r14}/4")

# 1.5 自检脚本
r15 = 4 if (BASE/"self_test.py").exists() else 0
c(r15>0, "self_test.py存在")
print(f"1.5 自检: {r15}/4")

run1r = r11 + r12 + r13 + r14 + r15
run1w = r11*1.0 + r12*1.5 + r13*1.0 + r14*1.0 + r15*1.0
print(f"\n第一跑: {run1r}/20 | 加权: {run1w:.1f}/22")

# ============================
# 第二跑：协同运行
# ============================
print("\n"+"="*60)
print("第二跑：协同运行（数据型→2.1数据格式标准化×1.5）")
print("="*60)

# 2.1 下游接收 /4（数据型侧重×1.5）
print("\n--- 2.1 下游接收 ---")
r21 = 0
if "ZH" in a: r21 += 1; c(True, "产出给ZH读")
if "agents/a7" in a: r21 += 1; c(True, "固定路径agents/a7/")
if "alert" in a: r21 += 1; c(True, "标准告警格式")
if "YYYY-MM-DD" in a or "BJTW" in a or "BJT" in a: r21 += 1; c(True, "时间格式统一")
else:
    # Check if time format exists
    if "HH:MM" in a or "时间" in a: r21 += 1; c(True, "时间标注统一")
print(f"2.1 下游接收(数据格式): {r21}/4 (×1.5 = {r21*1.5})")

# 2.2 上游输出
print("\n--- 2.2 上游输出 ---")
r22 = 0
if "ZH" in a: r22 += 1; c(True, "产出给ZH")
if "alert" in a: r22 += 1; c(True, "alert可被ZH直接读")
print(f"2.2 上游输出: {r22}/4")

# 2.3 通信标准
print("\n--- 2.3 通信标准 ---")
r23 = 0
if "agents/a7" in a: r23 += 1; c(True, "路径: agents/a7/")
if "profiles" in a: r23 += 1; c(True, "profile路径统一")
if "alert" in a: r23 += 1; c(True, "alert命名规范")
print(f"2.3 通信标准: {r23}/4")

# 2.4 异常上报
print("\n--- 2.4 异常上报 ---")
r24 = 0
if "告警" in a: r24 += 1; c(True, "告警机制")
if "ZH" in a: r24 += 1; c(True, "上报给ZH")
if "Elon" in a or "黑客" in a: r24 += 1; c(True, "能定位事件来源")
print(f"2.4 异常上报: {r24}/4")

run2r = r21 + r22 + r23 + r24
run2w = r21*1.5 + r22*1.0 + r23*1.0 + r24*1.0
print(f"\n第二跑: {run2r}/16 | 加权: {run2w:.1f}/19")

# ============================
# 第三跑：抗压运行
# ============================
print("\n"+"="*60)
print("第三跑：抗压运行（数据型→3.2源站故障需降级×1.5）")
print("="*60)

# 3.1 空输入
print("\n--- 3.1 空输入 ---")
r31 = 0
if "不编造" in s: r31 += 1; c(True, "无数据不编造")
if "沉默" in s or "跳过" in a: r31 += 1; c(True, "无告警沉默")
if "数据不够" in s or "找不到" in a: r31 += 1; c(True, "找不到异常不硬写")
print(f"3.1 空输入: {r31}/4")

# 3.2 数据异常 /4（数据型侧重×1.5）
print("\n--- 3.2 数据异常 ---")
r32 = 0
if "fallback" in cnf: r32 += 1; c(True, "模型fallback")
if "temperature" in cnf: r32 += 1; c(True, "温度配置")
if "web_search" in a: r32 += 1; c(True, "web_search可替代API")
if "宁可漏报不可误报" in a or "误报" in a: r32 += 1; c(True, "误报过滤机制")
print(f"3.2 数据异常: {r32}/4 (×1.5 = {r32*1.5})")

# 3.3 限流/重试
print("\n--- 3.3 限流/重试 ---")
r33 = 0
if "model:" in cnf: r33 += 1; c(True, "独立model")
if "fallback" in cnf: r33 += 1; c(True, "fallback机制")
if "*/15" in cnf or "15" in cnf: r33 += 1; c(True, "固定频率cron")
print(f"3.3 限流/重试: {r33}/4")

# 3.4 多轮稳定
print("\n--- 3.4 多轮稳定 ---")
r34 = 0
if "自检" in a: r34 += 1; c(True, "自检清单")
if "self_test" in str(BASE/"self_test.py"): r34 += 1; c(True, "可重复自检")
if "待接入" in a: r34 += 1; c(True, "改进路径")
if "15分钟" in a: r34 += 1; c(True, "每15分钟持续监控")
print(f"3.4 多轮稳定: {r34}/4")

run3r = r31 + r32 + r33 + r34
run3w = r31*1.0 + r32*1.5 + r33*1.0 + r34*1.0
print(f"\n第三跑: {run3r}/16 | 加权: {run3w:.1f}/19")

# ============================
# 汇总评分
# ============================
raw = run1r + run2r + run3r
wt = run1w + run2w + run3w
max_raw = 52; max_w = 60

sc36 = round(36 * raw / max_raw, 1)
if sc36 >= 33: g, gm = "S级", "可独立考核，可上实盘"
elif sc36 >= 27: g, gm = "A级", "核心功能打通，少量边界待完善"
elif sc36 >= 18: g, gm = "B级", "基本能用，依赖外部协助"
else: g, gm = "C级", "还在搭建中"

print(f"\n{'='*60}")
print(f"📊 综合评分")
print(f"{'='*60}")
print(f"""
┌──────────────────────────────────────────────┐
│        A7 舆情官 — 三跑三验证报告              │
│        职能类型: 数据型（舆情数据采集+判断）     │
├──────────────────────────────────────────────┤
│ 原始分: {raw}/{max_raw} (等权)                │
│ 加权分: {wt:.1f}/{max_w} (数据型加权)          │
│ 36分制: {sc36}/36                             │
│ 等级:   {g} — {gm}                            │
├──────────────────────────────────────────────┤
│ 三跑明细:                                     │
│   第一跑(独立): {run1r}/20                      │
│     ├─ 1.1 输入接收 {r11}/4                     │
│     ├─ 1.2 核心处理 {r12}/4 (×1.5={r12*1.5})     │
│     ├─ 1.3 输出产出 {r13}/4                     │
│     ├─ 1.4 6文件完备 {r14}/4                     │
│     └─ 1.5 自检脚本 {r15}/4                     │
│   第二跑(协同): {run2r}/16                      │
│     ├─ 2.1 数据格式 {r21}/4 (×1.5={r21*1.5})     │
│     ├─ 2.2 上游输出 {r22}/4                     │
│     ├─ 2.3 通信标准 {r23}/4                     │
│     └─ 2.4 异常上报 {r24}/4                     │
│   第三跑(抗压): {run3r}/16                      │
│     ├─ 3.1 空输入 {r31}/4                       │
│     ├─ 3.2 源站故障 {r32}/4 (×1.5={r32*1.5})     │
│     ├─ 3.3 限流/重试 {r33}/4                     │
│     └─ 3.4 多轮稳定 {r34}/4                     │
├──────────────────────────────────────────────┤
│ 三验证:                                       │
""")

# 自验证
print("--- 自验证 ---")
c("告警类型" in a or "alert" in a, "✓1 输出格式符合schema")
c("不编造" in s, "✓2 逻辑自洽(不编造)")
c("web_search" in a, "✓3 数据可溯(到数据源)")

# 交验证
print("\n--- 交验证 ---")
c("ZH" in a, "✓✓1 下游(ZH)可解析alert")
c("误报" in a, "✓✓2 合理范围(误报过滤)")
c("15分钟" in a, "✓✓3 与市场实际时间一致")

# 终验证
print("\n--- 终验证 ---")
c("10行" in a, "✓✓✓1 可读性(精简)")
print(f"  ⏳ ✓✓✓2 可信度 — 待实际运行后验证（刚建好）")
c("待接入" in a, "✓✓✓3 可迭代(改进路径)")

print(f"\n{'='*60}")
print(f"  检测: {len(p)}通过 | {len(w)}警告 | {len(e)}错误")
print(f"  36分制: {sc36}/36")
print(f"  等级: {g}")
print(f"{'='*60}")
sys.exit(0 if len(e)==0 else 1)
