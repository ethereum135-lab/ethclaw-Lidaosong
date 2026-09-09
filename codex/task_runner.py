#!/usr/bin/env python3
"""
Codex 任务重试包装器
=====================
包装 Cron 任务，提供自动重试和失败告警。

特性:
  - 自动重试（默认3次，间隔递增）
  - 失败后通过 Telegram 告警
  - 超时保护
  - 执行日志记录
  - 状态写入 pipeline_status.json

用法:
  # 命令行模式（包装任意命令）
  python3 task_runner.py --name sync_trading_data --cmd "python3 sync_trading_data.py" --retries 3 --timeout 120

  # Cron 中使用
  */5 * * * * /usr/bin/python3 /home/ubuntu/shared_context/codex/task_runner.py \
    --name sync_trading_data \
    --cmd "/usr/bin/python3 /home/ubuntu/shared_context/sync_trading_data.py" \
    --log /home/ubuntu/shared_context/logs/sync.log \
    --retries 3 --timeout 120 --critical
"""

import json
import os
import sys
import time
import subprocess
import argparse
import logging
from datetime import datetime
from pathlib import Path

SHARED = Path("/home/ubuntu/shared_context")
LOG_DIR = SHARED / "logs"
MONITOR_DIR = SHARED / "monitor"
STATUS_FILE = MONITOR_DIR / "pipeline_status.json"

LOG_DIR.mkdir(parents=True, exist_ok=True)
MONITOR_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("runner")


def load_status():
    if STATUS_FILE.exists():
        try:
            with open(STATUS_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"tasks": {}, "retry_history": []}


def save_status(s):
    with open(STATUS_FILE, "w") as f:
        json.dump(s, f, indent=2, ensure_ascii=False)


def send_alert(title, message, task_name, level="WARNING"):
    """通过 alert_notifier 发送告警"""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "alert_notifier",
            str(Path(__file__).parent / "alert_notifier.py")
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        notifier = mod.AlertNotifier()
        notifier.send(title, message, level=level, task_name=task_name)
    except Exception as e:
        logger.error(f"告警发送失败: {e}")


def run_with_retry(name, cmd, cwd=None, retries=3, timeout=300,
                   critical=False, log_file=None, retry_delay=10):
    """
    执行命令，失败自动重试

    Args:
        name: 任务名
        cmd: 执行命令
        cwd: 工作目录
        retries: 最大重试次数
        timeout: 单次执行超时（秒）
        critical: 是否关键任务
        log_file: 日志文件路径
        retry_delay: 重试间隔基数（秒，指数递增）

    Returns:
        dict: 执行结果
    """
    result = {
        "name": name,
        "cmd": cmd,
        "success": False,
        "attempts": 0,
        "duration": 0,
        "last_run": datetime.now().isoformat(),
        "critical": critical,
    }

    t0 = time.time()
    last_error = None

    for attempt in range(1, retries + 1):
        result["attempts"] = attempt
        logger.info(f"▶ [{name}] 第 {attempt}/{retries} 次执行")

        attempt_t0 = time.time()
        try:
            proc = subprocess.run(
                cmd, shell=True, cwd=cwd, timeout=timeout,
                capture_output=True, text=True,
            )
            attempt_elapsed = time.time() - attempt_t0

            if proc.returncode == 0:
                result["success"] = True
                result["exit_code"] = 0
                result["duration"] = round(time.time() - t0, 2)
                logger.info(f"✅ [{name}] 成功 (第{attempt}次, {attempt_elapsed:.1f}s)")

                # 写入日志
                if log_file:
                    with open(log_file, "a") as f:
                        f.write(f"[{datetime.now().isoformat()}] [{name}] ✅ 成功 (第{attempt}次, {attempt_elapsed:.1f}s)\n")

                # 关键任务恢复告警
                if attempt > 1:
                    send_alert(
                        f"任务恢复: {name}",
                        f"第 {attempt} 次重试成功\n耗时: {attempt_elapsed:.1f}s",
                        task_name=name,
                        level="SUCCESS",
                    )
                break

            else:
                last_error = f"exit_code={proc.returncode}"
                stderr_tail = ""
                if proc.stderr:
                    stderr_lines = proc.stderr.strip().split("\n")[-3:]
                    stderr_tail = "\n".join(stderr_lines)

                logger.warning(f"❌ [{name}] 第{attempt}次失败: exit={proc.returncode} ({attempt_elapsed:.1f}s)")
                if stderr_tail:
                    logger.warning(f"   stderr: {stderr_tail}")

                if log_file:
                    with open(log_file, "a") as f:
                        f.write(f"[{datetime.now().isoformat()}] [{name}] ❌ 第{attempt}次失败 exit={proc.returncode} ({attempt_elapsed:.1f}s)\n")
                        if stderr_tail:
                            f.write(f"  stderr: {stderr_tail}\n")

        except subprocess.TimeoutExpired:
            attempt_elapsed = time.time() - attempt_t0
            last_error = f"timeout ({timeout}s)"
            logger.warning(f"⏰ [{name}] 第{attempt}次超时 ({attempt_elapsed:.1f}s)")

            if log_file:
                with open(log_file, "a") as f:
                    f.write(f"[{datetime.now().isoformat()}] [{name}] ⏰ 第{attempt}次超时 ({attempt_elapsed:.1f}s)\n")

        except Exception as e:
            attempt_elapsed = time.time() - attempt_t0
            last_error = str(e)
            logger.error(f"💥 [{name}] 第{attempt}次异常: {e}")

            if log_file:
                with open(log_file, "a") as f:
                    f.write(f"[{datetime.now().isoformat()}] [{name}] 💥 第{attempt}次异常: {e}\n")

        # 判断是否需要重试
        if attempt < retries:
            delay = retry_delay * (2 ** (attempt - 1))  # 指数退避: 10, 20, 40...
            logger.info(f"⏳ [{name}] {delay}s 后重试...")
            time.sleep(delay)

    result["duration"] = round(time.time() - t0, 2)
    result["last_error"] = last_error

    if not result["success"]:
        # 最终失败，发送告警
        level = "CRITICAL" if critical else "WARNING"
        message = (
            f"任务连续 {retries} 次重试均失败\n"
            f"错误: {last_error}\n"
            f"总耗时: {result['duration']}s"
        )
        if critical:
            message += "\n\n🚨 这是关键任务，请立即检查！"

        send_alert(
            f"任务失败: {name}",
            message,
            task_name=name,
            level=level,
        )

        logger.error(f"🚨 [{name}] 最终失败 ({retries}次重试, {result['duration']}s)")

    return result


def main():
    parser = argparse.ArgumentParser(description="Codex 任务重试包装器")
    parser.add_argument("--name", required=True, help="任务名")
    parser.add_argument("--cmd", required=True, help="执行命令")
    parser.add_argument("--cwd", default=None, help="工作目录")
    parser.add_argument("--retries", type=int, default=3, help="最大重试次数")
    parser.add_argument("--timeout", type=int, default=300, help="单次超时(秒)")
    parser.add_argument("--critical", action="store_true", help="关键任务")
    parser.add_argument("--log", default=None, help="日志文件路径")
    parser.add_argument("--retry-delay", type=int, default=10, help="重试间隔基数(秒)")
    args = parser.parse_args()

    result = run_with_retry(
        name=args.name,
        cmd=args.cmd,
        cwd=args.cwd,
        retries=args.retries,
        timeout=args.timeout,
        critical=args.critical,
        log_file=args.log,
        retry_delay=args.retry_delay,
    )

    # 更新 pipeline_status
    status = load_status()
    status["tasks"][args.name] = result
    save_status(status)

    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
