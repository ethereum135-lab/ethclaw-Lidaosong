#!/usr/bin/env python3
"""刷新 aws_snapshot.json 中的 F&G 指数 — 给 a3_signal_scanner.sh 每30分钟调用
不影响 snapshot 其他字段（BTC/ETH价格、费率等保持A1原始数据）
"""
import json, os, sys
import urllib.request

SNAPSHOT = os.path.join(os.path.dirname(__file__), '..', 'data', 'aws_snapshot.json')
DATA_FEED = os.path.join(os.path.dirname(__file__), '..', 'profiles', 'a1-data', 'output', 'data_feed.md')

def fetch_fg():
    req = urllib.request.Request(
        "https://api.alternative.me/fng/?limit=1",
        headers={"User-Agent": "Mozilla/5.0"}
    )
    resp = urllib.request.urlopen(req, timeout=10)
    d = json.loads(resp.read())
    value = d["data"][0]["value"]
    classification = d["data"][0]["value_classification"]
    return value, classification

def refresh_data_feed(value, classification):
    """刷新 data_feed.md 中的 F&G 值"""
    if not os.path.exists(DATA_FEED):
        print(f"⚠️ {DATA_FEED} 不存在，跳过")
        return
    import re
    with open(DATA_FEED) as f:
        content = f.read()
    old_fg_line = re.search(r'- fg_value: \d+', content)
    old_label_line = re.search(r'- fg_label: .+', content)
    updated = content
    updated = re.sub(r'- fg_value: \d+', f'- fg_value: {value}', updated)
    updated = re.sub(r'- fg_label: .+', f'- fg_label: {classification}', updated)
    if updated != content:
        with open(DATA_FEED, 'w') as f:
            f.write(updated)
        print(f"✅ data_feed.md F&G已同步: {value}({classification})")
    else:
        # 没变化：值相同或未找到匹配行，都是正常情况
        if re.search(r'- fg_value:', content):
            print(f"ℹ️  data_feed.md F&G无变化: {value}({classification})")
        else:
            print(f"⚠️ data_feed.md 未找到 F&G 行，跳过同步")


def main():
    if not os.path.exists(SNAPSHOT):
        print(f"❌ {SNAPSHOT} 不存在，跳过F&G刷新")
        return 1

    with open(SNAPSHOT) as f:
        data = json.load(f)

    old_fg = data.get('fg_index', 'N/A')
    old_label = data.get('fg_classification', 'N/A')

    try:
        value, classification = fetch_fg()
        data['fg_index'] = value
        data['fg_classification'] = classification
        import datetime as dt
        tz = dt.timezone(dt.timedelta(hours=8))
        data['fg_refreshed_at'] = dt.datetime.now(tz).strftime('%Y-%m-%d %H:%M BJT')

        with open(SNAPSHOT, 'w') as f:
            json.dump(data, f, indent=2)

        delta = int(value) - int(old_fg) if old_fg != 'N/A' else 0
        print(f"✅ F&G 已刷新: {old_fg}({old_label}) → {value}({classification}) 变化={delta:+d}")

        # 同步刷新 data_feed.md
        refresh_data_feed(value, classification)

        return 0
    except Exception as e:
        print(f"⚠️ F&G刷新失败: {e} (使用旧值 {old_fg})")
        return 1

if __name__ == '__main__':
    sys.exit(main())
