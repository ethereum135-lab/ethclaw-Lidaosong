#!/bin/bash
# deploy.sh — 部署脚本
# 用法: bash scripts/deploy.sh
# 功能: 通过SCP将Python代码+配置文件同步到AWS VPS，重启服务，生成版本记录
set -e

DEPLOY_USER="${DEPLOY_USER:-ubuntu}"
DEPLOY_HOST="${DEPLOY_HOST}"
DEPLOY_PATH="${DEPLOY_PATH:-/home/ubuntu/shared_context}"
VERSION_FILE="${DEPLOY_PATH}/DEPLOY_VERSION.txt"

if [ -z "$DEPLOY_HOST" ]; then
    echo "❌ DEPLOY_HOST 未设置"
    exit 1
fi

echo "🚀 开始部署到 ${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_PATH}"
echo "提交: ${GITHUB_SHA:-local}"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"

# ---------- 1. 同步Python脚本 ----------
echo ""
echo "--- 1/5 同步 Python 脚本 ---"
scp *.py "${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_PATH}/" 2>&1 | tail -5
echo "✅ Python脚本同步完成"

# ---------- 2. 同步子目录模块 ----------
echo ""
echo "--- 2/5 同步子目录模块 ---"
# economy目录
scp economy/*.py "${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_PATH}/economy/" 2>/dev/null && echo "✅ economy模块" || echo "⚠️  economy目录跳过"

# strategy目录
scp strategy/*.py "${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_PATH}/strategy/" 2>/dev/null && echo "✅ strategy模块" || echo "⚠️  strategy目录跳过"

# content目录
scp content/*.py "${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_PATH}/content/" 2>/dev/null && echo "✅ content模块" || echo "⚠️  content目录跳过"

# ---------- 3. 同步蓝图 ----------
echo ""
echo "--- 3/5 同步蓝图 ---"
if [ -f "master_blueprint_v3_final.html" ]; then
    scp master_blueprint_v3_final.html "${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_PATH}/docs/master_blueprint.html"
    echo "✅ 蓝图同步完成"
else
    echo "⚠️  蓝图文件不存在，跳过"
fi

# ---------- 4. 同步SOUL.md ----------
echo ""
echo "--- 4/5 同步 SOUL.md ---"
if [ -f "SOUL.md" ]; then
    scp SOUL.md "${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_PATH}/SOUL.md"
    echo "✅ SOUL.md 同步完成"
else
    echo "⚠️  SOUL.md 不存在，跳过"
fi

# ---------- 5. 写入版本记录 + 验证 ----------
echo ""
echo "--- 5/5 写入版本记录 ---"
ssh "${DEPLOY_USER}@${DEPLOY_HOST}" << EOF
    echo "版本: ${GITHUB_SHA:-local}" > ${VERSION_FILE}
    echo "部署时间: $(date '+%Y-%m-%d %H:%M:%S')" >> ${VERSION_FILE}
    echo "部署者: ${GITHUB_ACTOR:-manual}" >> ${VERSION_FILE}
    echo "提交信息: ${GITHUB_EVENT_MESSAGE:-manual deploy}" >> ${VERSION_FILE}

    echo ""
    echo "=== 部署后验证 ==="
    echo "Python脚本数: \$(ls ${DEPLOY_PATH}/*.py 2>/dev/null | wc -l)"
    echo "Cron任务数: \$(crontab -l 2>/dev/null | wc -l)"
    echo "Vibe-Trading状态: \$(systemctl is-active vibe-trading 2>/dev/null || echo '未运行')"
    echo "蓝图大小: \$(wc -c < ${DEPLOY_PATH}/docs/master_blueprint.html 2>/dev/null || echo 0) bytes"
EOF

echo ""
echo "🎉 部署完成！"
echo "版本文件: ${VERSION_FILE}"
