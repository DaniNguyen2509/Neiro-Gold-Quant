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


def solve_black76_iv(
    F: float,
    K: float,
    T: float,
    price: float,
    is_call: bool,
    r: float = 0.045,
    default_iv: float = 0.20,
) -> float:
    """Solves Black-76 implied volatility using Dekker-Brent root finder (_brentq).

    Guarantees pure-Python execution, zero external scipy dependency,
    and returns realistic calibrated volatility [0.03, 1.50].
    """
    if price <= 0.0 or F <= 0.0 or K <= 0.0 or T <= 0.0:
        return default_iv

    df_disc = math.exp(-r * T)
    sqrt_t = math.sqrt(T)

    # Intrinsic value lower bound check
    intrinsic = max(0.0, (F - K) if is_call else (K - F)) * df_disc
    if price <= intrinsic:
        return default_iv

    def b76_price(sigma: float) -> float:
        denom = max(1e-5, sigma * sqrt_t)
        d1 = (math.log(F / K) + 0.5 * (sigma ** 2) * T) / denom
        d2 = d1 - denom
        cdf_d1 = 0.5 * (1.0 + math.erf(d1 / math.sqrt(2.0)))
        cdf_d2 = 0.5 * (1.0 + math.erf(d2 / math.sqrt(2.0)))
        if is_call:
            return df_disc * (F * cdf_d1 - K * cdf_d2)
        else:
            return df_disc * (K * (1.0 - cdf_d2) - F * (1.0 - cdf_d1))

    try:
        f_low = b76_price(0.02) - price
        f_high = b76_price(2.00) - price
        if f_low * f_high <= 0:
            sol = float(_brentq(lambda s: b76_price(s) - price, 0.02, 2.00, xtol=0.001))
            return float(np.clip(sol, 0.035, 1.50))
        elif f_high < 0:
            # Market price exceeds 200% implied volatility ceiling -> clip to upper calibrated bound 1.50
            return 1.50
        elif f_low > 0:
            # Market price is below 2% implied volatility floor -> clip to lower calibrated bound 0.035
            return 0.035
    except Exception:
        pass

    return default_iv


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
        call_candidates = [s for s in snapshot.strikes if s.strike > spot_price and s.call_oi > 0]
        if not call_candidates:
            call_candidates = [s for s in snapshot.strikes if s.strike >= spot_price and s.call_oi > 0]
        put_candidates = [s for s in snapshot.strikes if s.strike < spot_price and s.put_oi > 0]
        if not put_candidates:
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


def classify_wall_regime(
    side: str,
    net_gex_at_strike: float = 0.0,
    siege_ratio: float = 0.0,
    total_net_gex: float = 0.0,
) -> str:
    """Classify structural wall regime: BOUNCE_WALL vs MAGNET_WALL vs NEUTRAL.

    Tactical Rules:
        - High Turnover / Under Siege (siege_ratio >= 0.8):
            MAGNET_WALL (breakthrough threat / heavy volume attack).
        - Put Wall:
            If siege_ratio >= 0.8 or total_net_gex < -10.0:
                MAGNET_WALL (Negative Gamma acceleration trap - forbidden to place blind bounce limit orders)
            Else if total_net_gex >= 0.0 or net_gex_at_strike >= 0.0:
                BOUNCE_WALL (Dealer Long Gamma support - mean-reverting pin/rebound)
            Else:
                NEUTRAL
        - Call Wall:
            If siege_ratio >= 0.8 or total_net_gex < -10.0 or net_gex_at_strike < -5.0:
                MAGNET_WALL (Short Gamma upside squeeze accelerator)
            Else if total_net_gex >= 0.0 or net_gex_at_strike > 5.0:
                BOUNCE_WALL (Dealer Long Gamma resistance ceiling)
            Else:
                NEUTRAL
    """
    side_lower = str(side).lower()
    if siege_ratio >= 0.8:
        return "MAGNET_WALL"

    if side_lower == "put":
        if total_net_gex < -10.0:
            return "MAGNET_WALL"
        if total_net_gex >= 0.0 or net_gex_at_strike >= 0.0:
            return "BOUNCE_WALL"
        return "NEUTRAL"
    elif side_lower == "call":
        if total_net_gex < -10.0 or net_gex_at_strike < -5.0:
            return "MAGNET_WALL"
        if total_net_gex >= 0.0 or net_gex_at_strike > 5.0:
            return "BOUNCE_WALL"
        return "NEUTRAL"
    return "NEUTRAL"


