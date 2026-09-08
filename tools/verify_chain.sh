#!/bin/bash
# 验证链检查 — 读取 CHANGE_LOG.md，找出待验证的改动，检查是否生效
# 被 ZH 每日 11:00 和 17:00 cron 调用

cd /Users/lidaosong/zq_web4_trading_system

echo "=== ZQ 验证链检查 $(date '+%Y-%m-%d %H:%M') ==="
echo ""

# 检查 CHANGE_LOG.md 中 验证② 或 验证③ 为 ⏳ 的条目
PENDING=$(grep -c '⏳' CHANGE_LOG.md 2>/dev/null || echo 0)
echo "待验证改动数: ${PENDING}"

if [ "$PENDING" -gt 0 ]; then
    echo ""
    echo "--- 待验证条目 ---"
    grep -B2 -A4 '⏳' CHANGE_LOG.md | head -80
fi

echo ""
echo "--- 系统基础状态 ---"
echo ""

# 1. A4 最近一次运行时间
A4_LAST=$(grep -o '"t": "[^"]*"' /Users/lidaosong/zq_web4_trading_system/data/node_history.jsonl 2>/dev/null | tail -1)
echo "A4 最后节点: ${A4_LAST:-无数据}"

# 2. 当前资产（从 state 读）
if [ -f /Users/lidaosong/zq_web4_trading_system/state/global_state.json ]; then
    TOTAL=$(grep -o '"total_balance": [0-9.]*' /Users/lidaosong/zq_web4_trading_system/state/global_state.json | tail -1 | awk '{print $2}')
    HOLDINGS=$(grep -o '"holdings": [^,]*' /Users/lidaosong/zq_web4_trading_system/state/global_state.json | tail -1 | sed 's/"holdings": //' | sed 's/}$//')
    echo "总资产: \$${TOTAL:-未知}"
    echo "资产数: ${HOLDINGS:-无}"
else
    echo "⚠️ state/global_state.json 不存在"
fi

# 3. 各 Agent 最近状态（从 state/*.json 读）
echo ""
echo "--- Agent 健康 ---"
for agent in a1 a2 a3 a4 a5 a7 a8; do
    if [ -f "/Users/lidaosong/zq_web4_trading_system/state/${agent}.json" ]; then
        TS=$(grep -o '"timestamp": "[^"]*"' "/Users/lidaosong/zq_web4_trading_system/state/${agent}.json" 2>/dev/null | tail -1 | sed 's/"timestamp": "//' | sed 's/"//')
        STATUS=$(grep -o '"status": "[^"]*"' "/Users/lidaosong/zq_web4_trading_system/state/${agent}.json" 2>/dev/null | tail -1 | sed 's/"status": "//' | sed 's/"//')
        echo "  ${agent}: status=${STATUS:-无}, last=${TS:-无}"
    else
        echo "  ${agent}: ❌ 无 state 文件"
    fi
done

echo ""
echo "=== 检查结束 ==="
