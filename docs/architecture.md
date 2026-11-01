# Neiro-Gold-Quant — TÀI LIỆU KIẾN TRÚC HỆ THỐNG ĐỊNH LƯỢNG (QUANT ARCHITECTURE)

> **Phiên bản:** v3.3 — Chuẩn Hóa 1:1 Cockpit Neiro-NQ-Quant & 4 Cột Profile Greeks Trên Canvas  
> **Dự án:** Neiro-Gold-Quant (Hệ thống Định lượng Vi mô Dòng tiền Market Maker & All-in-One Orderflow Terminal cho 100% Pure COMEX Gold Futures `GC` / `MGC`)  
> **Vận hành:** Cloud-Native Zero-Touch Automation (GitHub Actions + GitHub Pages, thuần Python, Zero-Waste < 15MB)  
> **Tài liệu chuẩn đối chiếu:** [docs/spec.md](spec.md), [config/settings.toml](../config/settings.toml), [docs/TRADER_PLAYBOOK.md](TRADER_PLAYBOOK.md), [ADR-018](decisions/ADR-018-tradingview-fullscreen-zero-tabs-and-realtime-tick-engine.md), [ADR-020](decisions/ADR-020-dedicated-vanna-and-charm-ladder-column.md).

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
4. **TradingView Fullscreen Zero-Tabs Realtime Terminal (Chuẩn hóa 1:1 Neiro-NQ-Quant):**
   - **Mặc định Timeframe M1:** Lấy 250 nến 1 phút liên tục gần nhất của COMEX Gold Futures `GC=F`, phản ánh từng biến động vi cấu trúc.
   - **TradingView Full-bleed Canvas 60 FPS:** Khung chart mở rộng 100% màn hình, topbar chuyên nghiệp với nhãn live badge và multiplier $100.0/oz.
   - **Floating Tactical HUD Card:** Góc trên bên trái hiển thị NET GEX, GAMMA SQUEEZE ↑/↓, VANNA, CHARM, THETA, 1-SIGMA.
   - **4 Cột Greeks Profile Cố Định Theo Trục Giá Nến:** GEX | VEX | CHEX | THETA trên Canvas 60 FPS bám sát `candleSeries.priceToCoordinate(k)`.
   - **Realtime Tick Engine:** Tự động đẩy giá nến M1 và đường giá live `livePriceLine` từng tick mà không cần reload trang (Zero Page Reload), triệt tiêu hiện tượng nhấp nháy chớp trắng.
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
│ [TẦNG 3: TRADINGVIEW FULLSCREEN REALTIME TERMINAL (CHUẨN HÓA 1:1 NEIRO-NQ-QUANT)]          │
│  ┌───────────────────────────────────────────────────────────────────────────────────────┐ │
│  │ KHỐI 1: TRADINGVIEW FULLSCREEN CANVAS 60 FPS (LIGHTWEIGHT CHARTS 4.2)                 │ │
│  │  - Mặc định M1 nến 1 phút liên tục CME GC=F, Topbar Live Badge, Multiplier $100.0/oz  │ │
│  │  - Floating Tactical HUD Card góc trên bên trái (GEX, SQZ, VEX, CHEX, TEX, 1-σ)       │ │
│  │  - 4 Cột Profile Greeks trên Canvas: GEX | VEX | CHEX | THETA bám chặt trục giá nến   │ │
│  │  - Pinned Edge Indicators: ▲ CALL WALL trên đỉnh, ▼ PUT WALL dưới đáy                 │ │
│  │  - Air Pocket Vacuum Zones, Realtime Tick Line, Subbar Live Greeks Radar              │ │
│  ├───────────────────────────────────────────────────────────────────────────────────────┤ │
│  │ KHỐI 2: UNIFIED GREEKS & ORDERFLOW PINNING MATRIX (FULL-BLEED 100% WIDTH)             │ │
│  │  - Hợp nhất toàn bộ: Net GEX ($M), Net VEX ($M/1%), Net CHEX ($M/d), Net Delta, OI, Vol│ │
│  ├───────────────────────────────────────────────────────────────────────────────────────┤ │
│  │ KHỐI 3: PLOTLY 4-PANEL QUANT LADDER (HIỂN THỊ SONG SONG LIỀN MẠCH)                    │ │
│  │  - Panel 1: Net GEX ($M) & Mốc Chiến Thuật | Panel 2: Volume, OI & Sổ Sách Net Delta   │ │
│  │  - Panel 3: Net VEX ($M/1% IV) Flow         | Panel 4: Net CHEX ($M/ngày) Delta Decay │ │
│  └───────────────────────────────────────────────────────────────────────────────────────┘ │
│  - Header KPI Bar: Spot CME, Net GEX Regime, Net Delta Tilt, Zero Gamma Flip, Expected Move│
│  - Multi-Expiry Term Structure: Xếp chồng tuyến tính Greeks ∑ NetGEX_e, ∑ NetVEX_e        │
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
│  - 100% Pure CME Futures Positioning: Khử bỏ toàn bộ Spot/Binance và kịch bản suy đoán.  │
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

