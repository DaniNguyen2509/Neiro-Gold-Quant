"""Unit tests for Institutional Hedge Fund Modules:
1. 25-Delta Risk Reversal & Butterfly (RR25 & BF25) Volatility Skew.
2. Volatility-Targeted Position Sizing Calculator.
3. CTA Momentum Confluence Detection.
"""
from __future__ import annotations

import pandas as pd
import pytest

from src.quant_engine.institutional import (
    SkewRegime,
    SkewMetrics,
    extract_rr_bf,
    size_xauusd,
    detect_cta_confluence,
    _interp_iv_at_delta,
)


def test_interp_iv_at_delta():
    deltas = pd.Series([0.10, 0.20, 0.30, 0.50]).to_numpy()
    ivs = pd.Series([0.22, 0.20, 0.18, 0.15]).to_numpy()

    # Interpolate at target 0.25 (midway between 0.20 and 0.30 -> (0.20 + 0.18) / 2 = 0.19)
    iv_25d = _interp_iv_at_delta(deltas, ivs, target_delta=0.25)
    assert pytest.approx(iv_25d, abs=1e-4) == 0.19

    # Boundary clamp test
    assert _interp_iv_at_delta(deltas, ivs, target_delta=0.05) == 0.22
    assert _interp_iv_at_delta(deltas, ivs, target_delta=0.60) == 0.15


def test_extract_rr_bf_bullish_call_skew():
    """Call IV at 25d is 22%, Put IV at 25d is 16% -> RR25 = +6% (Bullish Call Skew)."""
    chain = pd.DataFrame([
        {"strike": 4150.0, "callDelta": 0.60, "putDelta": -0.40, "callIV": 0.17, "putIV": 0.15},
        {"strike": 4175.0, "callDelta": 0.50, "putDelta": -0.50, "callIV": 0.18, "putIV": 0.16},
        {"strike": 4200.0, "callDelta": 0.25, "putDelta": -0.75, "callIV": 0.22, "putIV": 0.19},
        {"strike": 4125.0, "callDelta": 0.75, "putDelta": -0.25, "callIV": 0.16, "putIV": 0.16},
    ])

    skew = extract_rr_bf(chain, tau=0.005, atm_strike=4175.0)
    assert skew.rr25 > 0.005
    assert skew.regime == SkewRegime.BULLISH_CALL_SKEW
    assert "BULLISH CALL SKEW" in skew.label_vi
    assert skew.bias_pct > 0.0


def test_extract_rr_bf_bearish_put_skew():
    """Call IV at 25d is 16%, Put IV at 25d is 22% -> RR25 = -6% (Defensive Put Skew)."""
    chain = pd.DataFrame([
        {"strike": 4150.0, "callDelta": 0.60, "putDelta": -0.40, "callIV": 0.16, "putIV": 0.18},
        {"strike": 4175.0, "callDelta": 0.50, "putDelta": -0.50, "callIV": 0.17, "putIV": 0.17},
        {"strike": 4200.0, "callDelta": 0.25, "putDelta": -0.75, "callIV": 0.16, "putIV": 0.25},
        {"strike": 4125.0, "callDelta": 0.75, "putDelta": -0.25, "callIV": 0.18, "putIV": 0.22},
    ])

    skew = extract_rr_bf(chain, tau=0.005, atm_strike=4175.0)
    assert skew.rr25 < -0.005
    assert skew.regime == SkewRegime.BEARISH_PUT_SKEW
    assert "DEFENSIVE PUT SKEW" in skew.label_vi
    assert skew.bias_pct < 0.0


def test_extract_rr_bf_sparse_chain_fallback():
    """Empty or very sparse chain returns safe neutral fallback without crashing."""
    chain = pd.DataFrame([{"strike": 4180.0, "callDelta": 0.5, "putDelta": -0.5, "callIV": 0.18, "putIV": 0.18}])
    skew = extract_rr_bf(chain)
    assert skew.regime == SkewRegime.NEUTRAL_SKEW
    assert skew.rr25 == 0.0


def test_size_xauusd_long_gamma_vs_short_gamma():
    """Equity $10,000, Risk 1% = $100. SL = 5.0 USD (500 USD/lot).
    Base lot = 100 / 500 = 0.20 lot.
    Long Gamma: kappa = 1.0 -> 0.20 lot.
    Short Gamma: kappa = 0.5 -> 0.10 lot (halved to preserve capital).
    """
    long_res = size_xauusd(equity_usd=10000.0, risk_pct=1.0, sl_usd=5.0, gex_regime="LONG_GAMMA")
    assert long_res.recommended_lots == 0.20
    assert long_res.regime_multiplier == 1.00
    assert pytest.approx(long_res.risk_usd, abs=0.5) == 100.0

    short_res = size_xauusd(equity_usd=10000.0, risk_pct=1.0, sl_usd=5.0, gex_regime="SHORT_GAMMA")
    assert short_res.recommended_lots == 0.10
    assert short_res.regime_multiplier == 0.50
    assert pytest.approx(short_res.risk_usd, abs=0.5) == 50.0

    neutral_res = size_xauusd(equity_usd=10000.0, risk_pct=1.0, sl_usd=5.0, gex_regime="NEUTRAL")
    assert neutral_res.recommended_lots == 0.15
    assert neutral_res.regime_multiplier == 0.75


def test_size_xauusd_minimum_lot_enforcement():
    """Very small equity or huge SL still respects broker minimum 0.01 lot."""
    res = size_xauusd(equity_usd=100.0, risk_pct=0.5, sl_usd=50.0, gex_regime="SHORT_GAMMA")
    assert res.recommended_lots == 0.01


def test_detect_cta_confluence_super_squeeze():
    """Call Wall at 4230, Spot 4180, daily_move 35. H20 = 4180 + 35*1.5 = 4232.5.
    Difference is 2.5 <= tolerance (12.25) -> CTA Super-Squeeze Fuel.
    """
    cta = detect_cta_confluence(spot=4180.0, call_wall=4230.0, put_wall=4100.0, daily_move_1s=35.0)
    assert cta.is_call_wall_confluent is True
    assert "CTA SUPER-SQUEEZE" in cta.confluence_badge


def test_detect_cta_confluence_independent():
    """Walls far from H20 / L20 are categorized as Independent Dealer Walls."""
    cta = detect_cta_confluence(spot=4180.0, call_wall=4300.0, put_wall=4000.0, daily_move_1s=20.0)
    assert cta.is_call_wall_confluent is False
    assert cta.is_put_wall_confluent is False
    assert "INDEPENDENT DEALER WALLS" in cta.confluence_badge
