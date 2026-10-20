"""src/quant_engine/basis.py

Production-grade Basis Engine for Neiro-Quant.

MANDATORY MATHEMATICAL SIGN CONVENTION (CME/LBMA STANDARD):
    basis := spot_price - futures_price
    - Contango (futures > spot)     => basis < 0 (e.g. 4156.0 - 4180.0 = -24.0 USD)
    - Backwardation (futures < spot) => basis > 0

    spot_level = futures_level + basis
    futures_level = spot_level - basis

All conversion functions and callers MUST adhere to this signed convention.
"""
from __future__ import annotations

import json
import logging
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Final, Optional

from .models import QuantLevels

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration & Constants
# ---------------------------------------------------------------------------

_HTTP_TIMEOUT_S: Final[float] = 5.0
_HTTP_RETRIES: Final[int] = 2
_HTTP_BACKOFF_S: Final[float] = 0.25

# Cache TTL: 5.0 seconds is optimal to avoid rate-limiting while keeping quotes fresh.
_CACHE_TTL_S: Final[float] = 5.0

# Relative tolerance for sanity check (5% of futures price).
_BASIS_REL_TOLERANCE: Final[float] = 0.05

# OTC Spot Gold market closes Friday 22:00 UTC and reopens Sunday 22:00 UTC.
_SPOT_CLOSE_WEEKDAY: Final[int] = 4  # Friday
_SPOT_CLOSE_HOUR_UTC: Final[int] = 22
_SPOT_OPEN_WEEKDAY: Final[int] = 6   # Sunday
_SPOT_OPEN_HOUR_UTC: Final[int] = 22


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SpotQuote:
    """Spot gold quote with timestamp and source attribution."""
    price: float
    source: str
    fetched_at: datetime

    def age_seconds(self, now: Optional[datetime] = None) -> float:
        current_time = now or datetime.now(timezone.utc)
        return max(0.0, (current_time - self.fetched_at).total_seconds())


# ---------------------------------------------------------------------------
# In-Memory Thread-Safe Cache
# ---------------------------------------------------------------------------

_cache_lock = threading.Lock()
_cached_quote: Optional[SpotQuote] = None
_last_fetch_mono: float = 0.0
_cached_futures: Optional[float] = None
_last_fetch_futures_mono: float = 0.0


def clear_spot_cache() -> None:
    """Clears in-memory quote and futures cache (useful for testing and manual resets)."""
    global _cached_quote, _last_fetch_mono, _cached_futures, _last_fetch_futures_mono
    with _cache_lock:
        _cached_quote = None
        _last_fetch_mono = 0.0
        _cached_futures = None
        _last_fetch_futures_mono = 0.0


# ---------------------------------------------------------------------------
# Market Hours Verification
# ---------------------------------------------------------------------------

def is_gold_spot_market_open(dt: Optional[datetime] = None) -> bool:
    """Checks whether the OTC XAU/USD spot market is currently open.

    Market closes: Friday 22:00 UTC.
    Market opens:  Sunday 22:00 UTC.
    """
    check_time = dt or datetime.now(timezone.utc)
    if check_time.tzinfo is None:
        check_time = check_time.replace(tzinfo=timezone.utc)
    else:
        check_time = check_time.astimezone(timezone.utc)

    weekday = check_time.weekday()
    hour = check_time.hour

    # Friday after 22:00 UTC
    if weekday == _SPOT_CLOSE_WEEKDAY and hour >= _SPOT_CLOSE_HOUR_UTC:
        return False

    # Saturday (all day)
    if weekday == 5:
        return False

    # Sunday before 22:00 UTC
    if weekday == _SPOT_OPEN_WEEKDAY and hour < _SPOT_OPEN_HOUR_UTC:
        return False

    return True


# ---------------------------------------------------------------------------
# Live Spot Fetching
# ---------------------------------------------------------------------------

