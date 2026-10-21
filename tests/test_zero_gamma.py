"""Unit tests for Exact Zero Gamma Flip solver and Wall Siege Ratio."""
from __future__ import annotations

import pytest

from src.quant_engine.dealer import (
    compute_exact_gamma_flip,
    compute_wall_siege_ratio,
    find_walls,
)
from src.quant_engine.models import OptionsSnapshot, OptionsStrike


def make_strike(
    strike: float,
    call_oi: int,
    put_oi: int,
    call_volume: int = 100,
    put_volume: int = 100,
) -> OptionsStrike:
    return OptionsStrike(
        strike=strike,
        call_bid=10.0,
        call_ask=12.0,
        put_bid=10.0,
        put_ask=12.0,
        call_oi=call_oi,
        put_oi=put_oi,
        call_volume=call_volume,
        put_volume=put_volume,
    )


def test_compute_wall_siege_ratio():
    assert compute_wall_siege_ratio(0, 1000) == 0.0
    assert compute_wall_siege_ratio(250, 1000) == 0.25
    assert compute_wall_siege_ratio(850, 1000) == 0.85
    assert compute_wall_siege_ratio(2500, 1000) == 2.50
    # Zero OI safety
    assert compute_wall_siege_ratio(500, 0) == 9.99
    assert compute_wall_siege_ratio(0, 0) == 0.0


def test_find_walls_siege_ratio_and_flag():
    strikes = (
        make_strike(4150.0, call_oi=1000, put_oi=5000, call_volume=200, put_volume=4500),  # put siege: 4500/5000 = 0.90 -> True
        make_strike(4200.0, call_oi=6000, put_oi=1500, call_volume=1200, put_volume=300),  # call siege: 1200/6000 = 0.20 -> False
    )
    snapshot = OptionsSnapshot(symbol="GC", expiry="2026-10-27", timestamp="2026-10-19T00:00:00", strikes=strikes)
    call_walls, put_walls = find_walls(snapshot, top_n=1)

    assert len(call_walls) == 1
    assert call_walls[0].siege_ratio == 0.20
    assert not call_walls[0].is_under_siege

    assert len(put_walls) == 1
    assert put_walls[0].siege_ratio == 0.90
    assert put_walls[0].is_under_siege


def test_zero_gamma_symmetric_market():
    # Symmetrical distribution centered at 4200:
    # 4100: Call 100, Put 5000 (diff: -4900)
    # 4200: Call 1000, Put 1000 (diff: 0)
    # 4300: Call 5000, Put 100 (diff: +4900)
    strikes = (
        make_strike(4100.0, call_oi=100, put_oi=5000),
        make_strike(4200.0, call_oi=1000, put_oi=1000),
        make_strike(4300.0, call_oi=5000, put_oi=100),
    )
    snapshot = OptionsSnapshot(symbol="GC", expiry="2026-10-27", timestamp="2026-10-19T00:00:00", strikes=strikes)
    flip = compute_exact_gamma_flip(snapshot, spot_price=4200.0, dte_days=30.0)

    assert flip is not None
    # Symmetrical setup places Zero Gamma around ~4194.4 due to exact Black-76 lognormal drift (-0.5*sigma^2*T)
    assert 4190.0 <= flip <= 4205.0


def test_zero_gamma_skewed_market():
    # Put-heavy market below 4150, Call-heavy above 4250
    strikes = (
        make_strike(4050.0, call_oi=50, put_oi=6000),
        make_strike(4100.0, call_oi=100, put_oi=4500),
        make_strike(4150.0, call_oi=500, put_oi=2000),
        make_strike(4200.0, call_oi=2500, put_oi=1000),
        make_strike(4250.0, call_oi=5000, put_oi=200),
        make_strike(4300.0, call_oi=7000, put_oi=50),
    )
    snapshot = OptionsSnapshot(symbol="GC", expiry="2026-10-27", timestamp="2026-10-19T00:00:00", strikes=strikes)
    flip = compute_exact_gamma_flip(snapshot, spot_price=4170.0, dte_days=20.0)

    assert flip is not None
    assert 4150.0 <= flip <= 4220.0


def test_zero_gamma_unilateral_market():
    # Pure Long Gamma: All Call OI > Put OI everywhere
    strikes = (
        make_strike(4100.0, call_oi=3000, put_oi=100),
        make_strike(4200.0, call_oi=5000, put_oi=200),
        make_strike(4300.0, call_oi=8000, put_oi=300),
    )
    snapshot = OptionsSnapshot(symbol="GC", expiry="2026-10-27", timestamp="2026-10-19T00:00:00", strikes=strikes)
    flip = compute_exact_gamma_flip(snapshot, spot_price=4200.0)
    assert flip is None  # Pure Long Gamma, no zero crossing


def test_zero_gamma_sparse_or_empty_snapshot():
    s_empty = OptionsSnapshot(symbol="GC", expiry="2026-10-27", timestamp="2026-10-19T00:00:00", strikes=())
    assert compute_exact_gamma_flip(s_empty, spot_price=4200.0) is None

    s_single = OptionsSnapshot(
        symbol="GC",
        expiry="2026-10-27",
        timestamp="2026-10-19T00:00:00",
        strikes=(make_strike(4200.0, 1000, 1000),),
    )
    assert compute_exact_gamma_flip(s_single, spot_price=4200.0) is None
