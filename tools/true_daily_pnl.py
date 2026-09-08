#!/usr/bin/env python3
"""计算真·日盈亏（总权益变化），所有复盘cron统一调用
输出格式（一行，供cron解析）：
  TRUE:$-46.00 CLOSE:$289.00 NOW:$243.00 TARGET:$5.78 SELLS:$100.80
或
  ERROR:<原因>

依赖：从TRADES.md读取昨日收盘和当前总权益，或fallback到data/total_asset.json

🔴 2026-08-08 FIX: 只认「### YYYY-MM-DD 节 + 总资行」的带日期记录。
   昨日收盘 = 倒数第二条记录，且必须与最后一条相邻(间隔≤1天)。
   记录断档/缺失 → 诚实报GAP/STALE并用total_asset.json兜底，
   绝不拿N天前或旧复盘流水里的「总资~$X」冒充昨日收盘。
"""
import json, os, re, sys, subprocess
import datetime

# 2026-08-10 FIX: A4已改写到 data/TRADES.md（live），audit/TRADES.md 停留在08-08不再更新。
# 优先 live 文件；不存在或为空时回退 audit/。
TRADES_PATH = "/Users/lidaosong/zq_web4_trading_system/data/TRADES.md"
TRADES_PATH_LEGACY = "/Users/lidaosong/zq_web4_trading_system/audit/TRADES.md"
import os as _os
if not _os.path.exists(TRADES_PATH):
    TRADES_PATH = TRADES_PATH_LEGACY


def load_equity_with_dates(text):
    """返回 [(日期, 总资行), ...]，只收带 ##/### YYYY-MM-DD 节头的记录
    2026-08-14 FIX: A4已改写为 ## 节头 + 无分隔符总权益(如 总权益$213.76)，同步支持"""
    equity_with_dates = []
    cur_date = None
    for ln in text.split('\n'):
        dm = re.search(r'#{2,3}\s+(\d{4}-\d{2}-\d{2})', ln)
        if dm:
            cur_date = dm.group(1)
        if re.search(r'\|\s*(?:总资|净值)\s*\|\s*\$?\d+\.\d+', ln) or \
           re.search(r'(?:总权益|总资)\s*(?:[=~:：]+\s*|\$)\s*\*{0,2}\s*~?\$?\d+\.\d+', ln):
            if cur_date:
                equity_with_dates.append((cur_date, ln))
    return equity_with_dates


def _num(s):
    # 2026-08-10 FIX: 只取 总资/总权益 之后的数字，避免误取行首 USDT free 金额
    # 2026-08-14 FIX: 兼容无分隔符格式(总权益$213.76) 与 净值 列
    m = re.search(r'(?:总权益|总资)\s*(?:[=~:：]+\s*|\$)\s*\*{0,2}\s*~?\$?(\d+\.\d+)', s)
    if m:
        return float(m.group(1))
    m = re.search(r'\|\s*(?:总资|净值)\s*\|\s*\$?(\d+\.\d+)', s)
    if m:
        return float(m.group(1))
    m = re.search(r'(\d+\.\d+)', s)
    return float(m.group(1)) if m else None


def fetch_live_equity():
    """2026-08-24 FIX: 调 fetch_real_balance.py 从 Binance API 实查总权益。
    返回 (权益float, 查询时间str)；失败返回 None。"""
    try:
        base = os.path.dirname(os.path.abspath(__file__))
        proc = subprocess.run(
            [sys.executable, os.path.join(base, 'fetch_real_balance.py')],
            capture_output=True, timeout=40)
        out = proc.stdout.decode() if proc.stdout else ''
        m = re.search(r'总权益[:：]?\s*\$?(\d+\.\d+)', out)
        if m:
            tm = re.search(r'查询时间[:：]\s*([\d\-: ]+)', out)
            return float(m.group(1)), (tm.group(1).strip() if tm else '?')
    except Exception:
        pass
    return None


