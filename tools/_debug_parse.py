#!/usr/bin/env python3
"""Debug regex matching for node_check trade format."""
import re

# Test the regex against the actual line
line = '|| **SELL XPL** | 266.9 @ ~$0.0958 — weak consol/WATCH conf=4 gain=0.42% |'
line_clean = line.replace('**', '').strip()
parts = [p.strip() for p in line_clean.split('|')]
print('Parts:', parts)
print('Len:', len(parts))

# Find action+symbol
for i, p in enumerate(parts):
    m = re.match(r'^(SELL|BUY)\s+[A-Z0-9]+', p)
    if m:
        print(f'Match at i={i}: {m.group()}')
        action_symbol = m.group()
        details = parts[i+1] if i+1 < len(parts) else ''
        print(f'Details repr: {repr(details)}')
        
        # Test price regex with tilde support
        at_match = re.match(r'([\d.]+)\s*@\s*~?\$?([\d.]+)', details)
        if at_match:
            print(f'Price match: qty={at_match.group(1)}, price={at_match.group(2)}')
        else:
            print('NO PRICE MATCH')

# Test BUY line too
line2 = '|| **BUY STG** | 140.4 @ $0.2527 = $35.48 — USDTx15% — BUY_READY conf=9 |'
line_clean2 = line2.replace('**', '').strip()
parts2 = [p.strip() for p in line_clean2.split('|')]
print('\nParts2:', parts2)
for i, p in enumerate(parts2):
    m = re.match(r'^(SELL|BUY)\s+[A-Z0-9]+', p)
    if m:
        details2 = parts2[i+1] if i+1 < len(parts2) else ''
        print(f'Details2 repr: {repr(details2)}')
        at_match2 = re.match(r'([\d.]+)\s*@\s*~?\$?([\d.]+)', details2)
        if at_match2:
            print(f'Price match2: qty={at_match2.group(1)}, price={at_match2.group(2)}')
            after_at = details2[at_match2.end():]
            print(f'After @: [{after_at.strip().lstrip("-— ").strip()}]')

# Test DYM line
line3 = '|| **SELL DYM** | 239.5 @ ~$0.0175 — dust cleanup <$25 |'
line_clean3 = line3.replace('**', '').strip()
parts3 = [p.strip() for p in line_clean3.split('|')]
print('\nParts3:', parts3)
for i, p in enumerate(parts3):
    m = re.match(r'^(SELL|BUY)\s+[A-Z0-9]+', p)
    if m:
        details3 = parts3[i+1] if i+1 < len(parts3) else ''
        print(f'Details3 repr: {repr(details3)}')
        at_match3 = re.match(r'([\d.]+)\s*@\s*~?\$?([\d.]+)', details3)
        if at_match3:
            print(f'Price match3: qty={at_match3.group(1)}, price={at_match3.group(2)}')

# Test another sell
line4 = '|| **SELL UNI** | 1.22 @ ~$3.089 — dust cleanup <$25 (BUY_READY but too small) |'
line_clean4 = line4.replace('**', '').strip()
parts4 = [p.strip() for p in line_clean4.split('|')]
print('\nParts4:', parts4)
for i, p in enumerate(parts4):
    m = re.match(r'^(SELL|BUY)\s+[A-Z0-9]+', p)
    if m:
        details4 = parts4[i+1] if i+1 < len(parts4) else ''
        print(f'Details4 repr: {repr(details4)}')
        at_match4 = re.match(r'([\d.]+)\s*@\s*~?\$?([\d.]+)', details4)
        if at_match4:
            print(f'Price match4: qty={at_match4.group(1)}, price={at_match4.group(2)}')
