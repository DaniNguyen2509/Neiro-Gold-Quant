"""TDD tests verifying VPIN BVC calibration and KHỐI 6 / Strategy V2 calibration."""

from __future__ import annotations

import pandas as pd

from src.quant_engine.dealer import compute_vpin_bvc


def test_vpin_bvc_detects_real_gold_directional_sweep_against_calm_background():
    """Real GC bars have noisy background (+/-$0.5); a violent directional burst must elevate VPIN >= 55%."""
    candles = []
    # 50 calm choppy background bars with realistic variance
    p = 4150.0
    for i in range(50):
        dp = 0.55 if (i % 2 == 0) else -0.50
        candles.append({
            "open": p,
            "high": p + 0.8,
            "low": p - 0.8,
            "close": p + dp,
            "volume": 120,
        })
        p += dp

    calm_res = compute_vpin_bvc(candles)
    assert calm_res["vpin_pct"] < 45.0, f"Expected calm VPIN < 45%, got {calm_res['vpin_pct']}"

    # Followed by a violent 10-bar institutional dump with varying bar sizes (previously trapped by self-std!)
    drops = [-2.2, -3.5, -1.8, -4.1, -2.9, -3.3, -2.0, -3.8, -2.6, -3.1]
    for dp in drops:
        candles.append({
            "open": p,
            "high": p + 0.3,
            "low": p + dp - 0.3,
            "close": p + dp,
            "volume": 380,
        })
        p += dp

    sweep_res = compute_vpin_bvc(candles)
    assert sweep_res["vpin_pct"] >= 65.0, (
        f"Real-style variable crash sweep must score >= 65% toxic VPIN, got {sweep_res['vpin_pct']}"
    )
    assert sweep_res["vpin_regime"] == "TOXIC_INFORMED_FLOW"


def test_precompute_squeeze_ladder_enforces_outside_wick_and_min_5_sl():
    """Breakout triggers must clear stop-hunt wicks (>= k + 2.80) with SL >= $5.00 behind strike."""
    from src.quant_engine.strategy import precompute_squeeze_ladder

    rows = []
    for k in range(3940, 3985, 5):
        oi = 2500 if k in (3940, 3950, 3975, 3980) else 250
        rows.append({
            "strike": float(k),
            "callOI": oi,
            "putOI": oi,
            "callGEX": -40.0,
            "putGEX": 10.0,
            "netGEX": -30.0,
        })
    df = pd.DataFrame(rows)
    ladder = precompute_squeeze_ladder(df["strike"].values)
    lvl = ladder[3950.0]

    assert lvl.squeeze_trigger >= 3952.80, f"Squeeze trigger too tight inside wick: {lvl.squeeze_trigger}"
    assert (lvl.squeeze_trigger - lvl.squeeze_sl) >= 5.00, "Squeeze SL too tight (< $5.00)"
    assert lvl.squeeze_sl <= 3948.00, f"Squeeze SL must sit safely behind strike: {lvl.squeeze_sl}"
    assert lvl.waterfall_trigger <= 3947.20, f"Waterfall trigger too tight inside wick: {lvl.waterfall_trigger}"
    assert (lvl.waterfall_sl - lvl.waterfall_trigger) >= 5.00, "Waterfall SL too tight (< $5.00)"
    assert lvl.waterfall_sl >= 3952.00, f"Waterfall SL must sit safely behind strike: {lvl.waterfall_sl}"


