#!/usr/bin/env python3
import sys, os
sys.path.insert(0, '/Users/lidaosong/zq_web4_trading_system/tools')
from send_feishu_report import send_message

report_path = '/Users/lidaosong/zq_web4_trading_system/tmp_feishu_report.txt'
with open(report_path) as f:
    content = f.read().strip()

if content:
    send_message(content)
    print('Feishu report sent successfully')
else:
    print('Empty content, nothing sent')

os.remove(report_path)
