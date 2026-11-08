"""Unit tests for Multi-Expiry GEX Aggregation and Gamma-Weighted Liquidity Wall System."""
from __future__ import annotations

import datetime
import math
import numpy as np
import pandas as pd
import pytest

from src.quant_engine.dealer import (
    find_gamma_weighted_walls,
    classify_wall_regime,
    compute_exact_gamma_flip,
)
from src.quant_engine.synthetic import (
    resolve_active_expirations,
    compute_dynamic_dte,
)
from src.quant_engine.loader import aggregate_options_dataframes
from src.quant_engine.models import OptionsSnapshot, OptionsStrike, Wall


def test_gamma_scaling_1dte_vs_30dte():
    """Verify that 400 OI on 1DTE (Strike 4085) exerts higher hedging power than 1706 OI on 30DTE (Strike 4100)."""
    spot = 4100.0
    sigma = 0.16
    r = 0.045

    def calc_gamma(F: float, K: float, T_years: float) -> float:
        denom = sigma * math.sqrt(T_years)
        d1 = (math.log(F / K) + 0.5 * (sigma ** 2) * T_years) / denom
        pdf = (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * (d1 ** 2))
        return (math.exp(-r * T_years) * pdf) / (F * denom)

    # 30 DTE Strike 4100
    gamma_30d = calc_gamma(spot, 4100.0, 30.0 / 365.0)
    power_30d = 1706 * gamma_30d

    # 1 DTE Strike 4085
    gamma_1d = calc_gamma(spot, 4085.0, 1.0 / 365.0)
    power_1d = 400 * gamma_1d

    assert power_1d > power_30d, f"Expected 1DTE power ({power_1d:.2f}) > 30DTE power ({power_30d:.2f})"
    assert power_1d / power_30d > 1.10, "1DTE power should be at least 10% greater"


def test_find_gamma_weighted_walls_selection():
    """Verify find_gamma_weighted_walls selects the gamma-dominant strike over raw OI."""
    # Create DataFrame where Strike 4100 has huge OI (1706) but low gamma (0.002)
    # Strike 4085 has lower OI (400) but high gamma (0.012)
    df = pd.DataFrame({
        "strike": [4085.0, 4100.0, 4150.0],
        "callOpenInterest": [10, 50, 1000],
        "putOpenInterest": [400, 1706, 20],
        "callVolume": [0, 5, 20],
        "putVolume": [10, 40, 2],
        "callGamma": [0.001, 0.002, 0.003],
        "putGamma": [0.012, 0.002, 0.001],
        "callBid": [100.0, 90.0, 50.0],
        "callAsk": [102.0, 92.0, 52.0],
        "putBid": [5.0, 10.0, 30.0],
        "putAsk": [6.0, 11.0, 32.0],
    })

    spot = 4125.0
    call_walls, put_walls = find_gamma_weighted_walls(df, spot_price=spot, top_n=2)

    assert len(put_walls) >= 2
    # Primary Put Wall (rank 1) must be 4085 because 400 * 0.012 = 4.8 > 1706 * 0.002 = 3.412
    assert put_walls[0].strike == 4085.0
    assert put_walls[0].gamma_power > put_walls[1].gamma_power
    assert put_walls[1].strike == 4100.0


def test_classify_wall_regime():
    """Verify wall regime classification into MAGNET_WALL and BOUNCE_WALL."""
    # Negative GEX at strike -> MAGNET_WALL (acceleration trap)
    reg_magnet = classify_wall_regime(side="put", net_gex_at_strike=-12.5, siege_ratio=0.3, total_net_gex=-15.0)
    assert reg_magnet == "MAGNET_WALL"

    # High siege ratio (>= 0.8) -> MAGNET_WALL
    reg_siege = classify_wall_regime(side="put", net_gex_at_strike=1.0, siege_ratio=0.95, total_net_gex=5.0)
    assert reg_siege == "MAGNET_WALL"

    # Positive GEX with low siege -> BOUNCE_WALL
    reg_bounce = classify_wall_regime(side="put", net_gex_at_strike=8.0, siege_ratio=0.2, total_net_gex=10.0)
    assert reg_bounce == "BOUNCE_WALL"

    # Call side
    reg_call_bounce = classify_wall_regime(side="call", net_gex_at_strike=15.0, siege_ratio=0.1)
    assert reg_call_bounce == "BOUNCE_WALL"

    reg_call_magnet = classify_wall_regime(side="call", net_gex_at_strike=-8.0, siege_ratio=0.1)
    assert reg_call_magnet == "MAGNET_WALL"


