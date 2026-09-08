#!/usr/bin/env python3
"""
选币库标签同步脚本 — sync_enrich_to_coinpool.py

从 data/coin_enrichment/ 读取所有Agent标签（A7/A8/A3/ZH），
同步写入 coin_pool.json 中对应币种的 tags 字段。

使A3/A4在读取coin_pool时能直接看到所有Agent的标签数据。

用法:
  python3 tools/sync_enrich_to_coinpool.py

建议cron: 每30分钟执行一次（A3/A4读coin_pool之前）
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

BJT = timezone(timedelta(hours=8))
BASE_DIR = Path(__file__).resolve().parent.parent
ENRICH_DIR = BASE_DIR / "data" / "coin_enrichment"
COIN_POOL_PATH = BASE_DIR / "data" / "coin_pool.json"


def load_enrich_tags() -> dict:
    """读取所有enrich标签，返回 {symbol: {agent: data}}"""
    if not ENRICH_DIR.exists():
        print(f"⚠️  enrich目录不存在: {ENRICH_DIR}")
        return {}

    all_tags = {}
    for fpath in sorted(ENRICH_DIR.glob("*.json")):
        symbol_filename = fpath.stem.upper()
        try:
            with open(fpath) as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️  读取 {fpath.name} 失败: {e}")
            continue

        tags = data.get("tags", {})
        if not tags:
            continue

        # 统一key: 去掉USDT后缀
        symbol = symbol_filename.replace("USDT", "")
        all_tags[symbol] = {
            agent: info for agent, info in tags.items()
        }

    return all_tags


def sync_to_coinpool(enrich_tags: dict) -> dict:
    """将enrich标签同步写入coin_pool.json"""
    if not COIN_POOL_PATH.exists():
        print(f"❌ coin_pool.json 不存在: {COIN_POOL_PATH}")
        return {}

    with open(COIN_POOL_PATH) as f:
        pool = json.load(f)

    stats = {"total_pool": len(pool["pool"]), "synced": 0, "not_found": []}

    for coin in pool["pool"]:
        symbol = coin["symbol"]
        if symbol in enrich_tags:
            # 写入tags字段，保留原有的非Agent标签
            if "tags" not in coin or not isinstance(coin.get("tags"), dict):
                coin["tags"] = {}
            # 只写入A7/A8/A3/ZH的enrich标签，不覆盖其他字段
            coin["tags"]["_enrich"] = enrich_tags[symbol]
            stats["synced"] += 1
        else:
            # 没有enrich标签的币，清除旧的_enrich标签（如果有）
            if coin.get("tags", {}).get("_enrich"):
                del coin["tags"]["_enrich"]

    # 写回
    pool["_enrich_last_sync"] = datetime.now(BJT).strftime("%Y-%m-%d %H:%M:%S")
    with open(COIN_POOL_PATH, "w") as f:
        json.dump(pool, f, indent=2, ensure_ascii=False)

    return stats


def main():
    enrich_tags = load_enrich_tags()
    if not enrich_tags:
        print("⚠️  没有enrich标签数据可同步")
        # 仍然尝试写同步时间戳
        if COIN_POOL_PATH.exists():
            with open(COIN_POOL_PATH) as f:
                pool = json.load(f)
            pool["_enrich_last_sync"] = datetime.now(BJT).strftime("%Y-%m-%d %H:%M:%S")
            with open(COIN_POOL_PATH, "w") as f:
                json.dump(pool, f, indent=2, ensure_ascii=False)
        return 0

    print(f"📥 从 coin_enrichment/ 读取 {len(enrich_tags)} 个币的标签")
    print(f"   Agent分布: ", end="")
    agent_counts = {}
    for symbol, tags in enrich_tags.items():
        for agent in tags:
            agent_counts[agent] = agent_counts.get(agent, 0) + 1
    print(", ".join(f"{k}={v}" for k, v in sorted(agent_counts.items())))

    stats = sync_to_coinpool(enrich_tags)
    print(f"✅ 同步完成: {stats['synced']}/{stats['total_pool']} 个币同步了enrich标签")

    if stats.get("not_found"):
        print(f"⚠️  未在coin_pool中找到的币: {', '.join(stats['not_found'][:10])}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
