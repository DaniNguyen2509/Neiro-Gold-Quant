# Neiro-Gold-Quant — TÀI LIỆU KIẾN TRÚC HỆ THỐNG ĐỊNH LƯỢNG (QUANT ARCHITECTURE)

> **Phiên bản:** v3.0 — Kiến trúc Terminal Tác chiến Đa Chế Độ Dual-View (NEIRO Footprint & 3-Panel Quant Ladder)  
> **Dự án:** Neiro-Gold-Quant (Hệ thống Định lượng Vi mô Dòng tiền Market Maker & Terminal Tác chiến cho COMEX Gold Futures `GC` / `MGC` & Spot `XAUUSD`)  
> **Vận hành:** Cloud-Native Zero-Touch Automation (GitHub Actions + GitHub Pages, thuần Python, Zero-Waste < 15MB)  
> **Tài liệu chuẩn đối chiếu:** [docs/spec.md](spec.md), [config/settings.toml](../config/settings.toml), [docs/TRADER_PLAYBOOK.md](TRADER_PLAYBOOK.md).

---

## I. MỤC TIÊU CỐT LÕI & TRIẾT LÝ VẬN HÀNH (FIRST PRINCIPLES)

Thị trường Vàng quốc tế (COMEX Gold Futures & London OTC Spot) được chi phối bởi các Ngân hàng Vàng (Bullion Banks - HSBC, JPMorgan, UBS...), các Nhà tạo lập thị trường Quyền chọn (Options Market Makers - MMs / Dealers) và các quỹ vĩ mô (Macro Hedge Funds).  
Hệ thống **Neiro-Gold-Quant** giải quyết các bài toán định lượng cấu trúc vi mô độc nhất của thị trường Vàng:

1. **Định vị chính xác các chốt chặn dòng tiền thực tế:**
   - **Call Wall & Put Wall:** Các bức tường thành trì Open Interest lớn nhất của Dealer.
   - **Đặc thù Call Skew của Vàng:** Khác với chứng khoán (thường bị Put Skew do mua phòng hộ sập sàn), thị trường Vàng chịu chi phối bởi **Call Skew** mạnh mẽ (nhu cầu mua Call OTM phòng hộ lạm phát, khủng hoảng tiền tệ và rủi ro địa chính trị). Do đó, phía trần kháng cự luôn tiềm ẩn các đợt bùng nổ **Gamma Squeeze** cực mạnh khi giá vượt qua:
     $$Trigger_{Up} = CallWall + Call_{mid}(CallWall)$$
   - **Quy tắc khóa OTM Dealer Walls:** Call Wall bắt buộc là OTM Call ($strike \ge spot$), Put Wall bắt buộc là OTM Put ($strike \le spot$), loại bỏ hoàn toàn việc nhận nhầm Strike ITM.
   - **Gamma-Weighted Wall Scoring:** Phân hạng thành trì bằng $Power = OI \times \Gamma(S)$, phân loại rõ ràng giữa `[BOUNCE_WALL]` (Dealer Long Gamma pin/hỗ trợ phản xạ) và `[MAGNET_WALL]` (Dealer Short Gamma bẫy gia tốc xuyên thủng).
2. **Mô hình Định giá Cost of Carry & Cơ Chế EFP (Exchange for Physical):**
   - Giá tương lai lý thuyết của Vàng không có cổ tức mà chịu chi phí lưu kho, kiểm định, bảo hiểm vật chất tại kho COMEX ($u \approx 0.2\%$/năm) và bù trừ bởi lợi suất cho thuê vàng liên ngân hàng (Gold Lease Rate $y \approx 1.5\%$/năm):
     $$F_{0, \text{lý thuyết}} = S_0 \times e^{(r + u - y)T}$$
   - **Độ lệch Basis:** $\text{Basis} = F_{0, \text{thực tế}} - S_{0, \text{Spot}}$ phản ánh cơ chế EFP:
     - Khi $F_{0, \text{thực tế}} \gg F_{0, \text{lý thuyết}}$: Lực mua áp đảo trên sàn COMEX New York kích hoạt nghiệp vụ EFP: Bullion Banks bán khống GC Futures và mua gom vàng giao ngay London (XAUUSD), kéo giá Spot tăng đuổi theo.
     - Khi $F_{0, \text{thực tế}} \ll F_{0, \text{lý thuyết}}$: Áp lực bán phòng hộ của các mỏ khai thác vàng kéo giá Spot suy yếu.
