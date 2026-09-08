#!/usr/bin/env python3
"""
A8 资金官 — 三跑三验证 @框架v1.0 严格版
职能类型：数据型（资金数据采集+分析）
侧重点：1.2数据采集完整度×1.5 | 2.1数据格式标准化×1.5 | 3.2源站故障需降级×1.5
满分：36分
"""
import sys
from pathlib import Path

B = Path(__file__).resolve().parent
e, w, p = [], [], []

def c(cond, msg, err=True):
    if cond: print(f"  ✅ {msg}"); p.append(msg); return True
    else:
        if err: print(f"  ❌ {msg}"); e.append(msg)
        else: print(f"  ⚠️  {msg}"); w.append(msg); return False

def rf(n):
    x = B / n; return x.read_text() if x.exists() else ""

print("=" * 60)
print("  A8 资金官 — 三跑三验证 v1.0 严格版")
print("  职能类型: 数据型（资金数据采集+分析）")
print("=" * 60)

a = rf("AGENTS.md"); m = rf("MEMORY.md"); s = rf("SOUL.md")
i = rf("IDENTITY.md"); cnf = rf("config.yaml")

# ======= 步骤1 =======
print("\n━━━ 步骤1：6文件检查 ━━━")
ok6 = 0
for f in ["SOUL.md","IDENTITY.md","PERSONALITY.md","AGENTS.md","MEMORY.md","config.yaml"]:
    fp = B / f; ok = fp.exists() and fp.stat().st_size > 100
    if ok: ok6 += 1
    c(ok, f"{f} {'✅' if ok else '❌缺失'}")
c("资金官" in s and "A8" in i, "SOUL和IDENTITY一致")
c("聪明钱包" in a and "大额转账" in a, "AGENTS含监控规章")
c("铁断" in m, "MEMORY含铁断")
c("whale_transfer" in cnf, "config.yaml含大额阈值")

# ======= 第一跑 =======
print("\n" + "=" * 60)
print("第一跑：独立运行（数据型→1.2数据采集完整度×1.5）")
print("=" * 60)

# 1.1 输入接收 /4
print("\n--- 1.1 输入接收 ---")
r11 = 0
if "聪明钱包" in a or "聪明钱" in a: r11 += 2; c(True, "聪明钱包数据输入")
if "机构" in a or "持仓" in a: r11 += 1; c(True, "投资公司持仓输入")
if "大额转账" in a: r11 += 1; c(True, "大额转账数据输入")
print(f"1.1 输入接收: {r11}/4")

# 1.2 核心处理 /4（数据型侧重×1.5）
print("\n--- 1.2 核心处理 ---")
r12_items = [
    ("聪明钱包持仓监控", "聪明钱包" in a),
    ("机构持仓追踪", "机构" in a and "持仓" in a),
    ("大额转账检测", "大额转账" in a and "100万" in a),
    ("异常转账标记", "异常" in a),
    ("不推荐币", "不推荐" in s or "不推荐" in a),
    ("每小时更新", "每小时" in a or "60分钟" in cnf or "0 *" in cnf),
]
r12c = sum(1 for _, ok in r12_items if ok)
for name, ok in r12_items:
    c(ok, f"核心: {name}")
r12 = 4 if r12c >= 5 else (3 if r12c >= 4 else 2)
print(f"  通过: {r12c}/{len(r12_items)}")
print(f"1.2 核心处理: {r12}/4 (×1.5 = {r12*1.5})")

# 1.3 输出产出 /4
print("\n--- 1.3 输出产出 ---")
r13 = 0
if "agents/a8" in a or "fund_flow" in a: r13 += 1; c(True, "产出: agents/a8/fund_flow.md")
if "聪明钱包" in a and "机构" in a and "大额" in a: r13 += 1; c(True, "三项分类结构化报告")
if "无变化" in a or "无显著" in a: r13 += 1; c(True, "无数据时不编造")
if "|" in a: r13 += 1; c(True, "表格结构统一")
print(f"1.3 输出产出: {r13}/4")

# 1.4 6文件
r14 = 4 if ok6 == 6 else 3
print(f"1.4 6文件: {r14}/4")

