"""Unit tests for ADR-026 Dynamic Liquidity Vacuum, Institutional FVG & Post-Sweep Classifier."""
from __future__ import annotations

import pandas as pd

from src.quant_engine.dealer import (
    classify_post_sweep_execution,
    compute_dynamic_liquidity_vacuum,
    compute_rogers_satchell_bar,
    detect_institutional_fvgs,
    reconstruct_institutional_orderflow,
)


def _make_calm_bars(n: int = 35, base_price: float = 4000.0, start_ts: int = 1_760_000_000) -> list[dict]:
    """Generate steady, balanced OHLCV candles with modest volatility and volume."""
    bars = []
    p = base_price
    for i in range(n):
        step = 0.25 if i % 2 == 0 else -0.20
        o = round(p, 2)
        c = round(p + step, 2)
        h = round(max(o, c) + 0.40, 2)
        l = round(min(o, c) - 0.40, 2)
        bars.append({
            "time": start_ts + i * 60,
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "volume": 280 + (i % 5) * 20,
        })
        p = c
    return bars


def test_rogers_satchell_handles_directional_cascade_and_bad_bars():
    """Rogers-Satchell captures non-zero drift cascades and guards invalid prices."""
    rs_bad = compute_rogers_satchell_bar(0.0, 4000.0, 3990.0, 3995.0)
    assert rs_bad == 0.0

    rs_trend = compute_rogers_satchell_bar(4000.0, 4022.0, 3999.0, 4020.0)
    assert rs_trend > 0.001


def test_dynamic_vacuum_ignores_zero_volume_and_asian_thin_session():
    """Zero-volume bars must not divide by zero, and ASIAN_THIN must not trigger false vacuums."""
    bars = _make_calm_bars(35, base_price=4000.0)
    # Inject a zero-volume gap bar then a thin Asian low-volume spike
    bars.append({"time": 1_760_003_000, "open": 4001.0, "high": 4001.0, "low": 4001.0, "close": 4001.0, "volume": 0})
    bars.append({"time": 1_760_003_060, "open": 4001.0, "high": 4018.0, "low": 4000.5, "close": 4017.5, "volume": 25})

    res = compute_dynamic_liquidity_vacuum(bars, session_tag="ASIAN_THIN")
    assert res["vacuum_active"] is False
    assert res["regime"] == "THIN_SESSION_GUARDED"
    assert isinstance(res["illiq_latest"], float)
    assert res["rs_z_score"] == res["rs_z_score"]  # Not NaN


def test_dynamic_vacuum_triggers_on_deep_session_illiq_and_rs_outlier():
    """Simultaneous Amihud ILLIQ >= Q95 + Rogers-Satchell >= mu + 2*sigma triggers in deep session."""
    bars = _make_calm_bars(40, base_price=4000.0)
    last_close = bars[-1]["close"]
    # High price move per contract (high ILLIQ) + large RS directional range in deep session
    bars.append({
        "time": bars[-1]["time"] + 60,
        "open": last_close,
        "high": last_close + 16.5,
        "low": last_close - 0.5,
        "close": last_close + 15.8,
        "volume": 95,
    })

    res = compute_dynamic_liquidity_vacuum(bars, session_tag="NY_COMEX_DEEP")
    assert res["vacuum_active"] is True
    assert res["regime"] == "DYNAMIC_LIQUIDITY_VACUUM"
    assert res["rs_z_score"] >= 2.0
    assert res["illiq_percentile"] >= 95.0
    assert bars[-1]["time"] in res["vacuum_bar_times"]


def test_institutional_fvg_filters_unbacked_asian_gaps_and_keeps_vacuum_or_wall_fvgs():
    """Random unbacked FVG in ASIAN_THIN is filtered; vacuum-backed FVG at Wall is retained."""
    # Unbacked Asian gap between bar0.high=4001 and bar2.low=4004
    asian_bars = [
        {"time": 100, "open": 4000.0, "high": 4001.0, "low": 3999.5, "close": 4000.5, "volume": 15},
        {"time": 160, "open": 4000.5, "high": 4005.0, "low": 4000.5, "close": 4004.5, "volume": 12},
        {"time": 220, "open": 4004.5, "high": 4006.0, "low": 4004.0, "close": 4005.5, "volume": 18},
    ]
    rejected = detect_institutional_fvgs(
        asian_bars,
        vacuum_bar_times=set(),
        structural_levels=[4100.0, 3900.0],
        air_pockets=[],
        session_tag="ASIAN_THIN",
    )
    assert rejected == []

    # Institutional Bullish FVG backed by vacuum_bar_times AND Put Wall at 4002
    deep_bars = [
        {"time": 1000, "open": 4000.0, "high": 4001.5, "low": 3999.0, "close": 4001.0, "volume": 200},
        {"time": 1060, "open": 4001.0, "high": 4012.0, "low": 4001.0, "close": 4011.5, "volume": 110},
        {"time": 1120, "open": 4011.5, "high": 4013.5, "low": 4008.5, "close": 4013.0, "volume": 240},
    ]
    kept = detect_institutional_fvgs(
        deep_bars,
        vacuum_bar_times={1060},
        structural_levels=[4002.0],
        air_pockets=[],
        session_tag="NY_COMEX_DEEP",
    )
    assert len(kept) == 1
    fvg = kept[0]
    assert fvg["direction"] == "BULLISH"
    assert fvg["low"] == 4001.5
    assert fvg["high"] == 4008.5
    assert fvg["midpoint_50"] == 4005.0
    assert fvg["zone_75"] == 4003.25
    assert fvg["vacuum_backed"] is True


