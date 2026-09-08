#!/bin/bash
# A3 基础信号扫描定时刷新 — 通过SSH SOCKS隧道访问币安(绕过451地理封锁)
# 2026-08-31 创建：修复 signals.json 基础扫描3天无刷新的根因(Mac无法直连币安+无定时任务)
export ALL_PROXY=socks5h://127.0.0.1:1080
export all_proxy=socks5h://127.0.0.1:1080
cd /Users/lidaosong/zq_web4_trading_system || exit 1
LOG=logs/signals_scan.log
mkdir -p logs
LOCK=logs/.signals_scan.lock
mkdir "$LOCK" 2>/dev/null || { echo "[$(date '+%F %T')] 已有扫描在运行，跳过本次" >> "$LOG"; exit 0; }
trap 'rmdir "$LOCK" 2>/dev/null' EXIT
echo "===== [$(date '+%F %T')] 信号刷新开始 =====" >> "$LOG"
# 隧道未就绪则等待并重试(最多等2分钟)
for i in $(seq 1 8); do
    if curl -s --max-time 5 --socks5-hostname 127.0.0.1:1080 https://api.binance.com/api/v3/ping >/dev/null 2>&1; then
        break
    fi
    sleep 15
done
/opt/homebrew/bin/python3 tools/a3_signal_scanner.py --threads 8 >> "$LOG" 2>&1
/opt/homebrew/bin/python3 tools/smart_signal_inject.py >> "$LOG" 2>&1
echo "===== [$(date '+%F %T')] 信号刷新结束 =====" >> "$LOG"
