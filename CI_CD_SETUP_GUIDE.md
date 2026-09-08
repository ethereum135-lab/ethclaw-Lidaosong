# CI/CD 快速开始指南

## 当前状态

✅ 代码已推送到 GitHub: https://github.com/ethereum135-lab/ethclaw-Lidaosong
⚠️ GitHub Actions workflow 文件尚未推送（需要PAT添加 workflow 权限）
⏳ 待配置：部署SSH密钥、GitHub Secrets

---

## 第一步：给 PAT 添加 workflow 权限（必需）

您当前的 Personal Access Token 缺少 `workflow` 权限，导致无法推送 `.github/workflows/` 目录。

**操作步骤：**
1. 打开 https://github.com/settings/tokens
2. 找到您当前使用的 Token（ghp_ 开头的那个）
3. 点击编辑（Edit）
4. 勾选 `workflow` 权限（在 Select scopes 区域）
5. 滚动到底部点击 Update token

**然后执行以下命令推送 workflow：**
```bash
cd /Users/lidaosong/zq_web4_trading_system
git add .github/workflows/
git commit -m "Add CI/CD workflow configuration"
git push
```

---

## 第二步：生成部署专用 SSH Key

在本地终端执行：

```bash
# 生成部署密钥（无密码，方便CI使用）
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/github_deploy -N ""

# 查看公钥
cat ~/.ssh/github_deploy.pub

# 查看私钥（后面配置GitHub Secrets会用到）
cat ~/.ssh/github_deploy
```

### 将公钥添加到服务器

```bash
# 方法一：使用 ssh-copy-id
ssh-copy-id -i ~/.ssh/github_deploy.pub ubuntu@15.134.211.154

# 方法二：手动添加
cat ~/.ssh/github_deploy.pub | ssh ubuntu@15.134.211.154 "cat >> ~/.ssh/authorized_keys"
```

### 验证密钥能否登录

```bash
ssh -i ~/.ssh/github_deploy ubuntu@15.134.211.154 "echo 'SSH连接成功'"
```

---

## 第三步：获取 known_hosts

```bash
ssh-keyscan -H 15.134.211.154
```

复制输出的全部内容，后面配置 Secrets 会用到。

---

## 第四步：配置 GitHub Secrets

打开仓库设置页面：
https://github.com/ethereum135-lab/ethclaw-Lidaosong/settings/secrets/actions

点击 **New repository secret**，依次添加以下 Secrets：

| Secret 名称 | 值 | 说明 |
|------------|-----|------|
| `DEPLOY_HOST` | `15.134.211.154` | 服务器IP地址 |
| `DEPLOY_SSH_KEY` | `~/.ssh/github_deploy` 的私钥内容 | 从 `-----BEGIN...` 到 `...END-----` 全部复制 |
| `DEPLOY_KNOWN_HOSTS` | 第三步获取的 known_hosts 内容 | 整段粘贴 |

### 可选的 Secrets（部署通知）

如果需要 Telegram 部署通知，再添加：

| Secret 名称 | 值 |
|------------|-----|
| `TELEGRAM_BOT_TOKEN` | 你的 Telegram Bot Token |
| `TELEGRAM_CHAT_ID` | 你的 Telegram Chat ID |

---

## 第五步：触发首次 CI/CD 验证

配置完所有 Secrets 后，推送一次代码触发 workflow：

```bash
cd /Users/lidaosong/zq_web4_trading_system
git commit --allow-empty -m "Trigger first CI/CD pipeline"
git push
```

然后打开 Actions 页面查看运行状态：
https://github.com/ethereum135-lab/ethclaw-Lidaosong/actions

### 预期的三个 Job

1. **lint-test** - 代码语法检查 ✅
2. **blueprint-check** - 蓝图一致性验证 ✅
3. **deploy** - 自动部署到服务器（仅main分支）✅

---

## 常见问题

### Q: 推送 workflow 失败怎么办？
A: 确认 PAT 已勾选 `workflow` 权限，然后重新 push。

### Q: 部署失败怎么办？
A: 打开 Actions → 点击失败的 workflow → 查看 deploy job 的日志，根据错误信息排查。

### Q: 如何手动触发部署？
A: Actions 页面 → 选择 "CI/CD Full Pipeline" → 点击 "Run workflow" 按钮。

### Q: 如何暂停自动部署？
A: Settings → Actions → 选择 "Disable Actions"。

---

## 安全提醒

1. **永远不要** 将 `.env` 文件、API 密钥、私钥提交到 Git
2. `.gitignore` 已配置排除敏感文件，请勿随意修改
3. 部署用的 SSH Key 仅用于代码部署，不要赋予其他权限
4. 定期轮换 PAT 和 SSH 密钥（建议每 90 天）
