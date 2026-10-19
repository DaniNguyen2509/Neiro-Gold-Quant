import json
import urllib.request

from .models import QuantLevels


def fetch_live_spot_gold_price() -> float | None:
    """Fetches real-time physical XAU/USD spot price from public zero-latency APIs with fallback.

    Sources:
    1. Gold-API (Direct LBMA-blended spot XAU/USD)
    2. Binance PAXG/USDT (1:1 London Good Delivery physical gold spot)
    """
    sources = [
        ("https://api.gold-api.com/price/XAU", "price"),
        ("https://api.binance.com/api/v3/ticker/price?symbol=PAXGUSDT", "price"),
    ]

    for url, key in sources:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode())
                p = float(data.get(key, 0.0))
                if p > 1000.0:
                    return p
        except Exception:
            continue

    return None


def resolve_dynamic_basis(futures_price: float, fallback_basis: float = 24.0) -> float:
    """Computes dynamic basis spread = futures_price - spot_price.

    If live spot price is unavailable, gracefully falls back to fallback_basis.
    """
    spot = fetch_live_spot_gold_price()
    if spot is not None and spot > 0:
        spread = futures_price - spot
        # Sanity check: gold basis spread for active contracts is typically between 0 and 60 USD
        if 0.0 <= spread <= 60.0:
            return round(spread, 2)
    return fallback_basis


def compute_basis(spot_price: float, futures_price: float) -> float:
    """Compute basis = Spot - Futures.

    Args:
        spot_price: Current spot price (e.g., Exness XAUUSDc).
        futures_price: Current futures/forward price (e.g., MT5 XAUUSD-F).

    Returns:
        Basis value (typically negative for contango).
    """
    return spot_price - futures_price


def convert_to_spot(futures_level: float, basis: float) -> float:
    """Convert a futures-referenced level to spot reference.

    spot_level = futures_level + basis
    """
    return futures_level + basis


def convert_levels_to_spot(levels: QuantLevels, basis: float) -> dict:
    """Convert all QuantLevels to spot-referenced values.

    Returns dict with all key levels in spot terms.
    """
    result = {
        "synthetic_atm_pivot": convert_to_spot(levels.synthetic_atm_pivot, basis),
        "sigma_1_upper": convert_to_spot(levels.sigma_1_upper, basis),
        "sigma_1_lower": convert_to_spot(levels.sigma_1_lower, basis),
        "sigma_085_upper": convert_to_spot(levels.sigma_085_upper, basis),
        "sigma_085_lower": convert_to_spot(levels.sigma_085_lower, basis),
    }

    if levels.call_wall_1:
        result["call_wall_1"] = convert_to_spot(levels.call_wall_1.strike, basis)
    if levels.put_wall_1:
        result["put_wall_1"] = convert_to_spot(levels.put_wall_1.strike, basis)
    if levels.gamma_squeeze_up is not None:
        result["gamma_squeeze_up"] = convert_to_spot(levels.gamma_squeeze_up, basis)
    if levels.gamma_waterfall_down is not None:
        result["gamma_waterfall_down"] = convert_to_spot(
            levels.gamma_waterfall_down, basis
        )

    return result