---

## VI. BẢNG ĐỊNH LƯỢNG MICROSTRUCTURE MATRIX 8 CỘT & OTM VOLATILITY SMILE (ADR-019)

1. **Chuẩn hóa OTM Volatility Smile:**
   - Khi Call IV và Put IV giải ngược trùng nhau do Put-Call parity, hệ thống tự động tách biệt biểu diễn theo chuẩn tổ chức quốc tế (CME QuikStrike & Bloomberg):
     - Vùng Strike $\le$ Spot: Biểu diễn Put IV thực tế (OTM Puts).
     - Vùng Strike $\ge$ Spot: Biểu diễn Call IV thực tế (OTM Calls).
   - Loại bỏ hoàn toàn lỗi hiển thị chồng đè các điểm dữ liệu.

2. **Ma trận Vi Cấu Trúc Microstructure Matrix 8 Cột Đa Kỳ Hạn:**
   - 8 cột tiêu chuẩn chuẩn hóa theo Neiro-NQ-Quant: `GC Strike`, `Net GEX ($M)`, `Call OI`, `Put OI`, `Call Vol`, `Put Vol`, `Net VEX ($M)`, `Net CHEX ($M/d)`.
   - Tổng hợp vị thế đa kỳ hạn, tự động làm nổi bật Spot realtime, Call Wall, Put Wall và Zero Gamma Flip.

---

## VII. CHUẨN HÓA 1:1 GIAO DIỆN COCKPIT VỚI NEIRO-NQ-QUANT & 4 CỘT PROFILE GREEKS (ADR-020)

1. **Khắc phục điểm mù và lệch trục giá (Zero Vertical Desynchronization):**
   - Loại bỏ triệt để các bảng HTML độc lập ngoài chart để tránh hiện tượng lệch giá khi co giãn nến. Biểu đồ TradingView và Canvas chiếm trọn 100% diện tích màn hình.
   - Sử dụng hàm `candleSeries.priceToCoordinate(k)` tính tọa độ Y của từng mức giá trực tiếp trên Canvas 60 FPS, đảm bảo 4 cột profile Greeks (`GEX | VEX | CHEX | THETA`) luôn bám chặt và cố định theo mức giá của nến M1.

2. **Cấu trúc Cockpit Chuẩn Neiro-NQ-Quant:**
   - **Floating Quant HUD Card:** Đặt tại góc trên bên trái biểu đồ nến, hiển thị `NET GEX`, `GAMMA SQUEEZE ↑/↓`, `VANNA (VEX)`, `CHARM (CHEX)`, `THETA (TEX)`, `1-SIGMA`.
   - **Topbar & Subbar Realtime Greeks Radar:** Topbar hiển thị trạng thái `M1 INTRADAY` và các chỉ số tài chính vi cấu trúc; Subbar hiển thị live Black-76 Greeks tick-by-tick (Delta, Gamma, Vega, Theta, Vanna, Charm, Zero Gamma).
   - **4 Cột Profile Greeks Trên Canvas (colW = 60px):** Đặt bên phải sát thước đo giá, tỏa đều 2 phía từ trục tâm, với mã màu chuẩn hóa:
     * GEX: Xanh lá (`#22C55E`) / Đỏ (`#EF4444`).
     * VEX: Xanh Cyan (`#22D3EE` / `#0E7490`).
     * CHEX: Tím (`#C084FC` / `#7E22CE`).
     * THETA: Cam (`#FDBA74` / `#EA580C`).
   - **Pinned Edge Indicators:** Ghim cảnh báo `▲ CALL WALL` khi nằm vượt lên trên khung hình, `▼ PUT WALL` khi nằm tụt xuống dưới đáy khung hình.