3. **Bất biến Zero Gamma Flip ($S^*$) & Tỷ lệ Công thành (Wall Siege Ratio):**
   - Mốc đảo pha $S^*$ được giải liên tục bằng phương trình $\sum_k \text{NetGEX}_k(S^*) = 0$ thông qua thuật toán Dekker-Brent (`_brentq` thuần Python, không dùng xấp xỉ strike thô để tránh sai lệch Jensen).
   - Áp lực tấn công thành trì trong ngày được đo lường bằng tỷ lệ tốc độ dòng tiền:
     $$\text{Wall Siege Ratio} = \frac{\text{Volume}}{\max(\text{Baseline OI}, 1)}$$
     Khi $\text{Siege Ratio} \ge 0.25$, hệ thống phát cảnh báo nguy cơ vỡ trận phòng thủ.
4. **Terminal Tác chiến Đa Chế Độ Dual-View (Single-Page HUD):**
   - **Tab 1: NEIRO ORDERFLOW FOOTPRINT:** Canvas HTML5 60 FPS mô phỏng sổ lệnh thang giá dọc, Bid/Ask Footprint Delta, Micro-candles Brownian-bridge / Globex 1m-5m, Multiplier = 100.0 cho GC ($10.0 cho MGC), Tick-by-Tick tape.
   - **Tab 2: 3-PANEL QUANT LADDER & PLAYBOOK:** Plotly Dark HUD tương tác cao (Net GEX Profile, OI Concentration, Vanna/Charm Flow, Intraday Scalping Strategy, Structural Swing Walls, Strike Microstructure Matrix, Anti-collision layout).
5. **Vận hành Tự động Đám mây (Zero-Touch Cloud-Native Automation):**
   - Chạy 100% không người lái trên GitHub Actions theo Lưới Cron Đa Tầng Pre-Session Radar, xuất bản trực tiếp lên GitHub Pages. Không cần cài đặt phần mềm nặng, không phụ thuộc laptop, repo < 15MB.

---

## II. SƠ ĐỒ TOÀN CẢNH KIẾN TRÚC HỆ THỐNG (6 TẦNG ĐỘC LẬP)

