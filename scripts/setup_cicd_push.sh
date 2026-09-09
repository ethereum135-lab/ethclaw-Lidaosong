#!/bin/bash
# ============================================================
#  一键推送 CI/CD Workflow 并触发首次部署
# ============================================================
# 使用前请确保：
#   1. 您的 PAT (ghp_...) 已添加 workflow 权限
#      地址：https://github.com/settings/tokens
#   2. 在以下 TOKEN= 处填入您的 PAT
# ============================================================

# ====== 请填入您的 GitHub Personal Access Token ======
TOKEN="your_github_personal_access_token_here"
# ====================================================

set -e

cd /Users/lidaosong/zq_web4_trading_system

echo ""
echo "🚀 === 开始配置 CI/CD Workflow ==="
echo ""

# 1. 更新 remote URL 包含 token
echo "📝 更新 Git 远程仓库配置..."
git remote set-url origin "https://ethereum135-lab:${TOKEN}@github.com/ethereum135-lab/ethclaw-Lidaosong.git"

# 2. 添加并提交 workflow 文件
echo "📦 提交 CI/CD Workflow 文件..."
git add .github/workflows/
git commit -m "feat: Add CI/CD workflow (lint-test, blueprint-check, deploy)" 2>/dev/null || echo "   (已提交，跳过)"

# 3. 推送到 GitHub
echo "☁️  推送到 GitHub..."
git push -u origin main

echo ""
echo "✅ Workflow 推送成功！"
echo ""
echo "🔗 Actions 页面: https://github.com/ethereum135-lab/ethclaw-Lidaosong/actions"
echo ""
echo "⏳ 首次 CI/CD Pipeline 已自动触发，约 2-3 分钟完成"
echo "   - lint-test     (代码语法检查)"
echo "   - blueprint-check (蓝图一致性验证)"
echo "   - deploy        (部署到 VPS)"
echo ""
