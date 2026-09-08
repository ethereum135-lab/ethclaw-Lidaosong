#!/bin/bash
# A4 买入 - 通过SOCKS5代理执行
# 用法: bash tools/a4_buy_socks5.sh <SYMBOL> <USDT_AMOUNT>

BINANCE="https://api.binance.com"
PROXY="--socks5-hostname 127.0.0.1:1080"
CONFIG="/Users/lidaosong/zq_web4_trading_system/config/auth.json"

API_KEY=$(python3 -c "import json;print(json.load(open('$CONFIG'))['binance']['api_key'])")
API_SECRET=$(python3 -c "import json;print(json.load(open('$CONFIG'))['binance']['api_secret'])")

SYMBOL="${1}USDT"
BUY_USDT="${2:-10}"

TS=$(date '+%Y-%m-%d %H:%M BJT')
echo "=== A4 BUY (SOCKS5) === $SYMBOL \$${BUY_USDT} @ $TS"

# 1. 获取账户信息
echo "--- 获取账户信息 ---"
ACCT_QS="omitZeroBalances=true&recvWindow=60000&timestamp=$(date +%s%N | cut -b1-13)"
ACCT_SIG=$(echo -n "$ACCT_QS" | openssl dgst -sha256 -hmac "$API_SECRET" | sed 's/^.* //')
ACCT=$(curl $PROXY -s --max-time 15 "$BINANCE/api/v3/account?$ACCT_QS&signature=$ACCT_SIG" -H "X-MBX-APIKEY: $API_KEY")
echo "$ACCT" | python3 -c "
import sys,json
d=json.load(sys.stdin)
if 'balances' in d:
    usdt=sum(float(b['free'])+float(b['locked']) for b in d['balances'] if b['asset']=='USDT')
    print(f'USDT: \${usdt:.2f}')
else:
    print(f'ERROR: {d.get(\"msg\",\"unknown\")}')
"

