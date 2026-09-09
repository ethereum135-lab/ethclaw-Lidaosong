#!/usr/bin/env python3
"""
Codex 管道状态看板生成器
========================
读取 pipeline_status.json，生成可视化 HTML 看板。

用法:
  python3 pipeline_dashboard.py              # 生成看板
  python3 pipeline_dashboard.py --watch      # 持续模式（每30秒刷新）
"""

import json
import os
import sys
import time
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

SHARED = Path("/home/ubuntu/shared_context")
STATUS_FILE = SHARED / "monitor" / "pipeline_status.json"
OUTPUT_FILE = SHARED / "reports" / "pipeline_dashboard.html"

PHASES = {
    "collect": {"name": "数据采集", "icon": "📥", "color": "#3b82f6"},
    "analyze": {"name": "数据分析", "icon": "🔬", "color": "#8b5cf6"},
    "risk_check": {"name": "风控检查", "icon": "🛡️", "color": "#ef4444"},
    "execute": {"name": "策略执行", "icon": "⚡", "color": "#f59e0b"},
    "monitor": {"name": "监控告警", "icon": "📡", "color": "#10b981"},
}

CRITICAL_TASKS = ["sync_trading_data", "fx_rates", "risk_manager", "system_monitor"]


def load_status():
    if STATUS_FILE.exists():
        with open(STATUS_FILE, "r") as f:
            return json.load(f)
    return {"phases": {}, "tasks": {}, "history": [], "last_run": None}


def get_system_metrics():
    """获取系统资源指标"""
    try:
        mem_info = {}
        with open("/proc/meminfo") as f:
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    key = parts[0].strip()
                    val = int(parts[1].strip().split()[0])
                    mem_info[key] = val

        total = mem_info.get("MemTotal", 0)
        avail = mem_info.get("MemAvailable", 0)
        free_swap = mem_info.get("SwapFree", 0)
        total_swap = mem_info.get("SwapTotal", 0)

        mem_pct = ((total - avail) / total * 100) if total > 0 else 0
        swap_pct = ((total_swap - free_swap) / total_swap * 100) if total_swap > 0 else 0

        # CPU
        load1 = os.getloadavg()[0] if hasattr(os, "getloadavg") else 0

        # Disk
        disk = subprocess.run(["df", "-h", "/"], capture_output=True, text=True)
        disk_pct = 0
        disk_used = "0G"
        disk_total = "0G"
        if disk.returncode == 0:
            lines = disk.stdout.strip().split("\n")
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) >= 5:
                    disk_pct_s = parts[4].replace("%", "")
                    disk_pct = float(disk_pct_s)
                    disk_used = parts[2]
                    disk_total = parts[1]

        return {
            "mem_total_mb": total // 1024,
            "mem_used_mb": (total - avail) // 1024,
            "mem_pct": round(mem_pct, 1),
            "swap_total_mb": total_swap // 1024,
            "swap_used_mb": (total_swap - free_swap) // 1024,
            "swap_pct": round(swap_pct, 1),
            "load1": round(load1, 2),
            "disk_pct": disk_pct,
            "disk_used": disk_used,
            "disk_total": disk_total,
        }
    except Exception:
        return {}


def calc_24h_stats(history):
    """计算24小时统计"""
    now = datetime.now()
    recent = []
    for h in history:
        try:
            ts = h.get("timestamp", "")
            if ts:
                dt = datetime.fromisoformat(ts)
                if (now - dt).total_seconds() < 86400:
                    recent.append(h)
        except:
            pass

    if not recent:
        return {"runs": 0, "success": 0, "rate": 0}
    runs = len(recent)
    succ = sum(1 for r in recent if r.get("success"))
    return {"runs": runs, "success": succ, "rate": round(succ / runs * 100, 1)}


