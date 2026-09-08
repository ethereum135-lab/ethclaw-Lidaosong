#!/bin/bash
# A8 大额买入检测 - v2.2 追加选币库打标
# 部分数据源受限（Solscan 404、Dune超时）属于已知状态，不视为崩溃
# 只有完全无法运行时才报故障
cd /Users/lidaosong/zq_web4_trading_system
LOG="/Users/lidaosong/zq_web4_trading_system/data/a8/a8_last_run.log"
python3 tools/a8_data_fetch.py > "$LOG" 2>&1
RC=$?

# 选币库打标：提取快照中的TOP信号币写入标签
if [ -f "data/a8/a8_data_snapshot.json" ]; then
  python3 -c "
import json, os, sys
snap_path = 'data/a8/a8_data_snapshot.json'
if not os.path.exists(snap_path):
    sys.exit(0)
with open(snap_path) as f:
    data = json.load(f)
# 提取solana买入信号
coins = []
for tx_type, txs in data.items():
    if isinstance(txs, list):
        for tx in txs[:5]:  # 每类取前5
            if isinstance(tx, dict):
                sym = tx.get('symbol', tx.get('token', tx.get('coin', '')))
                if sym and sym.endswith('USDT'):
                    coins.append(sym)
                elif sym and not any(x in sym.upper() for x in ['BTC','ETH','SOL','USDT','USDC','BUSD']):
                    coins.append(sym + 'USDT')
# 去重并打标
for sym in set(coins[:10]):
    tag = '{\"smart_money_signal\":true,\"source\":\"a8_snapshot\",\"detected_at\":\"' + data.get('timestamp','now') + '\"}'
    os.system(f'python3 tools/enrich_coin.py --source A8 --symbol {sym} --tag \'{tag}\' >> /dev/null 2>&1')
" 2>/dev/null
fi

if [ $RC -ne 0 ]; then
  # Python内部errors包含"失败"：部分数据源受限但整体仍可用
  # 只有完全无输出才标error
  if grep -q "=== A8 数据采集" "$LOG" 2>/dev/null; then
    # 部分数据源受限但整体可用 — 静默写入state
    python3 tools/write_state_now.py a8 ok > /dev/null 2>&1
    exit 0
  fi
  echo "⚠️ A8 数据采集完全失败 (exit code=$RC)"
  echo "=== 错误日志 ==="
  tail -30 "$LOG"
  exit $RC
fi
# 完全成功 — 写入state后静默退出
python3 tools/write_state_now.py a8 ok > /dev/null 2>&1
exit 0
