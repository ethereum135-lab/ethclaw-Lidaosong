#!/usr/bin/env python3
"""
补丁脚本: 在content_loop_v3.py中注入content_strategy.json读取
让内容生成器能读取效果分析器的优化建议，闭环环节6
"""
import re

FILE = "/home/ubuntu/shared_context/content_loop_v3.py"

with open(FILE, "r") as f:
    code = f.read()

# 1. 在generate_content函数中注入策略读取
# 找到 data = { ... } 块的结尾，在后面注入策略读取
old_data_block = '''        "futures": read_json("futures/signals.json"),
    }'''

new_data_block = '''        "futures": read_json("futures/signals.json"),
    }

    # 读取内容策略（由content_analyzer.py每周日生成）
    strategy = read_json("content/content_strategy.json")
    if strategy:
        data["strategy"] = strategy
        recs = strategy.get("recommendations", [])
        adjustments = strategy.get("content_adjustments", {})
        if recs:
            print("[内容闭环 v3.0] 读取到内容策略:")
            for r in recs[:3]:
                print("  →", r[:60])
        if adjustments.get("new_topics_to_try"):
            print("  新主题建议:", ", ".join(adjustments.get("new_topics_to_try", [])[:3]))
    else:
        data["strategy"] = {}
'''

code = code.replace(old_data_block, new_data_block)

# 2. 在generate_deep_analysis中注入策略建议
old_deep = '''    prompt = "你是加密货币分析师。根据以下数据写一段200字深度分析：\\n\\n"'''

new_deep = '''    # 读取内容策略建议
    strategy = data.get("strategy", {})
    strategy_hint = ""
    recs = strategy.get("recommendations", [])
    adjustments = strategy.get("content_adjustments", {})
    if recs:
        strategy_hint = "\\n\\n上周内容表现参考:\\n" + "\\n".join(recs[:3])
    if adjustments.get("tone"):
        strategy_hint += "\\n风格要求: " + adjustments.get("tone", "")

    prompt = "你是加密货币分析师。根据以下数据写一段200字深度分析：\\n\\n"'''

code = code.replace(old_deep, new_deep)

# 3. 在deep_analysis的prompt结尾加入策略提示
old_prompt_end = '''        + "操作建议（非投资建议，仅为策略输出）"
    )'''

new_prompt_end = '''        + "操作建议（非投资建议，仅为策略输出）"
        + strategy_hint
    )'''

code = code.replace(old_prompt_end, new_prompt_end)

# 4. 在版本号中标注策略读取
code = code.replace('"version": "3.0"', '"version": "3.1"')
code = code.replace('[内容闭环 v3.0]', '[内容闭环 v3.1]')

with open(FILE, "w") as f:
    f.write(code)

print("补丁已应用: content_loop_v3.py → v3.1 (支持策略读取)")
