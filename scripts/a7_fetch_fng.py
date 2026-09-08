#!/usr/bin/env python3
"""Fetch F&G Index from Alternative.me"""
import json, urllib.request
try:
    resp = urllib.request.urlopen("https://api.alternative.me/fng/?limit=1", timeout=10)
    data = json.loads(resp.read())
    val = data['data'][0]['value']
    cls = data['data'][0]['value_classification']
    print(f"F&G: {val} ({cls})")
except Exception as e:
    print(f"F&G_FAILED: {e}")
