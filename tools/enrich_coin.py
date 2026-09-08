#!/usr/bin/env python3
"""
选币库多Agent打标工具 — enrich_coin.py

用法:
  # A7写入舆情标签
  python3 tools/enrich_coin.py --source A7 --symbol PLAYUSDT \\
    --tag '{"sentiment":"positive","narrative":"Gaming板块轮动","alert_level":"info"}'

  # A8写入资金流标签
  python3 tools/enrich_coin.py --source A8 --symbol STRAXUSDT \\
    --tag '{"smart_money_inflow_1h":5800000,"large_transactions":12}'

  # A1写入基础数据标签
  python3 tools/enrich_coin.py --source A1 --symbol PLAYUSDT \\
    --tag '{"volume_24h_usdt":13600000,"vol_change_24h_pct":320}'

  # 查看某个币的全部标签
  python3 tools/enrich_coin.py --view PLAYUSDT

  # 查看所有有标签的币（按综合信号强度排序）
  python3 tools/enrich_coin.py --list

数据存储: data/coin_enrichment/{symbol}.json
每个币一个文件，各Agent往自己的key下写数据，不互相覆盖。
"""

import json
import os
import sys
import argparse
from datetime import datetime, timezone, timedelta

BJT = timezone(timedelta(hours=8))
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data", "coin_enrichment")


def ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def coin_path(symbol: str) -> str:
    return os.path.join(DATA_DIR, f"{symbol.upper()}.json")


def load_coin(symbol: str) -> dict:
    path = coin_path(symbol)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {"symbol": symbol.upper(), "tags": {}, "updated_at": None}


def save_coin(data: dict):
    path = coin_path(data["symbol"])
    data["updated_at"] = datetime.now(BJT).strftime("%Y-%m-%dT%H:%M:%S+08:00")
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ {data['symbol']} — tags 已更新 (by {list(data['tags'].keys())})")


def set_tag(symbol: str, source: str, tag_data: dict):
    coin = load_coin(symbol)
    if "tags" not in coin:
        coin["tags"] = {}
    coin["tags"][source] = {
        "last_updated": datetime.now(BJT).strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        **tag_data
    }
    save_coin(coin)


def view_coin(symbol: str):
    coin = load_coin(symbol)
    if not coin.get("tags"):
        print(f"❌ {symbol} 没有标签数据")
        return
    print(f"\n📊 {symbol} 多Agent标签:")
    print("=" * 50)
    for source, data in coin.get("tags", {}).items():
        print(f"\n  [{source}] 更新: {data.get('last_updated', 'N/A')}")
        for k, v in data.items():
            if k != "last_updated":
                print(f"    {k}: {v}")
    print()


def list_coins():
    ensure_dir()
    coins = []
    for fname in os.listdir(DATA_DIR):
        if fname.endswith(".json"):
            with open(os.path.join(DATA_DIR, fname)) as f:
                coin = json.load(f)
            tags = coin.get("tags", {})
            # 计算综合信号强度: 有Agent推的越多越强
            strength = len(tags)
            coin["_strength"] = strength
            coins.append(coin)

    if not coins:
        print("❌ 没有打标的币")
        return

    coins.sort(key=lambda c: c["_strength"], reverse=True)
    print(f"\n📋 已打标币种 ({len(coins)}个):")
    print(f"{'币种':<15} {'Agent':<20} {'更新时间':<25}")
    print("-" * 60)
    for c in coins:
        agents = "/".join(c.get("tags", {}).keys())
        updated = c.get("updated_at", "N/A")[:19]
        print(f"{c['symbol']:<15} {agents:<20} {updated:<25}")


def main():
    parser = argparse.ArgumentParser(description="选币库多Agent打标工具")
    parser.add_argument("--source", choices=["A1", "A7", "A8", "A3", "A4", "ZH"],
                        help="打标来源Agent")
    parser.add_argument("--symbol", help="币种符号（如 PLAYUSDT）")
    parser.add_argument("--tag", help="标签JSON数据")
    parser.add_argument("--view", help="查看某个币的标签")
    parser.add_argument("--list", action="store_true", help="列出所有打标币")
    args = parser.parse_args()

    ensure_dir()

    if args.list:
        list_coins()
    elif args.view:
        view_coin(args.view)
    elif args.source and args.symbol and args.tag:
        try:
            tag_data = json.loads(args.tag)
        except json.JSONDecodeError as e:
            print(f"❌ tag JSON格式错误: {e}")
            sys.exit(1)
        set_tag(args.symbol, args.source, tag_data)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
