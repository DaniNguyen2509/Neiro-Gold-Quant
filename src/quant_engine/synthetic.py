from __future__ import annotations

import datetime
from typing import Optional, Union

from .models import OptionsSnapshot, OptionsStrike


def compute_dynamic_dte(
    expiry: Optional[Union[str, datetime.date, datetime.datetime]] = None,
    now: Optional[datetime.datetime] = None,
    default_dte: float = 30.0,
) -> float:
    """Compute dynamic Days to Expiration (DTE) in days.

    Args:
        expiry: Target expiration date string (YYYY-MM-DD) or date/datetime.
        now: Current timestamp (defaults to UTC now).
        default_dte: Fallback DTE in days if expiry is missing/invalid.

    Returns:
        DTE in fractional days, floored at 1 minute (1.0 / 1440.0).
    """
    if now is None:
        now = datetime.datetime.now(datetime.timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=datetime.timezone.utc)

    if not expiry:
        return default_dte

    try:
        if isinstance(expiry, datetime.datetime):
            exp_dt = expiry
        elif isinstance(expiry, datetime.date):
            exp_dt = datetime.datetime.combine(expiry, datetime.time(18, 30))
        else:
            s = str(expiry).strip()
            if len(s) == 10 and s[4] == "-" and s[7] == "-":
                parts = [int(p) for p in s.split("-")]
                exp_dt = datetime.datetime(parts[0], parts[1], parts[2], 18, 30)
            else:
                exp_dt = datetime.datetime.fromisoformat(s)

        if exp_dt.tzinfo is None:
            exp_dt = exp_dt.replace(tzinfo=datetime.timezone.utc)

        diff = (exp_dt - now).total_seconds() / 86400.0
        return max(1.0 / 1440.0, float(diff))
    except Exception:
        return default_dte



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
