import math
from typing import Any
import numpy as np

from .models import OptionsSnapshot, Wall


def _brentq(f, a: float, b: float, xtol: float = 0.01, maxiter: int = 100) -> float:
    """Self-contained Dekker-Brent root finder.

    Guarantees superlinear convergence without external heavy scipy dependency.
    """
    fa = f(a)
    fb = f(b)
    if fa * fb > 0:
        raise ValueError(f"Root not bracketed: f({a})={fa}, f({b})={fb}")
    if abs(fa) < abs(fb):
        a, b = b, a
        fa, fb = fb, fa

    c = a
    fc = fa
    mflag = True
    d = 0.0

    for _ in range(maxiter):
        if abs(fb) < 1e-12 or abs(b - a) < xtol:
            return b

        if fa != fc and fb != fc:
            # Inverse quadratic interpolation
            s = (
                a * fb * fc / ((fa - fb) * (fa - fc))
                + b * fa * fc / ((fb - fa) * (fb - fc))
                + c * fa * fb / ((fc - fa) * (fc - fb))
            )
        else:
            # Secant method
            s = b - fb * (b - a) / (fb - fa)

        # Force bisection if interpolation step is unsuitable
        cond1 = not (((3 * a + b) / 4 <= s <= b) or (b <= s <= (3 * a + b) / 4))
        cond2 = mflag and abs(s - b) >= abs(b - c) / 2
        cond3 = (not mflag) and abs(s - b) >= abs(c - d) / 2
        cond4 = mflag and abs(b - c) < xtol
        cond5 = (not mflag) and abs(c - d) < xtol

        if cond1 or cond2 or cond3 or cond4 or cond5:
            s = (a + b) / 2.0
            mflag = True
        else:
            mflag = False

        fs = f(s)
        d = c
        c = b
        fc = fb

        if fa * fs < 0:
            b = s
            fb = fs
        else:
            a = s
            fa = fs

        if abs(fa) < abs(fb):
            a, b = b, a
            fa, fb = fb, fa

    return b


def compute_wall_siege_ratio(volume: int, oi: int) -> float:
    """Compute Wall Siege / Turnover Ratio = Volume / max(1, OI)."""
    if oi <= 0:
        return 0.0 if volume <= 0 else 9.99
    return round(float(volume) / float(oi), 2)


def compute_exact_gamma_flip(
    snapshot: OptionsSnapshot,
    spot_price: float,
    r: float = 0.045,
    dte_days: float = 30.0,
    default_iv: float = 0.16,
) -> float | None:
    """Compute continuous Zero Gamma (Gamma Flip Line) S* where aggregate net dealer GEX = 0.

    Solves:
        g(S) = sum_k [ n(d1(S, K_k, sigma, T)) * (OI_call_k - OI_put_k) ] = 0
    via Dekker-Brent root-finding (Black-76 model for CME Gold Futures Options).

    Returns:
        Exact S* (USD) if a zero crossing exists, or None if the market is purely Long or Short Gamma.
    """
    if not snapshot.strikes or len(snapshot.strikes) < 2:
        return None

    valid = [s for s in snapshot.strikes if s.strike > 0 and (s.call_oi > 0 or s.put_oi > 0)]
    if len(valid) < 2:
        return None

    strikes_arr = np.array([float(s.strike) for s in valid], dtype=float)
    call_oi_arr = np.array([float(s.call_oi) for s in valid], dtype=float)
    put_oi_arr = np.array([float(s.put_oi) for s in valid], dtype=float)
    diff_oi = call_oi_arr - put_oi_arr

    # If all net OI are >= 0 or all <= 0, no zero crossing is possible
    if np.all(diff_oi >= 0) or np.all(diff_oi <= 0):
        return None

    t_years = max(float(dte_days) / 365.0, 1.0 / 365.0)
    sigma = max(0.01, float(default_iv))
    denom = sigma * math.sqrt(t_years)
    half_sig2_t = 0.5 * (sigma ** 2) * t_years

    def g(s_val: float) -> float:
        if s_val <= 0:
            return -1e9
        d1 = (np.log(s_val / strikes_arr) + half_sig2_t) / denom
        pdf = np.exp(-0.5 * (d1 ** 2))
        return float(np.sum(pdf * diff_oi))

    s_min = max(1.0, float(np.min(strikes_arr)) - 150.0)
    s_max = float(np.max(strikes_arr)) + 150.0

    num_pts = max(60, len(strikes_arr) * 2)
    grid = np.linspace(s_min, s_max, num=num_pts)
    vals = np.array([g(p) for p in grid])

    crossings: list[tuple[float, float]] = []
    for i in range(len(grid) - 1):
        if vals[i] == 0.0:
            return round(float(grid[i]), 2)
        if vals[i] * vals[i + 1] < 0:
            crossings.append((float(grid[i]), float(grid[i + 1])))

    if not crossings:
        return None

    best_bracket = min(crossings, key=lambda b: abs(0.5 * (b[0] + b[1]) - spot_price))

    try:
        root = _brentq(g, best_bracket[0], best_bracket[1], xtol=0.01, maxiter=100)
        return round(float(root), 2)
    except Exception:
        return round(0.5 * (best_bracket[0] + best_bracket[1]), 2)


