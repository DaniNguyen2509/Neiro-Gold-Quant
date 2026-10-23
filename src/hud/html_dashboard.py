"""Neiro-Quant Tactical HTML Dashboard Generator.

Generates a standalone, production-grade Plotly interactive dark-mode terminal for
CME Gold Options (GCZ26 / COMEX Futures) incorporating:
- 100% Pure CME Gold Futures Real-time Positioning (No MT5 clutter)
- Instant Action Command Banner (Glanceable 3-second decision UI)
- Visual Level Spine (Market Maker distance map)
- 6-Scenario Real-time Dynamic Matrix (Auto-activated by live price)
- Compact Plotly GEX & Greeks Charts
- Tactical Scalping & Structural Swing Strategy Tables
- Pocket Glossary (1-line definitions, Vietnamese with accents, zero icons)
"""
from __future__ import annotations

import argparse
import datetime
import gc
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.quant_engine.synthetic import compute_dynamic_dte
from src.quant_engine import basis as basis_engine
from src.quant_engine.basis import (
    fetch_live_cme_futures_price,
    fetch_live_cme_m5_tape,
    resolve_dynamic_basis,
    resolve_dynamic_basis_with_source,
)
from src.quant_engine.institutional import (
    extract_rr_bf,
    size_xauusd,
    detect_cta_confluence,
)
from src.quant_engine.level_state import (
    LevelState,
    evaluate_tactical_level_states,
    find_next_major_wall,
    detect_strike_air_pockets,
)
from src.quant_engine.scenario_engine import (
    AlertLevel,
    ActionDirective,
    evaluate_market_scenarios,
)
from src.quant_engine.dealer import (
    compute_exact_gamma_flip,
    compute_wall_siege_ratio,
    find_gamma_weighted_walls,
    classify_wall_regime,
)
from src.quant_engine.loader import to_options_snapshot, load_multi_expiry_options


def clean_val(v: Any, default: float = 0.0) -> float:
    if v is None:
        return default
    if isinstance(v, (int, float)):
        return default if (math.isnan(v) or math.isinf(v)) else float(v)
    s = str(v).strip().replace('"', '').replace("'", "").replace("$", "")
    for ch in ("=", "+"):
        if s.startswith(ch):
            s = s[1:].strip()
    if s.endswith(("%", "s", "S")):
        s = s[:-1].strip()
    s = s.replace(",", "").replace(" ", "")
    try:
        return float(s)
    except Exception:
        return default


def load_and_preprocess_options(
    csv_path: str,
    basis: float | None = None,
    no_mt5: bool = False,
) -> tuple[pd.DataFrame, dict[str, Any]]:

    p_path = Path(csv_path)
    if p_path.exists():
        data_parent = str(p_path.parent)
        df_multi = load_multi_expiry_options(data_parent)
        if hasattr(df_multi, "attrs") and df_multi.attrs.get("is_aggregated"):
            df_raw = df_multi
        else:
            df_raw = pd.read_csv(csv_path)
    else:
        df_raw = pd.read_csv(csv_path)

    # Normalize column names
    col_clean = {c: c.strip() for c in df_raw.columns}
    df_raw.rename(columns=col_clean, inplace=True)

    # Standardize expected columns
    for col in [
        "callMid", "callBid", "callAsk", "callLatest", "callVolume", "callOpenInterest", "callGamma", "callIV",
        "putMid", "putBid", "putAsk", "putLatest", "putVolume", "putOpenInterest", "putGamma", "putIV"
    ]:
        if col not in df_raw.columns:
            df_raw[col] = 0.0
        else:
            df_raw[col] = df_raw[col].apply(clean_val)

    df_raw["strike"] = df_raw["strike"].apply(clean_val)
    df = df_raw[df_raw["strike"] > 0].sort_values("strike").reset_index(drop=True)

    # Fallback fill for mid prices
    mask_c_mid = (df["callMid"] <= 0) & (df["callBid"] > 0) & (df["callAsk"] > 0)
    df.loc[mask_c_mid, "callMid"] = (df.loc[mask_c_mid, "callBid"] + df.loc[mask_c_mid, "callAsk"]) / 2.0

    mask_p_mid = (df["putMid"] <= 0) & (df["putBid"] > 0) & (df["putAsk"] > 0)
    df.loc[mask_p_mid, "putMid"] = (df.loc[mask_p_mid, "putBid"] + df.loc[mask_p_mid, "putAsk"]) / 2.0

    # Expiry and DTE
    exp_val = ""
    if "expirationDate" in df.columns:
        s_exp = df["expirationDate"].dropna()
        if not s_exp.empty:
            exp_val = str(s_exp.iloc[0]).strip()
    if not exp_val and hasattr(df, "attrs") and df.attrs.get("expiration_date"):
        exp_val = str(df.attrs["expiration_date"]).strip()

    if not exp_val:
        exp_val = "2026-10-27"

    dte_days = compute_dynamic_dte(exp_val, default_dte=8.0)
    T_years = max(dte_days / 365.0, 1.0 / 365.0)
    r = 0.045

    # 1. CME Futures Price Resolution & ATM Strike Lock
    live_futures = basis_engine.fetch_live_cme_futures_price()
    if live_futures is not None and live_futures > 500.0:
        spot_price = live_futures
        futures_feed = "LIVE COMEX (GC=F)"
        # Dynamically lock ATM strike directly to the live futures price
        atm_idx = (df["strike"] - spot_price).abs().idxmin()
        atm_strike = float(df.loc[atm_idx, "strike"])
        c_mid_atm = float(df.loc[atm_idx, "callMid"]) if float(df.loc[atm_idx, "callMid"]) > 0 else 25.0
        p_mid_atm = float(df.loc[atm_idx, "putMid"]) if float(df.loc[atm_idx, "putMid"]) > 0 else 25.0
    else:
        # Fallback to liquid strike
        total_interest = df["callOpenInterest"] + df["putOpenInterest"] + df["callVolume"] + df["putVolume"]
        liquid_threshold = np.percentile(total_interest[total_interest > 0], 50) if (total_interest > 0).any() else 0
        candidate_mask = (total_interest >= liquid_threshold) & (df["callMid"] > 0) & (df["putMid"] > 0)
        if candidate_mask.any():
            diff = (df.loc[candidate_mask, "callMid"] - df.loc[candidate_mask, "putMid"]).abs()
            atm_idx = diff.idxmin()
        else:
            diff = (df["callMid"] - df["putMid"]).abs()
            atm_idx = diff.idxmin()

        atm_strike = float(df.loc[atm_idx, "strike"])
        c_mid_atm = float(df.loc[atm_idx, "callMid"])
        p_mid_atm = float(df.loc[atm_idx, "putMid"])
        spot_price = atm_strike + math.exp(r * T_years) * (c_mid_atm - p_mid_atm)
        if spot_price <= 0 or math.isnan(spot_price):
            spot_price = atm_strike
        futures_feed = "ATM STRIKE SYNTHESIS"

    # 2. Greeks via Black-76 & Volatility Model
    MULT = 100.0
    scale = (spot_price ** 2) * 0.01 / 1e6
    # Calibrate ATM Implied Volatility:
    # 1. Prefer real observed market IVs from COMEX if present in options chain
    valid_c_iv = df["callIV"][(df["callIV"] > 0.05) & (df["callIV"] < 0.80)] if "callIV" in df.columns else pd.Series(dtype=float)
    valid_p_iv = df["putIV"][(df["putIV"] > 0.05) & (df["putIV"] < 0.80)] if "putIV" in df.columns else pd.Series(dtype=float)
    all_valid_iv = pd.concat([valid_c_iv, valid_p_iv])

    c_iv_atm = float(df.loc[atm_idx, "callIV"]) if ("callIV" in df.columns and atm_idx in df.index) else 0.0
    p_iv_atm = float(df.loc[atm_idx, "putIV"]) if ("putIV" in df.columns and atm_idx in df.index) else 0.0

    if c_iv_atm > 0.05 and p_iv_atm > 0.05:
        sigma_atm = float((c_iv_atm + p_iv_atm) / 2.0)
    elif c_iv_atm > 0.05:
        sigma_atm = float(c_iv_atm)
    elif p_iv_atm > 0.05:
        sigma_atm = float(p_iv_atm)
    elif not all_valid_iv.empty:
        sigma_atm = float(all_valid_iv.median())
    else:
        # Fallback: Time-value synthetic straddle (subtract intrinsic to prevent artificial inflation)
        intrinsic_c = max(0.0, spot_price - atm_strike)
        intrinsic_p = max(0.0, atm_strike - spot_price)
        tv_c = max(1.0, c_mid_atm - intrinsic_c)
        tv_p = max(1.0, p_mid_atm - intrinsic_p)
        pure_straddle = tv_c + tv_p
        sigma_atm = float(np.clip(pure_straddle / (0.7979 * spot_price * np.sqrt(T_years)), 0.08, 0.45))

    atm_straddle = float(sigma_atm * 0.7979 * spot_price * np.sqrt(T_years))
    expected_move_1s = atm_straddle / 0.7979
    rule16_daily_move = (sigma_atm / 16.0) * spot_price

    strikes_all = df["strike"].values.astype(float)
    denom = sigma_atm * np.sqrt(T_years)
    d1 = (np.log(np.maximum(1e-4, spot_price / strikes_all)) + 0.5 * (sigma_atm ** 2) * T_years) / denom
    d2 = d1 - denom
    pdf_d1 = (1.0 / np.sqrt(2.0 * np.pi)) * np.exp(-0.5 * (d1 ** 2))
    cdf_d1 = 0.5 * (1.0 + np.vectorize(math.erf)(d1 / np.sqrt(2.0)))
    df_disc = np.exp(-r * T_years)

    # Black-76 Gamma: e^(-rT) * n(d1) / (F * sigma * sqrt(T))
    gamma_b76 = (df_disc * pdf_d1) / np.maximum(1e-4, spot_price * denom)
    gamma_c = np.where(df["callGamma"] > 0, df["callGamma"], gamma_b76)
    gamma_p = np.where(df["putGamma"] > 0, df["putGamma"], gamma_b76)

    # 3. GEX Calculation ($M / 1% move)
    df["callGEX"] = gamma_c * df["callOpenInterest"] * MULT * scale
    df["putGEX"] = - (gamma_p * df["putOpenInterest"] * MULT * scale)
    df["netGEX"] = df["callGEX"] + df["putGEX"]

    vanna = - df_disc * pdf_d1 * (d2 / sigma_atm)
    charm_call = - df_disc * (pdf_d1 * (r / denom - d2 / (2.0 * T_years)) - r * cdf_d1)
    charm_put = charm_call - r * df_disc

    df["callVEX"] = vanna * df["callOpenInterest"] * MULT * spot_price * 0.01 / 1e6
    df["putVEX"] = - (vanna * df["putOpenInterest"] * MULT * spot_price * 0.01 / 1e6)
    df["netVEX"] = df["callVEX"] + df["putVEX"]

    df["callCHEX"] = (charm_call / 365.0) * df["callOpenInterest"] * MULT * spot_price / 1e6
    df["putCHEX"] = - ((charm_put / 365.0) * df["putOpenInterest"] * MULT * spot_price / 1e6)
    df["netCHEX"] = df["callCHEX"] + df["putCHEX"]

    # 4. Deltas & Dealer Net Position Delta (Contracts & DEX)
    df["callDelta"] = df_disc * cdf_d1
    df["putDelta"] = df["callDelta"] - df_disc
    df["callDeltaContracts"] = np.round(df["callOpenInterest"] * df["callDelta"], 1)
    df["putDeltaContracts"] = np.round(df["putOpenInterest"] * df["putDelta"], 1)
    df["netDeltaContracts"] = np.round(df["callDeltaContracts"] + df["putDeltaContracts"], 1)
    df["netDEX"] = df["netDeltaContracts"] * MULT * spot_price / 1e6

    total_net_delta_contracts = float(df["netDeltaContracts"].sum())
    total_net_dex = float(df["netDEX"].sum())

    if not df.empty and (df["netDeltaContracts"].abs().max() > 0):
        max_tilt_row = df.loc[df["netDeltaContracts"].abs().idxmax()]
        max_tilt_strike = float(max_tilt_row["strike"])
        max_tilt_contracts = float(max_tilt_row["netDeltaContracts"])
    else:
        max_tilt_strike = float(atm_strike)
        max_tilt_contracts = 0.0

    if total_net_delta_contracts > 200.0:
        delta_tilt_regime = "BULLISH_CALL_TILT"
        delta_tilt_label = "NGHIÊNG CALL (BULLISH)"
        delta_tilt_color = "#22C55E"
    elif total_net_delta_contracts < -200.0:
        delta_tilt_regime = "BEARISH_PUT_TILT"
        delta_tilt_label = "NGHIÊNG PUT (BEARISH)"
        delta_tilt_color = "#EF4444"
    else:
        delta_tilt_regime = "NEUTRAL"
        delta_tilt_label = "CÂN BẰNG (DELTA NEUTRAL)"
        delta_tilt_color = "#FACC15"

    # 5. Structural Walls & Regime: Gamma-Weighted vs Raw OI
    call_walls_gamma, put_walls_gamma = find_gamma_weighted_walls(
        df, top_n=2, spot_price=spot_price, r=r, dte_days=dte_days, default_iv=sigma_atm
    )
    raw_calls_otm = df[df["strike"] > spot_price]
    if raw_calls_otm.empty or raw_calls_otm["callOpenInterest"].max() <= 0:
        raw_calls_otm = df[df["strike"] >= spot_price]
    raw_call_row = raw_calls_otm.loc[raw_calls_otm["callOpenInterest"].idxmax()] if not raw_calls_otm.empty and raw_calls_otm["callOpenInterest"].max() > 0 else df.loc[df["callOpenInterest"].idxmax()]

    raw_puts_otm = df[df["strike"] < spot_price]
    if raw_puts_otm.empty or raw_puts_otm["putOpenInterest"].max() <= 0:
        raw_puts_otm = df[df["strike"] <= spot_price]
    raw_put_row = raw_puts_otm.loc[raw_puts_otm["putOpenInterest"].idxmax()] if not raw_puts_otm.empty and raw_puts_otm["putOpenInterest"].max() > 0 else df.loc[df["putOpenInterest"].idxmax()]
    raw_call_wall_strike = float(raw_call_row["strike"])
    raw_call_wall_oi = int(raw_call_row["callOpenInterest"])
    raw_put_wall_strike = float(raw_put_row["strike"])
    raw_put_wall_oi = int(raw_put_row["putOpenInterest"])

    if call_walls_gamma:
        call_wall = float(call_walls_gamma[0].strike)
        call_wall_oi = int(call_walls_gamma[0].oi)
        call_wall_power = float(call_walls_gamma[0].gamma_power)
        call_wall_regime = call_walls_gamma[0].regime
    else:
        call_wall = raw_call_wall_strike
        call_wall_oi = raw_call_wall_oi
        call_wall_power = 0.0
        call_wall_regime = "NEUTRAL"

    if put_walls_gamma:
        put_wall = float(put_walls_gamma[0].strike)
        put_wall_oi = int(put_walls_gamma[0].oi)
        put_wall_power = float(put_walls_gamma[0].gamma_power)
        put_wall_regime = put_walls_gamma[0].regime
    else:
        put_wall = raw_put_wall_strike
        put_wall_oi = raw_put_wall_oi
        put_wall_power = 0.0
        put_wall_regime = "NEUTRAL"

    total_net_gex = float(df["netGEX"].sum())
    total_net_vex = float(df["netVEX"].sum())
    total_net_chex = float(df["netCHEX"].sum())
    regime = "LONG_GAMMA" if total_net_gex > 10.0 else ("SHORT_GAMMA" if total_net_gex < -10.0 else "NEUTRAL")

    squeeze_trigger = call_wall + 2.50
    waterfall_trigger = put_wall - 2.50

    basis_source = "CME_ONLY"
    if no_mt5:
        basis = 0.0
        basis_source = "CME_ONLY"
    elif basis is None:
        basis, src_tag = resolve_dynamic_basis_with_source(spot_price, fallback_basis=-24.0)
        basis_source = f"{src_tag} CONTANGO" if "CALIBRATED" in src_tag else src_tag
    elif basis > 0:
        basis = -basis
        basis_source = "MANUAL"
    else:
        basis_source = "MANUAL"

    # 6. Institutional Skew & CTA Confluence
    skew_metrics = extract_rr_bf(df, atm_strike=atm_strike)
    cta_conf = detect_cta_confluence(
        spot=spot_price,
        call_wall=call_wall,
        put_wall=put_wall,
        daily_move_1s=rule16_daily_move,
    )

    # 7. Real-Time M5 Orderflow Tape & Volume Pulse
    m5_tape = fetch_live_cme_m5_tape(limit=8)

    call_wall_matches = df.loc[df["strike"] == call_wall, "callVolume"]
    put_wall_matches = df.loc[df["strike"] == put_wall, "putVolume"]
    call_wall_vol = int(call_wall_matches.iloc[0]) if not call_wall_matches.empty else 0
    put_wall_vol = int(put_wall_matches.iloc[0]) if not put_wall_matches.empty else 0
    call_wall_siege = compute_wall_siege_ratio(call_wall_vol, call_wall_oi)
    put_wall_siege = compute_wall_siege_ratio(put_wall_vol, put_wall_oi)

    snap = to_options_snapshot(df)
    exact_gamma_flip = compute_exact_gamma_flip(
        snap, spot_price=spot_price, r=r, dte_days=dte_days, default_iv=sigma_atm
    )

    meta = {
        "spot_price": spot_price,
        "futures_feed": futures_feed,
        "m5_tape": m5_tape,
        "atm_strike": atm_strike,
        "atm_straddle": atm_straddle,
        "sigma_atm": sigma_atm,
        "expected_move_1s": expected_move_1s,
        "rule16_daily_move": rule16_daily_move,
        "call_wall": call_wall,
        "call_wall_oi": call_wall_oi,
        "call_wall_siege": call_wall_siege,
        "call_wall_power": call_wall_power,
        "call_wall_regime": call_wall_regime,
        "raw_call_wall_strike": raw_call_wall_strike,
        "raw_call_wall_oi": raw_call_wall_oi,
        "put_wall": put_wall,
        "put_wall_oi": put_wall_oi,
        "put_wall_siege": put_wall_siege,
        "put_wall_power": put_wall_power,
        "put_wall_regime": put_wall_regime,
        "raw_put_wall_strike": raw_put_wall_strike,
        "raw_put_wall_oi": raw_put_wall_oi,
        "total_net_gex": total_net_gex,
        "total_net_vex": total_net_vex,
        "total_net_chex": total_net_chex,
        "regime": regime,
        "squeeze_trigger": squeeze_trigger,
        "waterfall_trigger": waterfall_trigger,
        "zero_gamma_flip": exact_gamma_flip,
        "basis": basis,
        "basis_source": basis_source,
        "no_mt5": no_mt5,
        "dte_days": dte_days,
        "expiration_date": f"OGX26 ({exp_val})" if exp_val else "OGX26 (2026-10-27)",
        "skew_rr25": skew_metrics.rr25,
        "skew_bf25": skew_metrics.bf25,
        "skew_regime": skew_metrics.regime.value,
        "skew_label": skew_metrics.label_vi,
        "skew_bias_pct": skew_metrics.bias_pct,
        "cta_h20": cta_conf.h20,
        "cta_l20": cta_conf.l20,
        "cta_badge": cta_conf.confluence_badge,
        "cta_desc": cta_conf.confluence_desc,
        "total_net_delta_contracts": total_net_delta_contracts,
        "total_net_dex": total_net_dex,
        "max_tilt_strike": max_tilt_strike,
        "max_tilt_contracts": max_tilt_contracts,
        "delta_tilt_regime": delta_tilt_regime,
        "delta_tilt_label": delta_tilt_label,
        "delta_tilt_color": delta_tilt_color,
    }
    return df, meta


