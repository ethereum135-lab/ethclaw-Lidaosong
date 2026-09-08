#!/usr/bin/env python3
"""Isolate the exact regex error character by character from full length."""
import re

# Extract from file
with open('/Users/lidaosong/zq_web4_trading_system/profiles/a4-blade/executor.py') as f:
    content = f.read()
lines = content.split('\n')
line254 = lines[253]

import ast
# Try to evaluate the EXACT Python expression
# The line is: r'...' + esc + r'...'
# We need to extract the r-strings
exec_env = {'esc': 'HYPER'}
try:
    result = eval(line254.strip(), exec_env)
    print(f'Eval result type: {type(result)}')
    print(f'Eval result: {result!r}')
    print(f'Length: {len(result)}')
    
    try:
        re.compile(result)
        print('✅ Compiles OK')
    except re.error as e:
        print(f'❌ at pos {e.pos}: {e.msg}')
        # Show each character around the error
        start = max(0, e.pos - 5)
        end = min(len(result), e.pos + 10)
        for i in range(start, end):
            marker = ' <-- ERROR' if i == e.pos else ''
            print(f'  pos {i}: char={result[i]!r} (0x{ord(result[i]):04x}){marker}')
except Exception as e:
    print(f'Eval error: {e}')
    # Try manual construction
    print('\nManual construction fallback...')
