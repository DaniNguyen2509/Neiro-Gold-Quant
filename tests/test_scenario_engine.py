"""Unit tests for Scenario Engine (src/quant_engine/scenario_engine.py)."""
from __future__ import annotations

import pytest
from src.quant_engine.scenario_engine import (
    AlertLevel,
    ActionDirective,
    evaluate_market_scenarios,
)


def test_scenario_kb1_pinning_box():
    """Verify KB-1 activation when price is sandwiched inside pinning range."""
    res = evaluate_market_scenarios(
        spot_price=4150.0,
        atm_strike=4150.0,
        strike_above=4175.0,
        strike_below=4125.0,
        call_wall=4250.0,
        call_wall_oi=5000,
        put_wall=4100.0,
        put_wall_oi=6000,
        regime="LONG_GAMMA",
        total_chex=-1.5,
    )
    assert res.active_scenario.code == "KB-1"
    assert res.active_scenario.is_active is True
    assert res.active_scenario.alert_level == AlertLevel.YELLOW
    assert res.active_scenario.action == ActionDirective.WAIT
    assert "ĐỨNG NGOÀI" in res.active_scenario.action_label


def test_scenario_kb2_call_defense():
    """Verify KB-2 activation when price tests strike_above."""
    res = evaluate_market_scenarios(
        spot_price=4174.5,
        atm_strike=4150.0,
        strike_above=4175.0,
        strike_below=4125.0,
        call_wall=4250.0,
        call_wall_oi=5000,
        put_wall=4100.0,
        put_wall_oi=6000,
    )
    assert res.active_scenario.code == "KB-2"
    assert res.active_scenario.action == ActionDirective.SELL_FADE
    assert res.active_scenario.take_profit == 4150.0


def test_scenario_kb3_gamma_squeeze():
    """Verify KB-3 Red Alert activation when price breaches above strike_above."""
    res = evaluate_market_scenarios(
        spot_price=4177.5,
        atm_strike=4150.0,
        strike_above=4175.0,
        strike_below=4125.0,
        call_wall=4250.0,
        call_wall_oi=5000,
        put_wall=4100.0,
        put_wall_oi=6000,
        major_up_wall=4250.0,
    )
    assert res.active_scenario.code == "KB-3"
    assert res.active_scenario.alert_level == AlertLevel.RED
    assert res.active_scenario.action == ActionDirective.BUY_BREAKOUT
    assert res.active_scenario.take_profit == 4249.0


def test_scenario_kb4_put_defense():
    """Verify KB-4 activation when price tests strike_below."""
    res = evaluate_market_scenarios(
        spot_price=4126.0,
        atm_strike=4150.0,
        strike_above=4175.0,
        strike_below=4125.0,
        call_wall=4250.0,
        call_wall_oi=5000,
        put_wall=4100.0,
        put_wall_oi=6000,
    )
    assert res.active_scenario.code == "KB-4"
    assert res.active_scenario.alert_level == AlertLevel.GREEN
    assert res.active_scenario.action == ActionDirective.BUY_REBOUND


def test_scenario_kb5_air_pocket_breakdown():
    """Verify KB-5 Red Alert activation when price breaches below strike_below."""
    res = evaluate_market_scenarios(
        spot_price=4122.0,
        atm_strike=4150.0,
        strike_above=4175.0,
        strike_below=4125.0,
        call_wall=4250.0,
        call_wall_oi=5000,
        put_wall=4100.0,
        put_wall_oi=6000,
        major_down_wall=4100.0,
    )
    assert res.active_scenario.code == "KB-5"
    assert res.active_scenario.alert_level == AlertLevel.RED
    assert res.active_scenario.action == ActionDirective.SELL_BREAKDOWN
    assert "CẤM BẮT ĐÁY" in res.active_scenario.action_label
    assert res.active_scenario.take_profit == 4101.0


def test_scenario_kb1_real_market_case_4140():
    """Verify that when Gold price is at 4140.20 (between support 4125 and resistance 4150),
    KB-1 is active and KB-5 is strictly INACTIVE, even if ITM put wall is passed.
    """
    res = evaluate_market_scenarios(
        spot_price=4140.20,
        atm_strike=4150.0,
        strike_above=4150.0,
        strike_below=4125.0,
        call_wall=4200.0,
        call_wall_oi=1362,
        put_wall=4100.0,
        put_wall_oi=394,
    )
    assert res.active_scenario.code == "KB-1"
    assert res.active_scenario.is_active is True

    # Assert KB-5 is NOT active
    kb5 = next(s for s in res.all_scenarios if s.code == "KB-5")
    assert kb5.is_active is False
    assert "Thủng dứt khoát < $4,123.50 (Hiện tại: $4,140.20)" in kb5.condition_desc


def test_scenario_kb5_never_triggers_when_price_above_support():
    """Even if an erroneous ITM put strike (e.g. 4200) is passed, price at 4140.0
    must NEVER trigger KB-5 because 4140.0 > 4125.0 - 1.50 = 4123.50.
    """
    res = evaluate_market_scenarios(
        spot_price=4140.0,
        atm_strike=4150.0,
        strike_above=4150.0,
        strike_below=4125.0,
        call_wall=4200.0,
        call_wall_oi=1362,
        put_wall=4200.0,  # Rogue ITM strike
        put_wall_oi=1271,
    )
    assert res.active_scenario.code != "KB-5"
    kb5 = next(s for s in res.all_scenarios if s.code == "KB-5")
    assert kb5.is_active is False

