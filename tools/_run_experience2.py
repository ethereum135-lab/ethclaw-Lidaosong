#!/usr/bin/env python3
"""Record LAYER sell experience and show master"""
import sys
sys.path.insert(0, 'tools')
from trade_experience import *
from datetime import datetime
import os

# LAYER sell: price $0.0733, PnL -3.55% 
# => buy_price = 0.0733 / (1 - 0.0355) ≈ 0.0760
sell_price = 0.0733
pnl_pct = -3.55
buy_price = sell_price / (1 + pnl_pct/100)

analysis = {
    'symbol': 'LAYER',
    'sell_time': '2026-06-23 06:45 BJT',
    'buy_time': '未知(外部下单)',
    'sell_price': sell_price,
    'buy_price': round(buy_price, 4),
    'exit_reason': '硬止损触发: PnL -3.55%超FNG<20 -3%硬止损',
    'qty': 1686.15,
    'pnl_pct': pnl_pct,
    'pnl_usd': round(1686.15 * (sell_price - buy_price), 2),
    'trigger_signals': ['硬止损'],
    'exit_quality': 'wrong',
    'lesson': 'LAYER硬止损-3.55%: FNG<20环境下指标止损严格执行，亏损已验证硬止损信号有效性0%'
}

entry = record_trade_experience(analysis)
if entry:
    print('经验已记录: LAYER P&L:{:+.1f}% 质量:{}'.format(pnl_pct, analysis['exit_quality']))
else:
    print('重复分析，跳过写入（文件已存在）')

print()
print(show_master())
