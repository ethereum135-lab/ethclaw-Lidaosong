# Position Sizing, Risk Management & The Mathematics of Not Going Broke

## A Practical Guide for a $200 Crypto Account

---

## 1. Risk of Ruin Formula

**Definition:** The probability of losing your entire account before reaching a target.

### Classic Formula (Fixed Fraction Betting):
```
RoR = ((1 - Edge) / (1 + Edge))^Units
```
Where `Edge = Win probability - Loss probability` (for even-money bets)

### Practical Trading Version:
```
RoR = ((1 - W) / W)^(Account / Risk_per_trade)
```
Where:
- **W** = Win rate (decimal, e.g. 0.55 for 55%)
- **Account** = Total capital ($200)
- **Risk_per_trade** = Dollar amount risked per trade

### Concrete Examples for $200:

| Win Rate | Risk/Trade | RoR Calculation | Result |
|----------|-----------|-----------------|--------|
| 55% | $4 (2%) | (0.45/0.55)^(200/4) = (0.818)^50 | **0.005%** (essentially zero) |
| 50% | $4 (2%) | (0.50/0.50)^(200/4) = (1)^50 | **1.0** (certain ruin without edge) |
| 45% | $4 (2%) | (0.55/0.45)^(200/4) = (1.222)^50 | **~10,000+** (certain ruin) |
| 40% | $4 (2%) | (0.60/0.40)^(200/4) = (1.5)^50 | **~637,000,000** (certain ruin) |
| 40% | $10 (5%) | (0.60/0.40)^(200/10) = (1.5)^20 | **3,325** (certain, rapid ruin) |
| 55% | $10 (5%) | (0.45/0.55)^(200/10) = (0.818)^20 | **1.3%** (manageable) |
| 55% | $20 (10%) | (0.45/0.55)^(200/20) = (0.818)^10 | **13.4%** (high risk) |

### Key Insight:
If your win rate is below the risk/reward-adjusted breakeven point, ruin is **mathematically certain** — it's not a question of if, but when.

**Breakeven Win Rate = Risk / (Risk + Reward)**

| R/R Ratio | Breakeven Win Rate |
|-----------|-------------------|
| 1:1 | 50.0% |
| 1:1.5 | 40.0% |
| 1:2 | 33.3% |
| 1:3 | 25.0% |

---

## 2. Kelly Criterion — Optimal Position Sizing

**Formula:**
```
f* = (bp - q) / b
```
Where:
- **f*** = Fraction of capital to risk
- **b** = Net odds received (reward/risk ratio)
- **p** = Probability of winning
- **q** = Probability of losing (1-p)

### Examples:

| Win Rate | R/R | Full Kelly | Half Kelly | Quarter Kelly (Conservative) |
|----------|-----|-----------|------------------------|-----------------------------|
| 55% | 1:1 | 10% ($20) | 5% ($10) | 2.5% ($5) |
| 50% | 1:1 | 0% ($0) | 0% ($0) | 0% ($0) |
| 50% | 1:1.5 | 16.7% ($33) | 8.3% ($17) | 4.2% ($8) |
| 45% | 1:2 | 17.5% ($35) | 8.75% ($17.50) | 4.4% ($8.80) |
| 40% | 1:2 | 10% ($20) | 5% ($10) | 2.5% ($5) |
| 40% | 1:3 | 20% ($40) | 10% ($20) | 5% ($10) |
| 30% | 1:3 | 6.7% ($13) | 3.3% ($6.70) | 1.7% ($3.40) |

**Key rule:** Never bet more than 2% of account per trade for survival, even if Kelly says >2%. The **Kelly Criterion is an upper bound, not a target** — fractional Kelly (0.25x) is the professional standard.

---

## 3. Achievable Win Rates & Risk/Reward for Small Accounts

### Professional Benchmarks:
- **Day trading (equities):** 50-60% win rate, 1:1 to 1:1.5 R/R
- **Trend following:** 35-45% win rate, 1:2 to 1:4 R/R
- **Crypto retail (studies):** Typically **<45% win rate**, with **70-80% of traders losing money**
- **Statistical edge in crypto:** Very difficult to maintain consistently

### Realistic Expectations for $200:
| Trader Type | Win Rate | R/R | Notes |
|------------|----------|-----|-------|
| Scalper | 55-60% | 1:1 | Very hard to maintain, fee-sensitive |
| Scalper (realistic) | 50-52% | 1:1 | Breakeven at best for most |
| Swing Trader | 40-45% | 1:2 | Depends on market conditions |
| Momentum Trader | 40-50% | 1:1.5 | Win rate drops during low volatility |

### The Math of Losing Streaks:
Starting with $200, how consecutive losses destroy you:

