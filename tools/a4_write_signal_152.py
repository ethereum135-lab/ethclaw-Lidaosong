#!/usr/bin/env python3
"""Write A4 cycle #152 a4_signals.json"""
import json, os
from datetime import datetime

signal = {
    "signal_id": "sig_20260609_0130_152",
    "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00"),
    "a4_cycle": "2026-06-09 01:30 BJT",
    "sequence": 152,
    "buy_signals": [],
    "sell_signals": [],
    "position_eval": {
        "positions_count": 3,
        "usdt_balance": 65.64,
        "action_summary": "ALL_HOLD_NOOP",
        "reason": "3满位+PARTI浮亏-2.5%→有亏损仓位不轮换·BUY_READY14候选(最佳WLDconf10+4.1%/NXPCconf10+8.35%/ONDOconf9+7.7%/NEARconf9+9.6%)但USDT$65.64(24%>20%铁律冲突→规则优先级:3满+亏损不轮换覆盖防漂移)"
    },
    "hold_positions": [
        {"coin": "ZEC", "value_usd": 105, "phase": "just_starting", "action": "BUY_READY", "score": 88, "24h_gain": 7.07},
        {"coin": "TON", "value_usd": 52, "phase": "just_starting", "action": "BUY_READY", "score": 94, "24h_gain": 1.1},
        {"coin": "PARTI", "value_usd": 34, "pnl_pct": -2.5, "hard_stop": -5.0, "24h_change": -6.67}
    ],
    "best_candidates": [
        {"coin": "WLD", "conf": 10, "gain_24h": 4.1, "score": 106, "phase": "just_starting", "tags": "A7+A8"},
        {"coin": "NXPC", "conf": 10, "gain_24h": 8.35, "score": 71, "phase": "just_starting", "tags": "A7+"},
        {"coin": "ONDO", "conf": 9, "gain_24h": 7.74, "score": 102, "phase": "just_starting", "tags": "A7+A8"},
        {"coin": "NEAR", "conf": 9, "gain_24h": 9.62, "score": 91, "phase": "just_starting", "tags": "A7+A8"}
    ],
    "tags_context": {
        "a3_report_date": None,
        "phase_analysis_at": "2026-06-09 01:22",
        "quick_buy_at": "2026-06-09 01:25",
        "btc_price": 63666,
        "fng": 12
    }
}

os.makedirs("data/signals", exist_ok=True)
with open("data/signals/a4_signals.json", "w") as f:
    json.dump(signal, f, indent=2, ensure_ascii=False)
print(f"✅ a4_signals.json written (seq={signal['sequence']}, NOOP)")
