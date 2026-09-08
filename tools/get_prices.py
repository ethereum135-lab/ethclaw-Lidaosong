#!/usr/bin/env python3
"""Get prices for trading symbols"""
import requests, json

symbols = ['SUI','BCH','FIDA','ASTER','NEAR','HOME','FIL','FET','WLD','HIGH','DOGE','LAYER','ONDO','VIRTUAL','ZRO','UNI','XEC','OP','TIA','ORDI','DYM','STRK','PENDLE','ACH','CFX']
prices = {}
for sym in symbols:
    try:
        r = requests.get(f'https://api.binance.com/api/v3/ticker/price?symbol={sym}USDT', timeout=5)
        if r.status_code == 200:
            data = r.json()
            prices[sym] = float(data['price'])
        else:
            prices[sym] = None
            print(f'{sym}: HTTP {r.status_code}')
    except Exception as e:
        prices[sym] = None
        print(f'{sym}: {e}')

for sym in symbols:
    val = prices.get(sym)
    if val is not None:
        print(f'{sym}: ${val}')
    else:
        print(f'{sym}: N/A')
