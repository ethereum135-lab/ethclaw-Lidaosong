#!/usr/bin/env python3
"""
社交反馈采集器 v1.0
读取已发布内容的互动数据（点赞/转发/评论/阅读量）
支持: Twitter API v2, Telegram Bot API, 手动录入模板
Cron: 每日 12:00 和 00:00 运行
"""
import json, time, os, sys, urllib.request, urllib.parse, datetime

SC = "/home/ubuntu/shared_context"
FEEDBACK_DIR = os.path.join(SC, "content", "feedback")
os.makedirs(FEEDBACK_DIR, exist_ok=True)

# === Twitter API v2 ===
TWITTER_BEARER = os.environ.get("TWITTER_BEARER_TOKEN", "")

# === Telegram Bot API ===
TELEGRAM_BOT = "8651889565:AAFYPPgPimA-GTckG93oJXorNRcQ9n8UQoY"
TELEGRAM_CHAT = "8403170666"

# === Log event ===
try:
    sys.path.insert(0, SC)
    import bus_bridge
except Exception:
    bus_bridge = None


def read_json(path):
    try:
        return json.load(open(path))
    except Exception:
        return {}


def write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def log_event(event_type, message):
    """写入事件总线"""
    ndjson_path = os.path.join(SC, "events", "events.ndjson")
    os.makedirs(os.path.join(SC, "events"), exist_ok=True)
    entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "type": event_type,
        "source": "feedback_collector",
        "message": message,
    }
    with open(ndjson_path, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    if bus_bridge:
        try:
            bus_bridge._publish("content.feedback", message, "workbuddy")
        except Exception:
            pass


# ============================================================
# Twitter 反馈采集
# ============================================================
def collect_twitter_metrics(daily_content, content_date):
    """通过 Twitter API v2 获取推文互动数据"""
    twitter_data = daily_content.get("twitter", {})
    status = twitter_data.get("status", "pending")

    if status != "published":
        return {
            "status": "not_published",
            "reason": f"内容状态为{status}，未发布到Twitter",
            "metrics": None,
        }

    tweet_ids = twitter_data.get("tweet_ids", [])
    if not tweet_ids:
        return {
            "status": "no_tweet_ids",
            "reason": "已发布但未记录tweet_ids",
            "metrics": None,
        }

    if not TWITTER_BEARER:
        return {
            "status": "no_api_key",
            "reason": "未配置TWITTER_BEARER_TOKEN",
            "metrics": None,
        }

    # Twitter API v2: GET /2/tweets
    # 公共指标: public_metrics (retweet_count, reply_count, like_count, quote_count, impression_count)
    all_metrics = []
    try:
        for tweet_id in tweet_ids:
            url = f"https://api.twitter.com/2/tweets/{tweet_id}?tweet.fields=public_metrics,created_at"
            req = urllib.request.Request(url)
            req.add_header("Authorization", f"Bearer {TWITTER_BEARER}")
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read())
            pm = data.get("data", {}).get("public_metrics", {})
            all_metrics.append({
                "tweet_id": tweet_id,
                "impressions": pm.get("impression_count", 0),
                "likes": pm.get("like_count", 0),
                "retweets": pm.get("retweet_count", 0),
                "replies": pm.get("reply_count", 0),
                "quotes": pm.get("quote_count", 0),
            })
    except Exception as e:
        return {
            "status": "api_error",
            "reason": str(e)[:100],
            "metrics": None,
        }

    total_imp = sum(m["impressions"] for m in all_metrics)
    total_likes = sum(m["likes"] for m in all_metrics)
    total_rt = sum(m["retweets"] for m in all_metrics)
    total_rp = sum(m["replies"] for m in all_metrics)
    eng = total_likes + total_rt + total_rp + sum(m["quotes"] for m in all_metrics)
    eng_rate = round(eng / max(total_imp, 1) * 100, 2)

    return {
        "status": "collected",
        "tweet_count": len(all_metrics),
        "per_tweet": all_metrics,
        "totals": {
            "impressions": total_imp,
            "likes": total_likes,
            "retweets": total_rt,
            "replies": total_rp,
            "engagement": eng,
            "engagement_rate_pct": eng_rate,
        },
    }


