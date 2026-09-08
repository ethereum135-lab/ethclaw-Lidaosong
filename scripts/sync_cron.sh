#!/bin/bash
# sync_cron.sh — Cron同步脚本
# 用法: bash scripts/sync_cron.sh
# 功能: 将仓库中的cron_list.txt同步到服务器crontab，保留注释行，去重
set -e

DEPLOY_USER="${DEPLOY_USER:-ubuntu}"
DEPLOY_HOST="${DEPLOY_HOST}"
CRON_FILE="cron_list.txt"

if [ -z "$DEPLOY_HOST" ]; then
    echo "❌ DEPLOY_HOST 未设置"
    exit 1
fi

if [ ! -f "$CRON_FILE" ]; then
    echo "❌ cron_list.txt 不存在"
    exit 1
fi

echo "⏰ 同步 Cron 到 ${DEPLOY_USER}@${DEPLOY_HOST}"
echo "本地Cron行数: $(grep -c '^[0-9*]' "$CRON_FILE") 行"

# 读取服务器当前Cron（保留服务器上可能有的额外任务）
echo ""
echo "--- 获取服务器当前Cron ---"
ssh "${DEPLOY_USER}@${DEPLOY_HOST}" 'crontab -l 2>/dev/null || echo ""' > /tmp/server_cron.txt
SERVER_COUNT=$(grep -c '^[0-9*]' /tmp/server_cron.txt 2>/dev/null || echo 0)
echo "服务器Cron行数: $SERVER_COUNT"

# 合并：服务器现有 + 仓库中的新行，去重
echo ""
echo "--- 合并去重 ---"
cat /tmp/server_cron.txt "$CRON_FILE" | sort -u | grep -v '^$' > /tmp/merged_cron.txt
MERGED_COUNT=$(grep -c '^[0-9*]' /tmp/merged_cron.txt 2>/dev/null || echo 0)
echo "合并后Cron行数: $MERGED_COUNT"

# 验证Cron语法（简单检查：每行是否5个时间字段）
echo ""
echo "--- Cron语法验证 ---"
ERRORS=0
while IFS= read -r line; do
    # 跳过空行和注释行
    [[ -z "$line" || "$line" == \#* ]] && continue
    # 检查是否有5个时间字段 + 命令
    FIELDS=$(echo "$line" | awk '{print NF}')
    if [ "$FIELDS" -lt 6 ]; then
        echo "⚠️  可疑行（字段不足）: $line"
        ERRORS=$((ERRORS + 1))
    fi
done < /tmp/merged_cron.txt

if [ "$ERRORS" -gt 0 ]; then
    echo "❌ 发现 $ERRORS 个可疑Cron行，取消同步"
    exit 1
fi
echo "✅ Cron语法验证通过"

# 应用到服务器
echo ""
echo "--- 应用到服务器 ---"
scp /tmp/merged_cron.txt "${DEPLOY_USER}@${DEPLOY_HOST}:/tmp/crontab_new.txt"
ssh "${DEPLOY_USER}@${DEPLOY_HOST}" 'crontab /tmp/crontab_new.txt && rm /tmp/crontab_new.txt'

# 验证
FINAL_COUNT=$(ssh "${DEPLOY_USER}@${DEPLOY_HOST}" 'crontab -l | grep -c "^[0-9*]" 2>/dev/null || echo 0')
echo ""
echo "✅ Cron同步完成"
echo "最终Cron行数: $FINAL_COUNT"

# 清理
rm -f /tmp/server_cron.txt /tmp/merged_cron.txt
