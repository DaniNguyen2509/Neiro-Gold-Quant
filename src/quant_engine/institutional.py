"""src/quant_engine/institutional.py

Hedge Fund Institutional Mechanisms for Neiro-Quant:
1. 25-Delta Risk Reversal (RR25) & 25-Delta Butterfly (BF25) Volatility Skew Architecture.
2. Volatility-Targeted Position Sizing Calculator with GEX Regime Adjustment for MT5 XAUUSD.
3. CTA Momentum Breakout & Structural Confluence Detection.

Mathematical formulation audited with DeepSeek (Senior Quant / Volatility Desk).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Final, Optional

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# 1. 25-Delta Risk Reversal (RR25) & 25-Delta Butterfly (BF25)
# ---------------------------------------------------------------------------

class SkewRegime(str, Enum):
    BULLISH_CALL_SKEW = "BULLISH_CALL_SKEW"
    BEARISH_PUT_SKEW = "BEARISH_PUT_SKEW"
    NEUTRAL_SKEW = "NEUTRAL_SKEW"


@dataclass(frozen=True, slots=True)
class SkewMetrics:
    """Institutional Volatility Skew metrics extracted from options chain."""
    rr25: float                 # Call 25d IV - Put 25d IV (positive = call skew)
    bf25: float                 # 0.5 * (Call 25d IV + Put 25d IV) - ATM IV (smile curvature)
    iv_call_25d: float          # Interpolated IV at Call Delta = +0.25
    iv_put_25d: float           # Interpolated IV at Put Delta = -0.25
    iv_atm: float               # ATM Implied Volatility
    regime: SkewRegime          # Qualitative regime
    label_vi: str               # Human-readable Vietnamese label for UI HUD
    bias_pct: float             # Normalized bias score (-100% to +100%)


def _interp_iv_at_delta(deltas: np.ndarray, ivs: np.ndarray, target_delta: float) -> float:
    """Linear interpolation of IV at a target delta.

    Ensures deltas are strictly sorted before interpolation.
    """
    if len(deltas) == 0:
        raise ValueError("Empty delta array for interpolation")

    order = np.argsort(deltas)
    d_sorted, iv_sorted = deltas[order], ivs[order]

    # Clip target to boundary range to prevent out-of-bounds error
    target_clamped = float(np.clip(target_delta, d_sorted[0], d_sorted[-1]))
    return float(np.interp(target_clamped, d_sorted, iv_sorted))


def extract_rr_bf(
    chain: pd.DataFrame,
    tau: float = 0.005,             # 0.5 vol point threshold for neutral band
    atm_strike: Optional[float] = None,
) -> SkewMetrics:
    """Extracts 25-Delta Risk Reversal (RR25) and Butterfly (BF25) from options chain.

    Linear interpolation across deltas is the industry standard for CME Gold options.
    """
    # Ensure required columns exist
    df = chain.copy()
    if "callDelta" not in df.columns or "putDelta" not in df.columns:
        raise ValueError("DataFrame missing required callDelta or putDelta columns")

    # Filter rows with valid, non-zero IVs
    valid_calls = df[(df["callIV"] > 0.01) & (df["callDelta"] > 0.0)]
    valid_puts = df[(df["putIV"] > 0.01) & (df["putDelta"] < 0.0)]

    if len(valid_calls) < 2 or len(valid_puts) < 2:
        # Fallback to ATM estimate if chain is sparse, preserve standard institutional smile curvature
        median_iv = float(df["callIV"][df["callIV"] > 0].median()) if (df["callIV"] > 0).any() else 0.18
        baseline_bf25 = max(0.015, round(median_iv * 0.08, 4))
        return SkewMetrics(
            rr25=0.0,
            bf25=baseline_bf25,
            iv_call_25d=median_iv + baseline_bf25,
            iv_put_25d=median_iv + baseline_bf25,
            iv_atm=median_iv,
            regime=SkewRegime.NEUTRAL_SKEW,
            label_vi="CÂN BẰNG (NEUTRAL SKEW)",
            bias_pct=0.0,
        )

    # 1. 25-delta call: interpolate IV where callDelta = +0.25
    iv_c25 = _interp_iv_at_delta(
        valid_calls["callDelta"].to_numpy(),
        valid_calls["callIV"].to_numpy(),
        target_delta=0.25,
    )

    # 2. 25-delta put: interpolate IV where putDelta = -0.25
    iv_p25 = _interp_iv_at_delta(
        valid_puts["putDelta"].to_numpy(),
        valid_puts["putIV"].to_numpy(),
        target_delta=-0.25,
    )

    # 3. ATM IV
    if atm_strike is None:
        atm_strike = float(df["strike"].median())
    idx_atm = (df["strike"] - atm_strike).abs().idxmin()
    c_iv_atm = df.loc[idx_atm, "callIV"]
    p_iv_atm = df.loc[idx_atm, "putIV"]
    valid_all_iv = pd.concat([valid_calls["callIV"], valid_puts["putIV"]])
    if c_iv_atm > 0.05 and p_iv_atm > 0.05:
        iv_atm = float((c_iv_atm + p_iv_atm) / 2.0)
    elif c_iv_atm > 0.05:
        iv_atm = float(c_iv_atm)
    elif p_iv_atm > 0.05:
        iv_atm = float(p_iv_atm)
    elif not valid_all_iv.empty:
        # If specific strike lacks IV, estimate ATM IV at trough (below wing average)
        avg_wings = 0.5 * (iv_c25 + iv_p25)
        median_iv = float(valid_all_iv.median())
        iv_atm = float(min(median_iv, max(0.10, avg_wings - 0.015)))
    else:
        iv_atm = 0.18

    rr25 = iv_c25 - iv_p25
    bf25 = max(0.005, 0.5 * (iv_c25 + iv_p25) - iv_atm)

    # Classify regime
    if rr25 > tau:
        regime = SkewRegime.BULLISH_CALL_SKEW
        label_vi = "BULLISH CALL SKEW (DÒNG TIỀN QUỸ GOM CALL CƯỢC PHÁ ĐỈNH)"
    elif rr25 < -tau:
        regime = SkewRegime.BEARISH_PUT_SKEW
        label_vi = "DEFENSIVE PUT SKEW (SMART MONEY MUA BẢO HIỂM PHÒNG HỘ)"
    else:
        regime = SkewRegime.NEUTRAL_SKEW
        label_vi = "CÂN BẰNG (NEUTRAL SKEW)"

    # Bias percentage: scaled from -100% to +100% with +/- 3 vol points as saturation
    bias_pct = float(np.clip(rr25 / 0.03 * 100.0, -100.0, 100.0))

    return SkewMetrics(
        rr25=round(rr25, 4),
        bf25=round(bf25, 4),
        iv_call_25d=round(iv_c25, 4),
        iv_put_25d=round(iv_p25, 4),
        iv_atm=round(iv_atm, 4),
        regime=regime,
        label_vi=label_vi,
        bias_pct=round(bias_pct, 1),
    )


# ---------------------------------------------------------------------------
# 2. Volatility-Targeted Position Sizing Calculator
# ---------------------------------------------------------------------------

OZ_PER_LOT: Final[float] = 100.0
MIN_LOT: Final[float] = 0.01
LOT_STEP: Final[float] = 0.01
MAX_LOTS: Final[float] = 5.0


@dataclass(frozen=True, slots=True)
class SizingResult:
    """Output of quantitative position sizing calculation."""
    recommended_lots: float     # Final rounded lot size for MT5
    base_lots: float            # Unadjusted risk-based lot size
    risk_usd: float             # Actual dollar risk with final lots
    regime_multiplier: float    # Regime scale factor kappa (1.0 vs 0.5)
    account_equity: float       # Base equity
    risk_pct: float             # Target risk percentage
    sl_usd: float               # Stop loss distance in USD/oz
    regime_note: str            # Explanation for the sizing multiplier


def size_xauusd(
    equity_usd: float = 10000.0,
    risk_pct: float = 1.0,          # 1.0% risk
    sl_usd: float = 4.5,            # SL distance in USD/oz
    gex_regime: str = "LONG_GAMMA",
    max_lots: float = MAX_LOTS,
) -> SizingResult:
    """Calculates quantitative lot size for MT5 XAUUSD trades.

    Adapts dynamically to the dealer market regime:
    - Long Gamma: Normal volatility, mean-reversion favored -> kappa = 1.0
    - Short Gamma: Volatility explosion, gap risk, wide slippage -> kappa = 0.5 (Capital Preservation)
    - Neutral: kappa = 0.75
    """
    if sl_usd <= 0:
        sl_usd = 4.5  # Safe default if invalid

    # 1. Base Risk Budget ($)
    risk_budget_usd = equity_usd * (risk_pct / 100.0)

    # 2. Base lots: each $1.0 move on 1 lot (100 oz) = $100.0 PnL
    base_lots = risk_budget_usd / (OZ_PER_LOT * sl_usd)

    # 3. GEX Regime Multiplier
    reg_upper = gex_regime.upper()
    if "LONG" in reg_upper:
        kappa = 1.00
        regime_note = "Long Gamma (Chuẩn 100% Vol Budget)"
    elif "SHORT" in reg_upper:
        kappa = 0.50
        regime_note = "Short Gamma (Giảm 50% Vol Bảo Vệ Vốn)"
    else:
        kappa = 0.75
        regime_note = "Neutral Gamma (75% Vol Baseline)"

    raw_lots = base_lots * kappa
    capped_lots = min(raw_lots, max_lots)

    # 4. Round to broker step 0.01 and enforce minimum 0.01
    final_lots = max(MIN_LOT, math.floor(capped_lots / LOT_STEP) * LOT_STEP)
    final_lots = round(final_lots, 2)
    actual_risk_usd = round(final_lots * OZ_PER_LOT * sl_usd, 2)

    return SizingResult(
        recommended_lots=final_lots,
        base_lots=round(base_lots, 3),
        risk_usd=actual_risk_usd,
        regime_multiplier=kappa,
        account_equity=equity_usd,
        risk_pct=risk_pct,
        sl_usd=sl_usd,
        regime_note=regime_note,
    )


# ---------------------------------------------------------------------------
# 3. CTA Momentum Confluence Detection
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class CTAConfluence:
    """Detects confluence between Dealer Walls and algorithmic CTA Breakout levels."""
    h20: float
    l20: float
    is_call_wall_confluent: bool
    is_put_wall_confluent: bool
    confluence_badge: str
    confluence_desc: str


def detect_cta_confluence(
    spot: float,
    call_wall: float,
    put_wall: float,
    daily_move_1s: float = 35.0,
    price_series: Optional[pd.Series] = None,
    daily_candles: Optional[list[dict]] = None,
) -> CTAConfluence:
    """Evaluates whether Call/Put Walls coincide with 20-period CTA Momentum Breakouts."""
    if daily_candles and len(daily_candles) >= 5:
        window_1d = daily_candles[-20:]
        highs = [float(c.get("high", spot)) for c in window_1d if float(c.get("high", 0.0)) > 0]
        lows = [float(c.get("low", spot)) for c in window_1d if float(c.get("low", 0.0)) > 0]
        if highs and lows:
            h20 = max(highs)
            l20 = min(lows)
        else:
            h20 = spot + daily_move_1s * 1.5
            l20 = spot - daily_move_1s * 1.5
    elif price_series is not None and len(price_series) >= 5:
        h20 = float(price_series.iloc[-20:].max())
        l20 = float(price_series.iloc[-20:].min())
    else:
        # Approximate 20-day high/low boundaries using 1-sigma expected move when 1D history is unavailable
        h20 = spot + daily_move_1s * 1.5
        l20 = spot - daily_move_1s * 1.5

    # Confluence tolerance: within 0.35 of daily expected move
    tol = max(5.0, daily_move_1s * 0.35)

    is_call_conf = abs(call_wall - h20) <= tol
    is_put_conf = abs(put_wall - l20) <= tol

    if is_call_conf and is_put_conf:
        badge = "DUAL CTA BREAKOUT CONFLUENCE"
        desc = "Cả Call Wall và Put Wall đều trùng khớp hoàn hảo với biên độ nổ của quỹ CTA (High Conviction)."
    elif is_call_conf:
        badge = "CTA SUPER-SQUEEZE FUEL"
        desc = "Call Wall trùng mốc 20-Day High của CTA. Khi giá vượt cản, lực mua tự động của quỹ sẽ kích hoạt Super-Squeeze."
    elif is_put_conf:
        badge = "CTA CAPITULATION WATERFALL"
        desc = "Put Wall trùng mốc 20-Day Low của CTA. Nếu thủng cản, các quỹ CTA sẽ kích hoạt bán tháo theo xu hướng."
    else:
        badge = "INDEPENDENT DEALER WALLS"
        desc = "Các chốt chặn hiện tại do Market Maker độc lập phòng thủ trong biên độ thông thường."

    return CTAConfluence(
        h20=round(h20, 2),
        l20=round(l20, 2),
        is_call_wall_confluent=is_call_conf,
        is_put_wall_confluent=is_put_conf,
        confluence_badge=badge,
        confluence_desc=desc,
    )


# ---------------------------------------------------------------------------
# 4. Volatility Risk Premium (VRP - Carr & Wu 2009) & Informed Trader Matrix
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class VRPMetrics:
    """Carr & Wu (2009) Volatility Risk Premium comparing CME ATM IV vs GC=F Realized Volatility."""
    iv_atm_pct: float
    rv_annual_pct: float
    vrp_vol_spread_pct: float
    vrp_var_spread: float
    iv_rv_ratio: float
    regime: str
    label_vi: str
    tactical_advice_vi: str


def compute_vrp_metrics(
    sigma_atm: float,
    daily_candles: Optional[list[dict]] = None,
    intraday_candles: Optional[list[dict]] = None,
    spot: float = 4700.0,
) -> VRPMetrics:
    """Computes Volatility Risk Premium: VRP = IV_ATM^2 - RV_GC^2 (and vol spread IV_ATM - RV_GC)."""
    iv_dec = float(sigma_atm) if float(sigma_atm) <= 2.0 else float(sigma_atm) / 100.0
    iv_dec = max(0.05, min(1.50, iv_dec))
    iv_pct = round(iv_dec * 100.0, 2)

    rv_dec = iv_dec * 0.90  # Safe fallback only if no candle history exists
    if daily_candles and len(daily_candles) >= 5:
        w_c = daily_candles[-20:]
        # Parkinson High-Low Estimator (1980) on real CME GC=F 1D candles:
        # sigma_P^2 = (252 / (4 * N * ln(2))) * sum(ln(H_i / L_i)^2)
        hl_sq = []
        for c in w_c:
            h_v = float(c.get("high", 0.0))
            l_v = float(c.get("low", 0.0))
            if h_v > l_v > 0:
                hl_sq.append((math.log(h_v / l_v)) ** 2)
        if hl_sq:
            parkinson_var = (252.0 / (4.0 * len(hl_sq) * math.log(2.0))) * float(np.sum(hl_sq))
            rv_dec = math.sqrt(max(1e-6, parkinson_var))
    elif intraday_candles and len(intraday_candles) >= 10:
        closes = [float(c.get("close", 0.0)) for c in intraday_candles[-60:] if float(c.get("close", 0.0)) > 0]
        if len(closes) >= 10:
            log_rets = np.diff(np.log(np.array(closes, dtype=float)))
            # Annualize M1/M5 returns assuming ~1,380 Globex minutes/day * 252 days
            rv_dec = float(np.std(log_rets)) * math.sqrt(252.0 * 276.0)

    rv_dec = max(0.04, min(1.50, rv_dec))
    rv_pct = round(rv_dec * 100.0, 2)

    vrp_vol_pct = round(iv_pct - rv_pct, 2)
    vrp_var = round((iv_dec ** 2) - (rv_dec ** 2), 4)
    ratio = round(iv_pct / max(1.0, rv_pct), 2)

    if vrp_vol_pct >= 4.0 or ratio >= 1.35:
        regime = "OVERPRICED_VEGA_CRUSH"
        label_vi = f"🔥 VRP +{vrp_vol_pct:.1f}% (IV {iv_pct:.1f}% > RV {rv_pct:.1f}% • CHỜ VEGA CRUSH)"
        advice_vi = "IV đang đắt hơn biến động thực tế: Khi tin qua & VPIN hạ nhiệt, Net VEX (Vanna) sẽ kéo giá giật ngược về tâm."
    elif vrp_vol_pct <= -2.0 or ratio <= 0.85:
        regime = "UNDERPRICED_GAMMA_EXPLOSION"
        label_vi = f"⚡ VRP {vrp_vol_pct:+.1f}% (IV {iv_pct:.1f}% < RV {rv_pct:.1f}% • NỔ BIẾN ĐỘNG)"
        advice_vi = "Biến động thực tế vượt định giá Options: Ưu tiên đánh thuận chiều Breakout, không chặn tàu."
    else:
        regime = "FAIR_VOLATILITY_PREMIUM"
        label_vi = f"⚖️ VRP {vrp_vol_pct:+.1f}% (IV {iv_pct:.1f}% vs RV {rv_pct:.1f}% • ĐỊNH GIÁ CÂN BẰNG)"
        advice_vi = "Phần bù rủi ro biến động ở mức cân bằng chuẩn tổ chức."

    return VRPMetrics(
        iv_atm_pct=iv_pct,
        rv_annual_pct=rv_pct,
        vrp_vol_spread_pct=vrp_vol_pct,
        vrp_var_spread=vrp_var,
        iv_rv_ratio=ratio,
        regime=regime,
        label_vi=label_vi,
        tactical_advice_vi=advice_vi,
    )


@dataclass(frozen=True, slots=True)
class InformedTraderRegime:
    """Closed-loop Informed Trader Execution Regime (Kyle 1985; Grossman-Stiglitz 1980; Easley et al. 2012)."""
    session_name: str
    sigma_u_depth_score: float
    vpin_pct: float
    kyle_lambda_ols: float
    parity_z_score: float
    vrp_spread_pct: float
    bayesian_conviction_rho: float
    kelly_fraction_mult: float
    regime_code: str
    action_badge_vi: str
    action_color: str
    tactical_guidance_vi: str


def resolve_cme_session_liquidity() -> tuple[str, float]:
    """Resolves current CME Globex session liquidity depth sigma_u in [0.0, 1.0]."""
    import datetime
    try:
        from zoneinfo import ZoneInfo
        now_et = datetime.datetime.now(ZoneInfo("America/New_York"))
    except Exception:
        now_et = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-5)))

    wd = now_et.weekday()
    hr = now_et.hour
    if wd == 5 or (wd == 4 and hr >= 17) or (wd == 6 and hr < 18) or hr == 17:
        return "GLOBEX_CLOSED", 0.0
    # NY COMEX Pit & Overlap (08:00 - 13:30 ET)
    if 8 <= hr < 14:
        return "NY_COMEX_DEEP", 0.95
    # London Pre-US & Afternoon NY (03:00 - 08:00 ET or 14:00 - 16:59 ET)
    if 3 <= hr < 8 or 14 <= hr < 17:
        return "LONDON_DEEP", 0.80
    # Asian Globex Session (18:00 - 02:59 ET) -> lower noise flow sigma_u
    return "ASIAN_THIN", 0.35


def evaluate_informed_trader_regime(
    spot: float,
    call_wall: float,
    put_wall: float,
    total_net_gex: float,
    vpin_pct: float,
    kyle_lambda_ols: float,
    kyle_regime: str,
    parity_z_score: float,
    dealer_hedge_flow: float,
    vrp_spread_pct: float,
    session_tag: Optional[str] = None,
) -> InformedTraderRegime:
    """Evaluates the 5-State Informed Trader Action Matrix, Bayesian SNR rho_{v,s}, and Fractional Kelly."""
    if session_tag is None:
        session_name, sigma_u = resolve_cme_session_liquidity()
    else:
        session_name = session_tag
        sigma_u = (
            0.95 if "NY" in session_tag
            else (0.80 if "LONDON" in session_tag else (0.0 if "CLOSED" in session_tag else 0.35))
        )

    # Bayesian Signal-to-Noise Ratio (SNR = sigma_v^2 / sigma_eps^2) from multi-pillar structural alignment
    gex_signal = min(2.0, abs(total_net_gex) / 25.0)
    hedge_signal = min(2.0, abs(dealer_hedge_flow) / 60.0)
    parity_signal = min(2.0, abs(parity_z_score) / 1.5)
    snr = max(0.05, (0.40 * gex_signal + 0.35 * hedge_signal + 0.25 * parity_signal) * max(0.30, sigma_u))
    rho_vs = round(math.sqrt(snr / (1.0 + snr)), 2)

    dist_cw = abs(call_wall - spot)
    dist_pw = abs(spot - put_wall)
    near_wall = min(dist_cw, dist_pw) <= 15.0

    if session_name == "GLOBEX_CLOSED":
        return InformedTraderRegime(
            session_name=session_name,
            sigma_u_depth_score=sigma_u,
            vpin_pct=vpin_pct,
            kyle_lambda_ols=kyle_lambda_ols,
            parity_z_score=parity_z_score,
            vrp_spread_pct=vrp_spread_pct,
            bayesian_conviction_rho=rho_vs,
            kelly_fraction_mult=0.25,
            regime_code="GLOBEX_SETTLED_WAIT",
            action_badge_vi="⏸️ SÀN CME ĐÓNG CỬA: QUAN SÁT CẤU TRÚC ĐẦU PHIÊN",
            action_color="#94A3B8",
            tactical_guidance_vi="Chờ mở cửa phiên CME Globex (05:00/06:00 sáng VN) để đo lại dòng lệnh VPIN thực tế.",
        )

    if kyle_regime == "PREDATORY_SWEEP_EXHAUSTION":
        return InformedTraderRegime(
            session_name=session_name,
            sigma_u_depth_score=sigma_u,
            vpin_pct=vpin_pct,
            kyle_lambda_ols=kyle_lambda_ols,
            parity_z_score=parity_z_score,
            vrp_spread_pct=vrp_spread_pct,
            bayesian_conviction_rho=max(0.72, rho_vs),
            kelly_fraction_mult=0.85,
            regime_code="PREDATORY_EXHAUSTION_REV",
            action_badge_vi="🟢 CẠN KIỆT QUÉT SĂN MỒI (SWEEP EXHAUSTION) — VÀO ĐẢO CHIỀU",
            action_color="#4ADE80",
            tactical_guidance_vi="Cú quét thanh khoản cơ học (Brunnermeier-Pedersen) đã đạt đỉnh Volume và λ đang hạ nhiệt: Canh bắt đảo chiều ăn nhịp hồi.",
        )

    if vpin_pct >= 65.0 or (near_wall and total_net_gex < -10.0 and vpin_pct >= 55.0):
        return InformedTraderRegime(
            session_name=session_name,
            sigma_u_depth_score=sigma_u,
            vpin_pct=vpin_pct,
            kyle_lambda_ols=kyle_lambda_ols,
            parity_z_score=parity_z_score,
            vrp_spread_pct=vrp_spread_pct,
            bayesian_conviction_rho=rho_vs,
            kelly_fraction_mult=0.50,
            regime_code="TOXIC_SQUEEZE_HUNT",
            action_badge_vi=f"🚨 VPIN ĐỘC HẠI ({vpin_pct:.1f}% ≥ 65%): HỦY LIMIT CẢN TÀU — ĐÁNH THUẬN SQUEEZE",
            action_color="#F87171",
            tactical_guidance_vi="Dòng tiền Informed Trader đang càn quét một chiều (Phân vị >90%): Tuyệt đối không đặt Limit chặn Wall, chỉ đánh thuận chiều phá vỡ.",
        )

    if near_wall and vpin_pct < 40.0 and sigma_u >= 0.60:
        return InformedTraderRegime(
            session_name=session_name,
            sigma_u_depth_score=sigma_u,
            vpin_pct=vpin_pct,
            kyle_lambda_ols=kyle_lambda_ols,
            parity_z_score=parity_z_score,
            vrp_spread_pct=vrp_spread_pct,
            bayesian_conviction_rho=max(0.75, rho_vs),
            kelly_fraction_mult=1.00,
            regime_code="WALL_MEAN_REVERSION",
            action_badge_vi=f"🟢 CHẠM WALL + VPIN THẤP ({vpin_pct:.1f}% < 40%): KÍCH HOẠT ĐẢO CHIỀU (FADE WALL)",
            action_color="#4ADE80",
            tactical_guidance_vi="Thanh khoản đám đông (σ_u) dày và VPIN thấp: Tựa lưng vào dòng tiền phòng hộ cơ học của Market Maker để đánh đảo chiều.",
        )

    if vrp_spread_pct >= 4.0 and vpin_pct < 55.0:
        return InformedTraderRegime(
            session_name=session_name,
            sigma_u_depth_score=sigma_u,
            vpin_pct=vpin_pct,
            kyle_lambda_ols=kyle_lambda_ols,
            parity_z_score=parity_z_score,
            vrp_spread_pct=vrp_spread_pct,
            bayesian_conviction_rho=max(0.68, rho_vs),
            kelly_fraction_mult=0.75,
            regime_code="VEGA_CRUSH_VANNA",
            action_badge_vi=f"🔥 VRP CỰC ĐẠI (+{vrp_spread_pct:.1f}%) + VPIN HẠ NHIỆT: ĐÓN SÓNG VANNA / VEGA CRUSH",
            action_color="#38BDF8",
            tactical_guidance_vi="IV đang bị thổi phồng quá mức so với RV: Đón lực mua/bán trả giá của Market Maker khi IV xì hơi (Vega Crush) về trục Vanna.",
        )

    if session_name == "ASIAN_THIN" and vpin_pct < 60.0:
        return InformedTraderRegime(
            session_name=session_name,
            sigma_u_depth_score=sigma_u,
            vpin_pct=vpin_pct,
            kyle_lambda_ols=kyle_lambda_ols,
            parity_z_score=parity_z_score,
            vrp_spread_pct=vrp_spread_pct,
            bayesian_conviction_rho=rho_vs,
            kelly_fraction_mult=0.25,
            regime_code="THIN_BOOK_WAIT",
            action_badge_vi="⚠️ THANH KHOẢN MỎNG PHIÊN Á (σ_u THẤP): GIẢM SIZE / CHỜ PHIÊN ÂU-MỸ",
            action_color="#FACC15",
            tactical_guidance_vi="Theo Kyle (1985), khi σ_u thấp thì λ phình to khiến lệnh dễ tự trượt giá: Chỉ rải Limit nhỏ tại Wall hoặc chờ phiên Âu.",
        )

    if abs(total_net_gex) < 12.0 and abs(parity_z_score) < 1.0 and not near_wall:
        return InformedTraderRegime(
            session_name=session_name,
            sigma_u_depth_score=sigma_u,
            vpin_pct=vpin_pct,
            kyle_lambda_ols=kyle_lambda_ols,
            parity_z_score=parity_z_score,
            vrp_spread_pct=vrp_spread_pct,
            bayesian_conviction_rho=rho_vs,
            kelly_fraction_mult=0.25,
            regime_code="ATM_RANDOM_WALK",
            action_badge_vi="⚖️ MẮT BÃO TRUNG HÒA (ATM RANDOM WALK): ĐỨNG NGOÀI CHỜ GIÁ TIẾP CẬN WALL",
            action_color="#CBD5E1",
            tactical_guidance_vi="Market Maker không bị ép phòng hộ cơ học tại vùng trung tâm: Đứng ngoài bảo toàn vốn chờ giá dạt về biên.",
        )

    return InformedTraderRegime(
        session_name=session_name,
        sigma_u_depth_score=sigma_u,
        vpin_pct=vpin_pct,
        kyle_lambda_ols=kyle_lambda_ols,
        parity_z_score=parity_z_score,
        vrp_spread_pct=vrp_spread_pct,
        bayesian_conviction_rho=rho_vs,
        kelly_fraction_mult=0.75 if sigma_u >= 0.70 else 0.50,
        regime_code="ACTIVE_STRUCTURAL_FLOW",
        action_badge_vi=f"🎯 THEO DÕI DÒNG TIỀN CẤU TRÚC (VPIN {vpin_pct:.1f}% • ρ={rho_vs:.2f} • Kelly {0.75 if sigma_u >= 0.70 else 0.50:.2f}x)",
        action_color="#38BDF8",
        tactical_guidance_vi="Canh giao dịch tại các chốt chặn Sàn dưới / Trần trên theo hướng ưu thế của Dealer Hedge Flow và Put-Call Parity.",
    )

