#!/usr/bin/env python3
"""Get prices for key holdings"""
import requests

# Key positions from Binance account
key = {
    'CUSDT': 'C',
    'JTOUSDT': 'JTO', 
    'ALLOUSDT': 'ALLO',
    'DYMUSDT': 'DYM',
    'NEARUSDT': 'NEAR',
    'ONDOUSDT': 'ONDO',
    'WLDUSDT': 'WLD',
    'ENAUSDT': 'ENA',
    'MEMEUSDT': 'MEME',
    'BTCUSDT': 'BTC'
}

for sym, name in key.items():
    r = requests.get(f'https://api.binance.com/api/v3/ticker/price?symbol={sym}', timeout=5)
    if r.status_code == 200:
        print(f"{sym}: ${float(r.json()['price']):.6f}")