def find_walls(
    snapshot: OptionsSnapshot,
    top_n: int = 2,
    spot_price: float | None = None,
) -> tuple[list[Wall], list[Wall]]:
    """Find top-N Call Walls and Put Walls by OI (OTM preferred if spot_price provided).

    Returns:
        (call_walls, put_walls) sorted by OI descending.
    """
    if not snapshot.strikes:
        return [], []

    if spot_price is not None and spot_price > 0:
        call_candidates = [s for s in snapshot.strikes if s.strike >= spot_price and s.call_oi > 0]
        put_candidates = [s for s in snapshot.strikes if s.strike <= spot_price and s.put_oi > 0]
        call_sorted = sorted(call_candidates or snapshot.strikes, key=lambda s: s.call_oi, reverse=True)
        put_sorted = sorted(put_candidates or snapshot.strikes, key=lambda s: s.put_oi, reverse=True)
    else:
        call_sorted = sorted(snapshot.strikes, key=lambda s: s.call_oi, reverse=True)
        put_sorted = sorted(snapshot.strikes, key=lambda s: s.put_oi, reverse=True)

    call_walls = [
        Wall(
            strike=s.strike,
            oi=s.call_oi,
            volume=s.call_volume,
            side="call",
            rank=i + 1,
            siege_ratio=compute_wall_siege_ratio(s.call_volume, s.call_oi),
            is_under_siege=compute_wall_siege_ratio(s.call_volume, s.call_oi) >= 0.8,
        )
        for i, s in enumerate(call_sorted[:top_n])
    ]

    put_walls = [
        Wall(
            strike=s.strike,
            oi=s.put_oi,
            volume=s.put_volume,
            side="put",
            rank=i + 1,
            siege_ratio=compute_wall_siege_ratio(s.put_volume, s.put_oi),
            is_under_siege=compute_wall_siege_ratio(s.put_volume, s.put_oi) >= 0.8,
        )
        for i, s in enumerate(put_sorted[:top_n])
    ]

    return call_walls, put_walls


def gamma_squeeze_trigger(call_wall: Wall, call_mid_at_wall: float) -> float:
    """Short Gamma breakeven for upside squeeze.

    Trigger_Up = Strike_CallWall + Call_mid(CallWall)
    """
    return call_wall.strike + call_mid_at_wall


def gamma_waterfall_trigger(put_wall: Wall, put_mid_at_wall: float) -> float:
    """Short Gamma breakeven for downside waterfall.

    Trigger_Down = Strike_PutWall - Put_mid(PutWall)
    """
    return put_wall.strike - put_mid_at_wall


def detect_pin_risk(snapshot: OptionsSnapshot) -> float | None:
    """Detect pin risk: strike where both Call_OI and Put_OI are in top 2.

    Returns the pinning strike, or None if no pin risk detected.
    """
    if len(snapshot.strikes) < 2:
        return None

    call_top2 = {
        s.strike
        for s in sorted(snapshot.strikes, key=lambda s: s.call_oi, reverse=True)[:2]
    }
    put_top2 = {
        s.strike
        for s in sorted(snapshot.strikes, key=lambda s: s.put_oi, reverse=True)[:2]
    }

    overlap = call_top2 & put_top2
    if not overlap:
        return None

    # Return the strike with highest combined OI
    return max(
        overlap,
        key=lambda k: next(
            s.call_oi + s.put_oi for s in snapshot.strikes if s.strike == k
        ),
    )


