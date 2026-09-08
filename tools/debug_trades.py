"""Debug: find latest SELL in TRADES.md"""
with open('audit/TRADES.md') as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")
print(f"Last 10 lines:")
for i, line in enumerate(lines[-10:], len(lines)-9):
    print(f"  L{i}: repr={repr(line[:100])}")

print("\n--- Looking for SELL lines ---")
sell_count = 0
last_sell = None
for i, line in enumerate(lines):
    if ' SELL ' in line:
        sell_count += 1
        cols = line.split('|')
        stripped_cols = [c.strip() for c in cols]
        last_sell = (i, line, cols, stripped_cols)
        print(f"  L{i}: SELL found | cols_len={len(cols)} | cols[3]={repr(cols[3]) if len(cols)>3 else 'N/A'} | NO_TRADE={'NO TRADE' not in line}")

print(f"\nTotal SELL lines: {sell_count}")
print(f"\nLast SELL full detail:")
if last_sell:
    i, line, cols, scols = last_sell
    print(f"  Line: {i}")
    print(f"  Raw cols ({len(cols)}): {cols}")
    print(f"  Stripped cols ({len(scols)}): {scols}")
    print(f"  Condition check - len>=7: {len(cols) >= 7}, cols[3].strip()=='SELL': {cols[3].strip()=='SELL' if len(cols)>3 else False}")
