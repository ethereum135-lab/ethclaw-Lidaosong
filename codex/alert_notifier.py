#!/usr/bin/env python3
"""
Codex 告警通知器
=================
统一告警入口，通过 Telegram 推送告警到手机。

告警级别:
  CRITICAL  — 红色 🔴  立即推送
  WARNING   — 黄色 🟡  推送
  INFO      — 蓝色 🔵  仅记录日志

用法:
  from alert_notifier import AlertNotifier
  notifier = AlertNotifier()
  notifier.send("标题", "内容", level="CRITICAL")

  # 或命令行
  python3 alert_notifier.py --title "测试" --message "内容" --level WARNING
"""

import json
import os
import sys
import time
import logging
import argparse
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path

SHARED = Path("/home/ubuntu/shared_context")
LOG_DIR = SHARED / "logs"
ALERTS_DIR = SHARED / "alerts"

LOG_DIR.mkdir(parents=True, exist_ok=True)
ALERTS_DIR.mkdir(parents=True, exist_ok=True)

TELEGRAM_BOT = "8651889565:AAFYPPgPimA-GTckG93oJXorNRcQ9n8UQoY"
TELEGRAM_CHAT = "8403170666"

LEVEL_ICONS = {
    "CRITICAL": "🔴",
    "WARNING": "🟡",
    "INFO": "🔵",
    "SUCCESS": "🟢",
}

LEVEL_COLORS = {
    "CRITICAL": "#dc2626",
    "WARNING": "#f59e0b",
    "INFO": "#3b82f6",
    "SUCCESS": "#22c55e",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "alert_notifier.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("alert")


class AlertNotifier:
    """统一告警通知器"""

    def __init__(self):
        self.bot = TELEGRAM_BOT
        self.chat = TELEGRAM_CHAT
        self.alerts_file = ALERTS_DIR / f"{datetime.now().strftime('%Y%m%d')}_alerts.jsonl"
        self.latest_file = ALERTS_DIR / "latest_alert.json"
        self.daily_state = self._load_daily_state()

    def _load_daily_state(self):
        """加载当日告警状态（防刷屏）"""
        today = datetime.now().strftime("%Y%m%d")
        state_file = SHARED / "monitor" / f"alert_state_{today}.json"
        if state_file.exists():
            try:
                with open(state_file, "r") as f:
                    return json.load(f)
            except:
                pass
        return {"sent_count": 0, "dedupe": {}, "last_reset": datetime.now().isoformat()}

    def _save_daily_state(self):
        """保存当日告警状态"""
        today = datetime.now().strftime("%Y%m%d")
        state_file = SHARED / "monitor" / f"alert_state_{today}.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(state_file, "w") as f:
            json.dump(self.daily_state, f, indent=2, ensure_ascii=False)

    def _is_deduped(self, key, window_seconds=300):
        """去重检查：同一告警5分钟内不重复推送"""
        now = time.time()
        last = self.daily_state["dedupe"].get(key, 0)
        if now - last < window_seconds:
            return True  # 在去重窗口内
        self.daily_state["dedupe"][key] = now
        return False

    def _check_rate_limit(self, max_per_hour=20):
        """限流检查：每小时最多20条告警"""
        if self.daily_state["sent_count"] >= max_per_hour:
            logger.warning("告警限流: 当日已发送 %d 条，超过上限 %d", self.daily_state["sent_count"], max_per_hour)
            return False
        return True

    def _send_telegram(self, text):
        """发送 Telegram 消息"""
        try:
            url = f"https://api.telegram.org/bot{self.bot}/sendMessage"
            data = urllib.parse.urlencode({
                "chat_id": self.chat,
                "text": text,
                "parse_mode": "HTML",
            }).encode()
            req = urllib.request.Request(url, data=data)
            resp = urllib.request.urlopen(req, timeout=10)
            return resp.status == 200
        except Exception as e:
            logger.error("Telegram发送失败: %s", e)
            return False

    def _format_message(self, title, message, level, task_name=None):
        """格式化 Telegram 消息"""
        icon = LEVEL_ICONS.get(level, "⚪")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        parts = [f"{icon} <b>[{level}]</b> {title}"]
        if task_name:
            parts.append(f"\n📋 任务: <code>{task_name}</code>")
        parts.append(f"\n📝 {message}")
        parts.append(f"\n🕐 {now_str}")
        return "".join(parts)

    def _write_alert_log(self, alert):
        """写入告警日志"""
        with open(self.alerts_file, "a") as f:
            f.write(json.dumps(alert, ensure_ascii=False) + "\n")
        with open(self.latest_file, "w") as f:
            json.dump(alert, f, indent=2, ensure_ascii=False)

    def send(self, title, message, level="WARNING", task_name=None, force=False):
        """
        发送告警

        Args:
            title: 告警标题
            message: 告警内容
            level: CRITICAL | WARNING | INFO | SUCCESS
            task_name: 关联任务名（可选）
            force: 强制发送，跳过去重

        Returns:
            bool: 是否发送成功
        """
        # INFO 级别只记录日志，不推送
        if level == "INFO":
            logger.info(f"[{level}] {title}: {message}")
            self._write_alert_log({
                "title": title, "message": message,
                "level": level, "task": task_name,
                "pushed": False,
                "timestamp": datetime.now().isoformat(),
            })
            return True

        # 去重检查
        dedupe_key = f"{level}:{task_name or title}"
        if not force and self._is_deduped(dedupe_key):
            logger.info("告警去重: %s (5分钟内已发送)", dedupe_key)
            return False

        # 限流检查
        if not force and not self._check_rate_limit():
            logger.warning("告警限流，跳过: %s", title)
            self._write_alert_log({
                "title": title, "message": message,
                "level": level, "task": task_name,
                "pushed": False, "reason": "rate_limited",
                "timestamp": datetime.now().isoformat(),
            })
            return False

        # 格式化消息
        text = self._format_message(title, message, level, task_name)

        # 发送 Telegram
        success = self._send_telegram(text)

        # 记录
        self.daily_state["sent_count"] += 1
        self._save_daily_state()

        alert = {
            "title": title,
            "message": message,
            "level": level,
            "task": task_name,
            "pushed": success,
            "sent_count_today": self.daily_state["sent_count"],
            "timestamp": datetime.now().isoformat(),
        }
        self._write_alert_log(alert)

        if success:
            logger.info(f"[{level}] 告警已推送: {title}")
        else:
            logger.error(f"[{level}] 告警推送失败: {title}")

        return success

    def send_critical(self, title, message, task_name=None):
        return self.send(title, message, level="CRITICAL", task_name=task_name)

    def send_warning(self, title, message, task_name=None):
        return self.send(title, message, level="WARNING", task_name=task_name)

    def send_info(self, title, message, task_name=None):
        return self.send(title, message, level="INFO", task_name=task_name)

    def send_success(self, title, message, task_name=None):
        return self.send(title, message, level="SUCCESS", task_name=task_name)


def main():
    parser = argparse.ArgumentParser(description="Codex 告警通知器")
    parser.add_argument("--title", required=True, help="告警标题")
    parser.add_argument("--message", required=True, help="告警内容")
    parser.add_argument("--level", default="WARNING",
                        choices=["CRITICAL", "WARNING", "INFO", "SUCCESS"],
                        help="告警级别")
    parser.add_argument("--task", default=None, help="关联任务名")
    parser.add_argument("--force", action="store_true", help="强制发送，跳过去重")
    args = parser.parse_args()

    notifier = AlertNotifier()
    notifier.send(args.title, args.message, level=args.level,
                  task_name=args.task, force=args.force)


if __name__ == "__main__":
    main()
