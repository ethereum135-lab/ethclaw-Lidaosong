#!/usr/bin/env python3
"""
每日收盘总资记录 — 铁律八「每天必须留下总资记录」的执行器
================================================================
在每天 21:20 BJT 由 launchd 触发（幂等：当天已有记录则更新，不重复追加）。

动作：
  1. 用 tools/fetch_real_balance.py 从 Binance API 实查总权益（物理验证，不用记忆）
  2. 更新 data/total_asset.json（date/time/total/change_pct vs 上次收盘）
  3. 在 data/TRADES.md 写入/更新当天「总资」记录：
       ### YYYY-MM-DD HH:MM BJT | 总权益
       | 总资 | $X |
       | 来源 | total_asset.json <时间> BJT |
  4. 同步 data/total_asset.json 到 AWS 对应目录（保持两端一致）

供 tools/true_daily_pnl.py 使用（只认带日期的「总资」记录）。
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta

PROJECT_ROOT = "/Users/lidaosong/zq_web4_trading_system"
TRADES_PATH = os.path.join(PROJECT_ROOT, "data", "TRADES.md")
TOTAL_ASSET_PATH = os.path.join(PROJECT_ROOT, "data", "total_asset.json")
FETCH_SCRIPT = os.path.join(PROJECT_ROOT, "tools", "fetch_real_balance.py")

BJT = timezone(timedelta(hours=8))


def now_bjt() -> datetime:
    return datetime.now(BJT)


def fetch_equity() -> float:
    """从 Binance API 实查总权益；失败抛异常。"""
    proc = subprocess.run(
        [sys.executable, FETCH_SCRIPT],
        capture_output=True, text=True, timeout=60,
    )
    out = proc.stdout or ""
    m = re.search(r"总权益[:：]?\s*\$?(\d+\.\d+)", out)
    if not m:
        raise RuntimeError(f"fetch_real_balance.py 未返回总权益: {out[-300:]}")
    return float(m.group(1))


def load_prev_close(today: str) -> float | None:
    """昨日收盘基准：data/TRADES.md 中今天之前最后一条 总资/总权益 记录（total_asset.json 是本日记录，不作昨日）。"""
    try:
        with open(TRADES_PATH, "r", encoding="utf-8") as f:
            lines = f.read().split("\n")
        cur_date = None
        prev = None
        for ln in lines:
            m = re.search(r"#{2,3}\s+(\d{4}-\d{2}-\d{2})", ln)
            if m:
                cur_date = m.group(1)
                continue
            if cur_date is None or cur_date >= today:
                continue
            m1 = re.search(r"(?:总权益|总资)\s*(?:[=~:：]+\s*|\$)\s*\*{0,2}\s*~?\$?(\d+\.\d+)", ln)
            m2 = re.search(r"\|\s*(?:总资|净值)\s*\|\s*\$?(\d+\.\d+)", ln)
            val = None
            if m1:
                val = float(m1.group(1))
            elif m2:
                val = float(m2.group(1))
            if val is not None:
                prev = val
        return prev
    except Exception:
        return None


def update_total_asset(total: float, today: str, prev_close: float | None) -> str:
    """更新 data/total_asset.json，返回写盘时间字符串（BJT）。"""
    ts = now_bjt().strftime("%H:%M")
    change_pct = None
    if prev_close:
        change_pct = round((total - prev_close) / prev_close * 100, 2)
    record = {
        "total": round(total, 2),
        "date": today,
        "time": ts,
        "change_pct": change_pct,
        "note": (
            f"UPDATE {today} {ts} BJT (daily_close_record.py): "
            f"真实净值=Binance API实查 ${total:.2f}"
            + (f" vs 前收盘 ${prev_close:.2f} ({change_pct:+.2f}%)" if prev_close else " (无前收盘基准)")
        ),
    }
    with open(TOTAL_ASSET_PATH, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    return ts


def upsert_trades_record(total: float, today: str, ts: str):
    """在 data/TRADES.md 中写入/更新当天总资记录（幂等）。"""
    with open(TRADES_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 找当天「### YYYY-MM-DD ... | 总权益」节头；有则更新总资行，无则追加
    section_idx = None
    for i, ln in enumerate(lines):
        if re.match(rf"#{{2,3}}\s+{today}\b", ln) and "总权益" in ln:
            section_idx = i
            break

    if section_idx is not None:
        # 更新节头时间为本次记录时间
        lines[section_idx] = f"### {today} {ts} BJT | 总权益\n"
        # 更新该节下第一个 | 总资 | $X | 行
        for j in range(section_idx, min(section_idx + 15, len(lines))):
            if re.match(r"\|\s*总资\s*\|\s*\$?\d+\.\d+", lines[j]):
                lines[j] = f"| 总资 | ${total:.2f} |\n"
                break
        # 更新来源行（如有）
        for j in range(section_idx, min(section_idx + 15, len(lines))):
            if re.match(r"\|\s*来源\s*\|", lines[j]):
                lines[j] = f"| 来源 | total_asset.json {today} {ts} BJT |\n"
                break
    else:
        block = (
            f"\n### {today} {ts} BJT | 总权益\n"
            f"| 字段 | 值 |\n"
            f"|:-----|:---|\n"
            f"| 总资 | ${total:.2f} |\n"
            f"| 来源 | total_asset.json {today} {ts} BJT |\n"
        )
        lines.append(block)

    with open(TRADES_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)


def push_to_aws():
    """把 total_asset.json 推到 AWS（保持两端一致）。"""
    aws_key = os.path.expanduser("~/.zq_vault/web4.0.pem")
    cmd = [
        "scp", "-i", aws_key, "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=12",
        TOTAL_ASSET_PATH,
        "ubuntu@15.134.211.154:/home/ubuntu/zq_web4_trading_system/data/total_asset.json",
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except Exception as e:
        print(f"⚠️ AWS推送失败（不影响本地记录）: {e}")


def main() -> int:
    today = now_bjt().strftime("%Y-%m-%d")
    try:
        total = fetch_equity()
    except Exception as e:
        print(f"ERROR: 获取总权益失败: {e}")
        return 1

    prev_close = load_prev_close(today)
    ts = update_total_asset(total, today, prev_close)
    upsert_trades_record(total, today, ts)
    push_to_aws()

    print(f"✅ 总资已记录: ${total:.2f} ({today} {ts} BJT)"
          + (f", 前收盘 ${prev_close:.2f}" if prev_close else ", 无前收盘基准"))
    print(f"   已写入 {TOTAL_ASSET_PATH}")
    print(f"   已写入/更新 {TRADES_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
