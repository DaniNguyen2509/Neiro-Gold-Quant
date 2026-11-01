"""Unit tests for src/collector/gold_collector.py."""
import math
import pytest
import pandas as pd
from src.collector.gold_collector import (
    clean_num,
    calculate_dte,
    black76_greeks_single,
    estimate_iv_brent,
    GoldCollector,
    generate_benchmark_gold_chain,
)


def test_clean_num():
    assert clean_num(10.5) == 10.5
    assert clean_num(None) == 0.0
    assert clean_num(float("nan")) == 0.0
    assert clean_num("$2,750.25") == 2750.25
    assert clean_num("invalid", default=99.0) == 99.0


def test_calculate_dte():
    dte = calculate_dte("2030-12-31")
    assert dte > 100.0

    dte_today = calculate_dte("2020-01-01")
    assert dte_today > 0.0  # Scales to min fraction


def test_black76_greeks_single():
    f = 2700.0
    k = 2700.0
    t = 30.0 / 365.0
    r = 0.045
    sigma = 0.18

    cg = black76_greeks_single(f, k, t, r, sigma, is_call=True)
    pg = black76_greeks_single(f, k, t, r, sigma, is_call=False)

    assert cg["price"] > 0.0
    assert pg["price"] > 0.0
    assert 0.4 < cg["delta"] < 0.6
    assert -0.6 < pg["delta"] < -0.4
    assert cg["gamma"] > 0.0
    assert cg["gamma"] == pytest.approx(pg["gamma"], rel=1e-5)
    assert cg["vega"] > 0.0
    assert cg["vanna"] != 0.0 or abs(cg["vanna"]) < 1e-4


def test_estimate_iv_brent_inversion():
    f = 2700.0
    k = 2750.0
    t = 15.0 / 365.0
    r = 0.045
    target_iv = 0.22

    cg = black76_greeks_single(f, k, t, r, target_iv, is_call=True)
    recovered_iv = estimate_iv_brent(cg["price"], f, k, t, r, is_call=True)

    assert recovered_iv == pytest.approx(target_iv, abs=1e-3)


def test_generate_benchmark_gold_chain():
    spot = 2700.0
    df = generate_benchmark_gold_chain(spot=spot)

    assert not df.empty
    assert len(df) == 31  # 2 * 15 + 1
    required_cols = [
        "strike", "callBid", "callAsk", "callMid", "callOpenInterest", "callIV", "callDelta", "callGamma",
        "putBid", "putAsk", "putMid", "putOpenInterest", "putIV", "putDelta", "putGamma",
        "netGEX", "netVEX", "netCHEX", "expirationDate", "dte",
    ]
    for col in required_cols:
        assert col in df.columns

    # Verify Gold Call Skew: OTM Call IV (strike > spot) should be higher than OTM Put IV (strike < spot)
    otm_call_iv = df[df["strike"] == spot + 30.0]["callIV"].iloc[0]
    atm_iv = df[df["strike"] == spot]["callIV"].iloc[0]
    assert otm_call_iv > atm_iv

    # Verify presence of Call Wall & Put Wall spikes
    max_c_oi_strike = df.loc[df["callOpenInterest"].idxmax(), "strike"]
    max_p_oi_strike = df.loc[df["putOpenInterest"].idxmax(), "strike"]
    assert max_c_oi_strike == spot + 40.0
    assert max_p_oi_strike == spot - 40.0


def test_gold_collector_initialization_and_prices():
    collector = GoldCollector(symbol="GLD", futures_symbol="GC=F", timeout=5)
    prices = collector.get_underlying_prices()

    assert "underlying" in prices
    assert "futures" in prices
    assert "basis" in prices
    assert "r_rate" in prices
    assert "carry_rate" in prices
    assert "f0_theoretical" in prices
    assert prices["basis"] > 5.0  # GC ~ 2700 / GLD ~ 250 => ~ 10.8

