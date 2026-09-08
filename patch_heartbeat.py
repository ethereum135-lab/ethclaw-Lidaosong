#!/usr/bin/env python3
"""Add new components to heartbeat_manager.py"""
import re

path = "/home/ubuntu/shared_context/heartbeat_manager.py"
with open(path) as f:
    content = f.read()

new_agents = '''    "fx_executor": {
        "name": "外汇执行器",
        "check_type": "json",
        "path": os.path.join(SC, "fx/paper_orders.json"),
        "max_silence_sec": 1800,
        "severity": "medium",
    },
    "futures_signal": {
        "name": "期货信号生成器",
        "check_type": "json",
        "path": os.path.join(SC, "futures/traditional_signals.json"),
        "max_silence_sec": 1800,
        "severity": "medium",
    },
    "economic_indicators": {
        "name": "经济指标采集",
        "check_type": "json",
        "path": os.path.join(SC, "macro/economic_indicators.json"),
        "max_silence_sec": 90000,
        "severity": "low",
    },
    "rule_learning": {
        "name": "规则库学习闭环",
        "check_type": "json",
        "path": os.path.join(SC, "macro/rule_performance.json"),
        "max_silence_sec": 90000,
        "severity": "low",
    },
    "correlation_matrix": {
        "name": "跨市场相关性矩阵",
        "check_type": "json",
        "path": os.path.join(SC, "macro/correlation_matrix.json"),
        "max_silence_sec": 18000,
        "severity": "medium",
    },
    "stop_order_verifier": {
        "name": "止损单同步验证",
        "check_type": "json",
        "path": os.path.join(SC, "risk/stop_order_audit.json"),
        "max_silence_sec": 7200,
        "severity": "high",
    },
'''

# Find the kill_switch entry and insert after its closing brace
marker = '    "kill_switch": {'
idx = content.find(marker)
if idx == -1:
    print("ERROR: kill_switch not found")
    exit(1)

# Find the closing brace of kill_switch entry
brace_count = 0
i = content.find("{", idx)
while i < len(content):
    if content[i] == "{":
        brace_count += 1
    elif content[i] == "}":
        brace_count -= 1
        if brace_count == 0:
            break
    i += 1

end = i + 1
new_content = content[:end] + "\n" + new_agents + content[end:]
with open(path, "w") as f:
    f.write(new_content)
print("OK: 6 new agents added after kill_switch")
