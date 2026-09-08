#!/usr/bin/env python3
"""Change TOP30 to TOP50 in a3_signal_scanner.py on AWS"""

import sys
sys.path.insert(0, '/Users/lidaosong/zq_web4_trading_system/tools')

from hermes_tools import terminal

# Read the file
r = terminal('ssh web4 "cat /home/ubuntu/zq_web4_trading_system/tools/a3_signal_scanner.py"', timeout=15)
code = r['output']

# Change TOP30 to TOP50
code = code.replace('[:30]', '[:50]')
code = code.replace('快速模式: TOP30', '快速模式: TOP50（精选池扩至165个币）')

# Write back via base64 to avoid escaping issues
import base64
encoded = base64.b64encode(code.encode()).decode()
r2 = terminal(f'ssh web4 "echo {encoded} | base64 -d > /home/ubuntu/zq_web4_trading_system/tools/a3_signal_scanner.py"', timeout=15)
print(r2['output'])

# Verify
r3 = terminal('ssh web4 "grep TOP50 /home/ubuntu/zq_web4_trading_system/tools/a3_signal_scanner.py"', timeout=10)
print(f'Verify: {r3["output"]}')
