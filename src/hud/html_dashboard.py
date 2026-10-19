"""Neiro-Quant Tactical HTML Dashboard Generator.

Generates a standalone, production-grade Plotly interactive dark-mode terminal for
CME Gold Options (GCZ26) incorporating:
- Live KPI cards (Spot Price, Regime, Net GEX, 1-Sigma Expected Move, Net VEX/CHEX)
- 3-Panel Plotly Interactive Charts (Net GEX with execution levels, Volume vs OI, Vanna/Charm)
- Intraday Scalping Strategy Table
- Structural Swing Walls Strategy Table
"""
from __future__ import annotations

import argparse
import datetime
import math
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.quant_engine.synthetic import compute_dynamic_dte
from src.quant_engine.basis import resolve_dynamic_basis
from src.quant_engine.level_state import (
    LevelState,
    evaluate_tactical_level_states,
    find_next_major_wall,
    detect_strike_air_pockets,
)


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


def load_and_preprocess_options(csv_path: str, basis: float | None = None) -> tuple[pd.DataFrame, dict[str, Any]]:
    df_raw = pd.read_csv(csv_path)

    # Normalize column names
    col_clean = {c: c.strip() for c in df_raw.columns}
    df_raw.rename(columns=col_clean, inplace=True)

    # Standardize expected columns
    for col in ["callMid", "callBid", "callAsk", "callLatest", "callVolume", "callOpenInterest", "callGamma", "callIV",
                "putMid", "putBid", "putAsk", "putLatest", "putVolume", "putOpenInterest", "putGamma", "putIV"]:
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

    # 1. ATM Strike & Implied Spot Price via Put-Call Parity
    # Filter liquid strikes with active OI/volume to avoid stale outlier quotes
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

    r = 0.045
    exp_val = ""
    if "expirationDate" in df.columns:
        s_exp = df["expirationDate"].dropna()
        if not s_exp.empty:
            exp_val = str(s_exp.iloc[0]).strip()
    if not exp_val and hasattr(df, "attrs") and df.attrs.get("expiration_date"):
        exp_val = str(df.attrs["expiration_date"]).strip()

    if not exp_val:
        # Default to active CME Gold front-month Monthly Options (OGX26 / 2026-10-27)
        exp_val = "2026-10-27"

    dte_days = compute_dynamic_dte(exp_val, default_dte=8.0)
    T_years = max(dte_days / 365.0, 1.0 / 365.0)
    spot_price = atm_strike + math.exp(r * T_years) * (c_mid_atm - p_mid_atm)
    if spot_price <= 0 or math.isnan(spot_price):
        spot_price = atm_strike

    # 2. GEX Calculation ($M / 1% move)
    MULT = 100.0
    scale = (spot_price ** 2) * 0.01 / 1e6
    gamma_c = df["callGamma"].replace(0, 0.0037).fillna(0.0037)
    gamma_p = df["putGamma"].replace(0, 0.0037).fillna(0.0037)
    df["callGEX"] = gamma_c * df["callOpenInterest"] * MULT * scale
    df["putGEX"] = - (gamma_p * df["putOpenInterest"] * MULT * scale)
    df["netGEX"] = df["callGEX"] + df["putGEX"]

    # 3. Greeks Bac 2: Vanna (VEX) & Charm (CHEX) via Black-76
    atm_straddle = max(1.0, c_mid_atm + p_mid_atm)
    sigma_atm = float(np.clip(atm_straddle / (0.7979 * spot_price * np.sqrt(T_years)), 0.01, 2.0))
    expected_move_1s = atm_straddle / 0.7979
    rule16_daily_move = (sigma_atm / 16.0) * spot_price

    strikes_all = df["strike"].values.astype(float)
    denom = sigma_atm * np.sqrt(T_years)
    d1 = (np.log(np.maximum(1e-4, spot_price / strikes_all)) + 0.5 * (sigma_atm ** 2) * T_years) / denom
    d2 = d1 - denom
    pdf_d1 = (1.0 / np.sqrt(2.0 * np.pi)) * np.exp(-0.5 * (d1 ** 2))
    cdf_d1 = 0.5 * (1.0 + np.vectorize(math.erf)(d1 / np.sqrt(2.0)))
    df_disc = np.exp(-r * T_years)

    vanna = - df_disc * pdf_d1 * (d2 / sigma_atm)
    charm_call = - df_disc * (pdf_d1 * (r / denom - d2 / (2.0 * T_years)) - r * cdf_d1)
    charm_put = charm_call - r * df_disc

    df["callVEX"] = vanna * df["callOpenInterest"] * MULT * spot_price * 0.01 / 1e6
    df["putVEX"] = - (vanna * df["putOpenInterest"] * MULT * spot_price * 0.01 / 1e6)
    df["netVEX"] = df["callVEX"] + df["putVEX"]

    df["callCHEX"] = (charm_call / 365.0) * df["callOpenInterest"] * MULT * spot_price / 1e6
    df["putCHEX"] = - ((charm_put / 365.0) * df["putOpenInterest"] * MULT * spot_price / 1e6)
    df["netCHEX"] = df["callCHEX"] + df["putCHEX"]

    # 4. Structural Walls & Regime
    call_wall_row = df.loc[df["callOpenInterest"].idxmax()]
    put_wall_row = df.loc[df["putOpenInterest"].idxmax()]
    call_wall = float(call_wall_row["strike"])
    call_wall_oi = int(call_wall_row["callOpenInterest"])
    put_wall = float(put_wall_row["strike"])
    put_wall_oi = int(put_wall_row["putOpenInterest"])

    total_net_gex = float(df["netGEX"].sum())
    total_net_vex = float(df["netVEX"].sum())
    total_net_chex = float(df["netCHEX"].sum())
    regime = "LONG_GAMMA" if total_net_gex > 10.0 else ("SHORT_GAMMA" if total_net_gex < -10.0 else "NEUTRAL")

    squeeze_trigger = call_wall + 2.50
    waterfall_trigger = put_wall - 2.50

    if basis is None:
        basis = resolve_dynamic_basis(spot_price, fallback_basis=24.0)

    meta = {
        "spot_price": spot_price,
        "atm_strike": atm_strike,
        "atm_straddle": atm_straddle,
        "sigma_atm": sigma_atm,
        "expected_move_1s": expected_move_1s,
        "rule16_daily_move": rule16_daily_move,
        "call_wall": call_wall,
        "call_wall_oi": call_wall_oi,
        "put_wall": put_wall,
        "put_wall_oi": put_wall_oi,
        "total_net_gex": total_net_gex,
        "total_net_vex": total_net_vex,
        "total_net_chex": total_net_chex,
        "regime": regime,
        "squeeze_trigger": squeeze_trigger,
        "waterfall_trigger": waterfall_trigger,
        "basis": basis,
        "dte_days": dte_days,
        "expiration_date": f"OGX26 ({exp_val})" if exp_val else "OGX26 (2026-10-27)",
    }
    return df, meta


