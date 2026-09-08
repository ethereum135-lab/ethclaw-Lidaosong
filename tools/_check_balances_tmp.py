#!/usr/bin/env python3
import json, sys
d = json.load(sys.stdin)
targets = ['USDT', 'NEAR', 'OP', 'ZRO', 'FET', 'DYM']
for b in d:
    if b['asset'] in targets:
        print(f"{b['asset']}: free={b['free']} locked={b['locked']}")
