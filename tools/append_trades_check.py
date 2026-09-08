#!/usr/bin/env python3
"""Append A4 Cycle #191 NODE_CHECK to TRADES.md"""
import json
from datetime import datetime

timestamp = "2026-06-10 03:00 BJT"
now = datetime.now().strftime("%Y-%m-%d %H:%M BJT")

entry = f"||||||| {now} | NODE_CHECK | - | - | - | A4 Cycle #191 SOCKS5通 SSH AWS死(port65535)·路径B本地直连·4满位·ZEC($106 +15.95%entry -0.37%24h consolidating/WATCH) HOLD·TON($51 +6.48%entry -3.88%24h consolidating/WATCH) HOLD·PARTI($36 +2.01%entry +5.67%24h js/BUY_READYconf10 STRONG100)·CHIP($26 +2.29%entry +11.53%24h new3h just_starting) HOLD·USDT$40.64(15.7%<20%)·总资~$259·今日$0(0%日目标$5.17)·F&G=10极恐·BTC~$61,734(-2.73%)·SELL_CHECK(全盈利无风险信号)·BUY_READY(10候:STGconf7/112/A8A7 +13.6% HMSTRconf9/80 CHZconf7/97/vol$39M GENIUSconf7/92 ELFconf7/82 INITcs/87 LTCcs/78)·4满位+USDT<20%+CHIP新<6h→FULL HOLD·无BUY/SELL·决策完成·本地直连·等待SSH恢复推信号 |TRADES_EOF|\n"

# Read existing TRADES.md and find end
trades_path = '/Users/lidaosong/zq_web4_trading_system/audit/TRADES.md'
with open(trades_path, 'r') as f:
    content = f.read()

# Remove trailing marker if present
if 'TRADES_EOF|' in content:
    content = content.replace('|TRADES_EOF|', '')
if 'TRADES_EOF|\n' in content:
    content = content.replace('|TRADES_EOF|\n', '')

# Append new entry
content += entry

with open(trades_path, 'w') as f:
    f.write(content)

print(f"✅ Cycle #191 NODE_CHECK appended to TRADES.md at {now}")
