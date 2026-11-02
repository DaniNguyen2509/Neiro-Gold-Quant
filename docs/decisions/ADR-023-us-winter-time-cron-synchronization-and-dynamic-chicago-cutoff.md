# ADR-023: US Winter Time Cron Synchronization and Dynamic Chicago Cutoff

## Status
Accepted

## Context
On November 1, 2026, the United States transitioned from Daylight Saving Time (EDT/CDT) to Standard Time (EST/CST) — commonly known as US Winter Time. 

This biannual clock shift alters the UTC alignment of all COMEX Gold Futures (`GC`) and CME Gold Options (`OG`) trading sessions:
1. **US Macroeconomic Data Releases (CPI, NFP, PPI):**
   - 08:30 AM EST = 13:30 UTC = 20:30 VN (shifted from 12:30 UTC / 19:30 VN in summer).
2. **US Cash Equities & GLD ETF Open:**
   - 09:30 AM EST = 14:30 UTC = 21:30 VN (shifted from 13:30 UTC / 20:30 VN in summer).
3. **COMEX Pit Close & Gold Options Settlement Cutoff:**
   - 13:30 Chicago Time (CT) = 19:30 UTC = 02:30 VN (next day) during CST winter (shifted from 18:30 UTC / 01:30 VN in CDT summer).

Prior to this decision, an audit of the automated ingestion pipeline (`.github/workflows/daily_options_sync.yml`) and quant engine (`src/quant_engine/synthetic.py`) revealed several vulnerabilities:
- **Cron Desynchronization:** GitHub Actions cron triggers were aligned exclusively to CDT summer hours (e.g. running at 17:15 UTC and 18:45 UTC). In winter, 18:45 UTC occurs 45 minutes *before* the 13:30 CST options settlement, missing final clearing prices.
- **Hardcoded Cutoff:** `synthetic.py` and rollover unit tests assumed a constant 18:30 UTC expiration cutoff, causing options expiring in winter months (e.g., contract month 12 expiring in late November) to calculate inaccurate DTE and prematurely roll contracts.
- **Pre-Market Zero-Quote Bias:** In off-hours or pre-market trading, unquoted deep out-of-the-money options have 0.0 bid and 0.0 ask. Evaluating `min(abs(call_mid - put_mid))` resulted in `|0 - 0| = 0`, erroneously choosing strike $1,350 instead of the active ATM strike near $4,000.
- **Barchart Scraper Zero IV:** Scraped merged-view option chains frequently leave implied volatility fields at `0.0`, propagating empty Greeks downstream.

## Decision
1. **Dynamic Chicago Cutoff (`get_cme_cutoff_dt`):**
   - Implemented dynamic timezone evaluation using Python standard library `zoneinfo.ZoneInfo("America/Chicago")`.
   - 13:30 Chicago Time automatically evaluates to **18:30 UTC in Summer (CDT)** and **19:30 UTC in Winter (CST)**.
   - Built-in zero-dependency calendar heuristic fallback ensures correct hour resolution even on stripped container runtimes lacking system tzdata.

2. **All-Weather CI Cron Synchronization:**
   - Updated `.github/workflows/daily_options_sync.yml` to support dual-season scheduling without manual winter/summer workflow edits:
     - `15 12,13,14 * * 1-5`: Intercepts Pre-US Macro releases (12:15 UTC summer, 13:15 UTC winter) and Pre-NYSE Open (14:15 UTC winter).
     - `45 13,14,15,16,17,18,19 * * 1-5`: Tracks continuous trading, London PM Fix, New York Power Hour, and captures both 18:45 UTC (Summer settlement) and 19:45 UTC (Winter settlement).

3. **Spot-Anchored ATM Resolution:**
   - Modified `find_atm_strike()` in `src/quant_engine/synthetic.py` to prioritize liquid two-sided quotes.
   - When all strikes are unquoted, anchors selection to `spot_price` (`min(abs(strike - spot_price))`) or median strike fallback, eliminating extreme $1,350 OTM selection.

4. **In-Scraper Automated Black-76 IV Enrichment:**
   - Added `_enrich_options_iv_and_greeks()` to `src/collector/scraper.py`.
   - When scraped chains contain zero IV (`callIV <= 0.01`), the scraper immediately solves for Black-76 implied volatility before saving to `data/options_prices_GCZ26.csv`, preventing downstream degradation.

## Consequences
- **Positive:**
  - Automated crawl and terminal build run at the exact right moment regardless of Daylight Saving Time.
  - Expiration cutoff and DTE calculations remain mathematically exact to the minute across all 12 months.
  - Zero-quote chains during weekend/pre-market correctly anchor to live CME Gold Futures.
  - Master CSV is guaranteed to contain valid IVs and Greeks.
- **Negative / Trade-offs:**
  - Added additional cron runs in GitHub Actions (within free tier allowance).

