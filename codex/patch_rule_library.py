#!/usr/bin/env python3
"""
修补 rule_library.py：在 evaluate() 中读取 rule_performance.json，
根据命中率自动调整规则优先级（学习闭环反馈）。
"""
import re

path = "/home/ubuntu/shared_context/economy/rule_library.py"
with open(path, "r") as f:
    code = f.read()

# 在 evaluate() 函数开头加入学习反馈读取
old = '''def evaluate():
    """主评估函数：读取当前上下文，匹配规则，生成动作"""'''

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
                rule["priority"] = max(0, rule["priority"] - 1)
                rule["_learning_adjusted"] = f"priority demoted (hit_rate={hit_rate:.0%})"
            elif hit_rate > 0.7:
                rule["priority"] = min(5, rule["priority"] + 1)
                rule["_learning_adjusted"] = f"priority promoted (hit_rate={hit_rate:.0%})"
            break
    return rule


def evaluate():
    """主评估函数：读取当前上下文，匹配规则，生成动作"""'''

if old in code:
    code = code.replace(old, new)
    print("✅ evaluate() 已加入学习反馈函数")
else:
    print("❌ 未找到 evaluate() 函数")

# 在规则匹配之前应用学习调整
old2 = '''    # 匹配规则
    matched = []
    for rule in RULES:'''

new2 = '''    # 应用学习闭环反馈：根据命中率调整优先级
    performance = _load_performance()
    adjusted_rules = []
    for rule in RULES:
        r = dict(rule)  # 浅拷贝避免修改原始规则
        if performance:
            r = _adjust_priority(r, performance)
        adjusted_rules.append(r)

    # 匹配规则
    matched = []
    for rule in adjusted_rules:'''

if old2 in code:
    code = code.replace(old2, new2)
    print("✅ 规则匹配前已加入学习调整")
else:
    print("❌ 未找到规则匹配代码")

with open(path, "w") as f:
    f.write(code)

# 验证语法
import py_compile
py_compile.compile(path)
print("语法检查通过")
