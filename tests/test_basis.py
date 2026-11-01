"""Unit tests for Auto-Basis Sync and Live Spot Resolution.

Verifies:
1. Mathematical Sign Convention:
   basis = spot - futures (negative in contango, positive in backwardation).
   spot_level = futures_level + basis.
2. convert_levels_to_spot transformations across all QuantLevels fields.
3. Market hours checking (weekend close vs weekday open).
4. Live spot fetching with multi-source fallback (Gold-API -> Binance PAXG).
5. Thread-safe TTL cache behavior.
6. Relative sanity outlier rejection.
"""
from __future__ import annotations

import datetime
import json
import time
import unittest.mock as mock
import pytest

from src.quant_engine.basis import (
    compute_basis,
    convert_to_spot,
    convert_levels_to_spot,
    resolve_dynamic_basis,
    resolve_dynamic_basis_with_source,
    fetch_live_spot_gold_price,
    is_gold_spot_market_open,
    clear_spot_cache,
    SpotQuote,
)
from src.quant_engine.models import QuantLevels, Wall


@pytest.fixture(autouse=True)
def reset_cache():
    """Ensure clean cache before and after every test."""
    clear_spot_cache()
    yield
    clear_spot_cache()


# ---------------------------------------------------------------------------
# 1. Mathematical Convention & Invariants
# ---------------------------------------------------------------------------

def test_compute_basis_contango():
    """Contango: Futures > Spot => Basis is negative."""
    spot = 4156.0
    futures = 4180.0
    basis = compute_basis(spot, futures)
    assert basis == -24.0
    assert convert_to_spot(futures, basis) == 4156.0


def test_compute_basis_backwardation():
    """Backwardation: Spot > Futures => Basis is positive."""
    spot = 4180.0
    futures = 4156.0
    basis = compute_basis(spot, futures)
    assert basis == +24.0
    assert convert_to_spot(futures, basis) == 4180.0


def test_basis_conversion_identity_invariant():
    """Mathematical identity: convert_to_spot(F, compute_basis(S, F)) == S."""
    test_cases = [
        (4156.25, 4180.50),
        (2650.00, 2674.00),
        (3000.00, 3000.00),
        (4200.00, 4175.00),
    ]
    for spot, futures in test_cases:
        basis = compute_basis(spot, futures)
        converted_spot = convert_to_spot(futures, basis)
        assert pytest.approx(converted_spot, rel=1e-6) == spot
        # Reverse identity: futures = spot - basis
        assert pytest.approx(converted_spot - basis, rel=1e-6) == futures


# ---------------------------------------------------------------------------
# 2. Level State & QuantLevels Conversion
# ---------------------------------------------------------------------------

def test_convert_levels_to_spot_full():
    """Verify all levels in QuantLevels are converted to spot terms accurately."""
    basis = -24.0  # Contango: spot is 24 USD below futures
    levels = QuantLevels(
        synthetic_atm_pivot=4180.0,
        implied_straddle=50.0,
        sigma_1_upper=4230.0,
        sigma_1_lower=4130.0,
        sigma_085_upper=4222.5,
        sigma_085_lower=4137.5,
        call_wall_1=Wall(strike=4250.0, oi=5000, volume=1200, side="call", rank=1),
        put_wall_1=Wall(strike=4100.0, oi=6200, volume=1500, side="put", rank=1),
        gamma_squeeze_up=4265.0,
        gamma_waterfall_down=4085.0,
    )

    converted = convert_levels_to_spot(levels, basis)

    assert converted["synthetic_atm_pivot"] == 4156.0
    assert converted["sigma_1_upper"] == 4206.0
    assert converted["sigma_1_lower"] == 4106.0
    assert converted["sigma_085_upper"] == 4198.5
    assert converted["sigma_085_lower"] == 4113.5
    assert converted["call_wall_1"] == 4226.0
    assert converted["put_wall_1"] == 4076.0
    assert converted["gamma_squeeze_up"] == 4241.0
    assert converted["gamma_waterfall_down"] == 4061.0


