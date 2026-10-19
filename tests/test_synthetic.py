"""Unit tests for Tier 2 Synthetic ATM, DTE, and CME Expiry Resolution."""
from __future__ import annotations

import datetime
import pytest

from src.quant_engine.models import OptionsSnapshot, OptionsStrike
from src.quant_engine.synthetic import (
    get_cme_option_expiry_date,
    resolve_front_month_cme_option,
    compute_dynamic_dte,
    find_atm_strike,
    synthetic_atm_pivot,
    implied_straddle,
    sigma_bands,
)


def make_strike(strike: float, call_mid: float, put_mid: float) -> OptionsStrike:
    return OptionsStrike(
        strike=strike,
        call_bid=call_mid - 1.0,
        call_ask=call_mid + 1.0,
        put_bid=put_mid - 1.0,
        put_ask=put_mid + 1.0,
        call_oi=1000,
        put_oi=1000,
        call_volume=100,
        put_volume=100,
    )


def test_get_cme_option_expiry_date_january_boundary():
    """For contract month 1 (January), previous month is December of the prior year."""
    expiry_2027_jan = get_cme_option_expiry_date(2027, 1)
    assert expiry_2027_jan.month == 12
    assert expiry_2027_jan.year == 2026
    assert expiry_2027_jan.weekday() < 5  # Must be a weekday (Mon-Fri)


def test_get_cme_option_expiry_date_regular_month():
    """For contract month 11 (November 2026), previous month is October 2026."""
    expiry_nov = get_cme_option_expiry_date(2026, 11)
    assert expiry_nov.month == 10
    assert expiry_nov.year == 2026
    assert expiry_nov.weekday() < 5


def test_resolve_front_month_cme_option():
    # Pass a date in mid October 2026
    now = datetime.date(2026, 10, 15)
    res = resolve_front_month_cme_option(now=now, underlying_futures="GCZ26")
    assert "option_symbol" in res
    assert res["underlying"] == "GCZ26"
    assert "expiration_date" in res
    assert "barchart_url" in res
    assert res["option_symbol"].startswith("OG")


def test_compute_dynamic_dte_formats():
    now = datetime.datetime(2026, 10, 19, 12, 0, tzinfo=datetime.timezone.utc)

    # 1. Date object
    exp_date = datetime.date(2026, 10, 27)
    dte_date = compute_dynamic_dte(expiry=exp_date, now=now)
    assert 8.0 < dte_date < 9.0

    # 2. Datetime object
    exp_dt = datetime.datetime(2026, 10, 27, 18, 30, tzinfo=datetime.timezone.utc)
    dte_dt = compute_dynamic_dte(expiry=exp_dt, now=now)
    assert pytest.approx(dte_dt, abs=0.01) == 8.27

    # 3. String format 'YYYY-MM-DD'
    dte_str = compute_dynamic_dte(expiry="2026-10-27", now=now)
    assert pytest.approx(dte_str, abs=0.01) == 8.27

    # 4. ISO datetime string
    dte_iso = compute_dynamic_dte(expiry="2026-10-27T18:30:00+00:00", now=now)
    assert pytest.approx(dte_iso, abs=0.01) == 8.27

    # 5. Empty or None -> default_dte
    assert compute_dynamic_dte(expiry=None, now=now, default_dte=8.0) == 8.0

    # 6. Past expiry -> floored at 1 minute (1 / 1440 days)
    past_date = datetime.date(2026, 10, 1)
    dte_past = compute_dynamic_dte(expiry=past_date, now=now)
    assert pytest.approx(dte_past, abs=1e-5) == 1.0 / 1440.0

    # 7. Malformed string -> fallback to default_dte
    assert compute_dynamic_dte(expiry="invalid-date", now=now, default_dte=5.5) == 5.5


def test_atm_pivot_and_sigma_bands():
    strikes = (
        make_strike(4150.0, call_mid=35.0, put_mid=5.0),
        make_strike(4180.0, call_mid=20.0, put_mid=20.0),  # Smallest |Call - Put| = 0
        make_strike(4200.0, call_mid=10.0, put_mid=30.0),
    )
    snapshot = OptionsSnapshot(symbol="GC", expiry="2026-10-27", timestamp="2026-10-19T00:00:00", strikes=strikes)

    atm = find_atm_strike(snapshot)
    assert atm.strike == 4180.0

    pivot = synthetic_atm_pivot(snapshot)
    # 4180 + 20 - 20 = 4180.0
    assert pivot == 4180.0

    straddle = implied_straddle(snapshot)
    # 20 + 20 = 40.0
    assert straddle == 40.0

    upper_1s, lower_1s = sigma_bands(pivot, straddle, factor=1.0)
    assert upper_1s == 4220.0
    assert lower_1s == 4140.0

    upper_085, lower_085 = sigma_bands(pivot, straddle, factor=0.85)
    assert upper_085 == 4180.0 + 34.0
    assert lower_085 == 4180.0 - 34.0


def test_find_atm_strike_empty_snapshot():
    snapshot = OptionsSnapshot(symbol="GC", expiry="2026-10-27", timestamp="2026-10-19T00:00:00", strikes=())
    with pytest.raises(ValueError, match="Empty options chain"):
        find_atm_strike(snapshot)
