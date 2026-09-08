#!/bin/bash
# A4 Blade - final trade execution: SELL C → BUY MEME
CONFIG="/Users/lidaosong/zq_web4_trading_system/config/auth.json"
API_KEY=$(python3 -c "import json;print(json.load(open('$CONFIG'))['binance']['api_key'])")
API_SECRET=$(python3 -c "import json;print(json.load(open('$CONFIG'))['binance']['api_secret'])")
BN="https://api.binance.com"
sign() { echo -n "$1" | openssl dgst -sha256 -hmac "$API_SECRET" | sed 's/^.* //'; }

echo "=== A4 BLADE EXECUTION ==="
echo "Time: $(TZ=Asia/Shanghai date '+%Y-%m-%d %H:%M BJT')"
echo ""

# Get fresh server time for each request
get_ts() { curl -s --connect-timeout 5 "$BN/api/v3/time" | python3 -c "import sys,json;print(json.load(sys.stdin)['serverTime'])" 2>/dev/null; }

# ── SELL C ──
echo "--- 1. SELL C 412.3 (rotate weakest) ---"
TS=$(get_ts)
echo "TS=$TS"
QS="newOrderRespType=FULL&quantity=412.3&recvWindow=10000&side=SELL&symbol=CUSDT&timestamp=$TS&type=MARKET"
SIG=$(sign "$QS")
SELL_RESP=$(curl -s --connect-timeout 10 --max-time 20 -X POST "$BN/api/v3/order" -H "X-MBX-APIKEY: $API_KEY" -d "$QS&signature=$SIG")
echo "Response: $SELL_RESP"
echo ""

# Parse result
python3 -c "
import json,sys
d=json.loads(sys.argv[1])
if 'code' in d:
    print(f'❌ FAIL({d[\"code\"]}): {d[\"msg\"]}')
    sys.exit(1)
qty=sum(float(f['qty']) for f in d.get('fills',[]))
avg=sum(float(f['qty'])*float(f['price']) for f in d.get('fills',[]))/qty if qty>0 else 0
cum=sum(float(f['qty'])*float(f['price']) for f in d.get('fills',[]))
print(f'✅ C sold: {qty:.2f} @ \${avg:.4f} = \${cum:.2f}')
print(f'SELL_AVG={avg}')
print(f'SELL_CUM={cum}')
" "$SELL_RESP"
SELL_OK=$?

# ── BUY MEME $25 ──
echo ""
echo "--- 2. BUY MEME \$25 ---"
TS2=$(get_ts)
echo "TS=$TS2"
QS2="newOrderRespType=FULL&quoteOrderQty=25.00&recvWindow=10000&side=BUY&symbol=MEMEUSDT&timestamp=$TS2&type=MARKET"
SIG2=$(sign "$QS2")
BUY_RESP=$(curl -s --connect-timeout 10 --max-time 20 -X POST "$BN/api/v3/order" -H "X-MBX-APIKEY: $API_KEY" -d "$QS2&signature=$SIG2")
echo "Response: $BUY_RESP"
echo ""

python3 -c "
import json,sys
d=json.loads(sys.argv[1])
if 'code' in d:
    print(f'❌ FAIL({d[\"code\"]}): {d[\"msg\"]}')
    sys.exit(1)
qty=sum(float(f['qty']) for f in d.get('fills',[]))
avg=sum(float(f['qty'])*float(f['price']) for f in d.get('fills',[]))/qty if qty>0 else 0
cum=sum(float(f['qty'])*float(f['price']) for f in d.get('fills',[]))
print(f'✅ MEME bought: {qty:.0f} @ \${avg:.6f} = \${cum:.2f}')
print(f'BUY_AVG={avg}')
print(f'BUY_QTY={qty}')
print(f'BUY_CUM={cum}')
" "$BUY_RESP"
BUY_OK=$?

echo ""
echo "=== RESULTS ==="
echo "SELL C: $([ $SELL_OK -eq 0 ] && echo '✅' || echo '❌')"
echo "BUY MEME: $([ $BUY_OK -eq 0 ] && echo '✅' || echo '❌')"
