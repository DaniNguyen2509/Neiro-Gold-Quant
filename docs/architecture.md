# Neiro-Gold-Quant — TÀI LIỆU KIẾN TRÚC HỆ THỐNG ĐỊNH LƯỢNG (QUANT ARCHITECTURE)

> **Phiên bản:** v3.3 — Chuẩn Hóa 1:1 Cockpit Neiro-NQ-Quant & 4 Cột Profile Greeks Trên Canvas  
> **Dự án:** Neiro-Gold-Quant (Hệ thống Định lượng Vi mô Dòng tiền Market Maker & All-in-One Orderflow Terminal cho 100% Pure COMEX Gold Futures `GC` / `MGC`)  
> **Vận hành:** Cloud-Native Zero-Touch Automation (GitHub Actions + GitHub Pages, thuần Python, Zero-Waste < 15MB)  
> **Tài liệu chuẩn đối chiếu:** [docs/spec.md](spec.md), [config/settings.toml](../config/settings.toml), [docs/TRADER_PLAYBOOK.md](TRADER_PLAYBOOK.md), [ADR-018](decisions/ADR-018-tradingview-fullscreen-zero-tabs-and-realtime-tick-engine.md), [ADR-020](decisions/ADR-020-dedicated-vanna-and-charm-ladder-column.md).

---

## I. MỤC TIÊU CỐT LÕI & TRIẾT LÝ VẬN HÀNH (FIRST PRINCIPLES)

Thị trường Vàng phái sinh quốc tế (**COMEX Gold Futures `GC` / `GC=F`**) được chi phối bởi các Ngân hàng Vàng (Bullion Banks - HSBC, JPMorgan, UBS...), các Nhà tạo lập thị trường Quyền chọn (Options Market Makers - MMs / Dealers) và các quỹ vĩ mô (Macro Hedge Funds).  
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
   - **Độ lệch Cost-of-Carry & Term Structure:** Hệ thống neo 100% giá giao dịch và vị thế theo **COMEX Gold Futures (`GC` / `GC=F`)** (Rule 8). Chỉ sử dụng mô hình Cost-of-Carry nội tại khi phân tích chênh lệch Forward-Implied theo `F_0 = S_0 * exp((r + u - y)T)`:
     - Khi $F_{0, \text{thực tế}} \gg F_{0, \text{lý thuyết}}$: Lực mua áp đảo trên sàn COMEX New York phản ánh nhu cầu phòng hộ/đầu cơ Futures tăng mạnh (`GC` premium).
     - Khi $F_{0, \text{thực tế}} \ll F_{0, \text{lý thuyết}}$: Áp lực bán phòng hộ từ khai thác mỏ kéo kỳ hạn gần chiết khấu.
3. **Bất biến Zero Gamma Flip ($S^*$) & Tỷ lệ Công thành (Wall Siege Ratio):**
   - Mốc đảo pha $S^*$ được giải liên tục bằng phương trình $\sum_k \text{NetGEX}_k(S^*) = 0$ thông qua thuật toán Dekker-Brent (`_brentq` thuần Python, không dùng xấp xỉ strike thô để tránh sai lệch Jensen).
   - Áp lực tấn công thành trì trong ngày được đo lường bằng tỷ lệ tốc độ dòng tiền:
     $$\text{Wall Siege Ratio} = \frac{\text{Volume}}{\max(\text{Baseline OI}, 1)}$$
     Khi $\text{Siege Ratio} \ge 0.25$, hệ thống phát cảnh báo nguy cơ vỡ trận phòng thủ.
