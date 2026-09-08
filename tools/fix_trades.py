#!/usr/bin/env python3
"""Fix TRADES.md after replace_all corruption.
Strategy: Find the repeated new node content block and replace each instance with '|||'
to restore the original file structure."""
import re

with open('/Users/lidaosong/zq_web4_trading_system/audit/TRADES.md', 'r') as f:
    content = f.read()

# The replacement block starts with:
# \n|||\n|\n|\n### 2026-05-24 00:15 BJT | 执行节点
# and ends with:
# | 🟡 新日开始 |

# Find the first occurrence of our new node content
start_marker = '\n|||\n|\n|\n### 2026-05-24 00:15 BJT | 执行节点'
end_marker = '新交易日(5/24)尚未有交易，目标$5.66/天 | 🟡 新日开始 |'

idx_start = content.find(start_marker)
idx_end = content.find(end_marker, idx_start)
if idx_start >= 0 and idx_end >= 0:
    # Extract the repeated block (from start to end, inclusive)
    block = content[idx_start:idx_end + len(end_marker)]
    block_len = len(block)
    print(f"Found replacement block: {block_len} chars")
    print(f"Block starts with: {repr(block[:60])}")
    print(f"Block ends with: {repr(block[-60:])}")
    
    # Count occurrences
    count = content.count(block)
    print(f"Block appears {count} times")
    
    # Replace all instances with '|||' to restore original
    fixed = content.replace(block, '|||')
    
    # Write fixed version
    with open('/Users/lidaosong/zq_web4_trading_system/audit/TRADES.md', 'w') as f:
        f.write(fixed)
    
    # Check result
    lines = fixed.split('\n')
    print(f"Fixed file: {len(lines)} lines")
else:
    print("Could not find block boundaries")
    # Try alternate end marker
    idx_end = content.find('🟡 新日开始 |', idx_start)
    if idx_end >= 0:
        block = content[idx_start:idx_end + len('🟡 新日开始 |')]
        print(f"Alt block: {len(block)} chars, appears {content.count(block)} times")
        fixed = content.replace(block, '|||')
        with open('/Users/lidaosong/zq_web4_trading_system/audit/TRADES.md', 'w') as f:
            f.write(fixed)
        lines = fixed.split('\n')
        print(f"Fixed file: {len(lines)} lines")
    else:
        print("Still couldn't find it")
        # Print what's around where the start marker should be
        print(f"Content around {idx_start}:")
        print(repr(content[max(0,idx_start-100):idx_start+200]))
