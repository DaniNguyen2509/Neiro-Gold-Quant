"""Gold Options & Futures Collector (GLD / IAU / GC=F Futures).

Fetches options chains, standardizes strikes, calculates Black-76 Greeks,
and maps high-liquidity GLD ETF options to COMEX Gold Futures (GC) equivalents.
Supports Dual-Frame analysis (0DTE/Weekly front frame + Monthly institutional frame).
Includes fault-tolerant embedded benchmark data for offline and zero-crash execution.
Zero-Waste Compliant (< 15MB local machine footprint).
"""
from __future__ import annotations

import datetime
import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


def clean_num(val: Any, default: float = 0.0) -> float:
    """Sanitize dirty or NaN numeric values cleanly."""
    if val is None or pd.isna(val):
        return default
    if isinstance(val, (int, float)):
        return default if (math.isnan(val) or math.isinf(val)) else float(val)
    s = str(val).strip().replace("$", "").replace(",", "")
    try:
        f = float(s)
        return default if (math.isnan(f) or math.isinf(f)) else f
    except Exception:
        return default


def calculate_dte(expiration_date_str: str) -> float:
    """Calculate fractional days to expiration relative to US Eastern Time (16:00 ET settlement).

    Accurately scales intraday 0DTE time decay (T -> 0) into Power Hour.
    """
    try:
        exp_date = datetime.datetime.strptime(str(expiration_date_str)[:10], "%Y-%m-%d").date()
        try:
            import zoneinfo
            et_zone = zoneinfo.ZoneInfo("America/New_York")
            now_et = datetime.datetime.now(et_zone)
        except Exception:
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            now_et = now_utc - datetime.timedelta(hours=5)

        today_et = now_et.date()
        diff_days = (exp_date - today_et).days

        if diff_days <= 0:
            market_close_sec = (16 - now_et.hour) * 3600 - now_et.minute * 60 - now_et.second
            minutes_left = max(5.0, market_close_sec / 60.0)
            return max(0.0035, minutes_left / (24.0 * 60.0))
        return float(diff_days) + max(0.0, (16.0 - now_et.hour) / 24.0)
    except Exception:
        return 1.0


def normal_cdf(x: float) -> float:
    """Standard normal cumulative distribution function."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def normal_pdf(x: float) -> float:
    """Standard normal probability density function."""
    return (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * x * x)


def black76_greeks_single(
    f: float,
    k: float,
    t: float,
    r: float,
    sigma: float,
    is_call: bool,
) -> Dict[str, float]:
    """Calculate single-option Black-76 price and first/second order analytical Greeks."""
    if t <= 0.0 or sigma <= 0.0 or f <= 0.0 or k <= 0.0:
        intrinsic = max(0.0, f - k) if is_call else max(0.0, k - f)
        delta = 1.0 if (is_call and f > k) else (-1.0 if (not is_call and f < k) else 0.0)
        return {
            "price": intrinsic, "delta": delta, "gamma": 0.0,
            "vega": 0.0, "theta": 0.0, "vanna": 0.0, "charm": 0.0,
        }

    sqrt_t = math.sqrt(t)
    d1 = (math.log(f / k) + 0.5 * sigma * sigma * t) / (sigma * sqrt_t)
    d2 = d1 - sigma * sqrt_t
    df = math.exp(-r * t)
    pdf_d1 = normal_pdf(d1)

    if is_call:
        price = df * (f * normal_cdf(d1) - k * normal_cdf(d2))
        delta = df * normal_cdf(d1)
        charm = df * (r * normal_cdf(d1) + pdf_d1 * d2 / (2.0 * t))
    else:
        price = df * (k * normal_cdf(-d2) - f * normal_cdf(-d1))
        delta = -df * normal_cdf(-d1)
        charm = df * (-r * normal_cdf(-d1) + pdf_d1 * d2 / (2.0 * t))

    gamma = df * pdf_d1 / (f * sigma * sqrt_t)
    vega = df * f * sqrt_t * pdf_d1
    theta = -df * (f * pdf_d1 * sigma / (2.0 * sqrt_t))
    vanna = -df * pdf_d1 * (d2 / sigma)

    return {
        "price": price,
        "delta": delta,
        "gamma": gamma,
        "vega": vega,
        "theta": theta,
        "vanna": vanna,
        "charm": charm,
    }


def estimate_iv_brent(
    market_price: float,
    f: float,
    k: float,
    t: float,
    r: float,
    is_call: bool,
    lo: float = 0.01,
    hi: float = 3.0,
) -> float:
    """Estimate Black-76 Implied Volatility using pure Python Brent's method / bisection."""
    if market_price <= 0.0 or t <= 0.0 or f <= 0.0 or k <= 0.0:
        return 0.18

    def obj(sig: float) -> float:
        res = black76_greeks_single(f, k, t, r, sig, is_call)
        return res["price"] - market_price

    f_lo = obj(lo)
    f_hi = obj(hi)

    if f_lo * f_hi > 0:
        # Market price outside theoretical range, return safe default
        return 0.18

    # Bisection search
    for _ in range(35):
        mid = 0.5 * (lo + hi)
        if abs(hi - lo) < 1e-4:
            return mid
        f_mid = obj(mid)
        if abs(f_mid) < 1e-4:
            return mid
        if f_lo * f_mid < 0:
            hi = mid
            f_hi = f_mid
        else:
            lo = mid
            f_lo = f_mid

    return 0.5 * (lo + hi)


