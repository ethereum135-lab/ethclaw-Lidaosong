#!/usr/bin/env python3
"""修复 content_loop_v3.py 中的编码问题"""
path = "/home/ubuntu/shared_context/content_loop_v3.py"
with open(path, "r") as f:
    content = f.read()

# 修复错误的 unicode 转义
content = content.replace("\\u4e0d\\u672c\\u5468\\u5173\\u6ce8\\u4e3b\\u9898", "本周关注主题")

with open(path, "w") as f:
    f.write(content)

# 验证
import py_compile
py_compile.compile(path)
print("编码修复完成，语法检查通过")
