import math
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
