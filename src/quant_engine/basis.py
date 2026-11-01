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
import math
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Final, Optional, Any

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


def fetch_live_cme_futures_price(timeout: float = 4.0) -> Optional[float]:
    """Fetches real-time CME Gold Futures price (GC=F) directly from COMEX endpoints.

    Uses native urllib HTTP queries with TTL caching, falling back to yfinance if available.
    Returns:
        Live futures price float, or None if unavailable/offline.
    """
    global _cached_futures, _last_fetch_futures_mono
    with _cache_lock:
        now_mono = time.monotonic()
        if _cached_futures is not None and (now_mono - _last_fetch_futures_mono) < _CACHE_TTL_S:
            return _cached_futures

    # Method 1: Direct native HTTP query to Yahoo Finance chart endpoints (zero dependencies)
    chart_urls = [
        "https://query1.finance.yahoo.com/v8/finance/chart/GC=F",
        "https://query2.finance.yahoo.com/v8/finance/chart/GC=F",
    ]
    for url in chart_urls:
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Neiro-Quant/2.0",
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    result = data.get("chart", {}).get("result", [])
                    if result:
                        meta = result[0].get("meta", {})
                        price = meta.get("regularMarketPrice")
                        if price is not None and float(price) > 500.0:
                            p = round(float(price), 2)
                            with _cache_lock:
                                _cached_futures = p
                                _last_fetch_futures_mono = time.monotonic()
                            return p
        except Exception as e:
            logger.debug("Direct HTTP fetch from %s failed: %s", url, e)

    # Method 2: Fallback to yfinance if installed
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


def fetch_live_cme_m5_tape(limit: int = 8, timeout: float = _HTTP_TIMEOUT_S) -> dict[str, Any]:
    """Fetches recent 5-minute candles and orderflow volume pulse for COMEX Gold Futures (GC=F).

    Identifies volume spikes (>= 1.4x 20-bar avg) and absorption pin bars.
    Returns:
        dict with keys:
            'available': bool
            'candles': list of dicts (time_vn, open, high, low, close, volume, ratio, is_spike, note, signal_class)
            'day_high': float
            'day_low': float
            'day_range': float
            'avg_m5_volume': float
            'latest_price': float
    """
    chart_urls = [
        "https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=5m&range=1d",
        "https://query2.finance.yahoo.com/v8/finance/chart/GC=F?interval=5m&range=1d",
    ]
    for url in chart_urls:
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Neiro-Quant/2.0",
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    result = data.get("chart", {}).get("result", [])
                    if result:
                        res0 = result[0]
                        meta = res0.get("meta", {})
                        timestamps = res0.get("timestamp", [])
                        quote = res0.get("indicators", {}).get("quote", [{}])[0]
                        opens = quote.get("open", [])
                        highs = quote.get("high", [])
                        lows = quote.get("low", [])
                        closes = quote.get("close", [])
                        volumes = quote.get("volume", [])

                        raw_candles = []
                        for t, o, h, l, c, v in zip(timestamps, opens, highs, lows, closes, volumes):
                            if None in (t, o, h, l, c) or o <= 0:
                                continue
                            raw_candles.append({
                                "t": int(t),
                                "open": round(float(o), 2),
                                "high": round(float(h), 2),
                                "low": round(float(l), 2),
                                "close": round(float(c), 2),
                                "volume": int(v) if v is not None else 0,
                            })

                        # Discard Yahoo Finance trailing live tick snapshot (0 volume and zero spread)
                        if len(raw_candles) > 1 and raw_candles[-1]["volume"] <= 0 and (raw_candles[-1]["high"] - raw_candles[-1]["low"]) < 0.05:
                            raw_candles.pop()

                        if raw_candles:
                            valid_vols = [rc["volume"] for rc in raw_candles if rc["volume"] > 0]
                            window = valid_vols[-20:] if len(valid_vols) >= 5 else valid_vols
                            avg_vol = float(sum(window) / len(window)) if window else 200.0

                            selected = raw_candles[-limit:]
                            processed = []
                            for sc in selected:
                                dt_vn = datetime.fromtimestamp(sc["t"], timezone.utc).astimezone(timezone(timedelta(hours=7)))
                                time_str = dt_vn.strftime("%H:%M")
                                vol = sc["volume"]
                                ratio = round(vol / avg_vol, 2) if avg_vol > 0 else 1.0
                                is_spike = ratio >= 1.4 and vol >= 350
                                spread = max(0.1, sc["high"] - sc["low"])
                                lower_wick = min(sc["open"], sc["close"]) - sc["low"]
                                upper_wick = sc["high"] - max(sc["open"], sc["close"])
                                is_bull_rebound = (sc["close"] > sc["open"]) and ((sc["close"] - sc["low"]) >= spread * 0.60)
                                is_bear_rejection = (sc["close"] < sc["open"]) and ((sc["high"] - sc["close"]) >= spread * 0.60)
                                is_pinbar_bull = lower_wick >= spread * 0.38
                                is_pinbar_bear = upper_wick >= spread * 0.38
                                is_churn = lower_wick >= spread * 0.30 and upper_wick >= spread * 0.30

                                if is_spike and is_churn:
                                    note = "[ĐỘT BIẾN GIẰNG CO]"
                                    signal_class = "spike-neutral"
                                elif is_spike and (is_bull_rebound or is_pinbar_bull):
                                    note = "[HẤP THỤ ĐÁY RÚT CHÂN]"
                                    signal_class = "spike-absorption"
                                elif is_spike and (is_bear_rejection or is_pinbar_bear):
                                    note = "[CHẶN BÁN ĐÈ ĐỈNH]"
                                    signal_class = "spike-rejection"
                                elif is_spike:
                                    note = "[ĐỘT BIẾN KHỐI LƯỢNG]"
                                    signal_class = "spike-neutral"
                                elif ratio <= 0.6:
                                    note = "[THANH KHOẢN CẠN KIỆT]"
                                    signal_class = "low-vol"
                                else:
                                    note = "[BÌNH THƯỜNG]"
                                    signal_class = "normal"

                                processed.append({
                                    "time_vn": time_str,
                                    "open": sc["open"],
                                    "high": sc["high"],
                                    "low": sc["low"],
                                    "close": sc["close"],
                                    "volume": vol,
                                    "ratio": ratio,
                                    "is_spike": is_spike,
                                    "note": note,
                                    "signal_class": signal_class,
                                })

                            day_high = float(meta.get("regularMarketDayHigh") or max(rc["high"] for rc in raw_candles))
                            day_low = float(meta.get("regularMarketDayLow") or min(rc["low"] for rc in raw_candles))
                            last_p = float(meta.get("regularMarketPrice") or raw_candles[-1]["close"])

                            return {
                                "available": True,
                                "candles": processed,
                                "day_high": round(day_high, 2),
                                "day_low": round(day_low, 2),
                                "day_range": round(day_high - day_low, 2),
                                "avg_m5_volume": round(avg_vol, 1),
                                "latest_price": round(last_p, 2),
                            }
        except Exception as e:
            logger.debug("Live M5 tape fetch from %s failed: %s", url, e)

    return {
        "available": False,
        "candles": [],
        "day_high": 0.0,
        "day_low": 0.0,
        "day_range": 0.0,
        "avg_m5_volume": 0.0,
        "latest_price": 0.0,
    }



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


