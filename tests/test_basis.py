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
    """Primary Gold-API returns valid price."""
    fake_response = mock.MagicMock()
    fake_response.status = 200
    fake_response.read.return_value = json.dumps({"price": 4156.50}).encode("utf-8")
    fake_response.__enter__.return_value = fake_response

    with mock.patch("urllib.request.urlopen", return_value=fake_response):
        quote = fetch_live_spot_gold_price()
        assert quote is not None
        assert quote.price == 4156.50
        assert quote.source == "Gold-API"


def test_fetch_live_spot_gold_fallback_to_binance():
    """Primary fails, secondary Binance PAXG succeeds."""
    call_count = 0

    def mock_urlopen(req, timeout=5.0):
        nonlocal call_count
        call_count += 1
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "gold-api" in url:
            raise urllib.error.URLError("Connection refused")
        resp = mock.MagicMock()
        resp.status = 200
        resp.read.return_value = json.dumps({"price": "4155.80"}).encode("utf-8")
        resp.__enter__.return_value = resp
        return resp

    import urllib.error
    with mock.patch("urllib.request.urlopen", side_effect=mock_urlopen):
        quote = fetch_live_spot_gold_price()
        assert quote is not None
        assert quote.price == 4155.80
        assert quote.source == "Binance-PAXG"


def test_fetch_live_spot_gold_cache_ttl():
    """Subsequent calls within TTL reuse the cached quote without network calls."""
    fake_response = mock.MagicMock()
    fake_response.status = 200
    fake_response.read.return_value = json.dumps({"price": 4156.50}).encode("utf-8")
    fake_response.__enter__.return_value = fake_response

    with mock.patch("urllib.request.urlopen", return_value=fake_response) as mock_urlopen:
        quote1 = fetch_live_spot_gold_price()
        quote2 = fetch_live_spot_gold_price()

        assert quote1 == quote2
        assert mock_urlopen.call_count == 1  # Network called only once!


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