def build_plotly_figure(df_full: pd.DataFrame, meta: dict[str, Any]) -> go.Figure:
    spot_price = meta["spot_price"]
    atm_strike = meta["atm_strike"]
    call_wall = meta["call_wall"]
    put_wall = meta["put_wall"]

    atm_idx = int((df_full["strike"] - atm_strike).abs().idxmin())

    # Focus on active tactical trading zone: Put Wall buffer to Call Wall buffer
    put_wall_idx = int((df_full["strike"] - put_wall).abs().idxmin())
    call_wall_idx = int((df_full["strike"] - call_wall).abs().idxmin())

    # Bound lower index: 1 strike below Put Wall or at least 2 strikes below ATM
    s_idx = max(0, min(put_wall_idx - 1, atm_idx - 2))

    # Bound upper index: 1 strike above Call Wall or at least 2 strikes above ATM
    e_idx = min(len(df_full), max(call_wall_idx + 2, atm_idx + 3))

    # Safety clamp: if range exceeds 22 strikes, prioritize ATM +/- 10 strikes to keep chart compact & legible
    max_strikes = 22
    if (e_idx - s_idx) > max_strikes:
        s_idx = max(0, atm_idx - 10)
        e_idx = min(len(df_full), atm_idx + 11)

    df = df_full.iloc[s_idx:e_idx].copy().reset_index(drop=True)

    strikes = df["strike"].values
    step = float(np.diff(strikes).min()) if len(strikes) > 1 else 25.0

    # Calculate adaptive bar widths based on local strike spacing
    if len(strikes) > 1:
        diffs = np.zeros_like(strikes)
        diffs[0] = strikes[1] - strikes[0]
        diffs[-1] = strikes[-1] - strikes[-2]
        diffs[1:-1] = np.minimum(strikes[1:-1] - strikes[:-2], strikes[2:] - strikes[1:-1])
        bar_widths = np.clip(diffs * 0.72, 3.5, 18.0)
    else:
        bar_widths = 10.0

    strikes_above = strikes[strikes > spot_price]
    strike_above = float(strikes_above[0]) if len(strikes_above) > 0 else call_wall
    next_above = float(strikes_above[1]) if len(strikes_above) > 1 else strike_above + step

    strikes_below = strikes[strikes <= spot_price]
    strike_below = float(strikes_below[-1]) if len(strikes_below) > 0 else put_wall
    next_below = float(strikes_below[-2]) if len(strikes_below) > 1 else strike_below - step

    if "callDelta" not in df.columns:
        df["callDelta"] = 0.50
    if "putDelta" not in df.columns:
        df["putDelta"] = -0.50
    if "callDeltaContracts" not in df.columns:
        df["callDeltaContracts"] = np.round(df["callOpenInterest"] * df["callDelta"], 1)
    if "putDeltaContracts" not in df.columns:
        df["putDeltaContracts"] = np.round(df["putOpenInterest"] * df["putDelta"], 1)
    if "netDeltaContracts" not in df.columns:
        df["netDeltaContracts"] = np.round(df["callDeltaContracts"] + df["putDeltaContracts"], 1)

    fig = make_subplots(
        rows=1, cols=3,
        shared_yaxes=True,
        horizontal_spacing=0.035,
        subplot_titles=(
            "<b>Panel 1: Net GEX ($M) & Mốc Chiến Thuật (SL/TP)</b>",
            "<b>Panel 2: Volume, OI & Sổ Sách Net Delta (HĐ)</b>",
            "<b>Panel 3: Greeks Bậc 2 (Vanna & Charm)</b>",
        ),
        column_widths=[0.36, 0.36, 0.28],
    )

    # Panel 1: Net GEX
    colors_g = ["#4ADE80" if x >= 0 else "#F87171" for x in df["netGEX"]]
    fig.add_trace(
        go.Bar(
            y=df["strike"], x=df["netGEX"], orientation="h",
            width=bar_widths,
            marker_color=colors_g, name="Net GEX ($M)",
            hovertemplate="Strike: $%{y}<br>Net GEX: $%{x:.2f}M<extra></extra>",
        ),
        row=1, col=1,
    )
    fig.add_vline(x=0, line_dash="solid", line_color="#475569", row=1, col=1)

    # Panel 2: Volume vs OI & Sổ Sách Net Delta
    net_delta_colors = ["#4ADE80" if x >= 0 else "#F87171" for x in df["netDeltaContracts"]]
    net_customdata = np.stack(
        [
            df["callDelta"],
            df["callOpenInterest"],
            df["callDeltaContracts"],
            df["putDelta"],
            df["putOpenInterest"],
            df["putDeltaContracts"],
        ],
        axis=-1,
    )
    fig.add_trace(
        go.Bar(
            y=df["strike"],
            x=df["netDeltaContracts"],
            width=bar_widths,
            orientation="h",
            marker=dict(color=net_delta_colors, opacity=0.45, line=dict(color=net_delta_colors, width=1)),
            name="Net Delta (HĐ GC)",
            hovertemplate=(
                "<b>Strike: $%{y}</b><br>"
                "Call Δ: %{customdata[0]:+.4f} (OI: %{customdata[1]:,} &rarr; %{customdata[2]:+,.1f} HĐ)<br>"
                "Put Δ:  %{customdata[3]:+.4f} (OI: %{customdata[4]:,} &rarr; %{customdata[5]:+,.1f} HĐ)<br>"
                "<b>Net Delta Sổ Sách: %{x:+,.1f} HĐ GC</b><extra></extra>"
            ),
            customdata=net_customdata,
        ),
        row=1, col=2,
    )
    fig.add_trace(
        go.Bar(
            y=df["strike"], x=-df["putVolume"], orientation="h",
            width=bar_widths,
            marker_color="#F87171", opacity=0.75, name="Put Volume",
            hovertemplate="Strike: $%{y}<br>Put Vol: %{customdata:,}<extra></extra>",
            customdata=df["putVolume"],
        ),
        row=1, col=2,
    )
    fig.add_trace(
        go.Bar(
            y=df["strike"], x=df["callVolume"], orientation="h",
            width=bar_widths,
            marker_color="#4ADE80", opacity=0.75, name="Call Volume",
            hovertemplate="Strike: $%{y}<br>Call Vol: %{x:,}<extra></extra>",
        ),
        row=1, col=2,
    )
    fig.add_trace(
        go.Scatter(
            y=df["strike"], x=df["callOpenInterest"], mode="lines+markers",
            line=dict(color="#22C55E", width=2.2),
            marker=dict(size=5, symbol="circle"),
            name="Call OI (Trần)",
            hovertemplate="Strike: $%{y}<br>Call OI: %{x:,}<extra></extra>",
        ),
        row=1, col=2,
    )
    fig.add_trace(
        go.Scatter(
            y=df["strike"], x=-df["putOpenInterest"], mode="lines+markers",
            line=dict(color="#EF4444", width=2.2),
            marker=dict(size=5, symbol="circle"),
            name="Put OI (Sàn)",
            hovertemplate="Strike: $%{y}<br>Put OI: %{customdata:,}<extra></extra>",
            customdata=df["putOpenInterest"],
        ),
        row=1, col=2,
    )
    fig.add_vline(x=0, line_dash="solid", line_color="#475569", row=1, col=2)

    # Panel 3: Vanna & Charm
    fig.add_trace(
        go.Bar(
            y=df["strike"], x=df["netVEX"], orientation="h",
            width=bar_widths,
            marker_color="#38BDF8", opacity=0.8, name="Net VEX ($M)",
            hovertemplate="Strike: $%{y}<br>Net VEX: $%{x:.2f}M<extra></extra>",
        ),
        row=1, col=3,
    )
    fig.add_trace(
        go.Bar(
            y=df["strike"], x=df["netCHEX"], orientation="h",
            width=bar_widths,
            marker_color="#FACC15", opacity=0.8, name="Net CHEX ($M/ngày)",
            hovertemplate="Strike: $%{y}<br>Net CHEX: $%{x:.2f}M/ngày<extra></extra>",
        ),
        row=1, col=3,
    )
    fig.add_vline(x=0, line_dash="solid", line_color="#475569", row=1, col=3)

    # Horizontal Level Annotations across panels
    y_min = float(df["strike"].min()) - 10.0
    y_max = float(df["strike"].max()) + 10.0

    call_regime = meta.get("call_wall_regime", "NEUTRAL")
    put_regime = meta.get("put_wall_regime", "NEUTRAL")
    cw_tag = " [BOUNCE PIN]" if call_regime == "BOUNCE_WALL" else (" [MAGNET TRAP]" if call_regime == "MAGNET_WALL" else "")
    pw_tag = " [BOUNCE PIN]" if put_regime == "BOUNCE_WALL" else (" [MAGNET TRAP]" if put_regime == "MAGNET_WALL" else "")

    levels = [
        (call_wall, "#EF4444", f"CALL WALL (${call_wall:.0f}{cw_tag})", "top right", "dash"),
        (put_wall, "#22C55E", f"PUT WALL (${put_wall:.0f}{pw_tag})", "bottom right", "dash"),
        (strike_above, "#F87171", f"CẢN TRÊN (${strike_above:.0f})", "top right", "dot"),
        (strike_below, "#4ADE80", f"SÀN DƯỚI (${strike_below:.0f})", "bottom right", "dot"),
        (spot_price, "#FACC15", f"CME LIVE (${spot_price:.2f})", "top right", "solid"),
    ]
    zero_gamma = meta.get("zero_gamma_flip")
    if zero_gamma is not None and y_min <= zero_gamma <= y_max:
        levels.append((zero_gamma, "#F59E0B", f"ZERO GAMMA (${zero_gamma:.2f})", "top left", "longdash"))

    for lvl, color, label, pos, dash in levels:
        if y_min <= lvl <= y_max:
            for c in [1, 2, 3]:
                fig.add_hline(
                    y=lvl, line_color=color, line_width=1.8 if "LIVE" in label else 1.2,
                    line_dash=dash, row=1, col=c,
                )
            fig.add_annotation(
                y=lvl, x=0, xref="x1", yref="y1",
                text=f"<b>{label}</b>",
                showarrow=False,
                font=dict(color=color, size=11, family="JetBrains Mono"),
                bgcolor="rgba(15, 23, 42, 0.85)",
                bordercolor=color, borderwidth=1, borderpad=3,
                xanchor="left", yanchor="middle",
                row=1, col=1,
            )

    # Pin badges if key macro levels lie outside visible chart range
    if zero_gamma is not None and zero_gamma > y_max:
        fig.add_annotation(
            xref="paper", yref="paper",
            x=0.01, y=0.98,
            text=f"<b>▲ ZERO GAMMA FLIP: ${zero_gamma:.2f} (Macro Short Gamma ở trên)</b>",
            showarrow=False,
            font=dict(color="#F59E0B", size=10, family="JetBrains Mono"),
            bgcolor="rgba(15, 23, 42, 0.90)",
            bordercolor="#F59E0B", borderwidth=1, borderpad=4,
            xanchor="left", yanchor="top",
        )
    if call_wall > y_max:
        fig.add_annotation(
            xref="paper", yref="paper",
            x=0.01, y=0.90,
            text=f"<b>▲ CALL WALL: ${call_wall:.0f} (Nằm ngoài phạm vi trên)</b>",
            showarrow=False,
            font=dict(color="#EF4444", size=10, family="JetBrains Mono"),
            bgcolor="rgba(15, 23, 42, 0.90)",
            bordercolor="#EF4444", borderwidth=1, borderpad=4,
            xanchor="left", yanchor="top",
        )
    if put_wall < y_min:
        fig.add_annotation(
            xref="paper", yref="paper",
            x=0.01, y=0.04,
            text=f"<b>▼ PUT WALL: ${put_wall:.0f} (Nằm ngoài phạm vi dưới)</b>",
            showarrow=False,
            font=dict(color="#22C55E", size=10, family="JetBrains Mono"),
            bgcolor="rgba(15, 23, 42, 0.90)",
            bordercolor="#22C55E", borderwidth=1, borderpad=4,
            xanchor="left", yanchor="bottom",
        )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0F172A",
        plot_bgcolor="#0A0F1D",
        height=600,
        margin=dict(l=65, r=40, t=45, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(size=11, family="JetBrains Mono"),
        ),
        barmode="relative",
    )
    fig.update_yaxes(
        range=[y_min, y_max],
        gridcolor="#1E293B",
        tickmode="array",
        tickvals=df["strike"].tolist(),
        ticktext=[f"${int(s)}" if s == int(s) else f"${s:.1f}" for s in df["strike"]],
        tickfont=dict(size=11, family="JetBrains Mono", color="#94A3B8"),
    )
    fig.update_xaxes(gridcolor="#1E293B")
    return fig