| Risk/Trade | After 5 Losses | After 10 Losses | After 15 Losses |
|------------|---------------|----------------|----------------|
| 1% ($2) | $190.20 | **$180.86** | $171.93 |
| 2% ($4) | **$180.39** | **$163.41** | $147.47 |
| 5% ($10) | **$154.69** | **$119.73** | $92.66 |
| 10% ($20) | **$118.10** | **$69.74** | $41.18 |
| 15% ($30) | **$88.68** | **$39.35** | $17.45 |
| 20% ($40) | **$65.54** | **$21.47** | $7.04 |

**Probability of consecutive losing streak:**

| Streak Length | At 55% Win Rate | At 50% Win Rate | At 45% Win Rate | At 40% Win Rate |
|--------------|----------------|----------------|----------------|----------------|
| 5 | 1 in 56 | 1 in 32 | 1 in 19 | 1 in 13 |
| 7 | 1 in 357 | 1 in 128 | 1 in 53 | 1 in 27 |
| 10 | **1 in 2,944** | **1 in 1,024** | **1 in 303** | **1 in 166** |
| 15 | 1 in 194,676 | 1 in 32,768 | 1 in 10,130 | 1 in 3,815 |

---

## 4. The Survival First Principle

### The Small Account Paradox (Formal Statement):

> *A $200 account needs aggressive returns to be worthwhile (earning $4-8/day is not worth the time). Aggressive returns require larger position sizes. Larger position sizes increase risk of ruin. **The very thing you need to grow is the thing that kills you.** *

### Mathematical Reality — Time to Grow:

To grow $200 to $1,000 (5x):

| Risk/Trade | Win Rate | R/R | EV/Trade | Trades Needed | Time (5/day) | Ruin Risk |
|------------|----------|-----|----------|---------------|-------------|-----------|
| 1% ($2) | 55% | 1:1 | +$0.20 | ~800 | ~8 months | <1% |
| 2% ($4) | 50% | 1:1.5 | +$0.80 | ~190 | ~2 months | ~5% |
| 2% ($4) | 55% | 1:1 | +$0.40 | ~400 | ~3.2 months | ~2% |
| 5% ($10) | 55% | 1:1 | +$1.00 | ~160 | ~1 month | ~13% |
| 10% ($20) | 55% | 1:1 | +$2.00 | ~80 | ~16 days | ~40%+ |

### The Harsh Truth:

**Professional prop firm traders risk 0.5-1% per trade on accounts of $50k-$1M+.** They cannot reliably achieve returns that justify their time with those risk parameters — they rely on large capital bases.

A $200 account **cannot** follow professional risk management AND achieve meaningful growth. You are forced to choose between:
1. **Oversizing risk** (5-10% per trade) with high probability of ruin
2. **Accepting glacial growth** (months to go from $200 to $300)
3. **Adding more capital** ($1000+ for a viable trading operation)

**The only honest answer:** Add more capital or treat the $200 as education money you fully expect to lose.

---

## 5. Professional Prop Firm Risk Rules

| Rule | FTMO | Topstep | For $200 Account |
|------|------|---------|------------------|
| Max daily loss | 5% | 4% | **$10/day** |
| Max overall drawdown | 10% | 6% | **$20 max loss** |
| Max risk per trade | 1-2% | 0.5-2% | **$1-4/trade** |
| Profit target | 10-20% | 5% | — |

**Translation for $200:**
- Max risk per trade: **$2-4** (1-2%)
- Max daily loss: **$10** (5%)
- Max overall drawdown: **$20** (10%)
- You have essentially **$20 of "error budget"** before you're down 10%

---

## 6. Binance Minimum Trade Sizes & Constraints

### Current Minimums (2024-2025):
- **Spot:** BTC/ETH min $10, alts $5-10
- **Futures:** Min $5 (BTC/ETH), $1-5 (alts)

### Constraint Analysis for $200:

| Stop Loss % | Position for $2 risk (1%) | Position for $4 risk (2%) | Need Leverage? |
|------------|--------------------------|--------------------------|----------------|
| 0.5% | $400 | $800 | Yes (2-4x) |
| 1.0% | $200 | $400 | Maybe (2x) |
| 2.0% | $100 | $200 | No |
| 5.0% | $40 | $80 | No |

### Fee Impact (Critical):

| Exchange | Per Round Trip | Impact on $200 |
|----------|---------------|----------------|
| Binance Spot (0.1%) | ~$0.20-0.40 | -0.1 to -0.2% per trade |
| Binance Futures (0.02-0.05%) | ~$0.05-0.20 | -0.025 to -0.1% per trade |

**50 trades/day on spot = $20/day fees = 10% of account**
**50 trades/day on futures = $5/day fees = 2.5% of account**

