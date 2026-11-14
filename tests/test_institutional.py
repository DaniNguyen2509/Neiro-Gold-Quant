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


def test_detect_cta_confluence_with_real_daily_candles():
    """When real 1D candles are passed, H20 and L20 use the exact 20-day Donchian High/Low."""
    daily_candles = [
        {"high": 4650.0 + i * 10.0, "low": 4600.0 - i * 5.0}
        for i in range(10)
    ]
    cta = detect_cta_confluence(
        spot=4700.0,
        call_wall=4742.0,
        put_wall=4553.0,
        daily_move_1s=30.0,
        daily_candles=daily_candles,
    )
    assert cta.h20 == 4740.0
    assert cta.l20 == 4555.0
    assert cta.is_call_wall_confluent is True
    assert cta.is_put_wall_confluent is True
    assert "DUAL CTA BREAKOUT CONFLUENCE" in cta.confluence_badge


def test_reconstruct_institutional_orderflow_zero_bs_missing_quotes():
    """Verify that strikes without valid two-sided Bid/Ask quotes get w_c=0 and w_p=0 (no arbitrary fallback weights)."""
    from src.quant_engine.dealer import reconstruct_institutional_orderflow

    df = pd.DataFrame([
        {
            "strike": 4700.0,
            "callBid": 0.0, "callAsk": 0.0, "callMid": 45.0, "callLatest": 45.0,
            "putBid": 0.0, "putAsk": 0.0, "putMid": 42.0, "putLatest": 42.0,
            "callVolume": 500, "callOpenInterest": 1000,
            "putVolume": 500, "putOpenInterest": 1000,
            "callIV": 0.35, "putIV": 0.15,
        }
    ])
    res = reconstruct_institutional_orderflow(df, spot_price=4700.0, r=0.045, dte_days=10.0)
    assert res["signed_call_flow"] == 0.0
    assert res["signed_put_flow"] == 0.0
    assert res["dealer_hedge_futures_flow"] == 0.0


def test_reconstruct_institutional_orderflow_lee_ready_bvc_and_whales():
    """Verify Lee-Ready Signed Flow, Put-Call Parity Dislocation, Whale Initiation (Vol > OI), and BVC/Kyle Lambda."""
    from src.quant_engine.dealer import reconstruct_institutional_orderflow

    df = pd.DataFrame([
        {
            "strike": 4075.0,
            "callBid": 64.0, "callAsk": 66.0, "callMid": 65.0, "callLatest": 65.8,
            "putBid": 60.0, "putAsk": 62.0, "putMid": 61.0, "putLatest": 60.2,
            "callVolume": 450, "callOpenInterest": 200,  # Whale Initiation: 450 > 200 (+250 new contracts)
            "putVolume": 80, "putOpenInterest": 500,
            "callIV": 0.225, "putIV": 0.225,
        },
        {
            "strike": 4100.0,
            "callBid": 52.0, "callAsk": 54.0, "callMid": 53.0, "callLatest": 53.9,
            "putBid": 73.0, "putAsk": 75.0, "putMid": 74.0, "putLatest": 73.2,
            "callVolume": 600, "callOpenInterest": 1200,
            "putVolume": 50, "putOpenInterest": 800,
            "callIV": 0.228, "putIV": 0.224,
        },
    ])
    m5_tape = {
        "chart_candles": [
            {"open": 4070.0, "close": 4072.0, "volume": 500},
            {"open": 4072.0, "close": 4074.5, "volume": 650},
            {"open": 4074.5, "close": 4074.7, "volume": 1200},  # High volume, tiny body -> Iceberg absorption
        ]
    }
    res = reconstruct_institutional_orderflow(df, spot_price=4075.0, r=0.045, dte_days=17.0, m5_tape=m5_tape)

    # 1. Implied forward F_opt = 4075 + exp(rT)*(65 - 61) ~= 4079.01 -> +4.01 USD > +1.50 USD bullish lead
    assert res["forward_dislocation_usd"] > 1.50
    assert res["dislocation_regime"] == "OPTIONS_LEADING_BULLISH"

    # 2. Aggressive Call buying at Ask + Put hitting Bid -> positive Dealer Forced Futures Buying
    assert res["signed_call_flow"] > 0
    assert res["dealer_hedge_futures_flow"] > 50.0
    assert res["options_flow_regime"] == "DEALER_FORCED_BUYING"

    # 3. Guaranteed New Whale Initiation detected at Strike 4075 Call (Vol 450 > OI 200)
    assert len(res["whale_initiations"]) >= 1
    w0 = res["whale_initiations"][0]
    assert w0["strike"] == 4075.0
    assert w0["side"] == "CALL"
    assert w0["new_contracts_min"] == 250

    # 4. BVC Cumulative Volume Delta > 0 and Kyle's Lambda detects ICEBERG_ABSORPTION on final bar
    assert res["bvc_cvd_contracts"] > 0
    assert res["bvc_buy_pct"] > 50.0
    assert res["kyle_lambda_regime"] == "ICEBERG_ABSORPTION"


def test_evaluate_gamma_flip_integrity_true_vs_fake_bull_trap():
    """Verify True Gamma Flip vs Fakeout Bull Trap classification when price crosses Zero Gamma Flip."""
    from src.quant_engine.dealer import evaluate_gamma_flip_integrity

    # 1. TRUE_BULLISH_FLIP: Price above Zero Gamma ($4,095 vs $4,090) WITH strong dealer buying & parity lead
    true_flip = evaluate_gamma_flip_integrity(
        spot_price=4095.0,
        zero_gamma_flip=4090.0,
        dealer_hedge_flow=180.0,
        forward_dislocation_usd=1.25,
        bvc_buy_pct=64.0,
        kyle_lambda_regime="LIQUIDITY_VACUUM_SWEEP",
    )
    assert true_flip["flip_integrity_regime"] == "TRUE_BULLISH_FLIP"
    assert "FLIP THẬT" in true_flip["flip_integrity_label"]

    # 2. FAKE_BULL_TRAP: Price crossed above Zero Gamma ($4,095 vs $4,090), but Dealer is selling / Iceberg absorption
    fake_flip = evaluate_gamma_flip_integrity(
        spot_price=4095.0,
        zero_gamma_flip=4090.0,
        dealer_hedge_flow=-45.0,
        forward_dislocation_usd=-1.40,
        bvc_buy_pct=44.0,
        kyle_lambda_regime="ICEBERG_ABSORPTION",
    )
    assert fake_flip["flip_integrity_regime"] == "FAKE_BULL_TRAP"
    assert "BẪY FAKEOUT" in fake_flip["flip_integrity_label"]