# ============================================================
# Telegram 反馈采集（检查消息送达状态）
# ============================================================
def collect_telegram_metrics(daily_content, content_date):
    """检查Telegram消息发送状态"""
    tg_data = daily_content.get("telegram", {})
    status = tg_data.get("status", "unknown")
    sent_at = tg_data.get("sent_at", "")

    # Telegram Bot API可以获取消息数（仅已发送确认）
    result = {
        "status": status,
        "sent_at": sent_at,
        "delivered": status == "sent",
    }

    # 尝试获取Telegram Bot的更新（如果有用户交互）
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT}/getUpdates"
        req = urllib.request.Request(url)
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        updates = data.get("result", [])
        # 统计今日互动消息数
        today_str = content_date
        interacted = 0
        reactions = 0
        for update in updates:
            msg = update.get("message", update.get("callback_query", {}))
            if isinstance(msg, dict):
                msg_date = msg.get("date", 0)
                if msg_date:
                    msg_dt = datetime.datetime.fromtimestamp(msg_date).strftime("%Y-%m-%d")
                    if msg_dt == today_str:
                        interacted += 1
                if "reaction" in update:
                    reactions += 1
        result["user_interactions"] = interacted
        result["reactions"] = reactions
    except Exception:
        result["user_interactions"] = 0
        result["reactions"] = 0

    return result


# ============================================================
# 手动录入模板生成（微博/小红书/知乎等无API平台）
# ============================================================
def generate_manual_template(platform, content, content_date):
    """为无API平台生成手动录入模板"""
    publish_file = os.path.join(SC, "content", "publish", f"{platform}_{content_date}.txt")
    if platform == "zhihu":
        publish_file = publish_file.replace(".txt", ".md")

    has_content = os.path.exists(publish_file)

    return {
        "status": "manual_template",
        "published": has_content,
        "publish_file": publish_file if has_content else None,
        "instructions": f"手动发布后，在此JSON中填入实际互动数据",
        "fields_to_fill": {
            "views": 0,
            "likes": 0,
            "comments": 0,
            "shares": 0,
            "favorites": 0,
            "engagement_rate_pct": 0,
            "top_comment": "",
            "published_url": "",
            "published_at": "",
        },
    }


# ============================================================
# 主采集流程
# ============================================================
def collect_daily_feedback():
    """采集今日+昨日的反馈数据"""
    today = time.strftime("%Y-%m-%d")
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    # 优先采集昨日的数据（给平台24小时积累互动）
    target_date = yesterday

    daily_path = os.path.join(SC, "content", "daily_content.json")
    daily_content = read_json(daily_path)

    # 如果daily_content不是目标日期的，尝试读取历史文件
    if daily_content.get("date") != target_date:
        log_event("feedback_skip", f"daily_content日期={daily_content.get('date')}，目标日期={target_date}，跳过")
        # 采集今日的实时数据
        target_date = today

    if daily_content.get("date") != target_date:
        log_event("feedback_skip", f"无匹配内容，跳过反馈采集")
        return

    print(f"[反馈采集] 采集 {target_date} 的社交反馈...")

    metrics = {
        "date": target_date,
        "collected_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "collector_version": "1.0",
    }

    # 1. Twitter
    print("  → Twitter...")
    metrics["twitter"] = collect_twitter_metrics(daily_content, target_date)

    # 2. Telegram
    print("  → Telegram...")
    metrics["telegram"] = collect_telegram_metrics(daily_content, target_date)

    # 3. 微博（手动模板）
    print("  → 微博 (手动模板)...")
    metrics["weibo"] = generate_manual_template("weibo", daily_content.get("weibo", {}), target_date)

    # 4. 小红书（手动模板）
    print("  → 小红书 (手动模板)...")
    metrics["xiaohongshu"] = generate_manual_template("xiaohongshu", daily_content.get("xiaohongshu", {}), target_date)

    # 5. 知乎（手动模板）
    print("  → 知乎 (手动模板)...")
    metrics["zhihu"] = generate_manual_template("zhihu", daily_content.get("zhihu", {}), target_date)

    # 6. 视频脚本状态
    vs = daily_content.get("video_script", {})
    metrics["video_script"] = {
        "status": vs.get("status", "pending"),
        "title": vs.get("title", ""),
        "estimated_seconds": vs.get("estimated_seconds", 0),
        "platforms": vs.get("platforms", []),
    }

    # 汇总
    auto_collected = 0
    manual_pending = 0
    for platform, data in metrics.items():
        if not isinstance(data, dict):
            continue
        s = data.get("status", "")
        if s in ("collected", "sent", "delivered"):
            auto_collected += 1
        elif s in ("manual_template", "not_published", "no_api_key", "no_tweet_ids"):
            manual_pending += 1

    metrics["summary"] = {
        "total_platforms": 6,
        "auto_collected": auto_collected,
        "manual_pending": manual_pending,
        "coverage_pct": round(auto_collected / 6 * 100, 1),
        "best_platform": "",
        "best_topic": "",
    }

    # 写入文件
    output_path = os.path.join(FEEDBACK_DIR, f"metrics_{target_date}.json")
    write_json(output_path, metrics)
    print(f"[反馈采集] 已保存 → {output_path}")

    # 事件总线通知
    log_event("feedback_collected", f"{target_date} 反馈采集完成: 自动{auto_collected}/6, 手动待录{manual_pending}/6")

    # 如果是周日，生成周报
    if datetime.date.today().weekday() == 6:  # Sunday
        generate_weekly_summary()


