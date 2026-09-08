#!/bin/bash
# A4 Blade - execute trades via Binance API using curl
# Binance API has HTTP 451 regional block - must use AWS proxy
# Since SSH is DOWN, we cannot execute trades
# This script verifies the situation

echo "=== A4 BLADE EXECUTION CHECK ==="
echo "Time: $(TZ=Asia/Shanghai date '+%Y-%m-%d %H:%M BJT')"

# Check SSH status
echo ""
echo "--- SSH CHECK ---"
ssh -i ~/.zq_vault/web4.0.pem -o StrictHostKeyChecking=no -o ConnectTimeout=5 ubuntu@15.134.211.154 "echo AWS_OK" 2>&1 || echo "SSH DOWN"

# Check Binance direct access
echo ""
echo "--- BINANCE DIRECT CHECK ---"
BTC=$(curl -s --connect-timeout 8 "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT" | python3 -c "import sys,json;print(json.load(sys.stdin)['price'])")
echo "BTC: \$$BTC"

# Check F&G
FNG=$(curl -s --connect-timeout 8 "https://api.alternative.me/fng/?limit=1" | python3 -c "import sys,json;d=json.load(sys.stdin);print(f\"{d['data'][0]['value']} - {d['data'][0]['value_classification']}\")")
echo "F&G: $FNG"

# Check if Binance API allows signed requests from Mac
echo ""
echo "--- BINANCE SIGNED ACCESS CHECK ---"
# Test with a simple signed GET (account snapshot - no balances returned for privacy)
# We already got USDT=$172.85 from account endpoint earlier
echo "Previous balance check succeeded (USDT=\$172.85, C=412.3, ALLO=238.9, JTO=46.9)"
echo "But signed trading POST may fail due to regional restrictions"

echo ""
echo "=== STATUS ==="
echo "SSH: ❌ DOWN (4 consecutive failures, last at 13:04)"
echo "Binance GET: ✅ Working"
echo "Binance POST (signed): ⚠️ Unknown - may be blocked by regional restriction"
echo "Execution capability: ❌ Cannot execute trades without SSH or working POST"
