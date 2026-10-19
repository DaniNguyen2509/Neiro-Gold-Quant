"""Unit tests for Level State Engine & Air Pocket Detector (Tầng 4)."""
from __future__ import annotations

import pandas as pd
import pytest

from src.quant_engine.level_state import (
    LevelState,
    find_next_major_wall,
    detect_strike_air_pockets,
    evaluate_tactical_level_states,
)


@pytest.fixture
def sample_chain_df() -> pd.DataFrame:
    """Simulates realistic options chain data around 4180 ATM."""
    data = [
        {"strike": 4150.0, "callOpenInterest": 30, "putOpenInterest": 250, "callVolume": 5, "putVolume": 10, "netGEX": -1.2},
        {"strike": 4155.0, "callOpenInterest": 40, "putOpenInterest": 80, "callVolume": 10, "putVolume": 2, "netGEX": -0.8},
        {"strike": 4160.0, "callOpenInterest": 110, "putOpenInterest": 450, "callVolume": 20, "putVolume": 35, "netGEX": 3.5},
        {"strike": 4165.0, "callOpenInterest": 20, "putOpenInterest": 30, "callVolume": 2, "putVolume": 1, "netGEX": -0.2},
        {"strike": 4170.0, "callOpenInterest": 25, "putOpenInterest": 40, "callVolume": 4, "putVolume": 2, "netGEX": -0.3},
        {"strike": 4175.0, "callOpenInterest": 150, "putOpenInterest": 400, "callVolume": 30, "putVolume": 25, "netGEX": -1.5},
        {"strike": 4180.0, "callOpenInterest": 180, "putOpenInterest": 350, "callVolume": 45, "putVolume": 40, "netGEX": -2.0},
        {"strike": 4185.0, "callOpenInterest": 60, "putOpenInterest": 50, "callVolume": 12, "putVolume": 8, "netGEX": -0.5},
        {"strike": 4190.0, "callOpenInterest": 90, "putOpenInterest": 70, "callVolume": 15, "putVolume": 10, "netGEX": -0.4},
        {"strike": 4200.0, "callOpenInterest": 1200, "putOpenInterest": 800, "callVolume": 150, "putVolume": 50, "netGEX": 15.0},
    ]
    return pd.DataFrame(data)


def test_find_next_major_wall_downward(sample_chain_df: pd.DataFrame):
    """When falling below 4175, should find 4160 as the next major defense wall (high Put OI)."""
    wall_strike, oi = find_next_major_wall(sample_chain_df, current_strike=4175.0, direction="DOWN", min_distance=5.0)
    assert wall_strike == 4160.0
    assert oi > 300


def test_find_next_major_wall_upward(sample_chain_df: pd.DataFrame):
    """When breaking above 4185, should find 4200 as the major call wall."""
    wall_strike, oi = find_next_major_wall(sample_chain_df, current_strike=4185.0, direction="UP", min_distance=5.0)
    assert wall_strike == 4200.0
    assert oi > 1000


def test_detect_strike_air_pockets(sample_chain_df: pd.DataFrame):
    """Detects the low-liquidity vacuum zone between 4175 and 4160 (at 4165 and 4170)."""
    pockets = detect_strike_air_pockets(sample_chain_df, start_strike=4175.0, end_strike=4160.0, threshold_ratio=0.35)
    assert len(pockets) >= 1
    # Check that the pocket spans between 4165 and 4170
    assert any(p.start_strike in (4165.0, 4170.0) for p in pockets)


def test_evaluate_level_states_sliced_vacuum_run(sample_chain_df: pd.DataFrame):
    """When spot price is 4168.0 (plunged 7 pts below 4175 support in Short Gamma),
    4175 must be marked as SLICED_VACUUM_RUN with target reaching 4160, not 4170!"""
    meta = {
        "atm_strike": 4180.0,
        "call_wall": 4200.0,
        "put_wall": 4150.0,
        "total_net_gex": -5.2,
    }
    spot_price = 4168.0

    evals = evaluate_tactical_level_states(spot_price, sample_chain_df, meta)
    support_eval = next((e for e in evals if e.strike == 4175.0), None)

    assert support_eval is not None
    assert support_eval.state == LevelState.SLICED_VACUUM_RUN
    assert support_eval.vacuum_target == 4160.0
    assert "CẤM BẮT ĐÁY" in support_eval.notes
    assert support_eval.take_profit <= 4161.0


def test_evaluate_level_states_testing_support(sample_chain_df: pd.DataFrame):
    """When spot price is 4174.5 (testing 4175 within 2.0 pts), state is TESTING."""
    meta = {
        "atm_strike": 4180.0,
        "call_wall": 4200.0,
        "put_wall": 4150.0,
        "total_net_gex": 1.5,
    }
    spot_price = 4174.5

    evals = evaluate_tactical_level_states(spot_price, sample_chain_df, meta)
    support_eval = next((e for e in evals if e.strike == 4175.0), None)

    assert support_eval is not None
    assert support_eval.state == LevelState.TESTING