# ============================================================
# 周报汇总
# ============================================================
def generate_weekly_summary():
    """每周日生成周度汇总"""
    today = datetime.date.today()
    week_start = today - datetime.timedelta(days=7)

    weekly_data = {
        "week_start": week_start.strftime("%Y-%m-%d"),
        "week_end": today.strftime("%Y-%m-%d"),
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "platforms": {},
    }

    # 汇总7天数据
    for i in range(7):
        d = (week_start + datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        metrics_path = os.path.join(FEEDBACK_DIR, f"metrics_{d}.json")
        if not os.path.exists(metrics_path):
            continue
        data = read_json(metrics_path)
        for platform in ["twitter", "telegram", "weibo", "xiaohongshu", "zhihu"]:
            pd = data.get(platform, {})
            if not isinstance(pd, dict):
                continue
            if platform not in weekly_data["platforms"]:
                weekly_data["platforms"][platform] = {
                    "total_auto": 0,
                    "total_manual": 0,
                    "daily": [],
                }
            s = pd.get("status", "")
            if s in ("collected", "sent", "delivered"):
                weekly_data["platforms"][platform]["total_auto"] += 1
            elif s == "manual_template" and pd.get("published"):
                weekly_data["platforms"][platform]["total_manual"] += 1
            weekly_data["platforms"][platform]["daily"].append({
                "date": d,
                "status": s,
            })

    # 写入周报
    weekly_path = os.path.join(FEEDBACK_DIR, "weekly_summary.json")
    write_json(weekly_path, weekly_data)
    print(f"[反馈采集] 周报已生成 → {weekly_path}")
    log_event("feedback_weekly", f"周报已生成: {week_start} ~ {today}")


# ============================================================
# 手动录入接口
# ============================================================
def manual_input(date_str, platform, **kwargs):
    """手动更新某平台某日的反馈数据"""
    metrics_path = os.path.join(FEEDBACK_DIR, f"metrics_{date_str}.json")
    if not os.path.exists(metrics_path):
        print(f"文件不存在: {metrics_path}，请先运行自动采集")
        return

    data = read_json(metrics_path)
    if platform not in data:
        data[platform] = {}

    data[platform].update(kwargs)
    data[platform]["status"] = "manually_entered"
    data[platform]["entered_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

    write_json(metrics_path, data)
    print(f"[反馈采集] 手动录入完成: {date_str} {platform}")
    log_event("feedback_manual", f"手动录入: {date_str} {platform}")


# ============================================================
# 入口
# ============================================================
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="社交反馈采集器")
    parser.add_argument("--manual", nargs="+", metavar="KEY=VALUE",
                        help="手动录入: --manual date=2026-09-08 platform=twitter likes=15 views=1200")
    args = parser.parse_args()

    if args.manual:
        kwargs = {}
        for item in args.manual:
            k, v = item.split("=", 1)
            try:
                v = int(v)
            except ValueError:
                pass
            kwargs[k] = v
        date_str = kwargs.pop("date", time.strftime("%Y-%m-%d"))
        platform = kwargs.pop("platform", "twitter")
        manual_input(date_str, platform, **kwargs)
    else:
        collect_daily_feedback()