def build_volatility_smile_figure(df_full: pd.DataFrame, meta: dict[str, Any]) -> go.Figure:
    """Build a standalone, full-width Plotly figure for the Volatility Smile & Skew Curve.

    Implements the Malz (1997) closed-form SVI parametrization in delta space:
        sigma(Delta) = sigma_atm - 2 * RR25 * (Delta - 0.5) + 16 * BF25 * (Delta - 0.5)^2
    Annotates the 3 Tactical Microstructure Invariants:
        - 🎯 Tâm Bão Pinning (ATM Strike - minimum IV sweet spot / theta decay)
        - 🛡️ Hố Đen Giảm Tốc (Put Wall - structural skew dip / safe fade limit)
        - ⚠️ Bẫy Thuốc Nổ (Call Wall - wing skew explosion / hard SL boundary)
        - ⚡ Giá Realtime CME Gold Futures (Spot price)
        - Zero Gamma Flip ($S^*)
    """
    spot_price = float(meta.get("spot_price", 4000.0))
    atm_strike = float(meta.get("atm_strike", spot_price))
    sigma_atm = float(meta.get("sigma_atm", 0.20))
    if sigma_atm <= 0:
        sigma_atm = 0.20

    dte_days = float(meta.get("dte_days", 8.0))
    t_years = max(dte_days / 365.0, 1.0 / 365.0)

    rr25 = float(meta.get("skew_rr25", 0.0))
    bf25 = float(meta.get("skew_bf25", 0.02))
    skew_label = str(meta.get("skew_label", "CÂN BẰNG"))
    delta_tilt_color = str(meta.get("delta_tilt_color", "#FACC15"))

    call_wall = float(meta.get("call_wall", spot_price + 50.0))
    put_wall = float(meta.get("put_wall", spot_price - 50.0))
    zero_gamma = meta.get("zero_gamma_flip")
    if zero_gamma is not None:
        zero_gamma = float(zero_gamma)

    # Strike bounds around spot price
    min_k_avail = float(df_full["strike"].min()) if not df_full.empty and "strike" in df_full.columns else spot_price - 220.0
    max_k_avail = float(df_full["strike"].max()) if not df_full.empty and "strike" in df_full.columns else spot_price + 220.0

    k_min = max(spot_price - 220.0, min_k_avail)
    k_max = min(spot_price + 220.0, max_k_avail)
    if k_max <= k_min:
        k_min = spot_price - 100.0
        k_max = spot_price + 100.0

    # 1. Theoretical Malz (1997) SVI Smile Curve
    k_grid = np.linspace(k_min, k_max, 150)
    denom = sigma_atm * math.sqrt(t_years)
    d1_grid = (np.log(spot_price / k_grid) + 0.5 * (sigma_atm ** 2) * t_years) / denom
    delta_grid = 0.5 * (1.0 + np.vectorize(math.erf)(d1_grid / math.sqrt(2.0)))
    delta_grid = np.clip(delta_grid, 0.01, 0.99)
    diff = delta_grid - 0.5
    model_iv_grid = sigma_atm - 2.0 * rr25 * diff + 16.0 * bf25 * (diff ** 2)
    model_iv_grid = np.maximum(0.02, model_iv_grid) * 100.0

    fig = go.Figure()

    # Trace 1: Malz SVI continuous curve
    fig.add_trace(
        go.Scatter(
            x=k_grid,
            y=model_iv_grid,
            mode="lines",
            name="Nụ Cười Chuẩn Hóa (Malz 1997 SVI)",
            line=dict(color="#FACC15", width=3.5),
            hovertemplate="<b>Mức Giá Strike</b>: $%{x:,.0f}<br><b>Model IV</b>: %{y:.2f}%<extra>Malz SVI Curve</extra>",
        )
    )

    # Traces 2 & 3: Market Observed Call & Put IV Scatter
    call_iv_col = "callIV" if "callIV" in df_full.columns else ("call_iv" if "call_iv" in df_full.columns else None)
    put_iv_col = "putIV" if "putIV" in df_full.columns else ("put_iv" if "put_iv" in df_full.columns else None)
    call_oi_col = "callOpenInterest" if "callOpenInterest" in df_full.columns else None
    put_oi_col = "putOpenInterest" if "putOpenInterest" in df_full.columns else None

    if call_iv_col and not df_full.empty:
        c_mask = (df_full["strike"] >= k_min) & (df_full["strike"] <= k_max) & (df_full[call_iv_col] > 0.03)
        df_c = df_full[c_mask]
        if not df_c.empty:
            c_oi = df_c[call_oi_col].values if call_oi_col else np.zeros(len(df_c))
            fig.add_trace(
                go.Scatter(
                    x=df_c["strike"],
                    y=df_c[call_iv_col] * 100.0,
                    mode="markers",
                    name="Call IV Thực Tế (COMEX)",
                    marker=dict(
                        size=7,
                        color="#38BDF8",
                        symbol="circle",
                        opacity=0.85,
                        line=dict(width=1, color="#0284C7"),
                    ),
                    customdata=c_oi,
                    hovertemplate="<b>Call Strike</b>: $%{x:,.0f}<br><b>Call IV</b>: %{y:.2f}%<br><b>Call OI</b>: %{customdata:,.0f} HĐ<extra>CME Call</extra>",
                )
            )

    if put_iv_col and not df_full.empty:
        p_mask = (df_full["strike"] >= k_min) & (df_full["strike"] <= k_max) & (df_full[put_iv_col] > 0.03)
        df_p = df_full[p_mask]
        if not df_p.empty:
            p_oi = df_p[put_oi_col].values if put_oi_col else np.zeros(len(df_p))
            fig.add_trace(
                go.Scatter(
                    x=df_p["strike"],
                    y=df_p[put_iv_col] * 100.0,
                    mode="markers",
                    name="Put IV Thực Tế (COMEX)",
                    marker=dict(
                        size=7,
                        color="#F87171",
                        symbol="diamond",
                        opacity=0.85,
                        line=dict(width=1, color="#DC2626"),
                    ),
                    customdata=p_oi,
                    hovertemplate="<b>Put Strike</b>: $%{x:,.0f}<br><b>Put IV</b>: %{y:.2f}%<br><b>Put OI</b>: %{customdata:,.0f} HĐ<extra>CME Put</extra>",
                )
            )

    # Invariant helper for model IV at specific strike
    def get_model_iv(k_val: float) -> float:
        d1_val = (math.log(spot_price / max(1.0, k_val)) + 0.5 * (sigma_atm ** 2) * t_years) / denom
        delta_val = 0.5 * (1.0 + math.erf(d1_val / math.sqrt(2.0)))
        delta_val = min(0.99, max(0.01, delta_val))
        diff_val = delta_val - 0.5
        iv_val = sigma_atm - 2.0 * rr25 * diff_val + 16.0 * bf25 * (diff_val ** 2)
        return max(0.02, iv_val) * 100.0

    iv_atm = get_model_iv(atm_strike)
    iv_pw = get_model_iv(put_wall)
    iv_cw = get_model_iv(call_wall)

    annotations = [
        # ATM Pinning Annotation
        dict(
            x=atm_strike,
            y=iv_atm,
            text=f"<b>🎯 TÂM BÃO PINNING</b><br>ATM ${atm_strike:,.0f} (IV: {iv_atm:.1f}%)<br><span style='font-size:9.5px;color:#334155;'>Vùng thu Theta & Pinning của MM</span>",
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=1.5,
            arrowcolor="#FACC15",
            ax=0,
            ay=55,
            font=dict(color="#000000", size=10, family="JetBrains Mono"),
            bgcolor="#FACC15",
            bordercolor="#EAB308",
            borderwidth=1,
            borderpad=4,
            opacity=0.95,
        ),
        # Live Spot Annotation
        dict(
            x=spot_price,
            y=1.02,
            yref="paper",
            text=f"<b>⚡ SPOT: ${spot_price:,.2f}</b>",
            showarrow=False,
            font=dict(color="#FACC15", size=10.5, family="JetBrains Mono"),
            bgcolor="rgba(15, 23, 42, 0.90)",
            bordercolor="#FACC15",
            borderwidth=1,
            borderpad=3,
        ),
    ]

    # Dynamic anti-collision offsets for Call Wall and Zero Gamma annotations
    cw_ax, cw_ay = -50, -55
    zg_ax, zg_ay = 0, -40
    if zero_gamma and (k_min <= zero_gamma <= k_max) and (k_min <= call_wall <= k_max):
        diff_wall_zg = zero_gamma - call_wall
        if abs(diff_wall_zg) < 140:
            if diff_wall_zg >= 0:
                # Call Wall is to the left of Zero Gamma (e.g. 4200 vs 4242)
                cw_ax, cw_ay = -75, -65
                zg_ax, zg_ay = 50, -35
            else:
                # Call Wall is to the right of Zero Gamma
                cw_ax, cw_ay = 65, -65
                zg_ax, zg_ay = -50, -35

    if k_min <= put_wall <= k_max:
        annotations.append(
            dict(
                x=put_wall,
                y=iv_pw,
                text=f"<b>🛡️ HỐ ĐEN GIẢM TỐC</b><br>Put Wall ${put_wall:,.0f} (IV: {iv_pw:.1f}%)<br><span style='font-size:9.5px;color:#CBD5E1;'>MM bán đè Vol • Điểm Limit Fade an toàn</span>",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=1.5,
                arrowcolor="#22C55E",
                ax=-40,
                ay=-50,
                font=dict(color="#F8FAFC", size=10, family="JetBrains Mono"),
                bgcolor="#14532D",
                bordercolor="#22C55E",
                borderwidth=1,
                borderpad=4,
                opacity=0.95,
            )
        )

    if k_min <= call_wall <= k_max:
        annotations.append(
            dict(
                x=call_wall,
                y=iv_cw,
                text=f"<b>⚠️ BẪY THUỐC NỔ</b><br>Call Wall ${call_wall:,.0f} (IV: {iv_cw:.1f}%)<br><span style='font-size:9.5px;color:#CBD5E1;'>Mép vểnh Squeeze • Bắt buộc cắt lỗ Hard SL</span>",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=1.5,
                arrowcolor="#EF4444",
                ax=cw_ax,
                ay=cw_ay,
                font=dict(color="#F8FAFC", size=10, family="JetBrains Mono"),
                bgcolor="#7F1D1D",
                bordercolor="#EF4444",
                borderwidth=1,
                borderpad=4,
                opacity=0.95,
            )
        )

    if zero_gamma and (k_min <= zero_gamma <= k_max):
        iv_zg = get_model_iv(zero_gamma)
        annotations.append(
            dict(
                x=zero_gamma,
                y=iv_zg,
                text=f"<b>ZERO GAMMA FLIP</b><br>${zero_gamma:,.1f}",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=1.5,
                arrowcolor="#F59E0B",
                ax=zg_ax,
                ay=zg_ay,
                font=dict(color="#000000", size=9.5, family="JetBrains Mono"),
                bgcolor="#F59E0B",
                bordercolor="#D97706",
                borderwidth=1,
                borderpad=3,
                opacity=0.95,
            )
        )

    shapes = [
        # Spot Price Line
        dict(
            type="line",
            x0=spot_price,
            x1=spot_price,
            y0=0,
            y1=1,
            yref="paper",
            line=dict(color="#FACC15", width=2, dash="dash"),
        ),
        # ATM Strike Line
        dict(
            type="line",
            x0=atm_strike,
            x1=atm_strike,
            y0=0,
            y1=1,
            yref="paper",
            line=dict(color="#94A3B8", width=1.2, dash="dot"),
        ),
    ]

    if k_min <= put_wall <= k_max:
        shapes.append(
            dict(
                type="line",
                x0=put_wall,
                x1=put_wall,
                y0=0,
                y1=1,
                yref="paper",
                line=dict(color="#22C55E", width=1.8, dash="dashdot"),
            )
        )

    if k_min <= call_wall <= k_max:
        shapes.append(
            dict(
                type="line",
                x0=call_wall,
                x1=call_wall,
                y0=0,
                y1=1,
                yref="paper",
                line=dict(color="#EF4444", width=1.8, dash="dashdot"),
            )
        )

    if zero_gamma and (k_min <= zero_gamma <= k_max):
        shapes.append(
            dict(
                type="line",
                x0=zero_gamma,
                x1=zero_gamma,
                y0=0,
                y1=1,
                yref="paper",
                line=dict(color="#F59E0B", width=1.5, dash="dot"),
            )
        )

    skew_badge_raw = str(meta.get("skew_regime", "BULLISH_CALL_SKEW"))
    if "BULLISH" in skew_badge_raw or rr25 > 0.005:
        skew_short = "BULLISH CALL SKEW"
    elif "BEARISH" in skew_badge_raw or rr25 < -0.005:
        skew_short = "DEFENSIVE PUT SKEW"
    else:
        skew_short = "CÂN BẰNG"

    fig.update_layout(
        title=dict(
            text=f"<b>CME GOLD OPTIONS GCZ26: ĐƯỜNG CONG NỤ CƯỜI BIẾN ĐỘNG & ĐỘ XIÊN (VOLATILITY SMILE & SKEW CURVE)</b><br>"
                 f"<span style='font-size:12px; color:#94A3B8; font-weight:normal;'>"
                 f"Mô hình Vi Cấu Trúc Malz (1997) SVI • ATM IV: <b>{sigma_atm*100:.2f}%</b> • "
                 f"25Δ Skew (RR25): <b style='color:{delta_tilt_color};'>{rr25*100:+.2f}v</b> ({skew_short}) • "
                 f"Curvature (BF25): <b>{bf25*100:+.2f}v</b> • Hạn: {meta.get('expiration_date', 'OGX26')}</span>",
            x=0.01,
            y=0.96,
            xanchor="left",
            yanchor="top",
            font=dict(family="JetBrains Mono, Inter, sans-serif", size=15, color="#F8FAFC"),
        ),
        template="plotly_dark",
        paper_bgcolor="#0F172A",
        plot_bgcolor="#0A0F1D",
        height=450,
        margin=dict(l=65, r=40, t=75, b=45),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1.0,
            font=dict(size=11, family="JetBrains Mono"),
            bgcolor="rgba(15, 23, 42, 0.8)",
            bordercolor="#334155",
            borderwidth=1,
        ),
        xaxis=dict(
            title=dict(text="Mức Giá Thực Hiện (Strike Price $K) - USD/oz", font=dict(size=12, color="#94A3B8")),
            gridcolor="#1E293B",
            tickfont=dict(size=11, family="JetBrains Mono", color="#94A3B8"),
            tickformat="$,.0f",
            range=[k_min - 2.0, k_max + 2.0],
        ),
        yaxis=dict(
            title=dict(text="Độ Biến Động Hàm Ý (Implied Volatility - IV %)", font=dict(size=12, color="#94A3B8")),
            gridcolor="#1E293B",
            tickfont=dict(size=11, family="JetBrains Mono", color="#94A3B8"),
            ticksuffix="%",
        ),
        annotations=annotations,
        shapes=shapes,
    )

    return fig


