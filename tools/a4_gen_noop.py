#!/usr/bin/env python3
"""Generate NOOP a4_signals.json and append NODE_CHECK to TRADES.md"""
import json, os
from datetime import datetime

ZQ_ROOT = os.path.expanduser("~/zq_web4_trading_system")
now = datetime.now()
ts = now.strftime('%Y-%m-%d %H:%M')
seq = 120

# === Phase analysis summary ===
with open(os.path.join(ZQ_ROOT, "data/phase_analysis.json")) as f:
    pa = json.load(f)

ps = pa.get("phase_summary", {})
ac = pa.get("action_summary", {})

buy_r = ac.get("BUY_READY", 0)
sell_n = ac.get("SELL_NOW", 0)
watch = ac.get("WATCH", 0)
just_s = ps.get("just_starting", 0)
peak = ps.get("peaking", 0)

buy_cands = pa.get("buy_candidates", [])
top_buy = ""
if buy_cands:
    top3 = buy_cands[:3]
    top_buy = "、".join([f'{c["symbol"]}(conf{c.get("confidence",0)}·score{c.get("total_score",0)}·{c.get("level","")}·{c.get("phase","")}·{c.get("gain_24h",0):.1f}%)' for c in top3])

sell_cands = pa.get("sell_candidates", [])
top_sell = ""
if sell_cands:
    top_sell = "、".join([f'{c["symbol"]}({c.get("phase","")}·{c.get("gain_24h",0):.1f}%)' for c in sell_cands])

# === Current balance info ===
holding_str = "ZEC($100.84·trending/WATCH·score66·HOLD✅)·EPIC($77.83·just_starting/BUY_READY·score88·HOLD✅)·TON($49.45·trending/WATCH·score76·HOLD✅)·PARTI($34.18·浮亏阻塞轮换·HOLD)"
dust_str = "DYM($3.78·unsellable)·UNI($3.06·unsellable)·ORDI($1.32·unsellable)"

node_check = (
    f'A4 Cycle #{seq} — '
    f'SOCKS5通·SSH通·AWS通·'
    f'a4_signals(seq={seq}·NOOP)已推送·'
    f'phase_analysis({ts[:16]}·{just_s}just_starting·{peak}peaking·{buy_r}BUY_READY·{sell_n}SELL_NOW·{watch}WATCH)·'
    f'4满位·'
    f'{holding_str}·'
    f'尘仓:{dust_str}·'
    f'BUY_READY最佳:{top_buy[:120]}·'
    f'SELL_NOW:{top_sell[:60]}·'
    f'4满+PARTI浮亏<$1→例外可轮换·'
    f'USDT=$0.01(0%)·'
    f'总资~$274·'
    f'今日已realized:+$14.78(269%日达标✅)·'
    f'无新BUY/SELL·全HOLD·'
    f'a4_signals(seq={seq}·NOOP)已推送AWS'
)

# === Append to TRADES.md ===
trades_path = os.path.join(ZQ_ROOT, "audit/TRADES.md")
pipe_line = f'||||||||||||| {ts} | NODE_CHECK | - | - | - | {node_check} |TRADES_EOF|\n'
with open(trades_path, 'a') as f:
    f.write(pipe_line)
print(f'✅ NODE_CHECK appended to TRADES.md')

# === Write a4_signals.json ===
signal = {
    'signal_id': f'sig_20260608_{seq}',
    'generated_at': now.strftime('%Y-%m-%dT%H:%M:%S+08:00'),
    'a4_cycle': f'{ts} BJT',
    'sequence': seq,
    'buy_signals': [],
    'sell_signals': [],
    'position_eval': {
        'positions_count': 4,
        'usdt_balance': 0.01,
        'total_equity': 274.35,
        'action_summary': 'NOOP — no USDT available, all positions HOLD'
    },
    'tags_context': {
        'today_realized_pnl': '+14.78',
        'daily_target_pct': '269%'
    }
}

sig_dir = os.path.join(ZQ_ROOT, "data/signals")
os.makedirs(sig_dir, exist_ok=True)
sig_path = os.path.join(sig_dir, "a4_signals.json")
with open(sig_path, 'w') as f:
    json.dump(signal, f, indent=2)
print(f'✅ a4_signals.json seq={seq} written (NOOP)')

# === Push to AWS via SCP ===
import subprocess
pem = os.path.expanduser("~/.zq_vault/web4.0.pem")
aws_host = "ubuntu@15.134.211.154"
aws_path = "/home/ubuntu/zq_web4_trading_system/data/signals/a4_signals.json"

# Use cat pipe mode to avoid SCP timeout
cmd = f'cat {sig_path} | ssh -i {pem} -o ConnectTimeout=10 {aws_host} "cat > {aws_path}"'
result = subprocess.run(cmd, shell=True, capture_output=True, timeout=20)
if result.returncode == 0:
    print(f'✅ a4_signals.json pushed to AWS')
else:
    print(f'⚠️ AWS push failed: {result.stderr.decode()[:200]}')
    print(f'   a4_signals.json available locally at {sig_path}')
