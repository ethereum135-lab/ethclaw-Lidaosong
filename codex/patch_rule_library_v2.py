#!/usr/bin/env python3
"""
修补 rule_library.py v2：在 evaluate() 中读取 rule_performance.json
"""
import os

path = "/home/ubuntu/shared_context/economy/rule_library.py"
with open(path, "r") as f:
    code = f.read()

# 插入学习反馈函数（在 evaluate 之前）
old = '''def evaluate():
    """评估所有规则，返回匹配的规则+动作"""
    context = _build_context()

    matched = []
    for rule in RULES:'''

new = '''def _load_performance():
    """读取规则学习表现数据（学习闭环反馈）"""
    try:
        with open(os.path.join(SC, "macro/rule_performance.json")) as f:
            return json.load(f)
    except Exception:
        return {}


def _adjust_priority(rule, performance):
    """根据学习闭环的命中率调整规则优先级"""
    perf_data = performance.get("evaluations", [])
    rule_id = rule.get("id", "")
    for ev in perf_data:
        if ev.get("rule_id") == rule_id:
            hit_rate = ev.get("hit_rate", -1)
            if hit_rate < 0:
                continue
            if hit_rate < 0.5 and rule.get("priority", 0) > 0:
                rule = dict(rule)
                rule["priority"] = max(0, rule["priority"] - 1)
                rule["_learning_adjusted"] = f"demoted (hit_rate={hit_rate:.0%})"
            elif hit_rate > 0.7:
                rule = dict(rule)
                rule["priority"] = min(5, rule["priority"] + 1)
                rule["_learning_adjusted"] = f"promoted (hit_rate={hit_rate:.0%})"
            break
    return rule


def evaluate():
    """评估所有规则，返回匹配的规则+动作"""
    context = _build_context()

    # 应用学习闭环反馈
    performance = _load_performance()
    active_rules = RULES
    if performance:
        active_rules = [_adjust_priority(r, performance) for r in RULES]

    matched = []
    for rule in active_rules:'''

if old in code:
    code = code.replace(old, new)
    print("patched")
else:
    print("not found")

with open(path, "w") as f:
    f.write(code)

import py_compile
py_compile.compile(path)
print("syntax ok")