def find_gamma_weighted_walls(
    data: Any,
    top_n: int = 2,
    spot_price: float | None = None,
    r: float = 0.045,
    dte_days: float = 30.0,
    default_iv: float = 0.16,
) -> tuple[list[Wall], list[Wall]]:
    """Find top-N Call Walls and Put Walls scored by True Gamma Power = OI * Gamma.

    Solves the DTE disparity and static ghost OI trap:
    A Weekly contract near expiration (e.g. 1DTE, 400 OI) with high gamma can exert
    greater hedging force than a 30DTE Monthly contract with 1,706 OI.

    Returns:
        (call_walls, put_walls) sorted by gamma_power descending.
    """
    import pandas as pd

    records = []
    total_net_gex = 0.0

    if isinstance(data, pd.DataFrame):
        df = data.copy()
        spot = spot_price if (spot_price is not None and spot_price > 0) else float(df["strike"].median())
        t_years = max(float(dte_days) / 365.0, 1.0 / 365.0)
        sigma = max(0.01, float(default_iv))
        denom = sigma * math.sqrt(t_years)
        half_sig2_t = 0.5 * (sigma ** 2) * t_years
        df_disc = math.exp(-r * t_years)
        mult = 100.0
        scale = (spot ** 2) * 0.01 / 1e6

        raw_unphys = (
            ("callGamma" in df.columns and len(df) > 5 and df["callGamma"].nunique() <= 3)
            or ("callGamma" in df.columns and bool(((df["strike"] > (spot + 800.0)) & (df["callGamma"] > 0.001)).any()))
            or (
                "callGammaPower" in df.columns
                and "callOpenInterest" in df.columns
                and bool(
                    (
                        (df["strike"] > (spot + 800.0))
                        & (df["callOpenInterest"] > 0)
                        & ((df["callGammaPower"] / np.maximum(1, df["callOpenInterest"])) > 0.001)
                    ).any()
                )
            )
        )

        for _, row in df.iterrows():
            k = float(row.get("strike", 0.0))
            if k <= 0:
                continue
            c_oi = int(row.get("callOpenInterest", 0))
            p_oi = int(row.get("putOpenInterest", 0))
            c_vol = int(row.get("callVolume", 0))
            p_vol = int(row.get("putVolume", 0))

            # Gamma resolution: use pre-existing or compute Black-76
            c_gamma = 0.0 if raw_unphys else float(row.get("callGamma", 0.0))
            p_gamma = 0.0 if raw_unphys else float(row.get("putGamma", 0.0))
            if c_gamma <= 0.0 or p_gamma <= 0.0:
                d1 = (math.log(max(1e-4, spot / k)) + half_sig2_t) / denom
                pdf = (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * (d1 ** 2))
                b76_gamma = (df_disc * pdf) / max(1e-4, spot * denom)
                if c_gamma <= 0.0:
                    c_gamma = b76_gamma
                if p_gamma <= 0.0:
                    p_gamma = b76_gamma

            c_power = (c_oi * c_gamma) if raw_unphys else float(row.get("callGammaPower", c_oi * c_gamma))
            p_power = (p_oi * p_gamma) if raw_unphys else float(row.get("putGammaPower", p_oi * p_gamma))

            c_gex = (c_gamma * c_oi * mult * scale) if raw_unphys else float(row.get("callGEX", c_gamma * c_oi * mult * scale))
            p_gex = (-(p_gamma * p_oi * mult * scale)) if raw_unphys else float(row.get("putGEX", - (p_gamma * p_oi * mult * scale)))
            net_gex = (c_gex + p_gex) if raw_unphys else float(row.get("netGEX", c_gex + p_gex))
            total_net_gex += net_gex

            records.append({
                "strike": k,
                "call_oi": c_oi,
                "put_oi": p_oi,
                "call_vol": c_vol,
                "put_vol": p_vol,
                "call_gamma": c_gamma,
                "put_gamma": p_gamma,
                "call_power": c_power,
                "put_power": p_power,
                "net_gex": net_gex,
            })
    elif isinstance(data, OptionsSnapshot) or hasattr(data, "strikes"):
        snapshot = data
        spot = spot_price if (spot_price is not None and spot_price > 0) else 4100.0
        t_years = max(float(dte_days) / 365.0, 1.0 / 365.0)
        sigma = max(0.01, float(default_iv))
        denom = sigma * math.sqrt(t_years)
        half_sig2_t = 0.5 * (sigma ** 2) * t_years
        df_disc = math.exp(-r * t_years)
        mult = 100.0
        scale = (spot ** 2) * 0.01 / 1e6

        for s in snapshot.strikes:
            if s.strike <= 0:
                continue
            d1 = (math.log(max(1e-4, spot / s.strike)) + half_sig2_t) / denom
            pdf = (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * (d1 ** 2))
            gamma = (df_disc * pdf) / max(1e-4, spot * denom)

            c_power = s.call_oi * gamma
            p_power = s.put_oi * gamma
            c_gex = gamma * s.call_oi * mult * scale
            p_gex = - (gamma * s.put_oi * mult * scale)
            net_gex = c_gex + p_gex
            total_net_gex += net_gex

            records.append({
                "strike": float(s.strike),
                "call_oi": int(s.call_oi),
                "put_oi": int(s.put_oi),
                "call_vol": int(s.call_volume),
                "put_vol": int(s.put_volume),
                "call_gamma": gamma,
                "put_gamma": gamma,
                "call_power": c_power,
                "put_power": p_power,
                "net_gex": net_gex,
            })
    else:
        return [], []

    if not records:
        return [], []

    spot_val = spot_price if (spot_price is not None and spot_price > 0) else None
    if spot_val is not None:
        call_cands = [r for r in records if r["strike"] > spot_val and r["call_power"] > 0]
        if not call_cands:
            call_cands = [r for r in records if r["strike"] >= spot_val and r["call_power"] > 0]
        put_cands = [r for r in records if r["strike"] < spot_val and r["put_power"] > 0]
        if not put_cands:
            put_cands = [r for r in records if r["strike"] <= spot_val and r["put_power"] > 0]
        call_sorted = sorted(call_cands or records, key=lambda x: x["call_power"], reverse=True)
        put_sorted = sorted(put_cands or records, key=lambda x: x["put_power"], reverse=True)
    else:
        call_sorted = sorted(records, key=lambda x: x["call_power"], reverse=True)
        put_sorted = sorted(records, key=lambda x: x["put_power"], reverse=True)

    call_walls = [
        Wall(
            strike=rec["strike"],
            oi=rec["call_oi"],
            volume=rec["call_vol"],
            side="call",
            rank=i + 1,
            siege_ratio=compute_wall_siege_ratio(rec["call_vol"], rec["call_oi"]),
            is_under_siege=compute_wall_siege_ratio(rec["call_vol"], rec["call_oi"]) >= 0.8,
            gamma_power=round(rec["call_power"], 4),
            regime=classify_wall_regime(
                side="call",
                net_gex_at_strike=rec["net_gex"],
                siege_ratio=compute_wall_siege_ratio(rec["call_vol"], rec["call_oi"]),
                total_net_gex=total_net_gex,
            ),
            net_gex=round(rec["net_gex"], 2),
        )
        for i, rec in enumerate(call_sorted[:top_n])
    ]

    put_walls = [
        Wall(
            strike=rec["strike"],
            oi=rec["put_oi"],
            volume=rec["put_vol"],
            side="put",
            rank=i + 1,
            siege_ratio=compute_wall_siege_ratio(rec["put_vol"], rec["put_oi"]),
            is_under_siege=compute_wall_siege_ratio(rec["put_vol"], rec["put_oi"]) >= 0.8,
            gamma_power=round(rec["put_power"], 4),
            regime=classify_wall_regime(
                side="put",
                net_gex_at_strike=rec["net_gex"],
                siege_ratio=compute_wall_siege_ratio(rec["put_vol"], rec["put_oi"]),
                total_net_gex=total_net_gex,
            ),
            net_gex=round(rec["net_gex"], 2),
        )
        for i, rec in enumerate(put_sorted[:top_n])
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


def evaluate_gamma_flip_integrity(
    spot_price: float,
    zero_gamma_flip: float | None,
    dealer_hedge_flow: float,
    forward_dislocation_usd: float,
    bvc_buy_pct: float,
    kyle_lambda_regime: str = "NORMAL_LIQUIDITY",
) -> dict[str, str]:
    """Classifies whether a Gamma Flip / Breakout is a TRUE structural flip or a FAKEOUT (Bull/Bear Trap).

    Addresses the core institutional microstructure phenomenon:
    When price crosses above Zero Gamma Flip (S*) into Positive Gamma, Market Makers are Long Gamma
    and naturally SELL Futures into rallies (mean-reversion headwind). Price will get slammed back down
    (Fake Flip / Bull Trap) UNLESS aggressive options buying (dealer_hedge_flow > 0, delta_F >= 0) and
    BVC orderflow override Dealer mean-reversion selling.
    """
    z_flip = float(zero_gamma_flip) if (zero_gamma_flip is not None and zero_gamma_flip > 0) else float(spot_price)
    dist_to_flip = float(spot_price) - z_flip

    # 1. Price is ABOVE Zero Gamma Flip (in Positive Gamma territory)
    if dist_to_flip >= 0.0:
        if (
            dealer_hedge_flow >= 35.0
            and forward_dislocation_usd >= -0.60
            and bvc_buy_pct >= 52.0
            and kyle_lambda_regime != "ICEBERG_ABSORPTION"
        ):
            return {
                "flip_integrity_regime": "TRUE_BULLISH_FLIP",
                "flip_integrity_label": "🟢 FLIP THẬT (TRUE BREAKOUT): OPTIONS + MM ĐỒNG THUẬN MUA ĐUỔI",
                "flip_integrity_color": "#4ADE80",
            }
        return {
            "flip_integrity_regime": "FAKE_BULL_TRAP",
            "flip_integrity_label": "🚨 BẪY FAKEOUT (BULL TRAP): VƯỢT GAMMA NHƯNG MM ĐANG XẢ ĐÈ (DỄ BỊ ĐẠP SẬP)",
            "flip_integrity_color": "#F87171",
        }

    # 2. Price is testing / approaching Zero Gamma Flip from below (within $15)
    if dist_to_flip >= -15.0:
        if (
            dealer_hedge_flow >= 45.0
            and forward_dislocation_usd >= 0.25
            and bvc_buy_pct >= 55.0
            and kyle_lambda_regime != "ICEBERG_ABSORPTION"
        ):
            return {
                "flip_integrity_regime": "TRUE_APPROACH_IMPULSE",
                "flip_integrity_label": "🟢 XUNG LỰC THẬT: DÒNG TIỀN OPTIONS ÉP VƯỢT TRỤC GAMMA FLIP",
                "flip_integrity_color": "#4ADE80",
            }
        if (
            dealer_hedge_flow < 20.0
            or forward_dislocation_usd < -0.50
            or bvc_buy_pct < 50.0
            or kyle_lambda_regime == "ICEBERG_ABSORPTION"
        ):
            return {
                "flip_integrity_regime": "FAKE_RALLY_REJECT",
                "flip_integrity_label": "🚨 RƯỚN GIẢ (FAKE FLIP): THIẾU LỰC OPTIONS — CẨN TRỌNG BỊ ĐẠP TẠI GAMMA FLIP",
                "flip_integrity_color": "#FACC15",
            }
        return {
            "flip_integrity_regime": "CONTESTED_FLIP_ZONE",
            "flip_integrity_label": "⚖️ TRANH CHẤP SÁT GAMMA FLIP: CHỜ XÁC NHẬN DÒNG TIỀN QUYỀN CHỌN",
            "flip_integrity_color": "#38BDF8",
        }

    # 3. Price is deep below Zero Gamma Flip (Negative Gamma territory)
    if dealer_hedge_flow <= -40.0 and bvc_buy_pct <= 46.0:
        return {
            "flip_integrity_regime": "TRUE_SHORT_GAMMA_CASCADE",
            "flip_integrity_label": "🔴 SẬP THẬT (SHORT GAMMA): MM BÁN ĐUỔI THUẬN XU HƯỚNG",
            "flip_integrity_color": "#F87171",
        }
    if dealer_hedge_flow >= 40.0 and bvc_buy_pct >= 54.0 and forward_dislocation_usd >= -0.40:
        return {
            "flip_integrity_regime": "BULLISH_ABSORPTION_DIVERGENCE",
            "flip_integrity_label": "🟢 HẤP THỤ ĐÁY (BEAR TRAP): CÁ MẬP GOM CALL ÉP MM MUA ĐỠ GIÁ",
            "flip_integrity_color": "#4ADE80",
        }
    return {
        "flip_integrity_regime": "NEGATIVE_GAMMA_CHOP",
        "flip_integrity_label": "⚡ VÙNG ÂM GAMMA (DƯỚI FLIP): MM KHUẾCH ĐẠI BIẾN ĐỘNG — CHỜ ĐỒNG THUẬN",
        "flip_integrity_color": "#FACC15",
    }


def reconstruct_institutional_orderflow(
    df: Any,
    spot_price: float,
    r: float = 0.045,
    dte_days: float = 15.0,
    m5_tape: dict[str, Any] | None = None,
    zero_gamma_flip: float | None = None,
) -> dict[str, Any]:
    """Reconstructs real-time institutional orderflow without paid CME MDP 3.0 Level 3 feed.

    Combines 4 market microstructure proxies:
    1. Lee-Ready Quote Location-in-Spread + Local IV Skew Signed Options Flow
    2. Put-Call Parity Implied Forward Dislocation (delta_F = F_opt - F_GC)
    3. Guaranteed New Intraday Whale Position Initiation (Volume_K > OI_K)
    4. Bulk Volume Classification (BVC - Easley, Lopez de Prado & O'Hara) + Kyle's Lambda on GC Tape
    """
    empty_res: dict[str, Any] = {
        "implied_forward_price": round(float(spot_price or 0.0), 2),
        "forward_dislocation_usd": 0.0,
        "dislocation_regime": "SYNCHRONIZED_PARITY",
        "dislocation_label": "CÂN BẰNG PARITY (ARB LOCKED)",
        "signed_call_flow": 0.0,
        "signed_put_flow": 0.0,
        "dealer_hedge_futures_flow": 0.0,
        "options_flow_regime": "NEUTRAL_FLOW",
        "options_flow_label": "DÒNG LỆNH QUYỀN CHỌN CÂN BẰNG",
        "whale_initiations": [],
        "top_flow_strikes": [],
        "per_strike_flow": {},
        "bvc_cvd_contracts": 0.0,
        "bvc_buy_pct": 50.0,
        "kyle_lambda_regime": "NORMAL_LIQUIDITY",
        "kyle_lambda_label": "THANH KHOẢN SỔ LỆNH BÌNH THƯỜNG",
        "flip_integrity_regime": "CONTESTED_FLIP_ZONE",
        "flip_integrity_label": "⚖️ ĐANG ĐỒNG BỘ DỮ LIỆU TRỤC GAMMA FLIP",
        "flip_integrity_color": "#38BDF8",
    }
    if df is None or getattr(df, "empty", True) or spot_price <= 0:
        return empty_res

    t_years = max(float(dte_days) / 365.0, 1.0 / 365.0)
    sqrt_t = math.sqrt(t_years)
    df_disc = math.exp(-r * t_years)
    exp_rt = math.exp(r * t_years)

    # 1. Put-Call Parity Implied Forward Dislocation (delta_F = F_opt - F_GC)
    near_mask = (df["strike"].astype(float) - spot_price).abs() <= 60.0
    near_df = df[near_mask] if near_mask.any() else df
    implied_forwards: list[tuple[float, float]] = []
    for _, row in near_df.iterrows():
        k = float(row.get("strike", 0.0))
        c_mid = float(row.get("callMid", 0.0))
        p_mid = float(row.get("putMid", 0.0))
        c_bid = float(row.get("callBid", 0.0))
        p_bid = float(row.get("putBid", 0.0))
        if k > 0 and c_mid > 0 and p_mid > 0 and (c_bid > 0 or p_bid > 0):
            f_k = k + exp_rt * (c_mid - p_mid)
            if abs(f_k - spot_price) <= 80.0:
                weight = max(1.0, float(row.get("callVolume", 0) + row.get("putVolume", 0) + 10)) / (1.0 + abs(k - spot_price))
                implied_forwards.append((f_k, weight))

    if implied_forwards:
        w_sum = sum(w for _, w in implied_forwards)
        f_opt = sum(f * w for f, w in implied_forwards) / max(1e-9, w_sum)
    else:
        f_opt = float(spot_price)

    delta_f = round(f_opt - spot_price, 2)
    if delta_f >= 1.50:
        disloc_regime = "OPTIONS_LEADING_BULLISH"
        disloc_label = f"OPTIONS DẪN SÓNG MUA (+${delta_f:.2f} vs GC)"
    elif delta_f <= -1.50:
        disloc_regime = "OPTIONS_LEADING_BEARISH"
        disloc_label = f"OPTIONS DẪN SÓNG BÁN (${delta_f:.2f} vs GC)"
    else:
        disloc_regime = "SYNCHRONIZED_PARITY"
        disloc_label = f"CÂN BẰNG PARITY ({delta_f:+.2f}$)"

    # 2. Lee-Ready Quote Rule + Volatility-Signed Options Flow & Whale Initiation
    atm_idx = (df["strike"].astype(float) - spot_price).abs().idxmin()
    atm_c_iv = float(df.loc[atm_idx, "callIV"]) if "callIV" in df.columns else 0.20
    atm_p_iv = float(df.loc[atm_idx, "putIV"]) if "putIV" in df.columns else 0.20
    if atm_c_iv > 2.0:
        atm_c_iv /= 100.0
    if atm_p_iv > 2.0:
        atm_p_iv /= 100.0

    signed_call_flow = 0.0
    signed_put_flow = 0.0
    dealer_hedge_flow = 0.0
    whale_initiations: list[dict[str, Any]] = []
    flow_candidates: list[dict[str, Any]] = []
    per_strike_flow: dict[float, dict[str, Any]] = {}

    for _, row in df.iterrows():
        k = float(row.get("strike", 0.0))
        if k <= 0:
            continue
        in_band = abs(k - spot_price) <= 400.0
        c_vol = int(float(row.get("callVolume", 0)))
        p_vol = int(float(row.get("putVolume", 0)))
        c_oi = int(float(row.get("callOpenInterest", 0)))
        p_oi = int(float(row.get("putOpenInterest", 0)))
        if c_vol <= 0 and p_vol <= 0:
            continue

        c_bid = float(row.get("callBid", 0.0))
        c_ask = float(row.get("callAsk", 0.0))
        c_last = float(row.get("callLatest", row.get("callMid", 0.0)))
        c_iv = float(row.get("callIV", atm_c_iv))
        if c_iv > 2.0:
            c_iv /= 100.0
        c_iv = max(0.05, min(1.50, c_iv))

        p_bid = float(row.get("putBid", 0.0))
        p_ask = float(row.get("putAsk", 0.0))
        p_last = float(row.get("putLatest", row.get("putMid", 0.0)))
        p_iv = float(row.get("putIV", atm_p_iv))
        if p_iv > 2.0:
            p_iv /= 100.0
        p_iv = max(0.05, min(1.50, p_iv))

        # Lee-Ready Location-in-Spread [-1, +1] for Call
        if c_bid > 0 and c_ask > c_bid and c_last > 0:
            w_c = max(-1.0, min(1.0, (2.0 * c_last - (c_bid + c_ask)) / (c_ask - c_bid)))
        else:
            # Volatility Skew expansion fallback sign
            iv_diff_c = c_iv - atm_c_iv
            w_c = 0.65 if iv_diff_c > 0.003 else (-0.45 if iv_diff_c < -0.003 else 0.25)

        # Lee-Ready Location-in-Spread [-1, +1] for Put
        if p_bid > 0 and p_ask > p_bid and p_last > 0:
            w_p = max(-1.0, min(1.0, (2.0 * p_last - (p_bid + p_ask)) / (p_ask - p_bid)))
        else:
            iv_diff_p = p_iv - atm_p_iv
            w_p = 0.65 if iv_diff_p > 0.003 else (-0.45 if iv_diff_p < -0.003 else 0.25)

        d1_c = (math.log(spot_price / k) + 0.5 * (c_iv ** 2) * t_years) / max(1e-5, c_iv * sqrt_t)
        d1_p = (math.log(spot_price / k) + 0.5 * (p_iv ** 2) * t_years) / max(1e-5, p_iv * sqrt_t)
        delta_c = df_disc * 0.5 * (1.0 + math.erf(d1_c / math.sqrt(2.0)))
        delta_p = abs(df_disc * (0.5 * (1.0 + math.erf(d1_p / math.sqrt(2.0))) - 1.0))

        s_c = c_vol * w_c
        s_p = p_vol * w_p
        # Customer buys Call (+s_c) -> Dealer short Call -> Dealer MUST BUY Futures (+s_c * delta_c)
        # Customer buys Put (+s_p)  -> Dealer short Put  -> Dealer MUST SELL Futures (-s_p * delta_p)
        strike_hedge = (s_c * delta_c) - (s_p * delta_p)
        if in_band:
            signed_call_flow += s_c
            signed_put_flow += s_p
            dealer_hedge_flow += strike_hedge

        is_whale_call = c_vol > c_oi and c_vol >= 30
        is_whale_put = p_vol > p_oi and p_vol >= 30

        # Guaranteed New Intraday Whale Initiation: Volume > Open Interest
        if in_band and is_whale_call:
            whale_initiations.append({
                "strike": k,
                "side": "CALL",
                "volume": c_vol,
                "oi": c_oi,
                "new_contracts_min": c_vol - c_oi,
                "siege_ratio": round(c_vol / max(1, c_oi), 2),
                "aggressor": "BUY_TO_OPEN (LIFT ASK)" if w_c >= 0 else "SELL_TO_OPEN (HIT BID)",
            })
        if in_band and is_whale_put:
            whale_initiations.append({
                "strike": k,
                "side": "PUT",
                "volume": p_vol,
                "oi": p_oi,
                "new_contracts_min": p_vol - p_oi,
                "siege_ratio": round(p_vol / max(1, p_oi), 2),
                "aggressor": "BUY_TO_OPEN (LIFT ASK)" if w_p >= 0 else "SELL_TO_OPEN (HIT BID)",
            })

        item_dict = {
            "strike": k,
            "call_vol": c_vol,
            "put_vol": p_vol,
            "total_vol": c_vol + p_vol,
            "call_oi": c_oi,
            "put_oi": p_oi,
            "signed_call": round(s_c, 1),
            "signed_put": round(s_p, 1),
            "dealer_hedge_gc": round(strike_hedge, 1),
            "is_whale_new_oi": bool(is_whale_call or is_whale_put),
            "whale_side": "CALL" if is_whale_call else ("PUT" if is_whale_put else ""),
            "dominant_flow": (
                "MUA CALL CHỦ ĐỘNG (Ép MM Mua GC)" if strike_hedge > 15.0
                else ("MUA PUT / XẢ CALL (Ép MM Bán GC)" if strike_hedge < -15.0
                      else ("MUA NHẸ (MM Mua GC)" if strike_hedge > 2.0
                            else ("BÁN NHẸ (MM Bán GC)" if strike_hedge < -2.0 else "CÂN BẰNG / HAI CHIỀU")))
            ),
        }
        per_strike_flow[round(k, 1)] = item_dict
        if in_band:
            flow_candidates.append(item_dict)

    whale_initiations.sort(key=lambda x: x["new_contracts_min"], reverse=True)
    flow_candidates.sort(key=lambda x: x["total_vol"], reverse=True)

    if dealer_hedge_flow > 50.0:
        opt_regime = "DEALER_FORCED_BUYING"
        opt_label = f"ÉP DEALER MUA FUTURES (+{dealer_hedge_flow:,.0f} HĐ GC)"
    elif dealer_hedge_flow < -50.0:
        opt_regime = "DEALER_FORCED_SELLING"
        opt_label = f"ÉP DEALER BÁN FUTURES ({dealer_hedge_flow:,.0f} HĐ GC)"
    else:
        opt_regime = "NEUTRAL_FLOW"
        opt_label = f"CÂN BẰNG HEDGING ({dealer_hedge_flow:+,.0f} HĐ GC)"

    # 3. Bulk Volume Classification (BVC) & Kyle's Lambda on M5/M1 Futures Tape
    bvc_cvd = 0.0
    bvc_buy_vol = 0.0
    bvc_total_vol = 0.0
    kyle_regime = "NORMAL_LIQUIDITY"
    kyle_label = "THANH KHOẢN SỔ LỆNH BÌNH THƯỜNG"

    candles = (m5_tape or {}).get("chart_candles") or (m5_tape or {}).get("candles") or []
    if len(candles) >= 3:
        recent_c = candles[-24:]
        dp_list = [float(c.get("close", 0.0)) - float(c.get("open", 0.0)) for c in recent_c]
        std_dp = float(np.std(dp_list)) if len(dp_list) > 1 else 1.0
        std_dp = max(0.25, std_dp)

        lambdas: list[float] = []
        for c in recent_c:
            vol = float(c.get("volume", 0.0))
            if vol <= 0:
                continue
            dp = float(c.get("close", 0.0)) - float(c.get("open", 0.0))
            z = dp / std_dp
            # Standard Normal CDF Phi(z) for BVC
            buy_frac = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
            v_buy = vol * buy_frac
            v_sell = vol - v_buy
            bvc_cvd += (v_buy - v_sell)
            bvc_buy_vol += v_buy
            bvc_total_vol += vol
            lambdas.append(abs(dp) / vol * 1000.0)

        if lambdas and bvc_total_vol > 0:
            avg_lam = float(np.mean(lambdas))
            last_lam = lambdas[-1]
            last_vol = float(recent_c[-1].get("volume", 0.0))
            avg_v = bvc_total_vol / len(lambdas)
            if last_vol >= 1.3 * avg_v and last_lam <= 0.55 * max(1e-6, avg_lam):
                kyle_regime = "ICEBERG_ABSORPTION"
                kyle_label = "HẤP THỤ TẢNG BĂNG (ICEBERG LIMIT ABSORPTION)"
            elif last_lam >= 1.75 * max(1e-6, avg_lam):
                kyle_regime = "LIQUIDITY_VACUUM_SWEEP"
                kyle_label = "TRƯỢT GIÁ RỖNG SỔ LỆNH (VACUUM MARKET SWEEP)"

    bvc_buy_pct = round((bvc_buy_vol / bvc_total_vol) * 100.0, 1) if bvc_total_vol > 0 else 50.0
    flip_integrity = evaluate_gamma_flip_integrity(
        spot_price=spot_price,
        zero_gamma_flip=zero_gamma_flip,
        dealer_hedge_flow=dealer_hedge_flow,
        forward_dislocation_usd=delta_f,
        bvc_buy_pct=bvc_buy_pct,
        kyle_lambda_regime=kyle_regime,
    )

    return {
        "implied_forward_price": round(f_opt, 2),
        "forward_dislocation_usd": delta_f,
        "dislocation_regime": disloc_regime,
        "dislocation_label": disloc_label,
        "signed_call_flow": round(signed_call_flow, 1),
        "signed_put_flow": round(signed_put_flow, 1),
        "dealer_hedge_futures_flow": round(dealer_hedge_flow, 1),
        "options_flow_regime": opt_regime,
        "options_flow_label": opt_label,
        "whale_initiations": whale_initiations[:5],
        "top_flow_strikes": flow_candidates[:6],
        "per_strike_flow": per_strike_flow,
        "bvc_cvd_contracts": round(bvc_cvd, 1),
        "bvc_buy_pct": bvc_buy_pct,
        "kyle_lambda_regime": kyle_regime,
        "kyle_lambda_label": kyle_label,
        "flip_integrity_regime": flip_integrity["flip_integrity_regime"],
        "flip_integrity_label": flip_integrity["flip_integrity_label"],
        "flip_integrity_color": flip_integrity["flip_integrity_color"],
    }