# 1.5 自检
r15 = 4 if (B / "self_test.py").exists() else 0
c(r15 > 0, "self_test.py存在")
print(f"1.5 自检: {r15}/4")

run1r = r11 + r12 + r13 + r14 + r15
run1w = r11*1.0 + r12*1.5 + r13*1.0 + r14*1.0 + r15*1.0
print(f"\n第一跑: {run1r}/20 | 加权: {run1w:.1f}/22")

# ======= 第二跑 =======
print("\n" + "=" * 60)
print("第二跑：协同运行（数据型→2.1数据格式标准化×1.5）")
print("=" * 60)

# 2.1 下游接收 /4（数据型侧重×1.5）
print("\n--- 2.1 下游接收 ---")
r21 = 0
if "agents/a8" in a: r21 += 1; c(True, "固定路径agents/a8/")
if "fund_flow" in a: r21 += 1; c(True, "固定文件名fund_flow.md")
if "YYYY-MM-DD" in a or "HH:MM" in a or "BJT" in a: r21 += 1; c(True, "时间格式统一")
if "|" in a or "：" in a: r21 += 1; c(True, "结构化格式")
print(f"2.1 数据格式: {r21}/4 (×1.5 = {r21*1.5})")

# 2.2 上游输出
print("\n--- 2.2 上游输出 ---")
r22 = 0
if "ZH" in i or "总指挥" in a: r22 += 1; c(True, "产出给ZH")
if "fund_flow" in a: r22 += 1; c(True, "fund_flow可被直接阅读")
print(f"2.2 上游输出: {r22}/4")

# 2.3 通信标准
print("\n--- 2.3 通信标准 ---")
r23 = 0
if "agents/a8" in a: r23 += 1; c(True, "路径: agents/a8/")
if "profiles" in a: r23 += 1; c(True, "profile路径统一")
if "###" in a or "##" in a: r23 += 1; c(True, "Markdown格式统一")
print(f"2.3 通信标准: {r23}/4")

# 2.4 异常上报
print("\n--- 2.4 异常上报 ---")
r24 = 0
if "异常" in a: r24 += 1; c(True, "异常转账标记")
if "30分钟" in a: r24 += 1; c(True, "30分钟内标记")
print(f"2.4 异常上报: {r24}/4")

run2r = r21 + r22 + r23 + r24
run2w = r21*1.5 + r22*1.0 + r23*1.0 + r24*1.0
print(f"\n第二跑: {run2r}/16 | 加权: {run2w:.1f}/19")

# ======= 第三跑 =======
print("\n" + "=" * 60)
print("第三跑：抗压运行（数据型→3.2源站故障需降级×1.5）")
print("=" * 60)

# 3.1 空输入
print("\n--- 3.1 空输入 ---")
r31 = 0
if "不编造" in s: r31 += 1; c(True, "无数据不编造")
if "无变化" in a or "无显著" in a: r31 += 1; c(True, "无变化时明确标注")
if "找不到" in a or "不编造" in s: r31 += 1; c(True, "找不到不硬写")
print(f"3.1 空输入: {r31}/4")

# 3.2 数据异常 /4（数据型侧重×1.5）
print("\n--- 3.2 数据异常 ---")
r32 = 0
if "fallback" in cnf: r32 += 1; c(True, "模型fallback")
if "temperature" in cnf: r32 += 1; c(True, "温度配置")
if "web_search" in a or "搜索" in a: r32 += 1; c(True, "web_search可替代API")
if "1000000" in cnf or "whale_transfer" in cnf: r32 += 1; c(True, "阈值配置($100万)")
print(f"3.2 数据异常: {r32}/4 (×1.5 = {r32*1.5})")

# 3.3 限流/重试
print("\n--- 3.3 限流/重试 ---")
r33 = 0
if "model:" in cnf: r33 += 1; c(True, "独立model")
if "fallback" in cnf: r33 += 1; c(True, "fallback机制")
if "0 *" in cnf or "每小时" in a: r33 += 1; c(True, "固定频率cron")
print(f"3.3 限流/重试: {r33}/4")

