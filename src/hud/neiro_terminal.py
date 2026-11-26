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
    contract_symbol = str(meta.get("contract_symbol") or "GCZ26")
    option_symbol_val = str(meta.get("option_symbol") or "")
    expiration_date_val = str(meta.get("expiration_date") or "")
    expiration_iso_val = str(meta.get("expiration_date_iso") or "")

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
    post_sweep_dir = str(post_sweep.get("direction") or "").strip().upper()
    v_shape_lbl = f"V-SHAPE {post_sweep_dir}" if post_sweep_dir and post_sweep_dir != "NONE" else "V-SHAPE ĐẢO CHIỀU"
    post_sweep_compact = (
        "CẤM CẢN TÀU (VPIN CAO)" if post_sweep_regime == "TOXIC_CASCADE_BLOCKED"
        else (v_shape_lbl if post_sweep_regime == "POST_SWEEP_V_SHAPE"
              else ("CHỜ HỒI FVG 50%–75%" if post_sweep_regime == "POST_SWEEP_PULLBACK"
                    else "CHỜ TÍN HIỆU SWEEP"))
    )
    kyle_compact = (
        kyle_label
        .replace(" (ICEBERG LIMIT ABSORPTION)", " (ICEBERG)")
        .replace(" (VACUUM MARKET SWEEP)", " (VACUUM)")
        .replace("THANH KHOẢN SỔ LỆNH BÌNH THƯỜNG (BAR OLS)", "SỔ LỆNH BÌNH THƯỜNG")
        .replace("THANH KHOẢN SỔ LỆNH BÌNH THƯỜNG", "SỔ LỆNH BÌNH THƯỜNG")
        .replace("THANH KHOẢN BÌNH THƯỜNG", "SỔ LỆNH BÌNH THƯỜNG")
    )
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

    /* Chart & Canvas View: 2-Panel Side-by-Side Architecture */
    .neiro-body-container {
        display: flex; flex-direction: row; flex: 0 0 auto; width: 100%; height: 540px;
        position: relative; overflow: hidden; background: #000000;
        border: 1px solid #1E293B; border-radius: 6px; margin-bottom: 10px;
    }
    .neiro-body-container.expanded { height: 700px; }
    #tv-chart-wrapper {
        position: relative; flex: 1 1 auto; min-width: 0; height: 100%; background-color: #000000;
        transition: flex 0.15s ease, width 0.15s ease;
    }
    #neiro-tv-chart { width: 100%; height: 100%; }
    #neiro-canvas {
        position: absolute; top: 0; left: 0; width: 100%; height: 100%;
        pointer-events: none; z-index: 5;
    }

    /* Dedicated Right Profile Panel: 6 Columns [VOL | FLOW | GEX | VEX | CHEX | THETA] */
    #neiro-profile-wrapper {
        position: relative; flex: 0 0 340px; width: 340px; height: 100%;
        background: #080B12; border-left: 1px solid #1E293B;
        display: flex; flex-direction: column; overflow: hidden;
        z-index: 6; transition: flex 0.15s ease, width 0.15s ease;
    }
    #neiro-profile-wrapper.collapsed {
        display: none !important;
    }
    .neiro-profile-header {
        display: flex; align-items: center; justify-content: space-between;
        padding: 5px 8px; background: rgba(15, 23, 42, 0.95);
        border-bottom: 1px solid #1E293B; height: 26px; flex-shrink: 0;
        font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 700; color: #94A3B8;
    }
    .neiro-profile-title { display: flex; align-items: center; gap: 6px; color: #E2E8F0; }
    .neiro-profile-canvas-box {
        position: relative; flex: 1 1 auto; width: 100%; height: calc(100% - 26px); overflow: hidden;
    }
    #neiro-profile-canvas {
        position: absolute; top: 0; left: 0; width: 100%; height: 100%;
        cursor: crosshair;
    }

    /* Compact Floating Quant HUD Card (5 Core Signals - Top-Left of Chart) */
    .neiro-floating-hud {
        position: absolute; top: 10px; left: 12px; z-index: 10;
        display: flex; flex-direction: column; gap: 3.5px;
        background: rgba(8, 11, 18, 0.92); border: 1px solid #1E293B; border-radius: 5px;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.55);
        padding: 6px 10px; font-family: 'JetBrains Mono', monospace; font-size: 10.5px;
        max-width: min(580px, calc(100% - 24px)); pointer-events: none;
    }
    .hud-item { display: flex; align-items: center; gap: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .hud-label { color: #94A3B8; font-weight: 700; font-size: 10px; min-width: 105px; }

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
    @media (max-width: 900px) {
        #neiro-profile-wrapper {
            display: none;
            width: 100%;
            height: 320px;
            border-left: none;
            border-top: 1px solid #1E293B;
        }
        #neiro-profile-wrapper.mobile-open {
            display: flex;
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
                <span class="neiro-pill-lbl" style="color:#38BDF8; font-weight:800;">CVD:</span> <b id="top-cvd-val" style="color:{cvd_color}; background:rgba(255,255,255,0.08); padding:1px 6px; border-radius:3px; font-weight:800;">{bvc_cvd_val:+.0f} HĐ ({bvc_buy_pct:.0f}%B)</b>
                <span class="neiro-pill-lbl">MM HEDGE:</span> <b id="top-hedge-val" style="color:{hedge_color};">{dealer_hedge_val:+.0f} GC</b>
            </div>
        </div>

        <div class="neiro-top-right">
            <button id="btn-overlay-mode" class="timeframe-pill" onclick="toggleOverlayMode()" title="Chuyển lớp phủ Chart: Tinh gọn (Call/Put Wall, Gamma Flip, Cản/Sàn &amp; Trạm Options, Air Pocket, Entry/SL/TP) hoặc Đầy đủ (thêm Vanna, Charm, FVG)">
                Lớp phủ: Tinh gọn
            </button>
            <button id="btn-toggle-profile" class="timeframe-pill" onclick="toggleProfilePanel()" title="Ẩn hoặc hiện Panel 6 cột Profile [VOL | FLOW | GEX | VEX | CHEX | THETA] bên phải">
                Ẩn Profile
            </button>
            <button id="btn-chart-height" class="timeframe-pill" onclick="toggleChartHeight()" title="Phóng to hoặc thu gọn chiều cao biểu đồ">
                Mở rộng Chart
            </button>
            <button id="btn-cloud-worker" class="timeframe-pill" onclick="promptCloudFeedUrl()" title="Cài đặt URL Cloudflare Worker (xem realtime 24/7 trên điện thoại &amp; GitHub Pages)">
                Cloud Feed
            </button>
            <button id="btn-sync-cme" class="timeframe-pill" onclick="triggerRemoteCmeSync()" title="Kích hoạt cào CME Options mới nhất từ đám mây (không cần mở máy tính)">
                ⚡ Sync CME
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
            <span id="subbar-contract-label" class="neiro-watermark-text" style="color:#38BDF8; font-weight:700;">NEIRO-QUANT TERMINAL &bull; CME GOLD FUTURES [GC=F / {contract_symbol}]</span>
        </div>
        <div class="neiro-subbar-right">
            <span style="color:#64748B;">ATM: <b id="top-ticker-atm">${atm_strike:,.0f}</b> | IV: <b id="top-ticker-iv">{gvz_iv:.1f}%</b> | Zero Gamma: <b style="color:#FACC15;">${zero_gamma:,.1f}</b> | 1-&sigma;: <b id="kpi-move-val" style="color:#FACC15;">&plusmn;${expected_move:,.1f}</b></span>
        </div>
    </div>
    """

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

    # 3. Main M1 Chart Body with Compact Quant HUD (5 Core Rows)
    neiro_container_html = f"""
    <div class="neiro-body-container" id="neiro-view-container">
        <div id="tv-chart-wrapper">
            <!-- Compact Quant HUD Card at Top-Left of Chart -->
            <div class="neiro-floating-hud">
                <div class="hud-item">
                    <span class="hud-label">REGIME / FLIP:</span>
                    <b id="hud-gex-val" style="color:{regime_color};">${total_gex:+.1f}M</b>
                    <span style="color:#64748B;">&bull;</span>
                    <span id="hud-flip-verdict-box" style="border-left:2px solid {flip_verdict_col}; padding-left:5px;">
                        <b id="hud-flip-verdict" style="color:{flip_verdict_col}; font-size:10px;">{flip_verdict_lbl}</b>
                    </span>
                </div>
                <div class="hud-item">
                    <span class="hud-label">GAMMA SQUEEZE:</span>
                    <b id="hud-sqz-up" style="color:#4ADE80;">&gt; ${strike_above:,.0f} &rarr; TP ${next_above:,.0f}</b>
                    <span style="color:#64748B;">&bull;</span>
                    <b id="hud-sqz-down" style="color:#F87171;">&lt; ${strike_below:,.0f} &rarr; TP ${next_below:,.0f}</b>
                </div>
                <div class="hud-item">
                    <span class="hud-label">VPIN TOXIC:</span>
                    <b id="hud-vpin-val" style="color:{vpin_col}; font-size:10px;">{vpin_label}</b>
                </div>
                <div class="hud-item" style="display:flex; align-items:center; gap:8px;">
                    <span class="hud-label" style="color:#38BDF8; font-weight:800;">CVD ORDERFLOW:</span>
                    <b id="hud-cvd-val" style="color:{cvd_color}; font-size:11px; font-weight:800;">CVD {bvc_cvd_val:+,.0f} HĐ ({bvc_buy_pct:.0f}% Mua)</b>
                    <div style="flex:1; max-width:90px; height:5px; background:#EF4444; border-radius:2px; overflow:hidden;">
                        <div id="hud-bvc-bar" style="width:{bvc_buy_pct:.1f}%; height:100%; background:#22C55E; transition:width 0.12s linear;"></div>
                    </div>
                </div>
                <div class="hud-item">
                    <span class="hud-label">POST-SWEEP / KYLE:</span>
                    <b id="hud-post-sweep-val" style="color:{post_sweep_col}; font-size:10px;" title="{vac_label}">{post_sweep_compact}</b>
                    <span style="color:#64748B;">&bull;</span>
                    <b id="hud-kyle-val" style="color:#38BDF8; font-size:9.5px;">{kyle_compact}</b>
                </div>
            </div>
            <div id="neiro-tv-chart"></div>
            <canvas id="neiro-canvas"></canvas>
        </div>
        <!-- Panel Phải: Dàn 6 Cột Profile Riêng Biệt (VOL | FLOW | GEX | VEX | CHEX | THETA) -->
        <div id="neiro-profile-wrapper">
            <div class="neiro-profile-header">
                <span class="neiro-profile-title">
                    <span style="color:#FACC15;">⚡</span> MATRIX PROFILE &amp; ORDERFLOW
                </span>
                <span id="profile-poc-tag" style="color:#FACC15; font-size:9.5px; font-weight:800;">POC $---</span>
            </div>
            <div class="neiro-profile-canvas-box" id="neiro-profile-box">
                <canvas id="neiro-profile-canvas"></canvas>
            </div>
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

    json_options_str = json.dumps(js_options_data)
    build_ts_utc = str(meta.get("timestamp_utc") or datetime.now(timezone.utc).isoformat())
    json_meta_str = json.dumps({
        "timestamp_utc": build_ts_utc,
        "spot": spot,
        "market_open": market_open_flag,
        "regime": regime_val,
        "dte_days": dte_days_val,
        "contract_symbol": contract_symbol,
        "option_symbol": option_symbol_val,
        "expiration_date": expiration_date_val,
        "expiration_date_iso": expiration_iso_val,
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
        "cloud_feed_url": str(meta.get("cloud_feed_url") or ""),
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
    let lastCloudWorkerEpoch = 0;
    let lastCloudFeedSource = '';
    let lastCloudSuccessEpoch = 0;
    let lastAuthoritativeVpinEpoch = 0;
    let renderedSeriesTf = '';
    let renderedSeriesCount = 0;
    let renderedSeriesBarsByTime = new Map();
    const CLOUD_WORKER_STORAGE_KEY = 'neiro_cloud_feed_url';

    function recordRenderedSeries(bars, tfKey) {{
        renderedSeriesTf = String(tfKey || '');
        renderedSeriesCount = Array.isArray(bars) ? bars.length : 0;
        renderedSeriesBarsByTime = new Map();
        if (Array.isArray(bars)) {{
            for (let i = 0; i < bars.length; i++) {{
                const b = bars[i];
                if (b && b.time !== undefined) {{
                    renderedSeriesBarsByTime.set(Number(b.time), {{
                        time: Number(b.time),
                        open: Number(b.open),
                        high: Number(b.high),
                        low: Number(b.low),
                        close: Number(b.close),
                    }});
                }}
            }}
        }}
    }}

    function normalizeCloudWorkerUrl(raw) {{
        if (!raw) return '';
        try {{
            const u = new URL(String(raw).trim());
            if (u.protocol === 'https:' || u.hostname === '127.0.0.1' || u.hostname === 'localhost') {{
                return u.origin;
            }}
        }} catch (e) {{}}
        return '';
    }}

    function getCloudFeedWorkerUrl() {{
        try {{
            const saved = normalizeCloudWorkerUrl(localStorage.getItem(CLOUD_WORKER_STORAGE_KEY));
            if (saved) return saved;
        }} catch (e) {{}}
        return normalizeCloudWorkerUrl(window.INITIAL_META && window.INITIAL_META.cloud_feed_url);
    }}

    function updateCloudWorkerButtonState() {{
        const btn = document.getElementById('btn-cloud-worker');
        if (!btn) return;
        const wUrl = getCloudFeedWorkerUrl();
        if (!wUrl) {{
            btn.innerText = 'Cloud Feed';
            btn.classList.remove('active');
            btn.title = 'Cài đặt URL Cloudflare Worker (xem realtime 24/7 trên điện thoại & GitHub Pages)';
            return;
        }}
        const isCtrader = String(lastCloudFeedSource || '').startsWith('ctrader_');
        btn.innerText = isCtrader ? 'Cloud: XAUUSDF' : 'Cloud: Bật';
        btn.classList.add('active');
        btn.title = 'Cloudflare Worker: ' + wUrl + ' (Bấm để đổi hoặc tắt)';
    }}

    function promptCloudFeedUrl() {{
        const current = getCloudFeedWorkerUrl();
        const entered = window.prompt(
            'Dán URL Cloudflare Worker (VD: https://neiro-gold-feed.ten-anh.workers.dev) — để trống để tắt:',
            current || ''
        );
        if (entered === null) return;
        const cleaned = normalizeCloudWorkerUrl(entered);
        try {{
            if (cleaned) localStorage.setItem(CLOUD_WORKER_STORAGE_KEY, cleaned);
            else localStorage.removeItem(CLOUD_WORKER_STORAGE_KEY);
        }} catch (e) {{}}
        lastCloudWorkerEpoch = 0;
        lastCloudFeedSource = '';
        updateCloudWorkerButtonState();
        updateSyncBadgeHonest();
        if (cleaned) checkCloudSyncNow(true);
    }}

    let isCmeSyncInProgress = false;
    function resetSyncCmeBtn(btn) {{
        isCmeSyncInProgress = false;
        if (btn) {{
            btn.classList.remove('active');
            btn.innerText = '⚡ Sync CME';
            btn.style.color = '';
        }}
    }}

    async function dispatchGithubSyncDirect(pat) {{
        const ghRes = await fetch('https://api.github.com/repos/DaniNguyen2509/Neiro-Gold-Quant/dispatches', {{
            method: 'POST',
            headers: {{
                'Accept': 'application/vnd.github+json',
                'Authorization': 'Bearer ' + pat,
                'Content-Type': 'application/json',
            }},
            body: JSON.stringify({{
                event_type: 'sync-options',
                client_payload: {{
                    triggered_at: new Date().toISOString(),
                    source: 'browser_direct_sync',
                }},
            }}),
        }});
        if (ghRes.status === 204 || ghRes.ok) {{
            return {{ ok: true }};
        }}
        const errTxt = await ghRes.text().catch(() => '');
        return {{
            ok: false,
            status: ghRes.status,
            error: 'GitHub API (' + ghRes.status + '): ' + (errTxt || ghRes.statusText),
        }};
    }}

    async function triggerRemoteCmeSync() {{
        if (isCmeSyncInProgress) {{
            alert('Yêu cầu cào CME đang chạy, vui lòng đợi hoàn tất!');
            return;
        }}
        const btn = document.getElementById('btn-sync-cme');
        const wUrl = getCloudFeedWorkerUrl() || 'https://neiro-gold-feed.dani-wind2509.workers.dev';
        const pat = (localStorage.getItem('NEIRO_GITHUB_PAT') || '').trim();
        if (!confirm('Kích hoạt máy ảo GitHub Actions cào bảng Options COMEX mới nhất từ Barchart ngay bây giờ? (~1-2 phút)')) {{
            return;
        }}

        isCmeSyncInProgress = true;
        if (btn) {{
            btn.classList.add('active');
            btn.innerText = '⏳ Đang gọi Cloud...';
            btn.style.color = '#FACC15';
        }}

        try {{
            let dispatchResult = null;
            if (!pat) {{
                try {{
                    const res = await fetch(wUrl + '/api/trigger_sync', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                    }});
                    const data = await res.json();
                    if (res.ok && data.ok) {{
                        dispatchResult = {{ ok: true }};
                    }} else if (res.status === 401 || (data.error && data.error.includes('Missing GITHUB_DISPATCH_TOKEN'))) {{
                        const entered = prompt(
                            'Đây KHÔNG phải mật khẩu đăng nhập mà là GitHub Token (bắt đầu bằng github_pat_... hoặc ghp_...) để gọi GitHub Actions cào CME.\\n\\n' +
                            'Cách tạo nhanh: GitHub -> Settings -> Developer settings -> Personal access tokens -> Fine-grained tokens -> chọn repo Neiro-Gold-Quant -> bật Contents: Read and write.\\n\\nDán GitHub Token vào đây:'
                        );
                        if (entered && entered.trim()) {{
                            localStorage.setItem('NEIRO_GITHUB_PAT', entered.trim());
                            resetSyncCmeBtn(btn);
                            triggerRemoteCmeSync();
                            return;
                        }}
                        resetSyncCmeBtn(btn);
                        return;
                    }} else {{
                        dispatchResult = {{ ok: false, status: res.status, error: data.error || 'Không thể kết nối Cloudflare Worker' }};
                    }}
                }} catch (workerErr) {{
                    dispatchResult = {{ ok: false, status: 0, error: workerErr.message || 'Lỗi kết nối Cloud Worker' }};
                }}
            }} else {{
                // Try Worker first; if Worker CORS rejects Authorization before redeploy, fallback directly to GitHub API
                try {{
                    const res = await fetch(wUrl + '/api/trigger_sync', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                            'Authorization': 'Bearer ' + pat,
                        }},
                    }});
                    const data = await res.json();
                    if (res.ok && data.ok) {{
                        dispatchResult = {{ ok: true }};
                    }} else {{
                        dispatchResult = {{ ok: false, status: res.status, error: data.error || 'Worker sync failed' }};
                    }}
                }} catch (_) {{
                    dispatchResult = await dispatchGithubSyncDirect(pat);
                }}
            }}

            if (!dispatchResult || !dispatchResult.ok) {{
                const errMsg = String((dispatchResult && dispatchResult.error) || 'Không thể kích hoạt');
                const isBadToken = pat && (errMsg.includes('(401)') || errMsg.includes('(403)') || (dispatchResult && (dispatchResult.status === 401 || dispatchResult.status === 403)));
                if (isBadToken) {{
                    localStorage.removeItem('NEIRO_GITHUB_PAT');
                    alert(
                        'GitHub từ chối Token vừa lưu (có thể anh nhập nhầm mật khẩu, token hết hạn, hoặc thiếu quyền Contents: Read and write).\\n\\n' +
                        'Hệ thống đã xóa token cũ để anh bấm Sync CME nhập lại GitHub Token (github_pat_... / ghp_...).\\nChi tiết: ' + errMsg
                    );
                }} else {{
                    alert('Lỗi kích hoạt: ' + errMsg);
                }}
                resetSyncCmeBtn(btn);
                return;
            }}

            let countdown = 150;
            const startEpoch = Date.now();
            if (btn) btn.innerText = '⏳ Đang cào (150s)';

            const timer = setInterval(async () => {{
                countdown--;
                if (btn) btn.innerText = '⏳ Đang cào (' + countdown + 's)';

                if (countdown % 8 === 0 || countdown <= 5) {{
                    try {{
                        const vData = await fetchCloudVersionJson();
                        if (vData) {{
                            const vTime = Date.parse(vData.timestamp_utc || vData.scraped_at_utc || 0);
                            if (vTime > Math.max(startEpoch, lastStaticSnapshotEpochMs)) {{
                                clearInterval(timer);
                                isCmeSyncInProgress = false;
                                if (btn) {{
                                    btn.innerText = '✅ Đã xong';
                                    btn.style.color = '#4ADE80';
                                    setTimeout(() => {{
                                        btn.classList.remove('active');
                                        btn.innerText = '⚡ Sync CME';
                                        btn.style.color = '';
                                    }}, 4000);
                                }}
                                alert('🎉 Bảng CME Options đã được cập nhật mới nhất! Đang tải lại...');
                                checkCloudSyncNow(true);
                                window.location.href = window.location.pathname + window.location.search;
                                return;
                            }}
                        }}
                    }} catch (_) {{}}
                }}

                if (countdown <= 0) {{
                    clearInterval(timer);
                    isCmeSyncInProgress = false;
                    if (btn) {{
                        btn.classList.remove('active');
                        btn.innerText = '⚡ Sync CME';
                        btn.style.color = '';
                    }}
                    alert('Lệnh cào đã gửi thành công lên GitHub Actions. Trang sẽ nhận data mới sau 1-2 phút!');
                }}
            }}, 1000);

        }} catch (e) {{
            alert('Lỗi kết nối: ' + e.message);
            isCmeSyncInProgress = false;
            if (btn) {{
                btn.classList.remove('active');
                btn.innerText = '⚡ Sync CME';
                btn.style.color = '';
            }}
        }}
    }}
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

    let profileCollapsed = false;
    function toggleProfilePanel() {{
        profileCollapsed = !profileCollapsed;
        const panel = document.getElementById('neiro-profile-wrapper');
        const btn = document.getElementById('btn-toggle-profile');
        if (panel) {{
            panel.classList.toggle('collapsed', profileCollapsed);
            panel.classList.toggle('mobile-open', !profileCollapsed);
        }}
        if (btn) {{
            btn.innerText = profileCollapsed ? 'Hiện Profile' : 'Ẩn Profile';
        }}
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
                    title: 'VEX · VÙNG BẬT',
                }});
            }}
            if (!charmPriceLine && m.charm_peak_strike) {{
                charmPriceLine = candleSeries.createPriceLine({{
                    price: m.charm_peak_strike,
                    color: '#C084FC',
                    lineWidth: 1.5,
                    lineStyle: LightweightCharts.LineStyle.Dashed,
                    axisLabelVisible: true,
                    title: 'CHEX · HÚT GIÁ',
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
            recordRenderedSeries(bars, key);
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
        if (typeof computeVolumeProfile === 'function') {{
            computeVolumeProfile((window.INITIAL_CANDLES && window.INITIAL_CANDLES.length) ? window.INITIAL_CANDLES : bars);
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

    function summarizeStrikeOiJs(strikePrice, spotRef) {{
        const opts = window.INITIAL_OPTIONS || [];
        const sVal = Number(strikePrice || 0);
        const refSpot = Number(spotRef || (window.INITIAL_META && window.INITIAL_META.spot) || sVal);
        let totalOi = 0;
        let corridorSum = 0;
        let corridorCnt = 0;
        let allSum = 0;
        let allCnt = 0;

        for (let i = 0; i < opts.length; i++) {{
            const o = opts[i];
            if (!o) continue;
            const k = Number(o.strike || 0);
            const oi = Number(o.c_oi || 0) + Number(o.p_oi || 0);
            if (Math.abs(k - sVal) < 0.05) {{
                totalOi = Math.round(oi);
            }}
            if (oi > 0) {{
                allSum += oi;
                allCnt++;
                if (Math.abs(k - refSpot) <= 100.0) {{
                    corridorSum += oi;
                    corridorCnt++;
                }}
            }}
        }}
        const meanOi = corridorCnt >= 3 ? (corridorSum / corridorCnt) : (allCnt > 0 ? (allSum / allCnt) : 0);
        let tier = 'MỎNG';
        if (totalOi > 0 && meanOi > 0) {{
            if (totalOi >= meanOi * 0.85) tier = 'DÀY';
            else if (totalOi >= meanOi * 0.40) tier = 'VỪA';
        }}
        return {{
            oi: totalOi,
            tier: tier,
            isThin: tier === 'MỎNG',
            tag: 'OI ' + totalOi.toLocaleString('en-US') + ' (' + tier + ')',
        }};
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
            squeeze: {{ key: 'sq', side: 'BUY', title: '1. THUẬN CHIỀU BUY (Phá cản)', label: '1. THUẬN CHIỀU BUY (Phá cản ' + Math.round(params.strikeAbove) + ')', trig: 'Vượt > ' + r2(entrySq - 0.50).toFixed(2), entry: entrySq, sl: slSq, slDist: r2(entrySq - slSq), tp: tpSq, active: sqActive, badge: sqActive ? '[KÍCH HOẠT]' : '[CHỜ XÁC NHẬN]', reason: sqReason, lots: sizeXauusdJs(r2(entrySq - slSq), normReg) }},
            fade:    {{ key: 'fd', side: 'SELL', title: '2. ĐẢO CHIỀU SELL (Chạm cản)', label: '2. ĐẢO CHIỀU SELL (Chạm cản ' + Math.round(params.strikeAbove) + ')', trig: (params.strikeAbove - 1.50).toFixed(2) + ' - ' + params.strikeAbove.toFixed(2), entry: entryFd, sl: slFd, slDist: r2(slFd - entryFd), tp: tpFd, active: fdActive, badge: fdActive ? '[KÍCH HOẠT]' : '[TẠM KHÓA]', reason: fdReason, lots: sizeXauusdJs(r2(slFd - entryFd), normReg) }},
            rebound: {{ key: 'rb', side: 'BUY', title: '3. ĐẢO CHIỀU BUY (Chạm sàn)', label: '3. ĐẢO CHIỀU BUY (Chạm sàn ' + Math.round(params.strikeBelow) + ')', trig: params.strikeBelow.toFixed(2) + ' - ' + (params.strikeBelow + 1.50).toFixed(2), entry: entryRb, sl: slRb, slDist: r2(entryRb - slRb), tp: tpRb, active: rbActive, badge: rbActive ? '[KÍCH HOẠT]' : '[TẠM KHÓA]', reason: rbReason, lots: sizeXauusdJs(r2(entryRb - slRb), normReg) }},
            breakdown: {{ key: 'bd', side: 'SELL', title: '4. THUẬN CHIỀU SELL (Thủng sàn)', label: '4. THUẬN CHIỀU SELL (Thủng sàn ' + Math.round(params.strikeBelow) + ')', trig: 'Thủng < ' + r2(entryBd + 0.50).toFixed(2), entry: entryBd, sl: slBd, slDist: r2(slBd - entryBd), tp: tpBd, active: bdActive, badge: bdActive ? '[KÍCH HOẠT]' : '[CHỜ XÁC NHẬN]', reason: bdReason, lots: sizeXauusdJs(r2(slBd - entryBd), normReg) }},
        }};
    }}

    // ----------------------------------------------------------------------------
    // Realtime Vectorized Black-76 Greeks Engine: Dynamic GEX, Walls & Flip S*
    // ----------------------------------------------------------------------------
    function recomputeLiveGreeksAndWalls(liveSpot) {{
        if (!liveSpot || isNaN(liveSpot) || liveSpot <= 0) return;
        const opts = window.INITIAL_OPTIONS;
        if (!Array.isArray(opts) || opts.length === 0) return;
        const m = window.INITIAL_META || {{}};

        // Preserve initial baseline walls as fallback reference
        if (m.baseline_call_wall === undefined) m.baseline_call_wall = m.call_wall;
        if (m.baseline_put_wall === undefined) m.baseline_put_wall = m.put_wall;
        if (m.baseline_zero_gamma === undefined) m.baseline_zero_gamma = m.zero_gamma_flip;

        const dteDays = Math.max(1.0, Number(m.dte_days || 30.0));
        const T = Math.max(dteDays / 365.0, 1.0 / 365.0);
        const r = 0.045;
        const sqrtT = Math.sqrt(T);
        const dfDisc = Math.exp(-r * T);
        const scale = (liveSpot * liveSpot) * 0.01 / 1e6 * 100.0;

        let totalGex = 0.0;
        let totalVex = 0.0;
        let totalChex = 0.0;
        let totalNetDelta = 0.0;

        let bestCallPower = -1;
        let bestCallStrike = Number(m.call_wall || (liveSpot + 50));
        let bestCallOi = Number(m.call_wall_oi || 0);

        let bestPutPower = -1;
        let bestPutStrike = Number(m.put_wall || (liveSpot - 50));
        let bestPutOi = Number(m.put_wall_oi || 0);

        for (let i = 0; i < opts.length; i++) {{
            const o = opts[i];
            const K = Number(o.strike || 0);
            if (K <= 0) continue;

            const cOi = Number(o.c_oi || 0);
            const pOi = Number(o.p_oi || 0);
            const iv = Math.max(0.01, Math.min(1.5, Number(o.c_iv || o.p_iv || 0.16)));
            const denom = Math.max(1e-5, iv * sqrtT);
            const halfSig2T = 0.5 * (iv * iv) * T;

            const d1 = (Math.log(liveSpot / K) + halfSig2T) / denom;
            const d2 = d1 - denom;
            const pdf = (1.0 / Math.sqrt(2.0 * Math.PI)) * Math.exp(-0.5 * d1 * d1);
            const gamma = (dfDisc * pdf) / Math.max(1e-4, liveSpot * denom);

            // Vectorized GEX (in Millions USD per 1% move)
            const cGex = gamma * cOi * scale;
            const pGex = -(gamma * pOi * scale);
            const netGex = cGex + pGex;
            o.currentNetGEX = netGex;
            o.c_gamma = gamma;
            o.p_gamma = gamma;
            totalGex += netGex;

            // Vectorized Delta & DEX
            const cdfD1 = normCdf(d1);
            const cDelta = dfDisc * cdfD1;
            const pDelta = cDelta - dfDisc;
            o.c_delta = cDelta;
            o.p_delta = pDelta;
            const netDelta = (cOi * cDelta) + (pOi * pDelta);
            o.netDelta = netDelta;
            totalNetDelta += netDelta;

            // Vectorized Vanna (VEX) & Charm (CHEX)
            const vanna = -dfDisc * pdf * (d2 / iv);
            const netVex = vanna * (cOi - pOi) * scale * 0.1;
            o.currentNetVEX = netVex;
            totalVex += netVex;

            const charm = dfDisc * pdf * ((2.0 * r * T - d2 * iv * sqrtT) / (2.0 * T * denom));
            const netChex = -charm * (cOi - pOi) * scale * 0.05;
            o.currentNetCHEX = netChex;
            totalChex += netChex;

            // Dynamic Gamma-Weighted Walls (True Gamma Power = OI * Gamma)
            const cPow = cOi * gamma;
            const pPow = pOi * gamma;
            if (K >= liveSpot && cPow > bestCallPower && cOi > 50) {{
                bestCallPower = cPow;
                bestCallStrike = K;
                bestCallOi = cOi;
            }}
            if (K <= liveSpot && pPow > bestPutPower && pOi > 50) {{
                bestPutPower = pPow;
                bestPutStrike = K;
                bestPutOi = pOi;
            }}
        }}

        // Update Live Total GEX, VEX, CHEX
        m.total_net_gex = totalGex;
        m.total_net_vex = totalVex;
        m.total_net_chex = totalChex;
        m.regime = totalGex >= 10.0 ? 'LONG_GAMMA' : (totalGex <= -10.0 ? 'SHORT_GAMMA' : 'NEUTRAL');

        // Update Walls only if not already provided by authoritative global CME snapshot
        if (!m.call_wall && bestCallPower > 0) {{
            m.call_wall = bestCallStrike;
            m.call_wall_oi = bestCallOi;
        }}
        if (!m.put_wall && bestPutPower > 0) {{
            m.put_wall = bestPutStrike;
            m.put_wall_oi = bestPutOi;
        }}

        // Live Zero Gamma Flip Solver (Bisection search in [liveSpot - 180, liveSpot + 180])
        function netGexAt(s) {{
            let sumG = 0;
            const sc = (s * s) * 0.01 / 1e6 * 100.0;
            for (let j = 0; j < opts.length; j++) {{
                const oj = opts[j];
                const k = Number(oj.strike);
                if (k <= 0) continue;
                const iv = Math.max(0.01, Number(oj.c_iv || oj.p_iv || 0.16));
                const den = Math.max(1e-5, iv * sqrtT);
                const d1Val = (Math.log(s / k) + 0.5 * (iv * iv) * T) / den;
                const p = (1.0 / Math.sqrt(2.0 * Math.PI)) * Math.exp(-0.5 * d1Val * d1Val);
                const gam = (dfDisc * p) / Math.max(1e-4, s * den);
                sumG += (gam * Number(oj.c_oi || 0) * sc) - (gam * Number(oj.p_oi || 0) * sc);
            }}
            return sumG;
        }}

        let lowS = liveSpot - 180.0;
        let highS = liveSpot + 180.0;
        let fLow = netGexAt(lowS);
        let fHigh = netGexAt(highS);
        if (fLow * fHigh <= 0) {{
            for (let iter = 0; iter < 24; iter++) {{
                const midS = (lowS + highS) / 2.0;
                const fMid = netGexAt(midS);
                if (Math.abs(fMid) < 0.05 || (highS - lowS) < 0.25) {{
                    m.zero_gamma_flip = Math.round(midS * 10) / 10;
                    break;
                }}
                if (fLow * fMid < 0) {{
                    highS = midS;
                    fHigh = fMid;
                }} else {{
                    lowS = midS;
                    fLow = fMid;
                }}
            }}
        }}

        // Real-time Intraday Wall Siege Ratio update based on price proximity
        const distCallWall = Math.abs(liveSpot - m.call_wall);
        const distPutWall = Math.abs(liveSpot - m.put_wall);
        const baselineCallSiege = Number(m.baseline_call_wall_siege || m.call_wall_siege || 0.05);
        const baselinePutSiege = Number(m.baseline_put_wall_siege || m.put_wall_siege || 0.05);
        if (m.baseline_call_wall_siege === undefined) m.baseline_call_wall_siege = baselineCallSiege;
        if (m.baseline_put_wall_siege === undefined) m.baseline_put_wall_siege = baselinePutSiege;

        if (distCallWall <= 4.0) {{
            const proximityBoost = (4.0 - distCallWall) / 4.0 * 0.25;
            m.call_wall_siege = Math.max(baselineCallSiege, Math.min(1.5, baselineCallSiege + proximityBoost));
        }}
        if (distPutWall <= 4.0) {{
            const proximityBoost = (4.0 - distPutWall) / 4.0 * 0.25;
            m.put_wall_siege = Math.max(baselinePutSiege, Math.min(1.5, baselinePutSiege + proximityBoost));
        }}

        // Sync DOM KPI elements
        const gCol = totalGex >= 0 ? '#4ADE80' : '#F87171';
        const gTxt = '$' + (totalGex >= 0 ? '+' : '') + totalGex.toFixed(1) + 'M';
        const elKpi = document.getElementById('kpi-gex-val');
        const elHud = document.getElementById('hud-gex-val');
        if (elKpi) {{ elKpi.innerText = gTxt; elKpi.style.color = gCol; }}
        if (elHud) {{ elHud.innerText = gTxt; elHud.style.color = gCol; }}
    }}

    function updateRealtimeTacticalCockpit() {{
        const m = window.INITIAL_META || {{}};
        const spot = Number(currentGoldPrice || m.spot || 0);
        if (!spot) return;

        // 0. Recompute Real-time Black-76 Greeks & Elastic GEX Profile on Live Spot
        recomputeLiveGreeksAndWalls(spot);

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
        const sbInfo = summarizeStrikeOiJs(strikes.strikeBelow, spot);
        const saInfo = summarizeStrikeOiJs(strikes.strikeAbove, spot);
        const elSb = document.getElementById('spine-strike-below');
        if (elSb) elSb.innerText = '$' + Math.round(strikes.strikeBelow).toLocaleString('en-US');
        const elSbo = document.getElementById('spine-below-oi');
        if (elSbo) {{
            elSbo.innerText = '(' + sbInfo.tag + ')';
            elSbo.style.color = sbInfo.isThin ? '#64748B' : (sbInfo.tier === 'DÀY' ? '#4ADE80' : '#FACC15');
        }}
        const elSa = document.getElementById('spine-strike-above');
        if (elSa) elSa.innerText = '$' + Math.round(strikes.strikeAbove).toLocaleString('en-US');
        const elSao = document.getElementById('spine-above-oi');
        if (elSao) {{
            elSao.innerText = '(' + saInfo.tag + ')';
            elSao.style.color = saInfo.isThin ? '#64748B' : (saInfo.tier === 'DÀY' ? '#F87171' : '#FACC15');
        }}
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
                regVal.innerText = 'ƯU TIÊN ĐÁNH ĐẢO CHIỀU (GEX +)';
                regVal.style.color = '#4ADE80';
                if (regCard) regCard.style.borderLeftColor = '#22C55E';
            }} else if (netGex < 0 && distFlip < 0) {{
                regVal.innerText = 'ƯU TIÊN ĐÁNH THUẬN CHIỀU (GEX -)';
                regVal.style.color = '#F87171';
                if (regCard) regCard.style.borderLeftColor = '#EF4444';
            }} else {{
                regVal.innerText = 'CHỜ XÁC NHẬN (CHUYỂN PHA)';
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
        if (lastCloudWorkerEpoch && (now - lastCloudWorkerEpoch) < 15000) {{
            const isCtrader = String(lastCloudFeedSource || '').startsWith('ctrader_');
            badge.style.background = isCtrader ? 'rgba(34, 197, 94, 0.18)' : 'rgba(56, 189, 248, 0.16)';
            badge.style.borderColor = isCtrader ? 'rgba(34, 197, 94, 0.45)' : 'rgba(56, 189, 248, 0.4)';
            badge.style.color = isCtrader ? '#4ADE80' : '#38BDF8';
            badge.innerText = isCtrader ? '● WORKER LIVE (XAUUSDF · 0s)' : '● WORKER CLOUD (GC=F)';
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
        const wallClockBucket = nowSec - (nowSec % currentPeriodSec);
        const canAdvanceToWallClock = Boolean(
            marketOpen &&
            !isAuthoritativeYahoo &&
            activeCandle &&
            wallClockBucket > activeCandle.time &&
            (wallClockBucket - activeCandle.time) <= currentPeriodSec * 2
        );
        const barTime = !activeCandle
            ? wallClockBucket
            : (canAdvanceToWallClock ? wallClockBucket : activeCandle.time);
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

        if (!activeCandle || activeCandle.time < barTime) {{
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
            const barPayload = {{
                time: activeCandle.time,
                open: activeCandle.open,
                high: activeCandle.high,
                low: activeCandle.low,
                close: activeCandle.close,
            }};
            candleSeries.update(barPayload);
            if (renderedSeriesTf === currentTf) {{
                if (!renderedSeriesBarsByTime.has(activeCandle.time)) {{
                    renderedSeriesCount += 1;
                }}
                renderedSeriesBarsByTime.set(activeCandle.time, barPayload);
            }}
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
            hudCvd.innerText = 'CVD ' + (liveCvdContracts >= 0 ? '+' : '') + Math.round(liveCvdContracts) + ' HĐ (' + Math.round(liveBuyPct) + '% Mua)';
            hudCvd.style.color = cvdCol;
        }}
        const hudBar = document.getElementById('hud-bvc-bar');
        if (hudBar) hudBar.style.width = liveBuyPct.toFixed(1) + '%';
        const hudKyle = document.getElementById('hud-kyle-val');
        if (hudKyle) {{
            const kyleCompact = liveKyleLabel
                .replace(' (ICEBERG LIMIT ABSORPTION)', ' (ICEBERG)')
                .replace(' (VACUUM MARKET SWEEP)', ' (VACUUM)')
                .replace('THANH KHOẢN SỔ LỆNH BÌNH THƯỜNG (BAR OLS)', 'SỔ LỆNH BÌNH THƯỜNG')
                .replace('THANH KHOẢN SỔ LỆNH BÌNH THƯỜNG', 'SỔ LỆNH BÌNH THƯỜNG')
                .replace('THANH KHOẢN BÌNH THƯỜNG', 'SỔ LỆNH BÌNH THƯỜNG');
            hudKyle.innerText = kyleCompact;
            hudKyle.title = liveKyleLabel;
        }}

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
            hudFv.innerText = fv.shortTxt || fv.txt;
            hudFv.title = fv.txt;
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
            const newH = container.clientHeight || (chartExpanded ? 700 : 540);
            neiroChart.applyOptions({{ width: newW, height: newH }});
            if (canvas) {{
                canvas.width = newW;
                canvas.height = newH;
            }}
            const pBox = document.getElementById('neiro-profile-box');
            const pCanvas = document.getElementById('neiro-profile-canvas');
            if (pBox && pCanvas) {{
                pCanvas.width = pBox.clientWidth || 340;
                pCanvas.height = pBox.clientHeight || (newH - 26);
            }}
            drawNeiroOverlay();
        }};

        window.addEventListener('resize', handleResize);
        neiroChart.timeScale().subscribeVisibleTimeRangeChange(() => drawNeiroOverlay());
        neiroChart.timeScale().subscribeVisibleLogicalRangeChange(() => drawNeiroOverlay());

        const pCanvas = document.getElementById('neiro-profile-canvas');
        if (pCanvas) {{
            pCanvas.addEventListener('mousemove', (e) => {{
                const rect = pCanvas.getBoundingClientRect();
                const mx = e.clientX - rect.left;
                const my = e.clientY - rect.top;
                const opts = window.INITIAL_OPTIONS || [];
                let closest = null;
                let minDist = 18;
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
                hoveredMx = mx;
                drawNeiroProfilePanel();
            }});
            pCanvas.addEventListener('mouseleave', () => {{
                hoveredOption = null;
                hoveredY = null;
                hoveredMx = null;
                drawNeiroProfilePanel();
            }});
        }}
        neiroChart.subscribeCrosshairMove(() => {{
            drawNeiroOverlay();
        }});

        computeVolumeProfile(window.INITIAL_CANDLES || []);
        handleResize();
    }}

    let hoveredOption = null;
    let hoveredY = null;
    let hoveredMx = null;

    // ----------------------------------------------------------------------------
    // Realtime Session Volume Profile Engine (POC / VAH / VAL / Strike Aggregation)
    // ----------------------------------------------------------------------------
    let sessionPocPrice = null;
    let sessionVahPrice = null;
    let sessionValPrice = null;
    let sessionPocVol = 0;
    let sessionTotalVol = 0;
    let sessionVolByStrike = {{}};

    function computeVolumeProfile(candles) {{
        if (!Array.isArray(candles) || candles.length === 0) return;
        const binSize = 1.0;
        const volByBin = {{}};
        let totalVol = 0;

        for (let i = 0; i < candles.length; i++) {{
            const c = candles[i];
            const v = Number(c.volume || 0);
            if (v <= 0) continue;
            const h = Number(c.high);
            const l = Number(c.low);
            totalVol += v;
            if (h <= l) {{
                const b = Math.round(c.close / binSize) * binSize;
                volByBin[b] = (volByBin[b] || 0) + v;
                continue;
            }}
            const bStart = Math.floor(l / binSize) * binSize;
            const bEnd = Math.floor(h / binSize) * binSize;
            const span = h - l;
            for (let b = bStart; b <= bEnd; b += binSize) {{
                const ov = Math.max(0.0, Math.min(h, b + binSize) - Math.max(l, b));
                const frac = ov / span;
                volByBin[b] = (volByBin[b] || 0) + v * frac;
            }}
        }}

        if (totalVol <= 0 || Object.keys(volByBin).length === 0) return;
        sessionTotalVol = totalVol;

        let maxV = 0;
        let poc = null;
        const bins = [];
        for (const bStr in volByBin) {{
            const b = parseFloat(bStr);
            bins.push(b);
            if (volByBin[b] > maxV) {{
                maxV = volByBin[b];
                poc = b;
            }}
        }}
        bins.sort((a, b) => a - b);
        sessionPocPrice = poc;
        sessionPocVol = maxV;

        const targetVa = totalVol * 0.70;
        const vaBins = new Set([poc]);
        let curVaVol = maxV;
        let upIdx = bins.indexOf(poc) + 1;
        let dnIdx = bins.indexOf(poc) - 1;

        while (curVaVol < targetVa && (upIdx < bins.length || dnIdx >= 0)) {{
            const upBin = upIdx < bins.length ? bins[upIdx] : null;
            const dnBin = dnIdx >= 0 ? bins[dnIdx] : null;
            const upV = upBin !== null ? (volByBin[upBin] || 0) : -1;
            const dnV = dnBin !== null ? (volByBin[dnBin] || 0) : -1;

            if (upV >= dnV && upBin !== null) {{
                vaBins.add(upBin);
                curVaVol += upV;
                upIdx++;
            }} else if (dnBin !== null) {{
                vaBins.add(dnBin);
                curVaVol += dnV;
                dnIdx--;
            }} else {{
                break;
            }}
        }}

        let minVa = Infinity, maxVa = -Infinity;
        vaBins.forEach(b => {{
            if (b < minVa) minVa = b;
            if (b > maxVa) maxVa = b;
        }});
        sessionVahPrice = maxVa;
        sessionValPrice = minVa;

        const opts = window.INITIAL_OPTIONS || [];
        sessionVolByStrike = {{}};
        for (let j = 0; j < opts.length; j++) {{
            const stk = opts[j].strike;
            let aggV = 0;
            for (let b = stk - 2.0; b <= stk + 2.0; b += binSize) {{
                if (volByBin[b]) aggV += volByBin[b];
            }}
            sessionVolByStrike[stk] = aggV;
        }}

        const pocTag = document.getElementById('profile-poc-tag');
        if (pocTag && sessionPocPrice) {{
            pocTag.innerText = 'POC $' + Math.round(sessionPocPrice) + ' (' + Math.round(sessionPocVol) + ' HĐ)';
        }}
    }}

    // ----------------------------------------------------------------------------
    // Canvas Overlay Engine: Clean Chart Lines, Key Levels & Air Pocket Matrix
    // ----------------------------------------------------------------------------
    function drawNeiroOverlay() {{
        const canvas = document.getElementById('neiro-canvas');
        if (!canvas || !neiroChart || !candleSeries) return;
        const ctx = canvas.getContext('2d');
        const w = canvas.width;
        const h = canvas.height;
        ctx.clearRect(0, 0, w, h);

        const m = window.INITIAL_META;
        // chartW leaves room for the Lightweight Charts price scale (65px) on the right
        const chartW = Math.max(100, w - 65);

        // 1. Always-On Air Pocket Vacuum Matrix (Across the pure chart canvas)
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
                    const apOi = Number(ap.avg_oi || 0);
                    const apSev = String(ap.severity || '').toUpperCase();
                    const isDeep = (apSev === 'CRITICAL') || (apSev === 'HIGH' && (apOi <= 0 || apOi < 125));
                    const isHigh = !isDeep && (apSev === 'HIGH');

                    let chartFill, borderCol, borderW, borderDash, labelCol, levelTxt;
                    if (isDeep) {{
                        chartFill = 'rgba(249, 115, 22, 0.18)';
                        borderCol = 'rgba(251, 146, 60, 0.85)';
                        borderW = 1.4;
                        borderDash = [5, 3];
                        labelCol = '#FDBA74';
                        levelTxt = 'RỖNG CỰC MẠNH';
                    }} else if (isHigh) {{
                        chartFill = 'rgba(56, 189, 248, 0.13)';
                        borderCol = 'rgba(56, 189, 248, 0.78)';
                        borderW = 1.15;
                        borderDash = [4, 4];
                        labelCol = '#7DD3FC';
                        levelTxt = 'RỖNG MẠNH';
                    }} else {{
                        const depthFactor = apOi > 0 ? Math.max(0.25, Math.min(1.0, 1.0 - (apOi - 150) / 300)) : 0.65;
                        const cAlpha = (0.045 + 0.055 * depthFactor).toFixed(3);
                        const bAlpha = (0.32 + 0.26 * depthFactor).toFixed(2);
                        chartFill = 'rgba(148, 163, 184, ' + cAlpha + ')';
                        borderCol = 'rgba(148, 163, 184, ' + bAlpha + ')';
                        borderW = 0.9;
                        borderDash = [3, 5];
                        labelCol = 'rgba(203, 213, 225, ' + (0.60 + 0.25 * depthFactor).toFixed(2) + ')';
                        levelTxt = 'MỎNG NHẸ';
                    }}

                    ctx.fillStyle = chartFill;
                    ctx.fillRect(0, topY, chartW, bandH);
                    ctx.strokeStyle = borderCol;
                    ctx.setLineDash(borderDash);
                    ctx.lineWidth = borderW;
                    ctx.strokeRect(0, topY, chartW, bandH);
                    ctx.setLineDash([]);

                    const apLabelX = (topY < 145 && chartW > 550) ? 460 : 20;
                    const apRange = '[$' + Math.min(pFrom, pTo).toFixed(0) + ' - $' + Math.max(pFrom, pTo).toFixed(0) + ']';
                    const oiInfo = apOi > 0 ? (' · OI ~' + Math.round(apOi)) : '';
                    const apTxt = (apLabelX > 20)
                        ? ('⚠️ AIR POCKET VACUUM ' + apRange + ' · ' + levelTxt)
                        : ('⚠️ AIR POCKET VACUUM ' + apRange + ' · ' + levelTxt + oiInfo + ' · CẤM ĐỠ DAO');
                    ctx.font = 'bold 9.5px "JetBrains Mono", monospace';
                    ctx.textAlign = 'left';
                    ctx.fillStyle = labelCol;
                    ctx.fillText(apTxt, apLabelX, topY + Math.min(bandH - 3, 13));
                }}
            }}
        }});

        // 2b. Secondary Structural Zones (Institutional FVGs) — visible in Full Overlay Mode
        if (!overlayCompactMode) {{
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

        // 3. Key Quant Options Levels + Volume Profile (POC / VAH / VAL)
        const fallbackOff = Math.max(2.30, Math.round((0.8 * Math.max(2.0, Math.min(6.5, Number(m.atr_5m || 4.0))) - 0.50) * 100) / 100);
        const sqTrigPx = (liveTacticalMatrix && liveTacticalMatrix.squeeze && liveTacticalMatrix.squeeze.entry)
            ? Number(liveTacticalMatrix.squeeze.entry) - 0.50
            : (Number(m.strike_above || 0) + fallbackOff);
        const bdTrigPx = (liveTacticalMatrix && liveTacticalMatrix.breakdown && liveTacticalMatrix.breakdown.entry)
            ? Number(liveTacticalMatrix.breakdown.entry) + 0.50
            : (Number(m.strike_below || 0) - fallbackOff);

        const saOi = summarizeStrikeOiJs(m.strike_above, currentGoldPrice);
        const sbOi = summarizeStrikeOiJs(m.strike_below, currentGoldPrice);
        const naOi = summarizeStrikeOiJs(m.next_above, currentGoldPrice);
        const nbOi = summarizeStrikeOiJs(m.next_below, currentGoldPrice);
        const muOi = summarizeStrikeOiJs(m.major_up_wall, currentGoldPrice);
        const mdOi = summarizeStrikeOiJs(m.major_down_wall, currentGoldPrice);

        const keyLevels = [
            {{ p: m.call_wall,          c: '#EF4444', d: [6, 4], lw: 1.4, pin: true,  txt: 'CALL WALL $' + Math.round(m.call_wall) + ' · OI ' + (m.call_wall_oi || 0).toLocaleString() + ' · Siege: ' + (m.call_wall_siege || 0).toFixed(2) + 'x' }},
            {{ p: m.put_wall,           c: '#22C55E', d: [6, 4], lw: 1.4, pin: true,  txt: 'PUT WALL $' + Math.round(m.put_wall) + ' · OI ' + (m.put_wall_oi || 0).toLocaleString() + ' · Siege: ' + (m.put_wall_siege || 0).toFixed(2) + 'x' }},
            {{ p: m.zero_gamma_flip,    c: '#FACC15', d: [4, 4], lw: 1.4, pin: true,  txt: 'GAMMA FLIP (Trục cân đối) $' + Math.round(m.zero_gamma_flip) + ' · [' + (liveFlipVerdict.split(':')[0] || 'KIỂM ĐỊNH') + ']' }},
            {{ p: m.strike_above,       c: '#FB7185', d: saOi.isThin ? [2, 4] : [5, 3], lw: saOi.isThin ? 1.0 : 1.5, pin: true,  txt: 'CẢN TRÊN $' + Math.round(m.strike_above) + ' · ' + saOi.tag + ' · Phá BUY >$' + sqTrigPx.toFixed(1) }},
            {{ p: m.strike_below,       c: '#4ADE80', d: sbOi.isThin ? [2, 4] : [5, 3], lw: sbOi.isThin ? 1.0 : 1.5, pin: true,  txt: 'SÀN DƯỚI $' + Math.round(m.strike_below) + ' · ' + sbOi.tag + ' · Thủng SELL <$' + bdTrigPx.toFixed(1) }},
            {{ p: m.next_above,         c: '#FBBF24', d: [2, 4], lw: 1.0, pin: false, txt: 'TRẠM TRÊN $' + Math.round(m.next_above) + ' · ' + naOi.tag }},
            {{ p: m.next_below,         c: '#38BDF8', d: [2, 4], lw: 1.0, pin: false, txt: 'TRẠM DƯỚI $' + Math.round(m.next_below) + ' · ' + nbOi.tag }},
            {{ p: m.major_up_wall,      c: '#F97316', d: [3, 4], lw: 1.1, pin: false, txt: 'TƯỜNG LỚN ↑ $' + Math.round(m.major_up_wall) + ' · ' + muOi.tag }},
            {{ p: m.major_down_wall,    c: '#2DD4BF', d: [3, 4], lw: 1.1, pin: false, txt: 'TƯỜNG LỚN ↓ $' + Math.round(m.major_down_wall) + ' · ' + mdOi.tag }},
        ];

        // Session Volume Profile Key Levels: POC, VAH, VAL
        if (sessionPocPrice) {{
            keyLevels.push({{
                p: sessionPocPrice,
                c: '#FACC15',
                d: [6, 3],
                lw: 1.6,
                pin: true,
                txt: '★ POC (Vol Max) $' + Math.round(sessionPocPrice) + ' · ' + Math.round(sessionPocVol) + ' HĐ'
            }});
        }}
        if (sessionVahPrice) {{
            keyLevels.push({{
                p: sessionVahPrice,
                c: '#38BDF8',
                d: [4, 4],
                lw: 1.2,
                pin: true,
                txt: 'VAH (Vùng Giá Trị 70%) $' + Math.round(sessionVahPrice)
            }});
        }}
        if (sessionValPrice) {{
            keyLevels.push({{
                p: sessionValPrice,
                c: '#FB7185',
                d: [4, 4],
                lw: 1.2,
                pin: true,
                txt: 'VAL (Vùng Giá Trị 70%) $' + Math.round(sessionValPrice)
            }});
        }}

        if (!overlayCompactMode) {{
            keyLevels.push(
                {{ p: m.charm_peak_strike,  c: '#C084FC', d: [4, 4], lw: 1.2, pin: true, txt: 'CHEX · HÚT GIÁ VỀ ĐÂY ' + (m.charm_peak_val || 0).toFixed(1) + 'M/d' }},
                {{ p: m.vanna_peak_strike,  c: '#22D3EE', d: [4, 4], lw: 1.2, pin: true, txt: 'VEX · VÙNG BẬT / GIẬT SÓNG ' + (m.vanna_peak_val || 0).toFixed(1) + 'M' }}
            );
        }}
        if (liveTacticalMatrix) {{
            const act = [liveTacticalMatrix.squeeze, liveTacticalMatrix.fade, liveTacticalMatrix.rebound, liveTacticalMatrix.breakdown].filter(s => s && s.active);
            if (act.length > 0) {{
                const topAct = act.slice().sort((a, b) => Math.abs(a.entry - currentGoldPrice) - Math.abs(b.entry - currentGoldPrice))[0];
                keyLevels.push(
                    {{ p: topAct.entry, c: topAct.side === 'BUY' ? '#4ADE80' : '#FB7185', d: [3, 2], lw: 1.4, pin: true,  txt: 'ACTIVE ENTRY ' + topAct.side + ' $' + topAct.entry.toFixed(2) }},
                    {{ p: topAct.sl,    c: '#EF4444', d: [2, 2], lw: 1.2, pin: false, txt: 'SL $' + topAct.sl.toFixed(2) }},
                    {{ p: topAct.tp,    c: '#38BDF8', d: [2, 2], lw: 1.2, pin: false, txt: 'TP $' + topAct.tp.toFixed(2) }}
                );
            }}
        }}

        const drawnPriceKeys = new Set();
        const placedPillBoxes = [];
        const pendingPins = [];
        const pillFont = chartW < 280 ? 'bold 8.5px "JetBrains Mono", monospace' : 'bold 9.5px "JetBrains Mono", monospace';
        const formatLevelTxt = (raw, compactOnly) => compactOnly
            ? raw.split('·')[0].replace(' (Trục cân đối)', '').trim()
            : raw;

        keyLevels.forEach(L => {{
            const px = Number(L.p);
            if (!px || Number.isNaN(px)) return;
            const pxKey = Math.round(px * 100);
            if (drawnPriceKeys.has(pxKey)) return;
            drawnPriceKeys.add(pxKey);

            const y = candleSeries.priceToCoordinate(px);
            if (y !== null && y >= 0 && y <= h) {{
                ctx.strokeStyle = L.c;
                ctx.setLineDash(L.d);
                ctx.lineWidth = L.lw || 1.3;
                ctx.beginPath();
                ctx.moveTo(0, y);
                ctx.lineTo(chartW, y);
                ctx.stroke();
                ctx.setLineDash([]);

                const boxTop = Math.min(h - 16, Math.max(2, y - 12));
                const boxBot = boxTop + 14;
                const textY = boxTop + 10;
                const labelTxt = formatLevelTxt(L.txt, chartW < 280);
                ctx.font = pillFont;
                ctx.textAlign = 'right';
                const tw = ctx.measureText(labelTxt).width;
                let labelRightX = chartW - 9;
                let guard = 0;
                while (guard < 3) {{
                    const boxLeft = labelRightX - tw - 5;
                    const hit = placedPillBoxes.find(b =>
                        !(labelRightX + 5 < b.left || boxLeft > b.right) &&
                        !(boxBot < b.top || boxTop > b.bottom)
                    );
                    if (!hit) break;
                    labelRightX = hit.left - 10;
                    guard++;
                }}
                if (labelRightX - tw - 5 >= 4) {{
                    ctx.fillStyle = 'rgba(6, 8, 14, 0.90)';
                    ctx.fillRect(labelRightX - tw - 5, boxTop, tw + 10, 14);
                    ctx.strokeStyle = L.c;
                    ctx.lineWidth = 1;
                    ctx.strokeRect(labelRightX - tw - 5, boxTop, tw + 10, 14);
                    ctx.fillStyle = L.c;
                    ctx.fillText(labelTxt, labelRightX, textY);
                    placedPillBoxes.push({{ left: labelRightX - tw - 5, right: labelRightX + 5, top: boxTop, bottom: boxBot }});
                }}
            }} else if (L.pin && y !== null && (y < 0 || y > h)) {{
                pendingPins.push({{ L: L, isTop: y < 0 }});
            }}
        }});

        // Render offscreen edge pins
        let topPinCount = 0;
        let botPinCount = 0;
        pendingPins.forEach(item => {{
            if (item.isTop && topPinCount >= 4) return;
            if (!item.isTop && botPinCount >= 4) return;
            const shortTxt = (item.isTop ? '▲ ' : '▼ ') + formatLevelTxt(item.L.txt.split('·')[0], chartW < 280);
            ctx.font = pillFont;
            ctx.textAlign = 'right';
            const tw = ctx.measureText(shortTxt).width;
            const pinLeft = chartW - tw - 14;
            const pinRight = chartW - 4;
            if (pinLeft < 4) return;

            let chosenEdgeY = null;
            for (let slot = 0; slot < 6; slot++) {{
                const candidateY = item.isTop ? (14 + slot * 16) : (h - 8 - slot * 16);
                const pTop = candidateY - 11;
                const pBot = candidateY + 3;
                const hit = placedPillBoxes.find(b =>
                    !(pinRight < b.left || pinLeft > b.right) &&
                    !(pBot < b.top || pTop > b.bottom)
                );
                if (!hit) {{
                    chosenEdgeY = candidateY;
                    break;
                }}
            }}
            if (chosenEdgeY === null) return;
            if (item.isTop) topPinCount++; else botPinCount++;

            ctx.fillStyle = 'rgba(15, 23, 42, 0.92)';
            ctx.fillRect(pinLeft, chosenEdgeY - 11, tw + 10, 14);
            ctx.strokeStyle = item.L.c;
            ctx.lineWidth = 1;
            ctx.strokeRect(pinLeft, chosenEdgeY - 11, tw + 10, 14);
            ctx.fillStyle = item.L.c;
            ctx.fillText(shortTxt, chartW - 9, chosenEdgeY);
            placedPillBoxes.push({{ left: pinLeft, right: pinRight, top: chosenEdgeY - 11, bottom: chosenEdgeY + 3 }});
        }});

        // Synchronize and repaint Right Dedicated Profile Panel
        drawNeiroProfilePanel();
    }}

    // ----------------------------------------------------------------------------
    // Dedicated Right Profile Panel: 6-Column Matrix [VOL | FLOW | GEX | VEX | CHEX | THETA]
    // ----------------------------------------------------------------------------
    function drawNeiroProfilePanel() {{
        const canvas = document.getElementById('neiro-profile-canvas');
        if (!canvas || !neiroChart || !candleSeries) return;
        const ctx = canvas.getContext('2d');
        const w = canvas.width;
        const h = canvas.height;
        ctx.clearRect(0, 0, w, h);

        const m = window.INITIAL_META;
        const opts = window.INITIAL_OPTIONS || [];
        if (!opts.length) return;

        // Background
        ctx.fillStyle = '#080B12';
        ctx.fillRect(0, 0, w, h);

        // 6 Columns: VOL, FLOW, GEX, VEX, CHEX, THETA
        const cols = [
            {{ key: 'currentVol',     name: 'VOL',   unit: 'HĐ',  pos: '#FBBF24', neg: '#FBBF24', bPos: '#F59E0B', bNeg: '#F59E0B' }},
            {{ key: 'currentNetFLOW', name: 'FLOW',  unit: 'GC',  pos: '#22C55E', neg: '#F43F5E', bPos: '#4ADE80', bNeg: '#FB7185' }},
            {{ key: 'currentNetGEX',  name: 'GEX',   unit: 'M',   pos: '#10B981', neg: '#EF4444', bPos: '#34D399', bNeg: '#F87171' }},
            {{ key: 'currentNetVEX',  name: 'VEX',   unit: 'M',   pos: '#06B6D4', neg: '#0284C7', bPos: '#22D3EE', bNeg: '#38BDF8' }},
            {{ key: 'currentNetCHEX', name: 'CHEX',  unit: 'M/d', pos: '#A855F7', neg: '#7E22CE', bPos: '#C084FC', bNeg: '#D8B4FE' }},
            {{ key: 'currentNetTEX',  name: 'THETA', unit: 'M/d', pos: '#F59E0B', neg: '#D97706', bPos: '#FBBF24', bNeg: '#FCD34D' }},
        ];

        const strikeColW = 46;
        const matrixW = Math.max(120, w - strikeColW);
        const colW = matrixW / cols.length;

        // 1. Air Pocket Vacuum horizontal background bands
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
                const bandH = Math.max(12, botY - topY);
                if (topY <= h && botY >= 0) {{
                    const apSev = String(ap.severity || '').toUpperCase();
                    const isDeep = (apSev === 'CRITICAL') || (apSev === 'HIGH');
                    ctx.fillStyle = isDeep ? 'rgba(249, 115, 22, 0.22)' : 'rgba(56, 189, 248, 0.14)';
                    ctx.fillRect(0, topY, w, bandH);
                    ctx.strokeStyle = isDeep ? 'rgba(251, 146, 60, 0.70)' : 'rgba(56, 189, 248, 0.60)';
                    ctx.lineWidth = 1;
                    ctx.strokeRect(0, topY, w, bandH);
                }}
            }}
        }});

        // 2. Render Columns
        cols.forEach((c, ci) => {{
            const cx = ci * colW + colW / 2;

            let visibleMaxAbs = 1e-9;
            let globalMaxAbs = 1e-9;
            opts.forEach(o => {{
                let val = 0;
                if (c.key === 'currentVol') {{
                    val = Number(sessionVolByStrike[o.strike] || 0);
                }} else {{
                    val = Math.abs(Number(o[c.key] || 0));
                }}
                globalMaxAbs = Math.max(globalMaxAbs, val);
                const y = candleSeries.priceToCoordinate(o.strike);
                if (y !== null && y >= 24 && y <= h - 4) {{
                    visibleMaxAbs = Math.max(visibleMaxAbs, val);
                }}
            }});
            if (visibleMaxAbs < 1e-6) visibleMaxAbs = globalMaxAbs > 1e-6 ? globalMaxAbs : 1.0;

            // Column vertical divider line
            ctx.strokeStyle = 'rgba(148, 163, 184, 0.14)';
            ctx.beginPath();
            ctx.moveTo(cx, 24);
            ctx.lineTo(cx, h);
            ctx.stroke();

            // Column Header
            ctx.fillStyle = c.name === 'VOL' ? '#FACC15' : (c.name === 'FLOW' ? '#4ADE80' : (c.name === 'VEX' ? '#22D3EE' : (c.name === 'CHEX' ? '#C084FC' : (c.name === 'GEX' ? '#34D399' : '#FBBF24'))));
            ctx.font = 'bold 9px "JetBrains Mono", monospace';
            ctx.textAlign = 'center';
            ctx.fillText(c.name, cx, 11);

            // Column Scale Subheader
            let scaleTxt = '';
            if (c.name === 'VOL') {{
                scaleTxt = visibleMaxAbs >= 1000 ? (visibleMaxAbs / 1000).toFixed(1) + 'k' : Math.round(visibleMaxAbs);
            }} else {{
                scaleTxt = '±' + (visibleMaxAbs >= 10 ? visibleMaxAbs.toFixed(0) : (visibleMaxAbs >= 1 ? visibleMaxAbs.toFixed(1) : visibleMaxAbs.toFixed(2))) + c.unit;
            }}
            ctx.fillStyle = 'rgba(148, 163, 184, 0.65)';
            ctx.font = '7.5px "JetBrains Mono", monospace';
            ctx.fillText(scaleTxt, cx, 21);

            // Bars
            const maxBarW = colW / 2 - 2;
            opts.forEach(o => {{
                const y = candleSeries.priceToCoordinate(o.strike);
                if (y === null || y < 24 || y > h - 4) return;

                let v = 0;
                let isPocStrike = false;
                if (c.key === 'currentVol') {{
                    v = Number(sessionVolByStrike[o.strike] || 0);
                    if (sessionPocPrice && Math.abs(o.strike - sessionPocPrice) <= 2.5) {{
                        isPocStrike = true;
                    }}
                }} else {{
                    v = Number(o[c.key] || 0);
                }}
                if (v === 0) return;

                const norm = Math.min(1.0, Math.abs(v) / visibleMaxAbs);
                const scaled = Math.pow(norm, 0.50);
                let len = scaled * maxBarW;
                if (Math.abs(v) > 0.0001) len = Math.max(3.0, len);

                const barH = c.name === 'VOL' ? 8 : (c.name === 'FLOW' ? 7 : 6);

                if (c.name === 'VOL') {{
                    const barX = cx - len / 2;
                    ctx.fillStyle = isPocStrike ? 'rgba(250, 204, 21, 0.95)' : 'rgba(251, 191, 36, 0.65)';
                    ctx.fillRect(barX, y - barH / 2, len, barH);
                    ctx.strokeStyle = isPocStrike ? '#FACC15' : '#D97706';
                    ctx.lineWidth = isPocStrike ? 1.2 : 0.7;
                    ctx.strokeRect(barX, y - barH / 2, len, barH);

                    if (isPocStrike) {{
                        ctx.fillStyle = '#FACC15';
                        ctx.font = 'bold 8px "JetBrains Mono", monospace';
                        ctx.textAlign = 'right';
                        ctx.fillText('★POC', barX - 2, y + 3);
                    }}
                }} else {{
                    const barX = v >= 0 ? cx : cx - len;
                    ctx.fillStyle = v >= 0 ? c.pos : c.neg;
                    ctx.fillRect(barX, y - barH / 2, len, barH);
                    ctx.strokeStyle = v >= 0 ? c.bPos : c.bNeg;
                    ctx.lineWidth = 0.8;
                    ctx.strokeRect(barX, y - barH / 2, len, barH);

                    if (c.name === 'FLOW' && o.isWhale) {{
                        ctx.fillStyle = '#FACC15';
                        ctx.font = 'bold 7.5px "JetBrains Mono", monospace';
                        ctx.textAlign = 'right';
                        ctx.fillText('⚡W', barX - 1, y + 3);
                    }}
                }}
            }});
        }});

        // 3. Right Strike Price Labels Column
        ctx.fillStyle = 'rgba(15, 23, 42, 0.75)';
        ctx.fillRect(matrixW, 0, strikeColW, h);
        ctx.strokeStyle = 'rgba(148, 163, 184, 0.20)';
        ctx.beginPath();
        ctx.moveTo(matrixW, 0);
        ctx.lineTo(matrixW, h);
        ctx.stroke();

        ctx.fillStyle = '#64748B';
        ctx.font = 'bold 8.5px "JetBrains Mono", monospace';
        ctx.textAlign = 'center';
        ctx.fillText('STRIKE', matrixW + strikeColW / 2, 16);

        opts.forEach(o => {{
            const y = candleSeries.priceToCoordinate(o.strike);
            if (y === null || y < 24 || y > h - 4) return;
            const isPoc = sessionPocPrice && Math.abs(o.strike - sessionPocPrice) <= 2.5;
            ctx.fillStyle = isPoc ? '#FACC15' : 'rgba(226, 232, 240, 0.82)';
            ctx.font = isPoc ? 'bold 9.5px "JetBrains Mono", monospace' : '8.5px "JetBrains Mono", monospace';
            ctx.textAlign = 'center';
            ctx.fillText('$' + Math.round(o.strike), matrixW + strikeColW / 2, y + 3);
        }});

        // 4. Interactive Hover Tooltip inside Right Panel
        if (hoveredOption && hoveredY !== null && hoveredY >= 24 && hoveredY <= h - 4) {{
            ctx.strokeStyle = 'rgba(250, 204, 21, 0.7)';
            ctx.setLineDash([2, 2]);
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(0, hoveredY);
            ctx.lineTo(w, hoveredY);
            ctx.stroke();
            ctx.setLineDash([]);

            const stk = hoveredOption.strike;
            const volVal = sessionVolByStrike[stk] || 0;
            const flowVal = hoveredOption.currentNetFLOW || 0;
            const gexHint = hoveredOption.currentNetGEX >= 0 ? '-> GEX (+): Đánh ĐẢO CHIỀU' : '-> GEX (-): Đánh THUẬN CHIỀU';
            const isPoc = sessionPocPrice && Math.abs(stk - sessionPocPrice) <= 2.5;

            const ttLines = [
                'Strike $' + stk.toFixed(0) + (isPoc ? ' ★POC' : '') + (hoveredOption.isWhale ? ' ⚡WHALE' : ''),
                'VOL: ' + Math.round(volVal) + ' HĐ' + (isPoc ? ' (KHỚP NHIỀU NHẤT)' : ''),
                'FLOW: ' + (flowVal >= 0 ? '+' : '') + flowVal.toFixed(1) + ' HĐ GC',
                'Vol C/P: ' + (hoveredOption.c_vol || 0) + ' / ' + (hoveredOption.p_vol || 0),
                'GEX: ' + (hoveredOption.currentNetGEX >= 0 ? '+' : '') + hoveredOption.currentNetGEX.toFixed(1) + 'M',
                'VEX: ' + (hoveredOption.currentNetVEX >= 0 ? '+' : '') + hoveredOption.currentNetVEX.toFixed(2) + 'M',
                'CHEX: ' + (hoveredOption.currentNetCHEX >= 0 ? '+' : '') + hoveredOption.currentNetCHEX.toFixed(2) + 'M/d',
                gexHint,
            ];
            const ttW = 186;
            const ttH = 114;
            const ttX = Math.max(8, Math.min(w - ttW - 8, (hoveredMx || 100) - ttW / 2));
            const ttY = Math.min(h - ttH - 8, Math.max(8, hoveredY - ttH / 2));

            ctx.fillStyle = 'rgba(15, 23, 42, 0.96)';
            ctx.fillRect(ttX, ttY, ttW, ttH);
            ctx.strokeStyle = isPoc ? '#FACC15' : '#38BDF8';
            ctx.lineWidth = 1;
            ctx.strokeRect(ttX, ttY, ttW, ttH);

            ctx.textAlign = 'left';
            ctx.font = 'bold 9.5px "JetBrains Mono", monospace';
            ctx.fillStyle = '#F8FAFC';
            ctx.fillText(ttLines[0], ttX + 6, ttY + 13);

            ctx.font = '8.5px "JetBrains Mono", monospace';
            ctx.fillStyle = '#FACC15';
            ctx.fillText(ttLines[1], ttX + 6, ttY + 26);
            ctx.fillStyle = flowVal >= 0 ? '#4ADE80' : '#FB7185';
            ctx.fillText(ttLines[2], ttX + 6, ttY + 39);
            ctx.fillStyle = '#FBBF24';
            ctx.fillText(ttLines[3], ttX + 6, ttY + 52);
            ctx.fillStyle = hoveredOption.currentNetGEX >= 0 ? '#4ADE80' : '#F87171';
            ctx.fillText(ttLines[4], ttX + 6, ttY + 65);
            ctx.fillStyle = '#22D3EE';
            ctx.fillText(ttLines[5], ttX + 6, ttY + 78);
            ctx.fillStyle = '#C084FC';
            ctx.fillText(ttLines[6], ttX + 6, ttY + 91);
            ctx.font = 'bold 8.5px "JetBrains Mono", monospace';
            ctx.fillStyle = hoveredOption.currentNetGEX >= 0 ? '#4ADE80' : '#F87171';
            ctx.fillText(ttLines[7], ttX + 6, ttY + 105);
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
        const urls = [];
        if (window.location.protocol !== 'file:') {{
            urls.push('version.json?_t=' + ts);
        }}
        urls.push('https://raw.githubusercontent.com/DaniNguyen2509/Neiro-Gold-Quant/main/version.json?_t=' + ts);
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

    function getTfPeriodSec(tfKey = '1m') {{
        const k = String(tfKey || '1m').toLowerCase();
        if (k === '5m') return 300;
        if (k === '15m') return 900;
        if (k === '1h') return 3600;
        if (k === '1d' || k === 'd') return 86400;
        return 60;
    }}

    function mergeLiveCandles(newCandles, tfKey = '1m', resetSeries = false) {{
        if (!Array.isArray(newCandles) || newCandles.length === 0) return;
        const tfSec = getTfPeriodSec(tfKey);
        const targetList = resetSeries ? [] : ((tfKey === '1m')
            ? (window.INITIAL_CANDLES || [])
            : ((window.INITIAL_TF_CANDLES && window.INITIAL_TF_CANDLES[tfKey]) || []));

        let baselineMap = null;
        let prevCount = 0;
        if (!resetSeries) {{
            if (renderedSeriesTf === tfKey && renderedSeriesBarsByTime.size > 0) {{
                baselineMap = renderedSeriesBarsByTime;
                prevCount = renderedSeriesCount;
            }} else if (targetList.length > 0) {{
                baselineMap = new Map();
                for (let i = 0; i < targetList.length; i++) {{
                    const tb = targetList[i];
                    if (tb && tb.time) {{
                        const rawTbTime = Math.floor(Number(tb.time));
                        const tbTime = tfSec < 86400 ? (rawTbTime - (rawTbTime % tfSec)) : rawTbTime;
                        baselineMap.set(tbTime, {{
                            time: tbTime,
                            open: Number(tb.open),
                            high: Number(tb.high),
                            low: Number(tb.low),
                            close: Number(tb.close),
                        }});
                    }}
                }}
                prevCount = baselineMap.size;
            }}
        }}

        const byTime = new Map();
        let latestKey = 0;

        function ingestBar(b, allowOverwrite) {{
            if (!b || !b.time) return;
            const rawT = Math.floor(Number(b.time));
            const vol = Math.max(0, Number(b.volume || 0));
            const spread = Math.abs(Number(b.high || 0) - Number(b.low || 0));
            // Drop/fold Yahoo unaligned trailing quote dots (:15, :35, :44 with 0 volume and 0 spread)
            if (tfSec < 86400 && (rawT % tfSec) !== 0 && vol <= 0 && spread < 0.05) {{
                if (latestKey > 0 && byTime.has(latestKey)) {{
                    const prev = byTime.get(latestKey);
                    const px = Number(b.close || 0);
                    if (px > 500 && Math.abs(px - prev.close) <= 25.0) {{
                        prev.close = px;
                        prev.high = Math.max(prev.high, px);
                        prev.low = Math.min(prev.low, px);
                    }}
                }}
                return;
            }}
            const bucketT = tfSec < 86400 ? (rawT - (rawT % tfSec)) : rawT;
            if (byTime.has(bucketT) && !allowOverwrite) {{
                const ex = byTime.get(bucketT);
                ex.high = Math.max(ex.high, Number(b.high));
                ex.low = Math.min(ex.low, Number(b.low));
                ex.close = Number(b.close);
                ex.volume = Math.max(Number(ex.volume || 0), vol);
            }} else {{
                byTime.set(bucketT, {{
                    time: bucketT,
                    open: Number(b.open),
                    high: Number(b.high),
                    low: Number(b.low),
                    close: Number(b.close),
                    volume: vol,
                    delta: b.delta || 0,
                }});
            }}
            if (bucketT > latestKey) latestKey = bucketT;
        }}

        for (let i = 0; i < targetList.length; i++) {{
            ingestBar(targetList[i], true);
        }}
        for (let i = 0; i < newCandles.length; i++) {{
            ingestBar(newCandles[i], false);
        }}
        const merged = Array.from(byTime.values()).sort((a, b) => a.time - b.time).slice(-360);
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
            if (typeof computeVolumeProfile === 'function') {{
                computeVolumeProfile(targetList);
            }}

            // Use setData() whenever resetSeries is set, or any earlier/intermediate bar
            // (gap fill, tab-sleep backfill, or historical bar revision) differs from rendered series.
            let needsFullSetData = Boolean(resetSeries || !baselineMap || baselineMap.size === 0);
            if (!needsFullSetData) {{
                for (let i = 0; i < merged.length - 1; i++) {{
                    const b = merged[i];
                    const prev = baselineMap.get(b.time);
                    if (!prev) {{
                        needsFullSetData = true;
                        break;
                    }}
                    if (
                        Math.abs(prev.open - b.open) > 1e-6 ||
                        Math.abs(prev.high - b.high) > 1e-6 ||
                        Math.abs(prev.low - b.low) > 1e-6 ||
                        Math.abs(prev.close - b.close) > 1e-6
                    ) {{
                        needsFullSetData = true;
                        break;
                    }}
                }}
            }}

            const applyFullSeries = () => {{
                const tsApi = (neiroChart && typeof neiroChart.timeScale === 'function') ? neiroChart.timeScale() : null;
                const prevRange = (tsApi && typeof tsApi.getVisibleLogicalRange === 'function')
                    ? tsApi.getVisibleLogicalRange()
                    : null;
                const wasAtRightEdge = !prevRange || prevCount === 0 || (prevRange.to >= prevCount - 3);
                candleSeries.setData(merged.map(c => ({{ time: c.time, open: c.open, high: c.high, low: c.low, close: c.close }})));
                if (tsApi && typeof tsApi.setVisibleLogicalRange === 'function' && (resetSeries || wasAtRightEdge)) {{
                    const span = prevRange ? Math.max(30, Math.min(240, prevRange.to - prevRange.from)) : 128;
                    tsApi.setVisibleLogicalRange({{
                        from: Math.max(0, merged.length + 8 - span),
                        to: merged.length + 8,
                    }});
                }}
            }};

            if (needsFullSetData) {{
                applyFullSeries();
            }} else {{
                try {{
                    candleSeries.update({{
                        time: lastBar.time,
                        open: lastBar.open,
                        high: lastBar.high,
                        low: lastBar.low,
                        close: lastBar.close,
                    }});
                }} catch (e) {{
                    applyFullSeries();
                }}
            }}
            recordRenderedSeries(merged, tfKey);
            applyLiveTick(lastBar.close, null, true);
        }}
    }}

    let lastYahooPollEpoch = 0;

    async function fetchJsonWithTimeout(url, timeoutMs = 5000) {{
        const ctrl = (typeof AbortController !== 'undefined') ? new AbortController() : null;
        const timer = ctrl ? setTimeout(() => ctrl.abort(), timeoutMs) : null;
        try {{
            const res = await fetch(url, {{ cache: 'no-store', signal: ctrl ? ctrl.signal : undefined }});
            if (!res || !res.ok) return null;
            return await res.json();
        }} finally {{
            if (timer) clearTimeout(timer);
        }}
    }}

    async function pollLiveYahooChart(tf = currentTf) {{
        const ts = Date.now();
        lastYahooPollEpoch = ts;
        const candidates = [];
        const workerUrl = getCloudFeedWorkerUrl();
        if (workerUrl) {{
            candidates.push({{
                kind: 'worker',
                timeoutMs: 6500,
                url: workerUrl + '/api/yahoo_gc?tf=' + encodeURIComponent(tf) + '&_t=' + ts,
            }});
        }}

        for (let i = 0; i < candidates.length; i++) {{
            const cand = candidates[i];
            try {{
                const payload = await fetchJsonWithTimeout(cand.url, cand.timeoutMs);
                if (!payload || (!payload.available && !(Array.isArray(payload.candles) && payload.candles.length > 0))) {{
                    continue;
                }}
                lastCloudWorkerEpoch = Date.now();
                const nextSrc = String(payload.source || '');
                const sourceSwitched = Boolean(nextSrc && lastCloudFeedSource && nextSrc !== lastCloudFeedSource)
                    || Boolean(!lastCloudFeedSource && nextSrc.startsWith('ctrader_'));
                if (nextSrc) lastCloudFeedSource = nextSrc;

                if (window.INITIAL_META) {{
                    window.INITIAL_META.timestamp_utc = new Date().toISOString();
                    if (payload.market_open !== undefined) {{
                        window.INITIAL_META.market_open = Boolean(payload.market_open);
                    }}
                }}
                if (payload.vpin_pct !== undefined) {{
                    liveVpinPct = Number(payload.vpin_pct);
                    if (payload.vpin_label) liveVpinLabel = String(payload.vpin_label);
                    if (payload.bvc_buy_pct !== undefined) liveBuyPct = Number(payload.bvc_buy_pct);
                    if (payload.bvc_cvd_contracts !== undefined) liveCvdContracts = Number(payload.bvc_cvd_contracts);
                    if (payload.kyle_lambda_label) liveKyleLabel = String(payload.kyle_lambda_label);
                    if (payload.atr_5m !== undefined) liveAtr5m = Number(payload.atr_5m);
                    lastAuthoritativeVpinEpoch = Date.now();
                }}
                if (Array.isArray(payload.candles) && payload.candles.length > 0) {{
                    mergeLiveCandles(payload.candles, tf, sourceSwitched);
                }}
                if (payload.latest_price) {{
                    applyLiveTick(Number(payload.latest_price), null, true);
                }} else {{
                    updateRealtimeTacticalCockpit();
                }}
                buildEpoch = Date.now();
                updateCloudWorkerButtonState();
                updateSyncTimeAgo();
                updateSyncBadgeHonest();
                return true;
            }} catch (e) {{
                // Try next live endpoint cleanly
            }}
        }}
        updateCloudWorkerButtonState();
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
        const streamLive = Boolean(
            lastCloudWorkerEpoch && (nowMs - lastCloudWorkerEpoch) < 15000
        );
        const allowLiveMarketState = Boolean(opts.forceLive || !streamLive);

        if (allowLiveMarketState && data.market_open !== undefined) m.market_open = Boolean(data.market_open);
        if (data.dte_days) m.dte_days = Number(data.dte_days);
        const rolledContract = Boolean(
            (data.contract_symbol && m.contract_symbol && data.contract_symbol !== m.contract_symbol) ||
            (data.expiration_date && m.expiration_date && data.expiration_date !== m.expiration_date)
        );
        if (data.contract_symbol) {{
            m.contract_symbol = String(data.contract_symbol);
            const subEl = document.getElementById('subbar-contract-label');
            if (subEl) subEl.innerText = 'NEIRO-QUANT TERMINAL • CME GOLD FUTURES [GC=F / ' + m.contract_symbol + ']';
            const kpiLbl = document.getElementById('kpi-contract-label');
            if (kpiLbl) kpiLbl.innerText = 'CME Gold Futures ' + m.contract_symbol + ' (COMEX)';
            document.title = 'NEIRO-QUANT: ' + m.contract_symbol + ' GOLD OPTIONS TACTICAL TERMINAL';
        }}
        if (data.option_symbol) m.option_symbol = String(data.option_symbol);
        if (data.expiration_date) m.expiration_date = String(data.expiration_date);
        if (data.expiration_date_iso) m.expiration_date_iso = String(data.expiration_date_iso);
        if (rolledContract && !opts.forceLive) {{
            try {{
                const lastRollReload = Number(sessionStorage.getItem('neiro_roll_reload_ts') || 0);
                if ((Date.now() - lastRollReload) > 60000) {{
                    sessionStorage.setItem('neiro_roll_reload_ts', String(Date.now()));
                    window.location.replace(window.location.pathname + window.location.search);
                    return true;
                }}
            }} catch (_) {{}}
        }}
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
            const elHud = document.getElementById('hud-post-sweep-val');
            if (elHud) {{
                let psCompact = 'CHỜ TÍN HIỆU SWEEP';
                if (psRegime === 'TOXIC_CASCADE_BLOCKED') psCompact = 'CẤM CẢN TÀU (VPIN CAO)';
                else if (psRegime === 'POST_SWEEP_V_SHAPE') {{
                    const d = String((data.post_sweep_execution && data.post_sweep_execution.direction) || '').trim().toUpperCase();
                    psCompact = (d && d !== 'NONE') ? ('V-SHAPE ' + d) : 'V-SHAPE ĐẢO CHIỀU';
                }}
                else if (psRegime === 'POST_SWEEP_PULLBACK') psCompact = 'CHỜ HỒI FVG 50%–75%';
                elHud.innerText = psCompact;
                elHud.style.color = psCol;
                if (vacTitle) elHud.title = vacTitle;
            }}
            const elMicro = document.getElementById('micro-post-sweep-val');
            if (elMicro) {{
                elMicro.innerText = psLabel;
                elMicro.style.color = psCol;
                if (vacTitle) elMicro.title = vacTitle;
            }}
        }}
        let staticRecentMaxTime = 0;
        if (Array.isArray(data.recent_candles) && data.recent_candles.length > 0) {{
            for (let i = 0; i < data.recent_candles.length; i++) {{
                const t = Number((data.recent_candles[i] && data.recent_candles[i].time) || 0);
                if (t > staticRecentMaxTime) staticRecentMaxTime = t;
            }}
        }}
        const staticIsOlderThanActive = Boolean(
            activeCandle && (
                (staticRecentMaxTime > 0 && staticRecentMaxTime < activeCandle.time) ||
                (incomingMs > 0 && (incomingMs / 1000) < activeCandle.time)
            )
        );
        if (allowLiveMarketState && Array.isArray(data.recent_candles) && data.recent_candles.length > 0) {{
            mergeLiveCandles(data.recent_candles, '1m');
        }}
        if (allowLiveMarketState && data.tf_candles && typeof data.tf_candles === 'object') {{
            Object.keys(data.tf_candles).forEach((k) => {{
                mergeLiveCandles(data.tf_candles[k], k);
            }});
        }}
        if (allowLiveMarketState && !staticIsOlderThanActive && data.timestamp_utc) m.timestamp_utc = data.timestamp_utc;
        if (data.regime) m.regime = data.regime;
        if (data.call_wall_siege !== undefined) m.call_wall_siege = Number(data.call_wall_siege);
        if (data.put_wall_siege !== undefined) m.put_wall_siege = Number(data.put_wall_siege);
        if (data.major_up_wall) m.major_up_wall = Number(data.major_up_wall);
        if (data.major_down_wall) m.major_down_wall = Number(data.major_down_wall);
        if (data.has_up_air_pocket !== undefined) m.has_up_air_pocket = Boolean(data.has_up_air_pocket);
        if (data.has_down_air_pocket !== undefined) m.has_down_air_pocket = Boolean(data.has_down_air_pocket);
        if (allowLiveMarketState && !staticIsOlderThanActive && data.vpin_pct !== undefined && (lastAuthoritativeVpinEpoch === 0 || (nowMs - lastAuthoritativeVpinEpoch) >= 15000 || incomingMs >= lastAuthoritativeVpinEpoch)) {{
            liveVpinPct = Number(data.vpin_pct);
            if (data.vpin_label) liveVpinLabel = String(data.vpin_label);
            if (data.kyle_lambda_label) {{
                liveKyleLabel = String(data.kyle_lambda_label);
                const hudKyle = document.getElementById('hud-kyle-val');
                if (hudKyle) {{
                    const kyleCompact = liveKyleLabel
                        .replace(' (ICEBERG LIMIT ABSORPTION)', ' (ICEBERG)')
                        .replace(' (VACUUM MARKET SWEEP)', ' (VACUUM)')
                        .replace('THANH KHOẢN SỔ LỆNH BÌNH THƯỜNG (BAR OLS)', 'SỔ LỆNH BÌNH THƯỜNG')
                        .replace('THANH KHOẢN SỔ LỆNH BÌNH THƯỜNG', 'SỔ LỆNH BÌNH THƯỜNG')
                        .replace('THANH KHOẢN BÌNH THƯỜNG', 'SỔ LỆNH BÌNH THƯỜNG');
                    hudKyle.innerText = kyleCompact;
                    hudKyle.title = liveKyleLabel;
                }}
            }}
            if (data.atr_5m !== undefined) liveAtr5m = Number(data.atr_5m);
            lastAuthoritativeVpinEpoch = Date.now();
        }}
        if (allowLiveMarketState && !staticIsOlderThanActive && data.spot_price) {{
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
    function getLivePollIntervalMs() {{
        return getCloudFeedWorkerUrl() ? 3000 : 10000;
    }}

    function connectLiveGoldOrderflowStream() {{
        if (!isCmeGlobexMarketOpen()) {{
            updateSyncBadgeHonest();
            setTimeout(connectLiveGoldOrderflowStream, 30000);
            return;
        }}
        pollLiveYahooChart(currentTf);
        setTimeout(connectLiveGoldOrderflowStream, getLivePollIntervalMs());
    }}

    // Tự động kiểm tra Yahoo GC=F / Worker & Cloud mỗi 10s hoàn toàn tự động (Zero-Touch, Zero-Reload)
    setInterval(updateSyncTimeAgo, 15000);
    setInterval(() => checkCloudSyncNow(false), 10000);
    window.addEventListener('focus', () => checkCloudSyncNow(false));

    // Auto-init 100% hands-free on load (supports ?worker=https://... quick setup link)
    window.addEventListener('DOMContentLoaded', () => {{
        try {{
            const qWorker = new URLSearchParams(window.location.search).get('worker');
            const normQ = normalizeCloudWorkerUrl(qWorker);
            if (normQ) localStorage.setItem(CLOUD_WORKER_STORAGE_KEY, normQ);
        }} catch (e) {{}}
        updateCloudWorkerButtonState();
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
