#!/usr/bin/env python3
"""
一行命令写入Agent状态 — 供cron末尾调用

用法：
  python3 tools/write_state_now.py a1 ok '{"data_dims_available":3}'
  python3 tools/write_state_now.py a5 ok
  
最后一个参数是可选的JSON数据字符串。
"""
import json, os, sys, time

STATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "state")

def main():
    if len(sys.argv) < 3:
        print(f"用法: {sys.argv[0]} <agent_name> <status> [data_json]")
        sys.exit(1)
    
    agent = sys.argv[1]
    status = sys.argv[2]
    data = json.loads(sys.argv[3]) if len(sys.argv) > 3 else None
    
    payload = {"status": status, "data": data, "errors": None}
    state = {
        "agent": agent,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime()),
        "ts_unix": int(time.time()),
        **payload
    }
    
    os.makedirs(STATE_DIR, exist_ok=True)
    tmp_path = os.path.join(STATE_DIR, f"{agent}.json.tmp")
    final_path = os.path.join(STATE_DIR, f"{agent}.json")
    
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, final_path)
    print(f"✅ state/{agent}.json 已更新 ({status})")

if __name__ == "__main__":
    main()