def test_aggregate_options_dataframes_multi_expiry():
    """Verify mathematical superposition across multiple expirations."""
    df_weekly = pd.DataFrame({
        "strike": [4085.0, 4100.0],
        "callOpenInterest": [5, 20],
        "putOpenInterest": [400, 100],
        "callVolume": [1, 2],
        "putVolume": [20, 10],
        "callGamma": [0.005, 0.005],
        "putGamma": [0.0116, 0.005],
        "callBid": [105.0, 92.0],
        "callAsk": [107.0, 94.0],
        "putBid": [5.0, 8.0],
        "putAsk": [6.0, 9.0],
    })
    df_weekly.attrs["expiration_date"] = "2026-10-23"
    df_weekly.attrs["dte_days"] = 1.0

    df_monthly = pd.DataFrame({
        "strike": [4085.0, 4100.0],
        "callOpenInterest": [10, 45],
        "putOpenInterest": [20, 1706],
        "callVolume": [0, 1],
        "putVolume": [2, 40],
        "callGamma": [0.002, 0.0021],
        "putGamma": [0.002, 0.0021],
        "callBid": [106.0, 93.0],
        "callAsk": [108.0, 95.0],
        "putBid": [6.0, 9.5],
        "putAsk": [7.0, 10.5],
    })
    df_monthly.attrs["expiration_date"] = "2026-10-27"
    df_monthly.attrs["dte_days"] = 5.0

    agg = aggregate_options_dataframes([df_weekly, df_monthly], spot_price=4100.0)

    assert not agg.empty
    assert len(agg) == 2
    assert agg.attrs.get("is_aggregated") is True

    row_4085 = agg[agg["strike"] == 4085.0].iloc[0]
    row_4100 = agg[agg["strike"] == 4100.0].iloc[0]

    # OI must sum
    assert row_4085["putOpenInterest"] == 420
    assert row_4100["putOpenInterest"] == 1806

    # Gamma Power superposition
    assert row_4085["putGammaPower"] > row_4100["putGammaPower"]


def test_resolve_active_expirations():
    """Verify dynamic discovery of Weekly Friday and Front-Month contracts."""
    base_date = datetime.date(2026, 10, 23)  # Friday
    exps = resolve_active_expirations(now=base_date, underlying_futures="GCZ26", weekly_count=2)

    assert len(exps) >= 2
    types = [e["type"] for e in exps]
    assert "WEEKLY" in types
    assert "MONTHLY" in types

    weekly_exp = next(e for e in exps if e["type"] == "WEEKLY")
    assert "OG" in weekly_exp["option_symbol"]
    assert weekly_exp["dte"] >= 0.0
    assert "barchart.com" in weekly_exp["barchart_url"]


def test_put_wall_bounce_in_long_gamma_regime():
    """Verify that a Put Wall in a Long Gamma market with low siege is classified as BOUNCE_WALL."""
    # Even if strike net GEX is negative (due to high Put OI), in a macro Long Gamma market
    # dealers act as mean-reverting pin stabilizers.
    reg = classify_wall_regime(
        side="put",
        net_gex_at_strike=-25.0,  # high put OI creates negative strike GEX
        siege_ratio=0.15,         # calm orderflow
        total_net_gex=20.0,       # macro Long Gamma
    )
    assert reg == "BOUNCE_WALL"

    # But if the same Put Wall is in a macro Short Gamma market, it becomes a MAGNET_WALL
    reg_short = classify_wall_regime(
        side="put",
        net_gex_at_strike=-25.0,
        siege_ratio=0.15,
        total_net_gex=-15.0,      # macro Short Gamma
    )
    assert reg_short == "MAGNET_WALL"


