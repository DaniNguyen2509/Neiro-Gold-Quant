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
        now_dt = datetime.datetime.now(datetime.timezone.utc)
    elif isinstance(now, datetime.datetime):
        now_dt = now if now.tzinfo is not None else now.replace(tzinfo=datetime.timezone.utc)
    else:
        now_dt = datetime.datetime.combine(now, datetime.time(0, 0), tzinfo=datetime.timezone.utc)

    now_date = now_dt.date()
    y = now_date.year
    m = now_date.month

    for offset in range(0, 14):
        target_m = ((m - 1 + offset) % 12) + 1
        target_y = y + ((m - 1 + offset) // 12)
        exp = get_cme_option_expiry_date(target_y, target_m)
        # COMEX Gold options expiration cutoff: 13:30 CT (18:30 UTC)
        exp_cutoff_dt = datetime.datetime.combine(exp, datetime.time(18, 30), tzinfo=datetime.timezone.utc)
        if exp_cutoff_dt >= now_dt:
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


def resolve_active_expirations(
    now: Optional[Union[datetime.date, datetime.datetime]] = None,
    underlying_futures: str = "GCZ26",
    weekly_count: int = 2,
) -> list[Dict[str, Any]]:
    """Resolves active CME Gold Options expirations (Weekly + Monthly).

    CME Gold Options structure:
    - Weekly options (OG1..OG5) expire every Friday.
    - Monthly option (OG) expires on the 4th business day prior to the end of the preceding month.

    Returns:
        List of dicts containing contract details, DTE, and Barchart URL for multi-expiry aggregation.
    """
    if now is None:
        now_dt = datetime.datetime.now(datetime.timezone.utc)
    elif isinstance(now, datetime.datetime):
        now_dt = now if now.tzinfo is not None else now.replace(tzinfo=datetime.timezone.utc)
    else:
        now_dt = datetime.datetime.combine(now, datetime.time(0, 0), tzinfo=datetime.timezone.utc)

    now_date = now_dt.date()
    front_monthly = resolve_front_month_cme_option(now=now_dt, underlying_futures=underlying_futures)

    results: list[Dict[str, Any]] = []

    # 1. Upcoming Weekly Friday expirations
    curr = now_date
    fridays_found = 0
    # COMEX Gold options expiration cutoff: 13:30 CT (18:30 UTC)
    while fridays_found < weekly_count:
        if curr.weekday() == 4:  # Friday
            cutoff_dt = datetime.datetime.combine(curr, datetime.time(18, 30), tzinfo=datetime.timezone.utc)
            if cutoff_dt >= now_dt:
                day = curr.day
                week_num = min(5, (day - 1) // 7 + 1)
                month_code = CME_OPTION_MONTH_CODES[curr.month]
                yr_code = str(curr.year)[-2:]
                opt_sym = f"OG{week_num}{month_code}{yr_code}"
                dte_val = compute_dynamic_dte(curr, now_dt)

                results.append({
                    "type": "WEEKLY",
                    "name": f"Weekly {week_num} ({curr.strftime('%b %d')})",
                    "option_symbol": opt_sym,
                    "underlying": underlying_futures,
                    "expiration_date": curr.isoformat(),
                    "dte": dte_val,
                    "barchart_url": f"https://www.barchart.com/futures/quotes/{underlying_futures}/options/{opt_sym}?futuresOptionsView=merged",
                })
                fridays_found += 1
        curr += datetime.timedelta(days=1)

    # 2. Front-Month Monthly expiration
    monthly_dte = compute_dynamic_dte(front_monthly["expiration_date"], now_dt)
    results.append({
        "type": "MONTHLY",
        "name": f"Monthly ({front_monthly['option_symbol']})",
        "option_symbol": front_monthly["option_symbol"],
        "underlying": underlying_futures,
        "expiration_date": front_monthly["expiration_date"],
        "dte": monthly_dte,
        "barchart_url": front_monthly["barchart_url"],
    })

    return results


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
    """Find the ATM strike where |Call_mid - Put_mid| is smallest (preferring liquid strikes)."""
    if not snapshot.strikes:
        raise ValueError("Empty options chain")

    # Prefer strikes with active two-sided quotes or non-zero mid on both sides
    liquid = [
        s for s in snapshot.strikes
        if (s.call_bid > 0 and s.call_ask > 0 and s.put_bid > 0 and s.put_ask > 0)
        or (s.call_mid > 0 and s.put_mid > 0)
    ]
    candidates = liquid if liquid else list(snapshot.strikes)
    return min(candidates, key=lambda s: abs(s.call_mid - s.put_mid))


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
