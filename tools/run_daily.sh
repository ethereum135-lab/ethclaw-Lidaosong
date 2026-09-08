#!/bin/bash
# 一键跑：选币库扫描 → 盈利方案
# 每天执行：cd /Users/lidaosong/zq_web4_trading_system && bash tools/run_daily.sh

cd /Users/lidaosong/zq_web4_trading_system

echo "================================================"
echo "📊 选币库每日扫描"
echo "================================================"
python3 tools/daily_scan.py

echo ""
echo "================================================"
echo "💡 候选深度分析 (top 3)"
echo "================================================"

# 从daily_scan输出抓取候选币 — manual
# 先跑deep scan
python3 tools/top_candidates.py 2>/dev/null || true

echo ""
echo "================================================"
echo "✅ 完成"
echo "================================================"
