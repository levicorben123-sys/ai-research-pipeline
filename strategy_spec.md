# Strategy spec (draft 1, 2026-09-23)

> **Superseded in detail by `research/creamer_knowledge.md`** (sections 15-16: answers to the
> open questions below, and a fuller numbered bot rulebook built from 32 of his videos). Next
> step: fold that rulebook into draft 2 of this spec once the remaining transcripts are in.

Translation of Chris Creamer's publicly described order-flow framework into testable rules.
**Status: draft.** Every rule marked *(approx)* is our stand-in for a discretionary read; the
open questions at the bottom need answers from more of his material before the backtest.

Sources used so far:
- Video summary: https://youtubesummary.com/summary/PL7LKUsCgIQ
  ("Trading WORLD CHAMPION Reveals the Orderflow Strategy That Won the Robbins Cup")
- Competition facts: https://www.worldcupchampionships.com/

## Instrument and session
- MNQ front-month futures (roll by volume). Trade window: 09:30-11:00 ET only.
- Charts: 5-minute and 1-minute order flow; higher timeframe for context.

## Step 1 - Environment (gamma exposure)
- Compute naive dealer gamma exposure (GEX) by strike for the Nasdaq-100 complex before the
  open: sum over strikes of (call OI x call gamma - put OI x put gamma) x contract multiplier.
- Positive net GEX -> "dampening" regime (expect mean reversion, fade extremes).
  Negative net GEX -> "amplification" regime (expect trend / larger moves).
- Call wall / put wall = strikes with the largest call / put gamma -> used as targets.
- *(approx)* How he uses the regime to filter trades is not specified; v1 rule: record the
  regime on every trade and test with and without a regime filter (one variable at a time).

## Step 2 - Location (discount)
- Value area: prior session's volume profile (70% of volume around the POC); POC = the price
  with the most volume.
- Long setups only below value (discount); shorts only above value (premium).
- Fibonacci retracement of the most recent swing (5-min swing points): entry zone
  0.705-0.886. Skip the setup if the zone sits inside the value area.

## Step 3 - Order-flow confirmation
- Needs trades with aggressor side (hit bid vs lifted ask) -> per-candle delta = ask volume -
  bid volume.
- Participation filter: skip if the 5-minute candle volume < 20,000 contracts. *(His number is
  quoted for NQ; must confirm whether it applies to MNQ volume - question Q2.)*
- *(approx)* "Failed sellers / absorption": inside the entry zone, a 1-minute candle with
  strongly negative delta whose low holds (price fails to make progress despite heavy selling).
- *(approx)* "Order flow flips bullish": the next 1-minute candle closes up with positive delta
  above the absorption candle's high -> enter long at that close.

## Step 4 - Risk, stop, target
- Stop: one tick beyond the extreme of the failed sellers (the absorption candle's low).
- Target: the nearest of prior swing high, POC, or call wall that gives >= 1.5R; skip the trade
  if none does. Trail the stop as price approaches the target *(approx: trail to breakeven at 1R)*.
- Risk per trade: fixed dollar amount (to be set; he trades inside prop-firm limits).
- Max trades per session and daily loss limit: to be set (question Q4).

## Validation standard (same discipline as the other projects)
- Backtest on several months of opening sessions, with commissions and 1-tick slippage.
- Report win rate, profit factor, average win/loss, max drawdown, results by month and by GEX
  regime, and number of trades. Compare with his stated 60-65% / PF ~1.8.
- Keep the last part of the data untouched until the rules are frozen (out-of-sample check).

## Open questions (need more of his material)
- G1. Which GEX source/definition does he use (Tanuki "naive GEX" on NQ options, NDX, or QQQ)?
  Determines which options data we buy.
- Q2. Is the 20,000-contract participation filter for NQ or MNQ?
- Q3. Exactly how does he define "dominance shift" / absorption on the footprint?
- Q4. Max trades per morning, daily loss stop, position size.
- Q5. Does he take shorts symmetrically (premium zones, bearish flip)?
