#!/usr/bin/env python3
"""
ZQ Web4.0 — AWS引擎数据同步到Mac端
每30分钟自动运行（cron），或手动触发。
同步：
  - 引擎日志 → 解析交易 → 更新 audit/TRADES.md
  - 生产数据文件 → 更新 data/ (node_history, trend_store, node_state)
  - 生产节点日志 → 更新 audit/NODES.md
"""

import re
import json
import os
import sys
import subprocess
from datetime import datetime, timezone, timedelta

WORKDIR = os.path.expanduser("~/zq_web4_trading_system")
AWS_KEY = os.path.expanduser("~/.zq_vault/web4.0.pem")
AWS_HOST = "15.134.211.154"
AWS_USER = "ubuntu"
AWS_LOG_PATH = "/home/ubuntu/zq_web4_trading_system/logs/engine_cron.log"
AWS_PROD_DIR = "/home/ubuntu/zq_web4_trading_system/production/engine"

BJT = timezone(timedelta(hours=8))


def ssh_cmd(cmd):
    """Run command via SSH and return stdout"""
    full_cmd = [
        "ssh", "-i", AWS_KEY,
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=10",
        f"{AWS_USER}@{AWS_HOST}", cmd
    ]
    r = subprocess.run(full_cmd, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        print(f"SSH ERROR [{r.returncode}]: {r.stderr.strip()}")
        return None
    return r.stdout


def parse_log(log_text):
    """Parse engine_cron.log into trade events."""
    lines = log_text.split('\n')
    trades = []
    current_ts = None
    pending_exits = []
    pending_sells = []
    pending_buys = []

    def flush_node():
        nonlocal current_ts, pending_exits, pending_sells, pending_buys
        for i, sel in enumerate(pending_sells):
            coin = pending_exits[i]['coin'] if i < len(pending_exits) else '?'
            reason = pending_exits[i]['reason'] if i < len(pending_exits) else ''
            trades.append({
                'ts': current_ts, 'action': 'SELL',
                'coin': coin, 'qty': sel['qty'],
                'price': sel['price'], 'reason': reason
            })
        for b in pending_buys:
            trades.append(b)
        pending_exits = []
        pending_sells = []
        pending_buys = []

    for line in lines:
        m = re.search(r'⏰ ZQ 30分钟节点 — (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
        if m:
            if current_ts:
                flush_node()
            current_ts = m.group(1)
            continue
        if current_ts is None:
            continue
        m = re.search(r'🔴 ([\w.]+) — (.+)', line)
        if m:
            pending_exits.append({'coin': m.group(1), 'reason': m.group(2)})
            continue
        m = re.search(r'✅ 卖出 ([\d.]+) @ \$([\d.]+)', line)
        if m:
            pending_sells.append({'qty': float(m.group(1)), 'price': float(m.group(2))})
            continue
        m = re.search(r'✅ 买入 ([\d.]+) ([\w.]+) @ \$([\d.]+)', line)
        if m:
            pending_buys.append({
                'ts': current_ts, 'action': 'BUY',
                'coin': m.group(2), 'qty': float(m.group(1)),
                'price': float(m.group(3)), 'reason': '评分自动执行'
            })
            continue

    if current_ts:
        flush_node()

    return trades


def utc_to_bjt(ts_str):
    """Convert UTC timestamp to BJT"""
    dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
    bjt_dt = dt.replace(tzinfo=timezone.utc).astimezone(BJT)
    return bjt_dt.strftime("%Y-%m-%d %H:%M:%S")


def format_trades_row(trade):
    """Format as TRADES.md row"""
    ts_bjt = utc_to_bjt(trade['ts'])
    action = trade['action']
    coin = trade['coin']
    qty = f"{trade['qty']:.4f}".rstrip('0').rstrip('.')
    price = f"${trade['price']:.4f}"
    reason = trade['reason']
    decision = ''
    return f"| {ts_bjt} | {action} | {coin} | {qty} | {price} | {reason} | {decision} | | |\n"


def load_existing_trades(path):
    """Load existing TRADES.md lines, return last BJT timestamp"""
    if not os.path.exists(path):
        return [], None
    with open(path) as f:
        lines = f.readlines()
    last_ts = None
    for line in lines:
        m = re.match(r'\| (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
        if m:
            last_ts = m.group(1)
    return lines, last_ts


def update_trades_md(aws_trades):
    """Append new trades to TRADES.md"""
    trades_path = os.path.join(WORKDIR, "audit", "TRADES.md")
    existing, last_ts = load_existing_trades(trades_path)

    if last_ts:
        print(f"  Mac端 TRADES.md 最后时间: {last_ts} (BJT)")
    else:
        print("  Mac端 TRADES.md 为空或无有效记录")

    new_trades = []
    for t in aws_trades:
        ts_bjt = utc_to_bjt(t['ts'])
        if last_ts is None or ts_bjt > last_ts:
            new_trades.append(t)

    if not new_trades:
        print("  无新交易需要同步")
        return

    print(f"  发现 {len(new_trades)} 条新交易（AWS端）")

    os.makedirs(os.path.dirname(trades_path), exist_ok=True)
    with open(trades_path, 'a') as f:
        for t in new_trades:
            row = format_trades_row(t)
            f.write(row)

    print(f"  ✅ 已追加 {len(new_trades)} 条到 TRADES.md")
    buys = [t for t in new_trades if t['action'] == 'BUY']
    sells = [t for t in new_trades if t['action'] == 'SELL']
    print(f"    其中 BUY={len(buys)}, SELL={len(sells)}")
    print(f"    时间范围: {utc_to_bjt(new_trades[0]['ts'])} ~ {utc_to_bjt(new_trades[-1]['ts'])} (BJT)")


def sync_data_file(aws_path, local_path, name, optional=False):
    """Sync a single data file from AWS to local"""
    print(f"  📄 同步 {name}...")
    content = ssh_cmd(f"cat {aws_path}")
    if content is None:
        if optional:
            print(f"    ⏭ {name} 在AWS端暂无记录（可选文件），跳过")
            return True
        print(f"    ❌ 无法读取AWS: {aws_path}")
        return False
    
    if not content.strip():
        if optional:
            print(f"    ⏭ {name} 为空（暂无成交），跳过")
            return True
        print(f"    ⚠️ AWS端文件为空")
        return False

    # 2026-08-11 修复: AWS旧档覆盖本地新数据事故（本地node_history被覆盖为5月旧档）
    # 本地文件比AWS新 → 跳过覆盖（本地聚合器每5分钟追加，本地几乎总是更新）
    if os.path.exists(local_path):
        remote_mtime = ssh_cmd(f"stat -c %Y {aws_path} 2>/dev/null")
        if remote_mtime and remote_mtime.strip().isdigit():
            try:
                if os.path.getmtime(local_path) > float(remote_mtime.strip()):
                    print(f"    ⏭ 本地{name}比AWS新(mtime)，跳过覆盖保护本地数据")
                    return True
            except Exception:
                pass

    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    with open(local_path, 'w') as f:
        f.write(content)
    
    lines = content.count('\n')
    size = len(content)
    print(f"    ✅ 已同步 {lines}行 / {size/1024:.0f}KB → {local_path}")
    return True


def main():
    print("=" * 60)
    print(f"🔁 ZQ AWS→Mac 全量同步 | {datetime.now(BJT).strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Step 1: Sync data files from AWS production engine
    print("\n1️⃣  同步生产数据文件...")
    aws_prod_data = f"{AWS_PROD_DIR}/data"
    
    data_files = [
        ("node_history.jsonl", os.path.join(WORKDIR, "data", "node_history.jsonl")),
        ("trend_store.json",   os.path.join(WORKDIR, "data", "trend_store.json")),
        ("node_state.json",    os.path.join(WORKDIR, "data", "node_state.json")),
    ]

    # 2026-08-31 新增: trend_bot v3.1 主引擎状态/账本同步（AWS 权威 → Mac 只读副本）
    trend_files = [
        ("/home/ubuntu/zq_web4_trading_system/data/trades/trend_state.json",
         os.path.join(WORKDIR, "data", "trades", "trend_state.json"), "trend_state.json"),
        ("/home/ubuntu/zq_web4_trading_system/data/trades/trend_trades.jsonl",
         os.path.join(WORKDIR, "data", "trades", "trend_trades.jsonl"), "trend_trades.jsonl"),
    ]
    
    data_ok = 0
    for fname, local_path in data_files:
        aws_path = f"{aws_prod_data}/{fname}"
        if sync_data_file(aws_path, local_path, fname):
            data_ok += 1
    for aws_path, local_path, name in trend_files:
        if sync_data_file(aws_path, local_path, name, optional=(name == "trend_trades.jsonl")):
            data_ok += 1
    print(f"  数据文件同步: {data_ok}/{len(data_files) + len(trend_files)}")

    # Step 2: Sync NODES.md
    print("\n2️⃣  同步节点日志 (NODES.md)...")
    aws_nodes = f"{AWS_PROD_DIR}/audit/NODES.md"
    local_nodes = os.path.join(WORKDIR, "audit", "NODES.md")
    sync_data_file(aws_nodes, local_nodes, "NODES.md")

    # Step 3: Sync TRADES.md directly (AWS权威台账直同步)
    # 2026-08-23 修复: engine_cron.log自5/11起已死(A4改用a4_independent.py直接写台账),
    # 旧逻辑 cat 死日志→解析0笔→Mac TRADES.md冻结在8/16, 且cat 60s超时导致launchd退出码1
    print("\n3️⃣  同步 TRADES.md (AWS权威台账直同步)...")
    aws_trades_md = "/home/ubuntu/zq_web4_trading_system/audit/TRADES.md"
    local_trades_md = os.path.join(WORKDIR, "audit", "TRADES.md")
    ok = sync_data_file(aws_trades_md, local_trades_md, "TRADES.md")
    if not ok:
        print("  ❌ TRADES.md 同步失败")
        return 1

    print(f"\n✅ 同步完成 — {datetime.now(BJT).strftime('%Y-%m-%d %H:%M:%S')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
