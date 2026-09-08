#!/usr/bin/env python3
"""Fetch Fear & Greed Index from alternative.me"""
import json, urllib.request

try:
    req = urllib.request.Request("https://api.alternative.me/fng/?limit=1",
                                 headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        d = json.loads(resp.read())
    item = d["data"][0]
    print(f"value={item['value']}")
    print(f"classification={item['value_classification']}")
    print(f"timestamp={item['timestamp']}")
except Exception as e:
    print(f"ERROR: {e}")