def compute_gold_cost_of_carry(
    spot_price: float,
    dte_days: float = 30.0,
    risk_free_rate: float = 0.045,
    storage_cost: float = 0.002,
    lease_rate: float = 0.015,
) -> float:
    """Computes theoretical COMEX Gold Futures price using Cost of Carry model.

    Formula:
        F_{0, theoretical} = S_0 * exp((r + u - y) * T)
    Where:
        S_0: Spot price (XAUUSD)
        r: Risk-free rate (SOFR / 3M Treasury yield, e.g. 4.5%)
        u: Physical vault storage & insurance cost at COMEX (~0.2%/year)
        y: Gold Lease Rate between bullion banks (~1.5%/year)
        T: Time to expiration in years (dte_days / 365.0)
    """
    if spot_price <= 0.0:
        return 0.0
    t = max(0.0035, dte_days / 365.0)
    net_carry = risk_free_rate + storage_cost - lease_rate
    return round(spot_price * math.exp(net_carry * t), 2)


def analyze_efp_spread(
    futures_price: float,
    spot_price: float,
    dte_days: float = 30.0,
    risk_free_rate: float = 0.045,
    storage_cost: float = 0.002,
    lease_rate: float = 0.015,
    threshold: float = 3.0,
) -> dict[str, Any]:
    """Analyzes Exchange for Physical (EFP) basis spread between London OTC Spot and NY COMEX.

    Returns:
        dict containing:
            'f0_theoretical': float
            'delta_f': float (futures - theoretical)
            'status': str ('PREMIUM', 'DISCOUNT', 'FAIR_VALUE')
            'label': str (Vietnamese descriptive label)
            'color': str (HEX color code)
            'efp_arbitrage_signal': str
    """
    f0_theo = compute_gold_cost_of_carry(
        spot_price, dte_days, risk_free_rate, storage_cost, lease_rate
    )
    delta_f = round(futures_price - f0_theo, 2)

    if delta_f > threshold:
        status = "PREMIUM"
        label = "PREMIUM &bull; MUA ĐUỔI COMEX"
        color = "#4ADE80"
        arb_signal = "EFP BUY SPOT / SELL FUTURES (Lực mua New York áp đảo, kéo Spot tăng)"
    elif delta_f < -threshold:
        status = "DISCOUNT"
        label = "DISCOUNT &bull; BÁN XẢ COMEX"
        color = "#F87171"
        arb_signal = "EFP SELL SPOT / BUY FUTURES (Áp lực mỏ vàng phòng hộ xả hàng)"
    else:
        status = "FAIR_VALUE"
        label = "FAIR VALUE &bull; CÂN BẰNG"
        color = "#FACC15"
        arb_signal = "MARKET IN EQUILIBRIUM (Cung cầu vật chất và phái sinh cân bằng)"

    return {
        "f0_theoretical": f0_theo,
        "delta_f": delta_f,
        "status": status,
        "label": label,
        "color": color,
        "efp_arbitrage_signal": arb_signal,
    }

