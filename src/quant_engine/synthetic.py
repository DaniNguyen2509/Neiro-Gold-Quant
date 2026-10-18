"""Tier 2: Synthetic ATM Pivot, Straddle, 1-Sigma Bands."""
from __future__ import annotations

from .models import OptionsSnapshot, OptionsStrike


def find_atm_strike(snapshot: OptionsSnapshot) -> OptionsStrike:
    """Find the ATM strike where |Call_mid - Put_mid| is smallest."""
    if not snapshot.strikes:
        raise ValueError("Empty options chain")
    return min(snapshot.strikes, key=lambda s: abs(s.call_mid - s.put_mid))


def synthetic_atm_pivot(snapshot: OptionsSnapshot) -> float:
    """Compute Implied Underlying via Put-Call Parity.

    S_Implied = K_ATM + Call_mid - Put_mid
    """
    atm = find_atm_strike(snapshot)
    return atm.strike + atm.call_mid - atm.put_mid


def implied_straddle(snapshot: OptionsSnapshot) -> float:
    """Compute ATM Straddle = Call_mid(ATM) + Put_mid(ATM)."""
    atm = find_atm_strike(snapshot)
    return atm.call_mid + atm.put_mid


def sigma_bands(
    pivot: float,
    straddle: float,
    factor: float = 1.0,
) -> tuple[float, float]:
    """Compute +/-1 sigma bands.

    Args:
        pivot: Synthetic ATM pivot price.
        straddle: ATM straddle value.
        factor: Multiplier (1.0 for full sigma, 0.85 for conservative).

    Returns:
        (upper_band, lower_band)
    """
    move = straddle * factor
    return pivot + move, pivot - move
