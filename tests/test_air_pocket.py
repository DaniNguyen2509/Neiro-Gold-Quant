"""Unit tests for Tier 3 OI Air Pocket Detection."""
from __future__ import annotations

import pytest

from src.quant_engine.air_pocket import detect_air_pockets
from src.quant_engine.models import AirPocket, OptionsSnapshot, OptionsStrike


def make_strike(strike: float, call_oi: int, put_oi: int) -> OptionsStrike:
    return OptionsStrike(
        strike=strike,
        call_bid=10.0,
        call_ask=12.0,
        put_bid=10.0,
        put_ask=12.0,
        call_oi=call_oi,
        put_oi=put_oi,
        call_volume=100,
        put_volume=100,
    )


def test_detect_air_pockets_empty_snapshot():
    snapshot = OptionsSnapshot(symbol="GC", expiry="2026-10-27", timestamp="2026-10-19T00:00:00")
    pockets = detect_air_pockets(snapshot, atm_strike=4180.0, wall_strike=4250.0)
    assert pockets == []


def test_detect_air_pockets_out_of_zone():
    strikes = (
        make_strike(4000.0, 5000, 5000),
        make_strike(4050.0, 5000, 5000),
    )
    snapshot = OptionsSnapshot(symbol="GC", expiry="2026-10-27", timestamp="2026-10-19T00:00:00", strikes=strikes)
    pockets = detect_air_pockets(snapshot, atm_strike=4180.0, wall_strike=4250.0)
    assert pockets == []


def test_detect_air_pockets_single_pocket():
    """Strikes 4180 (OI=1000), 4190 (OI=50), 4200 (OI=50), 4210 (OI=1000).
    Avg OI = 525. 35% threshold = 183.75.
    4190 and 4200 are below threshold -> forms an air pocket from 4190 to 4200.
    """
    strikes = (
        make_strike(4180.0, 500, 500),   # 1000
        make_strike(4190.0, 25, 25),     # 50  <-- Air pocket
        make_strike(4200.0, 25, 25),     # 50  <-- Air pocket
        make_strike(4210.0, 500, 500),   # 1000
    )
    snapshot = OptionsSnapshot(symbol="GC", expiry="2026-10-27", timestamp="2026-10-19T00:00:00", strikes=strikes)
    pockets = detect_air_pockets(snapshot, atm_strike=4180.0, wall_strike=4210.0, threshold_pct=0.35)

    assert len(pockets) == 1
    assert pockets[0].low_strike == 4190.0
    assert pockets[0].high_strike == 4200.0
    assert pockets[0].avg_oi == 50.0
    assert pockets[0].threshold_pct == 0.35


def test_detect_air_pockets_trailing_pocket():
    """Air pocket extending to the very boundary of the wall."""
    strikes = (
        make_strike(4180.0, 1000, 1000), # 2000
        make_strike(4190.0, 10, 10),     # 20  <-- Air pocket trailing to edge
    )
    snapshot = OptionsSnapshot(symbol="GC", expiry="2026-10-27", timestamp="2026-10-19T00:00:00", strikes=strikes)
    pockets = detect_air_pockets(snapshot, atm_strike=4180.0, wall_strike=4190.0)

    assert len(pockets) == 1
    assert pockets[0].low_strike == 4190.0
    assert pockets[0].high_strike == 4190.0


def test_detect_air_pockets_no_pockets_when_dense():
    """All strikes have ample OI -> no air pockets."""
    strikes = (
        make_strike(4180.0, 1000, 1000),
        make_strike(4190.0, 950, 950),
        make_strike(4200.0, 1050, 1050),
    )
    snapshot = OptionsSnapshot(symbol="GC", expiry="2026-10-27", timestamp="2026-10-19T00:00:00", strikes=strikes)
    pockets = detect_air_pockets(snapshot, atm_strike=4180.0, wall_strike=4200.0)
    assert pockets == []
