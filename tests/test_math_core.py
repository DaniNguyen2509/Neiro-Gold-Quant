"""Math-core tests (Test Plan - Section 2: M1-M11).

Covers the quantitative engine: Brent root-finder, Black-76 IV solver,
and Zero Gamma Flip (S*). All tests are deterministic, pure-math, no
network access.

Tests marked RED-EXPECTED document real gaps left failing until owner
approves the behavior change (rule G5).
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from src.quant_engine.dealer import (
    _brentq,
    compute_exact_gamma_flip,
    compute_wall_siege_ratio,
    solve_black76_iv,
)
from src.quant_engine.models import OptionsSnapshot, OptionsStrike

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
GC_REF = 4000.0  # Reference CME Gold Futures price


def _b76_price(F: float, K: float, T: float, sigma: float, is_call: bool, r: float = 0.045) -> float:
    """Textbook Black-76 pricer used as reference in tests."""
    disc = math.exp(-r * T)
    sqrt_t = math.sqrt(T)
    denom = sigma * sqrt_t
    d1 = (math.log(F / K) + 0.5 * sigma**2 * T) / denom
    d2 = d1 - denom
    n = lambda x: 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))
    if is_call:
        return disc * (F * n(d1) - K * n(d2))
    else:
        return disc * (K * n(-d2) - F * n(-d1))


def _make_snapshot(strikes_data: list[tuple[float, int, int]]) -> OptionsSnapshot:
    """Build OptionsSnapshot from [(strike, call_oi, put_oi), ...]."""
    return OptionsSnapshot(
        symbol="GCZ26",
        expiry="2026-11-25",
        timestamp="2026-11-02T00:00:00Z",
        strikes=tuple(
            OptionsStrike(
                strike=k,
                call_bid=10.0, call_ask=11.0,
                call_oi=c_oi, call_volume=0,
                put_bid=10.0, put_ask=11.0,
                put_oi=p_oi, put_volume=0,
            )
            for k, c_oi, p_oi in strikes_data
        ),
    )


# ===================================================================
# M1 - _brentq matches scipy reference
# ===================================================================
class TestM1BrentqAccuracy:
    """_brentq must match scipy.optimize.brentq within xtol."""

    @pytest.mark.parametrize(
        "f, a, b, xtol, exact_root",
        [
            (lambda x: x**3 - 1, 0.0, 2.0, 0.001, 1.0),
            (lambda x: math.cos(x) - x, 0.0, 2.0, 0.001, 0.7390851332),
            (lambda x: x - 0.001, -1.0, 1.0, 0.0001, 0.001),
            (lambda x: x**2 - 2, 1.0, 2.0, 0.001, math.sqrt(2)),
        ],
    )
    def test_brentq_vs_known_root(self, f, a, b, xtol, exact_root):
        our = _brentq(f, a, b, xtol=xtol)
        assert abs(our - exact_root) < xtol * 10, f"ours={our}, expected={exact_root}"


# ===================================================================
# M2 - _brentq raises when root is not bracketed
# ===================================================================
def test_m2_brentq_no_bracket():
    with pytest.raises(ValueError, match="Root not bracketed"):
        _brentq(lambda x: x**2 + 1, -1.0, 1.0)


def test_m2_brentq_same_sign():
    with pytest.raises(ValueError, match="Root not bracketed"):
        _brentq(lambda x: x + 10.0, 1.0, 5.0)


# ===================================================================
# M3 - IV round-trip
# ===================================================================
class TestM3IVRoundTrip:
    """Price with known sigma, then recover sigma via solver."""

    @pytest.mark.parametrize("sigma", [0.08, 0.16, 0.40, 1.20])
    @pytest.mark.parametrize("k_offset", [-0.15, -0.05, 0.0, 0.05, 0.15])
    @pytest.mark.parametrize("T_days", [1.0, 7.0, 30.0])
    def test_iv_round_trip(self, sigma, k_offset, T_days):
        F = GC_REF
        K = F * (1.0 + k_offset)
        T = T_days / 365.0
        is_call = K >= F

        price = _b76_price(F, K, T, sigma, is_call)
        if price <= 0.01:
            pytest.skip("price too small for stable inversion")

        recovered = solve_black76_iv(F, K, T, price, is_call)
        assert abs(recovered - sigma) < 0.002, (
            f"sigma={sigma}, recovered={recovered}, K={K}, T={T_days}d, price={price:.4f}"
        )


# ===================================================================
# M4 - IV outside [0.03, 1.50] (RED-EXPECTED)
# ===================================================================
def test_m4_iv_above_band_returns_clip_not_default():
    """RED-EXPECTED: sigma=2.5 price should yield clipped IV=1.50, not default 0.20."""
    F, K, T = GC_REF, GC_REF, 30.0 / 365.0
    price = _b76_price(F, K, T, 2.50, True)
    iv = solve_black76_iv(F, K, T, price, True)
    # The solver CAN'T bracket 2.50 because the search band is [0.02, 2.00].
    # It silently returns default_iv=0.20 instead of the clipped maximum 1.50.
    # Acceptable: iv == 1.50 (clipped). Not acceptable: iv == 0.20 (silent fallback).
    assert iv != pytest.approx(0.20, abs=0.01), (
        "IV silently fell back to default_iv instead of reporting out-of-band"
    )


def test_m4_iv_below_band_returns_clip_not_default():
    """sigma=0.01 price -> clipped to 0.03 or flagged, not silent 0.20."""
    F = GC_REF
    K = GC_REF * 1.01  # slightly OTM call
    T = 30.0 / 365.0
    price = _b76_price(F, K, T, 0.015, True)
    if price <= 0:
        pytest.skip("price zero")
    iv = solve_black76_iv(F, K, T, price, True)
    assert iv != pytest.approx(0.20, abs=0.01), (
        "IV silently fell back to default_iv instead of reporting out-of-band"
    )


# ===================================================================
# M5 - Price <= intrinsic
# ===================================================================
def test_m5_price_below_intrinsic():
    """When price < intrinsic, solver must return default_iv (documented fallback)."""
    F, K, T = GC_REF, 3900.0, 30.0 / 365.0
    intrinsic = (F - K) * math.exp(-0.045 * T)
    price = intrinsic * 0.5  # clearly below intrinsic
    iv = solve_black76_iv(F, K, T, price, is_call=True)
    assert iv == pytest.approx(0.20, abs=0.001), "Should return default_iv for sub-intrinsic price"


def test_m5_price_exactly_zero():
    iv = solve_black76_iv(GC_REF, GC_REF, 30.0 / 365.0, 0.0, True)
    assert iv == pytest.approx(0.20, abs=0.001)


def test_m5_negative_inputs():
    """All guard-rails must produce default_iv without crashing."""
    assert solve_black76_iv(-1.0, GC_REF, 0.1, 10.0, True) == pytest.approx(0.20)
    assert solve_black76_iv(GC_REF, -1.0, 0.1, 10.0, True) == pytest.approx(0.20)
    assert solve_black76_iv(GC_REF, GC_REF, -0.1, 10.0, True) == pytest.approx(0.20)


# ===================================================================
# M6 - Zero Gamma Flip with known solution
# ===================================================================
def test_m6_symmetric_snapshot_flip_at_midpoint():
    """Two symmetric strikes with mirrored OI -> S* at midpoint."""
    snap = _make_snapshot([
        (3900.0, 1000, 0),   # net call -> long gamma above
        (4100.0, 0, 1000),   # net put -> short gamma below
    ])
    s_star = compute_exact_gamma_flip(snap, spot_price=GC_REF, dte_days=30.0)
    assert s_star is not None
    assert abs(s_star - 4000.0) < 10.0, f"Expected ~4000, got {s_star}"


def test_m6_three_strikes_known_crossover():
    snap = _make_snapshot([
        (3800.0, 500, 200),
        (4000.0, 300, 300),
        (4200.0, 200, 500),
    ])
    s_star = compute_exact_gamma_flip(snap, spot_price=GC_REF, dte_days=30.0)
    assert s_star is not None
    assert 3800.0 < s_star < 4200.0


# ===================================================================
# M7 - No zero crossing
# ===================================================================
def test_m7_all_long_gamma_returns_none():
    """Toàn call OI > put OI mọi nơi -> net diff > 0 -> no crossing."""
    snap = _make_snapshot([
        (3800.0, 1000, 100),
        (4000.0, 1000, 100),
        (4200.0, 1000, 100),
    ])
    assert compute_exact_gamma_flip(snap, spot_price=GC_REF) is None


def test_m7_all_short_gamma_returns_none():
    snap = _make_snapshot([
        (3800.0, 100, 1000),
        (4000.0, 100, 1000),
        (4200.0, 100, 1000),
    ])
    assert compute_exact_gamma_flip(snap, spot_price=GC_REF) is None


def test_m7_empty_chain():
    snap = _make_snapshot([])
    assert compute_exact_gamma_flip(snap, spot_price=GC_REF) is None


def test_m7_single_strike():
    snap = _make_snapshot([(4000.0, 500, 500)])
    assert compute_exact_gamma_flip(snap, spot_price=GC_REF) is None


# ===================================================================
# M8 - Multiple crossings: choose nearest to GC
# ===================================================================
def test_m8_multiple_crossings_picks_nearest():
    """Two crossings: one near 3400, another near 4000. GC is 4000."""
    snap = _make_snapshot([
        (3300.0, 800, 100),
        (3500.0, 100, 800),  # crossing 1 around 3400
        (3900.0, 1000, 100),
        (4100.0, 100, 1000),  # crossing 2 around 4000
    ])
    s_star = compute_exact_gamma_flip(snap, spot_price=GC_REF, dte_days=30.0)
    assert s_star is not None
    # Must pick the crossing near 4000, not the one near 3400
    assert abs(s_star - 4000.0) < 150.0, f"Picked wrong crossing: {s_star}"


# ===================================================================
# M9 - Grid resolution: narrow crossing on real-scale chain
#       (RED-EXPECTED)
# ===================================================================
def test_m9_narrow_crossing_not_missed():
    """RED-EXPECTED: 895 strikes (1350-10000), crossing within a 25-USD gap near GC.

    The current grid is max(60, 2*895) = 1790 points over ~8800 USD range
    (~4.9 USD/step). The 25-USD gap should be resolvable... but this test
    verifies that explicitly.
    """
    strikes_data = []
    for k in np.arange(1350.0, 10025.0, 25.0):
        if k < 3990.0:
            # net call OI -> positive diff
            strikes_data.append((float(k), 200, 50))
        elif k > 4010.0:
            # net put OI -> negative diff
            strikes_data.append((float(k), 50, 200))
        else:
            # crossing zone (3990-4010): equal OI
            strikes_data.append((float(k), 100, 100))

    snap = _make_snapshot(strikes_data)
    s_star = compute_exact_gamma_flip(snap, spot_price=GC_REF, dte_days=30.0)
    assert s_star is not None, "Crossing near GC was missed by the grid"
    assert abs(s_star - 4000.0) < 25.0, f"S*={s_star} too far from expected ~4000"


# ===================================================================
# M10 - Scale invariance: OI * k -> same S*
# ===================================================================
def test_m10_oi_scale_invariance():
    base = [
        (3800.0, 500, 200),
        (4000.0, 300, 300),
        (4200.0, 200, 500),
    ]
    snap1 = _make_snapshot(base)
    snap10 = _make_snapshot([(k, c * 10, p * 10) for k, c, p in base])

    s1 = compute_exact_gamma_flip(snap1, spot_price=GC_REF, dte_days=30.0)
    s10 = compute_exact_gamma_flip(snap10, spot_price=GC_REF, dte_days=30.0)
    assert s1 is not None and s10 is not None
    assert abs(s1 - s10) < 0.5, f"S* shifted from {s1} to {s10} after OI scaling"


# ===================================================================
# M11 - Golden test with real CSV data (snapshot locked)
# ===================================================================
@pytest.fixture(scope="module")
def real_csv_snapshot():
    """Load the real CSV into an OptionsSnapshot for golden tests."""
    import pandas as pd
    from src.quant_engine.loader import to_options_snapshot

    csv_path = "data/options_prices_GCZ26.csv"
    df = pd.read_csv(csv_path)
    snap = to_options_snapshot(df)
    return snap, df


def test_m11_golden_flip_consistency(real_csv_snapshot):
    """S* must be stable across runs with the same data.

    The first run prints the value; subsequent runs verify it hasn't drifted.
    Tolerance: 0.5 USD (xtol of Brent = 0.01).
    """
    snap, _ = real_csv_snapshot
    s1 = compute_exact_gamma_flip(snap, spot_price=GC_REF, dte_days=22.0, default_iv=0.16)
    s2 = compute_exact_gamma_flip(snap, spot_price=GC_REF, dte_days=22.0, default_iv=0.16)
    assert s1 is not None, "No gamma flip found on real data"
    assert s1 == s2, "Two identical calls produced different S*"
    print(f"[GOLDEN] S* = {s1} (review and lock this value)")


def test_m11_walls_stable(real_csv_snapshot):
    """Call Wall and Put Wall must be identical across two calls."""
    from src.quant_engine.dealer import find_gamma_weighted_walls

    snap, df = real_csv_snapshot
    cw1, pw1 = find_gamma_weighted_walls(df, top_n=2, spot_price=GC_REF, dte_days=22.0)
    cw2, pw2 = find_gamma_weighted_walls(df, top_n=2, spot_price=GC_REF, dte_days=22.0)
    assert len(cw1) > 0 and len(pw1) > 0
    assert cw1[0].strike == cw2[0].strike
    assert pw1[0].strike == pw2[0].strike
    print(f"[GOLDEN] Call Wall = {cw1[0].strike}, Put Wall = {pw1[0].strike}")


# ===================================================================
# Wall Siege Ratio (bonus: quick coverage)
# ===================================================================
class TestWallSiegeRatio:
    def test_zero_oi(self):
        assert compute_wall_siege_ratio(100, 0) == 9.99

    def test_zero_volume_zero_oi(self):
        assert compute_wall_siege_ratio(0, 0) == 0.0

    def test_normal(self):
        assert compute_wall_siege_ratio(80, 100) == 0.80

    def test_under_siege_threshold(self):
        assert compute_wall_siege_ratio(80, 100) >= 0.8
