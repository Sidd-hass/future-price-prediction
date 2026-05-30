# Verification Guide — For Stock Chart Analyst

Hand this document to anyone with access to a trading terminal (Upstox Pro, Zerodha Kite, TradingView, etc.) to manually confirm the app's logic is correct.

---

## What This App Monitors

| # | Stock | Spot Symbol | Current Month Future | Next Month Future |
|---|-------|------------|---------------------|-------------------|
| 1 | Reliance Industries | **RELIANCE** (NSE) | **RELIANCE JUN FUT** (expiry 30-Jun-2026) | **RELIANCE JUL FUT** (expiry 28-Jul-2026) |
| 2 | TCS | **TCS** (NSE) | **TCS JUN FUT** (expiry 30-Jun-2026) | **TCS JUL FUT** (expiry 28-Jul-2026) |
| 3 | Infosys | **INFY** (NSE) | **INFY JUN FUT** (expiry 30-Jun-2026) | **INFY JUL FUT** (expiry 28-Jul-2026) |
| 4 | HDFC Bank | **HDFCBANK** (NSE) | **HDFCBANK JUN FUT** (expiry 30-Jun-2026) | **HDFCBANK JUL FUT** (expiry 28-Jul-2026) |
| 5 | ICICI Bank | **ICICIBANK** (NSE) | **ICICIBANK JUN FUT** (expiry 30-Jun-2026) | **ICICIBANK JUL FUT** (expiry 28-Jul-2026) |

---

## The Two Formulas

### Formula 1 — Basis Discount (%)

```
Basis = ((Spot Price − Current Month Future Price) / Spot Price) × 100
```

- A **positive** Basis means the future is trading **cheaper** than spot (discount).
- A **negative** Basis means the future is trading at a **premium** to spot.

**Threshold:** App alerts when **Basis > 2.00%**

### Formula 2 — Calendar Spread (%)

```
Spread = ((Next Month Future Price − Current Month Future Price) / Current Month Future Price) × 100
```

- Shows the price difference between the two consecutive monthly futures.

**Threshold:** App alerts when **0.00% ≤ Spread ≤ 0.20%**

### Alert Triggers When

> **BOTH conditions are true at the same time:**
> 1. Basis > 2.00%
> 2. Spread is between 0.00% and 0.20%

---

## How to Manually Verify on a Chart

### Step 1: Open 3 Charts Side-by-Side

For any stock (e.g., RELIANCE), open these three on your trading terminal:

1. **RELIANCE** (NSE Equity / Cash)
2. **RELIANCE JUN FUT** (NSE F&O, expiry 30-Jun-2026)
3. **RELIANCE JUL FUT** (NSE F&O, expiry 28-Jul-2026)

### Step 2: Note the Current Prices

At any moment during market hours, write down the **Last Traded Price (LTP)** for all three.

Example (hypothetical):
| Instrument | LTP |
|---|---|
| RELIANCE (Spot) | ₹1,356.30 |
| RELIANCE JUN FUT | ₹1,325.00 |
| RELIANCE JUL FUT | ₹1,326.30 |

### Step 3: Calculate Basis

```
Basis = ((1356.30 − 1325.00) / 1356.30) × 100
      = (31.30 / 1356.30) × 100
      = 2.31%  ✅ (> 2.00% threshold)
```

### Step 4: Calculate Spread

```
Spread = ((1326.30 − 1325.00) / 1325.00) × 100
       = (1.30 / 1325.00) × 100
       = 0.098%  ✅ (between 0.00% and 0.20%)
```

### Step 5: Verdict

Both conditions met → **App would send a Telegram alert** ✅

---

## What the Telegram Alert Looks Like

```
🚨 FUTURES DISCOUNT ALERT
━━━━━━━━━━━━━━━━━━━━━━
Stock:          RELIANCE
Time:           2026-05-27 10:45:23 IST

Spot Price:     ₹1356.30
Cur Month Fut:  ₹1325.00  (2.31% discount)  Exp: 2026-06-30
Nxt Month Fut:  ₹1326.30  (0.10% vs cur)   Exp: 2026-07-28

Basis:   2.31%  ✅ [Threshold > 2.00%]
Spread:  0.10% ✅ [Threshold 0.00%-0.20%]

SIGNAL: BOTH CONDITIONS MET
```

---

## Quick Reference — When It Does NOT Alert

| Scenario | Spot | Cur Fut | Nxt Fut | Basis | Spread | Alert? | Why Not? |
|---|---|---|---|---|---|---|---|
| Normal premium | ₹3,450 | ₹3,400 | ₹3,407 | 1.45% | 0.21% | ❌ | Basis below 2%; Spread above 0.2% |
| Basis OK but spread too wide | ₹1,520 | ₹1,485 | ₹1,490 | 2.30% | 0.34% | ❌ | Spread exceeds 0.20% |
| Both conditions met | ₹1,520 | ₹1,485 | ₹1,486.5 | 2.30% | 0.10% | ✅ | — |

---

## Noise Filter (Why It Doesn't Alert on Every Tick)

The app does **not** alert on the first tick that meets the conditions. It waits for **5 consecutive ticks** (price updates) that all satisfy both conditions. This filters out momentary spikes.

After sending an alert, the app enters a **15-minute cooldown** for that stock before it can alert again.

---

## Summary Checklist for the Analyst

- [ ] Open spot + 2 futures charts for any watchlist stock
- [ ] Note all 3 LTP values at the same moment
- [ ] Calculate Basis using the formula above
- [ ] Calculate Spread using the formula above
- [ ] Confirm: Does Basis > 2.00% AND 0.00% ≤ Spread ≤ 0.20%?
- [ ] If yes → The app would alert. If no → The app stays silent.
- [ ] Cross-check with the Telegram message received (if app is running live)
