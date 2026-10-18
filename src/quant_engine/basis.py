"""Auto-Basis Sync: Futures <-> Spot conversion."""
from __future__ import annotations

from .models import QuantLevels


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
