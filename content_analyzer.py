#!/usr/bin/env python3
"""
内容效果分析器 v1.0
读取本周所有反馈数据，分析哪类内容/平台最受欢迎，输出优化建议
Cron: 每周日 10:00 运行
"""
import json, time, os, sys, datetime, glob, urllib.request

SC = "/home/ubuntu/shared_context"
FEEDBACK_DIR = os.path.join(SC, "content", "feedback")
ANALYSIS_DIR = os.path.join(SC, "content", "analysis")
os.makedirs(ANALYSIS_DIR, exist_ok=True)

# === DeepSeek LLM 用于内容归因分析 ===
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

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
    ndjson_path = os.path.join(SC, "events", "events.ndjson")
    os.makedirs(os.path.join(SC, "events"), exist_ok=True)
    entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "type": event_type,
        "source": "content_analyzer",
        "message": message,
    }
    with open(ndjson_path, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    if bus_bridge:
        try:
            bus_bridge._publish("content.analysis", message, "workbuddy")
        except Exception:
            pass


def call_llm(prompt, max_tokens=600):
    """调用DeepSeek生成分析建议"""
    if not DEEPSEEK_KEY or not DEEPSEEK_KEY.startswith("sk-"):
        return None
    try:
        req = urllib.request.Request(
            DEEPSEEK_URL,
            data=json.dumps({
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": 0.3,
            }).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {DEEPSEEK_KEY}",
            },
        )
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"LLM调用失败: {str(e)[:80]}")
        return None