def generate_html(status, metrics):
    """生成 HTML 看板"""
    stats_24h = calc_24h_stats(status.get("history", []))
    last_run = status.get("last_run", "从未运行")

    phases_html = ""
    for pk, pv in PHASES.items():
        ps = status.get("phases", {}).get(pk, {})
        if ps:
            ok = ps.get("success", False)
            sc = ps.get("success_count", 0)
            tc = ps.get("task_count", 0)
            dur = ps.get("duration", 0)
            lr = ps.get("last_run", "-")
            try:
                lr_dt = datetime.fromisoformat(lr)
                lr = lr_dt.strftime("%H:%M:%S")
            except:
                pass
        else:
            ok = None
            sc = tc = dur = 0
            lr = "-"

        status_class = "ok" if ok else ("fail" if ok is False else "idle")
        phases_html += f"""
        <div class="phase-card {status_class}">
            <div class="phase-icon">{pv['icon']}</div>
            <div class="phase-info">
                <div class="phase-name">{pv['name']}</div>
                <div class="phase-detail">
                    <span class="badge {'badge-ok' if ok else 'badge-fail'}">{sc}/{tc}</span>
                    <span class="duration">{dur:.1f}s</span>
                    <span class="last-run">上次: {lr}</span>
                </div>
            </div>
        </div>"""

    tasks_html = ""
    for tn in CRITICAL_TASKS:
        ts = status.get("tasks", {}).get(tn, {})
        if ts:
            ok = ts.get("success", False)
            dur = ts.get("duration", 0)
            lr = ts.get("last_run", "-")
            try:
                lr_dt = datetime.fromisoformat(lr)
                lr = lr_dt.strftime("%H:%M:%S")
            except:
                pass
        else:
            ok = None
            dur = 0
            lr = "-"

        icon = "✅" if ok else ("❌" if ok is False else "⏳")
        tasks_html += f"""
        <tr>
            <td>{icon}</td>
            <td>{tn}</td>
            <td>{dur:.1f}s</td>
            <td>{lr}</td>
        </tr>"""

    history_html = ""
    for h in reversed(status.get("history", [])[-10:]):
        date = h.get("date", "-")
        ok = h.get("success", False)
        total = h.get("total", 0)
        passed = h.get("passed", 0)
        dur = h.get("duration", 0)
        icon = "✅" if ok else "❌"
        history_html += f"""
        <tr>
            <td>{icon}</td>
            <td>{date}</td>
            <td>{passed}/{total}</td>
            <td>{dur:.1f}s</td>
        </tr>"""

    mem_pct = metrics.get("mem_pct", 0)
    swap_pct = metrics.get("swap_pct", 0)
    disk_pct = metrics.get("disk_pct", 0)
    load1 = metrics.get("load1", 0)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="30">
    <title>Codex 管道状态看板</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0f172a; color: #e2e8f0; padding: 20px;
        }}
        .header {{
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 24px; padding-bottom: 16px;
            border-bottom: 1px solid #334155;
        }}
        .header h1 {{ font-size: 24px; color: #f8fafc; }}
        .header .last-run {{ font-size: 13px; color: #94a3b8; }}
        .header .auto-refresh {{
            font-size: 12px; color: #22c55e;
            background: #14532d; padding: 4px 10px; border-radius: 12px;
        }}
        .grid {{ display: grid; gap: 20px; grid-template-columns: 2fr 1fr; }}
        .left-col {{ display: flex; flex-direction: column; gap: 20px; }}
        .right-col {{ display: flex; flex-direction: column; gap: 20px; }}
        .section {{
            background: #1e293b; border-radius: 12px; padding: 20px;
        }}
        .section-title {{
            font-size: 16px; font-weight: 600; margin-bottom: 16px;
            color: #f1f5f9; display: flex; align-items: center; gap: 8px;
        }}
        .phases-grid {{ display: grid; gap: 12px; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); }}
        .phase-card {{
            display: flex; align-items: center; gap: 12px;
            padding: 14px; border-radius: 10px; border: 1px solid #334155;
            background: #0f172a; transition: all 0.2s;
        }}
        .phase-card.ok {{ border-color: #22c55e; }}
        .phase-card.fail {{ border-color: #ef4444; }}
        .phase-card.idle {{ border-color: #64748b; }}
        .phase-icon {{ font-size: 28px; }}
        .phase-name {{ font-size: 15px; font-weight: 600; }}
        .phase-detail {{ font-size: 12px; color: #94a3b8; display: flex; gap: 10px; margin-top: 4px; align-items: center; }}
        .badge {{ font-size: 11px; padding: 2px 8px; border-radius: 8px; font-weight: 600; }}
        .badge-ok {{ background: #14532d; color: #4ade80; }}
        .badge-fail {{ background: #7f1d1d; color: #f87171; }}
        .duration {{ color: #a78bfa; }}
        .stats-grid {{ display: grid; gap: 12px; grid-template-columns: repeat(2, 1fr); }}
        .stat-box {{
            background: #0f172a; border-radius: 10px; padding: 16px; text-align: center;
        }}
        .stat-value {{ font-size: 28px; font-weight: 700; }}
        .stat-label {{ font-size: 12px; color: #94a3b8; margin-top: 4px; }}
        .stat-value.green {{ color: #4ade80; }}
        .stat-value.yellow {{ color: #fbbf24; }}
        .stat-value.red {{ color: #f87171; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
        th {{ text-align: left; padding: 8px; color: #94a3b8; border-bottom: 1px solid #334155; }}
        td {{ padding: 8px; border-bottom: 1px solid #1e293b; }}
        .progress-bar {{
            height: 6px; background: #334155; border-radius: 3px; margin-top: 8px; overflow: hidden;
        }}
        .progress-fill {{ height: 100%; border-radius: 3px; transition: width 0.3s; }}
        .resource-bar {{
            display: flex; align-items: center; gap: 12px; margin-bottom: 12px;
        }}
        .resource-label {{ font-size: 13px; width: 80px; color: #cbd5e1; }}
        .resource-track {{ flex: 1; height: 8px; background: #334155; border-radius: 4px; overflow: hidden; }}
        .resource-fill {{ height: 100%; border-radius: 4px; }}
        .resource-pct {{ font-size: 13px; width: 50px; text-align: right; }}
        .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #64748b; }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>📊 Codex 数据管道状态看板</h1>
            <div class="last-run">上次运行: {last_run}</div>
        </div>
        <div class="auto-refresh">🔄 自动刷新 30s</div>
    </div>

    <div class="grid">
        <div class="left-col">
            <!-- 阶段状态 -->
            <div class="section">
                <div class="section-title">📦 管道阶段</div>
                <div class="phases-grid">
                    {phases_html}
                </div>
            </div>

            <!-- 关键任务 -->
            <div class="section">
                <div class="section-title">🔑 关键任务</div>
                <table>
                    <thead>
                        <tr><th>状态</th><th>任务</th><th>耗时</th><th>上次运行</th></tr>
                    </thead>
                    <tbody>{tasks_html}</tbody>
                </table>
            </div>

            <!-- 运行历史 -->
            <div class="section">
                <div class="section-title">📈 运行历史</div>
                <table>
                    <thead>
                        <tr><th>状态</th><th>日期</th><th>通过/总数</th><th>耗时</th></tr>
                    </thead>
                    <tbody>{history_html}</tbody>
                </table>
            </div>
        </div>

        <div class="right-col">
            <!-- 24h统计 -->
            <div class="section">
                <div class="section-title">📈 24小时统计</div>
                <div class="stats-grid">
                    <div class="stat-box">
                        <div class="stat-value green">{stats_24h['rate']}%</div>
                        <div class="stat-label">成功率</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">{stats_24h['runs']}</div>
                        <div class="stat-label">运行次数</div>
                    </div>
                </div>
            </div>

            <!-- 系统资源 -->
            <div class="section">
                <div class="section-title">💻 系统资源</div>
                <div class="resource-bar">
                    <span class="resource-label">内存</span>
                    <div class="resource-track">
                        <div class="resource-fill" style="width: {mem_pct}%; background: {'#22c55e' if mem_pct < 70 else '#fbbf24' if mem_pct < 85 else '#ef4444'};"></div>
                    </div>
                    <span class="resource-pct">{mem_pct}%</span>
                </div>
                <div style="font-size: 11px; color: #64748b; margin-bottom: 12px;">
                    {metrics.get('mem_used_mb', 0)}MB / {metrics.get('mem_total_mb', 0)}MB
                </div>

                <div class="resource-bar">
                    <span class="resource-label">Swap</span>
                    <div class="resource-track">
                        <div class="resource-fill" style="width: {swap_pct}%; background: {'#22c55e' if swap_pct < 30 else '#fbbf24' if swap_pct < 60 else '#ef4444'};"></div>
                    </div>
                    <span class="resource-pct">{swap_pct}%</span>
                </div>
                <div style="font-size: 11px; color: #64748b; margin-bottom: 12px;">
                    {metrics.get('swap_used_mb', 0)}MB / {metrics.get('swap_total_mb', 0)}MB
                </div>

                <div class="resource-bar">
                    <span class="resource-label">磁盘</span>
                    <div class="resource-track">
                        <div class="resource-fill" style="width: {disk_pct}%; background: {'#22c55e' if disk_pct < 70 else '#fbbf24' if disk_pct < 85 else '#ef4444'};"></div>
                    </div>
                    <span class="resource-pct">{disk_pct}%</span>
                </div>
                <div style="font-size: 11px; color: #64748b; margin-bottom: 12px;">
                    {metrics.get('disk_used', '0G')} / {metrics.get('disk_total', '0G')}
                </div>

                <div class="resource-bar">
                    <span class="resource-label">负载</span>
                    <span style="font-size: 13px; color: #cbd5e1;">{load1}</span>
                </div>
            </div>
        </div>
    </div>

    <div class="footer">
        Codex Pipeline Dashboard v1.0 · 生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </div>
</body>
</html>"""
    return html


def main():
    parser = argparse.ArgumentParser(description="Codex 管道看板生成器")
    parser.add_argument("--watch", action="store_true", help="持续模式")
    args = parser.parse_args()

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    while True:
        status = load_status()
        metrics = get_system_metrics()
        html = generate_html(status, metrics)

        with open(OUTPUT_FILE, "w") as f:
            f.write(html)

        print(f"[{datetime.now().strftime('%H:%M:%S')}] 看板已生成: {OUTPUT_FILE}")

        if not args.watch:
            break
        time.sleep(30)


if __name__ == "__main__":
    main()