def test_convert_levels_to_spot_partial():
    """Optional wall triggers can be None without raising errors."""
    basis = -24.0
    levels = QuantLevels(
        synthetic_atm_pivot=4180.0,
        implied_straddle=50.0,
        sigma_1_upper=4230.0,
        sigma_1_lower=4130.0,
        sigma_085_upper=4222.5,
        sigma_085_lower=4137.5,
        call_wall_1=None,
        put_wall_1=None,
        gamma_squeeze_up=None,
        gamma_waterfall_down=None,
    )

    converted = convert_levels_to_spot(levels, basis)
    assert converted["synthetic_atm_pivot"] == 4156.0
    assert "call_wall_1" not in converted
    assert "put_wall_1" not in converted
    assert "gamma_squeeze_up" not in converted
    assert "gamma_waterfall_down" not in converted


# ---------------------------------------------------------------------------
# 3. Market Hours Detection
# ---------------------------------------------------------------------------

def test_is_gold_spot_market_open():
    """Gold spot market closes Friday 22:00 UTC and opens Sunday 22:00 UTC."""
    # Wednesday 14:00 UTC -> Open
    wed = datetime.datetime(2026, 10, 21, 14, 0, tzinfo=datetime.timezone.utc)
    assert is_gold_spot_market_open(wed) is True

    # Friday 21:59 UTC -> Open
    fri_open = datetime.datetime(2026, 10, 23, 21, 59, tzinfo=datetime.timezone.utc)
    assert is_gold_spot_market_open(fri_open) is True

    # Friday 22:01 UTC -> Closed
    fri_closed = datetime.datetime(2026, 10, 23, 22, 1, tzinfo=datetime.timezone.utc)
    assert is_gold_spot_market_open(fri_closed) is False

    # Saturday 12:00 UTC -> Closed
    sat = datetime.datetime(2026, 10, 24, 12, 0, tzinfo=datetime.timezone.utc)
    assert is_gold_spot_market_open(sat) is False

    # Sunday 21:59 UTC -> Closed
    sun_closed = datetime.datetime(2026, 10, 25, 21, 59, tzinfo=datetime.timezone.utc)
    assert is_gold_spot_market_open(sun_closed) is False

    # Sunday 22:01 UTC -> Open
    sun_open = datetime.datetime(2026, 10, 25, 22, 1, tzinfo=datetime.timezone.utc)
    assert is_gold_spot_market_open(sun_open) is True


# ---------------------------------------------------------------------------
# 4. Live Spot Gold Fetching & TTL Caching
# ---------------------------------------------------------------------------

def test_fetch_live_spot_gold_primary_success():
    """Pure CME Futures invariant: External spot scraping is decommissioned, returns None by design."""
    from src.quant_engine.basis import clear_spot_cache
    clear_spot_cache()
    quote = fetch_live_spot_gold_price()
    assert quote is None


def test_fetch_live_spot_gold_fallback_to_binance():
    """Pure CME Futures invariant: returns None without external scraping."""
    from src.quant_engine.basis import clear_spot_cache
    clear_spot_cache()
    quote = fetch_live_spot_gold_price()
    assert quote is None


def test_fetch_live_spot_gold_cache_ttl():
    """Injected cached quote is reused under TTL without network requests."""
    from src.quant_engine import basis as b_mod
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    injected = SpotQuote(price=4156.50, source="MOCK", fetched_at=now)
    with b_mod._cache_lock:
        b_mod._cached_quote = injected
        b_mod._last_fetch_mono = time.monotonic()

    quote1 = fetch_live_spot_gold_price()
    quote2 = fetch_live_spot_gold_price()
    assert quote1 == quote2
    assert quote1 is not None
    assert quote1.price == 4156.50
    b_mod.clear_spot_cache()


def test_fetch_live_spot_gold_all_fail():
    """When all endpoints fail, returns None gracefully without throwing uncaught exceptions."""
    import urllib.error
    with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Timeout")):
        quote = fetch_live_spot_gold_price()
        assert quote is None


# ---------------------------------------------------------------------------
# 5. Dynamic Basis Resolution & Outlier Guards
# ---------------------------------------------------------------------------