4. **TradingView Fullscreen Zero-Tabs Realtime Terminal (Chuẩn hóa 1:1 Neiro-NQ-Quant & Yahoo `GC=F`):**
   - **Đồng bộ Nến Đa Khung Thời Gian Yahoo `GC=F` (`1m`, `5m`, `15m`, `1h`, `1d`):** Nạp nến thực tế từ COMEX Gold Futures `GC=F` cho cả khung Intraday và HTF (`window.INITIAL_TF_CANDLES`), bảo toàn 100% giá OHLC thực và đồng bộ tuyệt đối giữa `spot_price` và cây nến cuối.
   - **Cầu nối Local CORS HTTP (`127.0.0.1:8765`, `ThreadingHTTPServer`) & Cloud Hot-Patching:** Khi chạy `--loop`, hệ thống khởi chạy luồng HTTP JSON đa luồng kèm RAM cache (`1.8s` bridge TTL, `3.0s` M5 TTL, `60.0s` HTF TTL) phục vụ `/api/yahoo_gc` và `/version.json` (`Access-Control-Allow-Origin: *`), cho phép trình duyệt (kể cả khi mở qua `file://`) cập nhật nến Yahoo `GC=F` mỗi `2.5s` (local bridge) / `5.0s` (fallback) mà không bao giờ gọi `window.location.reload()`. Chu kỳ `--loop` tách bạch dữ liệu tĩnh theo chữ ký `mtime_ns`/`size` của CSV và cập nhật nhẹ JSON ở các nhịp trung gian.
   - **Kiểm soát Giờ Phiên CME Globex & Chuẩn Zero-BS (`yahooAnchorPrice`):** Khóa biểu đồ tại giá Settlement chính thức khi sàn CME đóng cửa cuối tuần hoặc nghỉ bảo trì hàng ngày (17:00–18:00 ET); gỡ bỏ hoàn toàn WebSocket proxy `paxgusdt@aggTrade`, nến giả lập `Math.random()`, và trọng số Lee-Ready suy đoán khi thiếu `Bid/Ask`. Toàn bộ `H20/L20` của quỹ CTA được lấy từ chuỗi nến `1D` thực tế của `GC=F`, kèm cơ chế tự động đồng bộ `data/options_prices_GCZ26.csv` mới nhất từ GitHub Cloud khi chạy cục bộ.
   - **TradingView Full-bleed Canvas 60 FPS (`UTC+7`):** Khung chart mở rộng 100% màn hình, trục thời gian hiển thị chuẩn giờ Việt Nam (`UTC+7`), topbar chuyên nghiệp với nhãn live badge và multiplier $100.0/oz.
   - **Floating Tactical HUD Card:** Góc trên bên trái hiển thị NET GEX, GAMMA SQUEEZE ↑/↓, VANNA, CHARM, THETA, 1-SIGMA.
   - **4 Cột Greeks Profile Cố Định Theo Trục Giá Nến:** GEX | VEX | CHEX | THETA trên Canvas 60 FPS bám sát `candleSeries.priceToCoordinate(k)`.
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
│  - dealer.py: Zero Gamma (_brentq), Wall Siege, Kyle OLS, VPIN, Dynamic Vacuum & FVG, Post-Sweep│
│  - level_state.py: Level State Machine & Static OI Air Pocket Zones (hợp nhất duy nhất).    │
│  - institutional.py: 25Δ Risk Reversal (RR25), Butterfly (BF25), VRP, Vol-Target & Bayesian. │
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
│  │  - 4 Cột Profile Greeks (ADR-021): Dynamic Visible Normalization & Sublinear Boost     │ │
│  │  - Cross-Canvas Air Pocket Matrix: Dải chân không quét xuyên suốt nến & cột Greeks     │ │
│  │  - Interactive Greeks Tooltip: Rê chuột xem chi tiết Strike, GEX, VEX, CHEX           │ │
│  │  - Pinned Edge Indicators: ▲ CALL WALL trên đỉnh, ▼ PUT WALL dưới đáy                 │ │
│  ├───────────────────────────────────────────────────────────────────────────────────────┤ │
│  │ KHỐI 2: UNIFIED GREEKS & ORDERFLOW PINNING MATRIX (FULL-BLEED 100% WIDTH)             │ │
│  │  - Hợp nhất toàn bộ: Net GEX ($M), Net VEX ($M/1%), Net CHEX ($M/d), Net Delta, OI, Vol│ │
│  ├───────────────────────────────────────────────────────────────────────────────────────┤ │
│  │ KHỐI 3: BỎ QUA RENDER PLOTLY 4-PANEL TRÊN LIVE HTML (ADR-027)                         │ │
│  │  - Giữ hàm `build_plotly_figure` phục vụ unit tests; live HTML dùng Canvas & Smile    │ │
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
- $S_0$: Giá quy chiếu nội tại theo Cost-of-Carry ($F_{0, \text{Forward}} \cdot e^{-(r + u - y)T}$). *(Lưu ý Rule 8: Terminal chỉ hiển thị duy nhất giá `GC=F` CME Futures).*
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
  $$\text{Charm}_{\text{Call}} = e^{-rT} \left[ N'(d_1) \frac{d_2}{2T} - r N(d_1) \right]$$
  $$\text{Charm}_{\text{Put}} = e^{-rT} \left[ N'(d_1) \frac{d_2}{2T} + r N(-d_1) \right]$$

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


3. **Chuẩn Hóa Nến M1 & Khử Nhiễu Settlement Spike Artifact:**
   - **Màu sắc TradingView chuẩn:** Nến tăng Xanh lá (#22C55E) và nến giảm Đỏ tươi (#EF4444) với viền và râu đồng màu, tối ưu độ tương phản trên nền đen sâu #000000.
   - **Khử nhiễu CME Settlement Fix:** Bộ lọc `basis.py` tự động nhận diện và gọt bỏ hiện tượng Yahoo Finance chèn giá chốt ngày `$4,898.90` vào cây nến 1 phút cuối (gây ra cây nến râu dài 14 USD dị thường). Thân nến M1 được giữ nguyên giá khớp thực tế (`~$4,885.50`), trong khi mốc thanh toán `$4,898.90` được biểu diễn qua đường ngang livePriceLine (F0 LIVE / CME SETTLE).
   - **Độ sâu nến lịch sử:** Mở rộng lên 400 nến M1 liên tục, cho phép trader cuộn xem trọn vẹn diễn biến phiên giao dịch.


---

## VIII. TÍCH HỢP XUYÊN SUỐT AIR POCKET MATRIX & DYNAMIC VISIBLE GREEKS NORMALIZATION (ADR-021)

1. **Khắc phục điểm mù Vanna/Charm quá nhỏ (Dynamic Visible Normalization & Sublinear Boost):**
   - Loại bỏ cơ chế chuẩn hóa toàn cầu theo cực đại toàn chuỗi (`globalMaxAbs = 26M`), vốn làm tê liệt các mốc Vanna/Charm quanh vùng ATM (chỉ rộng ~0.02 pixel).
   - Áp dụng **Dynamic Visible Normalization**: Chỉ chuẩn hóa theo cực trị của các Strike đang hiển thị trong viewport hiện tại (`visibleMaxAbs`).
   - Kết hợp **Perceptual Sublinear Scaling**: $\text{scaled} = (|v| / \text{visibleMaxAbs})^{0.50}$ và ép `minLen = 3.5px`, giúp các thanh bar VEX và CHEX luôn bung đều, đậm nét và có viền tương phản cao.
   - Bổ sung chỉ số biên độ thang đo động dưới tiêu đề cột (ví dụ: `VEX: ±2.8M`, `CHEX: ±1.1M/d`).

2. **Cross-Canvas Air Pocket Matrix (Tích hợp túi chân không vào cột Greeks):**
   - Sửa lỗi đa hình dataclass (`start_strike`/`end_strike`) trong pipeline Python, mở rộng quét túi chân không cấu trúc tầng sâu bên dưới Put Wall ($3,880 - $3,900) và tầng trên Call Wall.
   - Dải cảnh báo chân không quét xuyên suốt từ biểu đồ nến sang tận mép ngoài của 4 cột Greeks bên phải:
     * Nền cảnh báo hổ phách trong suốt `rgba(245, 158, 11, 0.22)` kèm viền nét đứt vàng cam.
     * Hiển thị trực tiếp Badge cảnh báo nổi giữa cột Greeks: `⚠️ AIR POCKET [CẤM ĐỠ] $from - $to`.

3. **Interactive Greeks Tooltip Inspection:**
   - Khi người dùng rê chuột vào vùng 4 cột Greeks bên phải, Canvas tự động kích hoạt gióng Strike gần nhất và hiển thị thẻ Tooltip Card nổi bật: `Strike $K`, `GEX ($M)`, `VEX ($M)`, `CHEX ($M/d)`.


---

## IX. KHUNG KIỂM THỬ TOÀN DIỆN & CÁC BẤT BIẾN VI CẤU TRÚC (ADR-022)

1. **Thiết kế 4 trụ cột kiểm thử chuyên biệt (125 tests mở rộng):**
   - **Cổng dữ liệu & CI Invariant (`tests/test_data_gate.py`):** Kiểm định độ bao phủ Strike quanh giá GC hiện tại, cờ Stale độc lập với mtime, cơ chế chặn rò rỉ rác (`clean_val`), và yêu cầu CI verify step phải báo lỗi minh bạch thay vì lặng lẽ revert.
   - **Lõi toán định lượng thuần Python (`tests/test_math_core.py`):** Kiểm định độ chính xác của Dekker-Brent `_brentq`, tính bất biến tỷ lệ OI của Zero Gamma Flip ($S^*$), xử lý biên độ biến động Black-76 IV.
   - **Tính nhất quán $T_{\text{floor}}$ & Rollover vi mô (`tests/test_expiry_rollover.py`):** Kiểm tra tính hữu hạn của Greeks khi $T \to 0$ (1 phút), logic tự động chuyển đổi hợp đồng cơ sở (`underlying_futures`), và loại bỏ ngày hết hạn trong quá khứ ở nhánh fallback.
   - **Smoke test render Dashboard end-to-end (`tests/test_hud_smoke.py`):** Xác minh toàn trình chuyển hóa CSV $\to$ HTML, kiểm tra hiển thị mốc tường/flip, bắt lỗi biến `stale_badge_html` bị bỏ quên và cờ fallback benchmark.

2. **Cơ chế Khóa Lỗi Đỏ (RED-EXPECTED Gates):**
   - Duy trì 16 ca kiểm thử ở trạng thái RED-EXPECTED để bảo vệ nguyên trạng hệ thống, hỗ trợ chủ dự án kiểm soát rủi ro và phê duyệt khắc phục từng bước có kiểm chứng (TDD / Doubt-Driven Development).

---

## X. ĐỒNG BỘ MÚI GIỜ MÙA ĐÔNG HOA KỲ & KHẢ NĂNG TỰ PHỤC HỒI DỮ LIỆU ĐẦU VÀO (ADR-023)

1. **Thích ứng Múi Giờ Mùa Đông (US Standard Time - EST/CST):**
   - Kể từ 01/11/2026, thị trường Mỹ chuyển dịch giờ giao dịch (lùi 1 giờ so với mùa hè):
     * Mở phiên chứng khoán & GLD ETF: 09:30 AM EST = 14:30 UTC = 21:30 VN.
     * Tin vĩ mô nhạy cảm (CPI/NFP): 08:30 AM EST = 13:30 UTC = 20:30 VN.
     * Giờ chốt phiên COMEX & Hết hạn Options: 13:30 CST = 19:30 UTC = 02:30 VN (ngày hôm sau).
   - Hàm `get_cme_cutoff_dt()` trong `src/quant_engine/synthetic.py` sử dụng `zoneinfo.ZoneInfo("America/Chicago")` tự động định tuyến chính xác 18:30 UTC vào mùa hè và 19:30 UTC vào mùa đông.

2. **Ma Trận Lập Lịch Tự Động Toàn Mùa (Dual-Season CI Radar):**
   - Workflow `.github/workflows/daily_options_sync.yml` tích hợp các mốc quét tự động:
     * `15 12,13,14 * * 1-5`: Đón đầu tin vĩ mô và trước giờ mở cửa New York (cả 2 mùa).
     * `45 13,14,15,16,17,18,19 * * 1-5`: Bám sát đà rung lắc cao điểm, London PM Fix và thu hoạch chính xác giá chốt sổ (18:45 UTC hè / 19:45 UTC đông).

3. **Tự Động Tính Black-76 IV Ngay Tại Scraper:**
   - Hàm `_enrich_options_iv_and_greeks()` trong `src/collector/scraper.py` tự động giải nghiệm độ biến động ngầm định bằng mô hình Black-76 nếu Barchart trả về `callIV == 0.0` hoặc `putIV == 0.0`.

4. **Neo Giữ ATM Strike Khi Thị Trường Kém Thanh Khoản (Spot-Anchored ATM):**
   - `find_atm_strike()` ưu tiên các strike có chào giá 2 chiều (Bid/Ask > 0). Trường hợp phiên ngoài giờ hoặc cuối tuần chưa mở bảng giá (`bid=0, ask=0`), hàm tự động neo vào `spot_price` (hoặc Strike trung vị) thay vì chọn nhầm strike xa lắc như $1,350.

---

## XI. ĐỘNG CƠ TÍNH TOÁN SẴN (PRECOMPUTED STATIC ENGINE) & CHUẨN HÓA DATA ANALYST (ADR-024)

1. **Tính toán sẵn toàn bộ Ma trận Gamma Squeeze (Precomputed Squeeze Ladder Grid):**
   - Cấu trúc Open Interest (OI) của CME Options là bất biến trong suốt phiên giao dịch (chỉ cập nhật qua đêm). Do đó, toàn bộ ngưỡng kích hoạt Squeeze ($K + \text{buffer} + 0.50$), ngưỡng chốt lời (TP) và ngưỡng cắt lỗ (SL) cho tất cả các strike trong dải tác chiến được tính toán sẵn một lần duy nhất qua hàm `precompute_squeeze_ladder()`.
   - Hàm `lookup_precomputed_squeeze(ladder, spot)` cung cấp khả năng gióng hàng tức thời $\mathcal{O}(1)$ với độ trễ $< 0.1\mu s$, loại bỏ hoàn toàn tính toán lặp lại trong vòng lặp nến realtime, bảo đảm CPU < 1% và zero memory leak.

2. **Quy trình chuẩn hóa dữ liệu Data Analyst (Data Ingestion & Cleaning Hardening):**
   - Hàm `clean_and_sanitize_options_dataset()` trong `src/collector/validator.py` tự động:
     * Khử trùng lặp strike (`drop_duplicates`).
     * Ép thứ tự tăng dần nghiêm ngặt (Monotonicity).
     * Tự động sửa lỗi chào giá chéo (Crossed quotes: tự động hoán đổi khi $\text{Ask} < \text{Bid}$).
     * Làm sạch các ký tự lạ, tiền tệ, công thức lỗi (#N/A, unch, $).
     * Khóa cận không âm cho OI, Volume và IV.


3. **Bất biến Tự Chữa Lành Gamma Power Black-76 & Làm giàu IV Đa Kỳ Hạn (Black-76 Gamma Power Self-Healing):**
   - Khi dữ liệu thô trả về `gamma = 0.0` và bị gán mặc định đồng loạt `0.0037` (unphysical flat gamma), toàn bộ chuỗi xử lý (`aggregate_options_dataframes`, `compute_tactical_matrix`, `find_gamma_weighted_walls`, `load_and_preprocess_options`) tự động phát hiện qua cờ `raw_unphys` (kiểm tra cả `callGamma` và tỷ lệ `callGammaPower / callOpenInterest` tại vùng Deep OTM `strike > spot + 800`) và ép tính lại `callGamma`, `putGamma`, `callGammaPower = callOI * gamma_b76`, `putGammaPower = putOI * gamma_b76` cùng `GEX/VEX/CHEX` theo giải tích Black-76 chuẩn xác.
   - Tại `scrape_multi_expiry_and_save()`, mỗi kỳ hạn con (Nearest Weekly, End-of-Month, Quarterly Anchor) bắt buộc được làm giàu Black-76 IV và Greeks theo đúng `dte` riêng trước khi gộp tỷ trọng Gamma Power (`aggregate_options_dataframes`), ngăn chặn triệt để hiện tượng tường ảo ở các strike Deep OTM ($5,500 hay $3,700).


4. **Tự Động Nhận Diện 3 Tầng Kỳ Hạn Đáo Hạn & Lịch Nghỉ Lễ Sàn CME (3-Tier Expiry Auto-Discovery):**
   - Hệ thống (`resolve_active_expirations` & `resolve_next_quarterly_cme_option` trong `src/quant_engine/synthetic.py`) tự động nhận diện đồng thời 3 tầng thanh khoản:
     * **Tầng 1 (`WEEKLY`):** Các kỳ Thứ Sáu gần nhất (`OG1..OG5` / Barchart `IG1..IG5`), tự động lùi về Thứ Năm nếu Thứ Sáu trùng ngày lễ sàn CME (`get_cme_holidays`: Good Friday, Christmas, Independence Day, New Year...) và tự động tránh trùng lặp nếu ngày Thứ Sáu trùng với ngày đáo hạn Monthly.
     * **Tầng 2 (`MONTHLY`):** Kỳ hạn Tháng hiện hành (`OG{Month}{YY}`), tự động chuyển tiếp hợp đồng cơ sở (`GCZ26` $\to$ `GCG27` $\to$ `GCJ27`...) ngay sau giờ chốt sổ `13:30 America/Chicago`.
     * **Tầng 3 (`QUARTERLY`):** Tự động phát hiện và thu thập kỳ hạn Chủ lực / Quý kế tiếp thuộc chu kỳ vàng tổ chức (`G-Feb, J-Apr, M-Jun, Q-Aug, Z-Dec`), bảo đảm không bao giờ bỏ sót bức tường Open Interest (OI) tổ chức lớn nhất khi kỳ Front-Month rơi vào các tháng phụ (Serial Months).
   - Khi thu thập thực tế từ Barchart (`scrape_multi_expiry_and_save`), hệ thống ưu tiên đọc trực tiếp trường `expirationDate` chính thức từ JSON của Barchart trả về cho từng kỳ hạn con để hiệu chỉnh `DTE` chính xác tuyệt đối trước khi giải nghiệm Black-76 IV và gộp đa kỳ hạn theo Volatility Skew từng Strike (`callIV` / `putIV`).


5. **Động Cơ Giải Mã Orderflow Thực Tế Không Cần Level 3 MDP 3.0 (`reconstruct_institutional_orderflow`):**
   - Trong `src/quant_engine/dealer.py`, hàm `reconstruct_institutional_orderflow()` tái tạo trực tiếp dòng lệnh tổ chức qua 4 thước đo vi cấu trúc:
     * **Lee-Ready Quote Location-in-Spread + Local IV Skew:** Định dấu chủ động Mua/Bán (`SignedCallFlow`, `SignedPutFlow`) từ vị trí giá khớp `LastPrice` trong khoảng `[Bid, Ask]` kết hợp độ bung `IV` cục bộ để tính chính xác số lượng hợp đồng tương lai `GC` mà Dealer bị ép phải mua/bán phòng hộ (`dealer_hedge_futures_flow`).
     * **Put-Call Parity Implied Forward Lead-Lag ($\delta F = F_{\text{opt}} - F_{\text{GC}}$):** Đo độ lệch giữa giá tương lai ngầm định trên sổ lệnh Options ($F_{\text{opt}} = K + e^{rT}(C_{\text{mid}} - P_{\text{mid}})$) và giá khớp lệnh `GC=F` để phát hiện dòng tiền tổ chức dẫn sóng từ bàn Options sang bàn Futures.
     * **Guaranteed New Intraday Whale Initiation ($\text{Volume}_K > \text{OI}_K$):** Phát hiện 100% vị thế mở mới trong ngày khi khối lượng khớp vượt trần Open Interest đầu ngày ($\text{new\_contracts\_min} = \text{Volume}_K - \text{OI}_K$).
     * **Bulk Volume Classification (BVC - Easley, López de Prado & O'Hara) & Kyle's Lambda ($\lambda$):** Phân rã `CVD` (Cumulative Volume Delta) và đo hệ số cản giá $\lambda = |\Delta P| / V$ để nhận diện **True Iceberg Absorption** (khối lượng lớn nhưng biên độ nén chặt) so với **Liquidity Vacuum Sweep** (trượt giá qua sổ lệnh rỗng).
     * **Trực Quan Hóa 60FPS Độ Trễ Bằng Không (`src/hud/neiro_terminal.py` & `QUANT MICROSTRUCTURE`):** Hiển thị trực tiếp ngay trên màn hình chính `NEIRO ORDERFLOW` gồm: (a) cột thứ 5 `FLOW (GC)` ngay cạnh `GEX | VEX | CHEX | THETA` trên `#neiro-canvas` kèm nhãn `⚡W` tại các strike cá mập mở mới (`Vol > OI`), (b) thanh kéo co `MUA BVC % vs BÁN %` và nhãn `Footprint Δ` gắn trực tiếp vào nến M1 hiện hành (`F0 LIVE`), (c) khối `REALTIME ORDERFLOW` trong hộp Floating HUD góc trên trái, và (d) 2 cột `Signed Flow (C/P)` + `Ép Dealer Hedge & Orderflow` ngay trong bảng `QUANT MICROSTRUCTURE` dưới biểu đồ, tự động nội suy `< 1ms` trên mỗi tick mà không cần tải lại trang.

---

## XII. ĐỘNG CƠ "INFORMED QUANT TRADER" KHÉP KÍN & CỬA SỔ REALTIME ±10 STRIKES (ADR-025)

1. **5 Trụ Cột Định Lượng Khép Kín (`src/quant_engine/dealer.py` & `src/quant_engine/institutional.py`):**
   - **Rolling OLS Kyle's Lambda ($\lambda_{\text{OLS}} = \text{Cov}(\Delta P, y)/\text{Var}(y)$):** Đo độ dốc tác động giá của dòng lệnh có dấu BVC và phát hiện kiệt sức sau quét thanh khoản (`PREDATORY_SWEEP_EXHAUSTION`).
   - **Chỉ số Độc Tính Dòng Lệnh VPIN (`compute_vpin_bvc` — Easley, López de Prado & O'Hara, 2012):** Phân ngưỡng học thuật chuẩn: `< 40%` (`SAFE_MEAN_REVERSION` — an toàn đánh đảo chiều tại Wall), `40%–65%` (`ELEVATED_IMBALANCE`), và `>= 65%` (`TOXIC_INFORMED_FLOW` — hủy lệnh Limit cản tàu, chuyển sang đánh thuận Squeeze).
   - **Phần Bù Rủi Ro Biến Động VRP (`compute_vrp_metrics` — Carr & Wu, 2009):** So sánh $IV_{\text{ATM}}$ của Options COMEX với biến động thực tế Parkinson High-Low $RV$ trên chuỗi nến `1D` `GC=F` để bắt nhịp `VEGA CRUSH` ($VRP \ge +4.0\%$) và `GAMMA EXPLOSION` ($VRP \le -2.0\%$).
   - **Z-Score Dẫn Dắt Put-Call Parity ($Z_{\Delta F}$) & Hệ Số Tương Quan Thông Tin Bayesian ($\rho_{v,s} = \sqrt{\text{SNR}/(1+\text{SNR})}$):** Kết hợp lọc độ dày thanh khoản phiên CME Globex ($\sigma_u$) và hệ số điều chỉnh khối lượng Fractional Kelly (`kelly_fraction_mult`).
2. **Cửa Sổ Động `±10 Strikes` & Đồng Bộ `👉 SPOT` Realtime (`src/hud/html_dashboard.py` & `src/hud/neiro_terminal.py`):**
   - Bảng `BẢNG DỮ LIỆU ĐỊNH LƯỢNG MICROSTRUCTURE & DÒNG LỆNH TỪNG STRIKE` chỉ hiển thị đúng `±10 strikes` quanh giá `GC=F` hiện hành (tối đa 21 dòng hiển thị).
   - Hàm `applyLiveTick()` cập nhật tức thời vị trí hàng `.row-spot`, huy hiệu `.micro-spot-badge` (`👉 SPOT: $...`), cửa sổ `±10 strikes`, `#kpi-cme-price` và `#spine-current-price` ngay khi giá `GC=F` biến động.

---

## XIII. ĐỘNG CƠ DYNAMIC LIQUIDITY VACUUM, INSTITUTIONAL FVG & POST-SWEEP EXECUTION (ADR-026)

1. **Hệ Sinh Thái Chân Không Thanh Khoản 3 Tầng Thuần CME Futures (`src/quant_engine/dealer.py` & `level_state.py`):**
   - **Tầng 1 — Static OI Air Pocket (`level_state.detect_strike_air_pockets`):** Nguồn sự thật duy nhất về khoảng trống OI giữa các Strike COMEX (`OI < 35% MA`), dùng chung cho `strategy.py` (`precompute_squeeze_ladder`), `neiro_terminal.py` và `html_dashboard.py` (loại bỏ `src/quant_engine/air_pocket.py` và bản `AirPocket` trùng trong `strategy.py`).
   - **Tầng 2 — Dynamic High-Frequency Liquidity Vacuum (`compute_dynamic_liquidity_vacuum` & `compute_rogers_satchell_bar`):** Kết hợp Amihud `ILLIQ` ($|\ln(C_t/C_{t-1})| / V_t$), biến động bất biến theo hướng Rogers-Satchell ($\sqrt{\max(RS_t, 0)}$) và `bar_lam` trên các nến có `Volume > 0`, khóa chặt nhiễu phiên Á mỏng (`THIN_SESSION_GUARDED`) và phiên nghỉ CME (`GLOBEX_CLOSED`), chỉ phát cảnh báo `DYNAMIC_LIQUIDITY_VACUUM` trong phiên sâu `LONDON_DEEP` / `NY_COMEX_DEEP`.
   - **Tầng 2.5 — Institutional Vacuum FVG (`detect_institutional_fvgs`):** Chỉ giữ lại khoảng trống 3 nến (`FVG`) gắn liền với nến Vacuum hoặc hợp lưu với Wall / Zero Gamma / Static Air Pocket, tính sẵn vùng hồi quy `midpoint_50` và `zone_75` để vẽ trực tiếp lên `#neiro-canvas`.
2. **Bộ Phân Loại Thực Thi Post-Sweep Không Giả Lập (`classify_post_sweep_execution`):**
   - Thay thế tham số $\kappa$ ẩn bằng biến quan sát thực tế thuần `GC=F` (tuân thủ Rule 8): khóa cứng `TOXIC_CASCADE_BLOCKED` khi `VPIN >= 65%`, và phân nhánh `POST_SWEEP_V_SHAPE` (phá đỉnh/đáy nến hấp thụ trong phiên sâu hoặc `VRP >= +4.0%` kèm động lượng $\lambda_{\text{post}}$ / Parity Z-Score) so với `POST_SWEEP_PULLBACK` (chờ Limit tại `50%–75%` FVG).
3. **Đồng Bộ Client JS & Tinh Gọn Kiến Trúc (`src/hud/neiro_terminal.py`, `html_dashboard.py`, `basis.py`):**
   - Loại bỏ `vTick` giả lập trong `applyLiveTick()` khi `tickVol === null` và fallback `volume: 120` trong `mergeLiveCandles()`; bổ sung `evaluateBarOrderflow()` trên nến hoàn tất mang Volume thật và `updateSqueezeHud()` tra cứu nhị phân `squeeze_ladder`.
   - Dọn bỏ 6 file mã chết (`src/main.py`, `src/hud/chart_exporter.py`, `src/quant_engine/scenario_engine.py`, `src/quant_engine/air_pocket.py`, `tests/test_scenario_engine.py`, `tests/test_air_pocket.py`) và đồng bộ nhãn khung thời gian `timeframe_label` (`M1`/`M5`) từ `basis.py`.

---

## XIV. TỐI ƯU HÓA ĐỘ TRỄ TOÀN TRÌNH, LIVE BRIDGE & TINH GỌN COCKPIT (ADR-027)

1. **Vector hóa Nạp Dữ liệu & Lõi Toán (`src/quant_engine/loader.py`, `dealer.py`, `validator.py`, `html_dashboard.py`):**
   - Cache `preloaded_dfs` trong `load_multi_expiry_options`, vector hóa `normalize_options_df` kèm cờ `attrs["is_normalized"]`, gán `allow_network=False` trong `aggregate_options_dataframes` và dựng `OptionsStrike` bằng NumPy/zip.
   - Vector hóa `find_gamma_weighted_walls`, `reconstruct_institutional_orderflow`, dùng `_series_clean_val` và chỉ giải Black-76 IV trên các chỉ mục `needs_c_iv` / `needs_p_iv` thực sự thiếu IV.
2. **Song song hóa Yahoo Feed, HTTP Gzip & Bridge Đa luồng (`src/quant_engine/basis.py`, `html_dashboard.py`, `neiro_terminal.py`):**
   - Hợp nhất `_read_yahoo_json()` với `"Accept-Encoding": "gzip"`, cache `_M5_TAPE_CACHE` (`3.0s`) và `_HTF_TAPE_CACHE` (`60.0s`) kèm tải song song `1h`/`1d` (`ThreadPoolExecutor`), tái dùng `m5_tape` trong `load_and_preprocess_options`.
   - `run_pipeline(..., no_mt5=True)` mặc định chạy `CME_ONLY` (`load_and_preprocess_options` giữ mặc định `no_mt5=False`), bỏ gọi `build_plotly_figure` trên đường chạy chính (giữ nguyên hàm cho tests), cache chuỗi CSV tĩnh theo `mtime_ns`/`size` và tách `_run_lightweight_live_tick()` cho `--loop`.
   - Nâng cấp cầu nối cục bộ sang `ThreadingHTTPServer` (`daemon_threads=True`) + RAM cache `1.8s` và đồng nhất nhịp poll client JS (`YAHOO_POLL_INTERVAL_MS` + chống trùng `checkCloudSyncNow`).
3. **Tinh gọn DOM/JSON & Giao diện Scalping (`src/hud/neiro_terminal.py`, `html_dashboard.py`):**
   - Cắt tỉa `window.INITIAL_OPTIONS` và `squeeze_ladder` trong hành lang `±$600` quanh Spot (kèm `±$25` quanh các mốc trụ cột), giới hạn bảng Pinning ở `±35 strikes` quanh Spot (`<= 71` dòng `<tr>` trên dữ liệu thực tế), bỏ 3 thẻ Orderflow đóng băng trùng lặp ở `KHỐI 5` và thu gọn `KHỐI 1` (Smile), `KHỐI 6`, `KHỐI 7` bằng `<details>` giữ nguyên thứ tự các landmark kiểm thử.

---

## XV. HIỆU CHỈNH ĐỘNG CƠ VPIN & MA TRẬN TÁC CHIẾN KHỐI 6 (ADR-028)

1. **Hiệu chỉnh VPIN BVC Không Tự Triệt Tiêu (`src/quant_engine/dealer.py`):**
   - Với chuỗi nến thực tế (`len >= window + 20`), `compute_vpin_bvc` tính $\sigma_{\Delta P}$ từ phân tán nền `candles[:-6]` (`0.5 * P60(|dp|)/0.8416 + 0.5 * MAD_scaled`) thay vì `np.std` trên chính 24 nến đang bùng nổ, và áp dụng equal-volume bucket splitting trên `12` nến gần nhất để phát hiện chính xác các cú quét có độc tính cao (`>= 65%`) mà vẫn giữ nguyên hành vi đơn vị cho fixture ngắn.
2. **Hợp nhất Ma trận Entry / SL / TP & Cổng Kích Hoạt `KHỐI 6` (`src/quant_engine/strategy.py`, `src/hud/html_dashboard.py`):**
   - `compute_m5_equivalent_atr()` ước lượng ATR `M5` từ dữ liệu nến đóng cửa (`[2.0, 6.5]`, fallback `4.0`).
   - `compute_tactical_intraday_matrix()` nâng khoảng đệm Breakout `Squeeze`/`Breakdown` tối thiểu `±$2.80` (`max(2.80, 0.8 * ATR)`), nâng Hard SL tối thiểu `\$5.00` cho cả Breakout lẫn Mean-Reversion (`Fade`/`Rebound`), giới hạn TP thực tế (`1.5x Risk` cho Breakout, `[\$3.00, \$6.00]` cho `Fade`, `[\$3.00, \$7.50]` cho `Rebound`) và gắn nhãn trạng thái `[KÍCH HOẠT]` / `[CHỜ XÁC NHẬN]` / `[TẠM KHÓA]` dựa trên GEX Regime, Zero Gamma Flip ($S^*$), neo Put Wall, Air Pocket, Wall Siege và VPIN.
   - `precompute_squeeze_ladder()` được đồng bộ ngưỡng kích hoạt tối thiểu `±2.80` và SL tối thiểu `\$5.00` sau strike, bảo toàn cơ chế mở rộng TP theo Air Pocket cho Live HUD.

---

## XVI. COCKPIT TÁC CHIẾN 3 GIÂY & ĐỒNG BỘ 100% REALTIME BRIDGE / JS (ADR-029)

1. **Thanh Chỉ Huy 3 Giây, Nhãn Tác Chiến Trực Quan & Bố Cục 2 Tầng Flexbox (`src/hud/html_dashboard.py`):**
   - Thanh `#tactical-3s-command-bar` (4 thẻ: `cmd-regime-card`, `cmd-wall-card`, `cmd-flow-card`, `cmd-action-card`) nằm ngay dưới `.cockpit-stage` (`order: 1` -> `order: 2`), giải đáp tức thời Regime (`ƯU TIÊN ĐÁNH ĐẢO CHIỀU (GEX +)` / `ƯU TIÊN ĐÁNH THUẬN CHIỀU (GEX -)` / `CHỜ XÁC NHẬN (CHUYỂN PHA)`), tường gần nhất + Air Pocket, áp lực VPIN/BVC/Siege và kèo `[KÍCH HOẠT]` tối ưu.
   - 4 dòng `KHỐI 6` & Ô 4 Command Bar chuẩn hóa nhãn Kiểu 2 đồng bộ Python/JS: `1. THUẬN CHIỀU BUY (Phá cản)`, `2. ĐẢO CHIỀU SELL (Chạm cản)`, `3. ĐẢO CHIỀU BUY (Chạm sàn)`, `4. THUẬN CHIỀU SELL (Thủng sàn)`.
   - CSS Flexbox `order` trên `.container` đưa `KHỐI 4 Spine` (`order: 3`) và `KHỐI 6` mở sẵn (`<details open>`, `order: 4`) lên ngay dưới Command Bar, trong khi gói gọn `Pinning` (`order: 6`), `KHỐI 1 Smile` (`order: 7`), `KHỐI 3 KPI` (`order: 8`), `KHỐI 5 Orderflow` (`order: 9`), `KHỐI 7 Glossary` (`order: 10`) vào `<details class="table-box drawer-box">` đóng mặc định mà vẫn bảo toàn bất biến thứ tự HTML (`pos_smile < pos_micro < pos_kpi < pos_orderflow < pos_strategy < pos_glossary`).
2. **Động cơ JS Parity 100% ADR-028 & Sửa Lỗi Live Polling (`src/hud/neiro_terminal.py`):**
   - Sửa 4 tham chiếu `currentTfKey` -> `currentTf` trong vòng polling `pollLiveYahooChart` để khôi phục đồng bộ realtime `GC=F`.
   - Triển khai các hàm JS thuần đồng bộ 1:1 với lõi Python: `computeLiveVpinBvcJs` (phân tán nền `candles[:-6]` + 5 equal-volume buckets có triệt tiêu dấu và nội suy `percentileSortedJs`), `computeM5AtrJs`, `resolveAdaptiveStrikesJs`, `sizeXauusdJs`, `computeTacticalMatrixJs`, `updateRealtimeTacticalCockpit` và `updateSyncBadgeHonest` (`LIVE BRIDGE (2.5s)` / `CLOUD SYNC (LIVE)` / `OFFLINE SNAPSHOT` / `CME GLOBEX: CLOSED (SETTLED)`).
   - Mỗi tick/nến mới tự động cập nhật lại Command Bar 3s, các khoảng cách trên `KHỐI 4 Spine`, 4 dòng `KHỐI 6` (`k6-row-{sq,fd,rb,bd}`), HUD nổi 5 dòng (`540px` / `.expanded 700px`), gỡ Top-Center Gauge đè chart và hỗ trợ toggle `Lớp phủ: Tinh gọn / Đầy đủ` (`#btn-overlay-mode` & `syncSecondaryPriceLines()`), kèm nhãn Chart/Tooltip bình dân (`CHEX · HÚT GIÁ VỀ ĐÂY`, `VEX · VÙNG BẬT / GIẬT SÓNG`, `-> GEX (+): Đánh ĐẢO CHIỀU` / `-> GEX (-): Đánh THUẬN CHIỀU`).
3. **Mở Rộng Payload Cầu Nối Realtime (`src/hud/html_dashboard.py`):**
   - Helper dùng chung `_compute_live_microstructure_payload(tape)` cấp trực tiếp `vpin_pct`, `vpin_label`, `bvc_buy_pct`, `bvc_cvd_contracts`, `kyle_lambda_label`, `atr_5m` cho `/api/yahoo_gc`, `_run_lightweight_live_tick()` và `version.json`, kết hợp trường adaptive strike mới trong `meta` (`next_above`, `next_below`, `step`, `major_up_wall`, `major_down_wall`, `has_up_air_pocket`, `has_down_air_pocket`, `atr_5m`).



