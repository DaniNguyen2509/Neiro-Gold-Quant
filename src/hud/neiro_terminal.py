"""src/hud/neiro_terminal.py

High-Fidelity All-in-One NEIRO Orderflow Footprint Terminal Component for COMEX Gold (GC / MGC).
Standardized 1:1 against the authentic Neiro-NQ-Quant tactical trading cockpit:
- 100% Fullscreen TradingView Cockpit with Live M1 Candlesticks
- Floating Quant HUD Card at Top-Left (NET GEX, SQZ Up/Down, VANNA, CHARM, THETA, 1-SIGMA)
- Authentic Topbar & Subbar with Live Black-76 Greeks Radar
- 4-Column Per-Strike Greeks Profile on Chart Canvas: GEX | VEX | CHEX | THETA
- Pinned Edge Indicators for Key Boundary Walls (CALL WALL, PUT WALL, GAMMA FLIP, CHARM, VANNA)
- Realtime Tick Engine (Zero Reload, Zero Lag)
- Zero-Waste Compliant (< 15MB).
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any
import pandas as pd


def render_neiro_orderflow_component(meta: dict[str, Any], df: pd.DataFrame) -> dict[str, str]:
    """Generates HTML, CSS, and JS artifacts for Neiro-Quant Tactical Gold Cockpit."""
    spot = float(meta.get("spot_price", 3898.90))
    atm_strike = float(meta.get("atm_strike", spot))
    call_wall = float(meta.get("call_wall", spot + 100.0))
    put_wall = float(meta.get("put_wall", spot - 100.0))
    call_wall_oi = int(meta.get("call_wall_oi", 0))
    put_wall_oi = int(meta.get("put_wall_oi", 0))
    call_wall_siege = float(meta.get("call_wall_siege", 0.0))
    put_wall_siege = float(meta.get("put_wall_siege", 0.0))
    total_gex = float(meta.get("total_net_gex", 0.0))
    total_vex = float(meta.get("total_net_vex", 0.0))
    total_chex = float(meta.get("total_net_chex", 0.0))
    total_thex = float(meta.get("total_theta", -19.9) or -19.9)
    total_vega = float(meta.get("total_vega", total_vex) or total_vex)
    atm_delta = float(meta.get("atm_delta", 0.505) or 0.505)
    atm_gamma = float(meta.get("atm_gamma", 0.00042) or 0.00042)
    total_thex_display = f"${total_thex:+.1f}M/d" if abs(total_thex) >= 1.0 else f"${total_thex*1000:+.0f}k/d"
    expected_move = float(meta.get("expected_move_1s", 35.0))
    strike_above = float(meta.get("strike_above", spot + 20.0))
    next_above = float(meta.get("next_above", strike_above + 20.0))
    strike_below = float(meta.get("strike_below", spot - 20.0))
    next_below = float(meta.get("next_below", strike_below - 20.0))
    zero_gamma = float(meta.get("zero_gamma_flip", spot))
    gvz_iv = float(meta.get("gvz_iv") or (float(meta.get("sigma_atm", 0.241)) * 100.0))
    air_pockets = meta.get("air_pockets", [])

    total_net_delta = float(meta.get("total_net_delta_contracts", 0.0) or (df["netDeltaContracts"].sum() if "netDeltaContracts" in df.columns else 0.0))
    total_vol = int(df["callVolume"].sum() + df["putVolume"].sum()) if ("callVolume" in df.columns and "putVolume" in df.columns) else 0
    total_oi = int(df["callOpenInterest"].sum() + df["putOpenInterest"].sum()) if ("callOpenInterest" in df.columns and "putOpenInterest" in df.columns) else 0

    regime_color = "#4ADE80" if total_gex >= 0 else "#F87171"
    regime_text = "POSITIVE GAMMA (LONG MM)" if total_gex >= 0 else "NEGATIVE GAMMA (SHORT MM)"

    inst_flow = meta.get("institutional_orderflow") or {}
    per_strike_flow = inst_flow.get("per_strike_flow") or {}
    f_opt_val = float(inst_flow.get("implied_forward_price", spot))
    delta_f_val = float(inst_flow.get("forward_dislocation_usd", 0.0))
    disloc_label = str(inst_flow.get("dislocation_label", "CÂN BẰNG PARITY"))
    dealer_hedge_val = float(inst_flow.get("dealer_hedge_futures_flow", 0.0))
    opt_flow_label = str(inst_flow.get("options_flow_label", "CÂN BẰNG HEDGING"))
    bvc_cvd_val = float(inst_flow.get("bvc_cvd_contracts", 0.0))
    bvc_buy_pct = float(inst_flow.get("bvc_buy_pct", 50.0))
    kyle_label = str(inst_flow.get("kyle_lambda_label", "THANH KHOẢN BÌNH THƯỜNG"))
    vpin_pct = float(inst_flow.get("vpin_pct", 35.0))
    vpin_label = str(inst_flow.get("vpin_label", f"🟢 VPIN AN TOÀN ({vpin_pct:.1f}% < 40%)"))
    vrp_label = str(inst_flow.get("vrp_label", "⚖️ VRP CÂN BẰNG"))
    informed_badge = str(inst_flow.get("informed_action_badge", "🟢 AN TOÀN ĐÁNH ĐẢO CHIỀU TẠI WALL"))
    informed_col = str(inst_flow.get("informed_action_color", "#4ADE80"))
    rho_vs = float(inst_flow.get("bayesian_conviction_rho", 0.50))
    kelly_mult = float(inst_flow.get("kelly_fraction_mult", 0.75))
    vpin_col = "#F87171" if vpin_pct >= 65.0 else ("#FACC15" if vpin_pct >= 40.0 else "#4ADE80")
    flip_verdict_lbl = str(inst_flow.get("flip_integrity_label", "⚖️ ĐANG KIỂM ĐỊNH TRỤC GAMMA FLIP"))
    flip_verdict_col = str(inst_flow.get("flip_integrity_color", "#FACC15"))
    dyn_vac = inst_flow.get("dynamic_vacuum") or {}
    inst_fvgs = inst_flow.get("institutional_fvgs") or []
    post_sweep = inst_flow.get("post_sweep_execution") or {}
    post_sweep_regime = str(post_sweep.get("post_sweep_regime", "MONITORING"))
    post_sweep_label = str(post_sweep.get("label_vi", "THEO DÕI — CHỜ QUÉT & HẤP THỤ TẠI WALL"))
    vac_label = str(dyn_vac.get("label_vi", "ĐỘ SÂU THỊ TRƯỜNG ỔN ĐỊNH"))
    post_sweep_col = (
        "#F87171" if post_sweep_regime == "TOXIC_CASCADE_BLOCKED"
        else ("#4ADE80" if post_sweep_regime == "POST_SWEEP_V_SHAPE"
              else ("#38BDF8" if post_sweep_regime == "POST_SWEEP_PULLBACK" else "#94A3B8"))
    )
    disloc_color = "#4ADE80" if delta_f_val >= 1.50 else ("#F87171" if delta_f_val <= -1.50 else "#38BDF8")
    hedge_color = "#4ADE80" if dealer_hedge_val > 50.0 else ("#F87171" if dealer_hedge_val < -50.0 else "#FACC15")
    cvd_color = "#4ADE80" if bvc_cvd_val >= 0 else "#F87171"

    # Identify Peak Vanna & Peak Charm strikes before corridor pruning
    vanna_peak_strike = float(meta.get("vanna_peak_strike") or 0.0)
    vanna_peak_val = float(meta.get("vanna_peak_val") or 0.0)
    charm_peak_strike = float(meta.get("charm_peak_strike") or 0.0)
    charm_peak_val = float(meta.get("charm_peak_val") or 0.0)

    if (vanna_peak_strike == 0.0 or charm_peak_strike == 0.0) and not df.empty:
        if "netVEX" in df.columns:
            vex_s = df["netVEX"].abs()
            if not vex_s.empty and vex_s.max() > 0:
                v_idx = vex_s.idxmax()
                vanna_peak_strike = float(df.loc[v_idx, "strike"])
                vanna_peak_val = float(df.loc[v_idx, "netVEX"])
        if "netCHEX" in df.columns:
            chex_s = df["netCHEX"].abs()
            if not chex_s.empty and chex_s.max() > 0:
                ch_idx = chex_s.idxmax()
                charm_peak_strike = float(df.loc[ch_idx, "strike"])
                charm_peak_val = float(df.loc[ch_idx, "netCHEX"])

    key_landmarks = (
        call_wall,
        put_wall,
        zero_gamma,
        atm_strike,
        vanna_peak_strike,
        charm_peak_strike,
        float(meta.get("major_call_oi_wall") or 0.0),
        float(meta.get("major_put_oi_wall") or 0.0),
    )

    def _in_active_corridor(k_val: float) -> bool:
        return abs(k_val - spot) <= 600.0 or any(lm > 0.0 and abs(k_val - lm) <= 25.0 for lm in key_landmarks)

    compact_ladder = []
    for k_raw, lvl in sorted((meta.get("squeeze_ladder") or {}).items(), key=lambda kv: float(kv[0])):
        k_flt = float(k_raw)
        if not _in_active_corridor(k_flt):
            continue
        sq_tr = getattr(lvl, "squeeze_trigger", lvl.get("squeeze_trigger") if isinstance(lvl, dict) else 0.0)
        sq_tp = getattr(lvl, "squeeze_tp", lvl.get("squeeze_tp") if isinstance(lvl, dict) else 0.0)
        wf_tr = getattr(lvl, "waterfall_trigger", lvl.get("waterfall_trigger") if isinstance(lvl, dict) else 0.0)
        wf_tp = getattr(lvl, "waterfall_tp", lvl.get("waterfall_tp") if isinstance(lvl, dict) else 0.0)
        compact_ladder.append({
            "k": round(k_flt, 2),
            "sq_tr": round(float(sq_tr), 2),
            "sq_tp": round(float(sq_tp), 2),
            "wf_tr": round(float(wf_tr), 2),
            "wf_tp": round(float(wf_tp), 2),
        })

    # 1. CSS styling cloned 1:1 from Neiro-NQ-Quant Tactical Cockpit
    neiro_css = """
    /* Neiro Desktop Window Styles */
    .neiro-win-topbar {
        height: 34px; background: #161A22; border-bottom: 1px solid #232A37;
        display: flex; align-items: center; justify-content: space-between;
        padding: 0 8px; font-family: 'JetBrains Mono', monospace; font-size: 11px;
        flex-shrink: 0;
    }
    .neiro-top-left, .neiro-top-center, .neiro-top-right {
        display: flex; align-items: center; gap: 5px;
    }
    .neiro-blue-indicator {
        width: 4px; height: 18px; background: #0284C7; border-radius: 2px; margin-right: 3px;
    }
    .neiro-tab {
        background: #202632; border: 1px solid #2F3849; color: #FFFFFF;
        padding: 3px 9px; border-radius: 4px; font-weight: 700; font-size: 11px;
        cursor: pointer;
    }
    .neiro-tab.active {
        background: #252D3C; border-color: #38BDF8; color: #FFFFFF;
    }
    .neiro-win-sep { color: #3A4556; margin: 0 2px; font-size: 11px; }
    .neiro-tf-group { display: flex; align-items: center; gap: 2px; }
    .timeframe-pill {
        background: transparent; color: #94A3B8; border: 1px solid transparent;
        padding: 2px 6px; border-radius: 3px; font-size: 11px; cursor: pointer; font-weight: 600;
        font-family: 'JetBrains Mono', monospace;
    }
    .timeframe-pill.active, .timeframe-pill:hover {
        background: #2A3444; color: #38BDF8; border-color: #38BDF8;
    }
    .neiro-badge-contract {
        background: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189, 248, 0.4);
        color: #38BDF8; padding: 2px 6px; border-radius: 3px; font-size: 10.5px; font-weight: 700;
    }
    .neiro-quant-pill {
        display: flex; align-items: center; gap: 6px; background: #10141C;
        border: 1px solid #1E2635; padding: 2px 8px; border-radius: 4px; font-size: 10.5px;
    }
    .neiro-sym-label { color: #64748B; font-size: 10px; font-weight: 600; }
    .neiro-price-val { font-size: 12px; font-weight: 800; }
    .ticker-change { font-size: 10px; font-weight: 600; padding: 1px 4px; border-radius: 2px; }
    .change-up { color: #4ADE80; background: rgba(34, 197, 94, 0.12); }
    .change-down { color: #F87171; background: rgba(239, 68, 68, 0.12); }
    .neiro-pill-lbl { color: #64748B; font-size: 9.5px; }

    /* Subbar Watermark & Radar */
    .neiro-win-subbar {
        height: 22px; background: #0B0E14; border-bottom: 1px solid #161D29;
        display: flex; align-items: center; justify-content: space-between;
        padding: 0 10px; font-family: 'JetBrains Mono', monospace; font-size: 10px;
        flex-shrink: 0;
    }
    .neiro-watermark-text { color: #475569; font-size: 9.5px; }

    /* Chart & Canvas View */
    .neiro-body-container {
        display: flex; flex: 0 0 auto; width: 100%; height: 540px;
        position: relative; overflow: hidden; background: #000000;
        border: 1px solid #1E293B; border-radius: 6px; margin-bottom: 10px;
    }
    .neiro-body-container.expanded { height: 700px; }
    #tv-chart-wrapper {
        position: relative; width: 100%; height: 100%; background-color: #000000;
    }
    #neiro-tv-chart { width: 100%; height: 100%; }
    #neiro-canvas {
        position: absolute; top: 0; left: 0; width: 100%; height: 100%;
        pointer-events: none; z-index: 5;
    }

    /* Compact Floating Quant HUD Card (5 Core Signals - Top-Left of Chart) */
    .neiro-floating-hud {
        position: absolute; top: 10px; left: 12px; z-index: 10;
        display: flex; flex-direction: column; gap: 3px;
        background: rgba(8, 11, 18, 0.88); border: 1px solid #1E293B; border-radius: 5px;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.55);
        padding: 6px 10px; font-family: 'JetBrains Mono', monospace; font-size: 10.5px;
        max-width: min(430px, calc(100% - 24px)); pointer-events: none;
    }
    .hud-item { display: flex; align-items: center; gap: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .hud-label { color: #94A3B8; font-weight: 700; font-size: 10px; min-width: 112px; }

    @media (max-width: 1180px) {
        .neiro-win-topbar {
            height: auto; min-height: 34px; flex-wrap: wrap; gap: 6px; padding: 6px 8px;
        }
        .neiro-top-left, .neiro-top-center, .neiro-top-right {
            flex-wrap: wrap; max-width: 100%; min-width: 0;
        }
        .neiro-quant-pill {
            flex-wrap: wrap; max-width: 100%; min-width: 0;
        }
    }
    @media (max-width: 768px) {
        .neiro-win-subbar {
            height: auto; flex-wrap: wrap; gap: 4px; padding: 4px 10px;
        }
        .neiro-floating-hud { padding: 5px 8px; }
        .hud-label { min-width: 84px; }
    }
    """

    # 2. Navigation Topbar HTML (Exact 1:1 Neiro-NQ-Quant layout)
    nav_topbar_html = f"""
    <div class="neiro-win-topbar">
        <div class="neiro-top-left">
            <span class="neiro-blue-indicator"></span>
            <div class="neiro-tab active" id="tab-neiro" onclick="switchTerminalView('neiro')"><span class="neiro-tab-text">NEIRO ORDERFLOW</span></div>
            <span class="neiro-win-sep">|</span>
            <div class="neiro-tf-group">
                <button class="timeframe-pill active" onclick="setTimeframe('1m')">1M</button>
                <button class="timeframe-pill" onclick="setTimeframe('5m')">5M</button>
                <button class="timeframe-pill" onclick="setTimeframe('15m')">15M</button>
                <button class="timeframe-pill" onclick="setTimeframe('1h')">1H</button>
                <button class="timeframe-pill" onclick="setTimeframe('d')">1D</button>
            </div>
            <span class="neiro-badge-contract" id="neiro-tf-badge">M1 INTRADAY</span>
        </div>

        <!-- Center: Quantitative Metrics Pill -->
        <div class="neiro-top-center">
            <div class="neiro-quant-pill">
                <span class="neiro-sym-label">SPOT CME:</span>
                <b class="neiro-price-val" id="top-ticker-price" style="color: #38BDF8;">${spot:,.2f}</b>
                <span class="ticker-change change-up" id="top-ticker-change">+0.00 (+0.00%)</span>
                <span class="neiro-win-sep">|</span>
                <span class="neiro-pill-lbl">GEX:</span> <b id="kpi-gex-val" style="color:{regime_color};">${total_gex:+.1f}M</b>
                <span class="neiro-pill-lbl">VPIN:</span> <b id="top-vpin-val" style="color:{vpin_col};">{vpin_pct:.1f}%</b>
                <span class="neiro-win-sep">|</span>
                <span class="neiro-pill-lbl">CVD:</span> <b id="top-cvd-val" style="color:{cvd_color};">{bvc_cvd_val:+.0f} HĐ ({bvc_buy_pct:.0f}%B)</b>
                <span class="neiro-pill-lbl">MM HEDGE:</span> <b id="top-hedge-val" style="color:{hedge_color};">{dealer_hedge_val:+.0f} GC</b>
            </div>
        </div>

        <div class="neiro-top-right">
            <button id="btn-overlay-mode" class="timeframe-pill" onclick="toggleOverlayMode()" title="Chuyển lớp phủ Chart: Tinh gọn (3 đường cấu trúc + Entry/SL/TP) hoặc Đầy đủ (thêm Vanna, Charm, FVG, Air Pocket)">
                Lớp phủ: Tinh gọn
            </button>
            <button id="btn-chart-height" class="timeframe-pill" onclick="toggleChartHeight()" title="Phóng to hoặc thu gọn chiều cao biểu đồ">
                Mở rộng Chart
            </button>
            <span class="neiro-badge-contract" id="cloud-sync-badge" style="background:rgba(148,163,184,0.16); border-color:rgba(148,163,184,0.4); color:#CBD5E1; font-size:10px; cursor:pointer;" title="Trạng thái đồng bộ realtime. Bấm để kiểm tra ngay." onclick="checkCloudSyncNow(true)">
                ● SNAPSHOT BUILD
            </span>
            <span id="sync-time-ago" style="color:#94A3B8; font-size:10px; margin-right:4px;">(vừa nạp)</span>
            <button onclick="clearHistoryAndCache()" style="background:rgba(239,68,68,0.15); border:1px solid rgba(239,68,68,0.4); color:#F87171; border-radius:3px; padding:2px 6px; font-size:10px; cursor:pointer; font-family:'JetBrains Mono',monospace; font-weight:600;" title="Dọn RAM & Cache">
                Dọn RAM
            </button>
        </div>
    </div>

    <!-- Authentic Greeks Subbar -->
    <div class="neiro-win-subbar">
        <div class="neiro-subbar-left">
            <span class="neiro-watermark-text" style="color:#38BDF8; font-weight:700;">NEIRO-QUANT TERMINAL &bull; CME GOLD FUTURES [GC=F / GCZ26]</span>
        </div>
        <div class="neiro-subbar-right">
            <span style="color:#64748B;">ATM: <b id="top-ticker-atm">${atm_strike:,.0f}</b> | IV: <b id="top-ticker-iv">{gvz_iv:.1f}%</b> | Zero Gamma: <b style="color:#FACC15;">${zero_gamma:,.1f}</b> | 1-&sigma;: <b id="kpi-move-val" style="color:#FACC15;">&plusmn;${expected_move:,.1f}</b></span>
        </div>
    </div>
    """

    # 3. Main M1 Chart Body with Compact 5-Line Floating Tactical HUD
    neiro_container_html = f"""
    <div class="neiro-body-container" id="neiro-view-container">
        <div id="tv-chart-wrapper">
            <!-- Compact 5-Line Quant HUD Card at Top-Left of Chart -->
            <div class="neiro-floating-hud">
                <div class="hud-item">
                    <span class="hud-label">REGIME / FLIP:</span>
                    <b id="hud-gex-val" style="color:{regime_color};">${total_gex:+.1f}M</b>
                    <span style="color:#64748B;">&bull;</span>
                    <span id="hud-flip-verdict-box" style="border-left:2px solid {flip_verdict_col}; padding-left:5px;">
                        <b id="hud-flip-verdict" style="color:{flip_verdict_col}; font-size:10px;">{flip_verdict_lbl}</b>
                    </span>
                </div>
                <div class="hud-item"><span class="hud-label">GAMMA SQUEEZE &uarr;:</span> <b id="hud-sqz-up" style="color:#4ADE80;">&gt; ${strike_above:,.0f} &rarr; TP ${next_above:,.0f}</b></div>
                <div class="hud-item"><span class="hud-label">GAMMA SQUEEZE &darr;:</span> <b id="hud-sqz-down" style="color:#F87171;">&lt; ${strike_below:,.0f} &rarr; TP ${next_below:,.0f}</b></div>
                <div class="hud-item" style="flex-wrap:nowrap;">
                    <span class="hud-label">VPIN &amp; BVC:</span>
                    <b id="hud-vpin-val" style="color:{vpin_col}; font-size:10px;">{vpin_label}</b>
                    <span style="color:#64748B;">&bull;</span>
                    <b id="hud-cvd-val" style="color:{cvd_color}; font-size:10px;">{bvc_cvd_val:+,.0f} HĐ | {bvc_buy_pct:.1f}% MUA</b>
                </div>
                <div style="width:100%; height:4px; background:#EF4444; border-radius:2px; overflow:hidden;">
                    <div id="hud-bvc-bar" style="width:{bvc_buy_pct:.1f}%; height:100%; background:#22C55E; transition:width 0.12s linear;"></div>
                </div>
                <div class="hud-item">
                    <span class="hud-label">POST-SWEEP / KYLE:</span>
                    <b id="hud-post-sweep-val" style="color:{post_sweep_col}; font-size:10px;" title="{vac_label}">{post_sweep_label}</b>
                    <span style="color:#64748B;">&bull;</span>
                    <b id="hud-kyle-val" style="color:#38BDF8; font-size:9.5px;">{kyle_label}</b>
                </div>
            </div>
            <div id="neiro-tv-chart"></div>
            <canvas id="neiro-canvas"></canvas>
        </div>
    </div>
    """

    # 4. JSON metadata & strikes for JavaScript engine (trimmed to active corridor + landmarks)
    js_options_data = []
    if not df.empty and "strike" in df.columns:
        df_sorted_js = df.sort_values("strike")
        for r in df_sorted_js.to_dict("records"):
            try:
                stk_num = float(r["strike"])
                if not _in_active_corridor(stk_num):
                    continue
                c_oi_val = int(r.get("callOpenInterest", 0) or 0)
                p_oi_val = int(r.get("putOpenInterest", 0) or 0)
                c_vol_val = int(r.get("callVolume", 0) or 0)
                p_vol_val = int(r.get("putVolume", 0) or 0)
                c_delta_val = float(r.get("callDelta", 0.0) or 0.0)
                p_delta_val = float(r.get("putDelta", 0.0) or 0.0)
                net_delta_val = float(r.get("netDeltaContracts", 0.0) or (c_oi_val * c_delta_val + p_oi_val * p_delta_val))
                gex_val = float(r.get("netGEX", 0.0) or 0.0)
                vex_val = float(r.get("netVEX", 0.0) or 0.0)
                chex_val = float(r.get("netCHEX", 0.0) or 0.0)
                theta_val = float(r.get("totalTheta", 0.0) or 0.0)

                sf = per_strike_flow.get(round(stk_num, 1)) or {}
                dh_gc_val = float(sf.get("dealer_hedge_gc", 0.0) or 0.0)
                s_call_val = float(sf.get("signed_call", 0.0) or 0.0)
                s_put_val = float(sf.get("signed_put", 0.0) or 0.0)
                is_whale_val = bool(sf.get("is_whale_new_oi", False))
                dom_flow_val = str(sf.get("dominant_flow", ""))

                js_options_data.append({
                    "strike": round(stk_num, 1),
                    "c_oi": c_oi_val,
                    "p_oi": p_oi_val,
                    "c_vol": c_vol_val,
                    "p_vol": p_vol_val,
                    "c_iv": round(float(r.get("callIV", 0.18) or 0.18), 4),
                    "p_iv": round(float(r.get("putIV", 0.18) or 0.18), 4),
                    "c_delta": round(c_delta_val, 4),
                    "p_delta": round(p_delta_val, 4),
                    "c_gamma": round(float(r.get("callGamma", 0.0) or 0.0), 6),
                    "p_gamma": round(float(r.get("putGamma", 0.0) or 0.0), 6),
                    "netGEX": round(gex_val, 3),
                    "netDelta": round(net_delta_val, 3),
                    "netVEX": round(vex_val, 3),
                    "netCHEX": round(chex_val, 3),
                    "currentNetFLOW": round(dh_gc_val, 3),
                    "signedCall": round(s_call_val, 3),
                    "signedPut": round(s_put_val, 3),
                    "isWhale": is_whale_val,
                    "dominantFlow": dom_flow_val,
                    "currentNetGEX": round(gex_val, 3),
                    "currentNetVEX": round(vex_val, 3),
                    "currentNetCHEX": round(chex_val, 3),
                    "currentNetTEX": round(theta_val, 3),
                })
            except Exception:
                continue

    raw_m5_tape = meta.get("m5_tape")
    m5_tape = raw_m5_tape if isinstance(raw_m5_tape, dict) else {}
    chart_candles = m5_tape.get("chart_candles") or []
    tf_candles = m5_tape.get("tf_candles") or {}
    market_open_flag = bool(m5_tape.get("market_open", True))

    regime_val = str(meta.get("regime") or ("LONG_GAMMA" if total_gex > 10.0 else ("SHORT_GAMMA" if total_gex < -10.0 else "NEUTRAL")))
    dte_days_val = float(meta.get("dte_days") or 8.0)
    step_val = float(meta.get("step") or 25.0)
    atr_5m_val = float(meta.get("atr_5m") or 4.0)
    major_up_wall_val = float(meta.get("major_up_wall") or call_wall)
    major_down_wall_val = float(meta.get("major_down_wall") or put_wall)
    has_up_ap_val = bool(meta.get("has_up_air_pocket", bool(air_pockets)))
    has_down_ap_val = bool(meta.get("has_down_air_pocket", bool(air_pockets)))
    session_name_val = str(inst_flow.get("session_name") or ("GLOBEX_CLOSED" if not market_open_flag else "NY_COMEX_DEEP"))

    json_options_str = json.dumps(js_options_data)
    build_ts_utc = str(meta.get("timestamp_utc") or datetime.now(timezone.utc).isoformat())
    json_meta_str = json.dumps({
        "timestamp_utc": build_ts_utc,
        "spot": spot,
        "market_open": market_open_flag,
        "regime": regime_val,
        "dte_days": dte_days_val,
        "step": step_val,
        "atr_5m": atr_5m_val,
        "major_up_wall": major_up_wall_val,
        "major_down_wall": major_down_wall_val,
        "has_up_air_pocket": has_up_ap_val,
        "has_down_air_pocket": has_down_ap_val,
        "session_name": session_name_val,
        "atm_strike": atm_strike,
        "call_wall": call_wall,
        "call_wall_oi": call_wall_oi,
        "call_wall_siege": call_wall_siege,
        "put_wall": put_wall,
        "put_wall_oi": put_wall_oi,
        "put_wall_siege": put_wall_siege,
        "total_net_gex": total_gex,
        "total_net_vex": total_vex,
        "total_net_chex": total_chex,
        "expected_move_1s": expected_move,
        "strike_above": strike_above,
        "next_above": next_above,
        "strike_below": strike_below,
        "next_below": next_below,
        "zero_gamma_flip": zero_gamma,
        "vanna_peak_strike": vanna_peak_strike,
        "vanna_peak_val": vanna_peak_val,
        "charm_peak_strike": charm_peak_strike,
        "charm_peak_val": charm_peak_val,
        "multiplier": 100.0,
        "air_pockets": air_pockets,
        "implied_forward_price": f_opt_val,
        "forward_dislocation_usd": delta_f_val,
        "dealer_hedge_futures_flow": dealer_hedge_val,
        "bvc_cvd_contracts": bvc_cvd_val,
        "bvc_buy_pct": bvc_buy_pct,
        "kyle_lambda_label": kyle_label,
        "vpin_pct": vpin_pct,
        "vpin_label": vpin_label,
        "vrp_label": vrp_label,
        "informed_action_badge": informed_badge,
        "informed_action_color": informed_col,
        "flip_integrity_label": flip_verdict_lbl,
        "flip_integrity_color": flip_verdict_col,
        "squeeze_ladder": compact_ladder,
        "dynamic_vacuum": dyn_vac,
        "institutional_fvgs": inst_fvgs,
        "post_sweep_execution": post_sweep,
    })

    json_candles_str = json.dumps(chart_candles)
    json_tf_candles_str = json.dumps(tf_candles)

    # 5. JavaScript Orderflow & Dual-View Engine (All-in-One Rendering 1:1 Neiro-NQ-Quant)
    neiro_js_script = f"""
    <script>
    window.INITIAL_OPTIONS = {json_options_str};
    window.INITIAL_META = {json_meta_str};
    window.INITIAL_CANDLES = {json_candles_str};
    window.INITIAL_TF_CANDLES = {json_tf_candles_str};

    let neiroChart = null;
    let candleSeries = null;
    let livePriceLine = null;
    let vannaPriceLine = null;
    let charmPriceLine = null;
    let currentGoldPrice = window.INITIAL_META.spot;
    let yahooAnchorPrice = window.INITIAL_META.spot;
    let currentTf = '1m';
    let currentPeriodSec = 60;
    let overlayCompactMode = true;
    let chartExpanded = false;
    let liveTacticalMatrix = null;
    let lastBridgeSuccessEpoch = 0;
    let lastCloudSuccessEpoch = 0;
    let lastAuthoritativeVpinEpoch = 0;
    let liveVpinPct = Number(window.INITIAL_META.vpin_pct || 32.0);
    let liveVpinLabel = String(window.INITIAL_META.vpin_label || '🟢 VPIN 32.0% [AN TOÀN FADE WALL]');
    let liveAtr5m = Number(window.INITIAL_META.atr_5m || 4.0);

    function toggleOverlayMode() {{
        overlayCompactMode = !overlayCompactMode;
        const btn = document.getElementById('btn-overlay-mode');
        if (btn) {{
            btn.innerText = overlayCompactMode ? 'Lớp phủ: Tinh gọn' : 'Lớp phủ: Đầy đủ';
            btn.classList.toggle('active', !overlayCompactMode);
        }}
        syncSecondaryPriceLines();
        requestAnimationFrame(drawNeiroOverlay);
    }}

    function toggleChartHeight() {{
        chartExpanded = !chartExpanded;
        const box = document.getElementById('neiro-view-container');
        const btn = document.getElementById('btn-chart-height');
        if (box) box.classList.toggle('expanded', chartExpanded);
        if (btn) btn.innerText = chartExpanded ? 'Thu gọn Chart' : 'Mở rộng Chart';
        window.dispatchEvent(new Event('resize'));
    }}

    function syncSecondaryPriceLines() {{
        if (!candleSeries) return;
        const m = window.INITIAL_META || {{}};
        if (!overlayCompactMode) {{
            if (!vannaPriceLine && m.vanna_peak_strike) {{
                vannaPriceLine = candleSeries.createPriceLine({{
                    price: m.vanna_peak_strike,
                    color: '#22D3EE',
                    lineWidth: 1.5,
                    lineStyle: LightweightCharts.LineStyle.Dashed,
                    axisLabelVisible: true,
                    title: 'VANNA (VEX)',
                }});
            }}
            if (!charmPriceLine && m.charm_peak_strike) {{
                charmPriceLine = candleSeries.createPriceLine({{
                    price: m.charm_peak_strike,
                    color: '#C084FC',
                    lineWidth: 1.5,
                    lineStyle: LightweightCharts.LineStyle.Dashed,
                    axisLabelVisible: true,
                    title: 'CHARM (CHEX)',
                }});
            }}
        }} else {{
            if (vannaPriceLine) {{
                try {{ candleSeries.removePriceLine(vannaPriceLine); }} catch (e) {{}}
                vannaPriceLine = null;
            }}
            if (charmPriceLine) {{
                try {{ candleSeries.removePriceLine(charmPriceLine); }} catch (e) {{}}
                charmPriceLine = null;
            }}
        }}
    }}

    function isCmeGlobexMarketOpen() {{
        try {{
            const fmt = new Intl.DateTimeFormat('en-US', {{
                timeZone: 'America/New_York',
                weekday: 'short',
                hour: 'numeric',
                hour12: false
            }});
            const parts = fmt.formatToParts(new Date());
            let wd = '';
            let hr = 0;
            parts.forEach(p => {{
                if (p.type === 'weekday') wd = p.value;
                if (p.type === 'hour') hr = parseInt(p.value, 10) % 24;
            }});
            if (wd === 'Sat') return false;
            if (wd === 'Fri' && hr >= 17) return false;
            if (wd === 'Sun' && hr < 18) return false;
            if ((wd === 'Mon' || wd === 'Tue' || wd === 'Wed' || wd === 'Thu') && hr === 17) return false;
            return true;
        }} catch (e) {{
            return Boolean(window.INITIAL_META && window.INITIAL_META.market_open);
        }}
    }}

    function switchTerminalView(view) {{
        // Seamless zero-reload switcher if needed
    }}

    function setTimeframe(tf) {{
        const normTf = (tf === 'd' || tf === '1d') ? '1d' : tf.toLowerCase();
        currentTf = normTf;
        const allBtns = document.querySelectorAll('.timeframe-pill');
        allBtns.forEach(b => b.classList.remove('active'));
        const activeBtn = Array.from(document.querySelectorAll('.timeframe-pill')).find(b => {{
            const t = b.innerText.trim().toLowerCase();
            return t === normTf || (normTf === '1d' && (t === 'd' || t === '1d'));
        }});
        if (activeBtn) activeBtn.classList.add('active');

        let period = 60;
        if (normTf === '1m') period = 60;
        else if (normTf === '5m') period = 300;
        else if (normTf === '15m') period = 900;
        else if (normTf === '1h') period = 3600;
        else if (normTf === '1d') period = 86400;

        currentPeriodSec = period;
        const tfBadge = document.getElementById('neiro-tf-badge');
        if (tfBadge) {{
            const tfLabels = {{ '1m': 'M1 INTRADAY', '5m': 'M5 INTRADAY', '15m': 'M15 INTRADAY', '1h': 'H1 INTRADAY', '1d': 'D1 SWING' }};
            tfBadge.innerText = tfLabels[normTf] || (normTf.toUpperCase() + ' INTRADAY');
        }}
        buildHistoricalGoldBars(period, normTf);
        pollLiveYahooChart(normTf);
    }}

    function resampleBars(candles, targetPeriodSec) {{
        if (!candles || candles.length === 0) return [];
        if (targetPeriodSec <= 60) {{
            return candles.map(c => ({{
                time: c.time,
                open: c.open,
                high: c.high,
                low: c.low,
                close: c.close,
                volume: c.volume || 0
            }}));
        }}

        const resampled = [];
        let currentBar = null;

        for (let i = 0; i < candles.length; i++) {{
            const c = candles[i];
            const bucketTime = c.time - (c.time % targetPeriodSec);
            if (!currentBar || currentBar.time !== bucketTime) {{
                if (currentBar) resampled.push(currentBar);
                currentBar = {{
                    time: bucketTime,
                    open: c.open,
                    high: c.high,
                    low: c.low,
                    close: c.close,
                    volume: c.volume || 0
                }};
            }} else {{
                currentBar.high = Math.max(currentBar.high, c.high);
                currentBar.low = Math.min(currentBar.low, c.low);
                currentBar.close = c.close;
                currentBar.volume = (currentBar.volume || 0) + (c.volume || 0);
            }}
        }}
        if (currentBar) resampled.push(currentBar);
        return resampled;
    }}

    function generateRealisticGoldCandles(currentP, numBars = 60, periodSec = 60) {{
        // Zero-BS Policy: Never fabricate synthetic random-walk candles.
        // Return a single deterministic flat anchor bar at the authoritative CME GC=F price.
        const nowSec = Math.floor(Date.now() / 1000);
        const barTime = nowSec - (nowSec % periodSec);
        return [{{
            time: barTime,
            open: currentP,
            high: currentP,
            low: currentP,
            close: currentP,
            volume: 0
        }}];
    }}

    function buildHistoricalGoldBars(periodSec = 60, tfKey = null) {{
        if (!candleSeries) return;
        const key = tfKey || (periodSec === 60 ? '1m' : (periodSec === 300 ? '5m' : (periodSec === 900 ? '15m' : (periodSec === 3600 ? '1h' : '1d'))));
        let bars = [];
        if (window.INITIAL_TF_CANDLES && window.INITIAL_TF_CANDLES[key] && window.INITIAL_TF_CANDLES[key].length > 0) {{
            bars = window.INITIAL_TF_CANDLES[key].map(c => ({{
                time: c.time,
                open: c.open,
                high: c.high,
                low: c.low,
                close: c.close,
                volume: c.volume || 0
            }}));
        }} else if (window.INITIAL_CANDLES && window.INITIAL_CANDLES.length > 0) {{
            bars = resampleBars(window.INITIAL_CANDLES, periodSec);
        }} else {{
            bars = generateRealisticGoldCandles(currentGoldPrice, 60, periodSec);
        }}

        if (bars && bars.length > 0) {{
            candleSeries.setData(bars);
            const lastB = bars[bars.length - 1];
            activeCandle = {{
                time: lastB.time,
                open: lastB.open,
                high: lastB.high,
                low: lastB.low,
                close: lastB.close,
                volume: lastB.volume || 28,
                delta: 0
            }};
            const totalBars = bars.length;
            if (neiroChart) {{
                neiroChart.timeScale().setVisibleLogicalRange({{
                    from: Math.max(0, totalBars - 120),
                    to: totalBars + 8,
                }});
            }}
        }}
        setTimeout(drawNeiroOverlay, 40);
    }}

    let activeCandle = null;
    let liveCvdContracts = window.INITIAL_META.bvc_cvd_contracts || 0;
    let liveBuyPct = window.INITIAL_META.bvc_buy_pct || 50.0;
    let liveDealerHedgeGC = window.INITIAL_META.dealer_hedge_futures_flow || 0;
    let liveImpliedForward = window.INITIAL_META.implied_forward_price || window.INITIAL_META.spot;
    let liveForwardDisloc = window.INITIAL_META.forward_dislocation_usd || 0;
    let liveKyleLabel = window.INITIAL_META.kyle_lambda_label || 'THANH KHOẢN SỔ LỆNH BÌNH THƯỜNG';
    let liveFlipVerdict = window.INITIAL_META.flip_integrity_label || '⚖️ ĐANG KIỂM ĐỊNH TRỤC GAMMA FLIP';
    let liveFlipColor = window.INITIAL_META.flip_integrity_color || '#FACC15';
    let liveCandleDelta = 0;

    function computeLiveFlipVerdict(price, zFlip, hedgeGC, dislocUsd, buyPct, kyleLbl) {{
        const dist = price - (zFlip || price);
        const isIceberg = kyleLbl.indexOf('ICEBERG') !== -1;
        if (dist >= 0) {{
            if (hedgeGC >= 35.0 && dislocUsd >= -0.60 && buyPct >= 52.0 && !isIceberg) {{
                return {{
                    txt: '🟢 FLIP THẬT (TRUE BREAKOUT): OPTIONS + MM ĐỒNG THUẬN MUA ĐUỔI',
                    shortTxt: '🟢 FLIP THẬT',
                    col: '#4ADE80'
                }};
            }}
            return {{
                txt: '🚨 BẪY FAKEOUT (BULL TRAP): VƯỢT GAMMA NHƯNG MM ĐANG XẢ ĐÈ (DỄ BỊ ĐẠP SẬP)',
                shortTxt: '🚨 BẪY FAKEOUT',
                col: '#F87171'
            }};
        }}
        if (dist >= -15.0) {{
            if (hedgeGC >= 45.0 && dislocUsd >= 0.25 && buyPct >= 55.0 && !isIceberg) {{
                return {{
                    txt: '🟢 XUNG LỰC THẬT: DÒNG TIỀN OPTIONS ÉP VƯỢT TRỤC GAMMA FLIP',
                    shortTxt: '🟢 XUNG LỰC VƯỢT FLIP',
                    col: '#4ADE80'
                }};
            }}
            if (hedgeGC < 20.0 || dislocUsd < -0.50 || buyPct < 50.0 || isIceberg) {{
                return {{
                    txt: '🚨 RƯỚN GIẢ (FAKE FLIP): THIẾU LỰC OPTIONS — CẨN TRỌNG BỊ ĐẠP TẠI GAMMA FLIP',
                    shortTxt: '🚨 RƯỚN GIẢ (DỄ ĐẠP)',
                    col: '#FACC15'
                }};
            }}
            return {{
                txt: '⚖️ TRANH CHẤP SÁT GAMMA FLIP: CHỜ XÁC NHẬN DÒNG TIỀN QUYỀN CHỌN',
                shortTxt: '⚖️ TRANH CHẤP FLIP',
                col: '#38BDF8'
            }};
        }}
        if (hedgeGC <= -40.0 && buyPct <= 46.0) {{
            return {{
                txt: '🔴 SẬP THẬT (SHORT GAMMA): MM BÁN ĐUỔI THUẬN XU HƯỚNG',
                shortTxt: '🔴 SẬP THẬT (MM BÁN)',
                col: '#F87171'
            }};
        }}
        if (hedgeGC >= 40.0 && buyPct >= 54.0 && dislocUsd >= -0.40) {{
            return {{
                txt: '🟢 HẤP THỤ ĐÁY (BEAR TRAP): CÁ MẬP GOM CALL ÉP MM MUA ĐỠ GIÁ',
                shortTxt: '🟢 HẤP THỤ ĐÁY (MM ĐỠ)',
                col: '#4ADE80'
            }};
        }}
        return {{
            txt: '⚡ VÙNG ÂM GAMMA (DƯỚI FLIP): MM KHUẾCH ĐẠI BIẾN ĐỘNG — CHỜ ĐỒNG THUẬN',
            shortTxt: '⚡ ÂM GAMMA (CHỜ FLOW)',
            col: '#FACC15'
        }};
    }}

    function normCdf(x) {{
        const t = 1 / (1 + 0.2316419 * Math.abs(x));
        const d = 0.3989423 * Math.exp(-x * x / 2);
        const p = d * t * (0.3193815 + t * (-0.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274))));
        return x > 0 ? 1 - p : p;
    }}

    function computeM5AtrJs(candles, tfKey = '1m', fallbackAtr = 4.0) {{
        if (!Array.isArray(candles) || candles.length === 0) {{
            return Math.max(2.0, Math.min(6.5, Number(fallbackAtr || 4.0)));
        }}
        const sample = candles.slice(-14);
        const scale = (tfKey === '1m') ? 2.2 : 1.0;
        let sumR = 0.0;
        let cnt = 0;
        for (let i = 0; i < sample.length; i++) {{
            const b = sample[i];
            if (b && b.high !== undefined && b.low !== undefined) {{
                sumR += Math.max(0.0, Number(b.high) - Number(b.low));
                cnt++;
            }}
        }}
        if (cnt === 0) return Math.max(2.0, Math.min(6.5, Number(fallbackAtr || 4.0)));
        const raw = (sumR / cnt) * scale;
        return Math.round(Math.max(2.0, Math.min(6.5, raw)) * 100) / 100;
    }}

    function percentileSortedJs(sortedArr, p) {{
        if (!sortedArr.length) return 0.25;
        if (sortedArr.length === 1) return sortedArr[0];
        const pos = (p / 100.0) * (sortedArr.length - 1);
        const lo = Math.floor(pos);
        const hi = Math.min(sortedArr.length - 1, lo + 1);
        const frac = pos - lo;
        return sortedArr[lo] * (1.0 - frac) + sortedArr[hi] * frac;
    }}

    function computeLiveVpinBvcJs(candles, win = 24) {{
        if (!Array.isArray(candles) || candles.length < 3) return null;
        let stdDp = 1.0;
        let recent = [];
        if (candles.length >= win + 20) {{
            const bgCandles = candles.slice(0, -6);
            const dpBg = bgCandles.map(c => Number(c.close || 0) - Number(c.open || 0));
            const absSorted = dpBg.map(v => Math.abs(v)).sort((a, b) => a - b);
            const sortedBg = dpBg.slice().sort((a, b) => a - b);
            const q60 = percentileSortedJs(absSorted, 60.0);
            const medBg = percentileSortedJs(sortedBg, 50.0);
            const devSorted = dpBg.map(v => Math.abs(v - medBg)).sort((a, b) => a - b);
            const madBg = percentileSortedJs(devSorted, 50.0) * 1.4826;
            stdDp = Math.max(0.25, 0.5 * (q60 / 0.8416) + 0.5 * madBg);
            recent = candles.slice(-12);
        }} else {{
            recent = candles.slice(-win);
            const dps = recent.map(c => Number(c.close || 0) - Number(c.open || 0));
            const mean = dps.reduce((a, b) => a + b, 0) / Math.max(1, dps.length);
            const variance = dps.reduce((a, b) => a + (b - mean) * (b - mean), 0) / Math.max(1, dps.length);
            stdDp = Math.max(0.25, dps.length > 1 ? Math.sqrt(variance) : 1.0);
        }}

        let bvcCvd = 0.0;
        let bvcBuyVol = 0.0;
        let bvcTotalVol = 0.0;
        const barSlices = [];
        for (let i = 0; i < recent.length; i++) {{
            const c = recent[i];
            const vol = Number(c && c.volume ? c.volume : 0);
            if (vol <= 0) continue;
            const dp = Number(c.close || 0) - Number(c.open || 0);
            const buyFrac = normCdf(dp / stdDp);
            const buyVol = vol * buyFrac;
            const sellVol = vol - buyVol;
            const signedRatio = 2.0 * buyFrac - 1.0;
            bvcCvd += buyVol - sellVol;
            bvcBuyVol += buyVol;
            bvcTotalVol += vol;
            barSlices.push({{ vol: vol, ratio: signedRatio }});
        }}
        if (bvcTotalVol <= 0 || barSlices.length === 0) return null;

        const nBuckets = Math.min(5, barSlices.length);
        const targetBucketVol = Math.max(1.0, bvcTotalVol / nBuckets);
        const bucketImbs = [];
        let curSigned = 0.0;
        let curVol = 0.0;
        for (let i = 0; i < barSlices.length; i++) {{
            let rem = barSlices[i].vol;
            const sRatio = barSlices[i].ratio;
            while (rem > 1e-9) {{
                const need = targetBucketVol - curVol;
                const take = need > 1e-9 ? Math.min(rem, need) : rem;
                curSigned += take * sRatio;
                curVol += take;
                rem -= take;
                if (curVol >= targetBucketVol - 1e-6 && bucketImbs.length < nBuckets) {{
                    bucketImbs.push(Math.abs(curSigned) / Math.max(1.0, curVol));
                    curSigned = 0.0;
                    curVol = 0.0;
                }}
            }}
        }}
        if (curVol > 1e-6 && bucketImbs.length < nBuckets) {{
            bucketImbs.push(Math.abs(curSigned) / Math.max(1.0, curVol));
        }}
        const rawVpin = bucketImbs.length ? (bucketImbs.reduce((a, b) => a + b, 0) / bucketImbs.length) : (Math.abs(bvcCvd) / bvcTotalVol);
        const vpinPct = Math.round(Math.max(5.0, Math.min(99.0, rawVpin * 100.0)) * 10) / 10;
        const buyPct = Math.round((bvcBuyVol / bvcTotalVol) * 1000) / 10;
        let vpinLbl = '🟢 VPIN ' + vpinPct.toFixed(1) + '% [NHIỄU ĐÁM ĐÔNG — AN TOÀN FADE WALL]';
        if (vpinPct >= 65.0) {{
            vpinLbl = '🚨 VPIN ' + vpinPct.toFixed(1) + '% [ĐỘC TÍNH >=65% — CẤM CHẶN TÀU]';
        }} else if (vpinPct >= 40.0) {{
            vpinLbl = '⚠️ VPIN ' + vpinPct.toFixed(1) + '% [LỆCH DÒNG LỆNH — GIẢM SIZE LIMIT]';
        }}
        return {{
            bvcCvd: Math.round(bvcCvd * 10) / 10,
            buyPct: buyPct,
            vpinPct: vpinPct,
            vpinLabel: vpinLbl,
        }};
    }}

    function resolveAdaptiveStrikesJs(spot, dteDays, callWall, putWall) {{
        const opts = window.INITIAL_OPTIONS || [];
        const uniqueSet = new Set();
        opts.forEach(o => {{ if (o && o.strike) uniqueSet.add(Number(o.strike)); }});
        const sorted = Array.from(uniqueSet).sort((a, b) => a - b);
        if (!sorted.length) sorted.push(Math.round(spot));

        const aboveList = sorted.filter(s => s > spot);
        const rawAbove = aboveList.length > 0 ? aboveList[0] : (callWall > spot ? callWall : spot + 25.0);
        const rawNextAbove = aboveList.length > 1 ? aboveList[1] : rawAbove + 25.0;

        const belowList = sorted.filter(s => s <= spot);
        const rawBelow = belowList.length > 0 ? belowList[belowList.length - 1] : (putWall < spot ? putWall : spot - 25.0);
        const rawNextBelow = belowList.length > 1 ? belowList[belowList.length - 2] : rawBelow - 25.0;

        let rawStep = 25.0;
        if (sorted.length > 1) {{
            rawStep = Infinity;
            for (let i = 1; i < sorted.length; i++) {{
                const d = sorted[i] - sorted[i - 1];
                if (d > 0 && d < rawStep) rawStep = d;
            }}
            if (!isFinite(rawStep)) rawStep = 25.0;
        }}

        let isMicro = false;
        let strikeAbove = rawAbove;
        let nextAbove = rawNextAbove;
        let strikeBelow = rawBelow;
        let nextBelow = rawNextBelow;
        let step = rawStep;

        if (dteDays <= 10.0) {{
            const fineStep = 5.0;
            let fineAbove = Math.ceil(spot / fineStep) * fineStep;
            if (fineAbove <= spot) fineAbove += fineStep;
            if ((rawAbove - spot) > fineStep) {{
                strikeAbove = fineAbove;
                nextAbove = rawAbove > (fineAbove + fineStep) ? (fineAbove + fineStep) : rawAbove;
                step = Math.min(step, fineStep);
                isMicro = true;
            }}
            let fineBelow = Math.floor(spot / fineStep) * fineStep;
            if (fineBelow >= spot) fineBelow -= fineStep;
            if ((spot - rawBelow) > fineStep) {{
                strikeBelow = fineBelow;
                nextBelow = rawBelow < (fineBelow - fineStep) ? (fineBelow - fineStep) : rawBelow;
                step = Math.min(step, fineStep);
                isMicro = true;
            }}
            if (isMicro) {{
                if (nextAbove > strikeAbove + step) nextAbove = strikeAbove + step;
                if (nextBelow < strikeBelow - step) nextBelow = strikeBelow - step;
            }}
        }}
        return {{ strikeAbove, nextAbove, strikeBelow, nextBelow, step, isMicroGuarded: isMicro }};
    }}

    function sizeXauusdJs(slUsd, gexRegime) {{
        const sl = slUsd > 0 ? slUsd : 4.5;
        const reg = String(gexRegime || 'LONG_GAMMA').toUpperCase();
        const kappa = reg.includes('LONG') ? 1.0 : (reg.includes('SHORT') ? 0.5 : 0.75);
        const baseLots = 100.0 / (100.0 * sl);
        const rawLots = baseLots * kappa;
        const floored = Math.floor((rawLots / 0.01) + 1e-9) * 0.01;
        return Math.max(0.01, Math.min(5.0, Math.round(floored * 100) / 100));
    }}

    function r2(v) {{
        const s = v < 0 ? -1 : 1;
        const av = Math.abs(v) * 100.0;
        const fl = Math.floor(av);
        if ((av - fl) === 0.5) {{
            return s * ((fl % 2 === 0 ? fl : fl + 1) / 100.0);
        }}
        return s * (Math.floor(av + 0.5) / 100.0);
    }}

    function computeTacticalMatrixJs(params) {{
        const atr5 = Math.max(2.0, Math.min(6.5, Number(params.atr5m || 4.0)));
        const brkOff = Math.max(2.80, r2(0.8 * atr5));
        const slBrk = Math.max(5.00, r2(1.5 * atr5), r2(brkOff + 2.00));
        const slRev = Math.max(5.00, r2(1.4 * atr5));
        const frontRunTp = 1.00;

        const normReg = String(params.regime || 'NEUTRAL').toUpperCase();
        const isLongGamma = normReg.includes('LONG');
        const isShortGamma = normReg.includes('SHORT');
        const zFlip = (params.zeroGamma && params.zeroGamma > 0) ? Number(params.zeroGamma) : Number(params.spot);
        const aboveZg = Number(params.spot) >= zFlip;
        const belowZg = Number(params.spot) < zFlip;
        const sessionOpen = Boolean(params.sessionOpen);
        const nearPutWall = (Number(params.putWall) > 0) && (Math.abs(params.strikeBelow - params.putWall) <= Math.max(params.step, 5.0));

        // 1. BUY Squeeze
        const entrySq = r2(params.strikeAbove + brkOff);
        const slSq = r2(entrySq - slBrk);
        const rawSqTp = params.hasUpAirPocket ? (params.majorUpWall - frontRunTp) : (params.nextAbove - frontRunTp);
        const tpSq = r2(Math.min(Math.max(entrySq + 4.00, rawSqTp), entrySq + 1.5 * slBrk));
        const sqActive = sessionOpen && isShortGamma && Boolean(params.hasUpAirPocket) && (params.vpinPct >= 55.0 || params.callWallSiege >= 0.25);
        const sqReason = sqActive ? 'SHORT_GAMMA + Air Pocket + Áp lực phá trần' : (!sessionOpen ? 'GLOBEX ĐÓNG CỬA' : 'Chờ SHORT_GAMMA + Air Pocket + VPIN/Siege');

        // 2. SELL Fade
        const entryFd = r2(params.strikeAbove - 1.00);
        const slFd = r2(entryFd + slRev);
        const candFdTp = (params.strikeBelow < entryFd - 2.00) ? Math.min(params.spot, params.strikeBelow + frontRunTp) : (entryFd - 4.50);
        const tpFd = r2(Math.max(entryFd - 6.00, Math.min(entryFd - 3.00, candFdTp)));
        const fdActive = sessionOpen && (params.vpinPct < 58.0) && (isLongGamma || aboveZg);
        const fdReason = fdActive ? 'MM LONG_GAMMA / Trên Zero Gamma + VPIN an toàn' : (!sessionOpen ? 'GLOBEX ĐÓNG CỬA' : (params.vpinPct >= 58.0 ? 'VPIN CAO (>=58%)' : 'Dưới Zero Gamma (Cấm chặn tàu)'));

        // 3. BUY Rebound
        const entryRb = r2(params.strikeBelow + 1.00);
        const slRb = r2(entryRb - slRev);
        const tpRb = r2(Math.min(entryRb + 7.50, Math.max(entryRb + 3.00, params.strikeAbove - frontRunTp)));
        const rbActive = sessionOpen && (params.vpinPct < 55.0) && (isLongGamma || aboveZg || nearPutWall);
        const rbReason = rbActive ? (nearPutWall ? 'Gần Put Wall + VPIN an toàn' : 'MM LONG_GAMMA / Trên Zero Gamma') : (!sessionOpen ? 'GLOBEX ĐÓNG CỬA' : (params.vpinPct >= 55.0 ? 'VPIN ĐỘC HẠI (>=55%)' : 'SHORT_GAMMA xa Put Wall (Tránh bắt dao)'));

        // 4. SELL Breakdown
        const entryBd = r2(params.strikeBelow - brkOff);
        const slBd = r2(entryBd + slBrk);
        const rawBdTp = params.hasDownAirPocket ? (params.majorDownWall + frontRunTp) : (params.nextBelow + frontRunTp);
        const tpBd = r2(Math.max(Math.min(entryBd - 4.00, rawBdTp), entryBd - 1.5 * slBrk));
        const bdActive = sessionOpen && isShortGamma && Boolean(params.hasDownAirPocket) && belowZg && (params.vpinPct >= 50.0 || params.putWallSiege >= 0.20);
        const bdReason = bdActive ? 'SHORT_GAMMA dưới ZG + Air Pocket + Áp lực xả' : (!sessionOpen ? 'GLOBEX ĐÓNG CỬA' : 'Chờ SHORT_GAMMA dưới ZG + Air Pocket + VPIN/Siege');

        return {{
            atr5m: atr5,
            strikeAbove: params.strikeAbove,
            strikeBelow: params.strikeBelow,
            isMicroGuarded: params.isMicroGuarded,
            squeeze: {{ key: 'sq', side: 'BUY', title: '1. BUY MUA ĐUỔI', label: '1. BUY MUA ĐUỔI (Squeeze ' + Math.round(params.strikeAbove) + ')', trig: 'Vượt > ' + r2(entrySq - 0.50).toFixed(2), entry: entrySq, sl: slSq, slDist: r2(entrySq - slSq), tp: tpSq, active: sqActive, badge: sqActive ? '[KÍCH HOẠT]' : '[CHỜ XÁC NHẬN]', reason: sqReason, lots: sizeXauusdJs(r2(entrySq - slSq), normReg) }},
            fade:    {{ key: 'fd', side: 'SELL', title: '2. SELL CHẶN TIỀN TUYẾN', label: '2. SELL CHẶN TIỀN TUYẾN (Fade ' + Math.round(params.strikeAbove) + ')', trig: (params.strikeAbove - 1.50).toFixed(2) + ' - ' + params.strikeAbove.toFixed(2), entry: entryFd, sl: slFd, slDist: r2(slFd - entryFd), tp: tpFd, active: fdActive, badge: fdActive ? '[KÍCH HOẠT]' : '[TẠM KHÓA]', reason: fdReason, lots: sizeXauusdJs(r2(slFd - entryFd), normReg) }},
            rebound: {{ key: 'rb', side: 'BUY', title: '3. BUY BẮT SÀN ATM', label: '3. BUY BẮT SÀN ATM (Rebound ' + Math.round(params.strikeBelow) + ')', trig: params.strikeBelow.toFixed(2) + ' - ' + (params.strikeBelow + 1.50).toFixed(2), entry: entryRb, sl: slRb, slDist: r2(entryRb - slRb), tp: tpRb, active: rbActive, badge: rbActive ? '[KÍCH HOẠT]' : '[TẠM KHÓA]', reason: rbReason, lots: sizeXauusdJs(r2(entryRb - slRb), normReg) }},
            breakdown: {{ key: 'bd', side: 'SELL', title: '4. SELL THỦNG SÀN', label: '4. SELL THỦNG SÀN & VACUUM RUN (Breakdown ' + Math.round(params.strikeBelow) + ')', trig: 'Thủng < ' + r2(entryBd + 0.50).toFixed(2), entry: entryBd, sl: slBd, slDist: r2(slBd - entryBd), tp: tpBd, active: bdActive, badge: bdActive ? '[KÍCH HOẠT]' : '[CHỜ XÁC NHẬN]', reason: bdReason, lots: sizeXauusdJs(r2(slBd - entryBd), normReg) }},
        }};
    }}

    function updateRealtimeTacticalCockpit() {{
        const m = window.INITIAL_META || {{}};
        const spot = Number(currentGoldPrice || m.spot || 0);
        if (!spot) return;

        const dteDays = Number(m.dte_days || 8.0);
        const callWall = Number(m.call_wall || spot + 50);
        const putWall = Number(m.put_wall || spot - 50);
        const zFlip = Number(m.zero_gamma_flip || spot);
        const strikes = resolveAdaptiveStrikesJs(spot, dteDays, callWall, putWall);

        m.strike_above = strikes.strikeAbove;
        m.next_above = strikes.nextAbove;
        m.strike_below = strikes.strikeBelow;
        m.next_below = strikes.nextBelow;
        m.step = strikes.step;

        const sessionOpen = isCmeGlobexMarketOpen();
        const regime = String(m.regime || (Number(m.total_net_gex || 0) >= 0 ? 'LONG_GAMMA' : 'SHORT_GAMMA'));
        const mat = computeTacticalMatrixJs({{
            spot: spot,
            strikeAbove: strikes.strikeAbove,
            nextAbove: strikes.nextAbove,
            strikeBelow: strikes.strikeBelow,
            nextBelow: strikes.nextBelow,
            step: strikes.step,
            callWall: callWall,
            putWall: putWall,
            zeroGamma: zFlip,
            majorUpWall: Number(m.major_up_wall || callWall),
            majorDownWall: Number(m.major_down_wall || putWall),
            hasUpAirPocket: Boolean(m.has_up_air_pocket),
            hasDownAirPocket: Boolean(m.has_down_air_pocket),
            regime: regime,
            vpinPct: liveVpinPct,
            callWallSiege: Number(m.call_wall_siege || 0),
            putWallSiege: Number(m.put_wall_siege || 0),
            sessionOpen: sessionOpen,
            atr5m: liveAtr5m,
            isMicroGuarded: strikes.isMicroGuarded,
        }});
        liveTacticalMatrix = mat;

        // 1. Topbar & HUD VPIN sync
        const vpinCol = liveVpinPct >= 65.0 ? '#F87171' : (liveVpinPct >= 40.0 ? '#FACC15' : '#4ADE80');
        const topVpin = document.getElementById('top-vpin-val');
        if (topVpin) {{ topVpin.innerText = liveVpinPct.toFixed(1) + '%'; topVpin.style.color = vpinCol; }}
        const hudVpin = document.getElementById('hud-vpin-val');
        if (hudVpin) {{ hudVpin.innerText = liveVpinLabel; hudVpin.style.color = vpinCol; }}
        const microVpin = document.getElementById('micro-vpin-val');
        if (microVpin) {{ microVpin.innerText = liveVpinLabel; microVpin.style.color = vpinCol; }}

        // 2. Spine (KHOI 4) real-time strikes & distances
        const elSb = document.getElementById('spine-strike-below');
        if (elSb) elSb.innerText = '$' + Math.round(strikes.strikeBelow).toLocaleString('en-US');
        const elSa = document.getElementById('spine-strike-above');
        if (elSa) elSa.innerText = '$' + Math.round(strikes.strikeAbove).toLocaleString('en-US');
        const elSat = document.getElementById('spine-above-title');
        if (elSat) elSat.innerText = 'CẢN TRÊN' + (strikes.isMicroGuarded ? ' (VI MÔ)' : '');
        const elDp = document.getElementById('spine-dist-put');
        if (elDp) elDp.innerText = ((spot - putWall) >= 0 ? '+' : '') + (spot - putWall).toFixed(1) + '$';
        const elDb = document.getElementById('spine-dist-below');
        if (elDb) elDb.innerText = ((spot - strikes.strikeBelow) >= 0 ? '+' : '') + (spot - strikes.strikeBelow).toFixed(1) + '$';
        const elDa = document.getElementById('spine-dist-above');
        if (elDa) elDa.innerText = ((strikes.strikeAbove - spot) >= 0 ? '+' : '') + (strikes.strikeAbove - spot).toFixed(1) + '$';
        const elDc = document.getElementById('spine-dist-call');
        if (elDc) elDc.innerText = ((callWall - spot) >= 0 ? '+' : '') + (callWall - spot).toFixed(1) + '$';

        // 3. KHOI 6 Dynamic Rows
        const items = [mat.squeeze, mat.fade, mat.rebound, mat.breakdown];
        items.forEach(it => {{
            const row = document.getElementById('k6-row-' + it.key);
            if (row) {{
                row.classList.toggle('k6-row-active', it.active);
                row.classList.toggle('k6-row-locked', !it.active);
            }}
            const lbl = document.getElementById('k6-' + it.key + '-label');
            if (lbl) lbl.innerText = it.label;
            const gate = document.getElementById('k6-' + it.key + '-gate');
            if (gate) {{
                const col = it.active ? '#4ADE80' : '#94A3B8';
                const bg = it.active ? 'rgba(34,197,94,0.14)' : 'rgba(100,116,139,0.16)';
                gate.innerHTML = "<span style='display:inline-block; margin-left:6px; padding:1px 6px; border-radius:4px; font-size:10px; font-weight:700; color:" + col + "; background:" + bg + "; border:1px solid " + col + ";'>" + it.badge + "</span><div style='font-size:10px; color:#64748B; font-weight:400; margin-top:2px;'>" + it.reason + "</div>";
            }}
            const trig = document.getElementById('k6-' + it.key + '-trig');
            if (trig) trig.innerText = it.trig;
            const ent = document.getElementById('k6-' + it.key + '-entry');
            if (ent) ent.innerText = it.entry.toFixed(2);
            const slEl = document.getElementById('k6-' + it.key + '-sl');
            if (slEl) slEl.innerText = it.sl.toFixed(2) + ' ($' + it.slDist.toFixed(1) + ')';
            const tpEl = document.getElementById('k6-' + it.key + '-tp');
            if (tpEl) tpEl.innerText = it.tp.toFixed(2);
            const lotEl = document.getElementById('k6-' + it.key + '-lot');
            if (lotEl) lotEl.innerText = '~' + it.lots.toFixed(2) + ' Lot';
        }});

        // 4. 3-Second Tactical Command Bar (4 Boxes)
        const netGex = Number(m.total_net_gex || 0);
        const distFlip = spot - zFlip;
        const isLongG = netGex >= 0 && distFlip >= 0;
        const regVal = document.getElementById('cmd-regime-val');
        const regSub = document.getElementById('cmd-regime-sub');
        const regCard = document.getElementById('cmd-regime-card');
        if (regVal && regSub) {{
            if (netGex >= 0 && distFlip >= 0) {{
                regVal.innerText = 'MM GHÌM ĐẢO CHIỀU (LONG Γ)';
                regVal.style.color = '#4ADE80';
                if (regCard) regCard.style.borderLeftColor = '#22C55E';
            }} else if (netGex < 0 && distFlip < 0) {{
                regVal.innerText = 'MM ĐẨY SÓNG MẠNH (SHORT Γ)';
                regVal.style.color = '#F87171';
                if (regCard) regCard.style.borderLeftColor = '#EF4444';
            }} else {{
                regVal.innerText = 'VÙNG CHUYỂN PHA (TRANH CHẤP)';
                regVal.style.color = '#FACC15';
                if (regCard) regCard.style.borderLeftColor = '#EAB308';
            }}
            regSub.innerText = 'Flip $' + zFlip.toFixed(0) + ' (' + (distFlip >= 0 ? '+' : '') + distFlip.toFixed(1) + '$) · NetGEX $' + (netGex >= 0 ? '+' : '') + netGex.toFixed(1) + 'M';
        }}

        const distAbove = strikes.strikeAbove - spot;
        const distBelow = spot - strikes.strikeBelow;
        const wallVal = document.getElementById('cmd-wall-val');
        const wallSub = document.getElementById('cmd-wall-sub');
        const wallCard = document.getElementById('cmd-wall-card');
        if (wallVal && wallSub) {{
            const nearTop = distAbove <= distBelow;
            const apNote = m.has_up_air_pocket && nearTop ? ' ⚠️ AIR POCKET TRÊN' : (m.has_down_air_pocket && !nearTop ? ' ⚠️ AIR POCKET DƯỚI' : ' · Biên ổn định');
            wallVal.innerText = nearTop
                ? ('SÁT CẢN $' + Math.round(strikes.strikeAbove).toLocaleString('en-US') + ' (+' + distAbove.toFixed(1) + '$)')
                : ('SÁT SÀN $' + Math.round(strikes.strikeBelow).toLocaleString('en-US') + ' (-' + distBelow.toFixed(1) + '$)');
            wallVal.style.color = (m.has_up_air_pocket && nearTop) || (m.has_down_air_pocket && !nearTop) ? '#FACC15' : '#38BDF8';
            if (wallCard) wallCard.style.borderLeftColor = nearTop ? '#EF4444' : '#22C55E';
            wallSub.innerText = 'PW $' + Math.round(putWall).toLocaleString('en-US') + ' (-' + (spot - putWall).toFixed(0) + '$) · CW $' + Math.round(callWall).toLocaleString('en-US') + ' (+' + (callWall - spot).toFixed(0) + '$)' + apNote;
        }}

        const flowVal = document.getElementById('cmd-flow-val');
        const flowSub = document.getElementById('cmd-flow-sub');
        const flowCard = document.getElementById('cmd-flow-card');
        if (flowVal && flowSub) {{
            const cwSiege = Number(m.call_wall_siege || 0);
            const pwSiege = Number(m.put_wall_siege || 0);
            const isBreaking = liveVpinPct >= 65.0 || cwSiege >= 0.25 || pwSiege >= 0.25;
            if (liveVpinPct >= 65.0) {{
                flowVal.innerText = 'DÒNG ĐỘC HẠI PHÁ TƯỜNG (VPIN ' + liveVpinPct.toFixed(1) + '%)';
                flowVal.style.color = '#F87171';
                if (flowCard) flowCard.style.borderLeftColor = '#EF4444';
            }} else if (isBreaking) {{
                flowVal.innerText = 'ÁP LỰC CÔNG THÀNH (SIEGE/VPIN TĂNG)';
                flowVal.style.color = '#FACC15';
                if (flowCard) flowCard.style.borderLeftColor = '#EAB308';
            }} else {{
                flowVal.innerText = 'DÒNG TIỀN ĐỠ TƯỜNG (VPIN ' + liveVpinPct.toFixed(1) + '%)';
                flowVal.style.color = '#4ADE80';
                if (flowCard) flowCard.style.borderLeftColor = '#22C55E';
            }}
            flowSub.innerText = 'Mua BVC: ' + liveBuyPct.toFixed(1) + '% · δF ' + (liveForwardDisloc >= 0 ? '+' : '') + liveForwardDisloc.toFixed(2) + '$ · CW/PW Siege: ' + cwSiege.toFixed(2) + 'x/' + pwSiege.toFixed(2) + 'x';
        }}

        const actVal = document.getElementById('cmd-action-val');
        const actSub = document.getElementById('cmd-action-sub');
        const actCard = document.getElementById('cmd-action-card');
        if (actVal && actSub) {{
            const activeList = items.filter(it => it.active);
            let best = null;
            if (activeList.length > 0) {{
                // Prefer momentum breakout in Short Gamma, otherwise nearest trigger distance
                best = activeList.slice().sort((a, b) => Math.abs(a.entry - spot) - Math.abs(b.entry - spot))[0];
            }}
            if (!sessionOpen) {{
                actVal.innerText = 'ĐỨNG NGOÀI (GLOBEX ĐÓNG CỬA)';
                actVal.style.color = '#94A3B8';
                if (actCard) actCard.style.borderLeftColor = '#64748B';
                actSub.innerText = 'Chờ phiên Globex mở cửa trở lại để khớp lệnh COMEX GC.';
            }} else if (best) {{
                const isBuy = best.side === 'BUY';
                actVal.innerText = best.title + ' @ ' + best.entry.toFixed(2);
                actVal.style.color = isBuy ? '#4ADE80' : '#F87171';
                if (actCard) actCard.style.borderLeftColor = isBuy ? '#22C55E' : '#EF4444';
                actSub.innerText = 'SL ' + best.sl.toFixed(2) + ' ($' + best.slDist.toFixed(1) + ') · TP ' + best.tp.toFixed(2) + ' · ~' + best.lots.toFixed(2) + ' Lot (' + best.reason + ')';
            }} else {{
                actVal.innerText = 'ĐỨNG NGOÀI QUAN SÁT (0 KÈO ACTIVE)';
                actVal.style.color = '#FACC15';
                if (actCard) actCard.style.borderLeftColor = '#EAB308';
                actSub.innerText = 'VPIN ' + liveVpinPct.toFixed(1) + '% · Chờ giá chạm bẫy & xác nhận bộ lọc ADR-028.';
            }}
        }}
    }}

    function updateSyncBadgeHonest() {{
        const badge = document.getElementById('cloud-sync-badge');
        if (!badge) return;
        const now = Date.now();
        if (!isCmeGlobexMarketOpen()) {{
            badge.style.background = 'rgba(148, 163, 184, 0.18)';
            badge.style.borderColor = 'rgba(148, 163, 184, 0.4)';
            badge.style.color = '#CBD5E1';
            badge.innerText = '● CME GLOBEX: CLOSED (SETTLED)';
            return;
        }}
        if (lastBridgeSuccessEpoch && (now - lastBridgeSuccessEpoch) < 12000) {{
            badge.style.background = 'rgba(34, 197, 94, 0.18)';
            badge.style.borderColor = 'rgba(34, 197, 94, 0.45)';
            badge.style.color = '#4ADE80';
            badge.innerText = '● LIVE BRIDGE (2.5s)';
            return;
        }}
        const tsUtc = window.INITIAL_META && window.INITIAL_META.timestamp_utc;
        const parsedTs = tsUtc ? Date.parse(tsUtc) : NaN;
        const ageMs = !isNaN(parsedTs) ? (now - parsedTs) : Infinity;
        if (lastCloudSuccessEpoch && ageMs < 180000) {{
            badge.style.background = 'rgba(56, 189, 248, 0.16)';
            badge.style.borderColor = 'rgba(56, 189, 248, 0.4)';
            badge.style.color = '#38BDF8';
            badge.innerText = '● CLOUD SYNC (LIVE)';
            return;
        }}
        const minsOld = isFinite(ageMs) ? Math.max(0, Math.floor(ageMs / 60000)) : null;
        badge.style.background = 'rgba(234, 179, 8, 0.14)';
        badge.style.borderColor = 'rgba(234, 179, 8, 0.4)';
        badge.style.color = '#FACC15';
        badge.innerText = minsOld !== null ? ('● OFFLINE SNAPSHOT (' + minsOld + 'p)') : '● OFFLINE SNAPSHOT';
    }}

    function updateSqueezeHud(price) {{
        const ladder = (window.INITIAL_META && window.INITIAL_META.squeeze_ladder) || [];
        if (!ladder.length || !price) return;
        let lo = 0, hi = ladder.length - 1, idxAbove = ladder.length - 1;
        while (lo <= hi) {{
            const mid = (lo + hi) >> 1;
            if (ladder[mid].k > price) {{
                idxAbove = mid;
                hi = mid - 1;
            }} else {{
                lo = mid + 1;
            }}
        }}
        const above = ladder[idxAbove];
        const below = ladder[Math.max(0, lo - 1)];
        const upEl = document.getElementById('hud-sqz-up');
        const dnEl = document.getElementById('hud-sqz-down');
        if (upEl && above) {{
            upEl.innerText = '> $' + Math.round(above.sq_tr).toLocaleString('en-US') + ' -> TP $' + Math.round(above.sq_tp).toLocaleString('en-US');
        }}
        if (dnEl && below) {{
            dnEl.innerText = '< $' + Math.round(below.wf_tr).toLocaleString('en-US') + ' -> TP $' + Math.round(below.wf_tp).toLocaleString('en-US');
        }}
    }}

    function evaluateBarOrderflow(candles, tfKey = '1m') {{
        const m1Source = (tfKey === '1m' && Array.isArray(candles) && candles.length >= 3)
            ? candles
            : (window.INITIAL_CANDLES || candles || []);
        const valid = Array.isArray(candles) ? candles.slice(-24).filter(b => b && Number(b.volume || 0) > 0) : [];
        if (valid.length >= 5) {{
            const lams = valid.map(b => Math.abs(Number(b.close) - Number(b.open)) / Number(b.volume) * 1000.0);
            const avgLam = lams.reduce((a, b) => a + b, 0) / lams.length;
            const avgVol = valid.reduce((a, b) => a + Number(b.volume), 0) / valid.length;
            const lastLam = lams[lams.length - 1];
            const lastVol = Number(valid[valid.length - 1].volume);
            if (lastVol >= 1.3 * avgVol && lastLam <= 0.55 * Math.max(1e-6, avgLam)) {{
                liveKyleLabel = 'HẤP THỤ TẢNG BĂNG (ICEBERG LIMIT ABSORPTION)';
            }} else if (lastLam >= 1.75 * Math.max(1e-6, avgLam)) {{
                liveKyleLabel = 'TRƯỢT GIÁ RỖNG SỔ LỆNH (VACUUM MARKET SWEEP)';
            }} else if (Date.now() - lastAuthoritativeVpinEpoch > 3000) {{
                liveKyleLabel = 'THANH KHOẢN SỔ LỆNH BÌNH THƯỜNG (BAR OLS)';
            }}
        }}
        if (Array.isArray(m1Source) && m1Source.length >= 3) {{
            liveAtr5m = computeM5AtrJs(m1Source, '1m', liveAtr5m);
            if (Date.now() - lastAuthoritativeVpinEpoch > 3000) {{
                const bvc = computeLiveVpinBvcJs(m1Source, 24);
                if (bvc) {{
                    liveCvdContracts = bvc.bvcCvd;
                    liveBuyPct = bvc.buyPct;
                    liveVpinPct = bvc.vpinPct;
                    liveVpinLabel = bvc.vpinLabel;
                }}
            }}
        }}
    }}

    function applyLiveTick(newPrice, tickVol = null, isAuthoritativeYahoo = false) {{
        if (!newPrice || isNaN(newPrice)) return;
        const marketOpen = isCmeGlobexMarketOpen();
        if (!marketOpen && !isAuthoritativeYahoo) return;

        const prevPrice = currentGoldPrice;
        currentGoldPrice = Math.round(newPrice * 100) / 100;
        if (isAuthoritativeYahoo) {{
            yahooAnchorPrice = currentGoldPrice;
        }}
        const dp = currentGoldPrice - prevPrice;

        if (livePriceLine) {{
            livePriceLine.applyOptions({{ price: currentGoldPrice }});
        }}

        const topSpotEl = document.getElementById('top-ticker-price');
        if (topSpotEl) {{
            topSpotEl.innerText = '$' + currentGoldPrice.toLocaleString('en-US', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});
            topSpotEl.style.color = dp >= 0 ? '#4ADE80' : '#F87171';
        }}

        const nowSec = Math.floor(Date.now() / 1000);
        const barTime = marketOpen
            ? (nowSec - (nowSec % currentPeriodSec))
            : (activeCandle ? activeCandle.time : (nowSec - (nowSec % currentPeriodSec)));
        const hasRealTickVol = (tickVol !== null && Number(tickVol) > 0);
        const realVTick = hasRealTickVol ? Number(tickVol) : 0;

        // 1. Real-Volume BVC Update (never synthesize fake vTick when tickVol === null)
        let tickDelta = 0.0;
        if (hasRealTickVol) {{
            const zScore = dp / 0.18;
            const buyFrac = normCdf(zScore);
            tickDelta = realVTick * (2.0 * buyFrac - 1.0);
            liveCvdContracts += tickDelta;
            liveBuyPct = Math.max(5.0, Math.min(95.0, 0.92 * liveBuyPct + 0.08 * (buyFrac * 100.0)));
        }}

        if (!activeCandle || (marketOpen && activeCandle.time < barTime)) {{
            activeCandle = {{
                time: barTime,
                open: prevPrice,
                high: Math.max(prevPrice, currentGoldPrice),
                low: Math.min(prevPrice, currentGoldPrice),
                close: currentGoldPrice,
                volume: realVTick,
                delta: tickDelta
            }};
        }} else {{
            activeCandle.high = Math.max(activeCandle.high, currentGoldPrice);
            activeCandle.low = Math.min(activeCandle.low, currentGoldPrice);
            activeCandle.close = currentGoldPrice;
            if (hasRealTickVol) {{
                activeCandle.volume += realVTick;
                activeCandle.delta += tickDelta;
            }}
        }}
        liveCandleDelta = activeCandle.delta || 0.0;

        if (candleSeries) {{
            candleSeries.update({{
                time: activeCandle.time,
                open: activeCandle.open,
                high: activeCandle.high,
                low: activeCandle.low,
                close: activeCandle.close,
            }});
        }}

        // 2. Zero-Latency Dealer Gamma Hedge Flow & Put-Call Parity Lead-Lag (delta_F)
        const netGexM = window.INITIAL_META.total_net_gex || -17.2;
        const gammaContractsPerUsd = (netGexM * 1e6) / Math.max(1e6, currentGoldPrice * currentGoldPrice);
        const instantGammaHedge = -dp * gammaContractsPerUsd * 0.35;
        liveDealerHedgeGC += instantGammaHedge;
        liveForwardDisloc = Math.round((liveImpliedForward - currentGoldPrice) * 100) / 100;

        // 3. Real-Volume Kyle's Lambda Regime (never evaluate on synthetic tick volume)
        if (hasRealTickVol) {{
            const kyleLambda = Math.abs(dp) / Math.max(1, realVTick);
            if (realVTick >= 12 && Math.abs(dp) <= 0.08) {{
                liveKyleLabel = 'HẤP THỤ TẢNG BĂNG (ICEBERG LIMIT ABSORPTION)';
            }} else if (kyleLambda >= 0.045 && Math.abs(dp) >= 0.22) {{
                liveKyleLabel = 'TRƯỢT RỖNG SỔ LỆNH (VACUUM MARKET SWEEP)';
            }}
        }}
        updateSqueezeHud(currentGoldPrice);

        // 4. Synchronize all DOM HUD & Microstructure Badges in <1ms
        const cvdCol = liveCvdContracts >= 0 ? '#4ADE80' : '#F87171';
        const hedgeCol = liveDealerHedgeGC > 50 ? '#4ADE80' : (liveDealerHedgeGC < -50 ? '#F87171' : '#FACC15');
        const leadCol = liveForwardDisloc >= 1.5 ? '#4ADE80' : (liveForwardDisloc <= -1.5 ? '#F87171' : '#38BDF8');

        const hudLead = document.getElementById('hud-lead-val');
        if (hudLead) {{
            hudLead.innerText = 'F_opt $' + liveImpliedForward.toLocaleString('en-US', {{minimumFractionDigits:2, maximumFractionDigits:2}}) + ' (' + (liveForwardDisloc >= 0 ? '+' : '') + liveForwardDisloc.toFixed(2) + '$)';
            hudLead.style.color = leadCol;
        }}
        const hudHedge = document.getElementById('hud-hedge-val');
        if (hudHedge) {{
            hudHedge.innerText = (liveDealerHedgeGC >= 0 ? '+' : '') + liveDealerHedgeGC.toFixed(1) + ' HĐ GC ' + (liveDealerHedgeGC > 50 ? '[ÉP MM MUA]' : (liveDealerHedgeGC < -50 ? '[ÉP MM BÁN]' : '[CÂN BẰNG]'));
            hudHedge.style.color = hedgeCol;
        }}
        const hudCvd = document.getElementById('hud-cvd-val');
        if (hudCvd) {{
            hudCvd.innerText = (liveCvdContracts >= 0 ? '+' : '') + Math.round(liveCvdContracts) + ' HĐ | ' + liveBuyPct.toFixed(1) + '% MUA';
            hudCvd.style.color = cvdCol;
        }}
        const hudBar = document.getElementById('hud-bvc-bar');
        if (hudBar) hudBar.style.width = liveBuyPct.toFixed(1) + '%';
        const hudKyle = document.getElementById('hud-kyle-val');
        if (hudKyle) hudKyle.innerText = liveKyleLabel;

        const topCvd = document.getElementById('top-cvd-val');
        if (topCvd) {{
            topCvd.innerText = (liveCvdContracts >= 0 ? '+' : '') + Math.round(liveCvdContracts) + ' HĐ (' + Math.round(liveBuyPct) + '%B)';
            topCvd.style.color = cvdCol;
        }}
        const topHedge = document.getElementById('top-hedge-val');
        if (topHedge) {{
            topHedge.innerText = (liveDealerHedgeGC >= 0 ? '+' : '') + Math.round(liveDealerHedgeGC) + ' GC';
            topHedge.style.color = hedgeCol;
        }}

        // Also sync QUANT MICROSTRUCTURE strip right below the chart
        const microLead = document.getElementById('micro-lead-val');
        if (microLead) {{
            microLead.innerText = 'F_opt $' + liveImpliedForward.toLocaleString('en-US', {{minimumFractionDigits:2, maximumFractionDigits:2}}) + ' (' + (liveForwardDisloc >= 0 ? '+' : '') + liveForwardDisloc.toFixed(2) + '$)';
            microLead.style.color = leadCol;
        }}
        const microHedge = document.getElementById('micro-hedge-val');
        if (microHedge) {{
            microHedge.innerText = (liveDealerHedgeGC >= 0 ? '+' : '') + liveDealerHedgeGC.toFixed(1) + ' HĐ GC';
            microHedge.style.color = hedgeCol;
        }}
        const microCvd = document.getElementById('micro-cvd-val');
        if (microCvd) {{
            microCvd.innerText = 'CVD ' + (liveCvdContracts >= 0 ? '+' : '') + Math.round(liveCvdContracts) + ' HĐ • Mua ' + liveBuyPct.toFixed(1) + '%';
            microCvd.style.color = cvdCol;
        }}
        const microBar = document.getElementById('micro-bvc-bar');
        if (microBar) microBar.style.width = liveBuyPct.toFixed(1) + '%';
        const microKyle = document.getElementById('micro-kyle-val');
        if (microKyle) microKyle.innerText = liveKyleLabel;

        // 4b. Compute & Update Gamma Flip Integrity Verdict (True Flip vs. Fakeout Trap) in <0.1ms
        const fv = computeLiveFlipVerdict(
            currentGoldPrice,
            window.INITIAL_META.zero_gamma_flip,
            liveDealerHedgeGC,
            liveForwardDisloc,
            liveBuyPct,
            liveKyleLabel
        );
        liveFlipVerdict = fv.txt;
        liveFlipColor = fv.col;

        const hudFv = document.getElementById('hud-flip-verdict');
        const hudFvBox = document.getElementById('hud-flip-verdict-box');
        if (hudFv) {{
            hudFv.innerText = liveFlipVerdict;
            hudFv.style.color = liveFlipColor;
        }}
        if (hudFvBox) {{
            hudFvBox.style.borderColor = liveFlipColor;
            hudFvBox.style.borderLeftColor = liveFlipColor;
        }}
        const microFv = document.getElementById('micro-flip-verdict');
        if (microFv) {{
            microFv.innerText = liveFlipVerdict;
            microFv.style.color = liveFlipColor;
        }}

        // 4c. Real-time sync of KPI CME price, Spine price, and ±10 Strikes window in Microstructure Table
        const fmtSpot = '$' + currentGoldPrice.toLocaleString('en-US', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});
        const kpiCmeEl = document.getElementById('kpi-cme-price');
        if (kpiCmeEl) kpiCmeEl.innerText = fmtSpot;
        const spinePriceEl = document.getElementById('spine-current-price');
        if (spinePriceEl) spinePriceEl.innerText = fmtSpot;

        const strikeRows = document.querySelectorAll('tr.micro-strike-row');
        if (strikeRows && strikeRows.length > 0) {{
            let bestStrikeIdx = 0;
            let bestDist = Infinity;
            strikeRows.forEach((row, idx) => {{
                const stk = parseFloat(row.getAttribute('data-strike') || '0');
                const dist = Math.abs(stk - currentGoldPrice);
                if (dist < bestDist) {{
                    bestDist = dist;
                    bestStrikeIdx = idx;
                }}
            }});
            strikeRows.forEach((row, idx) => {{
                const inWindow = Math.abs(idx - bestStrikeIdx) <= 10;
                const isSpotRow = (idx === bestStrikeIdx);
                row.style.display = inWindow ? '' : 'none';
                if (isSpotRow) {{
                    row.classList.add('row-spot');
                    row.style.background = 'rgba(56, 189, 248, 0.12)';
                    row.style.boxShadow = 'inset 3px 0 0 #38BDF8';
                }} else {{
                    row.classList.remove('row-spot');
                    row.style.background = '';
                    row.style.boxShadow = '';
                }}
                const spotBadge = row.querySelector('.micro-spot-badge');
                if (spotBadge) {{
                    if (isSpotRow) {{
                        spotBadge.style.display = '';
                        spotBadge.innerText = '👉 SPOT: ' + fmtSpot;
                    }} else {{
                        spotBadge.style.display = 'none';
                    }}
                }}
            }});
        }}

        // 5. Recompute 3-second tactical context (Command Bar + Spine + KHOI 6) & repaint Canvas
        updateRealtimeTacticalCockpit();
        requestAnimationFrame(drawNeiroOverlay);
    }}

    window.onLiveTick = function(data) {{
        if (data && data.price) {{
            applyLiveTick(data.price, data.volume || null, true);
        }}
    }};

    function formatVnTimestamp(unixSec, includeDate = true) {{
        const vnDate = new Date((Number(unixSec) + 7 * 3600) * 1000);
        const dd = String(vnDate.getUTCDate()).padStart(2, '0');
        const mm = String(vnDate.getUTCMonth() + 1).padStart(2, '0');
        const hh = String(vnDate.getUTCHours()).padStart(2, '0');
        const mi = String(vnDate.getUTCMinutes()).padStart(2, '0');
        return includeDate ? (dd + '/' + mm + ' ' + hh + ':' + mi + ' VN') : (hh + ':' + mi);
    }}

    function initNeiroGoldChart() {{
        const container = document.getElementById('neiro-tv-chart');
        const canvas = document.getElementById('neiro-canvas');
        if (!container || !window.LightweightCharts) return;

        neiroChart = LightweightCharts.createChart(container, {{
            width: container.clientWidth,
            height: container.clientHeight || 540,
            layout: {{
                background: {{ type: 'solid', color: '#000000' }},
                textColor: '#94A3B8',
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 11,
            }},
            localization: {{
                timeFormatter: (timestamp) => formatVnTimestamp(timestamp, true),
            }},
            grid: {{
                vertLines: {{ color: '#0A0F18' }},
                horzLines: {{ color: '#0A0F18' }},
            }},
            crosshair: {{
                mode: LightweightCharts.CrosshairMode.Normal,
                vertLine: {{ color: '#38BDF8', width: 1, style: 3 }},
                horzLine: {{ color: '#38BDF8', width: 1, style: 3 }},
            }},
            rightPriceScale: {{
                borderColor: '#1E293B',
                scaleMargins: {{ top: 0.10, bottom: 0.10 }},
            }},
            timeScale: {{
                borderColor: '#1E293B',
                timeVisible: true,
                secondsVisible: false,
                barSpacing: 20,
                minBarSpacing: 8,
                rightOffset: 12,
                tickMarkFormatter: (time) => formatVnTimestamp(time, currentPeriodSec >= 86400),
            }},
        }});

        candleSeries = neiroChart.addCandlestickSeries({{
            upColor: '#22C55E',
            downColor: '#EF4444',
            borderVisible: true,
            borderUpColor: '#22C55E',
            borderDownColor: '#EF4444',
            wickUpColor: '#22C55E',
            wickDownColor: '#EF4444',
        }});

        buildHistoricalGoldBars(60, '1m');
        updateSqueezeHud(currentGoldPrice);
        updateRealtimeTacticalCockpit();
        updateSyncBadgeHonest();

        livePriceLine = candleSeries.createPriceLine({{
            price: currentGoldPrice,
            color: '#F43F5E',
            lineWidth: 2,
            lineStyle: LightweightCharts.LineStyle.Solid,
            axisLabelVisible: true,
            title: 'F0 LIVE',
        }});

        syncSecondaryPriceLines();

        const handleResize = () => {{
            if (!container || !neiroChart) return;
            const newW = container.clientWidth;
            const newH = container.clientHeight || 540;
            neiroChart.applyOptions({{ width: newW, height: newH }});
            if (canvas) {{
                canvas.width = newW;
                canvas.height = newH;
            }}
            drawNeiroOverlay();
        }};

        window.addEventListener('resize', handleResize);
        neiroChart.timeScale().subscribeVisibleTimeRangeChange(() => drawNeiroOverlay());
        neiroChart.timeScale().subscribeVisibleLogicalRangeChange(() => drawNeiroOverlay());

        if (canvas) {{
            canvas.addEventListener('mousemove', (e) => {{
                const rect = canvas.getBoundingClientRect();
                const mx = e.clientX - rect.left;
                const my = e.clientY - rect.top;
                const rightX = canvas.width - 70;
                const panelW = 5 * 64 + 8;
                const panelX = rightX - panelW;
                if (mx >= panelX - 4 && mx <= rightX) {{
                    const opts = window.INITIAL_OPTIONS || [];
                    let closest = null;
                    let minDist = 16;
                    let closestY = null;
                    opts.forEach(o => {{
                        const y = candleSeries.priceToCoordinate(o.strike);
                        if (y !== null) {{
                            const d = Math.abs(y - my);
                            if (d < minDist) {{
                                minDist = d;
                                closest = o;
                                closestY = y;
                            }}
                        }}
                    }});
                    hoveredOption = closest;
                    hoveredY = closestY;
                }} else {{
                    hoveredOption = null;
                    hoveredY = null;
                }}
                drawNeiroOverlay();
            }});
            canvas.addEventListener('mouseleave', () => {{
                hoveredOption = null;
                hoveredY = null;
                drawNeiroOverlay();
            }});
        }}
        neiroChart.subscribeCrosshairMove(() => {{
            drawNeiroOverlay();
        }});

        handleResize();
    }}

    let hoveredOption = null;
    let hoveredY = null;

    // ----------------------------------------------------------------------------
    // Canvas Overlay Engine: 5-Column Orderflow + Greeks & Air Pocket Matrix
    // ----------------------------------------------------------------------------
    function drawNeiroOverlay() {{
        const canvas = document.getElementById('neiro-canvas');
        if (!canvas || !neiroChart || !candleSeries) return;
        const ctx = canvas.getContext('2d');
        const w = canvas.width;
        const h = canvas.height;
        ctx.clearRect(0, 0, w, h);

        const m = window.INITIAL_META;
        const rightX = w - 70;
        const colW = 64;
        const cols = [
            {{ key: 'currentNetFLOW', name: 'FLOW',  unit: 'GC',  pos: '#22C55E', neg: '#F43F5E', bPos: '#4ADE80', bNeg: '#FB7185' }},
            {{ key: 'currentNetGEX',  name: 'GEX',   unit: 'M',   pos: '#10B981', neg: '#EF4444', bPos: '#34D399', bNeg: '#F87171' }},
            {{ key: 'currentNetVEX',  name: 'VEX',   unit: 'M',   pos: '#06B6D4', neg: '#0284C7', bPos: '#22D3EE', bNeg: '#38BDF8' }},
            {{ key: 'currentNetCHEX', name: 'CHEX',  unit: 'M/d', pos: '#A855F7', neg: '#7E22CE', bPos: '#C084FC', bNeg: '#D8B4FE' }},
            {{ key: 'currentNetTEX',  name: 'THETA', unit: 'M/d', pos: '#F59E0B', neg: '#D97706', bPos: '#FBBF24', bNeg: '#FCD34D' }},
        ];
        const panelW = cols.length * colW + 8;
        const panelX = rightX - panelW;
        const chartW = panelX - 6;

        // Live Candle Orderflow Footprint Badge right next to current F0 LIVE price line
        const yLive = candleSeries.priceToCoordinate(currentGoldPrice);
        if (yLive !== null && yLive >= 36 && yLive <= h - 24) {{
            const fpTxt = '⚡ Δ ' + (liveCandleDelta >= 0 ? '+' : '') + liveCandleDelta.toFixed(1) + ' HĐ | CVD ' + (liveCvdContracts >= 0 ? '+' : '') + Math.round(liveCvdContracts) + ' | VPIN ' + liveVpinPct.toFixed(1) + '%';
            ctx.font = 'bold 9.5px "JetBrains Mono", monospace';
            const fpW = ctx.measureText(fpTxt).width + 12;
            const fpX = Math.max(14, chartW - fpW - 10);
            const fpY = Math.max(30, yLive + 4);
            ctx.fillStyle = 'rgba(15, 23, 42, 0.94)';
            ctx.fillRect(fpX, fpY, fpW, 15);
            ctx.strokeStyle = liveCandleDelta >= 0 ? '#22C55E' : '#F43F5E';
            ctx.lineWidth = 1;
            ctx.strokeRect(fpX, fpY, fpW, 15);
            ctx.textAlign = 'left';
            ctx.fillStyle = liveCandleDelta >= 0 ? '#4ADE80' : '#FB7185';
            ctx.fillText(fpTxt, fpX + 6, fpY + 11);
        }}

        // 1. Right Greeks Panel Background
        ctx.fillStyle = 'rgba(5, 7, 11, 0.82)';
        ctx.fillRect(panelX - 4, 0, panelW, h);
        ctx.strokeStyle = 'rgba(30, 41, 59, 0.7)';
        ctx.lineWidth = 1;
        ctx.strokeRect(panelX - 4, 0, panelW, h);

        // 2. Secondary Structural Zones (Air Pockets & Institutional FVGs) — visible in Full Overlay Mode
        if (!overlayCompactMode) {{
        const airPockets = m.air_pockets || [];
        airPockets.forEach(ap => {{
            const pFrom = parseFloat(ap.from || 0);
            const pTo = parseFloat(ap.to || 0);
            if (!pFrom || !pTo) return;
            const y1 = candleSeries.priceToCoordinate(Math.max(pFrom, pTo));
            const y2 = candleSeries.priceToCoordinate(Math.min(pFrom, pTo));
            if (y1 !== null && y2 !== null) {{
                const topY = Math.min(y1, y2);
                const botY = Math.max(y1, y2);
                const bandH = Math.max(14, botY - topY);
                if (topY <= h && botY >= 0) {{
                    // A. Main Chart Canvas Area:
                    ctx.fillStyle = 'rgba(245, 158, 11, 0.12)';
                    ctx.fillRect(0, topY, chartW, bandH);
                    ctx.strokeStyle = '#F59E0B';
                    ctx.setLineDash([4, 4]);
                    ctx.lineWidth = 1;
                    ctx.strokeRect(0, topY, chartW, bandH);
                    ctx.setLineDash([]);

                    ctx.font = 'bold 9.5px "JetBrains Mono", monospace';
                    ctx.textAlign = 'left';
                    ctx.fillStyle = '#FACC15';
                    ctx.fillText('⚠️ AIR POCKET VACUUM [$' + Math.min(pFrom, pTo).toFixed(0) + ' - $' + Math.max(pFrom, pTo).toFixed(0) + '] · NGUY CƠ TRƯỢT DÀI (CẤM ĐỠ DAO)', 20, topY + Math.min(bandH - 3, 13));

                    // B. Right Greeks / Orderflow Panel Area (User requested: highlight right profile):
                    ctx.fillStyle = 'rgba(245, 158, 11, 0.22)';
                    ctx.fillRect(panelX - 4, topY, panelW, bandH);
                    ctx.strokeStyle = '#F59E0B';
                    ctx.setLineDash([3, 3]);
                    ctx.lineWidth = 1;
                    ctx.strokeRect(panelX - 4, topY, panelW, bandH);
                    ctx.setLineDash([]);

                    // Amber caution badge inside right panel
                    const bW = Math.min(panelW - 14, 210);
                    const bX = panelX + (panelW - bW) / 2 - 4;
                    const bY = topY + Math.max(1, (bandH - 15) / 2);
                    ctx.fillStyle = 'rgba(15, 23, 42, 0.92)';
                    ctx.fillRect(bX, bY, bW, 15);
                    ctx.strokeStyle = '#F59E0B';
                    ctx.lineWidth = 1;
                    ctx.strokeRect(bX, bY, bW, 15);
                    ctx.fillStyle = '#FDE047';
                    ctx.font = 'bold 8.5px "JetBrains Mono", monospace';
                    ctx.textAlign = 'center';
                    ctx.fillText('⚠️ AIR POCKET [CẤM ĐỠ] $' + Math.min(pFrom, pTo).toFixed(0) + '-' + Math.max(pFrom, pTo).toFixed(0), bX + bW / 2, bY + 11);
                }}
            }}
        }});

        // 2b. Draw Validated Institutional FVG Zones (ADR-026: Bullish Green / Bearish Red + 50% Retrace Line)
        const instFvgs = m.institutional_fvgs || [];
        instFvgs.forEach(fvg => {{
            const gLo = parseFloat(fvg.low || 0);
            const gHi = parseFloat(fvg.high || 0);
            const mid50 = parseFloat(fvg.midpoint_50 || 0);
            if (!gLo || !gHi) return;
            const yHi = candleSeries.priceToCoordinate(gHi);
            const yLo = candleSeries.priceToCoordinate(gLo);
            if (yHi !== null && yLo !== null) {{
                const topY = Math.min(yHi, yLo);
                const botY = Math.max(yHi, yLo);
                const bandH = Math.max(10, botY - topY);
                if (topY <= h && botY >= 0) {{
                    const isBull = fvg.direction === 'BULLISH';
                    const fCol = isBull ? '#22C55E' : '#EF4444';
                    ctx.fillStyle = isBull ? 'rgba(34, 197, 94, 0.09)' : 'rgba(239, 68, 68, 0.09)';
                    ctx.fillRect(0, topY, chartW, bandH);
                    ctx.strokeStyle = fCol;
                    ctx.setLineDash([2, 3]);
                    ctx.lineWidth = 1;
                    ctx.strokeRect(0, topY, chartW, bandH);
                    ctx.setLineDash([]);
                    if (mid50) {{
                        const yMid = candleSeries.priceToCoordinate(mid50);
                        if (yMid !== null && yMid >= 0 && yMid <= h) {{
                            ctx.strokeStyle = fCol;
                            ctx.setLineDash([4, 2]);
                            ctx.beginPath();
                            ctx.moveTo(0, yMid);
                            ctx.lineTo(chartW, yMid);
                            ctx.stroke();
                            ctx.setLineDash([]);
                        }}
                    }}
                    ctx.font = 'bold 9px "JetBrains Mono", monospace';
                    ctx.textAlign = 'left';
                    ctx.fillStyle = fCol;
                    ctx.fillText('INSTITUTIONAL FVG 50% $' + mid50.toFixed(1) + ' | 75% $' + parseFloat(fvg.zone_75 || mid50).toFixed(1), 20, topY + Math.min(bandH - 2, 11));
                }}
            }}
        }});
        }}

        // 3. Key Quant Options Levels: Core 3 Structure Lines + Active Strategy Entry/SL/TP (+ Full Mode Extras)
        const keyLevels = [
            {{ p: m.call_wall,          c: '#EF4444', d: [6, 4], txt: 'CALL WALL $' + Math.round(m.call_wall) + ' · OI ' + (m.call_wall_oi || 0).toLocaleString() + ' · Siege: ' + (m.call_wall_siege || 0).toFixed(2) + 'x' }},
            {{ p: m.put_wall,           c: '#22C55E', d: [6, 4], txt: 'PUT WALL $' + Math.round(m.put_wall) + ' · OI ' + (m.put_wall_oi || 0).toLocaleString() + ' · Siege: ' + (m.put_wall_siege || 0).toFixed(2) + 'x' }},
            {{ p: m.zero_gamma_flip,    c: '#FACC15', d: [4, 4], txt: 'GAMMA FLIP (Trục cân đối) $' + Math.round(m.zero_gamma_flip) + ' · [' + (liveFlipVerdict.split(':')[0] || 'KIỂM ĐỊNH') + ']' }},
        ];
        if (!overlayCompactMode) {{
            keyLevels.push(
                {{ p: m.strike_above,       c: '#4ADE80', d: [2, 3], txt: 'GAMMA SQUEEZE ↑ > $' + Math.round(m.strike_above) + ' → TP $' + Math.round(m.next_above) }},
                {{ p: m.strike_below,       c: '#F87171', d: [2, 3], txt: 'GAMMA SQUEEZE ↓ < $' + Math.round(m.strike_below) + ' → TP $' + Math.round(m.next_below) }},
                {{ p: m.charm_peak_strike,  c: '#C084FC', d: [4, 4], txt: 'CHARM (CHEX) · GHÌM GIÁ ĐÊM ' + (m.charm_peak_val || 0).toFixed(1) + 'M/d' }},
                {{ p: m.vanna_peak_strike,  c: '#22D3EE', d: [4, 4], txt: 'VANNA (VEX) · V-REBOUND ' + (m.vanna_peak_val || 0).toFixed(1) + 'M' }}
            );
        }}
        if (liveTacticalMatrix) {{
            const act = [liveTacticalMatrix.squeeze, liveTacticalMatrix.fade, liveTacticalMatrix.rebound, liveTacticalMatrix.breakdown].filter(s => s && s.active);
            if (act.length > 0) {{
                const topAct = act.slice().sort((a, b) => Math.abs(a.entry - currentGoldPrice) - Math.abs(b.entry - currentGoldPrice))[0];
                keyLevels.push(
                    {{ p: topAct.entry, c: topAct.side === 'BUY' ? '#4ADE80' : '#FB7185', d: [3, 2], txt: 'ACTIVE ENTRY ' + topAct.side + ' $' + topAct.entry.toFixed(2) }},
                    {{ p: topAct.sl,    c: '#EF4444', d: [2, 2], txt: 'SL $' + topAct.sl.toFixed(2) }},
                    {{ p: topAct.tp,    c: '#38BDF8', d: [2, 2], txt: 'TP $' + topAct.tp.toFixed(2) }}
                );
            }}
        }}

        keyLevels.forEach(L => {{
            if (!L.p) return;
            const y = candleSeries.priceToCoordinate(L.p);
            if (y !== null && y >= 0 && y <= h) {{
                ctx.strokeStyle = L.c;
                ctx.setLineDash(L.d);
                ctx.lineWidth = 1.3;
                ctx.beginPath();
                ctx.moveTo(0, y);
                ctx.lineTo(rightX, y);
                ctx.stroke();
                ctx.setLineDash([]);

                ctx.font = 'bold 9.5px "JetBrains Mono", monospace';
                ctx.textAlign = 'right';
                const tw = ctx.measureText(L.txt).width;
                ctx.fillStyle = 'rgba(6, 8, 14, 0.90)';
                ctx.fillRect(chartW - tw - 14, y - 12, tw + 10, 14);
                ctx.strokeStyle = L.c;
                ctx.lineWidth = 1;
                ctx.strokeRect(chartW - tw - 14, y - 12, tw + 10, 14);
                ctx.fillStyle = L.c;
                ctx.fillText(L.txt, chartW - 9, y - 2);
            }} else if (y !== null && y < 0) {{
                // Pinned Top Edge Indicator
                const edgeY = 14;
                ctx.font = 'bold 9.5px "JetBrains Mono", monospace';
                ctx.textAlign = 'right';
                const shortTxt = '▲ ' + L.txt.split('·')[0];
                const tw = ctx.measureText(shortTxt).width;
                ctx.fillStyle = 'rgba(15, 23, 42, 0.92)';
                ctx.fillRect(chartW - tw - 14, edgeY - 11, tw + 10, 14);
                ctx.strokeStyle = L.c;
                ctx.lineWidth = 1;
                ctx.strokeRect(chartW - tw - 14, edgeY - 11, tw + 10, 14);
                ctx.fillStyle = L.c;
                ctx.fillText(shortTxt, chartW - 9, edgeY);
            }} else if (y !== null && y > h) {{
                // Pinned Bottom Edge Indicator
                const edgeY = h - 8;
                ctx.font = 'bold 9.5px "JetBrains Mono", monospace';
                ctx.textAlign = 'right';
                const shortTxt = '▼ ' + L.txt.split('·')[0];
                const tw = ctx.measureText(shortTxt).width;
                ctx.fillStyle = 'rgba(15, 23, 42, 0.92)';
                ctx.fillRect(chartW - tw - 14, edgeY - 11, tw + 10, 14);
                ctx.strokeStyle = L.c;
                ctx.lineWidth = 1;
                ctx.strokeRect(chartW - tw - 14, edgeY - 11, tw + 10, 14);
                ctx.fillStyle = L.c;
                ctx.fillText(shortTxt, chartW - 9, edgeY);
            }}
        }});

        // 4. Per-strike Greeks exposure profile (GEX | VEX | CHEX | THETA)
        const opts = window.INITIAL_OPTIONS || [];
        if (opts.length && opts[0].currentNetGEX !== undefined) {{
            cols.forEach((c, ci) => {{
                const cx = panelX + ci * colW + colW / 2;
                
                // Dynamic Visible Normalization
                let visibleMaxAbs = 1e-9;
                let globalMaxAbs = 1e-9;
                opts.forEach(o => {{
                    const val = Math.abs(o[c.key] || 0);
                    globalMaxAbs = Math.max(globalMaxAbs, val);
                    const y = candleSeries.priceToCoordinate(o.strike);
                    if (y !== null && y >= 28 && y <= h - 4) {{
                        visibleMaxAbs = Math.max(visibleMaxAbs, val);
                    }}
                }});
                if (visibleMaxAbs < 1e-6) visibleMaxAbs = globalMaxAbs > 1e-6 ? globalMaxAbs : 1.0;

                // Center divider line
                ctx.strokeStyle = 'rgba(148, 163, 184, 0.18)';
                ctx.beginPath();
                ctx.moveTo(cx, 26);
                ctx.lineTo(cx, h);
                ctx.stroke();

                // Column Header: Name
                ctx.fillStyle = c.name === 'FLOW' ? '#FACC15' : (c.name === 'VEX' ? '#22D3EE' : (c.name === 'CHEX' ? '#C084FC' : (c.name === 'GEX' ? '#34D399' : '#FBBF24')));
                ctx.font = 'bold 10px "JetBrains Mono", monospace';
                ctx.textAlign = 'center';
                ctx.fillText(c.name, cx, 12);

                // Column Subheader: Visible Magnitude Scale (e.g. ±2.8M or ±1.1M/d)
                const scaleTxt = '±' + (visibleMaxAbs >= 10 ? visibleMaxAbs.toFixed(0) : (visibleMaxAbs >= 1 ? visibleMaxAbs.toFixed(1) : visibleMaxAbs.toFixed(2))) + c.unit;
                ctx.fillStyle = 'rgba(148, 163, 184, 0.75)';
                ctx.font = '8px "JetBrains Mono", monospace';
                ctx.fillText(scaleTxt, cx, 22);

                // Render Per-Strike Bars with Square-Root / Sublinear Boost
                const maxBarW = colW / 2 - 3;
                opts.forEach(o => {{
                    const y = candleSeries.priceToCoordinate(o.strike);
                    const v = o[c.key] || 0;
                    if (y === null || y < 28 || y > h - 4 || v === 0) return;
                    
                    // Square-root boost: makes small VEX and CHEX clearly visible without blowing out
                    const norm = Math.min(1.0, Math.abs(v) / visibleMaxAbs);
                    const scaled = Math.pow(norm, 0.50);
                    let len = scaled * maxBarW;
                    if (Math.abs(v) > 0.0001) len = Math.max(3.5, len);

                    const barX = v >= 0 ? cx : cx - len;
                    const barH = c.name === 'FLOW' ? 7 : 6;
                    ctx.fillStyle = v >= 0 ? c.pos : c.neg;
                    ctx.fillRect(barX, y - barH / 2, len, barH);
                    ctx.strokeStyle = v >= 0 ? c.bPos : c.bNeg;
                    ctx.lineWidth = 0.8;
                    ctx.strokeRect(barX, y - barH / 2, len, barH);

                    if (c.name === 'FLOW' && o.isWhale) {{
                        ctx.fillStyle = '#FACC15';
                        ctx.font = 'bold 8px "JetBrains Mono", monospace';
                        ctx.textAlign = 'left';
                        ctx.fillText('⚡W', panelX - 2, y + 3);
                    }}
                }});
            }});
        }}

        // 5. Interactive Tooltip when hovering over 5-Column Orderflow + Greeks panel
        if (hoveredOption && hoveredY !== null && hoveredY >= 28 && hoveredY <= h - 4) {{
            ctx.strokeStyle = 'rgba(250, 204, 21, 0.6)';
            ctx.setLineDash([2, 2]);
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(panelX - 4, hoveredY);
            ctx.lineTo(rightX, hoveredY);
            ctx.stroke();
            ctx.setLineDash([]);

            const flowVal = hoveredOption.currentNetFLOW || 0;
            const ttLines = [
                'Strike $' + hoveredOption.strike.toFixed(0) + (hoveredOption.isWhale ? ' ⚡WHALE' : ''),
                'FLOW: ' + (flowVal >= 0 ? '+' : '') + flowVal.toFixed(1) + ' HĐ GC',
                'Vol C/P: ' + (hoveredOption.c_vol || 0) + ' / ' + (hoveredOption.p_vol || 0),
                'GEX: ' + (hoveredOption.currentNetGEX >= 0 ? '+' : '') + hoveredOption.currentNetGEX.toFixed(1) + 'M',
                'VEX: ' + (hoveredOption.currentNetVEX >= 0 ? '+' : '') + hoveredOption.currentNetVEX.toFixed(2) + 'M',
                'CHEX: ' + (hoveredOption.currentNetCHEX >= 0 ? '+' : '') + hoveredOption.currentNetCHEX.toFixed(2) + 'M/d',
            ];
            const ttW = 148;
            const ttH = 88;
            const ttX = Math.max(10, panelX - ttW - 8);
            const ttY = Math.min(h - ttH - 10, Math.max(10, hoveredY - ttH / 2));
            ctx.fillStyle = 'rgba(15, 23, 42, 0.96)';
            ctx.fillRect(ttX, ttY, ttW, ttH);
            ctx.strokeStyle = '#FACC15';
            ctx.lineWidth = 1;
            ctx.strokeRect(ttX, ttY, ttW, ttH);

            ctx.textAlign = 'left';
            ctx.font = 'bold 9.5px "JetBrains Mono", monospace';
            ctx.fillStyle = '#F8FAFC';
            ctx.fillText(ttLines[0], ttX + 6, ttY + 13);
            ctx.font = '8.5px "JetBrains Mono", monospace';
            ctx.fillStyle = flowVal >= 0 ? '#4ADE80' : '#FB7185';
            ctx.fillText(ttLines[1], ttX + 6, ttY + 26);
            ctx.fillStyle = '#FACC15';
            ctx.fillText(ttLines[2], ttX + 6, ttY + 39);
            ctx.fillStyle = hoveredOption.currentNetGEX >= 0 ? '#4ADE80' : '#F87171';
            ctx.fillText(ttLines[3], ttX + 6, ttY + 52);
            ctx.fillStyle = '#22D3EE';
            ctx.fillText(ttLines[4], ttX + 6, ttY + 65);
            ctx.fillStyle = '#C084FC';
            ctx.fillText(ttLines[5], ttX + 6, ttY + 78);
        }}
    }}

    // =========================================================================
    // 100% ONLINE ZERO-TOUCH CLOUD SYNC & REALTIME WEBSOCKET ORDERFLOW ENGINE
    // =========================================================================
    function parseIsoEpochMs(tsStr) {{
        if (!tsStr) return 0;
        const ms = Date.parse(String(tsStr));
        return Number.isFinite(ms) ? ms : 0;
    }}
    let lastCloudTimestamp = window.INITIAL_META ? (window.INITIAL_META.timestamp_utc || null) : null;
    let lastStaticSnapshotEpochMs = parseIsoEpochMs(lastCloudTimestamp);
    let buildEpoch = Date.now();
    let lastWsTickEpoch = 0;
    let lastWsRefPrice = null;

    function updateSyncTimeAgo() {{
        const el = document.getElementById('sync-time-ago');
        if (!el) return;
        const diffSec = Math.floor((Date.now() - buildEpoch) / 1000);
        if (diffSec < 60) {{
            el.innerText = '(vừa đồng bộ)';
        }} else {{
            const diffMin = Math.floor(diffSec / 60);
            el.innerText = '(' + diffMin + 'p trước)';
        }}
    }}

    async function fetchCloudVersionJson() {{
        const ts = Date.now();
        const urls = [
            'http://127.0.0.1:8765/version.json?_t=' + ts,
            'version.json?_t=' + ts,
            'https://raw.githubusercontent.com/DaniNguyen2509/Neiro-Gold-Quant/main/version.json?_t=' + ts
        ];
        if (window.location.protocol === 'file:') {{
            urls.splice(1, 1); // Skip relative file:// fetch to avoid CORS error in console
        }}
        for (let i = 0; i < urls.length; i++) {{
            try {{
                const res = await fetch(urls[i], {{ cache: 'no-store' }});
                if (res && res.ok) {{
                    return await res.json();
                }}
            }} catch (err) {{
                // Try next endpoint seamlessly
            }}
        }}
        return null;
    }}

    function mergeLiveCandles(newCandles, tfKey = '1m') {{
        if (!Array.isArray(newCandles) || newCandles.length === 0) return;
        const targetList = (tfKey === '1m')
            ? (window.INITIAL_CANDLES || [])
            : ((window.INITIAL_TF_CANDLES && window.INITIAL_TF_CANDLES[tfKey]) || []);
        const byTime = new Map();
        for (let i = 0; i < targetList.length; i++) {{
            const b = targetList[i];
            if (b && b.time) byTime.set(Number(b.time), b);
        }}
        for (let i = 0; i < newCandles.length; i++) {{
            const b = newCandles[i];
            if (b && b.time) byTime.set(Number(b.time), b);
        }}
        const merged = Array.from(byTime.values()).sort((a, b) => a.time - b.time).slice(-320);
        if (tfKey === '1m') {{
            window.INITIAL_CANDLES = merged;
        }}
        if (window.INITIAL_TF_CANDLES) {{
            window.INITIAL_TF_CANDLES[tfKey] = merged;
        }}
        if (tfKey === currentTf && candleSeries && merged.length > 0) {{
            const lastBar = merged[merged.length - 1];
            activeCandle = {{
                time: lastBar.time,
                open: lastBar.open,
                high: lastBar.high,
                low: lastBar.low,
                close: lastBar.close,
                volume: Number(lastBar.volume || 0),
                delta: lastBar.delta || 0,
            }};
            evaluateBarOrderflow(merged, tfKey);
            candleSeries.update({{
                time: lastBar.time,
                open: lastBar.open,
                high: lastBar.high,
                low: lastBar.low,
                close: lastBar.close,
            }});
            applyLiveTick(lastBar.close, null, true);
        }}
    }}

    let lastYahooPollEpoch = 0;

    async function pollLiveYahooChart(tf = currentTf) {{
        const ts = Date.now();
        lastYahooPollEpoch = ts;
        try {{
            const res = await fetch('http://127.0.0.1:8765/api/yahoo_gc?tf=' + encodeURIComponent(tf) + '&_t=' + ts, {{ cache: 'no-store' }});
            if (res && res.ok) {{
                const payload = await res.json();
                lastBridgeSuccessEpoch = Date.now();
                if (window.INITIAL_META) {{
                    window.INITIAL_META.timestamp_utc = new Date().toISOString();
                    if (payload && payload.market_open !== undefined) {{
                        window.INITIAL_META.market_open = Boolean(payload.market_open);
                    }}
                }}
                if (payload && payload.vpin_pct !== undefined) {{
                    liveVpinPct = Number(payload.vpin_pct);
                    if (payload.vpin_label) liveVpinLabel = String(payload.vpin_label);
                    if (payload.bvc_buy_pct !== undefined) liveBuyPct = Number(payload.bvc_buy_pct);
                    if (payload.bvc_cvd_contracts !== undefined) liveCvdContracts = Number(payload.bvc_cvd_contracts);
                    if (payload.kyle_lambda_label) liveKyleLabel = String(payload.kyle_lambda_label);
                    if (payload.atr_5m !== undefined) liveAtr5m = Number(payload.atr_5m);
                    lastAuthoritativeVpinEpoch = Date.now();
                }}
                if (payload && Array.isArray(payload.candles) && payload.candles.length > 0) {{
                    mergeLiveCandles(payload.candles, tf);
                }}
                if (payload && payload.latest_price) {{
                    applyLiveTick(Number(payload.latest_price), null, true);
                }} else {{
                    updateRealtimeTacticalCockpit();
                }}
                buildEpoch = Date.now();
                updateSyncTimeAgo();
                updateSyncBadgeHonest();
                return true;
            }}
        }} catch (e) {{
            // Local bridge not running; fallback to Cloud/Version JSON sync
        }}
        updateSyncBadgeHonest();
        return false;
    }}

    function hotPatchCloudMeta(data, opts = {{}}) {{
        if (!data || !window.INITIAL_META) return false;
        const incomingMs = parseIsoEpochMs(data.timestamp_utc);
        if (!opts.ignoreTimestamp && incomingMs > 0 && lastStaticSnapshotEpochMs > 0 && incomingMs < lastStaticSnapshotEpochMs) {{
            return false;
        }}
        if (incomingMs > 0) {{
            lastStaticSnapshotEpochMs = Math.max(lastStaticSnapshotEpochMs, incomingMs);
        }}
        const m = window.INITIAL_META;
        const nowMs = Date.now();
        const bridgeLive = Boolean(lastBridgeSuccessEpoch && (nowMs - lastBridgeSuccessEpoch) < 15000);
        const allowLiveMarketState = Boolean(opts.forceLive || !bridgeLive);

        if (allowLiveMarketState && data.market_open !== undefined) m.market_open = Boolean(data.market_open);
        if (data.call_wall) m.call_wall = data.call_wall;
        if (data.put_wall) m.put_wall = data.put_wall;
        if (data.zero_gamma_flip) m.zero_gamma_flip = data.zero_gamma_flip;
        if (data.strike_above) m.strike_above = data.strike_above;
        if (data.strike_below) m.strike_below = data.strike_below;
        if (data.expected_move_1s) m.expected_move_1s = data.expected_move_1s;
        if (data.total_net_gex !== undefined) {{
            m.total_net_gex = data.total_net_gex;
            const gCol = data.total_net_gex >= 0 ? '#4ADE80' : '#F87171';
            const gTxt = '$' + (data.total_net_gex >= 0 ? '+' : '') + data.total_net_gex.toFixed(1) + 'M';
            const el1 = document.getElementById('kpi-gex-val');
            const el2 = document.getElementById('hud-gex-val');
            if (el1) {{ el1.innerText = gTxt; el1.style.color = gCol; }}
            if (el2) {{ el2.innerText = gTxt; el2.style.color = gCol; }}
        }}
        if (data.total_net_vex !== undefined) {{
            m.total_net_vex = data.total_net_vex;
        }}
        if (data.total_net_chex !== undefined) {{
            m.total_net_chex = data.total_net_chex;
        }}
        if (data.implied_forward_price) liveImpliedForward = data.implied_forward_price;
        if (data.dealer_hedge_futures_flow !== undefined) liveDealerHedgeGC = data.dealer_hedge_futures_flow;
        if (allowLiveMarketState && data.bvc_cvd_contracts !== undefined) liveCvdContracts = data.bvc_cvd_contracts;
        if (allowLiveMarketState && data.bvc_buy_pct !== undefined) liveBuyPct = data.bvc_buy_pct;
        if (data.dynamic_vacuum && typeof data.dynamic_vacuum === 'object') {{
            m.dynamic_vacuum = data.dynamic_vacuum;
        }}
        if (Array.isArray(data.institutional_fvgs)) {{
            m.institutional_fvgs = data.institutional_fvgs;
        }}
        if (data.post_sweep_execution && typeof data.post_sweep_execution === 'object') {{
            m.post_sweep_execution = data.post_sweep_execution;
            const psRegime = String(data.post_sweep_execution.post_sweep_regime || 'MONITORING');
            const psLabel = String(data.post_sweep_execution.label_vi || 'THEO DÕI');
            const psCol = psRegime === 'TOXIC_CASCADE_BLOCKED'
                ? '#F43F5E'
                : (psRegime === 'POST_SWEEP_V_SHAPE'
                    ? '#4ADE80'
                    : (psRegime === 'POST_SWEEP_PULLBACK' ? '#38BDF8' : '#94A3B8'));
            const vacTitle = String((m.dynamic_vacuum && (m.dynamic_vacuum.label_vi || m.dynamic_vacuum.vacuum_label)) || '');
            ['hud-post-sweep-val', 'micro-post-sweep-val'].forEach((id) => {{
                const el = document.getElementById(id);
                if (el) {{
                    el.innerText = psLabel;
                    el.style.color = psCol;
                    if (vacTitle) el.title = vacTitle;
                }}
            }});
        }}
        if (allowLiveMarketState && Array.isArray(data.recent_candles) && data.recent_candles.length > 0) {{
            mergeLiveCandles(data.recent_candles, '1m');
        }}
        if (allowLiveMarketState && data.tf_candles && typeof data.tf_candles === 'object') {{
            Object.keys(data.tf_candles).forEach((k) => {{
                mergeLiveCandles(data.tf_candles[k], k);
            }});
        }}
        if (allowLiveMarketState && data.timestamp_utc) m.timestamp_utc = data.timestamp_utc;
        if (data.regime) m.regime = data.regime;
        if (data.call_wall_siege !== undefined) m.call_wall_siege = Number(data.call_wall_siege);
        if (data.put_wall_siege !== undefined) m.put_wall_siege = Number(data.put_wall_siege);
        if (data.major_up_wall) m.major_up_wall = Number(data.major_up_wall);
        if (data.major_down_wall) m.major_down_wall = Number(data.major_down_wall);
        if (data.has_up_air_pocket !== undefined) m.has_up_air_pocket = Boolean(data.has_up_air_pocket);
        if (data.has_down_air_pocket !== undefined) m.has_down_air_pocket = Boolean(data.has_down_air_pocket);
        if (allowLiveMarketState && data.vpin_pct !== undefined && (lastAuthoritativeVpinEpoch === 0 || (nowMs - lastAuthoritativeVpinEpoch) >= 15000 || incomingMs >= lastAuthoritativeVpinEpoch)) {{
            liveVpinPct = Number(data.vpin_pct);
            if (data.vpin_label) liveVpinLabel = String(data.vpin_label);
            if (data.kyle_lambda_label) liveKyleLabel = String(data.kyle_lambda_label);
            if (data.atr_5m !== undefined) liveAtr5m = Number(data.atr_5m);
            lastAuthoritativeVpinEpoch = Date.now();
        }}
        if (allowLiveMarketState && data.spot_price) {{
            yahooAnchorPrice = Number(data.spot_price);
            if (Math.abs(data.spot_price - currentGoldPrice) > 0.01) {{
                applyLiveTick(data.spot_price, null, true);
            }} else {{
                updateRealtimeTacticalCockpit();
                requestAnimationFrame(drawNeiroOverlay);
            }}
        }} else {{
            updateRealtimeTacticalCockpit();
            requestAnimationFrame(drawNeiroOverlay);
        }}
        return true;
    }}

    async function checkCloudSyncNow(isManual = false) {{
        const badge = document.getElementById('cloud-sync-badge');
        try {{
            if (badge && isManual) badge.innerText = '⟳ SYNCING...';
            if (isManual || (Date.now() - lastYahooPollEpoch > 4000)) {{
                await pollLiveYahooChart(currentTf);
            }}
            const data = await fetchCloudVersionJson();
            if (data && data.timestamp_utc) {{
                const incomingMs = parseIsoEpochMs(data.timestamp_utc);
                if (incomingMs > 0 && lastStaticSnapshotEpochMs > 0 && incomingMs <= lastStaticSnapshotEpochMs) {{
                    updateSyncBadgeHonest();
                    return;
                }}
                lastCloudTimestamp = data.timestamp_utc;
                lastCloudSuccessEpoch = Date.now();
                buildEpoch = Date.now();
                updateSyncTimeAgo();
                hotPatchCloudMeta(data);
                updateSyncBadgeHonest();
                return;
            }}
        }} catch (e) {{}}
        updateSyncBadgeHonest();
    }}

    // 100% Pure CME Gold Futures (GC=F) Real-Time Stream (No Crypto PAXG Proxy Contamination)
    const isLocalBridgeMode = (
        window.location.protocol === 'file:'
        || window.location.hostname === '127.0.0.1'
        || window.location.hostname === 'localhost'
    );
    const YAHOO_POLL_INTERVAL_MS = isLocalBridgeMode ? 2500 : 5000;

    function connectLiveGoldOrderflowStream() {{
        if (!isCmeGlobexMarketOpen()) {{
            updateSyncBadgeHonest();
            setTimeout(connectLiveGoldOrderflowStream, 30000);
            return;
        }}
        pollLiveYahooChart(currentTf);
        setTimeout(connectLiveGoldOrderflowStream, YAHOO_POLL_INTERVAL_MS);
    }}

    // Tự động kiểm tra Yahoo GC=F & Cloud mỗi 10s hoàn toàn tự động (Zero-Touch, Zero-Reload)
    setInterval(updateSyncTimeAgo, 15000);
    setInterval(() => checkCloudSyncNow(false), 10000);
    window.addEventListener('focus', () => checkCloudSyncNow(false));

    // Auto-init 100% hands-free on load
    window.addEventListener('DOMContentLoaded', () => {{
        setTimeout(initNeiroGoldChart, 60);
        setTimeout(connectLiveGoldOrderflowStream, 300);
        setTimeout(() => checkCloudSyncNow(false), 600);
    }});
    </script>
    """

    return {
        "neiro_css": neiro_css,
        "nav_topbar_html": nav_topbar_html,
        "neiro_container_html": neiro_container_html,
        "neiro_js_script": neiro_js_script,
        # Backward compatibility aliases
        "atas_css": neiro_css,
        "atas_container_html": neiro_container_html,
        "atas_js_script": neiro_js_script,
    }