def test_tactical_intraday_matrix_geometry_and_regime_gating():
    """Verify Entry/SL/TP calibration and structural gating tags across Long/Short Gamma."""
    from src.quant_engine.strategy import compute_tactical_intraday_matrix

    # 1. Long Gamma calm session: Mean Reversion (Fade + Rebound) active; Breakouts gated
    lg = compute_tactical_intraday_matrix(
        spot=4152.5,
        strike_above=4155.0,
        next_above=4160.0,
        strike_below=4150.0,
        next_below=4145.0,
        step=5.0,
        call_wall=4180.0,
        put_wall=4140.0,
        zero_gamma=4145.0,
        major_up_wall=4180.0,
        major_down_wall=4140.0,
        has_up_air_pocket=False,
        has_down_air_pocket=False,
        regime="LONG_GAMMA",
        vpin_pct=31.0,
        call_wall_siege=0.05,
        put_wall_siege=0.05,
        session_tag="NY_COMEX_DEEP",
        atr_5m=4.0,
    )

    sq = lg["squeeze"]
    fd = lg["fade"]
    rb = lg["rebound"]
    bd = lg["breakdown"]

    assert sq["entry"] >= 4155.0 + 2.80
    assert sq["sl_dist"] >= 5.00
    assert sq["tp"] <= round(sq["entry"] + 1.5 * sq["sl_dist"] + 1e-6, 2)
    assert sq["active"] is False

    assert fd["entry"] == 4154.00
    assert fd["sl_dist"] >= 5.00
    assert fd["active"] is True

    assert rb["entry"] == 4151.00
    assert rb["sl_dist"] >= 5.00
    assert rb["active"] is True

    assert bd["entry"] <= 4150.0 - 2.80
    assert bd["sl_dist"] >= 5.00
    assert bd["active"] is False

    # 2. Short Gamma below Zero Gamma with Down Pocket + elevated VPIN, unanchored minor Rebound:
    #    Breakdown unlocks; Fade & unanchored minor Rebound stay locked!
    sg_crash = compute_tactical_intraday_matrix(
        spot=4147.0,
        strike_above=4150.0,
        next_above=4155.0,
        strike_below=4145.0,
        next_below=4140.0,
        step=5.0,
        call_wall=4180.0,
        put_wall=4120.0,  # far away!
        zero_gamma=4160.0,
        major_up_wall=4180.0,
        major_down_wall=4120.0,
        has_up_air_pocket=False,
        has_down_air_pocket=True,
        regime="SHORT_GAMMA",
        vpin_pct=52.0,
        call_wall_siege=0.05,
        put_wall_siege=0.28,
        session_tag="LONDON_DEEP",
        atr_5m=4.0,
    )
    assert sg_crash["breakdown"]["active"] is True
    assert sg_crash["fade"]["active"] is False
    assert sg_crash["rebound"]["active"] is False


def test_html_dashboard_renders_calibrated_k6_with_status_gates():
    """KHỐI 6 must display structural gating tags while keeping all 4 core strategy labels."""
    from src.hud.html_dashboard import generate_html_terminal

    rows = []
    for k in range(4130, 4195, 5):
        c_oi = 5000 if k == 4180 else 400
        p_oi = 4800 if k == 4140 else 350
        rows.append({
            "strike": float(k),
            "callOpenInterest": c_oi,
            "putOpenInterest": p_oi,
            "callOI": c_oi,
            "putOI": p_oi,
            "callVolume": 300,
            "putVolume": 200,
            "callGEX": 120.0,
            "putGEX": -20.0,
            "netGEX": 100.0,
            "netVEX": 10.0,
            "netCHEX": -2.0,
            "totalTheta": -15.0,
            "totalVega": 5.0,
            "callIV": 0.18,
            "putIV": 0.19,
            "callDelta": 0.5,
            "callGamma": 0.0005,
            "callMid": 12.0,
            "putMid": 11.0,
        })
    df = pd.DataFrame(rows)
    meta = {
        "spot_price": 4152.5,
        "atm_strike": 4155.0,
        "atm_straddle": 23.0,
        "regime": "LONG GAMMA (VOLATILITY SUPPRESSION / MEAN REVERSION)",
        "total_net_gex": 1200.0,
        "total_net_vex": 100.0,
        "total_net_chex": -12.0,
        "expected_move_1s": 25.0,
        "rule16_daily_move": 18.0,
        "call_wall": 4180.0,
        "call_wall_oi": 5000,
        "put_wall": 4140.0,
        "put_wall_oi": 4800,
        "zero_gamma_flip": 4145.0,
        "dte_days": 8.0,
        "basis": 0.0,
        "basis_spread": 0.0,
        "basis_source": "CME_ONLY",
        "institutional_orderflow": {"vpin_pct": 31.0, "session_tag": "NY_COMEX_DEEP"},
        "squeeze_ladder": {},
    }
    import plotly.graph_objects as go
    fig = go.Figure()
    fig.add_trace(go.Bar(x=[4140, 4155, 4180], y=[10, 20, 30]))
    html = generate_html_terminal(df, meta, fig)
    for label in ("BUY MUA ĐUỔI", "SELL CHẶN TIỀN TUYẾN", "BUY BẮT SÀN ATM", "SELL THỦNG SÀN"):
        assert label in html
    assert "[KÍCH HOẠT]" in html
    assert "[CHỜ XÁC NHẬN]" in html