def test_post_sweep_vpin_blocks_contrarian_entries_and_classifies_vshape_vs_pullback():
    """VPIN >= 65% must block reversals; VPIN < 65% cleanly distinguishes V-Shape vs Pullback."""
    bars = _make_calm_bars(25, base_price=4005.0)
    # Sweep below Put Wall 4000 -> absorption pinbar -> strong V-Shape bounce breaking high
    t0 = bars[-1]["time"]
    bars.append({"time": t0 + 60, "open": 4002.0, "high": 4002.5, "low": 3997.0, "close": 4001.8, "volume": 480})
    bars.append({"time": t0 + 120, "open": 4001.8, "high": 4009.5, "low": 4001.5, "close": 4009.0, "volume": 90})

    # 1. Toxic VPIN lock (>= 65%)
    blocked = classify_post_sweep_execution(
        candles=bars,
        spot_price=4002.0,
        call_wall=4100.0,
        put_wall=4000.0,
        vpin_pct=72.0,
        kyle_regime="ICEBERG_ABSORPTION",
        parity_z_score=2.1,
        vrp_spread_pct=5.0,
        session_tag="NY_COMEX_DEEP",
    )
    assert blocked["allow_reversal"] is False
    assert blocked["post_sweep_regime"] == "TOXIC_CASCADE_BLOCKED"

    # 2. Safe VPIN (< 65%) + break of absorption high + high reversal lambda + NY deep -> V-Shape
    vshape = classify_post_sweep_execution(
        candles=bars,
        spot_price=4009.0,
        call_wall=4100.0,
        put_wall=4000.0,
        vpin_pct=34.0,
        kyle_regime="PREDATORY_SWEEP_EXHAUSTION",
        parity_z_score=1.8,
        vrp_spread_pct=4.5,
        session_tag="NY_COMEX_DEEP",
    )
    assert vshape["allow_reversal"] is True
    assert vshape["post_sweep_regime"] == "POST_SWEEP_V_SHAPE"
    assert vshape["direction"] == "BULLISH"

    # 3. Safe VPIN + absorption near wall + calm follow-through + active FVG -> Pullback 50-75%
    calm_pullback_bars = _make_calm_bars(25, base_price=4002.0)
    tp0 = calm_pullback_bars[-1]["time"]
    calm_pullback_bars.append({"time": tp0 + 60, "open": 4001.0, "high": 4002.5, "low": 3998.5, "close": 4001.5, "volume": 450})
    calm_pullback_bars.append({"time": tp0 + 120, "open": 4001.5, "high": 4002.2, "low": 4001.2, "close": 4002.0, "volume": 320})
    fvgs = [{
        "direction": "BULLISH",
        "low": 4000.0,
        "high": 4004.0,
        "midpoint_50": 4002.0,
        "zone_75": 4001.0,
        "vacuum_backed": True,
    }]
    pullback = classify_post_sweep_execution(
        candles=calm_pullback_bars,
        spot_price=4002.0,
        call_wall=4100.0,
        put_wall=4000.0,
        vpin_pct=30.0,
        kyle_regime="ICEBERG_ABSORPTION",
        parity_z_score=0.5,
        vrp_spread_pct=1.0,
        active_fvgs=fvgs,
        session_tag="LONDON_DEEP",
    )
    assert pullback["allow_reversal"] is True
    assert pullback["post_sweep_regime"] == "POST_SWEEP_PULLBACK"
    assert pullback["target_zone"] == [4001.0, 4002.0]


def test_reconstruct_institutional_orderflow_exposes_adr026_fields():
    """reconstruct_institutional_orderflow returns dynamic_vacuum, institutional_fvgs, and post_sweep_execution."""
    df = pd.DataFrame([
        {
            "strike": 4050.0,
            "callBid": 32.0,
            "callAsk": 34.0,
            "putBid": 12.0,
            "putAsk": 14.0,
            "callVolume": 100,
            "putVolume": 40,
            "callOpenInterest": 500,
            "putOpenInterest": 300,
            "callDelta": 0.65,
            "putDelta": -0.35,
        },
        {
            "strike": 4100.0,
            "callBid": 10.0,
            "callAsk": 12.0,
            "putBid": 38.0,
            "putAsk": 40.0,
            "callVolume": 80,
            "putVolume": 90,
            "callOpenInterest": 1200,
            "putOpenInterest": 400,
            "callDelta": 0.35,
            "putDelta": -0.65,
        },
    ])
    bars = _make_calm_bars(30, base_price=4070.0)
    res = reconstruct_institutional_orderflow(
        df,
        spot_price=4070.0,
        m5_tape={"chart_candles": bars},
        call_wall=4100.0,
        put_wall=4050.0,
        vrp_spread_pct=2.0,
        session_tag="NY_COMEX_DEEP",
    )
    assert "dynamic_vacuum" in res
    assert "institutional_fvgs" in res
    assert "post_sweep_execution" in res