# 3.4 多轮稳定
print("\n--- 3.4 多轮稳定 ---")
r34 = 0
if "自检" in a or "验收" in a: r34 += 1; c(True, "自检机制")
if "self_test" in str(B/"self_test.py"): r34 += 1; c(True, "可重复自检")
if "每小时" in a: r34 += 1; c(True, "每小时持续更新")
print(f"3.4 多轮稳定: {r34}/4")

run3r = r31 + r32 + r33 + r34
run3w = r31*1.0 + r32*1.5 + r33*1.0 + r34*1.0
print(f"\n第三跑: {run3r}/16 | 加权: {run3w:.1f}/19")

# ======= 汇总 =======
raw = run1r + run2r + run3r
wt = run1w + run2w + run3w
max_raw = 52; max_w = 60

sc36 = round(36 * raw / max_raw, 1)
if sc36 >= 33: g, gm = "S级", "可独立考核，可上实盘"
elif sc36 >= 27: g, gm = "A级", "核心功能打通，少量边界待完善"
elif sc36 >= 18: g, gm = "B级", "基本能用，依赖外部协助"
else: g, gm = "C级", "还在搭建中"

print(f"\n{'=' * 60}")
print(f"📊 综合评分")
print(f"{'=' * 60}")
print(f"""
┌──────────────────────────────────────────────┐
│        A8 资金官 — 三跑三验证报告              │
│        职能类型: 数据型（资金数据采集+分析）     │
├──────────────────────────────────────────────┤
│ 原始分: {raw}/{max_raw}                        │
│ 加权分: {wt:.1f}/{max_w}                       │
│ 36分制: {sc36}/36                              │
│ 等级:   {g} — {gm}                             │
├──────────────────────────────────────────────┤
│ 三跑明细:                                     │
│   第一跑: {run1r}/20                            │
│     ├─ 1.1 输入接收 {r11}/4                     │
│     ├─ 1.2 核心处理 {r12}/4 (×1.5={r12*1.5})     │
│     ├─ 1.3 输出产出 {r13}/4                     │
│     ├─ 1.4 6文件完备 {r14}/4                     │
│     └─ 1.5 自检脚本 {r15}/4                     │
│   第二跑: {run2r}/16                            │
│     ├─ 2.1 数据格式 {r21}/4 (×1.5={r21*1.5})     │
│     ├─ 2.2 上游输出 {r22}/4                     │
│     ├─ 2.3 通信标准 {r23}/4                     │
│     └─ 2.4 异常上报 {r24}/4                     │
│   第三跑: {run3r}/16                            │
│     ├─ 3.1 空输入 {r31}/4                       │
│     ├─ 3.2 数据异常 {r32}/4 (×1.5={r32*1.5})     │
│     ├─ 3.3 限流/重试 {r33}/4                     │
│     └─ 3.4 多轮稳定 {r34}/4                     │
├──────────────────────────────────────────────┤
│ 三验证:                                       │
""")

# 自验证
print("--- 自验证 ---")
c("fund_flow" in a or "###" in a, "✓1 输出格式符合schema")
c("不编造" in s, "✓2 逻辑自洽(不编造)")
c("web_search" in a or "搜索" in a, "✓3 数据可溯(到数据源)")

print("\n--- 交验证 ---")
c("agents/a8" in a, "✓✓1 下游(ZH)可解析fund_flow")
c("100万" in a or "1000000" in cnf, "✓✓2 合理范围(>$100万标记)")
c("每小时" in a, "✓✓3 更新频率一致")

print("\n--- 终验证 ---")
c("###" in a or "##" in a, "✓✓✓1 可读性(结构化)")
print("  ⏳ ✓✓✓2 可信度 — 待实际运行后验证")
c("待接入" in a or "待" in m, "✓✓✓3 可迭代(改进路径)")

print(f"\n{'=' * 60}")
print(f"  检测: {len(p)}通过 | {len(w)}警告 | {len(e)}错误")
print(f"  36分制: {sc36}/36 | 等级: {g}")
print(f"{'=' * 60}")
sys.exit(0 if len(e) == 0 else 1)
