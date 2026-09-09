#!/usr/bin/env python3
"""
WorkBuddy 内容发布状态管理器
=============================
统一管理内容发布状态，解决发布链路断裂问题。

核心功能:
  1. 标记内容为已发布（手动发布后）
  2. 自动检测 Telegram 发布状态
  3. 生成发布状态报告
  4. 为反馈采集器提供准确状态

用法:
  # 标记Twitter已手动发布
  python3 content_status_manager.py --mark-published twitter --url https://x.com/xxx/status/123

  # 标记微博已手动发布
  python3 content_status_manager.py --mark-published weibo --url https://weibo.com/xxx

  # 查看今日发布状态
  python3 content_status_manager.py --status

  # 自动检测Telegram发布状态
  python3 content_status_manager.py --check-telegram
"""

import json
import os
import sys
import time
import argparse
import logging
from datetime import datetime
from pathlib import Path

SC = Path("/home/ubuntu/shared_context")
CONTENT_DIR = SC / "content"
LOG_DIR = SC / "logs"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "content_status.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("content_status")


def load_daily_content():
    """加载今日内容"""
    today = datetime.now().strftime("%Y-%m-%d")
    path = CONTENT_DIR / "daily_content.json"
    if path.exists():
        with open(path, "r") as f:
            return json.load(f)
    return {"date": today}


def save_daily_content(content):
    """保存今日内容"""
    path = CONTENT_DIR / "daily_content.json"
    with open(path, "w") as f:
        json.dump(content, f, indent=2, ensure_ascii=False)


def mark_published(platform, url=None, note=None):
    """标记某平台内容为已发布"""
    content = load_daily_content()
    today = content.get("date", datetime.now().strftime("%Y-%m-%d"))

    if platform == "twitter":
        twitter = content.get("twitter", {})
        twitter["status"] = "published"
        twitter["published_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if url:
            twitter["published_url"] = url
        if note:
            twitter["publish_note"] = note
        content["twitter"] = twitter
    elif platform == "telegram":
        tg = content.get("telegram", {})
        tg["status"] = "sent"
        tg["sent_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content["telegram"] = tg
    else:
        # 微博/小红书/知乎等手动平台
        platforms = content.setdefault("manual_platforms", {})
        pf = platforms.get(platform, {})
        pf["status"] = "published"
        pf["published_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if url:
            pf["published_url"] = url
        if note:
            pf["publish_note"] = note
        platforms[platform] = pf
        content["manual_platforms"] = platforms

    save_daily_content(content)
    logger.info(f"✅ {platform} 已标记为已发布")
    if url:
        logger.info(f"   链接: {url}")
    return True


def check_telegram_status():
    """检查 Telegram 发布状态"""
    content = load_daily_content()
    tg = content.get("telegram", {})
    status = tg.get("status", "unknown")
    sent_at = tg.get("sent_at", "")
    logger.info(f"Telegram 状态: {status}")
    if sent_at:
        logger.info(f"发送时间: {sent_at}")
    return status


def show_status():
    """显示今日发布状态"""
    content = load_daily_content()
    today = content.get("date", "?")
    logger.info(f"\n{'='*50}")
    logger.info(f"📅 内容发布状态 — {today}")
    logger.info(f"{'='*50}")

    # Twitter
    twitter = content.get("twitter", {})
    tw_status = twitter.get("status", "pending")
    icon = "✅" if tw_status == "published" else "⏳" if tw_status == "pending_manual" else "❌"
    logger.info(f"  {icon} Twitter: {tw_status}")
    if twitter.get("published_url"):
        logger.info(f"     链接: {twitter['published_url']}")

    # Telegram
    tg = content.get("telegram", {})
    tg_status = tg.get("status", "unknown")
    icon = "✅" if tg_status == "sent" else "❌"
    logger.info(f"  {icon} Telegram: {tg_status}")

    # 手动平台
    manual = content.get("manual_platforms", {})
    for pf_name in ["weibo", "xiaohongshu", "zhihu", "video_script"]:
        pf = manual.get(pf_name, {})
        pf_status = pf.get("status", "pending")
        icon = "✅" if pf_status == "published" else "⏳"
        logger.info(f"  {icon} {pf_name}: {pf_status}")
        if pf.get("published_url"):
            logger.info(f"     链接: {pf['published_url']}")

    logger.info(f"{'='*50}\n")


def main():
    parser = argparse.ArgumentParser(description="WorkBuddy 内容发布状态管理器")
    parser.add_argument("--mark-published", metavar="PLATFORM",
                        help="标记平台为已发布 (twitter/weibo/xiaohongshu/zhihu)")
    parser.add_argument("--url", default=None, help="发布链接")
    parser.add_argument("--note", default=None, help="备注")
    parser.add_argument("--status", action="store_true", help="查看今日发布状态")
    parser.add_argument("--check-telegram", action="store_true", help="检查Telegram发布状态")
    args = parser.parse_args()

    if args.status:
        show_status()
        return
    if args.check_telegram:
        check_telegram_status()
        return
    if args.mark_published:
        mark_published(args.mark_published, url=args.url, note=args.note)
        show_status()
        return

    parser.print_help()


if __name__ == "__main__":
    main()