```
                    ┌──────────────────────────────────────────────────┐
                    │      CME COMEX / BARCHART / YFINANCE FEEDS       │
                    │   (GC Futures, OG Options, GLD Proxy, GVZ Index) │
                    └────────────────────────┬─────────────────────────┘
                                             │ Playwright Headless + yfinance API
                                             ▼
┌────────────────────────────────────────────────────────────────────────────────────────────┐
│ [TẦNG 1: CLOUD COLLECTOR & MULTI-SOURCE INGESTION]                                         │
│  - Playwright Headless Chromium: Sniff API JSON Barchart (/quotes/get & /options/get).      │
│  - Dynamic CME Rollover Engine: Tự động phân giải mã 5 tháng chẵn G, J, M, Q, Z.           │
│  - Gold Collector (yfinance): Quét ETF GLD Proxy và tỷ lệ Basis Ratio = GC / GLD ≈ 10.8.   │
│  - Lưới Cron Đa Tầng Pre-Session Radar: 07:15 VN (CME OI), London 2 nấc, US & COMEX Pit.   │
│  - Dataset Caching: data/options_prices_GCZ26.csv (tự động dọn rác, duy trì < 15MB).       │
└────────────────────────────────────────────┬───────────────────────────────────────────────┘
                                             │
                                             ▼
┌────────────────────────────────────────────────────────────────────────────────────────────┐
│ [TẦNG 2: QUANT ENGINE & BLACK-76 GREEKS CORE]                                              │
│  - black76.py: Mô hình Black-76 cho Options on Futures (Delta, Gamma, Vega, Theta).         │
│  - advanced_greeks.py: Vanna ($M / 1% IV) & Charm ($M / ngày) giải tích chuẩn xác.        │
│  - iv_solver.py: Bộ giải ngược IV lai (Newton-Raphson + Dekker-Brent bisection).           │
│  - synthetic.py: Put-Call Parity Implied Spot & Expected Move Bands (1.0σ & 0.85σ).         │
│  - dealer.py: Zero Gamma Solver (_brentq), Wall Siege Ratio, Gamma-Weighted Wall Scoring.   │
│  - air_pocket.py: Quét vùng chân không thanh khoản (OI < 35% Moving Average).              │
│  - institutional.py: 25Δ Risk Reversal (RR25), Butterfly (BF25), Vol-Target Sizing, CTA.  │
│  - Cost of Carry: F0 = S0 * exp((r + u - y) * T) với u = 0.2%, y = 1.5%.                   │
└────────────────────────────────────────────┬───────────────────────────────────────────────┘
                                             │
                                             ▼
┌────────────────────────────────────────────────────────────────────────────────────────────┐
│ [TẦNG 3: TERMINAL TÁC CHIẾN ĐA CHẾ ĐỘ DUAL-VIEW (FRONTEND HUD)]                            │
│  ┌──────────────────────────────────────────────┬────────────────────────────────────────┐ │
│  │ TAB 1: NEIRO ORDERFLOW FOOTPRINT             │ TAB 2: 3-PANEL QUANT LADDER & PLAYBOOK │ │
│  ├──────────────────────────────────────────────┼────────────────────────────────────────┤ │
│  │ - HTML5 Canvas 60 FPS Orderflow Layer        │ - Panel 1: Net GEX Profile & Walls     │ │
│  │ - Thang giá dọc DOM / Bid-Ask Ladder         │ - Panel 2: OI Concentration & Delta    │ │
│  │ - Footprint Delta Bar Cluster                │ - Panel 3: Vanna & Charm Flow          │ │
│  │ - Micro-candles 1m/5m Brownian Bridge        │ - Ma trận 6 Kịch bản Realtime          │ │
│  │ - Greeks Overlay Profile per Strike          │ - Bảng Scalping & Swing Playbook       │ │
│  │ - Tick-by-Tick Simulated Tape                │ - Strike Microstructure Matrix         │ │
│  │ - Multiplier = 100.0 (GC) / 10.0 (MGC)       │ - Thuật toán Chống Đè Chữ              │ │
│  └──────────────────────────────────────────────┴────────────────────────────────────────┘ │
│  - Header KPI Bar: Spot CME, Net GEX Regime, Net Delta Tilt, Zero Gamma Flip, Expected Move│
│  - Client-Side Black-76 Engine (Pure JS): Tái tính toán Greeks theo từng tick giá.         │
│  - Xuất bản tự động lên GitHub Pages (https://daninguyen2509.github.io/Neiro-Gold-Quant/).      │
└────────────────────────────────────────────┬───────────────────────────────────────────────┘
                                             │
                                             ▼
┌────────────────────────────────────────────────────────────────────────────────────────────┐
│ [TẦNG 4: MICROSTRUCTURE & LEVEL STATE ENGINE]                                              │
│  - Máy trạng thái hữu hạn cho từng Strike/Level:                                           │
│      * DORMANT: Giá cách xa > 5.0 pts.                                                     │
│      * TESTING: Giá tiếp cận trong phạm vi <= 2.0 pts.                                     │
│      * ABSORPTION_DEFENDED: Long Gamma + Hấp thụ volume -> FADE REVERSAL.                  │
│      * SLICED_VACUUM_RUN: Short Gamma + Air Pocket -> BREAKOUT RUNNER (CẤM ĐỠ DAO).        │
└────────────────────────────────────────────┬───────────────────────────────────────────────┘
                                             │
                                             ▼
┌────────────────────────────────────────────────────────────────────────────────────────────┐
│ [TẦNG 5: TACTICAL PLAYBOOK & RISK MATRICES]                                                │
│  - Intraday Scalping Strategy (biên độ 15-25 USD): Entry, Hard SL, TP, Lots.              │
│  - Structural Swing Strategy (biên độ 50-120 USD): Vị thế theo Major Walls.                │
│  - CTA 20-Day Momentum Confluence: Hợp lưu bứt phá đà tăng/giảm giữa Quỹ và Dealer.       │
└────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## III. MÔ HÌNH TOÁN HỌC & CÔNG THỨC ĐỊNH LƯỢNG

### 1. Cost of Carry & Chênh lệch EFP cho Vàng
$$F_{0, \text{lý thuyết}} = S_0 \times e^{(r + u - y)T}$$
Trong đó:
- $S_0$: Giá vàng giao ngay London OTC ($XAUUSD$).
- $r$: Lãi suất phi rủi ro USD ($SOFR \approx 4.5\%$).
- $u$: Chi phí lưu kho và bảo hiểm vật chất kho COMEX ($u \approx 0.2\%$).
- $y$: Gold Lease Rate giữa các ngân hàng thanh toán bù trừ vàng ($y \approx 1.5\%$).
- $T$: Thời gian đáo hạn tính theo năm ($T = \text{DTE} / 365$).

### 2. Mô hình Black-76 cho Options on Futures
$$d_1 = \frac{\ln(F/K) + \frac{1}{2}\sigma^2 T}{\sigma \sqrt{T}}, \quad d_2 = d_1 - \sigma \sqrt{T}$$
- **Giá Call & Put:**
  $$C = e^{-rT} \left[ F N(d_1) - K N(d_2) \right], \quad P = e^{-rT} \left[ K N(-d_2) - F N(-d_1) \right]$$
- **Delta ($\Delta$):** $\Delta_{\text{Call}} = e^{-rT} N(d_1), \quad \Delta_{\text{Put}} = -e^{-rT} N(-d_1)$
- **Gamma ($\Gamma$):** $\Gamma = e^{-rT} \frac{N'(d_1)}{F \sigma \sqrt{T}}$
- **Vega ($\nu$):** $\nu = e^{-rT} F \sqrt{T} N'(d_1)$
- **Vanna ($VEX$):** $\text{Vanna} = -e^{-rT} N'(d_1) \frac{d_2}{\sigma}$
- **Charm ($CHEX$):**
  $$\text{Charm}_{\text{Call}} = e^{-rT} \left[ r N(d_1) + N'(d_1) \frac{d_2}{2T} \right]$$
  $$\text{Charm}_{\text{Put}} = e^{-rT} \left[ -r N(-d_1) + N'(d_1) \frac{d_2}{2T} \right]$$

### 3. Dòng tiền Dealer ($M) với Hệ số nhân Vàng Multiplier = 100.0:
- **Net GEX ($M / 1% dịch chuyển giá vàng):**
  $$\text{Net GEX}_K = \left( OI_{\text{Call}, K} \times \Gamma_K - OI_{\text{Put}, K} \times \Gamma_K \right) \times 100 \times F_0^2 \times 0.01$$
- **Net VEX ($M / 1% IV):**
  $$\text{Net VEX}_K = \left( OI_{\text{Call}, K} \times \text{Vanna}_K - OI_{\text{Put}, K} \times \text{Vanna}_K \right) \times 100 \times F_0 \times 0.01$$
- **Net CHEX ($M / ngày):**
  $$\text{Net CHEX}_K = \left( OI_{\text{Call}, K} \times \text{Charm}_{\text{Call}, K} - OI_{\text{Put}, K} \times \text{Charm}_{\text{Put}, K} \right) \times 100 \times F_0 \times \frac{1}{365}$$

### 4. Zero Gamma Flip ($S^*$) & Wall Siege Velocity
- **Giải nghiệm số Dekker-Brent (`_brentq`):**
  $$f(S^*) = \sum_{K} \text{Net GEX}_K(S^*) = 0$$
- **Wall Siege Velocity Ratio:**
  $$\text{Siege Ratio}_K = \frac{\text{Volume}_K}{\max(\text{Baseline OI}_K, 1)}$$

---

## IV. LƯỚI CRON ĐA TẦNG PRE-SESSION RADAR

Lưới Cron chạy tự động trên GitHub Actions phục vụ các thời điểm thanh khoản chuyển pha của Vàng:

```yaml
on:
  schedule:
    # 1. Khối 1: Chốt OI chính thức ngày mới từ CME Clearing
    #    00:15 UTC = 07:15 VN
    - cron: '15 0 * * 1-5'

    # 2. Khối 2: Phiên Âu 2 nấc (Pre-Europe & In-Session Europe)
    #    05:30 UTC = 12:30 VN (Pre-Europe mùa hè / 13:30 VN mùa đông)
    #    07:30 UTC = 14:30 VN (London Open mùa hè / 15:30 VN mùa đông)
    - cron: '30 5 * * 1-5'
    - cron: '30 7 * * 1-5'

    # 3. Khối 3: Phiên Mỹ & COMEX Pit Open (Pre-US & In-Session New York)
    #    11:45 UTC = 18:45 VN (Pre-US chuẩn bị mở cửa)
    #    12:20 UTC = 19:20 VN (COMEX Gold Pit Open 08:20 EST)
    #    13:45 - 19:45 UTC = 20:45 - 02:45 VN (Mỗi 60 phút xuyên suốt phiên Mỹ & London Fix)
    - cron: '45 11 * * 1-5'
    - cron: '20 12 * * 1-5'
    - cron: '45 13-19/1 * * 1-5'
```

---

## V. TIÊU CHUẨN DỌN RÁC & ZERO-WASTE (< 15MB)

1. Mọi file tạm, cache Playwright và artifact kiểm thử phải tự động giải phóng ngay sau mỗi lần thực thi (`--clear-cache`).
2. Dung lượng toàn bộ repo Neiro-Gold-Quant luôn được bảo toàn dưới ngưỡng nghiêm ngặt **15 MB**.
3. Thuật toán tối ưu bộ nhớ: `gc.collect()`, đóng kết nối browser, xóa cache tick `clear_spot_cache()` mỗi 20 chu kỳ.
