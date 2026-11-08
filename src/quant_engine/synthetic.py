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

# Primary COMEX Gold Futures & Institutional Anchor Cycles: Feb(G), Apr(J), Jun(M), Aug(Q), Dec(Z)
CME_PRIMARY_GOLD_MONTHS = (2, 4, 6, 8, 12)


def _compute_easter_sunday(year: int) -> datetime.date:
    """Computes Easter Sunday using the Anonymous Gregorian algorithm (for Good Friday)."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l_val = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l_val) // 451
    month = (h + l_val - 7 * m + 114) // 31
    day = ((h + l_val - 7 * m + 114) % 31) + 1
    return datetime.date(year, month, day)


def get_cme_holidays(year: int) -> set[datetime.date]:
    """Returns official US / CME Group market holidays for a given year."""
    holidays: set[datetime.date] = set()

    def _observe(dt: datetime.date) -> datetime.date:
        if dt.weekday() == 5:  # Saturday -> Friday
            return dt - datetime.timedelta(days=1)
        if dt.weekday() == 6:  # Sunday -> Monday
            return dt + datetime.timedelta(days=1)
        return dt

    # 1. New Year's Day (Jan 1; if Sunday, observed Jan 2)
    ny = datetime.date(year, 1, 1)
    holidays.add(ny if ny.weekday() != 6 else datetime.date(year, 1, 2))

    # 2. Martin Luther King Jr. Day (3rd Monday of January)
    jan1 = datetime.date(year, 1, 1)
    mlk = jan1 + datetime.timedelta(days=(0 - jan1.weekday()) % 7 + 14)
    holidays.add(mlk)

    # 3. Presidents' Day (3rd Monday of February)
    feb1 = datetime.date(year, 2, 1)
    pres = feb1 + datetime.timedelta(days=(0 - feb1.weekday()) % 7 + 14)
    holidays.add(pres)

    # 4. Good Friday (2 days before Easter Sunday - full CME holiday)
    easter = _compute_easter_sunday(year)
    holidays.add(easter - datetime.timedelta(days=2))

    # 5. Memorial Day (Last Monday of May)
    may31 = datetime.date(year, 5, 31)
    memorial = may31 - datetime.timedelta(days=(may31.weekday() - 0) % 7)
    holidays.add(memorial)

    # 6. Juneteenth (June 19)
    holidays.add(_observe(datetime.date(year, 6, 19)))

    # 7. Independence Day (July 4)
    holidays.add(_observe(datetime.date(year, 7, 4)))

    # 8. Labor Day (1st Monday of September)
    sep1 = datetime.date(year, 9, 1)
    labor = sep1 + datetime.timedelta(days=(0 - sep1.weekday()) % 7)
    holidays.add(labor)

    # 9. Thanksgiving Day (4th Thursday of November)
    nov1 = datetime.date(year, 11, 1)
    thanksgiving = nov1 + datetime.timedelta(days=(3 - nov1.weekday()) % 7 + 21)
    holidays.add(thanksgiving)

    # 10. Christmas Day (December 25)
    holidays.add(_observe(datetime.date(year, 12, 25)))

    return holidays


def is_cme_business_day(d: datetime.date, adjust_holidays: bool = True) -> bool:
    """Checks if a date is a valid CME business day."""
    if d.weekday() >= 5:
        return False
    if adjust_holidays and d in get_cme_holidays(d.year):
        return False
    return True


def get_cme_option_expiry_date(year: int, contract_month: int, adjust_holidays: bool = False) -> datetime.date:
    """Computes the 4th last business day of the month preceding contract_month (CME Rule 120102.E).

    If the day before Christmas (Dec 24) or New Year's Eve (Dec 31) falls on that 4th business day,
    or if adjust_holidays=True excludes US federal holidays, shifts to the preceding business day.
    """
    if contract_month == 1:
        prev_month, prev_year = 12, year - 1
    else:
        prev_month, prev_year = contract_month - 1, year

    _, last_day = calendar.monthrange(prev_year, prev_month)
    d = datetime.date(prev_year, prev_month, last_day)
    biz_count = 0
    while biz_count < 4:
        if is_cme_business_day(d, adjust_holidays=adjust_holidays):
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


def resolve_next_quarterly_cme_option(
    now: Optional[Union[datetime.date, datetime.datetime]] = None,
    front_monthly: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Resolves the next Primary/Quarterly COMEX Gold Option anchor (Feb-G, Apr-J, Jun-M, Aug-Q, Dec-Z).

    If front_monthly is a serial month (Jan, Mar, May, Jul, Sep, Oct, Nov), returns the immediately
    upcoming Primary cycle month. If front_monthly is already a Primary cycle month, returns the
    subsequent Primary cycle anchor after front_monthly.
    """
    if now is None:
        now_dt = datetime.datetime.now(datetime.timezone.utc)
    elif isinstance(now, datetime.datetime):
        now_dt = now if now.tzinfo is not None else now.replace(tzinfo=datetime.timezone.utc)
    else:
        now_dt = datetime.datetime.combine(now, datetime.time(0, 0), tzinfo=datetime.timezone.utc)

    if front_monthly is None:
        front_monthly = resolve_front_month_cme_option(now=now_dt)

    start_y = int(front_monthly.get("contract_year", now_dt.year))
    start_m = int(front_monthly.get("contract_month", now_dt.month))

    # Search forward from the month after front_monthly for the next Primary Cycle (G, J, M, Q, Z)
    for offset in range(1, 15):
        target_m = ((start_m - 1 + offset) % 12) + 1
        target_y = start_y + ((start_m - 1 + offset) // 12)
        if target_m in CME_PRIMARY_GOLD_MONTHS:
            exp = get_cme_option_expiry_date(target_y, target_m)
            month_code = CME_OPTION_MONTH_CODES[target_m]
            yr_code = str(target_y)[-2:]
            opt_symbol = f"OG{month_code}{yr_code}"
            underlying = f"GC{month_code}{yr_code}"
            return {
                "option_symbol": opt_symbol,
                "underlying": underlying,
                "expiration_date": exp.isoformat(),
                "contract_month": target_m,
                "contract_year": target_y,
                "barchart_url": f"https://www.barchart.com/futures/quotes/{underlying}/options/{opt_symbol}?futuresOptionsView=merged",
            }

    return front_monthly


def resolve_active_expirations(
    now: Optional[Union[datetime.date, datetime.datetime]] = None,
    underlying_futures: str = "GCZ26",
    weekly_count: int = 2,
    include_quarterly: bool = True,
) -> list[Dict[str, Any]]:
    """Resolves active 3-Tier CME Gold Options expirations (Weekly + Monthly + Quarterly Anchor).

    CME Gold Options structure:
    - Tier 1 (WEEKLY): Weekly options (OG1..OG5 / Barchart IG1..IG5) expiring every Friday
      (automatically shifted to Thursday if Friday is a CME market holiday).
    - Tier 2 (MONTHLY): Front-month option (OG) expiring on the 4th business day prior to the end of the preceding month.
    - Tier 3 (QUARTERLY): Institutional Primary Cycle Anchor (G-Feb, J-Apr, M-Jun, Q-Aug, Z-Dec).

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
    active_underlying = front_monthly.get("underlying", underlying_futures)

    results: list[Dict[str, Any]] = []
    seen_dates: set[str] = {front_monthly["expiration_date"]}

    # 1. Tier 1: Upcoming Weekly Friday expirations (with CME Holiday adjustment)
    curr = now_date
    fridays_found = 0
    days_searched = 0
    # COMEX Gold options expiration cutoff: 13:30 CT (18:30 UTC Summer / 19:30 UTC Winter)
    while fridays_found < weekly_count and days_searched < 45:
        if curr.weekday() == 4:  # Friday
            # If Friday is a CME holiday (e.g. Good Friday, Christmas), expiration shifts to Thursday
            exp_day = curr
            while not is_cme_business_day(exp_day, adjust_holidays=True) and (curr - exp_day).days < 3:
                exp_day -= datetime.timedelta(days=1)

            cutoff_dt = get_cme_cutoff_dt(exp_day)
            if cutoff_dt >= now_dt:
                exp_iso = exp_day.isoformat()
                if exp_iso not in seen_dates:
                    day = curr.day
                    week_num = min(5, (day - 1) // 7 + 1)
                    month_code = CME_OPTION_MONTH_CODES[curr.month]
                    yr_code = str(curr.year)[-2:]
                    opt_sym = f"OG{week_num}{month_code}{yr_code}"
                    # Barchart uses IG prefix for Friday Weekly options
                    barchart_sym = f"IG{week_num}{month_code}{yr_code}"
                    dte_val = compute_dynamic_dte(exp_day, now_dt)

                    results.append({
                        "type": "WEEKLY",
                        "name": f"Weekly {week_num} ({exp_day.strftime('%b %d')})",
                        "option_symbol": opt_sym,
                        "barchart_symbol": barchart_sym,
                        "underlying": active_underlying,
                        "expiration_date": exp_iso,
                        "dte": dte_val,
                        "barchart_url": f"https://www.barchart.com/futures/quotes/{active_underlying}/options/{barchart_sym}?futuresOptionsView=merged",
                    })
                    seen_dates.add(exp_iso)
                    fridays_found += 1
        curr += datetime.timedelta(days=1)
        days_searched += 1

    # 2. Tier 2: Front-Month Monthly expiration
    monthly_dte = compute_dynamic_dte(front_monthly["expiration_date"], now_dt)
    results.append({
        "type": "MONTHLY",
        "name": f"Monthly ({front_monthly['option_symbol']})",
        "option_symbol": front_monthly["option_symbol"],
        "barchart_symbol": front_monthly["option_symbol"],
        "underlying": active_underlying,
        "expiration_date": front_monthly["expiration_date"],
        "dte": monthly_dte,
        "barchart_url": front_monthly["barchart_url"],
    })

    # 3. Tier 3: Quarterly / Primary Institutional Anchor (G, J, M, Q, Z)
    # Automatically included when include_quarterly=True and either:
    # - Front-month is a Serial month (Jan, Mar, May, Jul, Sep, Oct, Nov), OR
    # - Front-month is within 21 days of expiration, OR
    # - Always as the next macro structural anchor
    if include_quarterly:
        q_opt = resolve_next_quarterly_cme_option(now=now_dt, front_monthly=front_monthly)
        q_exp_iso = q_opt["expiration_date"]
        if q_exp_iso not in seen_dates and q_opt["option_symbol"] != front_monthly["option_symbol"]:
            q_dte = compute_dynamic_dte(q_exp_iso, now_dt)
            results.append({
                "type": "QUARTERLY",
                "name": f"Quarterly Anchor ({q_opt['option_symbol']})",
                "option_symbol": q_opt["option_symbol"],
                "barchart_symbol": q_opt["option_symbol"],
                "underlying": q_opt["underlying"],
                "expiration_date": q_exp_iso,
                "dte": q_dte,
                "barchart_url": q_opt["barchart_url"],
            })
            seen_dates.add(q_exp_iso)

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
            exp_dt = get_cme_cutoff_dt(expiry)
        else:
            s = str(expiry).strip()
            if len(s) == 10 and s[4] == "-" and s[7] == "-":
                parts = [int(p) for p in s.split("-")]
                exp_dt = get_cme_cutoff_dt(datetime.date(parts[0], parts[1], parts[2]))
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
