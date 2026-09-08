# CI/CD 部署配置指南

## 概览

本项目使用 GitHub Actions 实现全流程 CI/CD：
- **代码检查**：Python 语法验证 + 风格检查 + 密钥扫描
- **蓝图检查**：验证蓝图与代码一致性
- **自动部署**：push 到 main 分支后自动部署到 AWS VPS
- **Cron 同步**：自动同步 crontab 到服务器
- **部署通知**：Telegram 推送部署结果

## 前置条件

1. GitHub 仓库已创建
2. AWS VPS 可通过 SSH 访问
3. 服务器上已有运行环境（Python、systemd 服务等）

## 配置步骤

### 第一步：生成部署专用 SSH Key

在你的本地终端执行：

```bash
# 生成专用的部署密钥（不要设密码，方便CI使用）
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/github_deploy

# 将公钥添加到服务器的 authorized_keys
ssh-copy-id -i ~/.ssh/github_deploy.pub ubuntu@你的服务器IP
```

### 第二步：获取服务器 known_hosts

```bash
ssh-keyscan -H 你的服务器IP
```

复制输出的全部内容，后面会用到。

### 第三步：配置 GitHub Secrets

在 GitHub 仓库页面：`Settings` → `Secrets and variables` → `Actions` → `New repository secret`

添加以下 Secrets：

| Secret 名称 | 值 | 说明 |
|------------|-----|------|
| `DEPLOY_HOST` | `你的服务器IP或域名` | 比如 `1.2.3.4` 或 `web4.xxx.com` |
| `DEPLOY_SSH_KEY` | `~/.ssh/github_deploy` 的私钥内容 | 从 `-----BEGIN...` 到 `...END-----` 全部复制 |
| `DEPLOY_KNOWN_HOSTS` | 第二步获取的 known_hosts 内容 | 整段粘贴 |
| `TELEGRAM_BOT_TOKEN` | `你的Telegram Bot Token` | 可选，用于部署通知 |
| `TELEGRAM_CHAT_ID` | `你的Telegram Chat ID` | 可选，部署通知接收者 |

### 第四步：推送到 GitHub

```bash
cd /path/to/your/project
git init
git add .
git commit -m "Initial commit: full trading system with CI/CD"
git branch -M main
git remote add origin https://github.com/你的用户名/你的仓库名.git
git push -u origin main
```

### 第五步：验证

推送完成后：
1. 打开 GitHub 仓库 → `Actions` 标签
2. 应该能看到一个正在运行的 workflow
3. 等待完成（约2-3分钟）
4. 检查三个 job：lint-test ✅、blueprint-check ✅、deploy ✅

如果部署失败，点击失败的 job 查看日志排查。

## 文件结构

```
.github/
└── workflows/
    └── ci-cd.yml           # CI/CD 主配置

scripts/
├── deploy.sh             # 部署脚本
├── sync_cron.sh          # Cron 同步脚本
└── verify_blueprint.sh   # 蓝图一致性检查

cron_list.txt             # Cron 任务清单（Git管理）
```

## 工作流详解

### Job 1: lint-test（代码检查）

每次 push 和 PR 都会运行：
- Python 语法检查（py_compile）— **失败则阻断部署**
- Flake8 风格检查（仅警告，不阻断）
- 硬编码密钥扫描（警告）

### Job 2: blueprint-check（蓝图检查）

验证 24 个关键脚本的存在性 + 蓝图提及情况：
- 关键策略脚本存在性
- 内容生成器存在性
- 风控组件存在性
- 蓝图版本元信息

### Job 3: deploy（部署）

仅在 push 到 main/master 时触发：
1. 同步所有 `.py` 脚本到服务器
2. 同步子目录模块（economy/strategy/content）
3. 同步蓝图 master_blueprint_v3_final.html → docs/master_blueprint.html
4. 同步 SOUL.md
5. 写入版本记录文件 DEPLOY_VERSION.txt
6. 同步 crontab（去重合并）
7. 部署后验证
8. Telegram 通知（可选）

## 常见问题

### Q: 如何只触发代码检查不部署？
A: 提交到非 main 分支或发起 PR，只会运行 lint-test 和 blueprint-check。

### Q: 如何手动触发部署？
A: GitHub Actions 页面 → 对应 workflow → `Run workflow` 按钮。

### Q: 部署失败了怎么办？
A: 查看 Actions 日志，修复后重新 push。代码不会影响正在运行的系统，部署失败时服务器保持旧版本。

### Q: 如何新增 Cron 任务？
A: 在 `cron_list.txt` 中添加一行，push 后自动同步到服务器。

### Q: 如何临时停止自动部署？
A: GitHub → Settings → Actions → Disable Actions。

## 安全说明

- SSH 密钥仅用于部署，只对特定IP/用户开放
- API 密钥存储在 `.env` 文件中，**不要提交到 Git**
- 确认 `.gitignore` 包含 `.env`、`*.log`、`logs/` 等敏感文件
- 密钥轮换检查器会自动提醒90天更换密钥
