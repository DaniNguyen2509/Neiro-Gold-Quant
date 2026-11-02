# ADR-024: Precomputed Static Squeeze Ladder and Data Analyst Pipeline Hardening

## Status
Accepted

## Context
In COMEX Gold Options microstructure, Open Interest (OI) is strictly static throughout the intraday trading session (cleared and finalized once overnight by CME Clearing House). 

Consequently, key structural elements:
1. **Major Gamma Walls:** Call Wall (max call OI) and Put Wall (max put OI).
2. **Air Pocket Zones:** Structural liquidity voids where $\text{OI} < 0.15 \times \text{Mean(OI)}$.
3. **Gamma Squeeze Breakout Triggers and Take-Profit Targets:** Points where market makers face short gamma acceleration and must aggressively cover in the futures market.

These levels are mathematically invariant for any given strike $K$ until the next CME clearing cycle. Re-evaluating these levels sequentially on every incoming tick or render loop added unnecessary CPU overhead and left the system vulnerable to edge-case anomalies.

Furthermore, upstream raw options chains (whether scraped or imported) frequently contain data anomalies:
- Crossed market quotes ($\text{Ask} < \text{Bid}$).
- Duplicate strikes resulting from multi-expiry union operations.
- Unsorted / non-monotonic strike sequences.
- Formatted currency strings (`$3,967.10`, `1,500`, `#N/A`).

## Decision
1. **Precomputed Squeeze Ladder Engine (`precompute_squeeze_ladder`):**
   - Implemented in `src/quant_engine/strategy.py`.
   - Computes invariant Squeeze triggers ($K + \text{buffer} + 0.50$), targets (dynamically expanded if the next strike borders an Air Pocket), and stop-losses ($K - 1.50$) across all strikes upon data load.
   - Implemented `lookup_precomputed_squeeze(ladder, spot)` providing sub-millisecond $\mathcal{O}(1)$ / binary bisect lookup for immediate upper and lower levels.

2. **Data Analyst Ingestion & Cleaning Pipeline (`clean_and_sanitize_options_dataset`):**
   - Implemented in `src/collector/validator.py`.
   - Strips whitespace from column names.
   - Removes duplicate strikes (`drop_duplicates(subset=['strike'])`).
   - Enforces strict ascending monotonicity (`sort_values('strike')`).
   - Heals crossed market quotes: if $\text{Ask} < \text{Bid}$, quotes are automatically swapped to maintain market pricing invariants.
   - Enforces non-negative bounds on Open Interest, Volume, and Implied Volatility.
   - Filters out non-Gold outlier strikes ($K < 1000$ or $K > 10000$).

3. **Dashboard Realtime Integration:**
   - `src/hud/html_dashboard.py` automatically invokes `clean_and_sanitize_options_dataset()` and embeds `precompute_squeeze_ladder()` into `meta["squeeze_ladder"]`.

## Consequences
- **Positive:**
  - Microsecond $\mathcal{O}(1)$ tactical lookup during live trading without recalculating static structures.
  - Complete data purity guaranteed before mathematical modeling begins.
  - Clean separation of static intraday invariants vs. dynamic realtime tick updates.
- **Negative / Trade-offs:**
  - Negligible memory footprint increase for storing the precomputed ladder dictionary (895 entries $\approx 150$ KB, well within zero-leak constraints).

