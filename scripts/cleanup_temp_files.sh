#!/bin/bash
# ZQ 系统临时文件自动清理
# 每天04:30由cron触发（在04:00全量备份之后）
# 铁律九：工具脚本自身产生的垃圾，脚本结束时清理，不依赖外部cron扫尾
# 此cron只清理漏网之鱼 + 旧A7测试脚本残留

ZQ_HOME="/Users/lidaosong/zq_web4_trading_system"
NOW=$(date +%s)
CLEANED=0

echo "🧹 ZQ 临时文件清理 — $(date '+%Y-%m-%d %H:%M')"
echo ""

# 1. tmp/ 目录：清理 >24h 的旧文件
if [ -d "$ZQ_HOME/tmp" ]; then
    COUNT=$(find "$ZQ_HOME/tmp" -type f -mtime +1 2>/dev/null | wc -l | tr -d ' ')
    if [ "$COUNT" -gt 0 ]; then
        find "$ZQ_HOME/tmp" -type f -mtime +1 -delete 2>/dev/null
        echo "✅ tmp/: 清理 $COUNT 个 >24h的旧文件"
        CLEANED=$((CLEANED + COUNT))
    else
        echo "✅ tmp/: 无 >24h文件需清理"
    fi
fi

# 2. audit/TRADES.md.* 备份残留：清理所有.bak/.backup/.restored
for ext in bak backup restored; do
    for f in "$ZQ_HOME/audit/TRADES.md.$ext"; do
        if [ -f "$f" ]; then
            rm "$f"
            echo "✅ audit/: 删除 $f"
            CLEANED=$((CLEANED + 1))
        fi
    done
done

echo ""
if [ "$CLEANED" -eq 0 ]; then
    echo "✅ 无文件需清理"
else
    echo "✅ 共清理 $CLEANED 个文件"
fi