def generate_html_terminal(
    df: pd.DataFrame,
    meta: dict[str, Any],
    fig: go.Figure,
    fig_smile: go.Figure | None = None,
) -> str:
    if fig_smile is None:
        fig_smile = build_volatility_smile_figure(df, meta)

    now_vn = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7)))
    now_str = now_vn.strftime("%d/%m/%Y %H:%M:%S")

    spot = meta["spot_price"]
    atm_strike = meta["atm_strike"]
    regime = meta["regime"]
    total_gex = meta["total_net_gex"]
    total_vex = meta["total_net_vex"]
    total_chex = meta["total_net_chex"]
    expected_move = meta["expected_move_1s"]
    intraday_move = meta["rule16_daily_move"]
    call_wall = meta["call_wall"]
    call_wall_oi = meta["call_wall_oi"]
    put_wall = meta["put_wall"]
    put_wall_oi = meta["put_wall_oi"]
    zero_gamma = meta.get("zero_gamma_flip")
    call_wall_siege = float(meta.get("call_wall_siege", 0.0))
    put_wall_siege = float(meta.get("put_wall_siege", 0.0))
    call_wall_power = float(meta.get("call_wall_power", 0.0))
    put_wall_power = float(meta.get("put_wall_power", 0.0))
    call_wall_regime = str(meta.get("call_wall_regime", "NEUTRAL"))
    put_wall_regime = str(meta.get("put_wall_regime", "NEUTRAL"))

    call_badge_text = "BOUNCE PIN" if call_wall_regime == "BOUNCE_WALL" else ("BẪY NAM CHÂM" if call_wall_regime == "MAGNET_WALL" else "TRẦN MM")
    put_badge_text = "BOUNCE PIN" if put_wall_regime == "BOUNCE_WALL" else ("BẪY NAM CHÂM" if put_wall_regime == "MAGNET_WALL" else "ĐÁY MM")

    call_wall_tactical_note = (
        f"Call Wall {call_wall:.0f} là BẪY NAM CHÂM GIA TỐC (Short Gamma Squeeze / Siege {call_wall_siege:.2f}x): Cấm short đón đầu nếu volume lớn!"
        if call_wall_regime == "MAGNET_WALL"
        else f"Call Wall {call_wall_oi:,} OI (Pwr: {call_wall_power:.2f} - Nóc nhà kiên cố cuối cùng của MM)"
    )
    put_wall_tactical_note = (
        f"Put Wall {put_wall:.0f} là BẪY NAM CHÂM GIA TỐC (Negative GEX / Siege {put_wall_siege:.2f}x): CẤM ĐẶT LIMIT ĐÓN ĐẦU, chờ đâm thủng quét gamma mới buy reversal!"
        if put_wall_regime == "MAGNET_WALL"
        else f"Major Put Wall {put_wall_oi:,} OI (Pwr: {put_wall_power:.2f} - Đáy bê tông cốt thép của MM)"
    )

    # Institutional metrics
    rr25 = float(meta.get("skew_rr25", 0.0))
    bf25 = float(meta.get("skew_bf25", 0.0))
    skew_label = str(meta.get("skew_label", "CÂN BẰNG"))
    cta_badge = str(meta.get("cta_badge", "INDEPENDENT DEALER WALLS"))
    cta_desc = str(meta.get("cta_desc", "Biên độ phòng thủ của Market Maker"))
    cta_h20 = float(meta.get("cta_h20", spot + 50.0))
    cta_l20 = float(meta.get("cta_l20", spot - 50.0))

    # Dealer Net Position Delta (Contracts & DEX)
    total_net_delta_contracts = float(meta.get("total_net_delta_contracts", 0.0))
    total_net_dex = float(meta.get("total_net_dex", 0.0))
    max_tilt_strike = float(meta.get("max_tilt_strike", atm_strike))
    max_tilt_contracts = float(meta.get("max_tilt_contracts", 0.0))
    delta_tilt_label = str(meta.get("delta_tilt_label", "CÂN BẰNG"))
    delta_tilt_color = str(meta.get("delta_tilt_color", "#FACC15"))

    # Strikes and Geometry
    strikes = df["strike"].values
    step = float(np.diff(strikes).min()) if len(strikes) > 1 else 25.0
    buffer_up = min(step * 0.10, 2.50)
    buffer_down = min(step * 0.10, 2.50)
    front_run_tp = 1.00

    # Exact Entry & SL Calculations
    entry_squeeze = strike_above = float(strikes[strikes > spot][0]) if len(strikes[strikes > spot]) > 0 else call_wall
    next_above = float(strikes[strikes > spot][1]) if len(strikes[strikes > spot]) > 1 else strike_above + step
    entry_squeeze = strike_above + buffer_up + 0.50
    sl_squeeze = strike_above - 1.50
    sl_dist_squeeze = round(entry_squeeze - sl_squeeze, 2)

    entry_fade = strike_above - 1.00
    sl_fade = strike_above + buffer_up + 1.50
    sl_dist_fade = round(sl_fade - entry_fade, 2)

    strikes_below = strikes[strikes <= spot]
    strike_below = float(strikes_below[-1]) if len(strikes_below) > 0 else put_wall
    next_below = float(strikes_below[-2]) if len(strikes_below) > 1 else strike_below - step

    entry_rebound = strike_below + 1.00
    sl_rebound = strike_below - 4.00
    sl_dist_rebound = round(entry_rebound - sl_rebound, 2)

    entry_breakdown = strike_below - buffer_down - 0.50
    sl_breakdown = strike_below + 1.50
    sl_dist_breakdown = round(sl_breakdown - entry_breakdown, 2)

    entry_call_wall = call_wall - 1.00
    sl_call_wall = call_wall + 4.00
    sl_dist_cw = round(sl_call_wall - entry_call_wall, 2)

    entry_put_wall = put_wall + 0.50
    sl_put_wall = put_wall - 4.00
    sl_dist_pw = round(entry_put_wall - sl_put_wall, 2)

    # Volatility sizing with exact calculated SL distance
    size_squeeze = size_xauusd(equity_usd=10000.0, risk_pct=1.0, sl_usd=sl_dist_squeeze, gex_regime=regime)
    size_fade = size_xauusd(equity_usd=10000.0, risk_pct=1.0, sl_usd=sl_dist_fade, gex_regime=regime)
    size_rebound = size_xauusd(equity_usd=10000.0, risk_pct=1.0, sl_usd=sl_dist_rebound, gex_regime=regime)
    size_breakdown = size_xauusd(equity_usd=10000.0, risk_pct=1.0, sl_usd=sl_dist_breakdown, gex_regime=regime)
    size_call_wall = size_xauusd(equity_usd=10000.0, risk_pct=1.0, sl_usd=sl_dist_cw, gex_regime=regime)
    size_put_wall = size_xauusd(equity_usd=10000.0, risk_pct=1.0, sl_usd=sl_dist_pw, gex_regime=regime)
    # Major walls & air pockets
    major_down_wall, major_down_oi = find_next_major_wall(df, strike_below, direction="DOWN", oi_percentile=60.0)
    major_up_wall, major_up_oi = find_next_major_wall(df, strike_above, direction="UP", oi_percentile=60.0)

    down_pockets = detect_strike_air_pockets(df, strike_below, major_down_wall, threshold_ratio=0.40)
    has_down_air_pocket = len(down_pockets) > 0 or (abs(strike_below - major_down_wall) > step * 1.5)

    up_pockets = detect_strike_air_pockets(df, strike_above, major_up_wall, threshold_ratio=0.40)
    has_up_air_pocket = len(up_pockets) > 0 or (abs(major_up_wall - strike_above) > step * 1.5)

    # Run Scenario Engine
    scenario_res = evaluate_market_scenarios(
        spot_price=spot,
        atm_strike=atm_strike,
        strike_above=strike_above,
        strike_below=strike_below,
        call_wall=call_wall,
        call_wall_oi=call_wall_oi,
        put_wall=put_wall,
        put_wall_oi=put_wall_oi,
        regime=regime,
        total_gex=total_gex,
        total_chex=total_chex,
        has_up_air_pocket=has_up_air_pocket,
        has_down_air_pocket=has_down_air_pocket,
        major_up_wall=major_up_wall,
        major_down_wall=major_down_wall,
        recommended_lots=size_squeeze.recommended_lots,
        zero_gamma=zero_gamma,
        call_wall_siege=call_wall_siege,
        put_wall_siege=put_wall_siege,
    )
    active_sc = scenario_res.active_scenario

    # Scenario cards HTML
    scenario_cards_html = []
    for sc in scenario_res.all_scenarios:
        is_active = sc.is_active
        if sc.alert_level == AlertLevel.RED:
            card_border = "#EF4444" if is_active else "#7F1D1D"
            badge_bg = "rgba(239, 68, 68, 0.2)"
            badge_color = "#F87171"
            action_color = "#F87171"
        elif sc.alert_level == AlertLevel.GREEN:
            card_border = "#22C55E" if is_active else "#14532D"
            badge_bg = "rgba(34, 197, 94, 0.2)"
            badge_color = "#4ADE80"
            action_color = "#4ADE80"
        elif sc.alert_level == AlertLevel.YELLOW:
            card_border = "#EAB308" if is_active else "#713F12"
            badge_bg = "rgba(234, 179, 8, 0.2)"
            badge_color = "#FACC15"
            action_color = "#FACC15"
        else:
            card_border = "#475569" if is_active else "#1E293B"
            badge_bg = "rgba(148, 163, 184, 0.15)"
            badge_color = "#94A3B8"
            action_color = "#94A3B8"

        active_glow = f"box-shadow: 0 0 16px {card_border}; transform: scale(1.01); border: 2px solid {card_border};" if is_active else "opacity: 0.55; border: 1px solid #1E293B;"
        active_tag = f'<span class="badge" style="background:{badge_bg}; color:{badge_color}; border:1px solid {card_border}; font-weight:800; box-shadow:0 0 8px {card_border};">ĐANG DIỄN RA (ACTIVE)</span>' if is_active else '<span class="badge" style="background:rgba(51,65,85,0.4); color:#94A3B8; border:1px solid #334155;">CHỜ TÍN HIỆU (CHƯA KÍCH HOẠT)</span>'
        action_display = f'<span style="font-weight:800; color:{action_color};">{sc.action_label}</span>' if is_active else f'<span style="color:#64748B; font-weight:600;">{sc.action_label} <small style="color:#475569;">(Chưa áp dụng)</small></span>'

        scenario_cards_html.append(f"""
        <div id="card-{sc.code}" class="scenario-card" style="{active_glow} background:#0F172A; border-radius:10px; padding:14px; margin-bottom:12px; transition: all 0.3s ease;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; flex-wrap:wrap; gap:6px;">
                <div style="font-size:13px; font-weight:800; color:{'#F8FAFC' if is_active else '#94A3B8'};">{sc.code}: {sc.title.upper()}</div>
                <div id="card-tag-{sc.code}">{active_tag}</div>
            </div>
            <div style="font-size:12px; color:#94A3B8; margin-bottom:8px;">
                <b>Điều kiện:</b> {sc.condition_desc}
            </div>
            <div style="background:rgba(15,23,42,0.7); border:1px solid #1E293B; border-radius:6px; padding:8px 10px; margin-bottom:8px;">
                <div style="font-size:11px; text-transform:uppercase; color:#64748B; font-weight:700;">Hành vi Market Maker:</div>
                <div style="font-size:12px; color:#E2E8F0;">{sc.mm_state}</div>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid #1E293B; padding-top:8px;">
                <div style="font-size:11px; color:#94A3B8;">HÀNH ĐỘNG CẦN LÀM:</div>
                <div id="card-act-{sc.code}" style="font-size:12px; font-family:'JetBrains Mono', monospace;">{action_display}</div>
            </div>
        </div>
        """)
    scenario_cards_str = "".join(scenario_cards_html)

    # Strategy Table Targets with Invariant Enforcement (BUY: TP > Entry, SELL: TP < Entry)
    front_run_tp = 1.00
    buffer_up = min(step * 0.10, 2.50)
    buffer_down = min(step * 0.10, 2.50)

    # 1. Squeeze TP (BUY: must be strictly > entry_squeeze)
    raw_squeeze_tp = major_up_wall - front_run_tp if has_up_air_pocket else next_above - front_run_tp
    squeeze_tp = max(entry_squeeze + 2.00, raw_squeeze_tp)

    # 2. Fade TP (SELL: must be strictly < entry_fade)
    candidate_fade_tp = min(spot, strike_below + front_run_tp) if strike_below < entry_fade - 2.00 else entry_fade - 3.50
    tp_fade = min(entry_fade - 2.00, candidate_fade_tp)

    # 3. Rebound TP (BUY: must be strictly > entry_rebound)
    tp_rebound = max(entry_rebound + 2.50, strike_above - front_run_tp)

    # 4. Breakdown TP (SELL: must be strictly < entry_breakdown)
    raw_breakdown_tp = major_down_wall + front_run_tp if has_down_air_pocket else next_below + front_run_tp
    breakdown_tp = min(entry_breakdown - 2.00, raw_breakdown_tp)

    # 5. Call Wall Fade TP (SELL: must be strictly < entry_call_wall)
    tp_call_wall = min(entry_call_wall - 3.00, atm_strike)

    # 6. Put Wall Rebound TP (BUY: must be strictly > entry_put_wall)
    tp_put_wall = max(entry_put_wall + 3.00, atm_strike)

    # M5 Orderflow Tape & Volume Pulse processing
    m5_tape = meta.get("m5_tape") or {}
    m5_candles = m5_tape.get("candles") or []
    m5_high = float(m5_tape.get("day_high") or (spot + 10.0))
    m5_low = float(m5_tape.get("day_low") or (spot - 10.0))
    m5_range = float(m5_tape.get("day_range") or max(0.0, m5_high - m5_low))
    m5_avg_vol = float(m5_tape.get("avg_m5_volume") or 300.0)

    m5_rows = []
    # Cap candle history to most recent 30 candles to prevent memory growth
    for c in reversed(m5_candles[-30:]):
        is_spike = c.get("is_spike", False)
        sig_cls = c.get("signal_class", "normal")
        if sig_cls == "spike-absorption":
            badge_style = "background:rgba(34, 197, 94, 0.2); color:#4ADE80; border:1px solid #22C55E; font-weight:700;"
            vol_style = "color:#4ADE80; font-weight:800;"
        elif sig_cls == "spike-rejection":
            badge_style = "background:rgba(239, 68, 68, 0.2); color:#F87171; border:1px solid #EF4444; font-weight:700;"
            vol_style = "color:#F87171; font-weight:800;"
        elif sig_cls == "spike-neutral":
            badge_style = "background:rgba(234, 179, 8, 0.2); color:#FACC15; border:1px solid #EAB308; font-weight:700;"
            vol_style = "color:#FACC15; font-weight:800;"
        elif sig_cls == "low-vol":
            badge_style = "background:rgba(71, 85, 105, 0.2); color:#94A3B8; border:1px solid #475569;"
            vol_style = "color:#64748B;"
        else:
            badge_style = "background:transparent; color:#94A3B8; border:none;"
            vol_style = "color:#CBD5E1;"

        close_color = "#4ADE80" if c["close"] >= c["open"] else "#F87171"
        row_bg = "background:rgba(30, 41, 59, 0.7); box-shadow:inset 0 0 8px rgba(250,204,21,0.15);" if is_spike else ""
        m5_rows.append(f"""<tr style="{row_bg}">
            <td style="font-family:'JetBrains Mono', monospace; font-weight:700; color:#F8FAFC;">{c['time_vn']}</td>
            <td style="text-align:right; font-family:'JetBrains Mono', monospace;">${c['open']:,.2f}</td>
            <td style="text-align:right; font-family:'JetBrains Mono', monospace; color:#38BDF8;">${c['high']:,.2f}</td>
            <td style="text-align:right; font-family:'JetBrains Mono', monospace; color:#FACC15;">${c['low']:,.2f}</td>
            <td style="text-align:right; font-family:'JetBrains Mono', monospace; color:{close_color}; font-weight:700;">${c['close']:,.2f}</td>
            <td style="text-align:right; font-family:'JetBrains Mono', monospace; {vol_style}">{c['volume']:,}</td>
            <td style="text-align:center; font-family:'JetBrains Mono', monospace; {vol_style}">{c['ratio']:.1f}x</td>
            <td><span class="badge" style="{badge_style}">{c['note']}</span></td>
        </tr>""")

    m5_table_rows_html = "".join(m5_rows) if m5_rows else "<tr><td colspan='8' style='text-align:center; color:#64748B; padding:16px;'>Dữ liệu Orderflow M5 đang cập nhật từ COMEX...</td></tr>"

    smile_plotly_div = fig_smile.to_html(
        full_html=False,
        include_plotlyjs="cdn",
        config={"responsive": True, "displayModeBar": True},
    )
    plotly_div = fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        config={"responsive": True, "displayModeBar": True},
    )

    # Render complete HTML
    html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <title>NEIRO-QUANT: GCZ26 GOLD OPTIONS TACTICAL TERMINAL</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-base: #070B12; --bg-card: #0F172A; --border-color: #1E293B;
            --text-primary: #F8FAFC; --text-secondary: #94A3B8; --text-muted: #64748B;
            --neon-green: #22C55E; --neon-red: #EF4444; --neon-blue: #38BDF8; --neon-gold: #FACC15;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ background-color: var(--bg-base); color: var(--text-primary); font-family: 'Inter', sans-serif; padding: 14px; font-size: 13.5px; line-height: 1.5; }}
        .container {{ max-width: 1440px; margin: 0 auto; }}
        
        .header {{ display: flex; justify-content: space-between; align-items: center; padding: 14px 18px; background: linear-gradient(135deg, #1C1917 0%, #292524 100%); border: 1px solid #44403C; border-radius: 10px; margin-bottom: 14px; flex-wrap: wrap; gap: 10px; }}
        .brand {{ display: flex; align-items: center; gap: 10px; }}
        .brand-title {{ font-size: 18px; font-weight: 800; background: linear-gradient(90deg, #FDE047 0%, #EAB308 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: 0.5px; }}
        
        .badge {{ display: inline-block; padding: 3px 8px; border-radius: 5px; font-size: 11px; font-weight: 700; font-family: 'JetBrains Mono', monospace; }}
        .badge-gold {{ background: rgba(234, 179, 8, 0.15); color: #FACC15; border: 1px solid rgba(234, 179, 8, 0.4); }}
        .badge-live {{ background: rgba(34, 197, 94, 0.15); color: #4ADE80; border: 1px solid rgba(34, 197, 94, 0.4); }}
        
        .action-banner {{ border-radius: 12px; padding: 16px 20px; margin-bottom: 16px; transition: all 0.3s ease; }}
        .action-banner-red {{ border: 2px solid #EF4444; background: linear-gradient(135deg, rgba(239, 68, 68, 0.18) 0%, rgba(15, 23, 42, 0.95) 100%); box-shadow: 0 0 25px rgba(239, 68, 68, 0.3); }}
        .action-banner-green {{ border: 2px solid #22C55E; background: linear-gradient(135deg, rgba(34, 197, 94, 0.18) 0%, rgba(15, 23, 42, 0.95) 100%); box-shadow: 0 0 25px rgba(34, 197, 94, 0.3); }}
        .action-banner-yellow {{ border: 2px solid #EAB308; background: linear-gradient(135deg, rgba(234, 179, 8, 0.18) 0%, rgba(15, 23, 42, 0.95) 100%); box-shadow: 0 0 25px rgba(234, 179, 8, 0.3); }}
        .action-banner-gray {{ border: 1px solid #475569; background: #0F172A; }}

        .action-header-row {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 8px; }}
        .action-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; }}
        .action-box {{ background: rgba(15, 23, 42, 0.65); border: 1px solid #1E293B; border-radius: 8px; padding: 12px 14px; }}
        .action-cmd-title {{ font-size: 11px; text-transform: uppercase; color: #94A3B8; font-weight: 700; margin-bottom: 4px; }}
        .action-cmd-val {{ font-size: 22px; font-weight: 800; font-family: 'JetBrains Mono', monospace; margin-bottom: 4px; }}
        
        .spine-container {{ background: #0F172A; border: 1px solid #1E293B; border-radius: 10px; padding: 14px 18px; margin-bottom: 16px; }}
        .spine-track {{ display: flex; justify-content: space-between; align-items: center; position: relative; padding: 10px 0; margin-top: 8px; }}
        .spine-node {{ text-align: center; font-family: 'JetBrains Mono', monospace; z-index: 2; }}
        .spine-node-title {{ font-size: 10.5px; color: #94A3B8; text-transform: uppercase; margin-bottom: 2px; }}
        .spine-node-price {{ font-size: 14px; font-weight: 700; }}
        .spine-node-current {{ background: #FACC15; color: #000; padding: 4px 10px; border-radius: 6px; font-weight: 800; box-shadow: 0 0 10px #FACC15; }}
        
        .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; margin-bottom: 16px; }}
        .kpi-card {{ background-color: var(--bg-card); border: 1px solid var(--border-color); border-radius: 10px; padding: 12px 16px; }}
        .kpi-label {{ font-size: 10.5px; font-weight: 600; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 3px; }}
        .kpi-val {{ font-size: 21px; font-weight: 700; font-family: 'JetBrains Mono', monospace; }}
        .kpi-sub {{ font-size: 11px; color: var(--text-muted); margin-top: 2px; }}
        
        .chart-box {{ background-color: var(--bg-card); border: 1px solid var(--border-color); border-radius: 10px; padding: 10px; margin-bottom: 16px; }}
        .table-box {{ background-color: var(--bg-card); border: 1px solid var(--border-color); border-radius: 10px; padding: 14px; margin-bottom: 16px; overflow-x: auto; }}
        .section-header {{ font-size: 14px; font-weight: 700; margin-bottom: 10px; color: #E2E8F0; display: flex; align-items: center; justify-content: space-between; }}
        
        table {{ width: 100%; border-collapse: collapse; font-size: 12.5px; text-align: left; }}
        th {{ background-color: #111C33; color: var(--text-secondary); padding: 9px 12px; font-weight: 600; border-bottom: 1px solid var(--border-color); }}
        td {{ padding: 9px 12px; border-bottom: 1px solid #162238; font-family: 'JetBrains Mono', monospace; }}
        tr:hover td {{ background-color: #1E293B; }}
        .tag-buy {{ color: #4ADE80; font-weight: 700; }}
        .tag-sell {{ color: #F87171; font-weight: 700; }}
        
        .glossary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 10px; }}
        .glossary-item {{ background: #0B1120; border: 1px solid #1E293B; border-radius: 6px; padding: 10px 12px; font-size: 12px; line-height: 1.4; }}
        .glossary-term {{ font-weight: 700; color: #38BDF8; font-family: 'JetBrains Mono', monospace; margin-bottom: 2px; }}
        
        .footer {{ text-align: center; font-size: 11px; color: var(--text-muted); padding: 14px 0; border-top: 1px solid var(--border-color); }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <div class="brand">
            <div class="brand-title">NEIRO-QUANT: GCZ26 GOLD OPTIONS TACTICAL TERMINAL</div>
            <span class="badge badge-gold">100% PURE CME FUTURES</span>
            <span class="badge badge-live">ZERO TOUCH AUTOMATION</span>
        </div>
        <div style="font-family: 'JetBrains Mono', monospace; font-size: 11.5px; color: #D6D3D1; display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
            <div>Cập nhật: <b>{now_str} (Giờ VN)</b> | Hạn: <b>{meta.get('expiration_date', 'OGX26 (2026-10-27)')} ({float(meta.get('dte_days', 8.0)):.1f}d)</b></div>
            <button onclick="refreshWithCacheBuster()" style="background: rgba(250, 204, 21, 0.15); border: 1px solid rgba(250, 204, 21, 0.4); color: #FACC15; border-radius: 5px; padding: 3px 8px; font-size: 11px; cursor: pointer; font-family: 'JetBrains Mono', monospace; font-weight: 600;" title="Tải lại số liệu mới nhất">
                Làm mới
            </button>
            <button onclick="clearHistoryAndCache()" style="background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.4); color: #F87171; border-radius: 5px; padding: 3px 8px; font-size: 11px; cursor: pointer; font-family: 'JetBrains Mono', monospace; font-weight: 600;" title="Xóa sạch cache, giải phóng bộ nhớ RAM trình duyệt và đặt lại lịch sử">
                Dọn RAM & Cache
            </button>
            <span style="font-size: 10.5px; color: #64748B;">(Tự nạp lại: <b id="timer-sec" style="color: #4ADE80;">15</b>s)</span>
            <span class="badge badge-gold">100% PURE CME FUTURES</span>
        </div>
    </div>

    <!-- KHỐI 1: BIỂU ĐỒ VOLATILITY SMILE & SKEW (PANEL LỚN HẲN MALZ 1997 SVI) -->
    <div class="chart-box" style="margin-bottom: 16px;">
        {smile_plotly_div}
    </div>

    <!-- KHỐI 2: 3 PANEL BIỂU ĐỒ VI MÔ GEX, VOLUME/OI, GREEKS BẬC 2 (MẶC ĐỊNH TINH GỌN) -->
    <div class="chart-box" style="margin-bottom: 16px;">
        {plotly_div}
    </div>

    <!-- KHỐI 3: KPI THỐNG KÊ TOÀN CẢNH CME GOLD FUTURES (7 THẺ TOÀN CẢNH) -->
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-label">CME Gold Futures GCZ26 (COMEX)</div>
            <div id="kpi-cme-price" class="kpi-val" style="color: #FACC15;">${spot:,.2f}</div>
            <div class="kpi-sub">Trục ATM: <b id="kpi-atm-strike">${atm_strike:,.0f}</b> | Nguồn: <b id="kpi-price-source">{meta.get('futures_feed', 'LIVE COMEX (GC=F)')}</b></div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Market Regime & Net GEX</div>
            <div class="kpi-val" style="color: {'#4ADE80' if total_gex >= 0 else '#F87171'};">{total_gex:+.1f}M GEX</div>
            <div class="kpi-sub"><span class="badge badge-gold">{regime}</span>{f' <span style="color:#94A3B8; font-size:10.5px;">(Flip: ${zero_gamma:,.1f})</span>' if zero_gamma else ''}</div>
        </div>
        <div class="kpi-card" style="border: 1px solid {delta_tilt_color}66; box-shadow: 0 0 10px {delta_tilt_color}22;">
            <div class="kpi-label">Sổ Sách Dealer (Net Delta / DEX)</div>
            <div class="kpi-val" style="color: {delta_tilt_color}; font-size: 20px;">{total_net_delta_contracts:+,.0f} HĐ</div>
            <div class="kpi-sub"><span class="badge" style="background:{delta_tilt_color}22; color:{delta_tilt_color}; border:1px solid {delta_tilt_color}55;">{delta_tilt_label}</span> <span style="color:#94A3B8; font-size:10.5px;">(Tâm: ${max_tilt_strike:,.0f} &bull; {max_tilt_contracts:+,.0f} HĐ)</span></div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Zero Gamma Flip ($S^*) & Wall Siege</div>
            <div class="kpi-val" style="color: #F59E0B; font-size: 20px;">{f'${zero_gamma:,.2f}' if zero_gamma else 'N/A (Pure)'}</div>
            <div class="kpi-sub">CW Siege: <b>{call_wall_siege:.2f}x</b> | PW Siege: <b>{put_wall_siege:.2f}x</b></div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Biên Độ 1-Sigma Expected Move</div>
            <div class="kpi-val" style="color: #F59E0B;">±${expected_move:.2f}</div>
            <div class="kpi-sub">Trong ngày (Rule 16): <b>±${intraday_move:.2f}</b> (${spot-intraday_move:.1f} - ${spot+intraday_move:.1f})</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Greeks Bậc 2 (Vanna & Charm)</div>
            <div class="kpi-val" style="color: #38BDF8;">{total_vex:+.1f}M / {total_chex:+.1f}M</div>
            <div class="kpi-sub">VEX: {total_vex:+.1f}M | CHEX: {total_chex:+.1f}M/ngày</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Dòng Tiền Quỹ (25Δ Skew)</div>
            <div class="kpi-val" style="color: {'#4ADE80' if rr25 > 0.005 else ('#F87171' if rr25 < -0.005 else '#38BDF8')}; font-size: 19px;">
                {rr25*100:+.2f}v <span style="font-size:12px; color:#94A3B8;">(Fly: {bf25*100:+.2f}v)</span>
            </div>
            <div class="kpi-sub"><span class="badge badge-gold">{skew_label}</span></div>
        </div>
    </div>

    <!-- KHỐI 4: THƯỚC ĐO VỊ TRÍ GIÁ SO VỚI CHỐT CHẶN MM (VISUAL LEVEL SPINE) -->
    <div class="spine-container">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
            <div style="font-size:11.5px; font-weight:700; color:#94A3B8; text-transform:uppercase;">
                THƯỚC ĐO VỊ TRÍ GIÁ SO VỚI CÁC BỨC TƯỜNG CỦA MARKET MAKER:
            </div>
            <div style="font-size:11px; font-family:'JetBrains Mono', monospace; color:#64748B;">
                Đơn vị: CME Gold Futures (USD/oz)
            </div>
        </div>
        <div class="spine-track">
            <div class="spine-node">
                <div class="spine-node-title" style="color:#22C55E;">PUT WALL ({put_badge_text})</div>
                <div class="spine-node-price" style="color:#22C55E;">${put_wall:,.0f}</div>
                <div style="font-size:10px; color:#64748B;">({put_wall_oi:,} OI | Pwr: {put_wall_power:.2f} | Siege: {put_wall_siege:.2f}x)</div>
            </div>
            <div style="flex:1; height:2px; background:#1E293B; margin:0 8px; position:relative;">
                <div id="spine-dist-put" style="position:absolute; top:-8px; left:50%; transform:translateX(-50%); font-size:10px; color:#64748B;">
                    {spot - put_wall:+.1f}$
                </div>
            </div>
            <div class="spine-node">
                <div class="spine-node-title" style="color:#4ADE80;">SÀN DƯỚI</div>
                <div class="spine-node-price" style="color:#4ADE80;">${strike_below:,.0f}</div>
            </div>
            <div style="flex:1; height:2px; background:#FACC15; margin:0 8px; position:relative;">
                <div id="spine-dist-below" style="position:absolute; top:-8px; left:50%; transform:translateX(-50%); font-size:10px; color:#FACC15;">
                    {spot - strike_below:+.1f}$
                </div>
            </div>
            <div class="spine-node">
                <div class="spine-node-title" style="color:#FACC15; font-weight:800;">GIÁ HIỆN TẠI</div>
                <div id="spine-current-price" class="spine-node-current">${spot:,.2f}</div>
            </div>
            <div style="flex:1; height:2px; background:#FACC15; margin:0 8px; position:relative;">
                <div id="spine-dist-above" style="position:absolute; top:-8px; left:50%; transform:translateX(-50%); font-size:10px; color:#FACC15;">
                    {strike_above - spot:+.1f}$
                </div>
            </div>
            <div class="spine-node">
                <div class="spine-node-title" style="color:#F87171;">CẢN TRÊN</div>
                <div class="spine-node-price" style="color:#F87171;">${strike_above:,.0f}</div>
            </div>
            <div style="flex:1; height:2px; background:#1E293B; margin:0 8px; position:relative;">
                <div id="spine-dist-call" style="position:absolute; top:-8px; left:50%; transform:translateX(-50%); font-size:10px; color:#64748B;">
                    {call_wall - spot:+.1f}$
                </div>
            </div>
            <div class="spine-node">
                <div class="spine-node-title" style="color:#EF4444;">CALL WALL ({call_badge_text})</div>
                <div class="spine-node-price" style="color:#EF4444;">${call_wall:,.0f}</div>
                <div style="font-size:10px; color:#64748B;">({call_wall_oi:,} OI | Pwr: {call_wall_power:.2f} | Siege: {call_wall_siege:.2f}x)</div>
            </div>
        </div>
    </div>

    <!-- KHỐI 5: BĂNG GIÁ & XUNG LỰC VOLUME M5 THỜI GIAN THỰC (ORDERFLOW & VOLUME PULSE) -->
    <div class="table-box" style="margin-bottom: 16px; border: 1px solid #334155; background:#0B1120;">
        <div class="section-header" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:12px;">
            <div style="display:flex; align-items:center; gap:8px;">
                <span class="badge badge-gold">ORDERFLOW PULSE</span>
                <span style="font-size:13.5px; font-weight:800; color:#F8FAFC; letter-spacing:0.5px;">BĂNG GIÁ & XUNG LỰC VOLUME M5 REALTIME (COMEX GC=F)</span>
            </div>
            <div style="font-size:11.5px; font-family:'JetBrains Mono', monospace; color:#94A3B8;">
                Đỉnh ngày: <b style="color:#F87171;">${m5_high:,.2f}</b> &bull; Đáy ngày: <b style="color:#4ADE80;">${m5_low:,.2f}</b> &bull; Biên độ: <b style="color:#FACC15;">${m5_range:.2f}$</b> &bull; TB Vol M5: <b style="color:#38BDF8;">{m5_avg_vol:.0f} HĐ</b>
            </div>
        </div>
        <div style="overflow-x:auto;">
            <table>
                <thead>
                    <tr>
                        <th style="text-align:left;">Giờ VN (M5)</th>
                        <th style="text-align:right;">Giá Mở</th>
                        <th style="text-align:right;">Giá Cao</th>
                        <th style="text-align:right;">Giá Thấp</th>
                        <th style="text-align:right;">Giá Đóng</th>
                        <th style="text-align:right;">Volume (HĐ)</th>
                        <th style="text-align:center;">Xung Lực vs TB</th>
                        <th style="text-align:left;">Nhận Diện Vi Mô Orderflow</th>
                    </tr>
                </thead>
                <tbody>
                    {m5_table_rows_html}
                </tbody>
            </table>
        </div>
    </div>

    <!-- KHỐI 6: BẢNG CHIẾN LƯỢC TÁC CHIẾN RÚT GỌN (100% PURE CME FUTURES) -->
    <div class="table-box">
        <div class="section-header">PHẦN 1: BẢNG TÁC CHIẾN LƯỚT SÓNG TRONG NGÀY (INTRADAY SCALPING - ĂN 20-25 GIÁ)</div>
        <table>
            <thead>
                <tr>
                    <th>Chiến Lược</th>
                    <th>Vùng Kích Hoạt (CME)</th>
                    <th>Entry CME</th>
                    <th>Hard SL (CME)</th>
                    <th>Take Profit (TP)</th>
                    <th>Lot Size ($10K, R: 1%)</th>
                    <th>Hành Vi Của Market Maker & Túi Chân Không</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td class="tag-buy">1. BUY MUA ĐUỔI (Squeeze {strike_above:.0f})</td>
                    <td>Vượt > {strike_above + buffer_up:.2f}</td>
                    <td>{entry_squeeze:.2f}</td>
                    <td style="color:#F87171;">{sl_squeeze:.2f} (${sl_dist_squeeze:.1f})</td>
                    <td style="color:#4ADE80;">{squeeze_tp:.2f}</td>
                    <td style="color:#FACC15; font-weight:700;">~{size_squeeze.recommended_lots:.2f} Lot</td>
                    <td>MM vỡ trần Short -> Buộc mua Futures cover đẩy giá phóng lên trạm tiếp theo</td>
                </tr>
                <tr>
                    <td class="tag-sell">2. SELL CHẶN TIỀN TUYẾN (Fade {strike_above:.0f})</td>
                    <td>{strike_above - 1.50:.2f} - {strike_above:.2f}</td>
                    <td>{entry_fade:.2f}</td>
                    <td style="color:#F87171;">{sl_fade:.2f} (${sl_dist_fade:.1f})</td>
                    <td style="color:#4ADE80;">{tp_fade:.2f}</td>
                    <td style="color:#FACC15; font-weight:700;">~{size_fade.recommended_lots:.2f} Lot</td>
                    <td>Cản Vol cực đại -> MM tung lệnh bán chặn đầu ghìm giá quay lại ATM</td>
                </tr>
                <tr>
                    <td class="tag-buy">3. BUY BẮT SÀN ATM (Rebound {strike_below:.0f})</td>
                    <td>{strike_below:.2f} - {strike_below + 1.50:.2f}</td>
                    <td>{entry_rebound:.2f}</td>
                    <td style="color:#F87171;">{sl_rebound:.2f} (${sl_dist_rebound:.1f})</td>
                    <td style="color:#4ADE80;">{tp_rebound:.2f}</td>
                    <td style="color:#FACC15; font-weight:700;">~{size_rebound.recommended_lots:.2f} Lot</td>
                    <td>Đệm Put đỡ kỹ thuật -> MM gom mua đẩy giá phục hồi (vào khi có rút chân)</td>
                </tr>
                <tr>
                    <td class="tag-sell">4. SELL THỦNG SÀN & VACUUM RUN (Breakdown {strike_below:.0f})</td>
                    <td>Thủng < {strike_below - buffer_down:.2f}</td>
                    <td>{entry_breakdown:.2f}</td>
                    <td style="color:#F87171;">{sl_breakdown:.2f} (${sl_dist_breakdown:.1f})</td>
                    <td style="color:#4ADE80;">{breakdown_tp:.2f}</td>
                    <td style="color:#FACC15; font-weight:700;">~{size_breakdown.recommended_lots:.2f} Lot</td>
                    <td>Thủng đệm sàn -> Phía dưới là túi rỗng Air Pocket -> CẤM ĐỠ DAO, MM xả lũ</td>
                </tr>
            </tbody>
        </table>
    </div>

    <div class="table-box">
        <div class="section-header">PHẦN 2: BẢNG TÁC CHIẾN PHỤC KÍCH THÀNH TRÌ (STRUCTURAL SWING WALLS - ĐÁNH SÓNG LỚN)</div>
        <table>
            <thead>
                <tr>
                    <th>Chiến Lược</th>
                    <th>Vùng Kích Hoạt (CME)</th>
                    <th>Entry CME</th>
                    <th>Hard SL (CME)</th>
                    <th>Take Profit (TP)</th>
                    <th>Lot Size ($10K, R: 1%)</th>
                    <th>Ghi Chú Cấu Trúc Khối Lượng MM</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td class="tag-sell">5. BÁN ĐỈNH CALL WALL ({call_wall:.0f} - {call_badge_text})</td>
                    <td>{call_wall - 1.50:.2f} - {call_wall:.2f}</td>
                    <td>{entry_call_wall:.2f}</td>
                    <td style="color:#F87171;">{sl_call_wall:.2f} (${sl_dist_cw:.1f})</td>
                    <td style="color:#4ADE80;">{tp_call_wall:.2f}</td>
                    <td style="color:#FACC15; font-weight:700;">~{size_call_wall.recommended_lots:.2f} Lot</td>
                    <td>{call_wall_tactical_note}</td>
                </tr>
                <tr>
                    <td class="tag-buy">6. MUA ĐÁY PUT WALL ({put_wall:.0f} - {put_badge_text})</td>
                    <td>{put_wall:.2f} - {put_wall + 1.50:.2f}</td>
                    <td>{entry_put_wall:.2f}</td>
                    <td style="color:#F87171;">{sl_put_wall:.2f} (${sl_dist_pw:.1f})</td>
                    <td style="color:#4ADE80;">{tp_put_wall:.2f}</td>
                    <td style="color:#FACC15; font-weight:700;">~{size_put_wall.recommended_lots:.2f} Lot</td>
                    <td>{put_wall_tactical_note}</td>
                </tr>
            </tbody>
        </table>
    </div>

    <!-- KHỐI 7: BẢNG TÁC CHIẾN TỨC THÌ (GLANCEABLE 3-SECOND ACTION BANNER) -->
    <div id="live-action-banner" class="action-banner action-banner-{active_sc.alert_level.value.lower()}">
        <div class="action-header-row">
            <div>
                <span class="badge" style="background:#0F172A; color:#F8FAFC; border:1px solid #475569; font-size:12px; margin-right:6px;">KỊCH BẢN HIỆN TẠI</span>
                <span id="banner-sc-title" style="font-size:14px; font-weight:800; color:#F8FAFC; letter-spacing:0.5px;">{active_sc.code}: {active_sc.title.upper()}</span>
            </div>
            <div style="font-family:'JetBrains Mono', monospace; font-size:13px; color:#FACC15;">
                GIÁ REALTIME CME GCZ26: <b id="banner-cme-price">${spot:,.2f}</b> (Trục ATM: <span id="banner-atm-strike">${atm_strike:,.0f}</span>)
            </div>
        </div>
        <div class="action-grid">
            <div id="banner-action-card" class="action-box" style="border-left: 4px solid {'#EF4444' if active_sc.alert_level == AlertLevel.RED else ('#22C55E' if active_sc.alert_level == AlertLevel.GREEN else '#FACC15')};">
                <div class="action-cmd-title">HÀNH ĐỘNG CẦN THỰC HIỆN NGAY:</div>
                <div id="banner-action-cmd" class="action-cmd-val" style="color:{'#EF4444' if active_sc.alert_level == AlertLevel.RED else ('#4ADE80' if active_sc.alert_level == AlertLevel.GREEN else '#FACC15')};">
                    {active_sc.action_label}
                </div>
                <div id="banner-action-desc" style="font-size:11.5px; color:#94A3B8;">{active_sc.entry_desc}</div>
            </div>
            <div class="action-box">
                <div class="action-cmd-title">HÀNH VI CỦA MARKET MAKER:</div>
                <div id="banner-mm-state" style="font-size:12px; color:#E2E8F0; margin-bottom:6px;">{active_sc.mm_state}</div>
                <div style="font-size:11.5px; color:#38BDF8;">Dự đoán: <b id="banner-forecast">{active_sc.forecast}</b></div>
            </div>
            <div class="action-box">
                <div class="action-cmd-title">THÔNG SỐ VÀO LỆNH (CME FUTURES):</div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px; font-size:11.5px; font-family:'JetBrains Mono', monospace;">
                    <div>Kích hoạt: <b id="banner-entry-trigger">{f'${active_sc.entry_trigger:,.2f}' if active_sc.entry_trigger > 0 else 'Chờ tín hiệu'}</b></div>
                    <div>Khối lượng: <b id="banner-lot-size" style="color:#FACC15;">{f'~{active_sc.lot_size:.2f} Lot' if active_sc.lot_size > 0 else '0 Lot'}</b></div>
                    <div>Cắt lỗ SL: <b id="banner-hard-sl" style="color:#F87171;">{f'${active_sc.hard_sl:,.2f}' if active_sc.hard_sl > 0 else 'N/A'}</b></div>
                    <div>Chốt lời TP: <b id="banner-take-profit" style="color:#4ADE80;">{f'${active_sc.take_profit:,.2f}' if active_sc.take_profit > 0 else 'N/A'}</b></div>
                </div>
            </div>
        </div>
    </div>

    <!-- MA TRẬN 6 KỊCH BẢN THỜI GIAN THỰC (6-SCENARIO DYNAMIC MATRIX) -->
    <div class="table-box">
        <div class="section-header">
            <div>MA TRẬN 6 KỊCH BẢN HÀNH VI MARKET MAKER (TỰ ĐỘNG BẬT SÁNG THEO GIÁ REALTIME)</div>
            <div style="font-size:11.5px; font-weight:400; color:#94A3B8;">Kịch bản trùng khớp sẽ được viền sáng và báo động</div>
        </div>
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(340px, 1fr)); gap:12px;">
            {scenario_cards_str}
        </div>
    </div>

    <!-- KHỐI 7: TỪ ĐIỂN THUẬT NGỮ BỎ TÚI (QUICK GLOSSARY - 1 DÒNG DỄ HIỂU, KHÔNG ICON) -->
    <div class="table-box">
        <div class="section-header">
            <div>TỪ ĐIỂN THUẬT NGỮ BỎ TÚI (GIẢI THÍCH 1 DÒNG ĐƠN GIẢN)</div>
            <div style="font-size:11.5px; font-weight:400; color:#94A3B8;">Ngôn từ dễ hiểu, không rườm rà, hỗ trợ ra quyết định nhanh</div>
        </div>
        <div class="glossary-grid">
            <div class="glossary-item">
                <div class="glossary-term">Net GEX (Gamma Exposure)</div>
                <div>Lực ép mua hoặc bán của nhà cái khi giá chạy. Dương = nhà cái cản sóng; Âm = nhà cái đẩy sóng rơi hoặc tăng mạnh hơn.</div>
            </div>
            <div class="glossary-item">
                <div class="glossary-term">Call Wall</div>
                <div>Bức tường trần cứng nhất của nhà cái. Nếu giá vượt qua đây, nhà cái vỡ trận và phải mua đuổi cover.</div>
            </div>
            <div class="glossary-item">
                <div class="glossary-term">Put Wall</div>
                <div>Bức tường sàn đỡ cứng nhất của nhà cái. Nếu giá đâm thủng, nhà cái buông xuôi và xả hàng tháo chạy.</div>
            </div>
            <div class="glossary-item">
                <div class="glossary-term">Air Pocket (Túi chân không)</div>
                <div>Vùng rỗng thanh khoản, không có lệnh đệm của nhà cái. Giá rơi hoặc tăng xuyên qua vùng này rất nhanh và trượt dài.</div>
            </div>
            <div class="glossary-item">
                <div class="glossary-term">Gamma Squeeze</div>
                <div>Hiện tượng nhà cái bán khống bị cháy vị thế, thuật toán ép buộc họ phải ồ ạt mua Futures phòng hộ đẩy giá dựng đứng.</div>
            </div>
            <div class="glossary-item">
                <div class="glossary-term">Net CHEX (Charm Exposure)</div>
                <div>Mức độ nhà cái ghìm giá bất động qua từng giờ để đốt thời gian và bào mòn tiền phế quyền chọn mỗi ngày.</div>
            </div>
            <div class="glossary-item">
                <div class="glossary-term">25 Delta Skew (Risk Reversal)</div>
                <div>Thước đo dòng tiền của các quỹ lớn đang bỏ tiền cược vào chiều vàng phá đỉnh (Call) hay phòng hộ sập giá (Put).</div>
            </div>
            <div class="glossary-item">
                <div class="glossary-term">Zero Gamma Flip ($S^*)</div>
                <div>Mốc đảo chiều xu hướng sống còn. Trên Zero Gamma: MM mua thấp bán cao (Long Gamma / Hấp thụ biến động / Mean-reversion); Dưới Zero Gamma: MM bán tháo mua đuổi (Short Gamma / Kích hoạt bão giá Trend-following).</div>
            </div>
            <div class="glossary-item">
                <div class="glossary-term">Wall Siege Ratio (Tỷ Lệ Công Thành)</div>
                <div>Tốc độ dồn volume quyền chọn so với OI nền (Volume/OI). Nếu > 0.25 (Siege Alert): Phe tấn công đang dồn hỏa lực phá vỡ bức tường MM; MM có nguy cơ buông súng đầu hàng.</div>
            </div>
            <div class="glossary-item">
                <div class="glossary-term">Net Delta / DEX (Sổ Sách Dealer)</div>
                <div>Độ lệch số lượng hợp đồng Futures ròng (OI × Delta) mà Market Maker đang gánh trên sổ sách. Âm sâu (lệch Put): MM rủi ro cao nếu giá sập; Dương lớn (lệch Call): MM nghiêng về phe giữ hàng.</div>
            </div>
            <div class="glossary-item">
                <div class="glossary-term">Hard SL / Take Profit</div>
                <div>Điểm cắt lỗ tuyệt đối và chốt lời tối ưu được tính toán chính xác dựa theo độ dày của các bức tường nhà cái.</div>
            </div>
        </div>
    </div>

    <div class="footer">
        NEIRO-QUANT HEDGE FUND QUANTITATIVE SYSTEM &bull; 100% PURE CME GOLD FUTURES &bull; ZERO TOUCH CLOUD AUTOMATION
    </div>
</div>
<script>
    function refreshWithCacheBuster() {{
        var base = window.location.pathname.split('?')[0];
        // Dung location.replace de tranh tich luy history stack gay tran RAM trinh duyet
        window.location.replace(base + '?t=' + Date.now());
    }}
    function clearHistoryAndCache() {{
        try {{
            if (window.caches) {{
                caches.keys().then(function(names) {{
                    for (var name of names) caches.delete(name);
                }});
            }}
            if (window.sessionStorage) sessionStorage.clear();
            if (window.localStorage) localStorage.clear();
        }} catch(e) {{}}
        var base = window.location.pathname.split('?')[0];
        window.location.replace(base + '?cleared=1');
    }}
    if (window.location.search.indexOf('cleared=1') !== -1) {{
        var btn = document.querySelector("button[onclick='clearHistoryAndCache()']");
        if (btn) {{
            btn.innerText = "Đã dọn RAM!";
            btn.style.borderColor = "#22C55E";
            btn.style.color = "#4ADE80";
            setTimeout(function() {{
                btn.innerText = "Dọn RAM & Cache";
                btn.style.borderColor = "rgba(239, 68, 68, 0.4)";
                btn.style.color = "#F87171";
            }}, 3000);
        }}
    }}
    var countdown = 15;
    setInterval(function() {{
        countdown--;
        var el = document.getElementById("timer-sec");
        if (el) {{
            el.innerText = countdown;
        }}
        if (countdown <= 0) {{
            refreshWithCacheBuster();
        }}
    }}, 1000);
</script>
</body>
</html>
"""
    return html


def run_pipeline(
    input_csv: str = "data/options_prices_GCZ26.csv",
    output_files: list[str] | None = None,
    basis: float | None = None,
    no_mt5: bool | None = None,
) -> list[str]:
    if output_files is None:
        output_files = [
            "exports/latest_gold_dashboard.html",
            "exports/index.html",
        ]

    df_raw, meta = load_and_preprocess_options(input_csv, basis=basis, no_mt5=no_mt5)
    fig = build_plotly_figure(df_raw, meta)
    fig_smile = build_volatility_smile_figure(df_raw, meta)
    html_content = generate_html_terminal(df_raw, meta, fig, fig_smile=fig_smile)

    saved_paths = []
    for out_str in output_files:
        p = Path(out_str)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(html_content, encoding="utf-8")
        saved_paths.append(str(p))

    # Optional mirror to Google Drive Desktop if available locally
    drive_target = Path("H:/My Drive/Neiro-Quant/latest_gold_dashboard.html")
    if drive_target.parent.exists():
        try:
            drive_target.write_text(html_content, encoding="utf-8")
            saved_paths.append(str(drive_target))
        except Exception:
            pass

    # Zero-Waste Memory Cleanup: Giai phong doi tuong lon khoi RAM
    del df_raw, meta, fig, fig_smile, html_content
    gc.collect()

    return saved_paths


def get_process_memory_mb() -> float:
    """Returns current process RAM Working Set in MB without third-party dependencies."""
    try:
        import ctypes
        from ctypes import wintypes

        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        psapi = ctypes.windll.psapi
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS), wintypes.DWORD]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL

        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        if psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
            return float(counters.WorkingSetSize) / (1024.0 * 1024.0)
    except Exception:
        pass
    return 0.0


def clear_workspace_cache() -> int:
    """Clear memory, Python garbage, and temporary cache files."""
    basis_engine.clear_spot_cache()
    gc.collect()
    repo_root = Path(__file__).resolve().parent.parent.parent
    removed = 0
    # Clean temporary files in scratch or logs dirs
    for folder in [repo_root / "scratch", repo_root / "logs"]:
        if folder.exists():
            for f in folder.iterdir():
                if f.is_file() and (f.suffix in [".tmp", ".bak", ".log"] or f.name.startswith("temp_")):
                    try:
                        f.unlink()
                        removed += 1
                    except Exception:
                        pass
    return removed


def main():
    parser = argparse.ArgumentParser(description="Neiro-Quant Tactical HTML Dashboard Generator")
    parser.add_argument("--input", default="data/options_prices_GCZ26.csv", help="Input options CSV")
    parser.add_argument("--output", nargs="+", default=["exports/latest_gold_dashboard.html", "exports/index.html"], help="Output HTML paths")
    parser.add_argument("--basis", type=float, default=None, help="Dynamic Basis (Optional)")
    parser.add_argument("--no-mt5", action="store_true", default=True, help="Disable MT5 Spot conversion and display pure CME Futures levels only (Default: True)")
    parser.add_argument("--with-mt5", dest="no_mt5", action="store_false", help="Enable MT5 Spot conversion column")
    parser.add_argument("--loop", type=int, default=0, help="Continuous update interval in seconds (e.g. 15 for live). Default: 0 (run once)")
    parser.add_argument("--clear-cache", action="store_true", help="Clear temporary cache files, garbage collection, and spot cache")
    args = parser.parse_args()

    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    if args.clear_cache:
        removed_count = clear_workspace_cache()
        gc.collect()
        ram_mb = get_process_memory_mb()
        print(f"[CACHE CLEANUP] Flushed spot and memory caches. Removed {removed_count} temporary files. Current RAM: {ram_mb:.1f} MB.")

    if args.loop > 0:
        print(f"[LIVE RUNNER] Starting continuous dashboard update loop (Interval: {args.loop}s)... Press Ctrl+C to stop.")
        iteration = 0
        while True:
            iteration += 1
            now_vn = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7))).strftime("%H:%M:%S")
            try:
                saved = run_pipeline(input_csv=args.input, output_files=args.output, basis=args.basis, no_mt5=args.no_mt5)
                
                # Zero-Waste Memory Cleanup: Thu hoi ram, don sach cache sau moi chu ky
                basis_engine.clear_spot_cache()
                gc.collect()

                if iteration % 20 == 0:
                    removed_count = clear_workspace_cache()
                    if removed_count > 0:
                        print(f"[{now_vn}] [Zero-Waste] Cleaned {removed_count} temporary cache files.")

                ram_mb = get_process_memory_mb()
                ram_str = f" | RAM: {ram_mb:.1f} MB" if ram_mb > 0 else ""
                print(f"[{now_vn}] Iteration #{iteration}{ram_str}: Updated {len(saved)} files. Sleeping {args.loop}s...")
            except Exception as e:
                print(f"[{now_vn}] Warning during iteration #{iteration}: {e}. Retrying in {args.loop}s...")
                gc.collect()
            time.sleep(args.loop)
    else:
        saved = run_pipeline(input_csv=args.input, output_files=args.output, basis=args.basis, no_mt5=args.no_mt5)
        print(f"[SUCCESS] Generated {len(saved)} dashboard files:")
        for s in saved:
            print(f"   -> {s}")


if __name__ == "__main__":
    main()
