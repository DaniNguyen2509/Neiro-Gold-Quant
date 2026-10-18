"""
Neiro-Quant HUD: True-Vision Net GEX & Air Pocket Chart Exporter (100% CME Gold Futures).
Outputs:
1. quant_truevision_map.png (High-Resolution 200 DPI PNG, horizontal Net GEX & Air Pockets layout)
2. quant_truevision_map.html (Interactive Plotly Web Visualization)
"""

import os
import shutil
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import plotly.graph_objects as go

def export_quant_chart(
    df: pd.DataFrame,
    futures_price: float = 4181.10,
    k_atm: float = 4180.0,
    call_wall: float = 4200.0,
    put_wall: float = 4150.0,
    total_net_gex: float = -53.74,
    expected_move: float = 219.10,
    sigma_1_lower: float = 3906.50,
    sigma_1_upper: float = 4455.70,
    air_pocket_strikes: list = None,
    output_dir: str = "."
):
    if air_pocket_strikes is None:
        mean_oi = (df['callOpenInterest'] + df['putOpenInterest']).mean()
        air_pocket_strikes = df[df['callOpenInterest'] + df['putOpenInterest'] < 0.35 * mean_oi]['strike'].tolist()
        
    os.makedirs(output_dir, exist_ok=True)
    png_path = os.path.join(output_dir, "quant_truevision_map.png")
    html_path = os.path.join(output_dir, "quant_truevision_map.html")
    
    # -------------------------------------------------------------
    # 1. High-Resolution PNG Generator (CME Gold Futures Grid)
    # -------------------------------------------------------------
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(20, 11.5), dpi=200)
    fig.patch.set_facecolor('#0B0F19')
    ax.set_facecolor('#0E1424')
    
    strikes = df['strike'].values
    net_gex = df['netGEX'].values
    bar_height = 3.2
    
    # Air pocket bands
    for s in air_pocket_strikes:
        ax.axhspan(s - 2.2, s + 2.2, color='#FF1744', alpha=0.15, zorder=1)
        ax.text(-175, s, "[!] AIR POCKET (VUNG MONG)", color='#FF5252', fontsize=8.0, 
                fontweight='bold', va='center', ha='left',
                bbox=dict(boxstyle='round,pad=0.2', facecolor='#1F1018', edgecolor='#FF1744', alpha=0.85))

    # Horizontal bars
    colors = ['#00E676' if g >= 0 else '#FF3D71' for g in net_gex]
    edgecolors = ['#B9F6CA' if g >= 0 else '#FF80AB' for g in net_gex]
    ax.barh(strikes, net_gex, height=bar_height, color=colors, edgecolor=edgecolors, 
            linewidth=1.2, alpha=0.90, zorder=3)
    
    # Value labels with anti-collision vertical positioning
    for s, g, oi_c, oi_p in zip(strikes, net_gex, df['callOpenInterest'], df['putOpenInterest']):
        val_str = f" {g:+.1f}M (C:{oi_c:.0f}|P:{oi_p:.0f})"
        y_pos = s
        if abs(s - 4180.0) < 0.1 or abs(s - 4150.0) < 0.1 or abs(s - 4200.0) < 0.1:
            y_pos = s - 1.2
        elif abs(s - 4175.0) < 0.1:
            y_pos = s + 1.2
            
        if g >= 0:
            ax.text(g + 1.5, y_pos, val_str, color='#00E676', va='center', ha='left', fontsize=8.5, fontweight='bold', zorder=4)
        else:
            ax.text(g - 1.5, y_pos, val_str, color='#FF3D71', va='center', ha='right', fontsize=8.5, fontweight='bold', zorder=4)

    # Key Price Lines (100% CME Gold Futures)
    # Futures Price
    ax.axhline(futures_price, color='#00E5FF', linestyle='--', linewidth=2.5, zorder=5)
    ax.text(45, futures_price + 1.1, f"<< CME FUTURES: {futures_price:.2f}", color='#00E5FF', fontsize=10.5, fontweight='bold',
            bbox=dict(boxstyle='square,pad=0.3', facecolor='#002B36', edgecolor='#00E5FF', alpha=0.95), zorder=6)
    
    # ATM Pivot
    ax.axhline(k_atm, color='#FFD600', linestyle=':', linewidth=2.0, zorder=5)
    ax.text(125, k_atm - 1.1, f"<< ATM PIVOT: {k_atm:.1f} (TP1 Magnet)", color='#FFD600', fontsize=10, fontweight='bold',
            bbox=dict(boxstyle='square,pad=0.25', facecolor='#2B2600', edgecolor='#FFD600', alpha=0.95), zorder=6)
    
    # Call Wall
    ax.axhline(call_wall, color='#D500F9', linestyle='-.', linewidth=2.0, zorder=5)
    ax.text(45, call_wall + 1.2, f"<< MAJOR DUAL WALL (PIN): {call_wall:.1f} (2,444 C / 2,527 P)", color='#D500F9', fontsize=10, fontweight='bold',
            bbox=dict(boxstyle='square,pad=0.25', facecolor='#26002B', edgecolor='#D500F9', alpha=0.95), zorder=6)
            
    # Put Wall Defense
    ax.axhline(put_wall, color='#FF9100', linestyle='-.', linewidth=2.0, zorder=5)
    ax.text(45, put_wall + 1.2, f"<< PUT WALL DEFENSE: {put_wall:.1f} (1,162 Puts | -44.1M GEX)", color='#FF9100', fontsize=10, fontweight='bold',
            bbox=dict(boxstyle='square,pad=0.25', facecolor='#331A00', edgecolor='#FF9100', alpha=0.95), zorder=6)

    # Bullish GEX Cushion
    ax.axhline(4175.0, color='#00E676', linestyle=':', linewidth=1.5, zorder=4)
    ax.text(-105, 4175.0 + 1.2, "BULLISH GEX CUSHION: 4175.0 (+40.0M Net GEX)", color='#00E676', fontsize=8.5, fontweight='bold', va='center', ha='center',
            bbox=dict(boxstyle='round,pad=0.2', facecolor='#002B15', edgecolor='#00E676', alpha=0.85))

    # Trigger levels
    ax.axhline(4202.5, color='#00B0FF', linestyle=':', linewidth=1.2, alpha=0.7)
    ax.text(-100, 4202.5 + 1.0, "▲ SQUEEZE TRIGGER > 4202.50", color='#00B0FF', fontsize=8.5, fontweight='bold', va='center', ha='center')

    ax.axhline(4147.5, color='#FF5252', linestyle=':', linewidth=1.2, alpha=0.7)
    ax.text(-100, 4147.5 - 1.0, "▼ WATERFALL TRIGGER < 4147.50", color='#FF5252', fontsize=8.5, fontweight='bold', va='center', ha='center')

    # Axis Formatting
    ax.set_yticks(strikes)
    ax.set_yticklabels([f"{s:4.0f}" for s in strikes], fontsize=10, fontweight='bold', color='#CFD8DC')
    ax.set_ylabel("CME Gold Futures Strike Price (GCZ26 Grid)", fontsize=12, fontweight='bold', color='#90CAF9', labelpad=12)
    ax.set_xlabel("Net GEX Exposure ($ Millions per 1% Move)", fontsize=12, fontweight='bold', color='#90CAF9', labelpad=10)
    ax.set_xlim(-185, 235)
    ax.set_ylim(4130, 4235)
    ax.axvline(0, color='#546E7A', linestyle='-', linewidth=1.5, zorder=2)
    ax.grid(color='#1E293B', linestyle='--', linewidth=0.7, alpha=0.6, zorder=1)
    
    plt.title("NEIRO QUANT: CME GOLD FUTURES NET GEX & AIR POCKET PROFILE", 
              fontsize=16, fontweight='bold', color='#FFFFFF', pad=25, loc='left')
    fig.text(0.125, 0.915, f"Data Source: data/options_prices.csv + data/volatility-greeks.csv | Expiry: Weekly GCZ26 | Futures: {futures_price:.2f}",
             fontsize=10, color='#78909C')

    # HUD Card 1
    hud1_text = (
        "[QUANT FUTURES METRICS]\n"
        "-------------------------------\n"
        f"* Futures Price:   {futures_price:.2f}\n"
        f"* ATM Pivot:       {k_atm:.1f}\n"
        f"* Net GEX Regime:  SHORT ({total_net_gex:+.1f}M$)\n"
        f"* Major Dual Wall: {call_wall:.1f}\n"
        f"* Put Defense:     {put_wall:.1f}\n"
        f"* 1-Sigma Band:    [{sigma_1_lower:.1f} - {sigma_1_upper:.1f}]\n"
        f"* Expected Move:   +/- {expected_move:.2f} $\n"
        f"* Air Pockets:     {len(air_pocket_strikes)} Zones detected"
    )
    fig.text(0.75, 0.73, hud1_text, fontsize=9.5, fontfamily='monospace', color='#ECEFF1',
             bbox=dict(boxstyle='round,pad=0.8', facecolor='#111827', edgecolor='#38BDF8', linewidth=1.5, alpha=0.92))

    # HUD Card 2
    hud2_text = (
        "[FUTURES SETUPS] (SL = $4.0)\n"
        "-------------------------------\n"
        "[BUY] SETUP 1: CUSHION REBOUND\n"
        "* Futures Entry: 4175.00 - 4176.50\n"
        "* Futures SL:    4171.00 (Hard 4.0$)\n"
        "* Futures TP1:   4181.10 (ATM Pivot)\n"
        "* Futures TP2:   4200.00 (Dual Wall Pin)\n"
        "* R:R:           1 : 6.00\n"
        "-------------------------------\n"
        "[SELL] SETUP 2: DUAL WALL FADE\n"
        "* Futures Entry: 4198.50 - 4200.00\n"
        "* Futures SL:    4204.00 (Hard 4.0$)\n"
        "* Futures TP1:   4181.10 (ATM Pivot)\n"
        "* Futures TP2:   4175.00 (Support Cushion)\n"
        "* R:R:           1 : 4.75"
    )
    fig.text(0.75, 0.40, hud2_text, fontsize=9.5, fontfamily='monospace', color='#ECEFF1',
             bbox=dict(boxstyle='round,pad=0.8', facecolor='#111827', edgecolor='#F59E0B', linewidth=1.5, alpha=0.92))

    plt.tight_layout(rect=[0.02, 0.02, 0.74, 0.92])
    plt.savefig(png_path, dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    
    # -------------------------------------------------------------
    # 2. Interactive Plotly HTML Generator
    # -------------------------------------------------------------
    fig_pl = go.Figure()
    
    for s in air_pocket_strikes:
        fig_pl.add_hrect(
            y0=s - 2.2, y1=s + 2.2,
            fillcolor="red", opacity=0.15,
            line_width=0,
            annotation_text="⚠ AIR POCKET",
            annotation_position="top left",
            annotation_font=dict(color="#FF5252", size=10)
        )
        
    fig_pl.add_trace(go.Bar(
        y=strikes,
        x=net_gex,
        orientation='h',
        marker=dict(
            color=['#00E676' if g >= 0 else '#FF3D71' for g in net_gex],
            line=dict(color=['#B9F6CA' if g >= 0 else '#FF80AB' for g in net_gex], width=1)
        ),
        text=[f"{g:+.1f}M $" for g in net_gex],
        textposition="outside",
        name="Net GEX"
    ))
    
    fig_pl.add_hline(y=futures_price, line_dash="dash", line_color="#00E5FF", line_width=2.5,
                     annotation_text=f"Futures: {futures_price:.2f}", annotation_font_color="#00E5FF")
    fig_pl.add_hline(y=k_atm, line_dash="dot", line_color="#FFD600", line_width=2,
                     annotation_text=f"ATM Pivot: {k_atm:.1f}", annotation_font_color="#FFD600")
    fig_pl.add_hline(y=call_wall, line_dash="dashdot", line_color="#D500F9", line_width=2,
                     annotation_text=f"Dual Wall: {call_wall:.1f}", annotation_font_color="#D500F9")
    fig_pl.add_hline(y=put_wall, line_dash="dashdot", line_color="#FF9100", line_width=2,
                     annotation_text=f"Put Wall: {put_wall:.1f}", annotation_font_color="#FF9100")
    fig_pl.add_hline(y=4175.0, line_dash="dot", line_color="#00E676", line_width=1.5,
                     annotation_text="GEX Cushion: 4175.0", annotation_font_color="#00E676")

    fig_pl.update_layout(
        title=f"<b>NEIRO QUANT: CME GOLD FUTURES NET GEX PROFILE</b> (Futures: {futures_price:.2f})",
        template="plotly_dark",
        paper_bgcolor="#0B0F19",
        plot_bgcolor="#0E1424",
        xaxis=dict(title="Net GEX Exposure ($ Millions)", zeroline=True, zerolinecolor="#546E7A"),
        yaxis=dict(title="CME Gold Futures Strike Price", tickmode='linear', dtick=5),
        height=850,
        showlegend=False
    )
    fig_pl.write_html(html_path)
    
    return png_path, html_path