def test_resolve_dynamic_basis_with_mocked_spot():
    """Live spot 4148.0 vs Futures 4172.0 => Basis = 4148 - 4172 = -24.0 USD."""
    quote = SpotQuote(price=4148.0, source="Gold-API", fetched_at=datetime.datetime.now(datetime.timezone.utc))
    with mock.patch("src.quant_engine.basis.fetch_live_spot_gold_price", return_value=quote):
        with mock.patch("src.quant_engine.basis.is_gold_spot_market_open", return_value=True):
            futures_price = 4172.0
            basis = resolve_dynamic_basis(futures_price)
            assert basis == -24.0


def test_resolve_dynamic_basis_fallback_when_offline():
    """When live spot is unavailable, gracefully fall back to fallback_basis."""
    with mock.patch("src.quant_engine.basis.fetch_live_spot_gold_price", return_value=None):
        futures_price = 4172.0
        basis = resolve_dynamic_basis(futures_price, fallback_basis=-24.0)
        assert basis == -24.0


def test_resolve_dynamic_basis_outlier_rejection():
    """If API returns off-market price (e.g. 4146.15 vs 4181.0, spread=34.85 outside [21, 27]), reject and fallback."""
    quote = SpotQuote(price=4146.15, source="Gold-API-Stale", fetched_at=datetime.datetime.now(datetime.timezone.utc))
    with mock.patch("src.quant_engine.basis.fetch_live_spot_gold_price", return_value=quote):
        with mock.patch("src.quant_engine.basis.is_gold_spot_market_open", return_value=True):
            futures_price = 4181.0
            basis, source = resolve_dynamic_basis_with_source(futures_price, fallback_basis=-24.0)
            assert basis == -24.0
            assert source == "CALIBRATED"


def test_resolve_dynamic_basis_with_source_live():
    """If API returns valid price within [21, 27] spread (e.g. 4157.0 vs 4181.0), accept as LIVE."""
    quote = SpotQuote(price=4157.0, source="Gold-API-Live", fetched_at=datetime.datetime.now(datetime.timezone.utc))
    with mock.patch("src.quant_engine.basis.fetch_live_spot_gold_price", return_value=quote):
        with mock.patch("src.quant_engine.basis.is_gold_spot_market_open", return_value=True):
            futures_price = 4181.0
            basis, source = resolve_dynamic_basis_with_source(futures_price, fallback_basis=-24.0)
            assert basis == -24.0
            assert source == "LIVE"


def test_resolve_dynamic_basis_weekend_fallback():
    """When market is closed (weekend), do not trust live proxy and use fallback_basis."""
    quote = SpotQuote(price=4148.0, source="Binance-PAXG", fetched_at=datetime.datetime.now(datetime.timezone.utc))
    with mock.patch("src.quant_engine.basis.fetch_live_spot_gold_price", return_value=quote):
        with mock.patch("src.quant_engine.basis.is_gold_spot_market_open", return_value=False):
            futures_price = 4172.0
            basis, source = resolve_dynamic_basis_with_source(futures_price, fallback_basis=-24.0)
            assert basis == -24.0
            assert source == "WEEKEND_FALLBACK"


def test_resolve_dynamic_basis_with_none_futures():
    """When futures price is None or invalid, safely return calibrated fallback."""
    basis, source = resolve_dynamic_basis_with_source(None, fallback_basis=-24.0)
    assert basis == -24.0
    assert source == "CALIBRATED"


def test_fetch_live_cme_futures_price_mock_success():
    """Verify live CME futures price query with mocked direct HTTP response."""
    from src.quant_engine.basis import clear_spot_cache, fetch_live_cme_futures_price

    clear_spot_cache()
    fake_response = mock.MagicMock()
    fake_response.status = 200
    fake_response.read.return_value = json.dumps({
        "chart": {"result": [{"meta": {"regularMarketPrice": 4165.50}}]}
    }).encode("utf-8")
    fake_response.__enter__.return_value = fake_response

    with mock.patch("urllib.request.urlopen", return_value=fake_response):
        price = fetch_live_cme_futures_price()
        assert price == 4165.50


