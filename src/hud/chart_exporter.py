import os
import shutil
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches

from process_new_data import load_data_from_new_files

def build_master_3sec_chart():
    df = load_data_from_new_files()
    
    futures_price = 4181.10
    k_atm = 4180.0
    
    # GEX calculations
    MULT = 100
    df['callGEX'] = df['callGamma'] * df['callOpenInterest'] * MULT * (futures_price**2) * 0.01 / 1e6
    df['putGEX']  = - (df['putGamma'] * df['putOpenInterest'] * MULT * (futures_price**2) * 0.01 / 1e6)
    df['netGEX']  = df['callGEX'] + df['putGEX']
    total_net_gex = df['netGEX'].sum()
    
    # Air pockets (< 35% mean OI)
    df['totalOI'] = df['callOpenInterest'] + df['putOpenInterest']
    mean_oi = df['totalOI'].mean()
    air_pockets = df[df['totalOI'] < 0.35 * mean_oi]['strike'].tolist()
    
    call_wall = 4200.0
    put_wall = 4150.0
    cushion = 4175.0
    gamma_flip_floor = 4171.10
    gamma_flip_ceil  = 4201.00
    
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
    # 1.1 Air Pocket Bands (Vùng mỏng thanh khoản)
    for s in air_pockets:
        ax_left.axhspan(s - 2.0, s + 2.0, color='#FF1744', alpha=0.10, zorder=1)
        ax_left.text(0.012, s, "[!] AIR POCKET (VÙNG MỎNG)", color='#FF5252', 
                     fontsize=7.2, fontweight='bold', va='center', ha='left',
                     bbox=dict(boxstyle='round,pad=0.2', facecolor='#1A050A', edgecolor='#FF1744', alpha=0.75, linewidth=0.8),
                     zorder=2)

    # 1.2 Mốc tường chính
    ax_left.axhline(call_wall, color='#D500F9', linestyle='--', linewidth=1.8, alpha=0.85, zorder=3)
    ax_left.axhline(cushion, color='#00E676', linestyle=':', linewidth=1.8, alpha=0.85, zorder=3)
    ax_left.axhline(put_wall, color='#FF9100', linestyle='-.', linewidth=1.8, alpha=0.85, zorder=3)
    
    # Giá Futures & ATM Pivot
    ax_left.axhline(futures_price, color='#00E5FF', linestyle='-', linewidth=2.5, zorder=6)
    ax_left.axhline(k_atm, color='#FFD600', linestyle=':', linewidth=2.0, zorder=5)

    # 1.3 GAMMA FLIP LINES & BADGES (Căn phải ha='right' tại x=0.985 để không bao giờ bị cắt viền)
    # Gamma Flip Floor (4171.10 - Ranh giới Short Gamma -> Hard SL)
    ax_left.axhline(gamma_flip_floor, color='#FF80AB', linestyle='--', linewidth=1.6, alpha=0.9, zorder=6)
    ax_left.text(0.985, gamma_flip_floor - 0.9, f"⚡ GAMMA FLIP ĐÁY: {gamma_flip_floor:.1f} (Ranh giới Short Gamma -> Hard SL = 4171)", 
                 color='#FF80AB', fontsize=8.2, fontweight='bold', va='top', ha='right', zorder=7,
                 bbox=dict(boxstyle='round,pad=0.2', facecolor='#200510', edgecolor='#FF80AB', alpha=0.9, linewidth=1.0))

    # Gamma Flip Ceiling / Squeeze (4201.00)
    ax_left.axhline(gamma_flip_ceil, color='#00E5FF', linestyle='--', linewidth=1.6, alpha=0.9, zorder=6)
    ax_left.text(0.985, gamma_flip_ceil + 1.2, f"⚡ GAMMA FLIP ĐỈNH: {gamma_flip_ceil:.1f} (Vượt 4201 -> Squeeze Mua Đuổi)", 
                 color='#00E5FF', fontsize=8.2, fontweight='bold', va='bottom', ha='right', zorder=7,
                 bbox=dict(boxstyle='round,pad=0.2', facecolor='#001F26', edgecolor='#00E5FF', alpha=0.9, linewidth=1.0))

    # 1.4 Huy hiệu Giá Hiện Tại & ATM Pivot
    ax_left.text(0.985, futures_price, f"< GIÁ FUTURES HIỆN TẠI: {futures_price:.2f}", color='#FFFFFF', 
                 fontsize=11, fontweight='bold', va='center', ha='right',
                 bbox=dict(boxstyle='square,pad=0.35', facecolor='#006064', edgecolor='#00E5FF', linewidth=1.8, alpha=0.98),
                 zorder=8)
                 
    ax_left.text(0.38, k_atm - 1.1, f"[*] ATM PIVOT: {k_atm:.1f} (Trục hút giá TP1)", color='#FFD600', 
                 fontsize=9.2, fontweight='bold', va='center', ha='center',
                 bbox=dict(boxstyle='square,pad=0.25', facecolor='#2B2200', edgecolor='#FFD600', linewidth=1.2, alpha=0.95),
                 zorder=7)

    # 1.5 Waterfall Breakdown Trigger
    ax_left.axhline(4147.5, color='#FF5252', linestyle=':', linewidth=1.3, alpha=0.7, zorder=3)
    ax_left.text(0.985, 4146.5, "▼ WATERFALL BREAKDOWN < 4147.50 (Thủng đáy: Bán tháo về 4135)", 
                 color='#FF5252', fontsize=8.0, fontweight='bold', ha='right', zorder=6)

    # 1.6 CÁC HỘP CHIẾN THUẬT (TACTICAL TRADE BOXES)
    # Box A: SHORT SETUP TẠI 4200 (MAJOR CALL WALL)
    rect_sell = patches.FancyBboxPatch((0.15, 4197.3), 0.48, 5.2, boxstyle="round,pad=0.25",
                                       facecolor='#26040C', edgecolor='#FF1744', linewidth=1.8, alpha=0.95, zorder=7)
    ax_left.add_patch(rect_sell)
    ax_left.text(0.17, 4201.5, "[KẾ HOẠCH BÁN] - MAJOR CALL WALL (4,200.00)", color='#FF5252', fontsize=10.5, fontweight='bold', zorder=8)
    ax_left.text(0.17, 4200.1, "• Kháng cự: 4,971 HĐ OI (+158.1M USD GEX) - Chặn đà tăng cực mạnh", color='#FFCDD2', fontsize=8.8, fontweight='bold', zorder=8)
    ax_left.text(0.17, 4198.8, "• Vùng Bán (Entry): 4198.50 - 4200.00 | Cắt lỗ (Hard SL): 4204.00 (4.0 USD)", color='#FFFFFF', fontsize=9.0, fontweight='bold', zorder=8)
    ax_left.text(0.17, 4197.6, "• Chốt lời: TP1 = 4181.10 (ATM) | TP2 = 4175.00 (Cushion) [Tỷ lệ R:R = 1:4.8]", color='#FFE082', fontsize=8.8, fontweight='bold', zorder=8)

    # Box B: BUY SETUP TẠI 4175 (BULLISH GEX CUSHION)
    rect_buy = patches.FancyBboxPatch((0.15, 4172.3), 0.48, 5.2, boxstyle="round,pad=0.25",
                                      facecolor='#022612', edgecolor='#00E676', linewidth=1.8, alpha=0.95, zorder=7)
    ax_left.add_patch(rect_buy)
    ax_left.text(0.17, 4176.5, "[KẾ HOẠCH MUA] - GEX CUSHION ĐỆM ĐỠ (4,175.00)", color='#00E676', fontsize=10.5, fontweight='bold', zorder=8)
    ax_left.text(0.17, 4175.1, "• Hỗ trợ: Đệm Net GEX lớn nhất (+40.0M USD) | 1,039 Call bảo vệ", color='#C8E6C9', fontsize=8.8, fontweight='bold', zorder=8)
    ax_left.text(0.17, 4173.8, "• Vùng Mua (Entry): 4175.00 - 4176.50 | Cắt lỗ (Hard SL): 4171.00 (4.0 USD)", color='#FFFFFF', fontsize=9.0, fontweight='bold', zorder=8)
    ax_left.text(0.17, 4172.6, "• Chốt lời: TP1 = 4181.10 (ATM) | TP2 = 4200.00 (Call Wall) [Tỷ lệ R:R = 1:6.0]", color='#FFE082', fontsize=8.8, fontweight='bold', zorder=8)

    # Box C: MAJOR PUT WALL DEFENSE TẠI 4150
    rect_put = patches.FancyBboxPatch((0.15, 4148.6), 0.48, 3.6, boxstyle="round,pad=0.25",
                                      facecolor='#2B1700', edgecolor='#FF9100', linewidth=1.5, alpha=0.95, zorder=7)
    ax_left.add_patch(rect_put)
    ax_left.text(0.17, 4151.2, "[HỖ TRỢ ĐÁY] - MAJOR PUT WALL DEFENSE (4,150.00)", color='#FFA726', fontsize=10, fontweight='bold', zorder=8)
    ax_left.text(0.17, 4149.6, "• Chốt chặn đáy: 1,162 HĐ Put (-73.1M USD GEX) - Lực bảo vệ cuối phiên", color='#FFE0B2', fontsize=8.8, fontweight='bold', zorder=8)

    # Thanh Nguyên Tắc Vàng ở đáy
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

    # Level lines across right panel
    ax_right.axhline(futures_price, color='#00E5FF', linestyle='-', linewidth=2.0, alpha=0.85, zorder=4)
    ax_right.axhline(k_atm, color='#FFD600', linestyle=':', linewidth=1.8, alpha=0.85, zorder=4)
    ax_right.axhline(call_wall, color='#D500F9', linestyle='--', linewidth=1.5, alpha=0.7, zorder=3)
    ax_right.axhline(cushion, color='#00E676', linestyle=':', linewidth=1.5, alpha=0.7, zorder=3)
    ax_right.axhline(put_wall, color='#FF9100', linestyle='-.', linewidth=1.5, alpha=0.7, zorder=3)
    ax_right.axhline(gamma_flip_floor, color='#FF80AB', linestyle='--', linewidth=1.4, alpha=0.85, zorder=4)
    ax_right.axhline(gamma_flip_ceil, color='#00E5FF', linestyle='--', linewidth=1.4, alpha=0.85, zorder=4)

    # Stacked Bars: Call GEX (Green, right), Put GEX (Red, left)
    ax_right.barh(strikes, call_gex, height=bar_h, color='#00E676', edgecolor='#B9F6CA', 
                  linewidth=1.2, alpha=0.85, label='Call GEX (+Triệu USD Kháng Cự)', zorder=3)
    ax_right.barh(strikes, put_gex, height=bar_h, color='#FF3D71', edgecolor='#FF80AB', 
                  linewidth=1.2, alpha=0.85, label='Put GEX (-Triệu USD Hỗ Trợ)', zorder=3)
                  
    # Yellow Net GEX Line
    ax_right.plot(net_gex, strikes, color='#FFD600', linewidth=2.5, marker='o', markersize=5.5,
                  label='Đường Net GEX (Gamma Ròng)', zorder=5)

    # Numeric Values on bars
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

    # Zero Axis (Gamma Flip Axis)
    ax_right.axvline(0, color='#94A3B8', linestyle='-', linewidth=1.5, zorder=2)
    ax_right.text(0, 4233.5, "▲ ZERO GAMMA AXIS (0 USD)", color='#94A3B8', fontsize=8.0, fontweight='bold', ha='center', va='bottom')

    ax_right.set_xlim(-220, 220)
    ax_right.set_xlabel("Dollar Gamma Exposure (Triệu USD / 1% Biến Động Giá)", fontsize=11.5, fontweight='bold', color='#81D4FA', labelpad=10)
    ax_right.grid(color='#141D30', linestyle='--', linewidth=0.7, alpha=0.8)
    ax_right.legend(loc='lower right', facecolor='#0F172A', edgecolor='#334155', fontsize=9.2)
    ax_right.set_title("DÒNG TIỀN THANH KHOẢN DOM ORDERFLOW (CALL GEX vs PUT GEX)", 
                       fontsize=13, fontweight='bold', color='#FFFFFF', pad=15)

    # Figure Header & Subtitle
    fig.suptitle("NEIRO-QUANT: BẢNG ĐIỀU KHIỂN ĐỊNH LƯỢNG TỔNG HỢP (GOLD CME GCZ26)", 
                 fontsize=17, fontweight='bold', color='#38BDF8', y=0.985)
    
    status_str = f"Giá Futures: {futures_price:.2f}  |  ATM: {k_atm:.1f}  |  Call Wall: 4,200.0  |  Put Wall: 4,150.0  |  Gamma Flip: 4,171.10 (Đáy) & 4,201.00 (Đỉnh)  |  SL: 4.0 USD"
    fig.text(0.5, 0.952, status_str, fontsize=11, color='#E2E8F0', ha='center', fontweight='bold')

    out_png = r"C:\Users\Daniel\Documents\My-Projects\Neiro-Quant\quant_truevision_map.png"
    plt.tight_layout(rect=[0.015, 0.015, 0.985, 0.945])
    plt.savefig(out_png, dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    
    # Copy to brain artifact
    dst = r"C:\Users\Daniel\.gemini\antigravity-ide\brain\97105131-e759-4948-b783-d74242910c03\quant_truevision_map.png"
    shutil.copyfile(out_png, dst)
    print("Master 3-second chart with Gamma Flip generated successfully!")

if __name__ == '__main__':
    build_master_3sec_chart()
