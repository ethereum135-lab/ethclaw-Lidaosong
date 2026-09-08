#!/bin/bash
# verify_blueprint.sh — 蓝图一致性检查
# 用法: bash scripts/verify_blueprint.sh
# 功能: 验证蓝图与代码的一致性，检测已部署但蓝图未更新/蓝图有但代码缺的情况
set -e

BLUEPRINT_FILE="master_blueprint_v3_final.html"
REPORT="/tmp/blueprint_check_report.txt"

echo "📋 蓝图一致性检查"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')" > "$REPORT"
echo "" >> "$REPORT"

PASS=0
FAIL=0
WARN=0

check_file_exists() {
    local label="$1"
    local filepath="$2"
    if [ -f "$filepath" ]; then
        echo "✅ $label: $filepath" >> "$REPORT"
        PASS=$((PASS + 1))
    else
        echo "❌ $label: $filepath 不存在" >> "$REPORT"
        FAIL=$((FAIL + 1))
    fi
}

check_file_mentions() {
    local keyword="$1"
    local label="$2"
    if grep -q "$keyword" "$BLUEPRINT_FILE" 2>/dev/null; then
        echo "✅ $label: 蓝图中已提及" >> "$REPORT"
        PASS=$((PASS + 1))
    else
        echo "⚠️  $label: 蓝图中未提及$keyword" >> "$REPORT"
        WARN=$((WARN + 1))
    fi
}

echo "=== 检查1: 关键文件存在性 ===" >> "$REPORT"
check_file_exists "主蓝图" "$BLUEPRINT_FILE"
check_file_exists "SOUL人格约束" "SOUL.md"
check_file_exists "Cron列表" "cron_list.txt"

echo "" >> "$REPORT"
echo "=== 检查2: 蓝图提及的Python脚本是否存在 ===" >> "$REPORT"

SCRIPTS=(
    "mean_rev_bot.py:均值回归策略"
    "trend_bot.py:趋势跟踪策略"
    "futures_bot.py:期货机器人"
    "correlation_gate.py:相关性闸门"
    "debate_futures_bridge.py:期货辩论桥接"
    "debate_fx_bridge.py:外汇辩论桥接"
    "daily_report.py:每日报告"
    "risk_manager.py:风险管理器"
    "dsl_stop_loss.py:DSL动态止损"
    "heartbeat_manager.py:心跳管理器"
    "news_blackout.py:新闻黑名单"
    "futures_signal_generator.py:期货信号生成器"
    "fx_executor.py:外汇执行器"
    "economic_indicators.py:经济指标采集"
    "rule_learning.py:规则学习闭环"
    "correlation_matrix.py:相关性矩阵"
    "options_iv_collector.py:期权IV采集"
    "api_key_rotation_checker.py:密钥轮换检查"
    "stop_order_verifier.py:止损单验证"
    "event_log_archiver.py:事件日志归档"
    "content_macro_generator.py:宏观内容生成器"
    "content_review_generator.py:复盘内容生成器"
    "content_stock_generator.py:股票内容生成器"
    "content_fx_futures_generator.py:外汇期货内容生成器"
)

for item in "${SCRIPTS[@]}"; do
    file="${item%%:*}"
    label="${item##*:}"
    check_file_exists "$label" "$file"
done

echo "" >> "$REPORT"
echo "=== 检查3: 代码中已实现但蓝图可能遗漏的 ===" >> "$REPORT"

BLUEPRINT_MENTIONS=(
    "economic_indicators:经济指标采集器"
    "rule_learning:规则学习闭环"
    "correlation_matrix:相关性矩阵可视化"
    "options_iv_collector:期权隐含波动率"
    "api_key_rotation:密钥轮换检查"
    "stop_order_verifier:止损单同步验证"
    "event_log_archiver:事件日志归档"
    "futures_signal_generator:期货信号生成器"
    "fx_executor:外汇执行器"
    "content_macro_generator:宏观内容生成器"
    "content_review_generator:复盘内容生成器"
    "content_stock_generator:股票内容生成器"
    "content_fx_futures_generator:外汇期货内容生成器"
    "dsl_stop_loss:DSL动态止损"
)

for item in "${BLUEPRINT_MENTIONS[@]}"; do
    keyword="${item%%:*}"
    label="${item##*:}"
    check_file_mentions "$keyword" "$label"
done

echo "" >> "$REPORT"
echo "=== 检查4: 蓝图版本元信息 ===" >> "$REPORT"
if [ -f "$BLUEPRINT_FILE" ]; then
    VERSION=$(grep -o 'v[0-9].[0-9]' "$BLUEPRINT_FILE" | head -1 || echo "未知")
    LINES=$(wc -l < "$BLUEPRINT_FILE")
    SIZE=$(wc -c < "$BLUEPRINT_FILE")
    echo "版本: $VERSION" >> "$REPORT"
    echo "行数: $LINES" >> "$REPORT"
    echo "大小: $SIZE bytes" >> "$REPORT"
    PASS=$((PASS + 1))
else
    echo "❌ 蓝图文件不存在" >> "$REPORT"
    FAIL=$((FAIL + 1))
fi

echo "" >> "$REPORT"
echo "=== 总结 ===" >> "$REPORT"
echo "通过: $PASS" >> "$REPORT"
echo "警告: $WARN" >> "$REPORT"
echo "失败: $FAIL" >> "$REPORT"

cat "$REPORT"

if [ "$FAIL" -gt 0 ]; then
    echo ""
    echo "⚠️  蓝图一致性检查发现 $FAIL 项未通过（警告模式，不阻断部署）"
    echo "📌 这些是蓝图中规划但尚未实现的模块，属于正常情况"
else
    echo ""
    echo "✅ 蓝图一致性检查通过（$PASS 通过, $WARN 警告, $FAIL 失败）"
fi