def test_load_multi_expiry_options_no_double_counting(tmp_path):
    """Verify load_multi_expiry_options does not double-count when master file exists alongside sub-files."""
    from src.quant_engine.loader import load_multi_expiry_options

    df_w = pd.DataFrame({
        "strike": [4085.0, 4100.0],
        "callOpenInterest": [5, 20],
        "putOpenInterest": [400, 100],
        "callVolume": [1, 2],
        "putVolume": [20, 10],
        "callGamma": [0.005, 0.005],
        "putGamma": [0.0116, 0.005],
        "callBid": [105.0, 92.0],
        "callAsk": [107.0, 94.0],
        "putBid": [5.0, 8.0],
        "putAsk": [6.0, 9.0],
    })
    df_m = pd.DataFrame({
        "strike": [4085.0, 4100.0],
        "callOpenInterest": [10, 45],
        "putOpenInterest": [20, 1706],
        "callVolume": [0, 1],
        "putVolume": [2, 40],
        "callGamma": [0.002, 0.0021],
        "putGamma": [0.002, 0.0021],
        "callBid": [106.0, 93.0],
        "callAsk": [108.0, 95.0],
        "putBid": [6.0, 9.5],
        "putAsk": [7.0, 10.5],
    })
    # Save sub-expiry files
    df_w.to_csv(tmp_path / "options_prices_GCZ26_OG4V26.csv", index=False)
    df_m.to_csv(tmp_path / "options_prices_GCZ26_OGX26.csv", index=False)
    # Save master file (already aggregated)
    agg_direct = aggregate_options_dataframes([df_w, df_m], spot_price=4100.0)
    agg_direct.to_csv(tmp_path / "options_prices_GCZ26.csv", index=False)

    loaded = load_multi_expiry_options(str(tmp_path))

    row_4085 = loaded[loaded["strike"] == 4085.0].iloc[0]
    row_4100 = loaded[loaded["strike"] == 4100.0].iloc[0]

    # Exactly 420 and 1806, NOT 840 and 3612!
    assert row_4085["putOpenInterest"] == 420
    assert row_4100["putOpenInterest"] == 1806


def test_short_put_dynamic_hedging_math():
    """Verify Dealer delta hedging mathematical proof for 1,706 Put OI between 4,125 and 4,082."""
    sigma = 0.16
    r = 0.045
    T_years = 30.0 / 365.0
    K = 4100.0
    OI = 1706

    def put_delta(F: float) -> float:
        denom = sigma * math.sqrt(T_years)
        d1 = (math.log(F / K) + 0.5 * (sigma ** 2) * T_years) / denom
        cdf_minus_d1 = 0.5 * (1.0 + math.erf(-d1 / math.sqrt(2.0)))
        return - math.exp(-r * T_years) * cdf_minus_d1

    # Dealer Short Put -> Dealer Delta = - OI * PutDelta = + OI * exp(-rT) * N(-d1)
    dealer_delta_4125 = - OI * put_delta(4125.0)
    dealer_delta_4082 = - OI * put_delta(4082.0)

    # Change in dealer delta (futures to sell to remain neutral)
    delta_change = dealer_delta_4125 - dealer_delta_4082
    notional_mil = abs(delta_change) * 100 * 4100.0 / 1e6

    # Dealer was forced to sell ~154.5 futures contracts (~$63.3M - $63.7M notional)
    assert 150.0 <= abs(delta_change) <= 160.0
    assert 60.0 <= notional_mil <= 66.0


def test_unphysical_flat_gamma_healed_by_black76_in_wall_scoring():
    """Regression guard: uniform dummy 0.0037 gamma or stale callGammaPower at deep OTM ($5500)
    must be healed with true Black-76 gamma so $4200 wins over $5500."""
    strikes = [3700.0, 3900.0, 4000.0, 4075.0, 4100.0, 4200.0, 4500.0, 5000.0, 5500.0]
    call_oi = [10, 50, 500, 1000, 4076, 6193, 3000, 5000, 15000]
    put_oi = [12000, 6600, 5163, 1200, 400, 200, 50, 10, 5]

    df = pd.DataFrame({
        "strike": strikes,
        "callOpenInterest": call_oi,
        "putOpenInterest": put_oi,
        "callVolume": [10] * len(strikes),
        "putVolume": [10] * len(strikes),
        "callGamma": [0.0037] * len(strikes),
        "putGamma": [0.0037] * len(strikes),
        "callGammaPower": [oi * 0.0037 for oi in call_oi],
        "putGammaPower": [oi * 0.0037 for oi in put_oi],
    })

    cw, pw = find_gamma_weighted_walls(df, top_n=2, spot_price=4075.0, dte_days=17.0, default_iv=0.20)
    assert cw[0].strike == 4200.0, f"Expected Call Wall 4200.0, got {cw[0].strike}"
    assert pw[0].strike == 4000.0, f"Expected Put Wall 4000.0, got {pw[0].strike}"


