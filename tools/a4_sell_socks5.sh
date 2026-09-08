#!/bin/bash
# A4 卖出 - 通过SOCKS5代理执行
# 用法: bash tools/a4_sell_socks5.sh <SYMBOL> [pct=100]

BINANCE="https://api.binance.com"
PROXY="--socks5-hostname 127.0.0.1:1080"
CONFIG="/Users/lidaosong/zq_web4_trading_system/config/auth.json"

API_KEY=$(python3 -c "import json;print(json.load(open('$CONFIG'))['binance']['api_key'])")
API_SECRET=$(python3 -c "import json;print(json.load(open('$CONFIG'))['binance']['api_secret'])")

SYMBOL="${1:-SYN}USDT"
PCT="${2:-100}"

TS=$(date '+%Y-%m-%d %H:%M BJT')
echo "=== A4 SELL (SOCKS5) === $SYMBOL ${PCT}% @ $TS"

# 1. 获取账户信息 → 查持仓
echo "--- 获取账户信息 ---"
ACCT_QS="omitZeroBalances=true&recvWindow=60000&timestamp=$(date +%s%N | cut -b1-13)"
ACCT_SIG=$(echo -n "$ACCT_QS" | openssl dgst -sha256 -hmac "$API_SECRET" | sed 's/^.* //')
ACCT=$(curl $PROXY -s --max-time 15 "$BINANCE/api/v3/account?$ACCT_QS&signature=$ACCT_SIG" -H "X-MBX-APIKEY: $API_KEY")
echo "$ACCT" | python3 -c "
import sys,json
d=json.load(sys.stdin)
if 'balances' in d:
    base='${SYMBOL%USDT}'
    usdt=0
    qty=0
    for b in d['balances']:
        if b['asset']=='USDT': usdt=float(b['free'])+float(b['locked'])
        if b['asset']==base: qty=float(b['free'])
    print(f'USDT: \${usdt:.2f} | {base}: {qty:.6f}')
else:
    print(f'ERROR: {d.get(\"msg\", \"unknown\")}')
"

# 2. 获取最新价格
PRICE=$(curl $PROXY -s --max-time 10 "$BINANCE/api/v3/ticker/price?symbol=$SYMBOL" | python3 -c "import sys,json;print(json.load(sys.stdin)['price'])")
echo "Price: \$$PRICE"

# 3. 获取持仓数量
QTY=$(echo "$ACCT" | python3 -c "
import sys,json
d=json.load(sys.stdin)
base='${SYMBOL%USDT}'
for b in d['balances']:
    if b['asset']==base:
        print(b['free'])
        break
")
echo "Qty: $QTY"

if [ -z "$QTY" ] || [ "$QTY" = "0" ] || [ "$(echo "$QTY <= 0" | bc 2>/dev/null)" = "1" ] || [ "$QTY" = "0.00000000" ]; then
    echo "❌ 没有持仓，跳过卖出"
    exit 0
fi

# 4. 获取LOT_SIZE
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
echo "LOT_SIZE step=$STEP min=$MIN_QTY"

# 5. 计算卖出数量
if [ "$PCT" = "100" ]; then
    SELL_QTY=$(echo "scale=8; $QTY" | bc)
else
    SELL_QTY=$(echo "scale=8; $QTY * $PCT / 100" | bc)
fi
# Round down to step size
SELL_QTY=$(echo "$SELL_QTY" | python3 -c "
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
echo "Sell qty: $SELL_QTY"

# Check min
MIN_OK=$(echo "$SELL_QTY >= $MIN_QTY" | bc 2>/dev/null || echo "0")
if [ "$MIN_OK" != "1" ]; then
    echo "❌ 数量 $SELL_QTY < 最小 $MIN_QTY"
    exit 1
fi

# 6. 执行卖出
echo "--- 执行卖出 ---"
TS2=$(date +%s%N | cut -b1-13)
POST_QS="newOrderRespType=FULL&quantity=$SELL_QTY&recvWindow=60000&side=SELL&symbol=$SYMBOL&timestamp=$TS2&type=MARKET"
POST_SIG=$(echo -n "$POST_QS" | openssl dgst -sha256 -hmac "$API_SECRET" | sed 's/^.* //')
SELL_RESP=$(curl $PROXY -s --max-time 15 -X POST "$BINANCE/api/v3/order" \
    -H "X-MBX-APIKEY: $API_KEY" \
    -d "$POST_QS&signature=$POST_SIG")

echo "$SELL_RESP" | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin)
    if 'code' in d:
        print(f'❌ FAIL({d[\"code\"]}): {d[\"msg\"]}')
    else:
        qty=sum(float(f['qty']) for f in d.get('fills',[]))
        cost=float(d.get('cummulativeQuoteQty',0))
        avg=cost/qty if qty>0 else 0
        print(f'✅ 卖出成功! {qty:.6f} @ \${avg:.4f} = \${cost:.2f}')
        print(f'状态: {d.get(\"status\",\"?\")}')
except Exception as e:
    print(f'❌ 解析失败: {e}')
    print(sys.stdin.read()[:200])
"

# 7. 验证余额
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
    usdt=0
    qty=0
    for b in d['balances']:
        if b['asset']=='USDT': usdt=float(b['free'])+float(b['locked'])
        if b['asset']==base: qty=float(b['free'])
    print(f'USDT: \${usdt:.2f}')
    print(f'{base}: {qty:.6f} (剩余)')
"

echo ""
echo "=== DONE ==="