def test_fetch_live_cme_futures_price_mock_failure():
    """When both HTTP and yfinance fail, returns None without crashing."""
    from src.quant_engine.basis import clear_spot_cache, fetch_live_cme_futures_price

    clear_spot_cache()
    with mock.patch("urllib.request.urlopen", side_effect=RuntimeError("HTTP error")):
        with mock.patch("yfinance.Ticker", side_effect=RuntimeError("yfinance error")):
            price = fetch_live_cme_futures_price()
            assert price is None


def test_fetch_live_cme_m5_tape_mock_success():
    """Validates M5 candle extraction, volume spike detection, and pattern recognition."""
    from src.quant_engine.basis import fetch_live_cme_m5_tape

    fake_response = mock.MagicMock()
    fake_response.status = 200
    fake_response.read.return_value = json.dumps({
        "chart": {
            "result": [{
                "meta": {
                    "regularMarketPrice": 4143.20,
                    "regularMarketDayHigh": 4166.50,
                    "regularMarketDayLow": 4134.50,
                },
                "timestamp": [1792482000, 1792482300, 1792482600, 1792482900],
                "indicators": {
                    "quote": [{
                        "open": [4145.0, 4142.0, 4140.0, 4139.0],
                        "high": [4148.0, 4144.0, 4142.0, 4143.2],
                        "low": [4144.0, 4141.0, 4138.0, 4136.6],
                        "close": [4147.0, 4143.0, 4139.0, 4143.2],
                        "volume": [200, 250, 300, 722],
                    }]
                }
            }]
        }
    }).encode("utf-8")
    fake_response.__enter__.return_value = fake_response

    with mock.patch("urllib.request.urlopen", return_value=fake_response):
        tape = fetch_live_cme_m5_tape(limit=4)
        assert tape["available"] is True
        assert tape["day_high"] == 4166.50
        assert tape["day_low"] == 4134.50
        assert tape["day_range"] == 32.00
        assert len(tape["candles"]) == 4

        # Last candle (722 volume) should be recognized as spike + absorption
        last_c = tape["candles"][-1]
        assert last_c["volume"] == 722
        assert last_c["is_spike"] is True
        assert "[HẤP THỤ ĐÁY RÚT CHÂN]" in last_c["note"]


def test_fetch_live_cme_m5_tape_mock_failure():
    """When HTTP fails, returns fallback dictionary without throwing uncaught errors."""
    from src.quant_engine.basis import fetch_live_cme_m5_tape

    with mock.patch("urllib.request.urlopen", side_effect=RuntimeError("Network down")):
        tape = fetch_live_cme_m5_tape()
        assert tape["available"] is False
        assert tape["candles"] == []


