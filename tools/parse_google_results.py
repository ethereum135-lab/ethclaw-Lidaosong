#!/usr/bin/env python3
"""Parse Google search results HTML file."""
import sys
import re

try:
    with open(sys.argv[1], 'r') as f:
        content = f.read()
except:
    print("Could not read file")
    sys.exit(1)

# Try extracting h3 tags (modern Google)
results = re.findall(r'<h3[^>]*>(.*?)</h3>', content, re.DOTALL)
for i, r in enumerate(results[:10]):
    clean = re.sub(r'<[^>]+>', '', r).strip()
    if clean:
        print(f'{i+1}. {clean}')

if not results:
    # Try BNeawe spans
    results2 = re.findall(r'<span[^>]*class="[^"]*BNeawe[^"]*"[^>]*>(.*?)</span>', content, re.DOTALL)
    for i, r in enumerate(results2[:10]):
        clean = re.sub(r'<[^>]+>', '', r).strip()
        if len(clean) > 20:
            print(f'{i+1}. {clean}')

if not results and not results2:
    print(f"No structured results found. Content length: {len(content)}")
