#!/usr/bin/env python3
"""
Codex 数据管道编排器 v1.0
==========================
统一管理六大系统的数据管道，确保时序依赖正确、状态可追踪。

管道阶段（按顺序）:
  Phase 1: 数据采集 (collect)
  Phase 2: 数据分析 (analyze)
  Phase 3: 风控检查 (risk_check)
  Phase 4: 策略执行 (execute)
  Phase 5: 监控告警 (monitor)

用法:
  python3 pipeline_orchestrator.py --phase all       # 全管道
  python3 pipeline_orchestrator.py --phase collect   # 只采集
  python3 pipeline_orchestrator.py --status          # 状态看板
  python3 pipeline_orchestrator.py --health          # 健康检查
"""

import json
import os
import sys
import time
import subprocess
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path

SHARED = Path("/home/ubuntu/shared_context")
LOG_DIR = SHARED / "logs"
MONITOR_DIR = SHARED / "monitor"
STATUS_FILE = MONITOR_DIR / "pipeline_status.json"

PYTHON = "/usr/bin/python3"
ZQ_PY = "/home/ubuntu/zq_env/bin/python3"
ZQ_ROOT = Path("/home/ubuntu/zq_web4_trading_system")

LOG_DIR.mkdir(parents=True, exist_ok=True)
MONITOR_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "pipeline.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("pipeline")

PIPELINE = {
    "collect": {
        "name": "数据采集",
        "tasks": [
            {"name": "sync_trading_data", "cmd": f"{PYTHON} {SHARED}/sync_trading_data.py", "log": "sync.log", "timeout": 120, "critical": True, "retries": 3},
            {"name": "fx_rates", "cmd": f"{PYTHON} {SHARED}/fx_rates_collector.py", "log": "fx_rates.log", "timeout": 60, "critical": True, "retries": 3},
            {"name": "futures_prices", "cmd": f"{PYTHON} {SHARED}/futures_prices.py", "log": "futures.log", "timeout": 60, "critical": False},
            {"name": "stock_data", "cmd": f"{PYTHON} {SHARED}/stock_data_collector.py", "log": "stocks.log", "timeout": 120, "critical": False},
        ],
    },
    "analyze": {
        "name": "数据分析",
        "tasks": [
            {"name": "correlation_gate", "cmd": f"{PYTHON} {SHARED}/correlation_gate.py", "log": "correlation_gate.log", "timeout": 60, "critical": False},
            {"name": "economic_risk", "cmd": f"{PYTHON} {SHARED}/economy/economic_risk_state.py", "log": "economic_risk.log", "timeout": 60, "critical": False},
            {"name": "dashboard", "cmd": f"{PYTHON} {SHARED}/economy/dashboard.py", "log": "dashboard.log", "timeout": 60, "critical": False},
        ],
    },
    "risk_check": {
        "name": "风控检查",
        "tasks": [
            {"name": "risk_manager", "cmd": f"{PYTHON} {SHARED}/risk_manager.py", "log": "risk.log", "timeout": 60, "critical": True, "retries": 3},
        ],
    },
    "execute": {
        "name": "策略执行",
        "tasks": [
            {"name": "trend_follow", "cmd": f"{PYTHON} {SHARED}/trend_follow_bot.py", "log": "trend.log", "timeout": 120, "critical": False},
            {"name": "futures_bot", "cmd": f"FUTURES_MODE=live {PYTHON} {SHARED}/futures_bot.py", "log": "futures.log", "timeout": 120, "critical": False},
            {"name": "breakout", "cmd": f"{PYTHON} {SHARED}/breakout_bot.py", "log": "breakout.log", "timeout": 60, "critical": False},
            {"name": "fx_executor", "cmd": f"{PYTHON} {SHARED}/fx_executor.py", "log": "fx_executor.log", "timeout": 60, "critical": False},
            {"name": "mean_rev", "cmd": f"{ZQ_PY} {ZQ_ROOT}/tools/mean_rev_bot.py", "cwd": str(ZQ_ROOT), "log": "mean_rev.log", "timeout": 60, "critical": False},
            {"name": "radar", "cmd": f"{ZQ_PY} {ZQ_ROOT}/tools/radar_v2.py", "cwd": str(ZQ_ROOT), "log": "radar.log", "timeout": 60, "critical": False},
        ],
    },
    "monitor": {
        "name": "监控告警",
        "tasks": [
            {"name": "system_monitor", "cmd": f"{PYTHON} {SHARED}/system_monitor.py", "log": "monitor.log", "timeout": 30, "critical": False},
            {"name": "system_dashboard", "cmd": f"{PYTHON} {SHARED}/system_dashboard.py", "log": "dashboard.log", "timeout": 30, "critical": False},
            {"name": "watchdog", "cmd": f"{PYTHON} {SHARED}/openclaw/watchdog.py", "log": "watchdog.log", "timeout": 30, "critical": False},
        ],
    },
}