# ============================================================
# 数据收集
# ============================================================
def collect_week_data():
    """收集最近7天的反馈数据"""
    today = datetime.date.today()
    week_start = today - datetime.timedelta(days=7)

    daily_metrics = []
    for i in range(8):
        d = (week_start + datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        path = os.path.join(FEEDBACK_DIR, f"metrics_{d}.json")
        if os.path.exists(path):
            data = read_json(path)
            data["weekday"] = (week_start + datetime.timedelta(days=i)).strftime("%A")
            daily_metrics.append(data)

    return daily_metrics, week_start, today


# ============================================================
# 平台效果分析
# ============================================================
def analyze_platforms(daily_metrics):
    """分析各平台互动表现"""
    platform_stats = {}

    for day in daily_metrics:
        date = day.get("date", "")
        for platform in ["twitter", "telegram", "weibo", "xiaohongshu", "zhihu", "video_script"]:
            pd = day.get(platform, {})
            if not isinstance(pd, dict):
                continue

            if platform not in platform_stats:
                platform_stats[platform] = {
                    "dates": [],
                    "auto_collected": 0,
                    "manual_entered": 0,
                    "not_published": 0,
                    "total_likes": 0,
                    "total_impressions": 0,
                    "total_engagement": 0,
                    "total_interactions": 0,
                    "best_day": "",
                    "best_day_metrics": 0,
                }

            ps = platform_stats[platform]
            ps["dates"].append(date)

            status = pd.get("status", "")
            if status in ("collected", "sent", "delivered"):
                ps["auto_collected"] += 1
            elif status == "manually_entered":
                ps["manual_entered"] += 1
            elif status in ("not_published", "no_api_key", "no_tweet_ids", "manual_template"):
                ps["not_published"] += 1

            # 汇总指标
            likes = pd.get("likes", 0)
            if likes == 0 and "totals" in pd:
                likes = pd["totals"].get("likes", 0)
            ps["total_likes"] += likes

            impressions = pd.get("views", 0) or pd.get("impressions", 0)
            if impressions == 0 and "totals" in pd:
                impressions = pd["totals"].get("impressions", 0)
            ps["total_impressions"] += impressions

            interactions = pd.get("user_interactions", 0) or pd.get("reactions", 0)
            ps["total_interactions"] += interactions

            day_metric = likes + impressions + interactions
            if day_metric > ps["best_day_metrics"]:
                ps["best_day_metrics"] = day_metric
                ps["best_day"] = date

    # 计算互动率
    for platform, ps in platform_stats.items():
        if ps["total_impressions"] > 0:
            ps["engagement_rate_pct"] = round(
                (ps["total_likes"] + ps["total_interactions"]) / ps["total_impressions"] * 100, 2
            )
        else:
            ps["engagement_rate_pct"] = 0

    return platform_stats


# ============================================================
# 内容主题分析
# ============================================================
def analyze_content_topics(daily_metrics):
    """分析哪类内容主题表现最好"""
    topics = {
        "每日速报": {"count": 0, "platforms": set()},
        "持仓详情": {"count": 0, "platforms": set()},
        "合约信号": {"count": 0, "platforms": set()},
        "跨市场": {"count": 0, "platforms": set()},
        "操作建议": {"count": 0, "platforms": set()},
    }

    for day in daily_metrics:
        # 从daily_content推断内容类型
        twitter = day.get("twitter", {})
        if isinstance(twitter, dict):
            if twitter.get("status") in ("collected", "published", "pending_manual"):
                for topic in topics:
                    topics[topic]["count"] += 1
                    topics[topic]["platforms"].add("twitter")

    # 转set为list
    for t in topics.values():
        t["platforms"] = list(t["platforms"])

    return topics


# ============================================================
# 发布时间分析
# ============================================================
def analyze_publish_times(daily_metrics):
    """分析最佳发布时间"""
    time_stats = {
        "morning_08": {"count": 0, "total_metrics": 0},
        "evening_20": {"count": 0, "total_metrics": 0},
    }

    for day in daily_metrics:
        ts = day.get("collected_at", "")
        if "08" in ts:
            time_stats["morning_08"]["count"] += 1
        elif "20" in ts:
            time_stats["evening_20"]["count"] += 1

    return time_stats


# ============================================================
# 生成优化建议
# ============================================================
def generate_recommendations(platform_stats, content_topics, time_stats):
    """生成内容优化建议"""
    recommendations = []

    # 1. 平台建议
    best_platform = None
    best_score = -1
    for platform, stats in platform_stats.items():
        score = stats["total_likes"] + stats["total_interactions"]
        if score > best_score:
            best_score = score
            best_platform = platform

    if best_platform:
        recommendations.append(
            f"最佳平台: {best_platform}（互动总分{best_score}）→ 建议加大该平台投入"
        )

    # 2. 覆盖率建议
    total_not_published = sum(s["not_published"] for s in platform_stats.values())
    if total_not_published > 10:
        recommendations.append(
            f"未发布内容{total_not_published}条 → 优先配置Twitter API Key实现自动发布"
        )

    # 3. 手动录入建议
    total_manual = sum(s["manual_entered"] for s in platform_stats.values())
    if total_manual == 0:
        recommendations.append(
            "本周无手动录入数据 → 发布内容后请手动填写互动数据（python3 content_feedback_collector.py --manual date=2026-09-08 platform=weibo views=500 likes=5）"
        )

    # 4. 内容主题建议
    top_topic = max(content_topics.items(), key=lambda x: x[1]["count"])
    if top_topic[1]["count"] > 0:
        recommendations.append(
            f"最高频主题: {top_topic[0]}（{top_topic[1]['count']}次）→ 考虑增加深度分析"
        )

    # 5. 时间建议
    m_count = time_stats["morning_08"]["count"]
    e_count = time_stats["evening_20"]["count"]
    if m_count > e_count:
        recommendations.append("上午发布频次更高 → 观察上午内容互动是否更佳")
    elif e_count > m_count:
        recommendations.append("下午发布频次更高 → 观察下午内容互动是否更佳")

    # 默认建议
    if not recommendations:
        recommendations.append("数据量不足，继续积累后可生成更精准建议")

    return recommendations


# ============================================================
# 生成内容策略文件
# ============================================================
def write_content_strategy(recommendations, platform_stats):
    """写入内容策略文件，供content_loop_v3.py读取"""
    strategy = {
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "version": "1.0",
        "recommendations": recommendations,
        "platform_priorities": [],
        "content_adjustments": {},
    }

    # 平台优先级排序
    ranked = sorted(platform_stats.items(), key=lambda x: x[1]["total_likes"] + x[1]["total_interactions"], reverse=True)
    for rank, (platform, stats) in enumerate(ranked, 1):
        strategy["platform_priorities"].append({
            "rank": rank,
            "platform": platform,
            "priority": "high" if rank <= 2 else "medium" if rank <= 4 else "low",
            "reason": f"互动总分{stats['total_likes'] + stats['total_interactions']}",
        })

    # 内容调整
    strategy["content_adjustments"] = {
        "increase_topics": [],
        "decrease_topics": [],
        "new_topics_to_try": ["股票市场分析", "宏观经济走向", "交易复盘分享"],
        "tone": "保持数据驱动的客观风格",
        "format": "推特保持5条串，知乎增加深度长文（800字+）",
    }

    strategy_path = os.path.join(SC, "content", "content_strategy.json")
    write_json(strategy_path, strategy)
    print(f"[内容分析] 策略文件已写入 → {strategy_path}")
    return strategy_path


# ============================================================
# 主分析流程
# ============================================================
def run_analysis():
    print("[内容分析] 开始周度效果分析...")

    # 1. 收集数据
    daily_metrics, week_start, week_end = collect_week_data()
    print(f"  数据范围: {week_start} ~ {week_end} ({len(daily_metrics)}天)")

    if not daily_metrics:
        print("[内容分析] 本周无反馈数据，跳过")
        return

    # 2. 平台效果
    platform_stats = analyze_platforms(daily_metrics)

    # 3. 内容主题
    content_topics = analyze_content_topics(daily_metrics)

    # 4. 发布时间
    time_stats = analyze_publish_times(daily_metrics)

    # 5. 生成建议
    recommendations = generate_recommendations(platform_stats, content_topics, time_stats)

    # 6. LLM深度分析
    llm_analysis = None
    summary_text = json.dumps({
        "platform_stats": {k: {kk: vv for kk, vv in v.items() if kk != "dates"}
                           for k, v in platform_stats.items()},
        "recommendations": recommendations,
    }, ensure_ascii=False, indent=2)

    llm_prompt = f"""你是内容运营分析师。以下是本周各平台内容互动数据：
{summary_text}

请用3-5句话分析：
1. 哪个平台表现最好，为什么
2. 下周应该调整什么内容方向
3. 有什么新的内容机会值得尝试
简洁直接，给出可执行建议。"""

    llm_analysis = call_llm(llm_prompt)

    # 7. 写入策略文件
    strategy_path = write_content_strategy(recommendations, platform_stats)

    # 8. 生成周报
    report = {
        "week_start": week_start.strftime("%Y-%m-%d"),
        "week_end": week_end.strftime("%Y-%m-%d"),
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "data_days": len(daily_metrics),
        "platform_stats": platform_stats,
        "content_topics": content_topics,
        "time_stats": time_stats,
        "recommendations": recommendations,
        "llm_analysis": llm_analysis,
        "strategy_file": strategy_path,
    }

    report_path = os.path.join(ANALYSIS_DIR, "performance_report.json")
    write_json(report_path, report)
    print(f"[内容分析] 周报已生成 → {report_path}")

    # 事件总线通知
    log_event("analysis_complete", f"周度分析完成: {len(daily_metrics)}天数据, {len(recommendations)}条建议")

    # 打印摘要
    print("\n=== 周度分析摘要 ===")
    print(f"数据天数: {len(daily_metrics)}")
    print(f"平台覆盖: {len(platform_stats)}")
    for platform, stats in sorted(platform_stats.items(), key=lambda x: x[1]["total_likes"], reverse=True):
        print(f"  {platform}: 自动{stats['auto_collected']} | 手动{stats['manual_entered']} | 未发{stats['not_published']} | 点赞{stats['total_likes']}")
    print(f"\n建议:")
    for r in recommendations:
        print(f"  • {r}")
    if llm_analysis:
        print(f"\nLLM深度分析:\n{llm_analysis}")


if __name__ == "__main__":
    run_analysis()
