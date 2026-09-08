#!/usr/bin/env python3
"""Behavior test: MIN_NOTIONAL -> convert fallback in execute_sell (mocked, no real orders)."""
import sys, json
sys.path.insert(0, '/home/ubuntu/zq_web4_trading_system/production/engine')
import a4_independent as a4
from unittest.mock import patch

# Mock sell_market -> MIN_NOTIONAL, convert -> FILLED
with patch.object(a4, 'sell_market', return_value={"error": "订单价值$4.02低于最低$5", "code": "MIN_NOTIONAL", "price": 0.699}), \
     patch.object(a4, 'convert_dust_to_usdt', return_value={"status": "FILLED", "convert": True, "toAmount": "3.986", "orderId": "TEST123"}), \
     patch.object(a4, 'append_trades_line', lambda line: print("TRADE_LINE_OK:", "状态 | ✅ FILLED" in line)):
    res = a4.execute_sell({"coin": "MOVR", "quantity": 5.75, "reason": "TEST尘仓", "pnl_pct": "-5"}, "k", "s")
    print("RESULT:", json.dumps(res, ensure_ascii=False))
    assert res["status"] == "FILLED", f"expected FILLED got {res['status']}"
    assert abs(res["exec_price"] - 3.986/5.75) < 1e-6, f"exec_price wrong: {res['exec_price']}"
    print("PASS: MIN_NOTIONAL -> Convert fallback works, exec_price computed")

# Edge: convert fails -> REJECTED_CONVERT_NO_QUOTE, no crash
with patch.object(a4, 'sell_market', return_value={"error": "订单价值$4.02低于最低$5", "code": "MIN_NOTIONAL"}), \
     patch.object(a4, 'convert_dust_to_usdt', return_value={"error": "Convert getQuote失败", "code": "CONVERT_NO_QUOTE"}), \
     patch.object(a4, 'append_trades_line', lambda line: None):
    res = a4.execute_sell({"coin": "NFP", "quantity": 691.52, "reason": "TEST", "pnl_pct": "-66"}, "k", "s")
    print("EDGE RESULT:", res["status"])
    assert res["status"] == "REJECTED_CONVERT_NO_QUOTE"
    print("PASS: convert failure -> graceful REJECTED")
