# 飞书告警接入指引

## 概述

飞书 Webhook 已集成到 `codex/alert_notifier.py`，作为 Telegram 的降级方案。当 Telegram 发送失败时，自动尝试飞书 Webhook。

## 配置步骤

### 1. 创建飞书自定义机器人

1. 打开飞书 → 进入任意群聊 → 群设置 → 群机器人
2. 点击"添加机器人" → 选择"自定义机器人"
3. 填写机器人名称（如"ZQ交易告警"）
4. 复制 Webhook URL（格式：`https://open.feishu.cn/open-apis/bot/v2/hook/xxxxx`）

### 2. 配置环境变量

在服务器上执行：
```bash
# 添加到 .env 文件
echo 'FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/你的token' >> /home/ubuntu/.vibe-trading/.env

# 或直接添加到 crontab 环境变量
crontab -e
# 在顶部添加：
# FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/你的token
```

### 3. 测试

```bash
# 设置环境变量后测试
export FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/你的token
python3 /home/ubuntu/shared_context/codex/alert_notifier.py \
  --title "测试告警" --message "飞书接入测试" --level INFO
```

### 4. 告警级别

| 级别 | 图标 | 推送 |
|------|------|------|
| CRITICAL | 🔴 | 立即推送 |
| WARNING | 🟡 | 推送 |
| SUCCESS | 🟢 | 推送 |
| INFO | 🔵 | 仅日志 |

## 当前状态

- ✅ 代码已支持（alert_notifier.py `_send_feishu()`）
- ⚠️ 环境变量未配置（需创建飞书机器人获取 Webhook URL）
- 降级逻辑：Telegram 失败 → 自动尝试飞书
