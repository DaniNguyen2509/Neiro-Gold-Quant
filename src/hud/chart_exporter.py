"""
Neiro-Quant HUD: Master 3-Second All-In-One Chart Exporter (100% CME Gold Futures GCZ26).
Delivers a 2-panel institutional quantitative dashboard:
- Panel 1: Tactical Execution Map (Price, Setups, Walls, Air Pockets, Triggers)
- Panel 2: DOM Liquidity & Orderflow Profile (Call GEX vs Put GEX, Net GEX curve, Contract counts)
"""

import os
import shutil
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def export_quant_chart(
    df: pd.DataFrame,
    futures_price: float = 4181.10,
    k_atm: float = 4180.0,
    call_wall: float = 4200.0,
    put_wall: float = 4150.0,
    cushion: float = 4175.0,
    output_png: str = "quant_truevision_map.png",
    output_html: str = "quant_truevision_map.html"
):
    MULT = 100
    if 'callGEX' not in df.columns:
        df['callGEX'] = df['callGamma'] * df['callOpenInterest'] * MULT * (futures_price**2) * 0.01 / 1e6
        df['putGEX']  = - (df['putGamma'] * df['putOpenInterest'] * MULT * (futures_price**2) * 0.01 / 1e6)
        df['netGEX']  = df['callGEX'] + df['putGEX']
        
    total_net_gex = df['netGEX'].sum()
    
    if 'totalOI' not in df.columns:
        df['totalOI'] = df['callOpenInterest'] + df['putOpenInterest']
    mean_oi = df['totalOI'].mean()
    air_pockets = df[df['totalOI'] < 0.35 * mean_oi]['strike'].tolist()
    
    plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
    plt.rcParams['axes.unicode_minus'] = False
    
    fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(23, 12.5), dpi=200, sharey=True, 
                                            gridspec_kw={'width_ratios': [1.38, 1.0], 'wspace': 0.035})
    fig.patch.set_facecolor('#05070E')
    ax_left.set_facecolor('#090D18')
    ax_right.set_facecolor('#090D18')
    
    strikes = df['strike'].values
    y_min, y_max = 4130, 4235
    
    # -------------------------------------------------------------
    # 1. LEFT PANEL: TACTICAL EXECUTION MAP (3 GIÂY HIỂU NGAY)
    # -------------------------------------------------------------
    for s in air_pockets:
        ax_left.axhspan(s - 2.0, s + 2.0, color='#FF1744', alpha=0.10, zorder=1)
        ax_left.text(0.012, s, "[!] AIR POCKET (VÙNG MỎNG)", color='#FF5252', 
                     fontsize=7.2, fontweight='bold', va='center', ha='left',
                     bbox=dict(boxstyle='round,pad=0.2', facecolor='#1A050A', edgecolor='#FF1744', alpha=0.75, linewidth=0.8),
                     zorder=2)

    ax_left.axhline(call_wall, color='#D500F9', linestyle='--', linewidth=1.8, alpha=0.85, zorder=3)
    ax_left.axhline(cushion, color='#00E676', linestyle=':', linewidth=1.8, alpha=0.85, zorder=3)
    ax_left.axhline(put_wall, color='#FF9100', linestyle='-.', linewidth=1.8, alpha=0.85, zorder=3)
    
    ax_left.axhline(futures_price, color='#00E5FF', linestyle='-', linewidth=2.5, zorder=6)
    ax_left.axhline(k_atm, color='#FFD600', linestyle=':', linewidth=2.0, zorder=5)

    ax_left.text(0.985, futures_price, f"< GIÁ FUTURES HIỆN TẠI: {futures_price:.2f}", color='#FFFFFF', 
                 fontsize=11, fontweight='bold', va='center', ha='right',
                 bbox=dict(boxstyle='square,pad=0.35', facecolor='#006064', edgecolor='#00E5FF', linewidth=1.8, alpha=0.98),
                 zorder=8)
                 
    ax_left.text(0.40, k_atm - 1.1, f"[*] ATM PIVOT: {k_atm:.1f} (Trục hút giá TP1)", color='#FFD600', 
                 fontsize=9.2, fontweight='bold', va='center', ha='center',
                 bbox=dict(boxstyle='square,pad=0.25', facecolor='#2B2200', edgecolor='#FFD600', linewidth=1.2, alpha=0.95),
                 zorder=7)

    ax_left.axhline(4202.5, color='#00B0FF', linestyle=':', linewidth=1.3, alpha=0.7, zorder=3)
    ax_left.text(0.48, 4203.2, "▲ SQUEEZE BREAKOUT > 4202.50 (Nếu nến đóng vượt: Mua đuổi mục tiêu 4220)", 
                 color='#40C4FF', fontsize=8.2, fontweight='bold', zorder=6)

    ax_left.axhline(4147.5, color='#FF5252', linestyle=':', linewidth=1.3, alpha=0.7, zorder=3)
    ax_left.text(0.48, 4146.6, "▼ WATERFALL BREAKDOWN < 4147.50 (Nếu thủng đáy: Bán tháo nhanh về 4135)", 
                 color='#FF5252', fontsize=8.2, fontweight='bold', zorder=6)

    rect_sell = patches.FancyBboxPatch((0.15, 4197.3), 0.50, 5.2, boxstyle="round,pad=0.25",
                                       facecolor='#26040C', edgecolor='#FF1744', linewidth=1.8, alpha=0.95, zorder=7)
    ax_left.add_patch(rect_sell)
    ax_left.text(0.17, 4201.5, "[KẾ HOẠCH BÁN] - MAJOR CALL WALL (4,200.00)", color='#FF5252', fontsize=10.5, fontweight='bold', zorder=8)
    ax_left.text(0.17, 4200.1, "• Kháng cự: 4,971 HĐ OI (+158.1M USD GEX) - Chặn đà tăng cực mạnh", color='#FFCDD2', fontsize=8.8, fontweight='bold', zorder=8)
    ax_left.text(0.17, 4198.8, "• Vùng Bán (Entry): 4198.50 - 4200.00 | Cắt lỗ (Hard SL): 4204.00 (4.0 USD)", color='#FFFFFF', fontsize=9.0, fontweight='bold', zorder=8)
    ax_left.text(0.17, 4197.6, "• Chốt lời: TP1 = 4181.10 (ATM) | TP2 = 4175.00 (Cushion) [Tỷ lệ R:R = 1:4.8]", color='#FFE082', fontsize=8.8, fontweight='bold', zorder=8)

    rect_buy = patches.FancyBboxPatch((0.15, 4172.3), 0.50, 5.2, boxstyle="round,pad=0.25",
                                      facecolor='#022612', edgecolor='#00E676', linewidth=1.8, alpha=0.95, zorder=7)
    ax_left.add_patch(rect_buy)
    ax_left.text(0.17, 4176.5, "[KẾ HOẠCH MUA] - GEX CUSHION ĐỆM ĐỠ (4,175.00)", color='#00E676', fontsize=10.5, fontweight='bold', zorder=8)
    ax_left.text(0.17, 4175.1, "• Hỗ trợ: Đệm Net GEX lớn nhất (+40.0M USD) | 1,039 Call bảo vệ", color='#C8E6C9', fontsize=8.8, fontweight='bold', zorder=8)
    ax_left.text(0.17, 4173.8, "• Vùng Mua (Entry): 4175.00 - 4176.50 | Cắt lỗ (Hard SL): 4171.00 (4.0 USD)", color='#FFFFFF', fontsize=9.0, fontweight='bold', zorder=8)
    ax_left.text(0.17, 4172.6, "• Chốt lời: TP1 = 4181.10 (ATM) | TP2 = 4200.00 (Call Wall) [Tỷ lệ R:R = 1:6.0]", color='#FFE082', fontsize=8.8, fontweight='bold', zorder=8)

    rect_put = patches.FancyBboxPatch((0.15, 4148.6), 0.50, 3.6, boxstyle="round,pad=0.25",
                                      facecolor='#2B1700', edgecolor='#FF9100', linewidth=1.5, alpha=0.95, zorder=7)
    ax_left.add_patch(rect_put)
    ax_left.text(0.17, 4151.2, "[HỖ TRỢ ĐÁY] - MAJOR PUT WALL DEFENSE (4,150.00)", color='#FFA726', fontsize=10, fontweight='bold', zorder=8)
    ax_left.text(0.17, 4149.6, "• Chốt chặn đáy: 1,162 HĐ Put (-73.1M USD GEX) - Lực bảo vệ cuối phiên", color='#FFE0B2', fontsize=8.8, fontweight='bold', zorder=8)

    rect_rules = patches.FancyBboxPatch((0.012, 4131.0), 0.976, 3.0, boxstyle="square,pad=0.2",
                                        facecolor='#0E1726', edgecolor='#38BDF8', linewidth=1.0, alpha=0.9, zorder=7)
    ax_left.add_patch(rect_rules)
    ax_left.text(0.5, 4132.5, "QUY TẮC SỐNG CÒN: 1. Tuân thủ Hard SL = 4.0 USD tuyệt đối | 2. Chốt 50% tại TP1 (4181.10) dời BE | 3. Không Mua đuổi khi giá chạm 4200",
                 color='#E0F2FE', fontsize=9.2, fontweight='bold', ha='center', va='center', zorder=8)

    ax_left.set_xlim(0, 1)
    ax_left.set_xticks([])
    ax_left.set_ylim(y_min, y_max)
    ax_left.set_yticks(strikes)
    ax_left.set_yticklabels([f"${s:4.0f}" for s in strikes], fontsize=11, fontweight='bold', color='#ECEFF1')
    ax_left.set_ylabel("CME Gold Futures Strike Price ($)", fontsize=13, fontweight='bold', color='#81D4FA', labelpad=12)
    ax_left.grid(color='#141D30', linestyle='--', linewidth=0.7, alpha=0.8)
    ax_left.set_title("BẢN ĐỒ MỐC GIÁ VÀ ĐIỂM CHỜ VÀO LỆNH (TACTICAL EXECUTION MAP)", 
                      fontsize=13, fontweight='bold', color='#FFFFFF', pad=15)

    # -------------------------------------------------------------
    # 2. RIGHT PANEL: DOM ORDERFLOW & GEX PROFILE
    # -------------------------------------------------------------
    call_gex = df['callGEX'].values
    put_gex = df['putGEX'].values
    net_gex = df['netGEX'].values
    bar_h = 3.2
    
    for s in air_pockets:
        ax_right.axhspan(s - 2.0, s + 2.0, color='#FF1744', alpha=0.08, zorder=1)

    ax_right.axhline(futures_price, color='#00E5FF', linestyle='-', linewidth=2.0, alpha=0.85, zorder=4)
    ax_right.axhline(k_atm, color='#FFD600', linestyle=':', linewidth=1.8, alpha=0.85, zorder=4)
    ax_right.axhline(call_wall, color='#D500F9', linestyle='--', linewidth=1.5, alpha=0.7, zorder=3)
    ax_right.axhline(cushion, color='#00E676', linestyle=':', linewidth=1.5, alpha=0.7, zorder=3)
    ax_right.axhline(put_wall, color='#FF9100', linestyle='-.', linewidth=1.5, alpha=0.7, zorder=3)

    ax_right.barh(strikes, call_gex, height=bar_h, color='#00E676', edgecolor='#B9F6CA', 
                  linewidth=1.2, alpha=0.85, label='Call GEX (+Triệu USD Kháng Cự)', zorder=3)
    ax_right.barh(strikes, put_gex, height=bar_h, color='#FF3D71', edgecolor='#FF80AB', 
                  linewidth=1.2, alpha=0.85, label='Put GEX (-Triệu USD Hỗ Trợ)', zorder=3)
                  
    ax_right.plot(net_gex, strikes, color='#FFD600', linewidth=2.5, marker='o', markersize=5.5,
                  label='Đường Net GEX (Gamma Ròng)', zorder=5)

    for s, c_oi, p_oi, c_g, p_g, n_g in zip(strikes, df['callOpenInterest'], df['putOpenInterest'], call_gex, put_gex, net_gex):
        if c_oi > 0:
            if c_g > 90:
                ax_right.text(c_g - 4.0, s, f"{c_oi:.0f}C (+{c_g:.1f}M)", color='#003314', fontsize=8.5, fontweight='bold', va='center', ha='right', zorder=6)
            else:
                ax_right.text(c_g + 3.0, s, f"{c_oi:.0f}C (+{c_g:.1f}M)", color='#A7F3D0', fontsize=8.2, fontweight='bold', va='center', ha='left', zorder=6)
                
        if p_oi > 0:
            if abs(p_g) > 90:
                ax_right.text(p_g + 4.0, s, f"(-{abs(p_g):.1f}M) {p_oi:.0f}P", color='#FFFFFF', fontsize=8.5, fontweight='bold', va='center', ha='left', zorder=6)
            else:
                ax_right.text(p_g - 3.0, s, f"(-{abs(p_g):.1f}M) {p_oi:.0f}P", color='#FECDD3', fontsize=8.2, fontweight='bold', va='center', ha='right', zorder=6)

    ax_right.axvline(0, color='#94A3B8', linestyle='-', linewidth=1.5, zorder=2)
    ax_right.set_xlim(-220, 220)
    ax_right.set_xlabel("Dollar Gamma Exposure (Triệu USD / 1% Biến Động Giá)", fontsize=11.5, fontweight='bold', color='#81D4FA', labelpad=10)
    ax_right.grid(color='#141D30', linestyle='--', linewidth=0.7, alpha=0.8)
    ax_right.legend(loc='lower right', facecolor='#0F172A', edgecolor='#334155', fontsize=9.2)
    ax_right.set_title("DÒNG TIỀN THANH KHOẢN DOM ORDERFLOW (CALL GEX vs PUT GEX)", 
                       fontsize=13, fontweight='bold', color='#FFFFFF', pad=15)

    fig.suptitle("NEIRO-QUANT: BẢNG ĐIỀU KHIỂN ĐỊNH LƯỢNG TỔNG HỢP (GOLD CME GCZ26)", 
                 fontsize=17, fontweight='bold', color='#38BDF8', y=0.985)
    
    status_str = f"Giá Futures: {futures_price:.2f}   |   ATM Pivot: {k_atm:.1f}   |   Tổng Net GEX: {total_net_gex:+.1f}M USD (Short Gamma = Biên độ lớn)   |   Quy tắc SL: Cắt lỗ cứng 4.0 USD"
    fig.text(0.5, 0.952, status_str, fontsize=11.5, color='#E2E8F0', ha='center', fontweight='bold')

    plt.tight_layout(rect=[0.015, 0.015, 0.985, 0.945])
    plt.savefig(output_png, dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"[SUCCESS] Exported Master 3-Second Chart to: {output_png}")
