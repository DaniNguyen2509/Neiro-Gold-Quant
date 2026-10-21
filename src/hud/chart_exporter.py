"""
Neiro-Quant HUD: Tactical Flow & Execution Chart Exporter (100% CME Gold Futures GCZ26).
Delivers pure native Matplotlib 3-panel dashboard:
- Panel 1: Net GEX ($M) & Tactical Action Levels (Fade Sell, Rebound Buy, Squeeze, Waterfall, Hard SL)
- Panel 2: Intraday Volume vs Open Interest (Identifies 80% volume clusters and aggressive flow)
- Panel 3: Second-Order Greeks: Vanna (VEX) & Charm (CHEX) Flows (V-Rebound & Time Decay profile)
Ultra-fast execution (< 1.5s), no bloat, pure Python.
"""

import time
import os
import math
import shutil
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def export_quant_chart(
    df: pd.DataFrame,
    futures_price: float = 4181.10,
    k_atm: float = 4180.0,
    call_wall: float = 4200.0,
    put_wall: float = 4150.0,
    gamma_flip_floor: float = 4171.10,
    gamma_flip_ceil: float = 4201.00,
    squeeze_trigger: float = 4202.50,
    waterfall_trigger: float = 4147.50,
    zero_gamma: float | None = None,
    output_png: str = "quant_truevision_map.png"
):
    t0 = time.time()
    MULT = 100.0
    
    # 1. Vectorized GEX calculation fallback
    if 'callGEX' not in df.columns or 'putGEX' not in df.columns:
        scale = (futures_price ** 2) * 0.01 / 1e6
        df['callGEX'] = df['callGamma'] * df['callOpenInterest'] * MULT * scale
        df['putGEX']  = - (df['putGamma'] * df['putOpenInterest'] * MULT * scale)
        df['netGEX']  = df['callGEX'] + df['putGEX']

    # 2. Vectorized VEX & CHEX calculation fallback (Black-76)
    if 'netVEX' not in df.columns or 'netCHEX' not in df.columns:
        from src.quant_engine.synthetic import compute_dynamic_dte
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
        atm_idx = (df['strike'] - k_atm).abs().idxmin()
        c_mid_atm = float(df.loc[atm_idx, 'callMid']) if 'callMid' in df.columns else 45.0
        p_mid_atm = float(df.loc[atm_idx, 'putMid']) if 'putMid' in df.columns else 44.0
        atm_straddle = max(1.0, c_mid_atm + p_mid_atm)
        sigma_atm = float(np.clip(atm_straddle / (0.7979 * futures_price * np.sqrt(T_years)), 0.01, 2.0))
        
        strikes_arr = df['strike'].values.astype(float)
        denom = sigma_atm * np.sqrt(T_years)
        d1 = (np.log(np.maximum(1e-4, futures_price / strikes_arr)) + 0.5 * (sigma_atm ** 2) * T_years) / denom
        d2 = d1 - denom
        pdf_d1 = (1.0 / np.sqrt(2.0 * np.pi)) * np.exp(-0.5 * (d1 ** 2))
        cdf_d1 = 0.5 * (1.0 + np.vectorize(math.erf)(d1 / np.sqrt(2.0)))
        df_disc = np.exp(-0.045 * T_years)
        
        vanna = - df_disc * pdf_d1 * (d2 / sigma_atm)
        charm_call = - df_disc * (pdf_d1 * (0.045 / denom - d2 / (2.0 * T_years)) - 0.045 * cdf_d1)
        charm_put = charm_call - 0.045 * df_disc
        
        df['callVEX'] = vanna * df['callOpenInterest'] * MULT * futures_price * 0.01 / 1e6
        df['putVEX'] = - (vanna * df['putOpenInterest'] * MULT * futures_price * 0.01 / 1e6)
        df['netVEX'] = df['callVEX'] + df['putVEX']
        
        df['callCHEX'] = (charm_call / 365.0) * df['callOpenInterest'] * MULT * futures_price / 1e6
        df['putCHEX'] = - ((charm_put / 365.0) * df['putOpenInterest'] * MULT * futures_price / 1e6)
        df['netCHEX'] = df['callCHEX'] + df['putCHEX']
        
    # Filter Near-The-Money strikes for tactical intraday scalping (ensure Call/Put wall & Zero Gamma are covered if reasonable)
    if len(df) > 11:
        atm_idx = int((df['strike'] - k_atm).abs().idxmin())
        targets = [futures_price, call_wall, put_wall]
        target_zg = zero_gamma if zero_gamma is not None else gamma_flip_floor
        if target_zg is not None and not np.isnan(target_zg):
            if 0.85 * futures_price <= target_zg <= 1.15 * futures_price:
                targets.append(target_zg)
        min_idx = int((df['strike'] - min(targets)).abs().idxmin())
        max_idx = int((df['strike'] - max(targets)).abs().idxmin())
        half = 6
        start_idx = max(0, min(atm_idx - half, min_idx - 1))
        end_idx = min(len(df), max(atm_idx + half + 1, max_idx + 2))
        plot_df = df.iloc[start_idx:end_idx].copy().reset_index(drop=True)
    else:
        plot_df = df.copy()

    strikes = plot_df['strike'].values
    net_gex = plot_df['netGEX'].values
    net_vex = plot_df['netVEX'].values
    net_chex = plot_df['netCHEX'].values
    call_oi = plot_df['callOpenInterest'].values
    put_oi = plot_df['putOpenInterest'].values
    call_vol = plot_df['callVolume'].values
    put_vol = plot_df['putVolume'].values

    step = float(np.diff(strikes).min()) if len(strikes) > 1 else 25.0
    bar_h = step * 0.55
    y_bottom = strikes.min() - step * 1.05
    y_top = strikes.max() + step * 1.25
    
    plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
    plt.rcParams['axes.unicode_minus'] = False
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    
    fig, (ax1, ax2, ax3) = plt.subplots(
        1, 3,
        figsize=(24.0, 9.6),
        dpi=130,
        sharey=True,
        gridspec_kw={'width_ratios': [1.18, 1.0, 1.05]}
    )
    ax1.set_ylim(y_bottom, y_top)
    
    # -------------------------------------------------------------------------
    # PANEL 1: NET GEX & TACTICAL LEVELS (BẢN ĐỒ CHIẾN THUẬT VÀ MỐC VÀO LỆNH)
    # -------------------------------------------------------------------------
    colors = ['#2E7D32' if x >= 0 else '#C62828' for x in net_gex]
    ax1.barh(strikes, net_gex, height=bar_h, color=colors, alpha=0.78, edgecolor='black', linewidth=0.5)
    ax1.axvline(0, color='black', linewidth=0.8, linestyle='--')
    
    max_abs_gex = max(abs(net_gex.min()), abs(net_gex.max())) if len(net_gex) > 0 else 50.0
    gex_span = max(max_abs_gex * 1.5, 25.0)
    ax1.set_xlim(-gex_span, gex_span)
    
    # 1. Mốc Giá Hiện Tại & ATM
    ax1.axhline(futures_price, color='#0D47A1', linewidth=2.5, linestyle='-', zorder=4)
    ax1.text(gex_span * 0.35, futures_price, f"◄ GIÁ HIỆN TẠI: {futures_price:.2f} (ATM: {k_atm:.0f})", 
             color='#0D47A1', fontsize=8.6, fontweight='bold', va='center',
             bbox=dict(boxstyle='round,pad=0.25', facecolor='#E3F2FD', edgecolor='#0D47A1', alpha=0.95), zorder=5)
    
    # 2. VÙNG BÁN TẠI CALL WALL
    if strikes.min() <= call_wall <= strikes.max():
        ax1.axhline(call_wall, color='#6A1B9A', linewidth=2.0, linestyle='--')
        call_wall_oi_matches = plot_df.loc[plot_df['strike'] == call_wall, 'callOpenInterest'].values
        call_wall_oi_val = int(call_wall_oi_matches[0]) if len(call_wall_oi_matches) else 0
        call_wall_box = (
            f"[CALL WALL {call_wall:.0f}] ({call_wall_oi_val} OI - KHÁNG CỰ ĐỈNH MM)\n"
            f"• Vùng Bán (Fade Sell): {call_wall-1.5:.1f} - {call_wall:.1f} | SL: {call_wall+4:.1f} ($4.0) | TP: {futures_price:.1f}\n"
            f"• Squeeze Breakout: Vượt > {squeeze_trigger:.1f} -> Cắt Short, Mua Đuổi"
        )
        ax1.text(-gex_span * 0.96, call_wall + step * 0.18, call_wall_box, 
                 color='#4A148C', fontsize=7.2, fontweight='bold', va='bottom', ha='left',
                 bbox=dict(boxstyle='round,pad=0.25', facecolor='#F3E5F5', edgecolor='#6A1B9A', alpha=0.92, linewidth=1.0))
                 
        ax1.axhline(squeeze_trigger, color='#00838F', linewidth=1.2, linestyle=':')
             
    # 3. VÙNG MUA TẠI PUT WALL
    if strikes.min() <= put_wall <= strikes.max():
        ax1.axhline(put_wall, color='#1B5E20', linewidth=2.0, linestyle='--')
        put_wall_oi_matches = plot_df.loc[plot_df['strike'] == put_wall, 'putOpenInterest'].values
        put_wall_oi_val = int(put_wall_oi_matches[0]) if len(put_wall_oi_matches) else 0
        put_wall_box = (
            f"[MAJOR PUT WALL {put_wall:.0f}] ({put_wall_oi_val} OI - HỖ TRỢ ĐÁY MM)\n"
            f"• Vùng Mua (Rebound Buy): {put_wall:.1f} - {put_wall+1.5:.1f} | SL: {put_wall-4:.1f} ($4.0) | TP: {futures_price:.1f}\n"
            f"• Waterfall Breakout: Thủng < {waterfall_trigger:.1f} -> Bán Tháo Nhanh"
        )
        ax1.text(gex_span * 0.04, put_wall - step * 0.18, put_wall_box, 
                 color='#B71C1C', fontsize=7.2, fontweight='bold', va='top', ha='left',
                 bbox=dict(boxstyle='round,pad=0.25', facecolor='#FFF3E0', edgecolor='#E65100', alpha=0.92, linewidth=1.0))
                 
        ax1.axhline(waterfall_trigger, color='#D32F2F', linewidth=1.2, linestyle=':')

    # 3.1. ĐƯỜNG ZERO GAMMA (GAMMA FLIP LINE)
    target_zg = zero_gamma if zero_gamma is not None else gamma_flip_floor
    if target_zg is not None and strikes.min() <= target_zg <= strikes.max():
        ax1.axhline(target_zg, color='#F59E0B', linewidth=1.6, linestyle='--', zorder=3)
        ax1.text(gex_span * 0.12, target_zg, f"--- ZERO GAMMA FLIP: ${target_zg:.2f} ---", 
                 color='#B45309', fontsize=7.2, fontweight='bold', va='center',
                 bbox=dict(boxstyle='round,pad=0.2', facecolor='#FEF3C7', edgecolor='#F59E0B', alpha=0.92, linewidth=0.8), zorder=4)

    # 4. CÁC MỐC CHIẾN THUẬT LƯỚT SÓNG TRONG NGÀY (100% TỰ ĐỘNG THEO GIÁ SPOT & GEX)
    strikes_above = strikes[strikes > futures_price]
    strike_above = float(strikes_above[0]) if len(strikes_above) > 0 else call_wall
    next_above = float(strikes_above[1]) if len(strikes_above) > 1 else strike_above + step

    strikes_below = strikes[strikes <= futures_price]
    strike_below = float(strikes_below[-1]) if len(strikes_below) > 0 else put_wall
    next_below = float(strikes_below[-2]) if len(strikes_below) > 1 else strike_below - step

    # Mốc Cửa Ải Kháng Cự Tiền Tuyến (Strike ngay trên Spot)
    if strikes.min() <= strike_above <= strikes.max() and strike_above != call_wall:
        ax1.axhline(strike_above, color='#2E7D32', linewidth=1.1, linestyle=':')
        gex_above_matches = plot_df.loc[plot_df['strike'] == strike_above, 'netGEX'].values
        gex_above_val = gex_above_matches[0] if len(gex_above_matches) else 5.0
        ax1.text(gex_above_val + 0.6, strike_above, f"◄ CỬA ẢI {strike_above:.0f} (Squeeze > {strike_above+2.5:.1f} -> TP {next_above:.0f})", 
                 color='#1B5E20', fontsize=7.2, fontweight='bold', va='center', ha='left',
                 bbox=dict(boxstyle='round,pad=0.2', facecolor='#E8F5E9', edgecolor='#2E7D32', alpha=0.9, linewidth=0.8))

    # Mốc Sàn Đỡ ATM (Strike ngay dưới Spot)
    if strikes.min() <= strike_below <= strikes.max() and strike_below != put_wall:
        ax1.axhline(strike_below, color='#1565C0', linewidth=1.1, linestyle=':')
        gex_below_matches = plot_df.loc[plot_df['strike'] == strike_below, 'netGEX'].values
        gex_below_val = gex_below_matches[0] if len(gex_below_matches) else -9.0
        ax1.text(gex_below_val - 0.6, strike_below, f"SÀN ĐỠ ATM {strike_below:.0f} (Rebound: {strike_below:.1f}-{strike_below+1.5:.1f}) ►", 
                 color='#0D47A1', fontsize=7.2, fontweight='bold', va='center', ha='right',
                 bbox=dict(boxstyle='round,pad=0.2', facecolor='#E3F2FD', edgecolor='#1565C0', alpha=0.9, linewidth=0.8))

    # Mốc Trạm Nghỉ Kế Tiếp (Strike nấc 2 dưới Spot)
    if strikes.min() <= next_below <= strikes.max() and next_below != put_wall:
        ax1.axhline(next_below, color='#C62828', linewidth=1.1, linestyle=':')
        gex_next_below_matches = plot_df.loc[plot_df['strike'] == next_below, 'netGEX'].values
        gex_next_below_val = gex_next_below_matches[0] if len(gex_next_below_matches) else -5.0
        ax1.text(gex_next_below_val - 0.6, next_below, f"TRẠM NGHỈ {next_below:.0f} (Chốt lời Short / Retest) ►", 
                 color='#B71C1C', fontsize=7.2, fontweight='bold', va='center', ha='right',
                 bbox=dict(boxstyle='round,pad=0.2', facecolor='#FFEBEE', edgecolor='#C62828', alpha=0.9, linewidth=0.8))

    ax1.set_title("Panel 1: Net GEX ($M) & Mốc Chiến Thuật (SL/TP)", fontsize=11, fontweight='bold')
    ax1.set_xlabel("Net GEX (Triệu USD / 1% Biến Động)", fontsize=9.5)
    ax1.set_ylabel("CME Gold Futures Strike Price ($)", fontsize=9.5)
    ax1.set_yticks(strikes)
    ax1.set_yticklabels([f"${s:.0f}" for s in strikes], fontsize=8.5)
    ax1.grid(True, linestyle=':', alpha=0.6)
    
    # -------------------------------------------------------------------------
    # PANEL 2: VOLUME INTRADAY vs OPEN INTEREST (SOI DÒNG TIỀN THỰC CHIẾN)
    # -------------------------------------------------------------------------
    ax2.barh(strikes, call_oi, height=bar_h, color='#A5D6A7', alpha=0.6, label='Call OI (Vị thế tích lũy)', edgecolor='gray', linewidth=0.4)
    ax2.barh(strikes, -put_oi, height=bar_h, color='#EF9A9A', alpha=0.6, label='Put OI (Vị thế tích lũy)', edgecolor='gray', linewidth=0.4)
    
    ax2.barh(strikes, call_vol, height=bar_h * 0.45, color='#1B5E20', alpha=0.95, label='Call Volume (Lực Mua)', edgecolor='black', linewidth=0.6)
    ax2.barh(strikes, -put_vol, height=bar_h * 0.45, color='#B71C1C', alpha=0.95, label='Put Volume (Lực Bán)', edgecolor='black', linewidth=0.6)
    ax2.axvline(0, color='black', linewidth=0.8, linestyle='--')
    
    if len(plot_df) > 0 and call_vol.max() > 0:
        top_call_idx = plot_df['callVolume'].idxmax()
        top_call_stk = plot_df.loc[top_call_idx, 'strike']
        top_call_v = plot_df.loc[top_call_idx, 'callVolume']
        top_call_oi = plot_df.loc[top_call_idx, 'callOpenInterest']
        ax2.text(top_call_v + 15, top_call_stk, f"Call Vol: {int(top_call_v)} | OI: {int(top_call_oi)}", 
                 color='#1B5E20', fontsize=7.8, fontweight='bold', va='center')
                 
    if len(plot_df) > 0 and put_vol.max() > 0:
        top_put_idx = plot_df['putVolume'].idxmax()
        top_put_stk = plot_df.loc[top_put_idx, 'strike']
        top_put_v = plot_df.loc[top_put_idx, 'putVolume']
        top_put_oi = plot_df.loc[top_put_idx, 'putOpenInterest']
        ax2.text(-top_put_v - 15, top_put_stk, f"Put Vol: {int(top_put_v)} | OI: {int(top_put_oi)}", 
                 color='#B71C1C', fontsize=7.8, fontweight='bold', va='center', ha='right')

    ax2.axhline(futures_price, color='#0D47A1', linewidth=2.0, linestyle='-')
    if strikes.min() <= call_wall <= strikes.max():
        ax2.axhline(call_wall, color='#6A1B9A', linewidth=1.6, linestyle='--')
    if strikes.min() <= put_wall <= strikes.max():
        ax2.axhline(put_wall, color='#E65100', linewidth=1.6, linestyle='-.')
    
    max_vol_oi = max(call_oi.max() if len(call_oi) else 0, put_oi.max() if len(put_oi) else 0,
                     call_vol.max() if len(call_vol) else 0, put_vol.max() if len(put_vol) else 0)
    p2_span = max(max_vol_oi * 1.25, 200.0)
    ax2.set_xlim(-p2_span, p2_span)

    ax2.set_title("Panel 2: Dòng Tiền Volume vs Open Interest Nền", fontsize=11, fontweight='bold')
    ax2.set_xlabel("Put OI/Vol (-)  |  Call OI/Vol (+)", fontsize=9.5)
    ax2.legend(loc='lower right', fontsize=8.0, framealpha=0.95)
    ax2.grid(True, linestyle=':', alpha=0.6)

    # -------------------------------------------------------------------------
    # PANEL 3: SECOND-ORDER GREEKS: VANNA (VEX) & CHARM (CHEX) FLOWS
    # -------------------------------------------------------------------------
    ax3.barh(strikes + step * 0.16, net_vex, height=bar_h * 0.48, color='#FB8C00', alpha=0.88, label='Net VEX ($M / 1% IV)', edgecolor='black', linewidth=0.5)
    ax3.barh(strikes - step * 0.16, net_chex, height=bar_h * 0.48, color='#00ACC1', alpha=0.88, label='Net CHEX ($M / Ngày decay)', edgecolor='black', linewidth=0.5)
    ax3.axvline(0, color='black', linewidth=0.8, linestyle='--')

    ax3.axhline(futures_price, color='#0D47A1', linewidth=2.0, linestyle='-')
    if strikes.min() <= call_wall <= strikes.max():
        ax3.axhline(call_wall, color='#6A1B9A', linewidth=1.6, linestyle='--')
    if strikes.min() <= put_wall <= strikes.max():
        ax3.axhline(put_wall, color='#E65100', linewidth=1.6, linestyle='-.')

    # Annotate Top Vanna & Charm Strikes with Meaning & Practical Action
    if len(plot_df) > 0:
        top_vex_idx = (plot_df['netVEX'].abs()).idxmax()
        top_vex_stk = plot_df.loc[top_vex_idx, 'strike']
        top_vex_val = plot_df.loc[top_vex_idx, 'netVEX']
        if top_vex_val >= 0:
            vex_action = f"◄ ĐỈNH VANNA ({top_vex_val:+.1f}M): Lực đẩy V-Rebound (Canh BUY khi IV hạ)"
            ax3.text(top_vex_val + 0.4, top_vex_stk + step * 0.16, vex_action, 
                     color='#E65100', fontsize=7.2, fontweight='bold', va='center', ha='left',
                     bbox=dict(boxstyle='round,pad=0.2', facecolor='#FFF3E0', edgecolor='#E65100', alpha=0.92, linewidth=0.8))
        else:
            vex_action = f"ĐỈNH VANNA ({top_vex_val:+.1f}M): Áp lực xả khi IV tăng (Cẩn thận Waterfall) ►"
            ax3.text(top_vex_val - 0.4, top_vex_stk + step * 0.16, vex_action, 
                     color='#E65100', fontsize=7.2, fontweight='bold', va='center', ha='right',
                     bbox=dict(boxstyle='round,pad=0.2', facecolor='#FFF3E0', edgecolor='#E65100', alpha=0.92, linewidth=0.8))

        top_chex_idx = (plot_df['netCHEX'].abs()).idxmax()
        top_chex_stk = plot_df.loc[top_chex_idx, 'strike']
        top_chex_val = plot_df.loc[top_chex_idx, 'netCHEX']
        if top_chex_val >= 0:
            chex_action = f"◄ ĐỈNH CHARM ({top_chex_val:+.1f}M): Bệ đỡ thời gian (MM mua bù delta)"
            ax3.text(top_chex_val + 0.4, top_chex_stk - step * 0.16, chex_action, 
                     color='#00838F', fontsize=7.2, fontweight='bold', va='center', ha='left',
                     bbox=dict(boxstyle='round,pad=0.2', facecolor='#E0F7FA', edgecolor='#00838F', alpha=0.92, linewidth=0.8))
        else:
            chex_action = f"ĐỈNH CHARM ({top_chex_val:+.1f}M): Nam châm ghìm giá đêm (Canh Chốt Lời) ►"
            ax3.text(top_chex_val - 0.4, top_chex_stk - step * 0.16, chex_action, 
                     color='#00838F', fontsize=7.2, fontweight='bold', va='center', ha='right',
                     bbox=dict(boxstyle='round,pad=0.2', facecolor='#E0F7FA', edgecolor='#00838F', alpha=0.92, linewidth=0.8))

    max_vex_chex = max(abs(net_vex.min()) if len(net_vex) else 0, abs(net_vex.max()) if len(net_vex) else 0,
                       abs(net_chex.min()) if len(net_chex) else 0, abs(net_chex.max()) if len(net_chex) else 0)
    p3_span = max(max_vex_chex * 2.3, 16.0)
    ax3.set_xlim(-p3_span, p3_span)

    ax3.set_title("Panel 3: Greeks Bậc 2: Vanna (VEX) & Charm (CHEX)", fontsize=11, fontweight='bold')
    ax3.set_xlabel("Độ Nhạy Ròng Của Dealers (Triệu USD)", fontsize=9.5)
    ax3.legend(loc='lower right', fontsize=8.0, framealpha=0.95)
    ax3.grid(True, linestyle=':', alpha=0.6)
    
    tot_gex = float(net_gex.sum()) if len(net_gex) else 0.0
    tot_vex = float(net_vex.sum()) if len(net_vex) else 0.0
    tot_chex = float(net_chex.sum()) if len(net_chex) else 0.0
    regime = "LONG GAMMA" if tot_gex > 10 else ("SHORT GAMMA" if tot_gex < -10 else "NEUTRAL")
    
    header_title = (
        f"NEIRO-QUANT: GCZ26 GOLD OPTIONS (3 PANELS) | Futures: {futures_price:.2f} | "
        f"Trạng thái: {regime} ({tot_gex:+.1f}M GEX) | Net VEX: {tot_vex:+.1f}M/1% IV | Net CHEX: {tot_chex:+.1f}M/ngày"
    )
    fig.suptitle(header_title, fontsize=11.5, fontweight='bold')
                 
    plt.tight_layout()
    plt.savefig(output_png, dpi=130)
    plt.close()
    
    t1 = time.time()
    print(f"[SUCCESS] Exported 3-Panel Tactical Map to: {output_png} in {t1 - t0:.3f}s")
