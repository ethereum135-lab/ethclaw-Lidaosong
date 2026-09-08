#!/bin/bash
# Minimal trade execution test
CONFIG="/Users/lidaosong/zq_web4_trading_system/config/auth.json"
API_KEY=$(python3 -c "import json;print(json.load(open('$CONFIG'))['binance']['api_key'])")
API_SECRET=$(python3 -c "import json;print(json.load(open('$CONFIG'))['binance']['api_secret'])")

TS=$(curl -s "https://api.binance.com/api/v3/time" | python3 -c "import sys,json;print(json.load(sys.stdin)['serverTime'])")

# Try SELL C (small test quantity)
QS="newOrderRespType=FULL&quantity=0.1&recvWindow=5000&side=SELL&symbol=CUSDT&timestamp=$TS&type=MARKET"
SIG=$(echo -n "$QS" | openssl dgst -sha256 -hmac "$API_SECRET" | sed 's/^.* //')

echo "Testing SELL 0.1 C..."
RESP=$(curl -s --connect-timeout 8 --max-time 15 -X POST "https://api.binance.com/api/v3/order" \
    -H "X-MBX-APIKEY: $API_KEY" \
    -d "$QS&signature=$SIG")
echo "Response: $RESP" | head -5
echo "HTTP: $(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 8 --max-time 15 -X POST "https://api.binance.com/api/v3/order" \
    -H "X-MBX-APIKEY: $API_KEY" \
    -d "$QS&signature=$SIG")"
