#!/bin/bash
# A4 Blade - execute trades using curl + openssl for signing

BINANCE="https://api.binance.com"
CONFIG="/Users/lidaosong/zq_web4_trading_system/config/auth.json"

# Read API keys
API_KEY=$(python3 -c "import json;print(json.load(open('$CONFIG'))['binance']['api_key'])")
API_SECRET=$(python3 -c "import json;print(json.load(open('$CONFIG'))['binance']['api_secret'])")

echo "=== A4 BLADE EXECUTION ==="
echo "Time: $(TZ=Asia/Shanghai date '+%Y-%m-%d %H:%M BJT')"

# Get prices
BTC=$(curl -s --connect-timeout 8 "$BINANCE/api/v3/ticker/price?symbol=BTCUSDT" | python3 -c "import sys,json;print(json.load(sys.stdin)['price'])")
C=$(curl -s --connect-timeout 8 "$BINANCE/api/v3/ticker/price?symbol=CUSDT" | python3 -c "import sys,json;print(json.load(sys.stdin)['price'])")
MDX=$(curl -s --connect-timeout 8 "$BINANCE/api/v3/ticker/price?symbol=MDXUSDT" | python3 -c "import sys,json;print(json.load(sys.stdin)['price'])")
ALLO=$(curl -s --connect-timeout 8 "$BINANCE/api/v3/ticker/price?symbol=ALLOUSDT" | python3 -c "import sys,json;print(json.load(sys.stdin)['price'])")
JTO=$(curl -s --connect-timeout 8 "$BINANCE/api/v3/ticker/price?symbol=JTOUSDT" | python3 -c "import sys,json;print(json.load(sys.stdin)['price'])")

echo "BTC: \$$BTC"
echo "C: \$$C | ALLO: \$$ALLO | JTO: \$$JTO | MDX: \$$MDX"

# Get server time
SERVER_TIME=$(curl -s "$BINANCE/api/v3/time" | python3 -c "import sys,json;print(json.load(sys.stdin)['serverTime'])")
echo "Server time: $SERVER_TIME"

calc_sign() {
    local qs="$1"
    echo -n "$qs" | openssl dgst -sha256 -hmac "$API_SECRET" | sed 's/^.* //'
}

# Test signed GET: account info
echo ""
echo "--- TEST: Signed Account Query ---"
TS=$SERVER_TIME
QS="omitZeroBalances=true&recvWindow=5000&timestamp=$TS"
SIG=$(calc_sign "$QS")
ACCT_RESP=$(curl -s --connect-timeout 10 "$BINANCE/api/v3/account?$QS&signature=$SIG" -H "X-MBX-APIKEY: $API_KEY")
ACCT_CODE=$(echo "$ACCT_RESP" | python3 -c "import sys,json;d=json.load(sys.stdin);print('OK' if 'balances' in d else d.get('msg','UNKNOWN'))" 2>/dev/null)
echo "Account query: $ACCT_CODE"

if [ "$ACCT_CODE" = "OK" ]; then
    USDT=$(echo "$ACCT_RESP" | python3 -c "
import sys,json
d=json.load(sys.stdin)
for b in d['balances']:
    if b['asset']=='USDT':
        f=float(b['free'])
        l=float(b['locked'])
        print(f'{f+l:.2f}')
        break
")
    echo "USDT balance: \$$USDT"
fi

# Test signed POST: try a market sell of C
echo ""
echo "--- EXECUTE: SELL C (rotate out weakest) ---"
# C: 412.3026 tokens, round to LOT_SIZE
C_QTY=$(echo "$ACCT_RESP" | python3 -c "
import sys,json
d=json.load(sys.stdin)
for b in d['balances']:
    if b['asset']=='C':
        print(b['free'])
        break
" 2>/dev/null)
echo "C balance: $C_QTY"

# Try POST with data format
TS2=$(( SERVER_TIME + 1000 ))
POST_QS="newOrderRespType=FULL&quantity=412.3&recvWindow=5000&side=SELL&symbol=CUSDT&timestamp=$TS2&type=MARKET"
POST_SIG=$(calc_sign "$POST_QS")
SELL_RESP=$(curl -s --connect-timeout 10 -X POST "$BINANCE/api/v3/order" \
    -H "X-MBX-APIKEY: $API_KEY" \
    -d "$POST_QS&signature=$POST_SIG")
echo "SELL C response: $SELL_RESP"

SELL_STATUS=$(echo "$SELL_RESP" | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin)
    if 'code' in d:
        print(f\"FAIL({d['code']}): {d['msg']}\")
    else:
        qty=sum(float(f['qty']) for f in d.get('fills',[]))
        avg=sum(float(f['qty'])*float(f['price']) for f in d.get('fills',[]))/qty if qty>0 else 0
        print(f\"OK {qty:.2f} @ \${avg:.4f} = \${qty*avg:.2f}\")
except:
    print('PARSE_ERROR: ' + sys.stdin.read()[:200])
" 2>/dev/null)
echo "SELL C: $SELL_STATUS"

if echo "$SELL_STATUS" | grep -q "^OK"; then
    C_SELL_OK="yes"
    SELL_QTY=$(echo "$SELL_STATUS" | cut -d' ' -f2)
    SELL_PRICE=$(echo "$SELL_STATUS" | cut -d' ' -f4 | tr -d '$')
    SELL_TOTAL=$(echo "$SELL_STATUS" | cut -d' ' -f6 | tr -d '$')
fi

# Execute BUY MDX $25
echo ""
echo "--- EXECUTE: BUY MDX \$25 ---"
TS3=$(( SERVER_TIME + 2000 ))
BUY_QS="newOrderRespType=FULL&quoteOrderQty=25.00&recvWindow=5000&side=BUY&symbol=MDXUSDT&timestamp=$TS3&type=MARKET"
BUY_SIG=$(calc_sign "$BUY_QS")
BUY_RESP=$(curl -s --connect-timeout 10 -X POST "$BINANCE/api/v3/order" \
    -H "X-MBX-APIKEY: $API_KEY" \
    -d "$BUY_QS&signature=$BUY_SIG")
echo "BUY MDX response: $BUY_RESP"

BUY_STATUS=$(echo "$BUY_RESP" | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin)
    if 'code' in d:
        print(f\"FAIL({d['code']}): {d['msg']}\")
    else:
        qty=sum(float(f['qty']) for f in d.get('fills',[]))
        avg=sum(float(f['qty'])*float(f['price']) for f in d.get('fills',[]))/qty if qty>0 else 0
        print(f\"OK {qty:.2f} @ \${avg:.6f} = \${qty*avg:.2f}\")
except:
    print('PARSE_ERROR')
" 2>/dev/null)
echo "BUY MDX: $BUY_STATUS"

echo ""
echo "=== EXECUTION COMPLETE ==="