def build_plotly_figure(df_full: pd.DataFrame, meta: dict[str, Any]) -> go.Figure:
    spot_price = meta["spot_price"]
    atm_strike = meta["atm_strike"]
    call_wall = meta["call_wall"]
    call_wall_oi = meta["call_wall_oi"]
    put_wall = meta["put_wall"]
    put_wall_oi = meta["put_wall_oi"]
    squeeze_trigger = meta["squeeze_trigger"]
    waterfall_trigger = meta["waterfall_trigger"]

    # Near-The-Money filter: ATM ± 5 strikes for intraday scalping (10-11 strikes total)
    atm_idx = (df_full["strike"] - atm_strike).abs().idxmin()
    half = 5
    s_idx = max(0, atm_idx - half)
    e_idx = min(len(df_full), atm_idx + half + 1)
    df = df_full.iloc[s_idx:e_idx].copy().reset_index(drop=True)

    strikes = df["strike"].values
    step = float(np.diff(strikes).min()) if len(strikes) > 1 else 25.0

    # Dynamic Tactical levels
    strikes_above = strikes[strikes > spot_price]
    strike_above = float(strikes_above[0]) if len(strikes_above) > 0 else call_wall
    next_above = float(strikes_above[1]) if len(strikes_above) > 1 else strike_above + step

    strikes_below = strikes[strikes <= spot_price]
    strike_below = float(strikes_below[-1]) if len(strikes_below) > 0 else put_wall
    next_below = float(strikes_below[-2]) if len(strikes_below) > 1 else strike_below - step

    fig = make_subplots(
        rows=1, cols=3,
        shared_yaxes=True,
        horizontal_spacing=0.035,
        subplot_titles=(
            "<b>Panel 1: Net GEX ($M) & Mốc Chiến Thuật (SL/TP)</b>",
            "<b>Panel 2: Dòng Tiền Volume vs Open Interest Nén</b>",
            "<b>Panel 3: Greeks Bậc 2 (Vanna & Charm)</b>",
        ),
        column_widths=[0.36, 0.36, 0.28],
    )

    # Panel 1: Net GEX
    colors_g = ["#4ADE80" if x >= 0 else "#F87171" for x in df["netGEX"]]
    fig.add_trace(
        go.Bar(
            y=df["strike"], x=df["netGEX"], orientation="h",
            marker_color=colors_g, name="Net GEX ($M)",
            hovertemplate="Strike: $%{y}<br>Net GEX: $%{x:.2f}M<extra></extra>",
        ),
        row=1, col=1,
    )
    fig.add_vline(x=0, line_dash="solid", line_color="#475569", row=1, col=1)

    # Spot Price horizontal line across all 3 panels
    for col_idx in (1, 2, 3):
        fig.add_hline(
            y=spot_price, line_color="#38BDF8", line_width=2.2,
            row=1, col=col_idx,
        )

    # Panel 1 Action Annotations & Lines
    if strikes.min() <= call_wall <= strikes.max():
        fig.add_hline(y=call_wall, line_color="#A855F7", line_dash="dash", line_width=1.8, row=1, col=1)
    if strikes.min() <= put_wall <= strikes.max():
        fig.add_hline(y=put_wall, line_color="#34D399", line_dash="dash", line_width=1.8, row=1, col=1)

    # Place SPOT CME label cleanly at the right edge of Panel 1 to avoid colliding with left-side levels
    fig.add_annotation(
        x=0.98, y=spot_price,
        text=f"◄ SPOT CME: {spot_price:.2f} (ATM: {atm_strike:.0f})",
        showarrow=False, xanchor="right", xref="x domain", yref="y",
        font=dict(color="#FFFFFF", size=9.5, family="JetBrains Mono"),
        bgcolor="#0284C7", bordercolor="#38BDF8", borderwidth=1, borderpad=3,
    )

    if strikes.min() <= put_wall <= strikes.max():
        fig.add_annotation(
            x=0.03, y=put_wall - step * 0.15,
            text=f"<b>[PUT WALL {put_wall:.0f}] ({put_wall_oi:,} OI)</b> &bull; Mua Rebound: {put_wall-1.5:.1f}-{put_wall+1.5:.1f} (SL: {put_wall-4:.1f})",
            showarrow=True, arrowhead=2, arrowcolor="#EF4444", ax=0, ay=18,
            align="left", xref="x domain", yref="y",
            font=dict(color="#FEE2E2", size=8.5),
            bgcolor="rgba(127, 29, 29, 0.92)", bordercolor="#EF4444", borderwidth=1,
        )

    if strikes.min() <= strike_above <= strikes.max() and strike_above != call_wall:
        fig.add_annotation(
            x=0.03, y=strike_above + step * 0.15,
            text=f"<b>CỬA ẢI {strike_above:.0f}</b> (Squeeze > {strike_above+2.5:.1f} -> TP {next_above:.0f})",
            showarrow=True, arrowhead=2, arrowcolor="#22C55E", ax=0, ay=-16,
            xref="x domain", yref="y", font=dict(color="#DCFCE7", size=8.5),
            bgcolor="rgba(20, 83, 45, 0.92)", bordercolor="#22C55E", borderwidth=1,
        )

    # Only show separate Sàn Đỡ if not directly overlapping the ATM strike
    if strikes.min() <= strike_below <= strikes.max() and strike_below != put_wall and abs(strike_below - spot_price) > 3.0:
        fig.add_annotation(
            x=0.03, y=strike_below - step * 0.15,
            text=f"<b>SÀN ĐỠ {strike_below:.0f}</b> (Rebound: {strike_below-1.5:.1f}-{strike_below+1.5:.1f})",
            showarrow=True, arrowhead=2, arrowcolor="#38BDF8", ax=0, ay=16,
            xref="x domain", yref="y", font=dict(color="#E0F2FE", size=8.5),
            bgcolor="rgba(12, 74, 110, 0.92)", bordercolor="#38BDF8", borderwidth=1,
        )

    # Dynamic Tactical Banner for Secondary Support (Trạm Nghỉ Động nấc 2 / Chốt Lời Short)
    secondary_support = next_below
    if strikes.min() <= secondary_support <= strikes.max() and secondary_support != put_wall and secondary_support != strike_below:
        fig.add_annotation(
            x=0.03, y=secondary_support - step * 0.15,
            text=f"<b>TRẠM NGHỈ {secondary_support:.0f}</b> (TP Short / Đệm hỗ trợ nấc 2 trước Put Wall {put_wall:.0f})",
            showarrow=True, arrowhead=2, arrowcolor="#F59E0B", ax=0, ay=16,
            xref="x domain", yref="y", font=dict(color="#FEF3C7", size=8.5),
            bgcolor="rgba(180, 83, 9, 0.92)", bordercolor="#F59E0B", borderwidth=1,
        )

    # Panel 2: Volume vs Open Interest
    fig.add_trace(
        go.Bar(
            y=df["strike"], x=df["callOpenInterest"], orientation="h",
            marker_color="#86EFAC", opacity=0.5, name="Call OI (Nền tích lũy)",
            hovertemplate="Strike: $%{y}<br>Call OI: %{x:,}<extra></extra>",
        ),
        row=1, col=2,
    )
    fig.add_trace(
        go.Bar(
            y=df["strike"], x=-df["putOpenInterest"], orientation="h",
            marker_color="#FCA5A5", opacity=0.5, name="Put OI (Nền tích lũy)",
            hovertemplate="Strike: $%{y}<br>Put OI: %{customdata:,}<extra></extra>",
            customdata=df["putOpenInterest"],
        ),
        row=1, col=2,
    )
    fig.add_trace(
        go.Bar(
            y=df["strike"], x=df["callVolume"], orientation="h",
            marker_color="#16A34A", name="Call Volume (Lực Mua)",
            hovertemplate="Strike: $%{y}<br>Call Vol: %{x:,}<extra></extra>",
        ),
        row=1, col=2,
    )
    fig.add_trace(
        go.Bar(
            y=df["strike"], x=-df["putVolume"], orientation="h",
            marker_color="#DC2626", name="Put Volume (Lực Bán)",
            hovertemplate="Strike: $%{y}<br>Put Vol: %{customdata:,}<extra></extra>",
            customdata=df["putVolume"],
        ),
        row=1, col=2,
    )
    fig.add_vline(x=0, line_dash="solid", line_color="#475569", row=1, col=2)

    # Panel 3: Greeks Bac 2 (Vanna & Charm)
    fig.add_trace(
        go.Bar(
            y=df["strike"], x=df["netVEX"], orientation="h",
            marker_color="#FB923C", name="Net VEX ($M / 1% IV)",
            hovertemplate="Strike: $%{y}<br>Net VEX: $%{x:.2f}M<extra></extra>",
        ),
        row=1, col=3,
    )
    fig.add_trace(
        go.Bar(
            y=df["strike"], x=df["netCHEX"], orientation="h",
            marker_color="#22D3EE", name="Net CHEX ($M / ngày)",
            hovertemplate="Strike: $%{y}<br>Net CHEX: $%{x:.2f}M<extra></extra>",
        ),
        row=1, col=3,
    )
    fig.add_vline(x=0, line_dash="solid", line_color="#475569", row=1, col=3)

    # Top VEX & CHEX annotations with collision prevention
    top_vex_idx = df["netVEX"].abs().idxmax()
    top_vex_val = df.loc[top_vex_idx, "netVEX"]
    top_vex_stk = df.loc[top_vex_idx, "strike"]

    top_chex_idx = df["netCHEX"].abs().idxmax()
    top_chex_val = df.loc[top_chex_idx, "netCHEX"]
    top_chex_stk = df.loc[top_chex_idx, "strike"]

    # If Vanna and Charm peaks share the same strike, offset them vertically
    if top_vex_stk == top_chex_stk:
        y_vex = top_vex_stk + step * 0.22
        y_chex = top_chex_stk - data_step if (data_step := step * 0.22) else top_chex_stk
    else:
        y_vex = top_vex_stk
        y_chex = top_chex_stk

    fig.add_annotation(
        x=top_vex_val, y=y_vex,
        text=f"◄ ĐỈNH VANNA ({top_vex_val:+.1f}M): V-Rebound",
        showarrow=False, xanchor="left" if top_vex_val >= 0 else "right",
        xref="x3", yref="y3", font=dict(color="#FDBA74", size=8.5),
        bgcolor="#1C1917", bordercolor="#FB923C", borderwidth=1, borderpad=2,
    )

    fig.add_annotation(
        x=top_chex_val, y=y_chex,
        text=f"ĐỈNH CHARM ({top_chex_val:+.1f}M): Ghìm giá đêm ►",
        showarrow=False, xanchor="right" if top_chex_val <= 0 else "left",
        xref="x3", yref="y3", font=dict(color="#67E8F9", size=8.5),
        bgcolor="#1C1917", bordercolor="#22D3EE", borderwidth=1, borderpad=2,
    )

    # Layout styling with ample top margin to prevent legend/title overlap
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0A0E17",
        plot_bgcolor="#111827",
        font=dict(family="Inter, sans-serif", color="#F8FAFC"),
        height=720,
        margin=dict(l=70, r=30, t=115, b=45),
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.07,
            xanchor="center", x=0.5,
            font=dict(size=10),
        ),
        barmode="relative",
    )

    tickvals = list(strikes)
    ticktext = [f"${s:.0f}" for s in strikes]
    fig.update_yaxes(
        tickmode="array", tickvals=tickvals, ticktext=ticktext,
        gridcolor="#1E293B", row=1, col=1,
        title=dict(text="CME Gold Futures Strike Price ($)", font=dict(size=11)),
    )
    fig.update_yaxes(tickmode="array", tickvals=tickvals, showticklabels=False, gridcolor="#1E293B", row=1, col=2)
    fig.update_yaxes(tickmode="array", tickvals=tickvals, showticklabels=False, gridcolor="#1E293B", row=1, col=3)

    fig.update_xaxes(gridcolor="#1E293B", title=dict(text="Net GEX ($M / 1% Move)", font=dict(size=10)), row=1, col=1)
    fig.update_xaxes(gridcolor="#1E293B", title=dict(text="Put OI/Vol (-) | Call OI/Vol (+)", font=dict(size=10)), row=1, col=2)

    # Expand Panel 3 x-axis range so annotations never clip or overflow
    max_vc = max(float(df["netVEX"].abs().max()), float(df["netCHEX"].abs().max()), 5.0)
    fig.update_xaxes(
        range=[-max_vc * 2.2, max_vc * 2.2],
        gridcolor="#1E293B",
        title=dict(text="Greeks Bậc 2 ($M Exposure)", font=dict(size=10)),
        row=1, col=3,
    )

    return fig


