import calendar
import datetime
from typing import Any, Dict, Optional, Union

from .models import OptionsSnapshot, OptionsStrike

CME_OPTION_MONTH_CODES = {
    1: 'F', 2: 'G', 3: 'H', 4: 'J', 5: 'K', 6: 'M',
    7: 'N', 8: 'Q', 9: 'U', 10: 'V', 11: 'X', 12: 'Z'
}


def get_cme_option_expiry_date(year: int, contract_month: int) -> datetime.date:
    """Computes the 4th last business day of the month preceding contract_month (CME Rule 120102.E)."""
    if contract_month == 1:
        prev_month, prev_year = 12, year - 1
    else:
        prev_month, prev_year = contract_month - 1, year

    _, last_day = calendar.monthrange(prev_year, prev_month)
    d = datetime.date(prev_year, prev_month, last_day)
    biz_count = 0
    while biz_count < 4:
        if d.weekday() < 5:  # Mon-Fri
            biz_count += 1
            if biz_count == 4:
                return d
        d -= datetime.timedelta(days=1)
    return d


def resolve_front_month_cme_option(
    now: Optional[Union[datetime.date, datetime.datetime]] = None,
    underlying_futures: str = "GCZ26",
) -> Dict[str, Any]:
    """Dynamically resolves the active front-month COMEX Gold Option contract symbol and Barchart URL.

    Automatically handles future rollovers according to official CME expiry rules.
    """
    if now is None:
        now_date = datetime.datetime.now(datetime.timezone.utc).date()
    elif isinstance(now, datetime.datetime):
        now_date = now.date()
    else:
        now_date = now

    y = now_date.year
    m = now_date.month

    for offset in range(0, 14):
        target_m = ((m - 1 + offset) % 12) + 1
        target_y = y + ((m - 1 + offset) // 12)
        exp = get_cme_option_expiry_date(target_y, target_m)
        if exp >= now_date:
            month_code = CME_OPTION_MONTH_CODES[target_m]
            yr_code = str(target_y)[-2:]
            opt_symbol = f"OG{month_code}{yr_code}"
            url = f"https://www.barchart.com/futures/quotes/{underlying_futures}/options/{opt_symbol}?futuresOptionsView=merged"
            return {
                "option_symbol": opt_symbol,
                "underlying": underlying_futures,
                "expiration_date": exp.isoformat(),
                "contract_month": target_m,
                "contract_year": target_y,
                "barchart_url": url,
            }

    # Ultimate fallback
    return {
        "option_symbol": "OGX26",
        "underlying": underlying_futures,
        "expiration_date": "2026-10-27",
        "contract_month": 11,
        "contract_year": 2026,
        "barchart_url": f"https://www.barchart.com/futures/quotes/{underlying_futures}/options/OGX26?futuresOptionsView=merged",
    }


def compute_dynamic_dte(
    expiry: Optional[Union[str, datetime.date, datetime.datetime]] = None,
    now: Optional[datetime.datetime] = None,
    default_dte: float = 8.0,
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
