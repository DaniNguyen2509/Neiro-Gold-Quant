import calendar
import datetime
from typing import Any, Dict, Optional, Union

try:
    import zoneinfo
    CHI_ZONE = zoneinfo.ZoneInfo("America/Chicago")
except Exception:
    CHI_ZONE = None


def get_cme_cutoff_dt(exp: datetime.date) -> datetime.datetime:
    """Computes the COMEX Gold Options expiration cutoff at 13:30 Chicago Time (CT).

    Seamlessly adapts to both US Summer Time (CDT: 18:30 UTC) and Winter Time (CST: 19:30 UTC).
    """
    if CHI_ZONE is not None:
        try:
            exp_ct = datetime.datetime.combine(exp, datetime.time(13, 30), tzinfo=CHI_ZONE)
            return exp_ct.astimezone(datetime.timezone.utc)
        except Exception:
            pass
    # Fallback heuristic: Nov-Mar is CST (UTC-6 => 19:30 UTC), Apr-Oct is CDT (UTC-5 => 18:30 UTC)
    utc_hour = 19 if (exp.month in (11, 12, 1, 2) or (exp.month == 3 and exp.day < 10)) else 18
    return datetime.datetime(exp.year, exp.month, exp.day, utc_hour, 30, tzinfo=datetime.timezone.utc)

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
        exp_cutoff_dt = get_cme_cutoff_dt(exp)
        if exp_cutoff_dt >= now_dt:
            month_code = CME_OPTION_MONTH_CODES[target_m]
            yr_code = str(target_y)[-2:]
            opt_symbol = f"OG{month_code}{yr_code}"
            # COMEX Gold Futures primary active contract months: G(Feb), J(Apr), M(Jun), Q(Aug), V(Oct), Z(Dec)
            fut_month = {1: 'G', 2: 'G', 3: 'J', 4: 'J', 5: 'M', 6: 'M', 7: 'Q', 8: 'Q', 9: 'V', 10: 'V', 11: 'Z', 12: 'Z'}[target_m]
            active_underlying = f"GC{fut_month}{yr_code}"
            # If underlying_futures is default GCZ26 but we rolled into a later contract year/month, dynamically update underlying
            if underlying_futures == "GCZ26" and (target_y > 2026 or (target_y == 2026 and target_m != 12)):
                underlying = active_underlying
            else:
                underlying = underlying_futures

            url = f"https://www.barchart.com/futures/quotes/{underlying}/options?futuresOptionsView=merged"
            return {
                "option_symbol": opt_symbol,
                "underlying": underlying,
                "expiration_date": exp.isoformat(),
                "contract_month": target_m,
                "contract_year": target_y,
                "barchart_url": url,
            }

    # Ultimate dynamic fallback (never returns expired date in the past)
    fb_m = (m % 12) + 1
    fb_y = y + (1 if fb_m == 1 else 0)
    fb_exp = get_cme_option_expiry_date(fb_y, fb_m)
    fb_opt_code = CME_OPTION_MONTH_CODES[fb_m]
    fb_yr_code = str(fb_y)[-2:]
    fb_fut_m = {1: 'G', 2: 'G', 3: 'J', 4: 'J', 5: 'M', 6: 'M', 7: 'Q', 8: 'Q', 9: 'V', 10: 'V', 11: 'Z', 12: 'Z'}[fb_m]
    fb_underlying = f"GC{fb_fut_m}{fb_yr_code}"
    return {
        "option_symbol": f"OG{fb_opt_code}{fb_yr_code}",
        "underlying": fb_underlying,
        "expiration_date": fb_exp.isoformat(),
        "contract_month": fb_m,
        "contract_year": fb_y,
        "barchart_url": f"https://www.barchart.com/futures/quotes/{fb_underlying}/options?futuresOptionsView=merged",
    }


def resolve_active_expirations(
    now: Optional[Union[datetime.date, datetime.datetime]] = None,
    underlying_futures: str = "GCZ26",
    weekly_count: int = 2,
) -> list[Dict[str, Any]]:
    """Resolves active CME Gold Options expirations (Weekly + Monthly).

    CME Gold Options structure:
    - Weekly options (OG1..OG5) expire every Friday. On Barchart, they are listed as IG1..IG5.
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
            cutoff_dt = get_cme_cutoff_dt(curr)
            if cutoff_dt >= now_dt:
                day = curr.day
                week_num = min(5, (day - 1) // 7 + 1)
                month_code = CME_OPTION_MONTH_CODES[curr.month]
                yr_code = str(curr.year)[-2:]
                opt_sym = f"OG{week_num}{month_code}{yr_code}"
                # Barchart uses IG prefix for Friday Weekly options
                barchart_sym = f"IG{week_num}{month_code}{yr_code}"
                dte_val = compute_dynamic_dte(curr, now_dt)

                results.append({
                    "type": "WEEKLY",
                    "name": f"Weekly {week_num} ({curr.strftime('%b %d')})",
                    "option_symbol": opt_sym,
                    "underlying": underlying_futures,
                    "expiration_date": curr.isoformat(),
                    "dte": dte_val,
                    "barchart_url": f"https://www.barchart.com/futures/quotes/{underlying_futures}/options/{barchart_sym}?futuresOptionsView=merged",
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



def find_atm_strike(
    snapshot: OptionsSnapshot,
    spot_price: Optional[float] = None,
) -> OptionsStrike:
    """Find the ATM strike where |Call_mid - Put_mid| is smallest (preferring liquid strikes).

    If two-sided market quotes are absent (e.g. illiquid off-hours / weekend), anchors to spot_price
    or median strike to prevent choosing unquoted deep OTM strikes (e.g. $1,350).
    """
    if not snapshot.strikes:
        raise ValueError("Empty options chain")

    # Prefer strikes with active two-sided quotes or non-zero mid on both sides
    liquid = [
        s for s in snapshot.strikes
        if (s.call_bid > 0 and s.call_ask > 0 and s.put_bid > 0 and s.put_ask > 0)
        or (s.call_mid > 0 and s.put_mid > 0)
    ]
    if liquid:
        return min(liquid, key=lambda s: abs(s.call_mid - s.put_mid))

    # Illiquid / off-hours fallback anchored to spot price:
    if spot_price is not None and spot_price > 0:
        return min(snapshot.strikes, key=lambda s: abs(s.strike - spot_price))

    # Quoted strikes fallback
    quoted = [s for s in snapshot.strikes if (s.call_mid > 0 or s.put_mid > 0)]
    if quoted:
        return min(quoted, key=lambda s: abs(s.call_mid - s.put_mid))

    # Pure fallback to median strike (guarantees reasonable strike selection)
    median_k = snapshot.strikes[len(snapshot.strikes) // 2].strike
    return min(snapshot.strikes, key=lambda s: abs(s.strike - median_k))


def synthetic_atm_pivot(
    snapshot: OptionsSnapshot,
    spot_price: Optional[float] = None,
) -> float:
    """Compute Implied Underlying via Put-Call Parity.

    S_Implied = K_ATM + Call_mid - Put_mid
    """
    atm = find_atm_strike(snapshot, spot_price=spot_price)
    return atm.strike + atm.call_mid - atm.put_mid


def implied_straddle(
    snapshot: OptionsSnapshot,
    spot_price: Optional[float] = None,
) -> float:
    """Compute ATM Straddle = Call_mid(ATM) + Put_mid(ATM)."""
    atm = find_atm_strike(snapshot, spot_price=spot_price)
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