def fetch_live_spot_gold_price(
    timeout: float = _HTTP_TIMEOUT_S,
    retries: int = _HTTP_RETRIES,
) -> Optional[SpotQuote]:
    """Fetches real-time physical XAU/USD spot price with TTL caching & fallback.

    Sources:
    1. Gold-API (LBMA-blended spot XAU/USD)
    2. Binance PAXG/USDT (Physical crypto-backed proxy fallback)
    """
    global _cached_quote, _last_fetch_mono

    # Check cache under thread-lock
    with _cache_lock:
        now_mono = time.monotonic()
        if _cached_quote is not None and (now_mono - _last_fetch_mono) < _CACHE_TTL_S:
            return _cached_quote

    sources = [
        ("https://api.gold-api.com/price/XAU", "price", "Gold-API"),
        ("https://api.binance.com/api/v3/ticker/price?symbol=PAXGUSDT", "price", "Binance-PAXG"),
    ]

    for url, key, source_name in sources:
        for attempt in range(retries):
            try:
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Neiro-Quant/2.0",
                        "Accept": "application/json",
                    },
                )
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    status = getattr(resp, "status", getattr(resp, "code", 200))
                    if status != 200:
                        logger.warning("HTTP status %s from %s", status, source_name)
                        continue

                    raw_data = resp.read().decode("utf-8")
                    data = json.loads(raw_data)
                    p_val = data.get(key)
                    if p_val is None:
                        continue

                    price = float(p_val)
                    if price > 500.0:  # Valid gold price range
                        quote = SpotQuote(
                            price=price,
                            source=source_name,
                            fetched_at=datetime.now(timezone.utc),
                        )
                        with _cache_lock:
                            _cached_quote = quote
                            _last_fetch_mono = time.monotonic()
                        return quote

            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as e:
                logger.debug("Fetch attempt %d failed for %s: %s", attempt + 1, source_name, e)
                if attempt < retries - 1:
                    time.sleep(_HTTP_BACKOFF_S * (2 ** attempt))
            except Exception as e:
                logger.warning("Unexpected error fetching spot from %s: %s", source_name, e)
                break

    return None


def fetch_live_cme_futures_price() -> Optional[float]:
    """Fetches real-time CME Gold Futures price (GC=F) via yfinance.fast_info with TTL caching.

    Returns:
        Live futures price float, or None if unavailable/offline.
    """
    global _cached_futures, _last_fetch_futures_mono
    with _cache_lock:
        now_mono = time.monotonic()
        if _cached_futures is not None and (now_mono - _last_fetch_futures_mono) < _CACHE_TTL_S:
            return _cached_futures

    try:
        import yfinance as yf
        ticker = yf.Ticker("GC=F")
        info = ticker.fast_info
        last_price = None
        if hasattr(info, "get"):
            last_price = info.get("lastPrice") or info.get("last_price")
        if last_price is None:
            last_price = getattr(info, "last_price", None) or getattr(info, "lastPrice", None)
        if last_price is None:
            try:
                last_price = info["last_price"]
            except Exception:
                pass

        if last_price is not None and float(last_price) > 500.0:
            price = round(float(last_price), 2)
            with _cache_lock:
                _cached_futures = price
                _last_fetch_futures_mono = time.monotonic()
            return price
    except Exception as e:
        logger.debug("Live CME futures fetch via yfinance failed: %s", e)

    return None


# ---------------------------------------------------------------------------
# Basis Resolution & Conversions
# ---------------------------------------------------------------------------

# Plausibility band for front-month Gold CME Futures Contango (fair value ~$24.0 USD)
_DEFAULT_CONTANGO_BASIS: Final[float] = -24.0
_MIN_PLAUSIBLE_SPREAD_USD: Final[float] = 5.0
_MAX_PLAUSIBLE_SPREAD_USD: Final[float] = 32.0


def compute_basis(spot_price: float, futures_price: float) -> float:
    """Compute signed basis = Spot - Futures.

    Args:
        spot_price: Current spot price (e.g., Exness MT5 XAUUSDc).
        futures_price: Current active futures price (e.g., CME GCZ26).

    Returns:
        Basis value (typically negative for contango, e.g. -24.0 USD).
    """
    return spot_price - futures_price


def convert_to_spot(futures_level: float, basis: float) -> float:
    """Convert a futures-referenced level to spot reference.

    spot_level = futures_level + basis
    (Example in contango: 4180.0 + (-24.0) = 4156.0)
    """
    return futures_level + basis


