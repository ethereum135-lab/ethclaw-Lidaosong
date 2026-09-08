#!/usr/bin/env bash
# 每日涨幅榜覆盖复盘 + 评分更新 (cron入口)
# 用法: bash tools/daily_diagnostics/run_gainer_review.sh [--all]
#
# --all: 完整运行 (实时拉Binance+更新PROFIT_ARCHIVE.md)

set -e
cd "$(dirname "$0")/../.."  # 到 zq_web4_trading_system 目录

ALL_FLAG=""
if [ "$1" = "--all" ]; then
    ALL_FLAG="--all"
fi

echo "=== 涨幅榜覆盖复盘系统 ==="
date '+%Y-%m-%d %H:%M:%S BJT'

# 第一步: 涨幅榜覆盖复盘 (使用缓存或实时)
if [ "$ALL_FLAG" = "--all" ]; then
    echo ""
    echo "【步骤1/3】实时拉涨幅榜 + 覆盖复盘..."
    python3 tools/gainer_coverage_review.py --top 20 --save
else
    echo ""
    echo "【步骤1/3】涨幅榜覆盖复盘 (已有缓存)..."
    python3 tools/gainer_coverage_review.py --top 20 --save --cached || \
    python3 tools/gainer_coverage_review.py --top 20 --save
fi

# 第二步: 评分系统
echo ""
echo "【步骤2/3】计算10维评分..."
python3 tools/daily_diagnostics/scorer.py --from-cache

# 第三步: 更新PROFIT_ARCHIVE.md
if [ "$ALL_FLAG" = "--all" ]; then
    echo ""
    echo "【步骤3/3】更新PROFIT_ARCHIVE.md..."
    python3 tools/daily_diagnostics/scorer.py --from-cache --update-archive
fi

echo ""
echo "=== 完成 ==="
