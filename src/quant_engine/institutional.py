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
        # Fallback to ATM estimate if chain is sparse
        median_iv = float(df["callIV"][df["callIV"] > 0].median()) if (df["callIV"] > 0).any() else 0.18
        return SkewMetrics(
            rr25=0.0,
            bf25=0.0,
            iv_call_25d=median_iv,
            iv_put_25d=median_iv,
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
    iv_atm = float((c_iv_atm + p_iv_atm) / 2.0) if (c_iv_atm > 0 and p_iv_atm > 0) else float(max(c_iv_atm, p_iv_atm, 0.15))

    rr25 = iv_c25 - iv_p25
    bf25 = 0.5 * (iv_c25 + iv_p25) - iv_atm

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
) -> CTAConfluence:
    """Evaluates whether Call/Put Walls coincide with 20-period CTA Momentum Breakouts."""
    if price_series is not None and len(price_series) >= 20:
        h20 = float(price_series.iloc[-20:].max())
        l20 = float(price_series.iloc[-20:].min())
    else:
        # Approximate 20-day high/low boundaries using 1-sigma expected move
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
