"""Tests for precomputed static squeeze ladder and O(1) lookup."""
from __future__ import annotations

import time
import pytest
from src.quant_engine.strategy import (
    precompute_squeeze_ladder,
    lookup_precomputed_squeeze,
    PrecomputedSqueezeLevel,
)


def test_precompute_squeeze_ladder_structure():
    """Verify precomputed ladder generates mathematically sound triggers, TPs, and SLs."""
    strikes = [3900.0, 3925.0, 3950.0, 3975.0, 4000.0]
    call_wall = 4000.0
    put_wall = 3925.0

    ladder = precompute_squeeze_ladder(
        strikes=strikes,
        call_wall=call_wall,
        put_wall=put_wall,
        net_gex_by_strike={3900: 5.0, 3950: -5.0, 4000: 10.0},
    )

    assert len(ladder) == 5
    assert 3950.0 in ladder

    lvl_3950 = ladder[3950.0]
    assert isinstance(lvl_3950, PrecomputedSqueezeLevel)
    assert lvl_3950.squeeze_trigger > 3950.0
    assert lvl_3950.squeeze_tp > lvl_3950.squeeze_trigger, "Squeeze TP must be strictly > trigger"
    assert lvl_3950.squeeze_sl < 3950.0, "Squeeze SL must be strictly < strike"
    assert lvl_3950.waterfall_trigger < 3950.0
    assert lvl_3950.waterfall_tp < lvl_3950.waterfall_trigger, "Waterfall TP must be strictly < trigger"
    assert lvl_3950.waterfall_sl > 3950.0, "Waterfall SL must be strictly > strike"
    assert lvl_3950.regime == "SHORT_GAMMA_ACCELERATOR"

    # Wall flags
    assert ladder[4000.0].is_call_wall is True
    assert ladder[3925.0].is_put_wall is True
    assert ladder[3950.0].is_call_wall is False


def test_precompute_squeeze_ladder_with_air_pockets():
    """Verify that an air pocket expands the squeeze TP to the far edge of the pocket."""
    strikes = [3950.0, 3960.0, 3970.0, 4000.0]
    # Air pocket between 3960 and 3990
    air_pockets = [{"from": 3960.0, "to": 3990.0}]

    ladder = precompute_squeeze_ladder(
        strikes=strikes,
        call_wall=4000.0,
        put_wall=3950.0,
        air_pockets=air_pockets,
    )

    lvl_3950 = ladder[3950.0]
    # Since next strike is 3960 which sits in pocket [3960, 3990], TP must reach 3990!
    assert lvl_3950.squeeze_tp >= 3990.0


def test_lookup_precomputed_squeeze_speed_and_accuracy():
    """Verify O(1) / sub-millisecond lookup of immediate upper and lower levels."""
    strikes = [float(k) for k in range(3000, 5001, 5)]
    ladder = precompute_squeeze_ladder(strikes, call_wall=4200.0, put_wall=3800.0)

    # Test spot price at 3967.10
    spot = 3967.10

    t0 = time.perf_counter()
    above, below = lookup_precomputed_squeeze(ladder, spot)
    elapsed_us = (time.perf_counter() - t0) * 1_000_000

    assert above is not None
    assert below is not None
    assert above.strike == 3970.0
    assert below.strike == 3965.0
    # Lookup must be sub-millisecond (< 500 microseconds)
    assert elapsed_us < 500.0, f"Lookup took too long: {elapsed_us:.1f} us"

