"""Unit tests for Tier 3 Dealer Positioning and Wall Detection."""
from __future__ import annotations

import pytest

from src.quant_engine.dealer import (
    find_walls,
    gamma_squeeze_trigger,
    gamma_waterfall_trigger,
    detect_pin_risk,
)
from src.quant_engine.models import OptionsSnapshot, OptionsStrike, Wall


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


def test_find_walls_empty_snapshot():
    snapshot = OptionsSnapshot(symbol="GC", expiry="2026-10-27", timestamp="2026-10-19T00:00:00")
    call_walls, put_walls = find_walls(snapshot)
    assert call_walls == []
    assert put_walls == []


def test_find_walls_ranking():
    strikes = (
        make_strike(4150.0, call_oi=1000, put_oi=5000),
        make_strike(4180.0, call_oi=3000, put_oi=2000),
        make_strike(4200.0, call_oi=6000, put_oi=1500),
        make_strike(4250.0, call_oi=8000, put_oi=500),
    )
    snapshot = OptionsSnapshot(symbol="GC", expiry="2026-10-27", timestamp="2026-10-19T00:00:00", strikes=strikes)
    call_walls, put_walls = find_walls(snapshot, top_n=2)

    assert len(call_walls) == 2
    assert call_walls[0].strike == 4250.0
    assert call_walls[0].oi == 8000
    assert call_walls[0].side == "call"
    assert call_walls[0].rank == 1

    assert call_walls[1].strike == 4200.0
    assert call_walls[1].oi == 6000
    assert call_walls[1].rank == 2

    assert len(put_walls) == 2
    assert put_walls[0].strike == 4150.0
    assert put_walls[0].oi == 5000
    assert put_walls[0].side == "put"
    assert put_walls[0].rank == 1

    assert put_walls[1].strike == 4180.0
    assert put_walls[1].oi == 2000
    assert put_walls[1].rank == 2


def test_gamma_triggers():
    call_wall = Wall(strike=4200.0, oi=5000, volume=100, side="call", rank=1)
    put_wall = Wall(strike=4100.0, oi=6000, volume=100, side="put", rank=1)

    trigger_up = gamma_squeeze_trigger(call_wall, call_mid_at_wall=15.5)
    assert trigger_up == 4215.5

    trigger_down = gamma_waterfall_trigger(put_wall, put_mid_at_wall=12.25)
    assert trigger_down == 4087.75


def test_detect_pin_risk():
    # Less than 2 strikes -> None
    s_small = OptionsSnapshot(symbol="GC", expiry="2026-10-27", timestamp="2026-10-19T00:00:00", strikes=(make_strike(4180.0, 1000, 1000),))
    assert detect_pin_risk(s_small) is None

    # Case 1: Overlap at 4180 (top 2 in both calls and puts)
    strikes_overlap = (
        make_strike(4150.0, call_oi=500, put_oi=5000),   # put rank 1
        make_strike(4180.0, call_oi=6000, put_oi=4000),  # call rank 1, put rank 2 -> Pin Risk!
        make_strike(4200.0, call_oi=5000, put_oi=200),   # call rank 2
        make_strike(4250.0, call_oi=100, put_oi=100),
    )
    s_overlap = OptionsSnapshot(symbol="GC", expiry="2026-10-27", timestamp="2026-10-19T00:00:00", strikes=strikes_overlap)
    assert detect_pin_risk(s_overlap) == 4180.0

    # Case 2: No overlap
    strikes_no_overlap = (
        make_strike(4100.0, call_oi=100, put_oi=7000),
        make_strike(4150.0, call_oi=200, put_oi=6000),
        make_strike(4200.0, call_oi=8000, put_oi=300),
        make_strike(4250.0, call_oi=7500, put_oi=200),
    )
    s_no_overlap = OptionsSnapshot(symbol="GC", expiry="2026-10-27", timestamp="2026-10-19T00:00:00", strikes=strikes_no_overlap)
    assert detect_pin_risk(s_no_overlap) is None


def test_find_walls_otm_filtering():
    """Verify that ITM strikes with high legacy OI are filtered out when spot_price is provided."""
    strikes = (
        make_strike(4000.0, call_oi=99999, put_oi=1000),  # Deep ITM call with massive OI
        make_strike(4100.0, call_oi=1000, put_oi=5000),   # OTM put
        make_strike(4150.0, call_oi=3000, put_oi=4000),   # OTM put
        make_strike(4200.0, call_oi=6000, put_oi=500),    # OTM call
        make_strike(4250.0, call_oi=8000, put_oi=99999),  # Deep ITM put with massive OI
    )
    snapshot = OptionsSnapshot(symbol="GC", expiry="2026-10-27", timestamp="2026-10-19T00:00:00", strikes=strikes)
    spot = 4160.0

    call_walls, put_walls = find_walls(snapshot, top_n=2, spot_price=spot)

    # Call wall must be >= spot (4160)
    assert all(w.strike >= spot for w in call_walls)
    assert call_walls[0].strike == 4250.0  # Max OTM call OI
    assert call_walls[1].strike == 4200.0

    # Put wall must be <= spot (4160)
    assert all(w.strike <= spot for w in put_walls)
    assert put_walls[0].strike == 4100.0  # Max OTM put OI
    assert put_walls[1].strike == 4150.0