# 2. 获取LOT_SIZE和价格
echo "--- 获取交易规则 ---"
LOT_INFO=$(curl $PROXY -s --max-time 10 "$BINANCE/api/v3/exchangeInfo?symbol=$SYMBOL")
STEP=$(echo "$LOT_INFO" | python3 -c "
import sys,json
d=json.load(sys.stdin)
for f in d['symbols'][0]['filters']:
    if f['filterType']=='LOT_SIZE':
        print(f['stepSize'])
        break
")
MIN_QTY=$(echo "$LOT_INFO" | python3 -c "
import sys,json
d=json.load(sys.stdin)
for f in d['symbols'][0]['filters']:
    if f['filterType']=='LOT_SIZE':
        print(f['minQty'])
        break
")
MIN_NOTIONAL=$(echo "$LOT_INFO" | python3 -c "
import sys,json
d=json.load(sys.stdin)
for f in d['symbols'][0]['filters']:
    if f['filterType']=='MIN_NOTIONAL':
        print(f.get('minNotional',10))
        break
" 2>/dev/null || echo "10")
echo "LOT_SIZE step=$STEP min=$MIN_QTY min_notional=$MIN_NOTIONAL"

PRICE=$(curl $PROXY -s --max-time 10 "$BINANCE/api/v3/ticker/price?symbol=$SYMBOL" | python3 -c "import sys,json;print(json.load(sys.stdin)['price'])")
echo "Price: \$$PRICE"

# 3. 计算数量
RAW_QTY=$(echo "scale=8; $BUY_USDT / $PRICE" | bc)
# Round down to step size
QTY=$(echo "$RAW_QTY" | python3 -c "
import sys,math
q=float(sys.stdin.read().strip())
s=float('$STEP')
if s>0:
    precision=max(0,-int(math.floor(math.log10(s))))
    rounded=math.floor(q/s)*s
    print(f'{rounded:.{precision}f}')
else:
    print(q)
")
NOTIONAL=$(echo "$QTY * $PRICE" | bc)
echo "Buy qty: $QTY (≈\$$NOTIONAL)"

# Check if qty meets minimums
MIN_OK=$(echo "$QTY >= $MIN_QTY" | bc 2>/dev/null || echo "0")
NOTIONAL_OK=$(echo "$NOTIONAL >= $MIN_NOTIONAL" | bc 2>/dev/null || echo "0")

if [ "$MIN_OK" != "1" ] || [ "$NOTIONAL_OK" != "1" ]; then
    echo "❌ 数量不足: qty=$QTY < min_qty=$MIN_QTY 或 notional=\$$NOTIONAL < \$$MIN_NOTIONAL"
    echo "❗ 改用quoteOrderQty方式"
    # Use quoteOrderQty for MARKET BUY
    TS2=$(date +%s%N | cut -b1-13)
    POST_QS="newOrderRespType=FULL&quoteOrderQty=$BUY_USDT&recvWindow=60000&side=BUY&symbol=$SYMBOL&timestamp=$TS2&type=MARKET"
    POST_SIG=$(echo -n "$POST_QS" | openssl dgst -sha256 -hmac "$API_SECRET" | sed 's/^.* //')
    BUY_RESP=$(curl $PROXY -s --max-time 15 -X POST "$BINANCE/api/v3/order" \
        -H "X-MBX-APIKEY: $API_KEY" \
        -d "$POST_QS&signature=$POST_SIG")
else
    # Standard quantity-based MARKET BUY
    TS2=$(date +%s%N | cut -b1-13)
    POST_QS="newOrderRespType=FULL&quantity=$QTY&recvWindow=60000&side=BUY&symbol=$SYMBOL&timestamp=$TS2&type=MARKET"
    POST_SIG=$(echo -n "$POST_QS" | openssl dgst -sha256 -hmac "$API_SECRET" | sed 's/^.* //')
    BUY_RESP=$(curl $PROXY -s --max-time 15 -X POST "$BINANCE/api/v3/order" \
        -H "X-MBX-APIKEY: $API_KEY" \
        -d "$POST_QS&signature=$POST_SIG")
fi

echo "--- 执行结果 ---"
echo "$BUY_RESP" | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin)
    if 'code' in d:
        print(f'❌ FAIL({d[\"code\"]}): {d[\"msg\"]}')
    else:
        qty=float(d.get('executedQty',0))
        cost=float(d.get('cummulativeQuoteQty',0))
        avg=cost/qty if qty>0 else 0
        fills_qty=sum(float(f['qty']) for f in d.get('fills',[]))
        print(f'✅ 买入成功! {fills_qty:.6f} @ \${avg:.4f} = \${cost:.2f}')
        print(f'状态: {d.get(\"status\",\"?\")}')
except Exception as e:
    print(f'❌ 解析失败: {e}')
"

# 4. 验证余额
echo ""
echo "--- 余额验证 ---"
sleep 1
ACCT2_QS="omitZeroBalances=true&recvWindow=60000&timestamp=$(date +%s%N | cut -b1-13)"
ACCT2_SIG=$(echo -n "$ACCT2_QS" | openssl dgst -sha256 -hmac "$API_SECRET" | sed 's/^.* //')
ACCT2=$(curl $PROXY -s --max-time 15 "$BINANCE/api/v3/account?$ACCT2_QS&signature=$ACCT2_SIG" -H "X-MBX-APIKEY: $API_KEY")
echo "$ACCT2" | python3 -c "
import sys,json
d=json.load(sys.stdin)
if 'balances' in d:
    base='${SYMBOL%USDT}'
    usdt=sum(float(b['free'])+float(b['locked']) for b in d['balances'] if b['asset']=='USDT')
    qty=sum(float(b['free']) for b in d['balances'] if b['asset']==base)
    print(f'USDT: \${usdt:.2f}')
    print(f'{base}: {qty:.6f}')
"

echo ""
echo "=== DONE ==="