def fallback_output(reason, last_date='?', prev_date='?'):
    base_dir = os.path.dirname(TRADES_PATH)
    fallback_path = os.path.join(base_dir, '..', 'data', 'total_asset.json')
    node_hist_path = os.path.join(base_dir, '..', 'data', 'node_history.jsonl')
    # 2026-08-10 FIX: NOW 取 node_history.jsonl 最新一条（每5分钟实时），
    # CLOSE 取 total_asset.json（昨日收盘）。之前把昨日收盘当 NOW，导致 TRUE 恒为 $0。
    now_v = None
    if os.path.exists(node_hist_path):
        try:
            with open(node_hist_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    if rec.get('total'):
                        now_v = float(rec['total'])
        except Exception:
            now_v = None
    if os.path.exists(fallback_path):
        with open(fallback_path) as f:
            fallback = json.load(f)
        fb_total = fallback.get('total', 0)
        fb_date = fallback.get('date', '?')

        # 2026-08-31 FIX: total_asset.json 现在是「当日记录」（daily_close_record.py 21:20写入）。
        # 日期==今天 → 它作为 NOW；CLOSE 从 TRADES.md 中今天之前最后一条 总资/总权益 记录取，
        # 不再把它误当昨日收盘（否则 TRUE 恒≈0）。
        if fb_date == datetime.datetime.now().strftime('%Y-%m-%d'):
            if now_v is None:
                now_v = fb_total
            close_v = None
            close_date = '?'
            try:
                with open(TRADES_PATH) as f:
                    text = f.read()
                today = datetime.datetime.now().strftime('%Y-%m-%d')
                eq = load_equity_with_dates(text)
                by_date = {}
                for d, ln in eq:
                    by_date.setdefault(d, []).append(ln)
                prev_dates = sorted(d for d in by_date if d < today)
                if prev_dates:
                    close_date = prev_dates[-1]
                    close_v = _num(by_date[close_date][-1])
            except Exception:
                pass
            if close_v is None or close_v <= 0:
                print(f"ERROR:{reason} 且无可用昨日收盘基准（TRADES.md 无历史记录）")
                sys.exit(1)
            pnl = now_v - close_v
            target = close_v * 0.002
            target_pct = (pnl / target * 100) if target > 0 else 0
            print(f"TRUE:${pnl:+.2f} CLOSE:${close_v:.2f} NOW:${now_v:.2f} TARGET:${target:.2f} PCT:{target_pct:.0f}% ({reason}:last equity {last_date} vs prev {prev_date}, close=TRADES {close_date}, now=total_asset today)")
            if '--report' in sys.argv:
                emoji = "✅" if pnl >= 0 else "❌"
                print(f"{emoji} 真·日盈亏：{close_v:.2f}→{now_v:.2f}={pnl:+.2f} (目标+{target:.2f})")
            sys.exit(0)

        # 旧行为：total_asset.json 日期!=今天 → 它确实是昨日收盘
        close_v = fb_total
        close_date = fb_date
        if now_v is None:
            now_v = close_v
        pnl = now_v - close_v
        target = close_v * 0.002
        target_pct = (pnl / target * 100) if target > 0 else 0
        print(f"TRUE:${pnl:+.2f} CLOSE:${close_v:.2f} NOW:${now_v:.2f} TARGET:${target:.2f} PCT:{target_pct:.0f}% ({reason}:last equity {last_date} vs prev {prev_date}, close=total_asset.json {close_date}, now=node_history live)")
        if '--report' in sys.argv:
            emoji = "✅" if pnl >= 0 else "❌"
            print(f"{emoji} 真·日盈亏：{close_v:.2f}→{now_v:.2f}={pnl:+.2f} (目标+{target:.2f})")
    else:
        print(f"ERROR:{reason} and no total_asset.json fallback")
    sys.exit(0 if os.path.exists(fallback_path) else 1)


def main():
    """真·日盈亏：昨日收盘=最近一天的最后一条总资记录；今日NOW=今天最后一条(旧>30min→live API)。
    2026-08-31 FIX: 旧逻辑取「文件最后两条记录」当昨日/今日——A4每天写多条执行节点，
    会把今天盘中的 总权益=$X 快照误当昨日收盘。改为按日期分组，只认「昨天最后一条」为CLOSE。
    """
    if not os.path.exists(TRADES_PATH):
        print("ERROR:TRADES.md not found")
        sys.exit(1)

    with open(TRADES_PATH) as f:
        text = f.read()

    equity_with_dates = load_equity_with_dates(text)
    if not equity_with_dates:
        fallback_output("NO_RECORD")

    today_str = datetime.datetime.now().strftime('%Y-%m-%d')

    # 按日期分组：{date: [value_lines...]}
    by_date = {}
    for d, ln in equity_with_dates:
        by_date.setdefault(d, []).append(ln)
    dates = sorted(by_date.keys())

    prev_dates = [d for d in dates if d < today_str]
    if not prev_dates:
        fallback_output("NO_YESTERDAY", dates[-1] if dates else '?')

    prev_date = prev_dates[-1]
    close_v = _num(by_date[prev_date][-1])
    if close_v is None or close_v <= 0:
        fallback_output("BAD_CLOSE", prev_date)

    # 断档>1天 → 仍用真实最近收盘计算，但明确打 GAP 标签（诚实，不冒充相邻日）
    try:
        d_prev = datetime.datetime.strptime(prev_date, '%Y-%m-%d')
        d_today = datetime.datetime.strptime(today_str, '%Y-%m-%d')
        gap_days = (d_today - d_prev).days
    except ValueError:
        gap_days = 99

    today_records = by_date.get(today_str, [])
    now_v = None
    live_tag = ''

    if today_records:
        now_v = _num(today_records[-1])
        # 今天最后一条记录 >30min → Binance API实时权益覆盖NOW（防结算延迟低估）
        tm = re.findall(r'#{2,3}\s+(\d{4}-\d{2}-\d{2})\s+(\d{2}):(\d{2})', text)
        today_last_ts = None
        for ld, lh, lmi in reversed(tm):
            if ld == today_str:
                today_last_ts = datetime.datetime.strptime(f'{ld} {lh}:{lmi}', '%Y-%m-%d %H:%M')
                break
        if today_last_ts and (datetime.datetime.now() - today_last_ts).total_seconds() > 1800:
            live = fetch_live_equity()
            if live:
                now_v = live[0]
                live_tag = f' (live@{live[1]})'
    else:
        # 今天还没有总资记录 → node_history 最新一条作为NOW
        node_hist_path = os.path.join(os.path.dirname(TRADES_PATH), 'node_history.jsonl')
        if os.path.exists(node_hist_path):
            try:
                with open(node_hist_path) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        rec = json.loads(line)
                        if rec.get('total'):
                            now_v = float(rec['total'])
                live_tag = ' (node_history)'
            except Exception:
                now_v = None
        if now_v is None:
            live = fetch_live_equity()
            if live:
                now_v = live[0]
                live_tag = f' (live@{live[1]})'

    if now_v is None:
        fallback_output("NO_NOW", today_str, prev_date)

    pnl = now_v - close_v
    target = close_v * 0.002
    target_pct = (pnl / target * 100) if target > 0 else 0
    gap_tag = f" GAP{gap_days}d" if gap_days > 1 else ""
    print(f"TRUE:${pnl:+.2f} CLOSE:${close_v:.2f} NOW:${now_v:.2f} TARGET:${target:.2f} PCT:{target_pct:.0f}%{live_tag}{gap_tag}")
    if '--report' in sys.argv:
        emoji = "✅" if pnl >= 0 else "❌"
        print(f"{emoji} 真·日盈亏：{close_v:.2f}→{now_v:.2f}={pnl:+.2f} (目标+{target:.2f})")
    sys.exit(0)


if __name__ == '__main__':
    main()