def generate_html_terminal(df: pd.DataFrame, meta: dict[str, Any], fig: go.Figure) -> str:
    now_vn = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7)))
    now_str = now_vn.strftime("%d/%m/%Y %H:%M:%S")

    spot = meta["spot_price"]
    basis = float(meta.get("basis", 24.0))
    spot_mt5 = spot - basis
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

    strikes = df["strike"].values
    step = float(np.diff(strikes).min()) if len(strikes) > 1 else 25.0
    strikes_above = strikes[strikes > spot]
    strike_above = float(strikes_above[0]) if len(strikes_above) > 0 else call_wall
    next_above = float(strikes_above[1]) if len(strikes_above) > 1 else strike_above + step

    strikes_below = strikes[strikes <= spot]
    strike_below = float(strikes_below[-1]) if len(strikes_below) > 0 else put_wall
    next_below = float(strikes_below[-2]) if len(strikes_below) > 1 else strike_below - step
    secondary_support = next_below

    buffer_up = min(step * 0.10, 2.50)
    buffer_down = min(step * 0.10, 2.50)
    front_run_tp = 1.00

    # Level State Machine & Air Pocket Pipeline (Tầng 4)
    level_evals = evaluate_tactical_level_states(spot, df, meta)
    major_down_wall, major_down_oi = find_next_major_wall(df, strike_below, direction="DOWN", oi_percentile=60.0)
    major_up_wall, major_up_oi = find_next_major_wall(df, strike_above, direction="UP", oi_percentile=60.0)

    down_pockets = detect_strike_air_pockets(df, strike_below, major_down_wall, threshold_ratio=0.40)
    has_down_air_pocket = len(down_pockets) > 0 or (abs(strike_below - major_down_wall) > step * 1.5)

    up_pockets = detect_strike_air_pockets(df, strike_above, major_up_wall, threshold_ratio=0.40)
    has_up_air_pocket = len(up_pockets) > 0 or (abs(major_up_wall - strike_above) > step * 1.5)

    breakdown_tp = major_down_wall + front_run_tp if has_down_air_pocket else secondary_support + front_run_tp
    breakdown_tp_note = f"Nấc {major_down_wall:.0f} (Major Wall)" if has_down_air_pocket else f"Nấc {secondary_support:.0f}"
    breakdown_note = (
        f"🚨 SLICED_VACUUM_RUN: Phía dưới là Túi chân không (Air Pocket) -> CẤM BẮT ĐÁY! "
        f"Dealer xả Delta Hedge ép giá trượt thẳng về Major Wall {major_down_wall:.0f} ({major_down_oi:,} OI)"
    ) if has_down_air_pocket else (
        f"Mất mốc ATM Pivot -> Rơi tự do về trạm nghỉ {secondary_support:.0f} (Đệm nấc 2)"
    )

    squeeze_tp = major_up_wall - front_run_tp if has_up_air_pocket else next_above - front_run_tp
    squeeze_tp_note = f"Nấc {major_up_wall:.0f} (Major Wall)" if has_up_air_pocket else f"Nấc {next_above:.0f}"
    squeeze_note = (
        f"⚡ GAMMA SQUEEZE VACUUM RUN: MM vỡ trần Short -> Phía trên là Air Pocket, giá hút vụt lên {major_up_wall:.0f} ({major_up_oi:,} OI)"
    ) if has_up_air_pocket else (
        f"MM vỡ trần Short -> Gamma Squeeze đẩy giá lên nấc {next_above:.0f}"
    )

    radar_cards_html = []
    for ev in level_evals:
        if ev.state == LevelState.SLICED_VACUUM_RUN:
            badge_html = '<span class="badge" style="background:rgba(239, 68, 68, 0.2); color:#F87171; border:1px solid #EF4444;">🔴 SLICED / VACUUM RUN</span>'
            border_color = "rgba(239, 68, 68, 0.5)"
        elif ev.state == LevelState.TESTING:
            badge_html = '<span class="badge" style="background:rgba(250, 204, 21, 0.2); color:#FACC15; border:1px solid #EAB308;">🟡 TESTING</span>'
            border_color = "rgba(250, 204, 21, 0.5)"
        elif ev.state == LevelState.ABSORPTION_DEFENDED:
            badge_html = '<span class="badge" style="background:rgba(34, 197, 94, 0.2); color:#4ADE80; border:1px solid #22C55E;">🟢 DEFENDED</span>'
            border_color = "rgba(34, 197, 94, 0.5)"
        elif ev.state == LevelState.WALL_DEFENDED:
            badge_html = '<span class="badge" style="background:rgba(56, 189, 248, 0.15); color:#38BDF8; border:1px solid #0284C7;">🛡️ HOLDING</span>'
            border_color = "rgba(56, 189, 248, 0.3)"
        else:
            badge_html = '<span class="badge" style="background:rgba(148, 163, 184, 0.15); color:#94A3B8; border:1px solid #475569;">⚪ DORMANT</span>'
            border_color = "var(--border-color)"

        target_text = f" &bull; Đích đến: <b>${ev.vacuum_target:,.0f}</b>" if ev.vacuum_target else ""
        radar_cards_html.append(f"""
            <div class="kpi-card" style="border: 1px solid {border_color}; padding: 12px 14px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                    <div style="font-size:12px; font-weight:700; color:#E2E8F0;">{ev.level_name} (${ev.strike:,.0f})</div>
                    {badge_html}
                </div>
                <div style="font-size:11.5px; color:#94A3B8; line-height:1.4;">
                    {ev.notes}{target_text}
                </div>
            </div>
        """)
    radar_cards_str = "".join(radar_cards_html)

    plotly_div = fig.to_html(full_html=False, include_plotlyjs="cdn", config={"responsive": True, "displayModeBar": True})

    html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <meta http-equiv="refresh" content="300">
    <title>NEIRO-QUANT: GCZ26 GOLD OPTIONS TACTICAL TERMINAL</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-base: #070B12; --bg-card: #0F172A; --border-color: #1E293B;
            --text-primary: #F8FAFC; --text-secondary: #94A3B8; --text-muted: #64748B;
            --neon-green: #22C55E; --neon-red: #EF4444; --neon-blue: #38BDF8; --neon-gold: #FACC15;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ background-color: var(--bg-base); color: var(--text-primary); font-family: 'Inter', sans-serif; padding: 16px; font-size: 14px; line-height: 1.5; }}
        .container {{ max-width: 1440px; margin: 0 auto; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; background: linear-gradient(135deg, #1C1917 0%, #292524 100%); border: 1px solid #44403C; border-radius: 12px; margin-bottom: 16px; flex-wrap: wrap; gap: 12px; }}
        .brand {{ display: flex; align-items: center; gap: 12px; }}
        .brand-title {{ font-size: 19px; font-weight: 800; background: linear-gradient(90deg, #FDE047 0%, #EAB308 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .pulse-dot {{ width: 10px; height: 10px; border-radius: 50%; background-color: #FACC15; box-shadow: 0 0 10px #FACC15; animation: pulse 2s infinite; }}
        @keyframes pulse {{ 0% {{ transform: scale(0.95); box-shadow: 0 0 0 0 rgba(250, 204, 21, 0.7); }} 70% {{ transform: scale(1); box-shadow: 0 0 0 8px rgba(250, 204, 21, 0); }} 100% {{ transform: scale(0.95); box-shadow: 0 0 0 0 rgba(250, 204, 21, 0); }} }}
        .badge {{ display: inline-block; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 700; font-family: 'JetBrains Mono', monospace; }}
        .badge-gold {{ background: rgba(234, 179, 8, 0.15); color: #FACC15; border: 1px solid rgba(234, 179, 8, 0.4); }}
        .badge-live {{ background: rgba(34, 197, 94, 0.15); color: #4ADE80; border: 1px solid rgba(34, 197, 94, 0.4); }}
        .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; margin-bottom: 18px; }}
        .kpi-card {{ background-color: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px; padding: 14px 18px; }}
        .kpi-label {{ font-size: 11px; font-weight: 600; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 4px; }}
        .kpi-val {{ font-size: 23px; font-weight: 700; font-family: 'JetBrains Mono', monospace; margin-bottom: 2px; }}
        .kpi-sub {{ font-size: 11.5px; color: var(--text-muted); }}
        .chart-box {{ background-color: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px; padding: 10px; margin-bottom: 18px; }}
        .table-box {{ background-color: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px; padding: 16px; margin-bottom: 18px; overflow-x: auto; }}
        .section-header {{ font-size: 15px; font-weight: 700; margin-bottom: 12px; color: #E2E8F0; display: flex; align-items: center; gap: 8px; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 12.5px; text-align: left; }}
        th {{ background-color: #111C33; color: var(--text-secondary); padding: 10px 12px; font-weight: 600; border-bottom: 1px solid var(--border-color); }}
        td {{ padding: 10px 12px; border-bottom: 1px solid #162238; font-family: 'JetBrains Mono', monospace; }}
        tr:hover td {{ background-color: #1E293B; }}
        .tag-buy {{ color: #4ADE80; font-weight: 700; }}
        .tag-sell {{ color: #F87171; font-weight: 700; }}
        .footer {{ text-align: center; font-size: 11.5px; color: var(--text-muted); padding: 16px 0; border-top: 1px solid var(--border-color); }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <div class="brand">
            <div class="pulse-dot"></div>
            <div class="brand-title">NEIRO-QUANT GOLD TERMINAL</div>
            <span class="badge badge-gold">CME GCZ26 LIVE</span>
            <span class="badge badge-live">100% CLOUD AUTOMATED</span>
        </div>
        <div style="font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #D6D3D1; display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
            <div>Cập nhật: <b>{now_str} (Giờ VN)</b> | Hạn: <b>{meta['expiration_date']} ({meta['dte_days']:.1f}d)</b></div>
            <button onclick="window.location.reload(true)" style="background: rgba(250, 204, 21, 0.15); border: 1px solid rgba(250, 204, 21, 0.4); color: #FACC15; border-radius: 6px; padding: 3px 8px; font-size: 11px; cursor: pointer; font-family: 'JetBrains Mono', monospace; font-weight: 600; display: inline-flex; align-items: center; gap: 4px; transition: all 0.2s;" onmouseover="this.style.background='rgba(250, 204, 21, 0.3)'" onmouseout="this.style.background='rgba(250, 204, 21, 0.15)'" title="Tải lại số liệu mới nhất">
                <span>&#x21bb;</span> Làm mới
            </button>
        </div>
    </div>

    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-label">Spot CME Futures ↔ Spot MT5 (Quy Đổi)</div>
            <div class="kpi-val" style="color: #FACC15;">${spot:,.2f} <span style="font-size: 16px; color: #38BDF8;">(MT5: ~${spot_mt5:,.2f})</span></div>
            <div class="kpi-sub">Trục ATM CME: <b>${meta['atm_strike']:,.0f}</b> | Basis MT5 Spot: <b>-{basis:.2f} USD</b></div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Market Regime & Net GEX</div>
            <div class="kpi-val" style="color: {'#4ADE80' if total_gex >= 0 else '#F87171'};">{total_gex:+.1f}M GEX</div>
            <div class="kpi-sub"><span class="badge badge-gold">{regime}</span></div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Biên Độ 1-Sigma Expected Move</div>
            <div class="kpi-val" style="color: #F59E0B;">±${expected_move:.2f}</div>
            <div class="kpi-sub">Intraday (Rule of 16): <b>±${intraday_move:.2f}</b> (${spot-intraday_move:.1f} - ${spot+intraday_move:.1f})</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Greeks Bậc 2 (Vanna & Charm)</div>
            <div class="kpi-val" style="color: #38BDF8;">{total_vex:+.1f}M / {total_chex:+.1f}M</div>
            <div class="kpi-sub">Net VEX ({total_vex:+.1f}M) | Net CHEX ({total_chex:+.1f}M/ngày)</div>
        </div>
    </div>

    <div class="chart-box">
        {plotly_div}
    </div>

    <div class="table-box" style="margin-bottom: 18px;">
        <div class="section-header" style="justify-content:space-between; flex-wrap:wrap;">
            <div style="display:flex; align-items:center; gap:8px;">
                <span>🧭</span> RADAR VI MÔ: TRẠNG THÁI CHỐT CHẶN & TÚI CHÂN KHÔNG (LEVEL STATE MACHINE - TẦNG 4)
            </div>
            <span class="badge badge-gold">AUTOMATED LEVEL STATE ENGINE</span>
        </div>
        <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap:10px;">
            {radar_cards_str}
        </div>
    </div>

    <div class="table-box">
        <div class="section-header">⚡ PHẦN 1: BẢNG TÁC CHIẾN LƯỚT SÓNG TRONG NGÀY (INTRADAY SCALPING - ĂN 20-25 GIÁ VÀNG)</div>
        <table>
            <thead>
                <tr>
                    <th>Chiến Lược</th>
                    <th>Vùng Kích Hoạt (CME)</th>
                    <th>Entry CME</th>
                    <th>MT5 Spot (~ -{basis:.1f}$)</th>
                    <th>Hard SL (CME)</th>
                    <th>Take Profit (TP)</th>
                    <th>Ghi Chú Hành Vi Market Maker & Túi Chân Không</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td class="tag-buy">1. BUY MUA ĐUỔI (Squeeze {strike_above:.0f})</td>
                    <td>Vượt > {strike_above + buffer_up:.2f}</td>
                    <td>{strike_above + buffer_up + 0.50:.2f}</td>
                    <td style="color:#38BDF8; font-weight:600;">~{strike_above + buffer_up + 0.50 - basis:.2f}</td>
                    <td style="color:#F87171;">{strike_above - 1.50:.2f} ($4.5)</td>
                    <td style="color:#4ADE80;">{squeeze_tp:.2f} ({squeeze_tp_note})</td>
                    <td>{squeeze_note}</td>
                </tr>
                <tr>
                    <td class="tag-sell">2. SELL CHẶN TIỀN TUYẾN (Fade {strike_above:.0f})</td>
                    <td>{strike_above - 1.50:.2f} - {strike_above:.2f}</td>
                    <td>{strike_above - 1.00:.2f}</td>
                    <td style="color:#38BDF8; font-weight:600;">~{strike_above - 1.00 - basis:.2f}</td>
                    <td style="color:#F87171;">{strike_above + buffer_up + 1.50:.2f} ($5.0)</td>
                    <td style="color:#4ADE80;">{spot:.2f}</td>
                    <td>Cản Vol cực đại -> MM bán Futures chặn đầu ghìm giá hồi về Spot</td>
                </tr>
                <tr>
                    <td class="tag-buy">3. BUY BẮT SÀN ATM (Rebound {strike_below:.0f})</td>
                    <td>{strike_below:.2f} - {strike_below + 1.50:.2f}</td>
                    <td>{strike_below + 1.00:.2f}</td>
                    <td style="color:#38BDF8; font-weight:600;">~{strike_below + 1.00 - basis:.2f} (Vùng ~{spot_mt5:.0f})</td>
                    <td style="color:#F87171;">{strike_below - 4.00:.2f} ($5.0)</td>
                    <td style="color:#4ADE80;">{strike_above - front_run_tp:.2f}</td>
                    <td>Đệm Put hỗ trợ kỹ thuật trong phiên đẩy giá hồi phục (chỉ vào khi có nến rút chân xác nhận)</td>
                </tr>
                <tr>
                    <td class="tag-sell">4. SELL THỦNG SÀN & VACUUM RUN (Breakdown {strike_below:.0f})</td>
                    <td>Thủng < {strike_below - buffer_down:.2f}</td>
                    <td>{strike_below - buffer_down - 0.50:.2f}</td>
                    <td style="color:#38BDF8; font-weight:600;">~{strike_below - buffer_down - 0.50 - basis:.2f}</td>
                    <td style="color:#F87171;">{strike_below + 1.50:.2f} ($4.5)</td>
                    <td style="color:#4ADE80;">{breakdown_tp:.2f} ({breakdown_tp_note})</td>
                    <td>{breakdown_note}</td>
                </tr>
            </tbody>
        </table>
    </div>

    <div class="table-box">
        <div class="section-header">🏰 PHẦN 2: BẢNG TÁC CHIẾN PHỤC KÍCH THÀNH TRÌ (STRUCTURAL SWING WALLS - ĐÁNH SÓNG LỚN)</div>
        <table>
            <thead>
                <tr>
                    <th>Chiến Lược</th>
                    <th>Vùng Kích Hoạt (CME)</th>
                    <th>Entry CME</th>
                    <th>MT5 Spot (~ -{basis:.1f}$)</th>
                    <th>Hard SL (CME)</th>
                    <th>Take Profit (TP)</th>
                    <th>Ghi Chú Cấu Trúc Khối Lượng</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td class="tag-sell">5. BÁN ĐỈNH CALL WALL ({call_wall:.0f})</td>
                    <td>{call_wall - 1.50:.2f} - {call_wall:.2f}</td>
                    <td>{call_wall - 1.00:.2f}</td>
                    <td style="color:#38BDF8; font-weight:600;">~{call_wall - 1.00 - basis:.2f}</td>
                    <td style="color:#F87171;">{call_wall + 4.00:.2f} ($4.0)</td>
                    <td style="color:#4ADE80;">{strike_above:.2f} / {spot:.2f}</td>
                    <td>Call Wall {call_wall_oi:,} OI (Nóc nhà kiên cố cuối cùng của MM)</td>
                </tr>
                <tr>
                    <td class="tag-buy">6. MUA ĐÁY PUT WALL ({put_wall:.0f})</td>
                    <td>{put_wall:.2f} - {put_wall + 1.50:.2f}</td>
                    <td>{put_wall + 0.50:.2f}</td>
                    <td style="color:#38BDF8; font-weight:600;">~{put_wall + 0.50 - basis:.2f}</td>
                    <td style="color:#F87171;">{put_wall - 4.00:.2f} ($4.0)</td>
                    <td style="color:#4ADE80;">{spot:.2f} / {strike_above:.2f}</td>
                    <td>Major Put Wall {put_wall_oi:,} OI (Đáy bê tông cốt thép của MM)</td>
                </tr>
            </tbody>
        </table>
    </div>

    <div class="footer">
        NEIRO-QUANT HEDGE FUND QUANTITATIVE SYSTEM &bull; 100% CME GOLD FUTURES & OPTIONS FLOW
    </div>
</div>
</body>
</html>
"""
    return html


def run_pipeline(input_csv: str = "data/options_prices_GCZ26.csv", output_files: list[str] | None = None, basis: float | None = None) -> list[str]:
    if output_files is None:
        output_files = [
            "exports/latest_gold_dashboard.html",
            "exports/index.html",
        ]

    df_raw, meta = load_and_preprocess_options(input_csv, basis=basis)
    fig = build_plotly_figure(df_raw, meta)
    html_content = generate_html_terminal(df_raw, meta, fig)

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

    return saved_paths


def main():
    parser = argparse.ArgumentParser(description="Neiro-Quant Tactical HTML Dashboard Generator")
    parser.add_argument("--input", default="data/options_prices_GCZ26.csv", help="Input options CSV")
    parser.add_argument("--output", nargs="+", default=["exports/latest_gold_dashboard.html", "exports/index.html"], help="Output HTML paths")
    parser.add_argument("--basis", type=float, default=None, help="Dynamic Basis Spread (Futures - Spot XAUUSD, auto-resolves live if omitted)")
    args = parser.parse_args()

    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    saved = run_pipeline(input_csv=args.input, output_files=args.output, basis=args.basis)
    print(f"[SUCCESS] Generated {len(saved)} dashboard files:")
    for s in saved:
        print(f"   -> {s}")


if __name__ == "__main__":
    main()