def compute_net_delta_positions(
    snapshot: OptionsSnapshot,
    spot_price: float,
    r: float = 0.045,
    dte_days: float = 30.0,
    default_iv: float = 0.16,
) -> dict[str, Any]:
    """Compute exact Black-76 Net Delta Position (DEX) per strike and aggregate book tilt.

    Formulas:
        d1 = (ln(spot / strike) + 0.5 * sigma^2 * T) / (sigma * sqrt(T))
        call_delta = exp(-r * T) * N(d1)
        put_delta = call_delta - exp(-r * T)
        call_delta_contracts = call_oi * call_delta
        put_delta_contracts = put_oi * put_delta
        net_delta_contracts = call_delta_contracts + put_delta_contracts
        net_dex_usd = net_delta_contracts * 100.0 * spot_price

    Returns:
        Dictionary with per-strike details, total net delta, max tilt strike, and regime.
    """
    if not snapshot.strikes or spot_price <= 0:
        return {
            "strikes": {},
            "total_net_delta": 0.0,
            "max_tilt_strike": None,
            "max_tilt_contracts": 0.0,
            "regime": "NEUTRAL",
            "regime_label": "CÂN BẰNG (DELTA NEUTRAL)",
            "total_dex_usd": 0.0,
        }

    t_years = max(float(dte_days) / 365.0, 1.0 / 365.0)
    sigma = max(0.01, float(default_iv))
    denom = sigma * math.sqrt(t_years)
    half_sig2_t = 0.5 * (sigma ** 2) * t_years
    df_disc = math.exp(-r * t_years)

    strike_records: dict[float, dict[str, Any]] = {}
    total_net = 0.0

    for s in snapshot.strikes:
        if s.strike <= 0:
            continue
        d1 = (math.log(spot_price / s.strike) + half_sig2_t) / denom
        cdf_d1 = 0.5 * (1.0 + math.erf(d1 / math.sqrt(2.0)))
        c_delta = df_disc * cdf_d1
        p_delta = c_delta - df_disc

        c_contracts = round(s.call_oi * c_delta, 1)
        p_contracts = round(s.put_oi * p_delta, 1)
        net_contracts = round(c_contracts + p_contracts, 1)
        total_net += net_contracts

        strike_records[s.strike] = {
            "strike": s.strike,
            "call_oi": s.call_oi,
            "put_oi": s.put_oi,
            "call_delta": round(c_delta, 4),
            "put_delta": round(p_delta, 4),
            "call_contracts": c_contracts,
            "put_contracts": p_contracts,
            "net_contracts": net_contracts,
            "dex_usd": round(net_contracts * 100.0 * spot_price, 2),
        }

    total_net = round(total_net, 1)
    if strike_records:
        max_strike = max(strike_records.values(), key=lambda x: abs(x["net_contracts"]))
        max_tilt_strike = max_strike["strike"]
        max_tilt_contracts = max_strike["net_contracts"]
    else:
        max_tilt_strike = None
        max_tilt_contracts = 0.0

    if total_net > 200.0:
        regime = "BULLISH_CALL_TILT"
        regime_label = "NGHIÊNG CALL (BULLISH)"
    elif total_net < -200.0:
        regime = "BEARISH_PUT_TILT"
        regime_label = "NGHIÊNG PUT (BEARISH)"
    else:
        regime = "NEUTRAL"
        regime_label = "CÂN BẰNG (DELTA NEUTRAL)"

    return {
        "strikes": strike_records,
        "total_net_delta": total_net,
        "max_tilt_strike": max_tilt_strike,
        "max_tilt_contracts": max_tilt_contracts,
        "regime": regime,
        "regime_label": regime_label,
        "total_dex_usd": round(total_net * 100.0 * spot_price, 2),
    }
