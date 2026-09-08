#!/bin/bash
# A4 Blade - full trade execution
CONFIG="/Users/lidaosong/zq_web4_trading_system/config/auth.json"
API_KEY=$(python3 -c "import json;print(json.load(open('$CONFIG'))['binance']['api_key'])")
API_SECRET=$(python3 -c "import json;print(json.load(open('$CONFIG'))['binance']['api_secret'])")
BN="https://api.binance.com"

sign() { echo -n "$1" | openssl dgst -sha256 -hmac "$API_SECRET" | sed 's/^.* //'; }

echo "=== A4 BLADE EXECUTION ==="
echo "Time: $(TZ=Asia/Shanghai date '+%Y-%m-%d %H:%M BJT')"

TS=$(curl -s "$BN/api/v3/time" | python3 -c "import sys,json;print(json.load(sys.stdin)['serverTime'])")

# ── SELL C (412.3026) ──
echo ""
echo "--- SELL C (rotate out weakest) ---"
QS1="newOrderRespType=FULL&quantity=412.3026&recvWindow=5000&side=SELL&symbol=CUSDT&timestamp=$TS&type=MARKET"
SIG1=$(sign "$QS1")
SELL=$(curl -s --connect-timeout 8 --max-time 15 -X POST "$BN/api/v3/order" -H "X-MBX-APIKEY: $API_KEY" -d "$QS1&signature=$SIG1")
echo "SELL C: $SELL"

# Extract sell details
python3 -c "
import json,sys
d=json.load(sys.stdin)
if 'code' in d:
    print(f'❌ FAIL({d[\"code\"]}): {d[\"msg\"]}')
    sys.exit(1)
qty=sum(float(f['qty']) for f in d.get('fills',[]))
avg=sum(float(f['qty'])*float(f['price']) for f in d.get('fills',[]))/qty if qty>0 else 0
print(f'✅ C sold: {qty:.2f} @ \${avg:.4f} = \${qty*avg:.2f}')
print(f'SELL_PRICE={avg}')
print(f'SELL_QTY={qty}')
print(f'SELL_TOTAL={qty*avg}')
" <<< "$SELL"

# ── BUY MDX $25 ──
echo ""
echo "--- BUY MDX \$25 ---"
TS2=$((TS + 1000))
QS2="newOrderRespType=FULL&quoteOrderQty=25.00&recvWindow=5000&side=BUY&symbol=MDXUSDT&timestamp=$TS2&type=MARKET"
SIG2=$(sign "$QS2")
BUY=$(curl -s --connect-timeout 8 --max-time 15 -X POST "$BN/api/v3/order" -H "X-MBX-APIKEY: $API_KEY" -d "$QS2&signature=$SIG2")
echo "BUY MDX: $BUY"

python3 -c "
import json,sys
d=json.load(sys.stdin)
if 'code' in d:
    print(f'❌ FAIL({d[\"code\"]}): {d[\"msg\"]}')
    sys.exit(1)
qty=sum(float(f['qty']) for f in d.get('fills',[]))
avg=sum(float(f['qty'])*float(f['price']) for f in d.get('fills',[]))/qty if qty>0 else 0
print(f'✅ MDX bought: {qty:.2f} @ \${avg:.6f} = \${qty*avg:.2f}')
print(f'BUY_PRICE={avg}')
print(f'BUY_QTY={qty}')
print(f'BUY_TOTAL={qty*avg}')
" <<< "$BUY"

echo ""
echo "=== DONE ==="