> **Conclusion: Futures are mandatory for small accounts. Spot trading with $200 is mathematically disadvantaged.**

---

## 7. Grid Trading with $200 — Does It Work?

### Grid Parameters for $200:
- 10 levels: $20/level
- 20 levels: $10/level
- 50 levels: $4/level (near minimums)

### The Reality:

| Metric | $200 Grid | $2,000 Grid | $10,000 Grid |
|--------|----------|------------|-------------|
| Grid levels possible | 10-20 | 50-100 | 100-500 |
| Diversification | Poor | Good | Excellent |
| Drawdown protection | None | Moderate | Strong |
| Ruin in strong trend | **Yes** | Unlikely | Very unlikely |

**Verdict:** Grid trading with $200 is **not recommended**. The account is too small to properly diversify grid levels.

---

## 8. Case Studies

### Case 1: The Lucky Scalper (Survivorship Bias)
- $100 → **$370 in 3 months** (+270%)
- Risk: 3-5%/trade, 55-60% win, 1:1 R/R
- Truth: ~10 accounts blew up for each survivor

### Case 2: The Prop Firm Simulator (Most Realistic Blueprint)
- $200 → **$285 in 6 months** (+42.5%)
- Risk: 2%/trade, 50% win, 1:1.5 R/R
- Lesson: Slow, boring, sustainable

### Case 3: The Overleveraged Gambler (Most Common Result)
- $200 → **$0 in 3 weeks**
- Risk: 15-25%/trade, 40% win, 1:1 R/R
- Death spiral: $200 → 7 losses at 20% = $41.94 → desperation = blown

### Case 4: The Grid Bot Failure (Silent Death)
- $200 → **~$160** (BTC dropped 20%, grid stuck)
- Grid profit generated: $3 (irrelevant vs -$40 drawdown)

### Case 5: The Consistent Winner (Blueprint)
- $200, Risk: 1-1.5%/trade, ~50% win, 1:2 R/R
- EV per trade: 0.4×$10 - 0.5×$5 = **$1.50**
- After 100 trades: +$150 (75% return)
- Losing streak of 10: account at ~$176 (still fine)

---

## 9. The $200 Account Commandments

1. **MAX RISK PER TRADE: $4 (2%). NEVER exceed.**
2. **OPTIMAL RISK: $2 (1%)** for survival, **$4 (2%)** for growth
3. **MAX DAILY LOSS: $10 (5%)** — stop there
4. **MAX WEEKLY LOSS: $20 (10%)** — shut down
5. **LEVERAGE MAX: 5x** — higher is gambling
6. **MINIMUM R/R: 1:1.5** — no worse expectancy
7. **MAX TRADES/DAY: 3-5** — overtrading kills
8. **USE FUTURES, NOT SPOT** — fees 5-10x lower
9. **HAVE A WRITTEN EDGE** — document your strategy
10. **POSITION SIZING FORMULA:** `Position = (Account x Risk%) / StopLoss%`

### The Bottom Line:

| Scenario | Risk/Trade | Time to $1,000 | Ruin Risk | Verdict |
|----------|-----------|----------------|-----------|---------|
| Ultra-conservative | 1% ($2) | ~2 years | <1% | Boring but lives |
| Moderate | 2% ($4) | ~8-12 months | 2-5% | **Best balance** |
| Aggressive | 5% ($10) | ~3-6 months | 13-30% | Unacceptably risky |
| Reckless | 10%+ ($20+) | ~1-3 months | 40-80%+ | Eventual ruin |

### Final Truth:

1. **$200 is survivable but marginal.** The opportunity cost is terrible.
2. **The fastest path to profitability is depositing more capital.** $1,000-2,000 makes 1% risk meaningful ($10-20/trade).
3. **If $200 is all you have,** focus 80% on learning/backtesting. The $200 is your tuition.
4. **Mathematics is not negotiable.** Risk of ruin doesn't care about your feelings.

---

## Appendix: Quick Reference Formulas

| Need | Formula | Example ($200) |
|------|---------|----------------|
| Position size | `(Acct x Risk%) / Stop%` | `(200 x 0.02) / 0.05 = $80` |
| Risk of ruin | `((1-W)/W)^(Acct/RiskAmt)` | `(0.45/0.55)^(200/4) = 0.005%` |
| Kelly fraction | `(bp - q) / b` | `(1x0.55 - 0.45)/1 = 10%` |
| Breakeven WR | `Risk / (Risk+Rwd)` | `1 / (1+3) = 25%` |
| Trades to target | `ln(Target/Start) / ln(1+g)` | `ln(1000/200)/ln(1.005) = 322` |
| After streak loss | `Acct x (1-risk%)^streak` | `200 x (0.98)^10 = $163.41` |
