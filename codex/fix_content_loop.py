#!/usr/bin/env python3
"""修复 content_loop_v3.py 的语法错误"""
import re

path = "/home/ubuntu/shared_context/content_loop_v3.py"
with open(path, "r") as f:
    lines = f.readlines()

# 找到 # 根据内容策略建议 那行
start = None
end = None
for i, line in enumerate(lines):
    if "根据内容策略建议" in line:
        start = i
    if start is not None and i > start + 10 and "# 辩论分数" in line:
        end = i
        break

if start is None:
    # 找不到就找 辩论分数 前面的代码
    for i, line in enumerate(lines):
        if "# 辩论分数" in line:
            end = i
            # 往前找中性期
            for j in range(i-1, max(0, i-15), -1):
                if "中性期" in lines[j]:
                    start = j + 2  # 空行后
                    break
            break

print(f"start={start}, end={end}")

if start is not None and end is not None:
    # 删除中间所有错误代码
    del lines[start:end]

    # 在 start 位置插入正确代码
    correct = [
        '    # 根据内容策略建议添加本周关注主题\n',
        '    if new_topics:\n',
        '        t5 += "\\n"\n',
        '        t5 += "\\u4e0d\\u672c\\u5468\\u5173\\u6ce8\\u4e3b\\u9898:\\n"\n',
        '        for topic in new_topics[:3]:\n',
        '            t5 += f"  \\u2022 {topic}\\n"\n',
        '\n',
    ]

    lines = lines[:start] + correct + lines[start:]

    with open(path, "w") as f:
        f.writelines(lines)
    print("修复完成")

    # 验证
    import py_compile
    py_compile.compile(path)
    print("语法检查通过")
else:
    print("未找到目标位置")
