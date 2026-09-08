#!/usr/bin/env python3
"""
通用状态写入工具 — 每个Agent通过此模块原子写入自己的状态文件

用法：
  from tools.state_writer import write_agent_state
  
  write_agent_state("a1", {
      "status": "ok",
      "data": { "fng": 47, ... },
      "errors": None
  })

写入规则：
  1. 先写 .tmp 文件 → 再 rename 成正式名（原子操作）
  2. 下游Agent永远读不到半成品
  3. 自动添加 timestamp + agent 字段
"""
import json, os, time

STATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "state")

def write_agent_state(agent_name: str, payload: dict):
    """
    原子写入Agent状态文件
    
    Args:
        agent_name: "a1", "a2", ..., "zh"
        payload: 要写入的数据字典（不含timestamp和agent字段）
    """
    os.makedirs(STATE_DIR, exist_ok=True)
    
    # 构建完整状态
    state = {
        "agent": agent_name,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime()),
        "ts_unix": int(time.time()),
        **payload
    }
    
    # 原子写入: .tmp → rename
    tmp_path = os.path.join(STATE_DIR, f"{agent_name}.json.tmp")
    final_path = os.path.join(STATE_DIR, f"{agent_name}.json")
    
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())  # 强制写盘
    
    os.replace(tmp_path, final_path)  # 原子操作
    
    return final_path


def read_agent_state(agent_name: str) -> dict:
    """
    读取Agent最新状态
    如果文件不存在或损坏，返回默认状态
    """
    path = os.path.join(STATE_DIR, f"{agent_name}.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "agent": agent_name,
            "timestamp": None,
            "status": "no_data",
            "data": None,
            "errors": "文件不存在或损坏"
        }


def get_all_agent_states() -> dict:
    """获取所有Agent最新状态"""
    agents = ["a1", "a2", "a3", "a4", "a5", "a6", "a7", "a8", "a9", "zh"]
    result = {}
    for name in agents:
        result[name] = read_agent_state(name)
    return result