class GoldCollector:
    """Collector specialized for COMEX Gold (GC / MGC), ETF GLD Options and Spot XAUUSD."""

    def __init__(
        self,
        symbol: str = "GLD",
        futures_symbol: str = "GC=F",
        volatility_symbol: str = "^GVZ",
        risk_free_rate: float = 0.045,
        storage_cost: float = 0.002,
        lease_rate: float = 0.015,
        timeout: int = 20,
    ):
        self.symbol = symbol
        self.futures_symbol = futures_symbol
        self.volatility_symbol = volatility_symbol
        self.risk_free_rate = risk_free_rate
        self.storage_cost = storage_cost
        self.lease_rate = lease_rate
        self.timeout = timeout

    def get_available_expirations(self) -> List[str]:
        """Fetch list of available option expirations for GLD."""
        try:
            import yfinance as yf
            tk = yf.Ticker(self.symbol)
            expirations = list(tk.options)
            today_str = datetime.date.today().strftime("%Y-%m-%d")
            valid = [e for e in expirations if e >= today_str]
            if valid:
                return sorted(valid)
            elif expirations:
                return sorted(expirations)
        except Exception as e:
            print(f"[GoldCollector] Warning: Could not fetch online expirations ({e})")

        today_str = datetime.date.today().strftime("%Y-%m-%d")
        next_month = (datetime.date.today() + datetime.timedelta(days=30)).strftime("%Y-%m-%d")
        return [today_str, next_month]

    def get_underlying_prices(self) -> Dict[str, float]:
        """Fetch current prices for GLD ETF, Gold Futures (GC=F), GVZ, and compute Cost of Carry."""
        spot_gld = 250.0
        futures_gc = 2700.0
        r_rate = self.risk_free_rate
        gvz_iv = 18.5

        try:
            import yfinance as yf
            # 1. Fetch GLD Spot
            tk_gld = yf.Ticker(self.symbol)
            fast_gld = getattr(tk_gld, "fast_info", None)
            if fast_gld and "lastPrice" in fast_gld and fast_gld["lastPrice"] is not None:
                spot_gld = float(fast_gld["lastPrice"])
            else:
                hist_gld = tk_gld.history(period="1d")
                if not hist_gld.empty:
                    spot_gld = float(hist_gld["Close"].iloc[-1])

            # 2. Fetch Gold Futures (GC=F)
            tk_gc = yf.Ticker(self.futures_symbol)
            fast_gc = getattr(tk_gc, "fast_info", None)
            if fast_gc and "lastPrice" in fast_gc and fast_gc["lastPrice"] is not None:
                futures_gc = float(fast_gc["lastPrice"])
            else:
                hist_gc = tk_gc.history(period="1d")
                if not hist_gc.empty:
                    futures_gc = float(hist_gc["Close"].iloc[-1])

            # 3. Fetch Treasury 13-Week Bill (^IRX) for dynamic risk-free rate
            try:
                tk_irx = yf.Ticker("^IRX")
                fast_irx = getattr(tk_irx, "fast_info", None)
                if fast_irx and "lastPrice" in fast_irx and fast_irx["lastPrice"] is not None:
                    r_rate = float(fast_irx["lastPrice"]) / 100.0
            except Exception:
                pass

            # 4. Fetch CBOE Gold Volatility Index (^GVZ)
            try:
                tk_gvz = yf.Ticker(self.volatility_symbol)
                fast_gvz = getattr(tk_gvz, "fast_info", None)
                if fast_gvz and "lastPrice" in fast_gvz and fast_gvz["lastPrice"] is not None:
                    gvz_iv = float(fast_gvz["lastPrice"])
            except Exception:
                pass

        except Exception as e:
            print(f"[GoldCollector] Notice: Live fetch encountered ({e}). Using robust fallback values.")

        # Ensure valid range
        spot_gld = max(100.0, spot_gld)
        futures_gc = max(1500.0, futures_gc)
        basis_ratio = round(futures_gc / spot_gld, 4)

        # Cost of Carry for Gold: F0 = S0 * exp((r + u - y) * T)
        carry_rate = r_rate + self.storage_cost - self.lease_rate
        f0_theoretical = futures_gc * math.exp(carry_rate * (30.0 / 365.0))

        return {
            "underlying": spot_gld,
            "futures": futures_gc,
            "basis": basis_ratio,
            "r_rate": r_rate,
            "gvz_iv": gvz_iv,
            "carry_rate": carry_rate,
            "f0_theoretical": f0_theoretical,
        }

    def fetch_standardized_gold_chain(
        self,
        target_dte_mode: str = "NEAR",
        near_strikes_count: int = 35,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Fetch GLD options chain, map strikes to COMEX Gold Futures, and calculate Black-76 Greeks."""
        prices = self.get_underlying_prices()
        spot_gld = prices["underlying"]
        futures_gc = prices["futures"]
        basis_ratio = prices["basis"]
        r_rate = prices["r_rate"]

        expirations = self.get_available_expirations()
        if not expirations:
            print("[GoldCollector] Warning: No expirations found. Returning benchmark.")
            return generate_benchmark_gold_chain(spot=futures_gc), prices

        # Select target expiration
        target_exp = expirations[0]
        if target_dte_mode == "NEAR" and len(expirations) > 1:
            for exp in expirations:
                dte_test = calculate_dte(exp)
                if dte_test >= 0.8:
                    target_exp = exp
                    break

        dte_days = calculate_dte(target_exp)
        t_years = max(0.0035, dte_days / 365.0)

        df_chain = None
        try:
            import yfinance as yf
            tk = yf.Ticker(self.symbol)
            opt = tk.option_chain(target_exp)
            calls = opt.calls.copy()
            puts = opt.puts.copy()

            calls["optionType"] = "Call"
            puts["optionType"] = "Put"

            # Align calls and puts by strike
            c_sub = calls[["strike", "lastPrice", "bid", "ask", "volume", "openInterest", "impliedVolatility"]].rename(
                columns={
                    "lastPrice": "callLast", "bid": "callBid", "ask": "callAsk",
                    "volume": "callVolume", "openInterest": "callOpenInterest", "impliedVolatility": "callIV",
                }
            )
            p_sub = puts[["strike", "lastPrice", "bid", "ask", "volume", "openInterest", "impliedVolatility"]].rename(
                columns={
                    "lastPrice": "putLast", "bid": "putBid", "ask": "putAsk",
                    "volume": "putVolume", "openInterest": "putOpenInterest", "impliedVolatility": "putIV",
                }
            )

            merged = pd.merge(c_sub, p_sub, on="strike", how="outer").sort_values("strike").reset_index(drop=True)

            # Map GLD strike to Gold Futures GC strike
            merged["strike_gld"] = merged["strike"]
            merged["strike"] = (merged["strike_gld"] * basis_ratio).round(1)

            # Filter near ATM strikes
            merged["dist_atm"] = (merged["strike"] - futures_gc).abs()
            merged = merged.sort_values("dist_atm").head(near_strikes_count * 2).sort_values("strike").reset_index(drop=True)
            merged.drop(columns=["dist_atm"], inplace=True)

            # Clean prices and compute Mid
            merged["callBid"] = merged["callBid"].apply(clean_num)
            merged["callAsk"] = merged["callAsk"].apply(clean_num)
            merged["callMid"] = 0.5 * (merged["callBid"] + merged["callAsk"])
            zero_c_mid = merged["callMid"] <= 0.0
            merged.loc[zero_c_mid, "callMid"] = merged.loc[zero_c_mid, "callLast"].apply(clean_num)

            merged["putBid"] = merged["putBid"].apply(clean_num)
            merged["putAsk"] = merged["putAsk"].apply(clean_num)
            merged["putMid"] = 0.5 * (merged["putBid"] + merged["putAsk"])
            zero_p_mid = merged["putMid"] <= 0.0
            merged.loc[zero_p_mid, "putMid"] = merged.loc[zero_p_mid, "putLast"].apply(clean_num)

            merged["callOpenInterest"] = merged["callOpenInterest"].apply(lambda v: int(clean_num(v)))
            merged["putOpenInterest"] = merged["putOpenInterest"].apply(lambda v: int(clean_num(v)))
            merged["callVolume"] = merged["callVolume"].apply(lambda v: int(clean_num(v)))
            merged["putVolume"] = merged["putVolume"].apply(lambda v: int(clean_num(v)))

            # Calculate Black-76 Greeks for GC
            multiplier = 100.0  # COMEX GC Standard contract
            gex_list, vex_list, chex_list = [], [], []
            c_delta_list, p_delta_list, c_gamma_list, p_gamma_list = [], [], [], []

            for _, row in merged.iterrows():
                k_gc = float(row["strike"])
                c_iv = float(clean_num(row.get("callIV", 0.18), 0.18))
                p_iv = float(clean_num(row.get("putIV", 0.18), 0.18))
                if c_iv <= 0.01:
                    c_iv = estimate_iv_brent(float(row["callMid"]) * basis_ratio, futures_gc, k_gc, t_years, r_rate, True)
                if p_iv <= 0.01:
                    p_iv = estimate_iv_brent(float(row["putMid"]) * basis_ratio, futures_gc, k_gc, t_years, r_rate, False)

                cg = black76_greeks_single(futures_gc, k_gc, t_years, r_rate, c_iv, True)
                pg = black76_greeks_single(futures_gc, k_gc, t_years, r_rate, p_iv, False)

                c_oi = int(row["callOpenInterest"])
                p_oi = int(row["putOpenInterest"])

                # Net GEX ($M / 1% move)
                net_gex = (c_oi * cg["gamma"] - p_oi * pg["gamma"]) * multiplier * (futures_gc ** 2) * 0.01 / 1e6
                # Net VEX ($M / 1% IV)
                net_vex = (c_oi * cg["vanna"] - p_oi * pg["vanna"]) * multiplier * futures_gc * 0.01 / 1e6
                # Net CHEX ($M / day)
                net_chex = (c_oi * cg["charm"] - p_oi * pg["charm"]) * multiplier * futures_gc * (1.0 / 365.0) / 1e6

                gex_list.append(net_gex)
                vex_list.append(net_vex)
                chex_list.append(net_chex)
                c_delta_list.append(cg["delta"])
                p_delta_list.append(pg["delta"])
                c_gamma_list.append(cg["gamma"])
                p_gamma_list.append(pg["gamma"])

            merged["callDelta"] = c_delta_list
            merged["putDelta"] = p_delta_list
            merged["callGamma"] = c_gamma_list
            merged["putGamma"] = p_gamma_list
            merged["netGEX"] = gex_list
            merged["netVEX"] = vex_list
            merged["netCHEX"] = chex_list
            merged["expirationDate"] = target_exp
            merged["dte"] = dte_days

            df_chain = merged

        except Exception as e:
            print(f"[GoldCollector] Warning: Option chain parse error ({e}). Returning benchmark.")
            df_chain = generate_benchmark_gold_chain(spot=futures_gc)

        return df_chain, prices


def generate_benchmark_gold_chain(spot: float = 2700.0) -> pd.DataFrame:
    """Generate high-fidelity, production-grade COMEX Gold Options benchmark dataset.

    Used as an immutable, zero-crash fallback for tests, offline mode, and API outages.
    Accurately mirrors realistic Gold Call Skew and Put Wall support behavior.
    """
    step = 10.0
    half_count = 15
    strikes = [round(spot + (i - half_count) * step, 1) for i in range(half_count * 2 + 1)]
    today_str = datetime.date.today().strftime("%Y-%m-%d")

    records = []
    multiplier = 100.0
    r_rate = 0.045
    t_years = 7.0 / 365.0

    call_wall_strike = spot + 40.0
    put_wall_strike = spot - 40.0

    for k in strikes:
        dist = k - spot

        # Realistic Open Interest with Call Skew
        base_oi = max(150, int(1800 * math.exp(-abs(dist) / 60.0)))
        if abs(k - call_wall_strike) < 1.0:
            c_oi = base_oi * 4 + 2500
        else:
            c_oi = int(base_oi * (1.4 if dist > 0 else 0.7))

        if abs(k - put_wall_strike) < 1.0:
            p_oi = base_oi * 4 + 2200
        else:
            p_oi = int(base_oi * (1.3 if dist < 0 else 0.6))

        # Gold Call Skew: OTM Calls have higher IV than OTM Puts
        skew_adjust = 0.0006 * dist
        c_iv = max(0.12, 0.18 + skew_adjust)
        p_iv = max(0.12, 0.18 - skew_adjust * 0.5)

        cg = black76_greeks_single(spot, k, t_years, r_rate, c_iv, True)
        pg = black76_greeks_single(spot, k, t_years, r_rate, p_iv, False)

        c_mid = cg["price"]
        p_mid = pg["price"]

        net_gex = (c_oi * cg["gamma"] - p_oi * pg["gamma"]) * multiplier * (spot ** 2) * 0.01 / 1e6
        net_vex = (c_oi * cg["vanna"] - p_oi * pg["vanna"]) * multiplier * spot * 0.01 / 1e6
        net_chex = (c_oi * cg["charm"] - p_oi * pg["charm"]) * multiplier * spot * (1.0 / 365.0) / 1e6

        records.append({
            "strike": k,
            "callBid": round(max(0.05, c_mid - 0.20), 2),
            "callAsk": round(c_mid + 0.20, 2),
            "callMid": round(c_mid, 2),
            "callOpenInterest": c_oi,
            "callVolume": max(20, int(c_oi * 0.18)),
            "callIV": round(c_iv, 4),
            "callDelta": round(cg["delta"], 4),
            "callGamma": round(cg["gamma"], 6),
            "putBid": round(max(0.05, p_mid - 0.20), 2),
            "putAsk": round(p_mid + 0.20, 2),
            "putMid": round(p_mid, 2),
            "putOpenInterest": p_oi,
            "putVolume": max(20, int(p_oi * 0.15)),
            "putIV": round(p_iv, 4),
            "putDelta": round(pg["delta"], 4),
            "putGamma": round(pg["gamma"], 6),
            "netGEX": round(net_gex, 3),
            "netVEX": round(net_vex, 3),
            "netCHEX": round(net_chex, 3),
            "expirationDate": today_str,
            "dte": 7.0,
        })

    return pd.DataFrame(records)

