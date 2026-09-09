#!/usr/bin/env python3
"""
Codex 数据清理脚本
==================
定期清理历史数据文件，防止磁盘堆积。

清理规则:
  - data_sources/*.json      保留7天
  - logs/*.log               保留30天
  - shared_context 临时文件   保留3天

用法:
  python3 data_cleanup.py           # 执行清理
  python3 data_cleanup.py --dry     # 预览不执行
  python3 data_cleanup.py --verbose # 详细输出
"""

import os
import sys
import time
import argparse
import logging
from pathlib import Path
from datetime import datetime

LOG_DIR = Path("/home/ubuntu/shared_context/logs")
DATA_SOURCES = Path("/home/ubuntu/zq_web4_trading_system/data_sources")
ZQ_LOGS = Path("/home/ubuntu/zq_web4_trading_system/logs")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "data_cleanup.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("cleanup")

RETENTION = {
    "data_sources_json": 7,
    "logs": 30,
    "temp_files": 3,
}


def get_dir_size(path):
    total = 0
    if path.exists():
        for f in path.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
    return total


def clean_json_files(dry_run=False):
    """清理 data_sources 下的旧 JSON 文件"""
    if not DATA_SOURCES.exists():
        return 0, 0

    cutoff = time.time() - RETENTION["data_sources_json"] * 86400
    count = 0
    size = 0

    for f in DATA_SOURCES.glob("*.json"):
        if f.stat().st_mtime < cutoff:
            size += f.stat().st_size
            if not dry_run:
                f.unlink()
            count += 1

    return count, size


def clean_old_logs(dry_run=False):
    """清理旧日志文件"""
    count = 0
    size = 0
    cutoff = time.time() - RETENTION["logs"] * 86400

    for log_dir in [LOG_DIR, ZQ_LOGS]:
        if not log_dir.exists():
            continue
        for f in log_dir.glob("*.log.*"):
            if f.stat().st_mtime < cutoff:
                size += f.stat().st_size
                if not dry_run:
                    f.unlink()
                count += 1

    return count, size


def clean_temp_files(dry_run=False):
    """清理 shared_context 下的临时文件"""
    temp_patterns = ["*.tmp", "*.temp", "*.bak"]
    count = 0
    size = 0
    cutoff = time.time() - RETENTION["temp_files"] * 86400

    sc = Path("/home/ubuntu/shared_context")
    for pattern in temp_patterns:
        for f in sc.rglob(pattern):
            if f.is_file() and f.stat().st_mtime < cutoff:
                size += f.stat().st_size
                if not dry_run:
                    f.unlink()
                count += 1

    return count, size


def main():
    parser = argparse.ArgumentParser(description="Codex 数据清理")
    parser.add_argument("--dry", action="store_true", help="预览模式，不实际删除")
    parser.add_argument("--verbose", action="store_true", help="详细输出")
    args = parser.parse_args()

    mode = "预览" if args.dry else "执行"
    logger.info(f"=== 数据清理 ({mode}模式) ===")
    logger.info(f"保留策略: JSON {RETENTION['data_sources_json']}天, 日志 {RETENTION['logs']}天, 临时 {RETENTION['temp_files']}天")

    before_size = get_dir_size(DATA_SOURCES) + get_dir_size(LOG_DIR) + get_dir_size(ZQ_LOGS)
    before_mb = before_size / 1024 / 1024
    logger.info(f"清理前总占用: {before_mb:.1f} MB")

    total_count = 0
    total_size = 0

    # 1. 清理 JSON
    logger.info("扫描 data_sources/*.json ...")
    c, s = clean_json_files(args.dry)
    total_count += c
    total_size += s
    logger.info(f"  JSON 文件: {c} 个, {s/1024/1024:.1f} MB")

    # 2. 清理旧日志
    logger.info("扫描旧日志 ...")
    c, s = clean_old_logs(args.dry)
    total_count += c
    total_size += s
    logger.info(f"  日志文件: {c} 个, {s/1024/1024:.1f} MB")

    # 3. 清理临时文件
    logger.info("扫描临时文件 ...")
    c, s = clean_temp_files(args.dry)
    total_count += c
    total_size += s
    logger.info(f"  临时文件: {c} 个, {s/1024/1024:.1f} MB")

    after_size = before_size - total_size
    after_mb = after_size / 1024 / 1024
    freed_mb = total_size / 1024 / 1024

    logger.info(f"\n{'='*40}")
    logger.info(f"清理完成 ({mode}模式)")
    logger.info(f"  删除文件: {total_count} 个")
    logger.info(f"  释放空间: {freed_mb:.1f} MB")
    logger.info(f"  清理后占用: {after_mb:.1f} MB")
    logger.info(f"{'='*40}\n")


if __name__ == "__main__":
    main()