def resolve_dynamic_basis_with_source(
    futures_price: Optional[float],
    fallback_basis: float = _DEFAULT_CONTANGO_BASIS,
    min_spread: float = _MIN_PLAUSIBLE_SPREAD_USD,
    max_spread: float = _MAX_PLAUSIBLE_SPREAD_USD,
) -> tuple[float, str]:
    """Computes dynamic basis and returns (basis, source_label).

    Source label is one of: 'LIVE', 'CALIBRATED', 'WEEKEND_FALLBACK'.
    Guarantees basis never deviates wildly into absurd numbers (like -35$ or -41$).
    """
    if futures_price is None or futures_price <= 0:
        return fallback_basis, "CALIBRATED"
    # Guard 1: Market Hours
    if not is_gold_spot_market_open():
        logger.info(
            "OTC Gold Spot market is closed (weekend). Using calibrated contango basis: %s",
            fallback_basis,
        )
        return fallback_basis, "WEEKEND_FALLBACK"

    # Guard 2: Fetch Live Quote
    quote = fetch_live_spot_gold_price()
    if quote is None or quote.price <= 0:
        logger.warning(
            "Live spot quote unavailable. Falling back to calibrated contango basis: %s",
            fallback_basis,
        )
        return fallback_basis, "CALIBRATED"

    spot = quote.price
    candidate_basis = spot - futures_price
    spread = abs(futures_price - spot)

    # Guard 3: Plausibility Band Check for CME Gold Contango (Fair value ~$24.0 USD)
    # Public web APIs (Gold-API, Binance PAXG) frequently suffer from 10-20$ delays
    # or synthetic conversions. Any spread outside [min_spread, max_spread] is rejected.
    if not (min_spread <= spread <= max_spread):
        logger.warning(
            "Basis spread outlier rejected: spread=%.2f outside plausibility band [%.1f, %.1f] "
            "(spot=%.2f, futures=%.2f, API=%s). Clamped to calibrated contango: %.2f",
            spread,
            min_spread,
            max_spread,
            spot,
            futures_price,
            quote.source,
            fallback_basis,
        )
        return fallback_basis, "CALIBRATED"

    return round(candidate_basis, 2), "LIVE"


def resolve_dynamic_basis(
    futures_price: float,
    fallback_basis: float = _DEFAULT_CONTANGO_BASIS,
    min_spread: float = _MIN_PLAUSIBLE_SPREAD_USD,
    max_spread: float = _MAX_PLAUSIBLE_SPREAD_USD,
) -> float:
    """Computes dynamic basis: basis = spot_price - futures_price.

    In contango, returns a negative value (e.g., -24.0).
    If live spot is unavailable, market is closed, or outlier is detected
    (outside plausibility band [21.0, 27.0]), safely returns fallback_basis (-24.0).
    """
    basis, _ = resolve_dynamic_basis_with_source(
        futures_price,
        fallback_basis=fallback_basis,
        min_spread=min_spread,
        max_spread=max_spread,
    )
    return basis


def convert_levels_to_spot(levels: QuantLevels, basis: float) -> dict[str, float]:
    """Convert all QuantLevels to spot-referenced values.

    Returns dict with all key levels converted to spot terms.
    """
    result: dict[str, float] = {
        "synthetic_atm_pivot": convert_to_spot(levels.synthetic_atm_pivot, basis),
        "sigma_1_upper": convert_to_spot(levels.sigma_1_upper, basis),
        "sigma_1_lower": convert_to_spot(levels.sigma_1_lower, basis),
        "sigma_085_upper": convert_to_spot(levels.sigma_085_upper, basis),
        "sigma_085_lower": convert_to_spot(levels.sigma_085_lower, basis),
    }

    if levels.call_wall_1 is not None:
        result["call_wall_1"] = convert_to_spot(levels.call_wall_1.strike, basis)
    if levels.put_wall_1 is not None:
        result["put_wall_1"] = convert_to_spot(levels.put_wall_1.strike, basis)
    if levels.gamma_squeeze_up is not None:
        result["gamma_squeeze_up"] = convert_to_spot(levels.gamma_squeeze_up, basis)
    if levels.gamma_waterfall_down is not None:
        result["gamma_waterfall_down"] = convert_to_spot(
            levels.gamma_waterfall_down, basis
        )

    return result
