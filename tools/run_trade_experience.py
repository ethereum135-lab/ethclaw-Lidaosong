#!/usr/bin/env python3
"""运行经验分析工具处理最新卖出交易并更新总经验档案"""
import sys; sys.path.insert(0, 'tools')
from trade_experience import *
import json

# 用工具自带函数获取最近一笔卖出+对应买入
result = get_last_exit()
if result and result['sell']:
    sell = result['sell']
    buy = result['buy']
    
    # 分析并记录经验
    analysis = analyze_exit(sell, buy)
    
    entry = record_trade_experience(analysis)
    if entry is None:
        print(f"[SKIP] {analysis['symbol']}: already analyzed (duplicate)")
    else:
        print(f"[RECORDED] {analysis['symbol']} | P&L:{analysis['pnl_pct']:+.1f}% | Quality:{analysis['exit_quality']} | Signals:{analysis['trigger_signals']}")
    
    # 展示总档案
    print()
    print(show_master())
else:
    print("No sell trades found")
