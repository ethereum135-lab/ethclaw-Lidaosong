#!/bin/bash
# 全局状态聚合
cd /Users/lidaosong/zq_web4_trading_system || exit 1
# 先同步A4状态（A4运行在AWS，本地state可能过期）
python3 tools/sync_a4_state.py
# 主聚合
python3 tools/state_aggregator.py