def test_fetch_live_cme_m5_tape_pinbar_bear_and_tick_filter():
    """Validates shooting star rejection (green body with large upper wick), churn doji, and trailing tick discard."""
    from src.quant_engine.basis import fetch_live_cme_m5_tape

    fake_response = mock.MagicMock()
    fake_response.status = 200
    fake_response.read.return_value = json.dumps({
        "chart": {
            "result": [{
                "meta": {
                    # Deliberately omit regularMarketDayHigh / Low to test fallback to max/min
                    "regularMarketPrice": 4145.0,
                },
                "timestamp": [1792481100, 1792481400, 1792481700, 1792482000, 1792482300, 1792482600, 1792482603],
                "indicators": {
                    "quote": [{
                        # Candle 0..3: Baseline volume
                        # Candle 4: Shooting Star / Rejection at high with slight green close
                        # Candle 5: Long-legged Doji Churn with spike
                        # Candle 6: Trailing live tick snapshot (0 volume, 0 spread) -> should be discarded
                        "open": [4140.0, 4140.0, 4140.0, 4140.0, 4140.0, 4145.0, 4145.0],
                        "high": [4142.0, 4142.0, 4142.0, 4142.0, 4155.0, 4155.0, 4145.0],
                        "low": [4139.0, 4139.0, 4139.0, 4139.0, 4139.5, 4135.0, 4145.0],
                        "close": [4141.0, 4141.0, 4141.0, 4141.0, 4140.5, 4145.0, 4145.0],
                        "volume": [200, 200, 200, 200, 850, 920, 0],
                    }]
                }
            }]
        }
    }).encode("utf-8")
    fake_response.__enter__.return_value = fake_response

    with mock.patch("urllib.request.urlopen", return_value=fake_response):
        tape = fetch_live_cme_m5_tape(limit=10)
        assert tape["available"] is True
        # Trailing 0-vol tick was discarded, leaving 6 candles
        assert len(tape["candles"]) == 6

        # Day High / Day Low fallback accurately found the extremes across candles
        assert tape["day_high"] == 4155.0
        assert tape["day_low"] == 4135.0

        # Candle 4 (Shooting star with green body) -> CHẶN BÁN ĐÈ ĐỈNH
        bear_pinbar = tape["candles"][4]
        assert bear_pinbar["volume"] == 850
        assert bear_pinbar["is_spike"] is True
        assert "[CHẶN BÁN ĐÈ ĐỈNH]" in bear_pinbar["note"]
        assert bear_pinbar["signal_class"] == "spike-rejection"

        # Candle 5 (Long-legged Doji) -> ĐỘT BIẾN GIẰNG CO
        churn_candle = tape["candles"][5]
        assert churn_candle["volume"] == 920
        assert churn_candle["is_spike"] is True
        assert "[ĐỘT BIẾN GIẰNG CO]" in churn_candle["note"]
        assert churn_candle["signal_class"] == "spike-neutral"


def test_compute_gold_cost_of_carry():
    from src.quant_engine.basis import compute_gold_cost_of_carry

    # S0 = 2700, dte = 30 days, r = 0.045, u = 0.002, y = 0.015
    # net carry = 0.045 + 0.002 - 0.015 = 0.032 (3.2%/year)
    # T = 30 / 365 = 0.08219
    # F0 = 2700 * exp(0.032 * 0.08219) ~ 2700 * 1.002633 ~ 2707.11
    f0 = compute_gold_cost_of_carry(2700.0, dte_days=30.0, risk_free_rate=0.045, storage_cost=0.002, lease_rate=0.015)
    assert f0 == pytest.approx(2707.11, abs=0.5)

    # Edge cases
    assert compute_gold_cost_of_carry(0.0) == 0.0
    assert compute_gold_cost_of_carry(-100.0) == 0.0


def test_analyze_efp_spread():
    from src.quant_engine.basis import analyze_efp_spread

    # Case 1: Premium / Bullish NY Buying (Futures > Theoretical by > 3.0 USD)
    res_prem = analyze_efp_spread(
        futures_price=2720.0,
        spot_price=2700.0,
        dte_days=30.0,
        risk_free_rate=0.045,
        storage_cost=0.002,
        lease_rate=0.015,
    )
    assert res_prem["status"] == "PREMIUM"
    assert "MUA ĐUỔI" in res_prem["label"]
    assert res_prem["delta_f"] > 3.0

    # Case 2: Discount / Producer Hedging (Futures < Theoretical by > 3.0 USD)
    res_disc = analyze_efp_spread(
        futures_price=2695.0,
        spot_price=2700.0,
        dte_days=30.0,
        risk_free_rate=0.045,
        storage_cost=0.002,
        lease_rate=0.015,
    )
    assert res_disc["status"] == "DISCOUNT"
    assert "BÁN XẢ" in res_disc["label"]
    assert res_disc["delta_f"] < -3.0

    # Case 3: Fair Value Equilibrium (|delta_f| <= 3.0 USD)
    res_fair = analyze_efp_spread(
        futures_price=2708.0,
        spot_price=2700.0,
        dte_days=30.0,
        risk_free_rate=0.045,
        storage_cost=0.002,
        lease_rate=0.015,
    )
    assert res_fair["status"] == "FAIR_VALUE"
    assert "CÂN BẰNG" in res_fair["label"]



