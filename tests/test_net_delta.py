import math
import pytest
from src.quant_engine.dealer import compute_net_delta_positions
from src.quant_engine.models import OptionsSnapshot, OptionsStrike


def test_put_call_parity_delta_sum():
    """Verify Black-76 Delta satisfies Put-Call Parity: Delta_call - Delta_put = exp(-rT) ~= 1.00."""
    strikes = [
        OptionsStrike(
            strike=k,
            call_bid=10.0, call_ask=10.5, call_oi=100, call_volume=10,
            put_bid=10.0, put_ask=10.5, put_oi=100, put_volume=10,
        )
        for k in [4085.0, 4100.0, 4105.0, 4130.0]
    ]
    snapshot = OptionsSnapshot(symbol="GCZ26", expiry="2026-11-25", timestamp="2026-10-22", strikes=tuple(strikes))
    res = compute_net_delta_positions(snapshot, spot_price=4105.0, r=0.045, dte_days=30.0, default_iv=0.16)

    t_years = 30.0 / 365.0
    expected_disc = math.exp(-0.045 * t_years)

    for k, data in res["strikes"].items():
        c_delta = data["call_delta"]
        p_delta = data["put_delta"]
        # Invariant: c_delta - p_delta == expected_disc
        assert math.isclose(c_delta - p_delta, expected_disc, abs_tol=1e-3)
        # Invariant: |c_delta| + |p_delta| ~= 1.00
        assert math.isclose(abs(c_delta) + abs(p_delta), expected_disc, abs_tol=1e-3)


def test_atm_delta_neutral():
    """Verify that at exact ATM Strike, call delta ~= +0.50, put delta ~= -0.50 and their algebraic sum ~= 0."""
    strike_atm = 4105.0
    strikes = [
        OptionsStrike(
            strike=strike_atm,
            call_bid=50.0, call_ask=50.5, call_oi=1000, call_volume=50,
            put_bid=50.0, put_ask=50.5, put_oi=1000, put_volume=50,
        )
    ]
    snapshot = OptionsSnapshot(symbol="GCZ26", expiry="2026-11-25", timestamp="2026-10-22", strikes=tuple(strikes))
    res = compute_net_delta_positions(snapshot, spot_price=strike_atm, r=0.0, dte_days=30.0, default_iv=0.16)

    data = res["strikes"][strike_atm]
    # When r=0, ATM Call delta is > 0.50 due to 0.5*sigma^2*T convexity term, but very close to 0.50
    assert 0.49 <= data["call_delta"] <= 0.55
    assert -0.55 <= data["put_delta"] <= -0.49
    # Symmetrical OI of 1000/1000 at ATM produces near-zero net position
    assert abs(data["net_contracts"]) < 50.0


def test_user_case_strike_4100():
    """Verify user's exact manual calculation at Strike 4,100:
    502 Call OI (Delta ~= +0.5194) -> +260.7 contracts
    1,706 Put OI (Delta ~= -0.4760) -> -812.0 contracts
    Net Delta ~= -551.3 contracts (heavy Put tilt).
    """
    strikes = [
        OptionsStrike(
            strike=4100.0,
            call_bid=30.0, call_ask=30.5, call_oi=502, call_volume=10,
            put_bid=25.0, put_ask=25.5, put_oi=1706, put_volume=10,
        )
    ]
    snapshot = OptionsSnapshot(symbol="GCZ26", expiry="2026-11-25", timestamp="2026-10-22", strikes=tuple(strikes))
    # At spot=4106, 4100 has d1 slightly positive giving call delta ~0.52 and put delta ~ -0.48
    res = compute_net_delta_positions(snapshot, spot_price=4106.0, r=0.045, dte_days=30.0, default_iv=0.16)

    data = res["strikes"][4100.0]
    # Check that Put contracts dominate and net contracts is negative around -550
    assert data["net_contracts"] < -450.0
    assert data["call_contracts"] > 0
    assert data["put_contracts"] < 0
    assert res["regime"] == "BEARISH_PUT_TILT"
    assert res["max_tilt_strike"] == 4100.0


def test_edge_cases_empty_and_zero_spot():
    """Verify graceful handling for empty snapshot and zero spot."""
    empty_snap = OptionsSnapshot(symbol="GCZ26", expiry="", timestamp="", strikes=())
    res_empty = compute_net_delta_positions(empty_snap, spot_price=4100.0)
    assert res_empty["total_net_delta"] == 0.0
    assert res_empty["max_tilt_strike"] is None
    assert res_empty["regime"] == "NEUTRAL"

    snap_with_strike = OptionsSnapshot(
        symbol="GCZ26", expiry="", timestamp="",
        strikes=(OptionsStrike(4100.0, 1, 2, 10, 1, 1, 2, 10, 1),)
    )
    res_zero_spot = compute_net_delta_positions(snap_with_strike, spot_price=0.0)
    assert res_zero_spot["total_net_delta"] == 0.0
