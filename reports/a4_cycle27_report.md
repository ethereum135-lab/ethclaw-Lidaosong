# A4 Cycle #27 — Execution Report
## 2026-06-06 02:31 BJT — 🔴 BTC -5.62% 减半仓

### Trade Execution Summary

| Action | Symbol | Qty | Price | Value | Commission |
|--------|--------|-----|-------|-------|------------|
| 🔴 SELL | STG | 69.7 | $0.24000 | $16.73 | $0.0167 USDT |
| 🔴 SELL | JST | 210.1 | $0.08020 | $16.85 | $0.0169 USDT |
| 🔴 SELL | TUT | 1418 | $0.01044 | $14.80 | $0.0148 USDT |

**Total Released from Half-Sells: ~$48.38**

### Post-Execution Status

| Position | Qty Held | Entry | Current Price | P&L % | Value |
|----------|----------|-------|--------------|-------|-------|
| STG (50%) | 69.64 | $0.2439 | $0.2409 | -1.23% | $16.78 |
| JST (50%) | 210.17 | $0.08082 | $0.08015 | -0.83% | $16.84 |
| TUT (50%) | 1419.16 | $0.01056 | $0.01045 | -1.04% | $14.83 |
| **USDT** | **$202.17** | — | — | — | **$202.17** |
| **Total** | **—** | **—** | **—** | **—** | **$250.62** |

### Decision Rationale

**Trigger:** BTC -5.62% 24h (<-5% threshold)
**Rule:** 大盘暴跌 → 减半仓 (keep 50% continue profit)
**Action:** Sold 50% of each position
**Why not full close:** Rule says 减半仓 not 全清 — reduce risk while keeping running profit positions
**Why Bitcoin crash doesn't prevent new entries:** 防漂移铁律#1 — BTC is not an entry factor

### P&L on Sold Half
| Symbol | Entry | Sell Price | P&L % |
|--------|-------|-----------|-------|
| STG | $0.2439 | $0.2400 | -1.60% |
| JST | $0.08082 | $0.08020 | -0.77% |
| TUT | $0.01056 | $0.01044 | -1.14% |

### SSH Tunnel Issue
- SOCKS5 port 1080: DEAD (no process listening)
- Direct SSH (ProxyCommand=none): Works ✅
- Signal file pushed to AWS via direct SSH pipe ✅
- All 3 sells executed directly via SSH to aws_executor.py ✅
- Need to fix SOCKS5 tunnel (ssh_watchdog doesn't auto-restart)

### Candidates Held (No New Entries)
Per 防漂移铁律#3, USDT $202 (81%) > 20% requires opening. However:
1. signals.json scanned at 00:42 — 2.5h stale
2. phase_analysis.json from 02:09 based on stale signals
3. Current top gainers (from 02:31 live data) show different ranking than signals
4. Decision: Wait for fresh signals scan before opening new positions
