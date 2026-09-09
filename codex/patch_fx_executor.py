#!/usr/bin/env python3
"""修补 fx_executor.py：在 main 中调用 save_paper_orders"""
path = "/home/ubuntu/shared_context/fx_executor.py"
with open(path, "r") as f:
    code = f.read()

# 在 if __name__ 之前插入函数
insert_before = "if __name__ == '__main__':"

func_code = '''
def save_paper_orders():
    """保存模拟订单状态到 paper_orders.json 供心跳检测"""
    try:
        import json as _json
        _data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "running",
            "mode": "paper"
        }
        with open(PAPER_ORDERS, "w") as f:
            _json.dump(_data, f, indent=2)
    except Exception:
        pass

'''

if "def save_paper_orders" not in code:
    code = code.replace(insert_before, func_code + insert_before)
    print("函数已添加")

# 在 main 块中添加调用
main_idx = code.find("if __name__ == '__main__':")
if main_idx >= 0:
    next_line = code.find("\n", main_idx) + 1
    code = code[:next_line] + "    save_paper_orders()\n" + code[next_line:]
    print("调用已添加")

with open(path, "w") as f:
    f.write(code)

import py_compile
py_compile.compile(path)
print("语法检查通过")