def load_status():
    if STATUS_FILE.exists():
        try:
            with open(STATUS_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {
        "version": "1.0.0",
        "last_run": None,
        "phases": {},
        "tasks": {},
        "history": [],
    }


def save_status(s):
    s["last_run"] = datetime.now().isoformat()
    today = datetime.now().strftime("%Y-%m-%d")
    s["history"] = [h for h in s.get("history", []) if h.get("date") != today][-30:]
    with open(STATUS_FILE, "w") as f:
        json.dump(s, f, indent=2, ensure_ascii=False)


def _send_pipeline_alert(title, message, task_name, level="WARNING"):
    """通过 alert_notifier 发送管道告警"""
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


def run_task(task, phase_key):
    name = task["name"]
    cmd = task["cmd"]
    cwd = task.get("cwd", str(SHARED))
    timeout = task.get("timeout", 300)
    critical = task.get("critical", False)
    retries = task.get("retries", 1)

    t0 = time.time()
    logger.info(f"  ▶ {name}")

    last_error = None
    ok = False
    exit_code = 0

    for attempt in range(1, retries + 1):
        if attempt > 1:
            delay = 5 * (2 ** (attempt - 2))
            logger.info(f"    ⏳ 第{attempt}/{retries}次, {delay}s后重试...")
            time.sleep(delay)

        try:
            result = subprocess.run(
                cmd, shell=True, cwd=cwd, timeout=timeout,
                capture_output=True, text=True,
            )
            elapsed = time.time() - t0
            ok = result.returncode == 0
            exit_code = result.returncode

            if ok:
                logger.info(f"    ✅ {name} (第{attempt}次, {elapsed:.1f}s)")
                break
            else:
                last_error = f"exit={result.returncode}"
                logger.warning(f"    ❌ {name} 第{attempt}次失败: exit={result.returncode} ({elapsed:.1f}s)")
                if result.stderr:
                    for line in result.stderr.strip().split("\n")[-2:]:
                        logger.warning(f"       {line}")

        except subprocess.TimeoutExpired:
            last_error = "timeout"
            logger.warning(f"    ⏰ {name} 第{attempt}次超时 ({timeout}s)")
        except Exception as e:
            last_error = str(e)
            logger.error(f"    💥 {name} 第{attempt}次异常: {e}")

    elapsed = time.time() - t0

    if not ok and critical:
        _send_pipeline_alert(
            f"管道关键任务失败: {name}",
            f"阶段: {phase_key}\n错误: {last_error}\n重试: {retries}次\n耗时: {elapsed:.1f}s",
            task_name=name,
            level="CRITICAL",
        )

    return {
        "name": name, "phase": phase_key, "success": ok,
        "exit_code": exit_code, "duration": round(elapsed, 2),
        "last_run": datetime.now().isoformat(), "critical": critical,
        "retries": retries, "last_error": last_error,
    }


def run_phase(phase_key, status):
    phase = PIPELINE[phase_key]
    logger.info(f"\n{'='*50}")
    logger.info(f"📦 {phase['name']} ({phase_key})")
    logger.info(f"{'='*50}")

    t0 = time.time()
    results = []
    all_ok = True

    for task in phase["tasks"]:
        r = run_task(task, phase_key)
        results.append(r)
        status["tasks"][task["name"]] = r

        if not r["success"] and task.get("critical"):
            logger.error(f"  🚨 关键任务 {task['name']} 失败，终止阶段")
            all_ok = False
            break
        if not r["success"]:
            all_ok = False

    elapsed = time.time() - t0
    success_n = sum(1 for r in results if r["success"])
    status["phases"][phase_key] = {
        "name": phase["name"], "success": all_ok,
        "task_count": len(results), "success_count": success_n,
        "duration": round(elapsed, 2),
        "last_run": datetime.now().isoformat(),
    }

    status_msg = "全部成功" if all_ok else "部分失败"
    logger.info(f"  → {phase['name']} {status_msg} ({success_n}/{len(results)}, {elapsed:.1f}s)")
    return all_ok


def run_pipeline(phases, status):
    t0 = time.time()
    overall = True

    for pk in phases:
        ok = run_phase(pk, status)
        if not ok:
            for tn, ti in status.get("tasks", {}).items():
                if ti.get("critical") and not ti.get("success"):
                    logger.error(f"🚨 关键任务 {tn} 失败，管道中断")
                    overall = False
                    break
            if not overall:
                break

    elapsed = time.time() - t0
    total = len(status.get("tasks", {}))
    succ = sum(1 for t in status.get("tasks", {}).values() if t.get("success"))

    today = datetime.now().strftime("%Y-%m-%d")
    status["history"].append({
        "date": today,
        "timestamp": datetime.now().isoformat(),
        "success": overall,
        "total": total, "passed": succ,
        "duration": round(elapsed, 2),
    })

    logger.info(f"\n{'='*50}")
    if overall:
        logger.info(f"🎉 管道完成 ({elapsed:.1f}s, {succ}/{total})")
    else:
        logger.warning(f"⚠️ 管道完成但有失败 ({elapsed:.1f}s, {succ}/{total})")
    logger.info(f"{'='*50}\n")

    save_status(status)
    return overall


def show_status():
    status = load_status()
    print("\n" + "=" * 60)
    print("  📊 Codex 数据管道状态看板")
    print("=" * 60)

    if status.get("last_run"):
        try:
            lr = datetime.fromisoformat(status["last_run"])
            print(f"\n  上次运行: {lr.strftime('%Y-%m-%d %H:%M:%S')}")
        except:
            print(f"\n  上次运行: {status['last_run']}")
    else:
        print("\n  尚未运行")

    # 24h统计
    now = datetime.now()
    recent = [h for h in status.get("history", [])
              if h.get("timestamp") and
              (now - datetime.fromisoformat(h["timestamp"])).total_seconds() < 86400]
    if recent:
        runs = len(recent)
        succ_runs = sum(1 for h in recent if h.get("success"))
        print(f"  24h运行: {succ_runs}/{runs} 次成功")

    print("\n  --- 各阶段状态 ---")
    for pk, pv in PIPELINE.items():
        ps = status.get("phases", {}).get(pk, {})
        if ps:
            icon = "✅" if ps.get("success") else "❌"
            print(f"  {icon} {pv['name']:10s}  {ps.get('success_count',0)}/{ps.get('task_count',0)} 任务  {ps.get('duration',0):.1f}s")
        else:
            print(f"  ⏳ {pv['name']:10s}  未运行")

    print("\n  --- 关键任务 ---")
    for tn in ["sync_trading_data", "fx_rates", "risk_manager", "system_monitor"]:
        ts = status.get("tasks", {}).get(tn, {})
        if ts:
            icon = "✅" if ts.get("success") else "❌"
            print(f"  {icon} {tn:22s}  {ts.get('duration',0):.1f}s")
        else:
            print(f"  ⏳ {tn:22s}  未运行")

    print("\n  --- 近7天历史 ---")
    for h in status.get("history", [])[-7:]:
        date = h.get("date", "-")
        ok = "✅" if h.get("success") else "❌"
        total = h.get("total", 0)
        passed = h.get("passed", 0)
        dur = h.get("duration", 0)
        print(f"  {ok} {date}  {passed}/{total}  {dur:.1f}s")

    print("\n" + "=" * 60 + "\n")


def health_check():
    status = load_status()
    issues = []

    for pk, pv in PIPELINE.items():
        ps = status.get("phases", {}).get(pk, {})
        if not ps:
            issues.append(f"阶段 {pv['name']} 从未运行")
            continue
        lr = ps.get("last_run", "")
        if lr:
            try:
                dt = datetime.fromisoformat(lr)
                age = (datetime.now() - dt).total_seconds()
                if age > 600:
                    issues.append(f"阶段 {pv['name']} 超过 {int(age/60)} 分钟未运行")
            except:
                pass
        if not ps.get("success"):
            for tn, ts in status.get("tasks", {}).items():
                if ts.get("phase") == pk and not ts.get("success") and ts.get("critical"):
                    issues.append(f"关键任务 {tn} 失败")

    if issues:
        print(f"⚠️  发现 {len(issues)} 个问题:")
        for i in issues:
            print(f"  • {i}")
        return False
    else:
        print("✅ 管道健康检查通过，所有阶段正常运行")
        return True


def main():
    parser = argparse.ArgumentParser(description="Codex 数据管道编排器")
    parser.add_argument("--phase", default="all",
                        help="阶段: all, collect, analyze, risk_check, execute, monitor")
    parser.add_argument("--status", action="store_true", help="查看状态")
    parser.add_argument("--health", action="store_true", help="健康检查")
    args = parser.parse_args()

    if args.status:
        show_status()
        return
    if args.health:
        sys.exit(0 if health_check() else 1)

    if args.phase == "all":
        phases = list(PIPELINE.keys())
    elif args.phase in PIPELINE:
        phases = [args.phase]
    else:
        logger.error(f"未知阶段: {args.phase}")
        logger.info(f"可用: {', '.join(PIPELINE.keys())}")
        sys.exit(1)

    status = load_status()
    ok = run_pipeline(phases, status)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
