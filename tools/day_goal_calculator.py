#!/usr/bin/env python3
"""
ZQ 365天目标计算器 v1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

430U → 1,000,000U 在365天内实现
每天复利 +2.146%
策略随资金规模自动进化，4个Phase

用法:
  python3 tools/day_goal_calculator.py              # 今天的目标
  python3 tools/day_goal_calculator.py --date 2026-05-02  # 指定日期
  python3 tools/day_goal_calculator.py --all            # 全部365天
  python3 tools/day_goal_calculator.py --phase          # 当前Phase
"""
import json, os, sys
from datetime import datetime, date, timedelta

# ─── 常量 ───
START_CAPITAL = 430.0
TARGET_CAPITAL = 1_000_000.0
START_DATE = date(2026, 4, 29)  # Day 1
DAILY_RATE = (TARGET_CAPITAL / START_CAPITAL) ** (1/365) - 1  # 2.146%

# Phase 阈值
PHASE_THRESHOLDS = [
    (1,     430,     1_520,    "Phase1-超小资金",   0.50,   "高频短持(30min-2h)"),
    (61,    1_520,   19_000,   "Phase2-小资金",     0.75,   "趋势波段(数小时-2天)"),
    (181,   19_000,  237_000,  "Phase3-中等资金",    0.40,   "多策略混合"),
    (301,   237_000, 1_000_000,"Phase4-大资金",      0.30,   "蓝筹主导"),
]

# ─── 核心函数 ───

def get_day_number(today=None):
    """计算今天是第几天"""
    if today is None:
        today = date.today()
    delta = today - START_DATE
    return delta.days + 1

def get_target(day_num=None):
    """计算第N天的目标市值"""
    if day_num is None:
        day_num = get_day_number()
    return START_CAPITAL * ((1 + DAILY_RATE) ** (day_num - 1))

def get_phase(capital=None):
    """根据资金量判断当前Phase"""
    if capital is None:
        day_num = get_day_number()
        capital = get_target(day_num)
    
    for phase in PHASE_THRESHOLDS:
        start_day, min_cap, max_cap, name, risk_per_trade, strategy = phase
        if min_cap <= capital < max_cap:
            return {
                "phase": name,
                "day_range": f"Day {start_day}-{PHASE_THRESHOLDS[PHASE_THRESHOLDS.index(phase)+1][0]-1 if PHASE_THRESHOLDS.index(phase) < len(PHASE_THRESHOLDS)-1 else 365}",
                "min_capital": min_cap,
                "max_capital": max_cap,
                "risk_per_trade": risk_per_trade,
                "strategy": strategy,
                "position_size": round(capital * risk_per_trade, 2),
                "daily_pnl_target": round(capital * DAILY_RATE, 2),
            }
    # 超过目标
    return {
        "phase": "🎉 已达标",
        "day_range": "365+",
        "min_capital": 1_000_000,
        "max_capital": float('inf'),
        "risk_per_trade": 0.30,
        "strategy": "蓝筹+风控",
        "position_size": round(capital * 0.30, 2),
        "daily_pnl_target": round(capital * DAILY_RATE, 2),
    }

def format_goal(today=None):
    """输出今日目标"""
    if today is None:
        today = date.today()
    
    day_num = get_day_number(today)
    target = get_target(day_num)
    phase = get_phase(target)
    daily_pnl = target * DAILY_RATE
    
    result = f"""
╔══════════════════════════════════════════╗
║       ZQ 365天 — 今日目标               ║
╠══════════════════════════════════════════╣
║ Day #{day_num} / 365                      ║
║ 日期: {today}                          ║
╠══════════════════════════════════════════╣
║ 目标市值: ${target:>8.2f}               ║
║ 今日需赚: ${daily_pnl:>8.2f}              ║
║ 当前Phase: {phase['phase']:<21s}║
║ 策略: {phase['strategy']:<29s}║
║ 单笔风险: ${phase['position_size']:>8.2f}        ║
╠══════════════════════════════════════════╣
║ 选币条件(Phase阶段):                      ║"""
    
    if "Phase1" in phase['phase']:
        result += """
║  • 价格<$1        — 小额能买足够数量      ║
║  • 24h量>$5M     — 有流动性不卡单        ║
║  • 30min量比>2x  — 资金正在进场          ║
║  • 市值$10M-$500M — 有爆发力             ║
║  • 非稳定币                             ║"""
    elif "Phase2" in phase['phase']:
        result += """
║  • 价格<$50                            ║
║  • 24h量>$20M                          ║
║  • 4h趋势=+1~+2  — 大方向向上           ║
║  • 市值$100M-$5B                       ║
║  • 赛道=当期热点                        ║"""
    
    pnl_line = f"${daily_pnl:>8.2f}"
    result += f"""
╠══════════════════════════════════════════╣
║ 今日目标线: {pnl_line}                       ║
╚══════════════════════════════════════════╝
"""
    return result, phase

def print_all_goals():
    """打印全部365天目标（摘要）"""
    print("=" * 70)
    print(f"  430U → 1,000,000U 在365天内  每天复利 +{DAILY_RATE*100:.3f}%")
    print("=" * 70)
    print(f"{'Day':<6}{'日期':<14}{'目标市值':<14}{'日需盈利':<12}{'Phase':<20}")
    print("-" * 70)
    
    for d in range(1, 366):
        d_date = START_DATE + timedelta(days=d-1)
        target = get_target(d)
        daily_pnl = target * DAILY_RATE
        phase = get_phase(target)
        print(f"{d:<6}{str(d_date):<14}${target:<10.2f}${daily_pnl:<9.2f}{phase['phase']:<20}")

def save_goal_json():
    """保存今日目标为JSON供引擎消费"""
    today = date.today()
    day_num = get_day_number(today)
    target = get_target(day_num)
    phase = get_phase(target)
    
    data = {
        "date": str(today),
        "day_number": day_num,
        "target_capital": round(target, 2),
        "daily_pnl_target": round(target * DAILY_RATE, 2),
        "phase": phase['phase'],
        "strategy": phase['strategy'],
        "risk_per_trade": phase['risk_per_trade'],
        "position_size": phase['position_size'],
    }
    
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "daily_goal.json")
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"✅ 目标已保存到 {path}")
    return data

# ─── CLI ───
if __name__ == '__main__':
    if '--all' in sys.argv:
        print_all_goals()
    elif '--phase' in sys.argv:
        today = date.today()
        _, phase = format_goal(today)
        print(json.dumps(phase, indent=2, ensure_ascii=False))
    elif '--date' in sys.argv:
        idx = sys.argv.index('--date')
        d = datetime.strptime(sys.argv[idx+1], '%Y-%m-%d').date()
        output, phase = format_goal(d)
        print(output)
    elif '--json' in sys.argv:
        save_goal_json()
    else:
        today = date.today()
        output, phase = format_goal(today)
        print(output)
        save_goal_json()
