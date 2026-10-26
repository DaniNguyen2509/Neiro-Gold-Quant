# Neiro-Quant — TÀI LIỆU KIẾN TRÚC HỆ THỐNG ĐỊNH LƯỢNG (QUANT ARCHITECTURE)

> **Phiên bản:** v2.4 — 26/10/2026 (Adaptive Micro-Strike Guard, Stale Options Detection, Auto-Sync Pipeline & Multi-Tier Data Armor)  
> **Project:** Neiro-Quant (Hệ thống Định lượng Options Flow, GEX, DEX, Vanna, Charm & Market Microstructure)  
> **Tài sản mục tiêu:** Vàng CME Futures (`GCZ26` / `GC=F`) & COMEX Gold Options.  
> **Tài liệu chuẩn đối chiếu:** [spec.md](spec.md), [TRADER_PLAYBOOK.md](TRADER_PLAYBOOK.md), [HUONG_DAN_INDICATORS_MT5_TRADINGVIEW.md](HUONG_DAN_INDICATORS_MT5_TRADINGVIEW.md), [thuat_ngu_quant.md](thuat_ngu_quant.md), [ADR-007 (Zero Gamma)](decisions/ADR-007-zero-gamma-flip-and-wall-siege-velocity.md), [ADR-008 (Multi-Expiry GEX)](decisions/ADR-008-multi-expiry-gex-and-gamma-weighted-walls.md), [ADR-009 (Volatility Smile SVI)](decisions/ADR-009-volatility-smile-and-skew-microstructure-invariants.md), [ADR-010 (Multi-Tier Data Armor)](decisions/ADR-010-multi-tier-data-armor-and-self-healing-architecture.md) & [ADR-011 (Adaptive Micro-Strike Guard & Stale Detection)](decisions/ADR-011-adaptive-micro-strike-guard-and-stale-options-detection.md)

---

## I. MỤC TIÊU CỐT LÕI & TRIẾT LÝ VẬN HÀNH (FIRST PRINCIPLES)

Thị trường tài chính phái sinh (Futures & Options) được chi phối bởi cấu trúc phòng hộ (Hedging Mechanics) của các Nhà tạo lập thị trường (Market Makers - MMs / Dealers).  
Hệ thống **Neiro-Quant** được xây dựng không phải để đoán mò đỉnh đáy theo các chỉ báo kỹ thuật trễ thông thường (RSI, MACD, MA...), mà nhằm giải quyết các bài toán định lượng:

1. **Định vị chính xác các chốt chặn thực sự của dòng tiền lớn:**
   - Các bức tường quyền chọn: Call Wall, Put Wall, Absolute Gamma Strike, ATM Realtime Pivot, ±1.0σ & ±0.85σ Implied Bands.
   - Định vị 100% thuần theo Giá tương lai CME Gold Futures Realtime (`GC=F`), khóa chặt trục ATM theo bảng điện trực tiếp.
   - **Quy tắc khóa OTM Dealer Walls:** Call Wall bắt buộc là OTM Call ($strike \ge spot$), Put Wall bắt buộc là OTM Put ($strike \le spot$), triệt tiêu hoàn toàn rủi ro lấy nhầm Strike ITM làm sàn/trần.
   - **Gamma-Weighted Wall Scoring (ADR-008):** Xếp hạng thành trì bằng $Power = OI \times \Gamma$ thay vì OI thô, phân loại rõ `[BOUNCE_WALL]` (Dealer Long Gamma pin/hỗ trợ) vs `[MAGNET_WALL]` (Dealer Short Gamma bẫy gia tốc xuyên thủng).
2. **Giải mã trạng thái động và kích hoạt kịch bản tức thì (6-Scenario Realtime Engine):**
   - Đánh giá trực tiếp trong thời gian thực hành vi của Market Maker theo 6 kịch bản (KB-1 đến KB-6):
     * **KB-1 (Giằng co nén biên độ):** MM ghìm giá ăn phế -> ĐỨNG NGOÀI.
     * **KB-2 (MM chặn bán):** MM bảo vệ trần Call -> SELL FADE.
     * **KB-3 (MM vỡ trận Short - Gamma Squeeze):** Vượt trần phòng hộ -> BUY BREAKOUT.
     * **KB-4 (MM đệm mua):** MM bảo vệ sàn Put -> BUY REBOUND.
     * **KB-5 (Thủng sàn & Xả lũ - Air Pocket Slide):** Rơi vào Air Pocket -> CẤM ĐỠ DAO / SELL BREAKDOWN.
     * **KB-6 (Vùng trung lập):** Chưa chạm mốc -> KIÊN NHẪN CHỜ.
   - **Giao diện ma trận chống hiểu lầm:** Thẻ chờ tín hiệu được làm mờ 55% opacity, viền xám tối, nhãn hành động mang đuôi `(Chưa áp dụng)`. Chỉ kích hoạt phát sáng khi giá thực tế chạm hoặc xuyên thủng ngưỡng.
   - **Quy tắc bất biến cho Take-Profit (Invariant Enforcement):** Đối với kịch bản Mean-Reversion (KB-2 & KB-4), khi mốc biên cản trùng với trục ATM, hệ thống tự động dội mục tiêu về biên đối diện (`strike_below` hoặc `strike_above`), luôn đảm bảo nghiêm ngặt $TP < Entry$ cho lệnh SELL và $TP > Entry$ cho lệnh BUY.
3. **Băng Giá & Xung Lực Volume M5 Realtime (Orderflow Pulse Radar):**
   - Theo dõi luồng nến M5 trực tiếp từ COMEX, tự động phát hiện Volume Spike ($Volume \ge 1.4 \times MA_{20}$ và $Volume \ge 350$ HĐ), loại bỏ tick ảo tức thời ($Volume \le 0$) và đối xứng hóa nhận diện vi mô: Hấp thụ đáy rút chân (`is_pinbar_bull`), Chặn bán đè đỉnh (`is_pinbar_bear`) và Đột biến giằng co lưỡng lự (`is_churn`). Fallback Đỉnh/Đáy ngày chuẩn hóa cực trị toàn phiên.
3. **Bảng Tác Chiến Tức Thì (Instant Action UI):**
   - Giúp trader trong 3 giây nắm bắt ngay hành động cụ thể (Action), điểm vào lệnh, cắt lỗ, chốt lời.
   - Tối giản chữ, tuyệt đối không dùng icon trang trí rườm rà.
4. **Vận hành độc lập 100% trên Cloud (Zero-Touch Cloud Automation):**
   - Hoạt động tự động 24/5 trên máy chủ đám mây (GitHub Actions). Không phụ thuộc vào laptop của người dùng, tự động cào dữ liệu, tính toán ma trận Greeks và xuất bản Web Terminal xem trực tiếp trên điện thoại.

---

## II. GIẢI MÃ CA LÂM SÀNG THỰC TẾ (CASE STUDY TỪ BIỂU ĐỒ ORDERFLOW)

Phân tích cấu trúc thực tế từ biểu đồ CME Gold / Orderflow / TrueVision Levels:

```
[4250.00]  ════ Call Wall • Max Call OI ════ (Trần nhà kiên cố của Market Maker)
                  │
[4225.00]  ────── Cửa Ải Kháng Cự Tiền Tuyến (Squeeze > 4227.5 -> MM vỡ trần Short -> Phóng lên 4250)
                  │
[4201.96]  ────── SPOT CME FUTURES (Giá tương lai cân bằng ngầm định via Put-Call Parity)
                  │
[4200.00]  ────── Sàn Đỡ Kỹ Thuật ATM (Đệm Put đỡ nến M5 rút chân)
                  │
                  ▼ ──► [CÚ ĐÂM THỦNG & TRƯỢT DÀI (LIQUIDITY VACUUM / AIR POCKET SLIDE)]
                        Bên dưới 4175 cạn kiệt OI (< 35% trung bình), Dealer buộc phải bán hedge
                        -> Giá trượt tự do không phanh qua 4150
                  ▼
[4100.00]  ════ Major Put Wall • Max Put OI ════ (Đáy bê tông cốt thép cuối cùng của MM)
```

**Bài học cấu trúc:**  
Nếu trader chỉ nhìn vào các đường hỗ trợ kháng cự vẽ tay mà bắt đáy tại các vùng rỗng thanh khoản (Air Pocket), trader sẽ bị quét sạch tài khoản trong cú trượt chân không thanh khoản. Hệ thống **Neiro-Quant** sinh ra để phát hiện trước **nguy cơ bị đâm thủng** và ngăn chặn lệnh bắt đáy tai hại đó.

---

## III. SƠ ĐỒ TOÀN CẢNH KIẾN TRÚC HỆ THỐNG (6 TẦNG ĐỘC LẬP)

```
                    ┌──────────────────────────────────────────────┐
                    │       BARCHART / CME OPTIONS FEED            │
                    │  (Weekly OG1..OG5 & Monthly GCZ Gold Options)│
                    └──────────────────────┬───────────────────────┘
                                           │ Playwright Chromium Cloud + Internal API Sniffer
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ [TẦNG 1: CLOUD COLLECTOR & AUTOMATION PIPELINE]                                        │
│  - Playwright Headless Chromium: Tự động chạy trên Ubuntu GitHub Actions.              │
│  - Internal API Interceptor: Bắt gói JSON /proxies/core-api/v1/options/get.            │
│  - Dynamic CME Rollover Engine: Tự động giải mã Front-Month Options theo CME Rule       │
│    120102.E (resolve_front_month_cme_option), tự động rollover (OGX26 -> OGZ26...).     │
│  - Multi-Expiry Resolver (ADR-008): Tự động quét cả Weekly (OG1..OG5) và Monthly.     │
│  - Dynamic Expiration & DTE: Trích xuất expirationDate từ sàn, tính DTE chính xác.     │
│  - Lưới Cron thích ứng 2 mùa: 07:15 VN (Chốt OI), London 2 nấc (12:30/13:30 & 14:30/15:30),│
│    18:45 VN (Pre-US) & 19:45 đến 23:45 VN (Đón đầu phiên New York & London Fix).           │
│  - Real-Time Dual-Feed Engine (ADR-005): Tự động kéo giá CME Futures (yfinance GC=F)     │
│    kết hợp Spot Gold (Gold-API/Binance PAXG), tính toán Dynamic Basis Contango [5, 32] USD.│
│  - Lưu trữ CSV: data/options_prices_GCZ26.csv tự động commit vào repository.           │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ [TẦNG 2: QUANT ENGINE & GREEKS CORE (CÔNG THỨC TOÁN HỌC)]                              │
│  - black76.py: Mô hình Black-76 cho Options on Futures (Call, Put, d1, d2).            │
│  - iv_solver.py: Giải ngược Implied Volatility (Newton-Raphson + Brent fallback).      │
│  - loader.py (Multi-Expiry Superposition): aggregate_options_dataframes xếp chồng     │
│    tuyến tính Greeks giữa Weekly & Monthly, triệt tiêu điểm mù OI thô.                 │
│  - dealer.py: Gamma-Weighted Wall Scoring (Power = OI * Gamma), Wall Regime             │
│    Classification ([BOUNCE_WALL] vs [MAGNET_WALL]), Zero Gamma Solver (_brentq),       │
│    Wall Siege Ratio (compute_wall_siege_ratio), Dealer Net Delta Position.             │
│  - Put-Call Parity Implied Spot: S_Implied = K_ATM + exp(r*T)*(C_ATM - P_ATM).         │
│  - Liquid Strike Weighting: Lọc mốc ATM thực theo Open Interest và Volume thanh khoản. │
│  - advanced_greeks.py: Net VEX ($M/1% IV - Vanna) & Net CHEX ($M/ngày - Charm).        │
│  - expected_move.py: Biên độ 1-Sigma (Straddle / 0.7979) & Intraday Rule of 16.        │
│  - institutional.py: 25Δ Risk Reversal (RR25), Butterfly (BF25), Volatility-Targeted   │
│    Position Sizing với GEX Regime Scaler & CTA 20-Day Momentum Confluence.             │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ [TẦNG 3: CLOUD TACTICAL TERMINAL & STATIC HOSTING (FRONTEND)]                          │
│  - html_dashboard.py: Render độc lập file Plotly HTML Dark Mode cao cấp.               │
│  - 100% Pure CME Gold Futures Engine: Định vị chuẩn xác theo giá COMEX GC=F / GCZ26,   │
│    loại bỏ hoàn toàn cơ chế lấy Spot Gold (Gold-API/Binance PAXG) và hiệu chỉnh Basis. │
│    Triệt tiêu 100% hiện tượng sai lệch giá và báo động giả.                             │
│  - 7 Thẻ KPI Thống Kê: Spot CME, Net GEX Regime, Sổ Sách Dealer (Net Delta / DEX),     │
│    Zero Gamma Flip ($S*) & Wall Siege, Expected Move, Greeks Bậc 2, 25Δ Skew.          │
│  - Gamma-Weighted Walls & Regimes: Plotly Panel 1 vẽ nhãn [BOUNCE PIN] / [MAGNET TRAP], │
│    Visual Level Spine hiển thị Gamma Power & Siege Ratio, Tactical Table cấm Limit      │
│    bắt dao rơi tại Magnet Wall.                                                        │
│  - Plotly Panel 2: Trực quan hóa thanh Net Delta Bar (HĐ GC) và Hover Tooltip chi tiết │
│    Call/Put/Net contracts từng Strike.                                                 │
│  - Đường Zero Gamma Flip ($S*): Vẽ trực quan trên Panel 1, đánh dấu ranh giới đảo chiều.│
│  - Visual Level Spine: Thước đo vị trí giá tích hợp tỷ lệ Siege tại Call/Put Wall.     │
│  - Institutional Pinning Radar: Cảnh báo tự động hiện tượng Neo giá (Pinning Box).     │
│  - CTA Momentum Confluence Banner: Cảnh báo bứt phá đồng pha giữa Quỹ & Dealer.        │
│  - Chế độ Compact Tactical View: Giới hạn dải strikes tác chiến thực tế (từ 1 strike dưới Put Wall đến 1 strike trên Call Wall, tối đa 22 strikes quanh ATM), loại bỏ hoàn toàn vùng chết xa xôi giúp biểu đồ gọn gàng, thanh bar dày dặn và trực quan.│
│  - Adaptive Bar Widths: Bề dày thanh bar tự động thích ứng theo bước giá (chiếm 72% khoảng trống), triệt tiêu hiện tượng thanh mỏng dính như sợi chỉ.│
│  - Tickmode Array & Chống Đè Chữ: Trục Y chỉ hiển thị nhãn cho các strikes thực có trong dữ liệu (triệt tiêu 100% hiện tượng 120 nhãn đè nát chữ).│
│  - Pinned Macro Badges: Ghim huy hiệu Zero Gamma Flip hoặc Walls ở mép trên/dưới khi nằm ngoài khung ngắm mà không làm méo mó dải chiến thuật.│
│  - Adaptive Micro-Strike Guard (ADR-011): Tự động phát hiện khoảng trống bước giá vi mô $5.0 (Fine Strike Gap) trong hợp đồng cận đáo hạn (DTE <= 10). Tự động kích hoạt cản trên vi mô Fine Strike Above ($4,030 thay vì $4,050 khi giá $4,027.5), đảm bảo kịch bản KB-3 Buy Squeeze kích hoạt chuẩn xác từng tick.│
│  - Stale Options Data Detection & Header Warning Badge (ADR-011): Tự động tính toán tuổi file CSV (file_age_hours). Nếu > 6h, hiển thị cảnh báo đỏ trên UI Header và console.│
│  - Quick Zoom Preset Buttons: 3 nút chuyển chế độ nhanh trên thanh công cụ Plotly: [🛡️ Thành Trì MM] (Mặc định), [🎯 Scalping Tinh Gọn (ATM ± $50)], [🌐 Toàn Cảnh (Macro Range)].│
│  - GitHub Pages Hosting: Xuất bản tự động ra https://daninguyen2509.github.io/Neiro-Quant/ │
│  - Artifacts Storage: Lưu trữ bản build 7 ngày trên GitHub Actions.                    │
│  - Zero Laptop Dependency: Người dùng xem trực tiếp trên điện thoại ở bất kỳ đâu.      │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ [TẦNG 4: MICROSTRUCTURE & LEVEL STATE ENGINE] (src/quant_engine/level_state.py)        │
│  - Giám sát tương tác giữa Giá Real-time và từng Level (State Machine hoàn thiện):     │
│      * DORMANT: Cách xa > 5.0 pts (Chưa tiếp cận).                                     │
│      * TESTING / TRIGGERED: Khoảng cách <= 2.0 pts (Đang chạm chốt chặn).              │
│      * ABSORPTION_DEFENDED: Net GEX (+) + Hấp thụ cạn kiệt -> Tín hiệu FADE REVERSAL.  │
│      * SLICED_VACUUM_RUN: Thủng Level + Phía sau là Air Pocket + Net GEX (-)           │
│        -> Tín hiệu BREAKOUT RUNNER (Cảnh báo CẤM ĐỠ DAO, Target về Major Wall tiếp theo)│
│  - Tự động tích hợp vào Radar Vi Mô và Bảng Tác Chiến Scalping trong HTML Terminal.   │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
                      ┌────────────────────┴────────────────────┐
                      ▼                                         ▼
┌─────────────────────────────────────────┐ ┌────────────────────────────────────────────┐
│ [TẦNG 5: STRATEGY & RISK MATRICES]      │ │ [TẦNG 6: REAL-TIME BASIS & BROKER BRIDGE]  │
│  - Bảng 1: Intraday Scalping (Ăn 20-25$)│ │  - Auto-Basis Sync: Live Gold-API & Binance│
│    Entry, Hard SL, TP, Vol-Target Lot   │ │  - Plausibility Band [21, 27] USD           │
│  - Bảng 2: Structural Swing Walls       │ │  - Calibrated Contango Anchor (-24.00 USD) │
│    Bắt đáy Put Wall / Bán đỉnh Call Wall│ │  - MetaTrader 5 Connector (Pepperstone)     │
│  - CTA 20-Day Momentum Confluence       │ │  - MT5 Indicator: Neiro-Quant-Overlay.mq5   │
└─────────────────────────────────────────┘ └────────────────────────────────────────────┘
```

---

## IV. CƠ CHẾ LƯỚI CRON THÍCH ỨNG 2 MÙA (DUAL-SEASON CLOUD PIPELINE)

Do thị trường tài chính thế giới (London & New York) chuyển đổi qua lại giữa **Giờ mùa hè (Daylight Saving Time - EDT/BST)** và **Giờ mùa đông (Standard Time - EST/GMT)**, hệ thống áp dụng Lưới Cron đa tầng chạy theo giờ UTC tuyệt đối:

```yaml
on:
  schedule:
    # 1. Chốt Open Interest ngày mới từ CME Clearing: 00:15 UTC = 07:15 VN
    - cron: '15 0 * * 1-5'
    # 2. Phiên Âu 2 nấc thích ứng cả 2 mùa (Pre-Europe & In-Session Europe):
    #    05:30 UTC = 12:30 VN (Pre-Europe Mùa Hè: trước Frankfurt 13:00 và London 14:00)
    #    06:30 UTC = 13:30 VN (Pre-Europe Mùa Đông: trước Frankfurt 14:00 và London 15:00)
    #    07:30 UTC = 14:30 VN (In-Session Europe Mùa Hè: sau mở cửa London 30 phút)
    #    08:30 UTC = 15:30 VN (In-Session Europe Mùa Đông: sau mở cửa London 30 phút)
    - cron: '30 5,6,7,8 * * 1-5'
    # 3. Phiên Mỹ đón đầu tin tức vĩ mô (18:45 VN) và giờ cao điểm NYSE / London Fix:
    #    11:45 UTC = 18:45 VN (Pre-US: trước tin CPI/NFP 19:30 hè / 20:30 đông 45 phút)
    #    12:45, 13:45, 14:45, 15:45, 16:45 UTC (19:45, 20:45, 21:45, 22:45, 23:45 VN)
    - cron: '45 11,12,13,14,15,16 * * 1-5'
```

* **Phiên Á:** Chốt toàn bộ dữ liệu vị thế Open Interest (OI) của ngày hôm trước từ CME Clearing lúc 07:15 VN để định hình khung Asian Range.
* **Phiên Âu (2 nấc):** Cào nấc 1 (12:30 / 13:30 VN) để lên bản đồ tác chiến trước giờ G (Pre-Europe Radar). Cào nấc 2 (14:30 / 15:30 VN) để cập nhật Greeks và dịch chuyển Gamma sau khi dòng tiền London hấp thụ.
* **Phiên Mỹ:** Đón đầu trước tin vĩ mô lúc 18:45 VN, sau đó chạy đều mỗi 1 tiếng bao trọn giờ mở cửa sàn chứng khoán New York (NYSE) và đợt chốt sổ London Fix (00:00 VN).
* **Hạn mức tài nguyên:** 11 lần chạy/ngày $\times$ 1.5 phút $\approx$ **360 phút/tháng** (chỉ chiếm ~18% hạn mức 2,000 phút miễn phí của GitHub Actions, 100% miễn phí).

---

## V. CƠ CHẾ STATE MACHINE CHO TỪNG LEVEL (LEVEL STATE ENGINE)

Mỗi đường Level được hệ thống theo dõi 24/7 theo chu trình trạng thái khép kín:

```mermaid
stateDiagram-v2
    [*] --> DORMANT: Khoảng cách > 5.0 pts
    DORMANT --> TRIGGERED: Giá tiếp cận trong phạm vi <= 2.0 pts
    
    TRIGGERED --> ABSORPTION_DEFENDED: Net GEX (+) VÀ Delta Exhaustion VÀ Không có Air Pocket
    TRIGGERED --> SLICING_RISK: Net GEX (-) HOẶC Cụm Delta bán/mua áp đảo dội xuống
    
    SLICING_RISK --> SLICED_VACUUM: Giá xuyên qua Level > 1.5 pts VÀ Phía sau là Air Pocket
    SLICING_RISK --> ABSORPTION_DEFENDED: Xuất hiện Passive Limit Order hấp thụ thành công
    
    ABSORPTION_DEFENDED --> TARGET_REACHED: Đảo chiều thành công chạm ATM Pivot / Target
    SLICED_VACUUM --> NEXT_WALL_REACHED: Trượt hết Air Pocket tới Major Wall kế tiếp
    
    TARGET_REACHED --> DORMANT
    NEXT_WALL_REACHED --> DORMANT
```

### 1. Trạng thái `DORMANT` (Chờ kích hoạt)
- Giá hiện tại cách Level > 5.0 USD (với Gold).
- Level đóng vai trò là mốc định hướng trên bản đồ thanh khoản lớn.

### 2. Trạng thái `TRIGGERED / TESTING` (Đang tiếp cận & thử thách)
- Giá chạm vào phạm vi đệm `[Level - 2.0, Level + 2.0]`.
- Hệ thống kích hoạt radar phân tích vi mô:
  - Kiểm tra Net GEX tại Strike (Dương hay Âm?).
  - Đo tốc độ nến và khối lượng giao dịch dồn tụ.

### 3. Trạng thái `ABSORPTION_DEFENDED` (Chốt chặn trụ vững)
- **Điều kiện kích hoạt:**
  1. Net GEX tại Strike mang giá trị **DƯƠNG (+GEX)**: Dealer đóng vai trò đè nén dao động.
  2. Nến M5 rút chân trở lại vào trong vùng cản (Passive Absorption).
  3. Delta suy kiệt.
- **Quy tắc vào lệnh (Fade Reversal):**
  - **Entry:** Vào lệnh khi nến M1/M5 đóng cửa rút chân trở lại vào trong vùng cản.
  - **Stop Loss (SL):** Đặt cách mép ngoài của chốt chặn **1.5 - 2.5 giá**.
  - **Take Profit (TP):** Trục cân bằng ngầm định `S_Implied` (ATM Pivot) hoặc mốc cản đối diện.

### 4. Trạng thái `SLICED_VACUUM_RUN` (Chốt chặn bị đâm thủng - Trượt dốc)
- **Điều kiện kích hoạt:**
  1. Giá đóng cửa xuyên thủng qua Level > 1.5 giá.
  2. Phía sau Level là một **Air Pocket (Vùng rỗng thanh khoản)** có OI mỏng (< 35% trung bình).
  3. Net GEX mang giá trị **ÂM (-GEX)**: Dealer bị ép bán tháo phòng hộ.
- **Quy tắc ứng xử & Vào lệnh (Breakout Runner):**
  - **Lệnh cấm tối cao:** **TUYỆT ĐỐI KHÔNG BẮT ĐÁY / KHÔNG ĐỠ DAO**.
  - **Entry:** Đánh theo đà phá vỡ (Breakout Entry) ngay khi xác nhận nến đóng ngoài Level.
  - **Stop Loss (SL):** Đặt ngay phía trên Level vừa bị thủng 1.0 - 1.5 giá.
  - **Take Profit (TP):** Biên trên của Bức tường OI/GEX dày tiếp theo (Ăn trọn khoảng chân không Air Pocket).

---

## VI. BẢNG THÔNG SỐ CẤU HÌNH HỆ THỐNG (SETTINGS SPECIFICATION)

| Thông số | Giá trị | Ý nghĩa kỹ thuật |
|---|---|---|
| `underlying_symbol` | `GCZ26` / `GC` | Mã hợp đồng tương lai vàng CME |
| `spot_symbols` | `XAUUSD`, `XAUUSDc`, `XAUUSD-F` | Mã tài sản giao dịch trên sàn MT5 |
| `multiplier` | `100` | 100 troy oz mỗi CME Gold Contract |
| `risk_free_rate` | `0.045` (4.5%) | Lãi suất phi rủi ro chuẩn định giá Black-76 |
| `dte_days` | `38.0` | Số ngày còn lại tới ngày đáo hạn hợp đồng |
| `proximity_threshold` | `2.0` | Ngưỡng $ kích hoạt trạng thái TESTING |
| `breakout_threshold` | `1.5` | Ngưỡng $ xác nhận xuyên thủng Level |
| `air_pocket_threshold` | `< 0.35` | Tỷ lệ OI so với trung bình để định danh Air Pocket |
| `web_terminal_url` | `https://daninguyen2509.github.io/Neiro-Quant/` | Địa chỉ Web Terminal mở trên điện thoại |

---

## VII. CƠ CHẾ QUẢN TRỊ VỊ THẾ & DÒNG TIỀN QUỸ HEDGE FUND (INSTITUTIONAL QUANT MECHANISMS)

Để hoàn thiện hệ sinh thái định lượng chuẩn quỹ phòng hộ (Hedge Fund Standards), hệ thống tích hợp 3 cơ chế toán học vi mô:

### 1. 25-Delta Risk Reversal ($RR_{25}$) & Butterfly ($BF_{25}$) Volatility Skew
- **Cơ sở học thuật:** Quỹ đầu cơ và định chế tài chính hiếm khi nhìn giá quyền chọn trực tiếp mà theo dõi **Mặt cong biến động ẩn (Volatility Smile / Skew)** thông qua các mốc độ nhạy Delta chuẩn: $\Delta = +0.25$ (Call OTM) và $\Delta = -0.25$ (Put OTM).
- **Risk Reversal ($RR_{25}$):** Đo lường độ lệch định hướng (Directional Bias) của dòng tiền lớn:
  $$RR_{25} = IV(\text{Call}_{25\Delta}) - IV(\text{Put}_{25\Delta})$$
  - Khi $RR_{25} > +0.5\%$: **BULLISH CALL SKEW** — Quỹ chấp nhận trả phí cao (vol premium) gom Call OTM cược vàng phá đỉnh, bảo vệ kịch bản tăng tốc.
  - Khi $RR_{25} < -0.5\%$: **BEARISH PUT SKEW** — Quỹ dồn tiền mua Put OTM phòng hộ rủi ro đuôi (Tail Risk) hoặc cược đảo chiều giảm mạnh.
- **Butterfly ($BF_{25}$):** Đo lường độ cong mặt cười (Smile Curvature / Tail Fatness):
  $$BF_{25} = \frac{IV(\text{Call}_{25\Delta}) + IV(\text{Put}_{25\Delta})}{2} - IV(\text{ATM})$$
  - Giá trị $BF_{25}$ càng cao cảnh báo thị trường định giá rủi ro sự kiện bất ngờ (Black Swan Event) có xác suất xảy ra cao hơn phân phối chuẩn Gauss.

### 2. Quản Trị Vị Thế Volatility-Targeted Sizing Kết Hợp GEX Regime Cho MT5 XAUUSD
- **Công thức tính Lot quy chuẩn:**
  $$\text{Base Lots} = \frac{\text{Equity} \times \text{Risk\%} / 100}{100 \times \text{SL USD}}$$
  *(Ví dụ: Tài khoản \$10,000, rủi ro 1% = \$100, Stop Loss \$4.5 CME $\Rightarrow \text{Base Lots} = \frac{100}{100 \times 4.5} = 0.22$ Lot).*
- **Bộ điều tiết Regime Dealer (GEX Regime Multiplier):**
  - **Long Gamma Regime ($1.0\times$ Multiplier):** Thị trường dao động ổn định trong biên độ hẹp (Mean Reversion), Dealer mua thấp bán cao dập tắt biến động $\Rightarrow$ Giữ nguyên 100% Volume mục tiêu.
  - **Short Gamma Regime ($0.5\times$ Multiplier):** Thị trường biến động cực đại và dễ sụp đổ dây chuyền, Dealer buộc phải bán tháo khuếch đại đà rơi $\Rightarrow$ Tự động **cắt giảm 50% khối lượng** (ví dụ từ 0.22 Lot xuống 0.11 Lot) để bảo toàn vốn trước hiện tượng giãn spread và trượt giá (Slippage).

### 3. CTA Momentum Breakout Confluence (Hợp Lưu Quỹ Xu Hướng 20 Phiên)
- Theo dõi ngưỡng bứt phá Donchian 20 phiên (20-Day High / Low) của các quỹ CTA (Commodity Trading Advisors).
- Khi **20D Breakout High $\ge$ Call Wall**: Kích hoạt trạng thái `SUPER_SQUEEZE_CONFLUENCE`. Tại đây xảy ra hiệu ứng cộng hưởng kép (Double Squeeze): Quỹ CTA ồ ạt kích hoạt thuật toán mua gom theo xu hướng + Dealer Short Gamma bị chạm ngưỡng stop loss buộc phải vào lệnh Long Futures phòng hộ $\Rightarrow$ Cú đẩy giá vượt bậc.

### 4. Volatility Smile & Skew Microstructure Invariants (Chi Tiết Tại ADR-009)
Thiết lập 3 bất biến vi cấu trúc dựa trên hình thái đường cong nụ cười biến động $IV(K)$:
- **Bất biến 1: "Tâm Bão" (Sweet Spot / Pinning Center):** Đáy thấp nhất của đường cong $IV$ (nơi $IV$ chạm đáy và $IV$ Skew xấp xỉ $0\%$ quanh ATM). Vùng hội tụ Long Gamma + Long Vanna tối đa của Dealer, MM có động cơ tài chính cao nhất để ghìm giá vàng đứng yên thu phí Theta. Kích hoạt trạng thái **Sideway / Mean-Reversion**.
- **Bất biến 2: "Hố Đen Giảm Tốc" (Bức Tường Thật / Skew Dip):** Vết lõm sâu bất thường của Skew tại mức cản (ví dụ Put Skew âm sâu $-4.6\%$ đến $-8.8\%$ tại $4,045 - $4,050). Minh chứng MM đang chủ động **bán đè quyền chọn (Short Vega)** để xây đập ngăn lũ $\Rightarrow$ **Điểm đặt lệnh Limit đánh đảo chiều (Bounce) an toàn nhất!**
- **Bất biến 3: "Bẫy Thuốc Nổ" (Mép Vểnh / Volatility Squeeze Trap):** Vùng hai cánh vểnh dốc đứng của nụ cười ($IV$ Skew dương cao vọt $> +6.0\%$). Nếu giá phá vỡ tường cản và lọt vào mép vểnh, MM rơi vào Short Gamma hoảng loạn và buộc phải mua/bán đuổi Futures phòng hộ, tạo bão giá gia tốc $\Rightarrow$ **VÙNG BẮT BUỘC ĐẶT STOP LOSS, CẤM BẮT ĐỈNH/ĐÁY LIMIT!**

**Giao diện Tactical HUD (Chart-First Top-to-Bottom Sequence):**
Hệ thống thiết lập Panel độc lập toàn màn hình hiển thị trực quan Đường cong Nụ cười Biến động (`build_volatility_smile_figure`), đặt lên vị trí đầu tiên của Dashboard, tiếp nối bởi Biểu đồ 3 Panel vi mô mặc định tinh gọn, 7 Thẻ KPI toàn cảnh, thước đo Level Spine & Băng giá M5, và đưa toàn bộ Bảng tác chiến & Ma trận 6 kịch bản xuống nửa dưới trang web để tối ưu hóa quy trình phân tích định lượng trước khi đọc lệnh.

---

## VIII. QUY ĐỊNH BẢO TỒN DUNG LƯỢNG & HIỆU NĂNG (ZERO-WASTE MANDATE)

1. **Chuẩn dung lượng siêu nhẹ:** Toàn bộ repository luôn được duy trì < 15MB.
2. **Loại bỏ hoàn toàn rác tạm:** Mọi file cào tạm thời, script scratch, file log thử nghiệm phải bị xóa sạch ngay sau khi hoàn thành.
3. **Cloud-First:** Tính toán hoàn toàn trên đám mây, không cài đặt dữ liệu nặng vào ổ cứng của người dùng.
4. **Không phụ thuộc Laptop:** Toàn bộ luồng sinh dữ liệu và xuất bản giao diện vận hành trơn tru ngay cả khi laptop tắt nguồn.

---

## IX. KIẾN TRÚC BẢO VỆ BỘ NHỚ & CHỐNG RÒ RỈ RAM (ZERO-LEAK MEMORY ARCHITECTURE)

Khi trader chạy Live Terminal trên máy local trong nhiều giờ (hoặc cả ngày giao dịch 8-12 tiếng), hệ thống áp dụng cơ chế bảo vệ kép cho cả Backend Python và Frontend Browser:

### 1. Phía Trình Duyệt Web (Frontend DOM & History Stack Protection):
- **Triệt tiêu tích lũy History Stack:** Sử dụng `window.location.replace(...)` thay cho `window.location.href = ...`. Trình duyệt không bao giờ đẩy URL mới vào ngăn xếp lịch sử (`window.history.length` giữ nguyên là 1). Điều này ngăn chặn việc trình duyệt (Chrome/Edge) lưu lại hàng nghìn snapshot DOM gây tràn RAM sau 8 tiếng.
- **Nút "Dọn RAM & Cache":** Cho phép trader chủ động xóa sạch `caches`, `sessionStorage`, `localStorage` và nạp lại trang sạch sẽ chỉ bằng 1 cú nhấp chuột.
- **Đóng băng danh sách M5:** Giới hạn bảng nến M5 hiển thị tối đa 30 cây nến gần nhất (`m5_candles[-30:]`), triệt tiêu việc DOM phình to theo thời gian.

### 2. Phía Python Backend (Zero-Waste Engine):
- **Thu hồi rác chủ động (`gc.collect()`):** Giải phóng tường minh các đối tượng đồ họa nặng Plotly (`go.Figure`) và Pandas DataFrames ngay sau khi ghi file HTML.
- **Xóa cache điểm giá (`clear_spot_cache()`):** Xóa bộ đệm giá sau mỗi chu kỳ lặp để đảm bảo không tồn đọng tham chiếu cũ.
- **Giám sát RAM thời gian thực (Native Win32):** Sử dụng `GetProcessMemoryInfo` (qua Windows API `kernel32` & `psapi`) để theo dõi chính xác Working Set RSS trong console (`Iteration #N | RAM: XX.X MB`) mà không cần cài đặt thêm thư viện nặng ngoài chuẩn (`psutil`).
- **Tự động dọn rác định kỳ:** Cứ mỗi 20 chu kỳ lặp (hoặc khi gọi `--clear-cache`), hệ thống tự động quét và xóa sạch mọi file tạm `.tmp`, `.bak`, `.log` trong `scratch/` và `logs/`.
- **Khởi chạy tiện lợi 1-Click (`Chay_Live_Terminal.bat`):** Cung cấp bộ menu điều khiển trực quan bằng tiếng Việt: mở Live Terminal 15s/lần, dọn dẹp cache, cập nhật snapshot 1 lần hoặc thoát sạch sẽ không để lại tiến trình chạy ngầm.

---

## X. KIẾN TRÚC PHÒNG VỆ DỮ LIỆU ĐA TẦNG & TỰ ĐỘNG CHỮA LÀNH (MULTI-TIER DATA ARMOR & SELF-HEALING)

Để triệt tiêu hoàn toàn sự cố gián đoạn hoặc sai lệch số liệu khi các trang cào dữ liệu bên ngoài (như Barchart) gặp lỗi, bảo trì hoặc bật tường lửa bot (Cloudflare / AWS WAF Challenge), Neiro-Quant áp dụng mô hình Phòng vệ 4 Lớp Độc lập (4-Layer Armor):

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       4-LAYER ZERO-BREAK DATA ARMOR                         │
├─────────────────────────────────────────────────────────────────────────────┤
│ [LỚP 1: INGESTION GUARD]                                                    │
│  - Kiểm định biên dải Strike: Bắt buộc len >= 10, min <= 3800, max >= 4200. │
│  - Kiểm tra Total Open Interest > 0 (chống file rác 1 dòng, file trống).    │
│  - Nếu không đạt chuẩn: Scraper HỦY THAO TÁC GHI ĐÈ, bảo tồn file gốc.      │
├─────────────────────────────────────────────────────────────────────────────┤
│ [LỚP 2: RUNTIME SELF-HEALING FALLBACK]                                      │
│  - Tại html_dashboard.py: Tự động so sánh dải strike với giá Spot thực tế. │
│  - Nếu file bị lỗi/lệch > 200$: Tự động nạp Near-The-Money -> Nạp Google    │
│    Drive Mirror -> Nạp Benchmark GCZ26 nội tại.                             │
│  - Đảm bảo Terminal KHÔNG BAO GIỜ bị sập hay hiển thị cản âm.               │
├─────────────────────────────────────────────────────────────────────────────┤
│ [LỚP 3: CI/CD AUTO-REVERT PIPELINE]                                         │
│  - Trong daily_options_sync.yml: Chạy python test tính toàn vẹn sau khi cào.│
│  - Nếu Barchart trả về WAF Challenge: Tự động `git checkout` khôi phục data,│
│    tuyệt đối KHÔNG commit file hỏng lên kho mã nguồn.                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ [LỚP 4: DUAL-LAYER SEPARATION]                                              │
│  - Tầng 1: Giá CME Futures & Nến M5 chạy luồng REST độc lập (100% Realtime).│
│  - Tầng 2: Open Interest CME là cấu trúc vị thế tĩnh (chốt 07:15 VN).       │
│  - Đo lường áp lực nội phiên bằng Wall Siege Ratio (Volume / OI nền).       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## XI. KIẾN TRÚC BẢO VỆ BƯỚC GIÁ VI MÔ & TỰ ĐỘNG ĐỒNG BỘ CHUỖI OPTIONS (ADR-011)

### 1. Bản chất Lệch pha Vi cấu trúc (Microstructure Temporal & Spatial Mismatch)
1. **Lệch pha Thời gian (Temporal Mismatch):** Giá Futures COMEX (`GC=F`) nhảy realtime từng tick giây, trong khi chuỗi hợp đồng quyền chọn Options Chain (`data/options_prices_GCZ26.csv`) là dữ liệu tĩnh chốt theo ngày từ Clearing House. Nếu file CSV không được cập nhật mới trong ngày giao dịch, hệ thống sẽ tính toán các mốc cản dựa trên tập strike cũ.
2. **Lệch pha Không gian (Spatial & Strike Grid Mismatch):** Trong các hợp đồng cận ngày đáo hạn ($\text{DTE} \le 10$ ngày, đặc biệt là 1DTE - 5DTE), sàn COMEX mở thêm các mức giá thực hiện bước giá hẹp **$5.0** (Fine Strikes) quanh vùng ATM ($\pm 50$ USD). Ví dụ: `4005, 4010, 4015, 4020, 4025, 4030, 4035, 4040, 4045, 4050`.  
Nếu file dữ liệu cũ chỉ có bước giá chuẩn **$25.0**, khi giá chạy tới `4027.5`, thuật toán tìm strike trên sẽ nhảy vọt lên `4050.0`, hoàn toàn bỏ lọt chốt chặn nóng `4030.0`. Hệ quả là kịch bản `KB-3 (BUY BREAKOUT / GAMMA SQUEEZE)` bị trễ 20 giá, gây rủi ro bắt lệnh sai thời điểm cho trader.

### 2. Thuật toán Adaptive Micro-Strike Guard (`resolve_adaptive_tactical_strikes`)
Để giải quyết triệt để vấn đề này, hàm `resolve_adaptive_tactical_strikes()` trong `src/hud/html_dashboard.py` kích hoạt quy trình bảo vệ tự động:
- **Điều kiện kích hoạt:** Hợp đồng cận hạn ($\text{DTE} \le 10.0$ ngày) và khoảng cách từ giá Spot đến strike kế tiếp trong file CSV $> 5.0$ USD (phát hiện Fine Strike Gap).
- **Công thức giải Strike trên vi mô:**
  $$\text{Fine Strike Above} = \lceil \text{spot} / 5.0 \rceil \times 5.0$$
  *(Nếu $\text{Fine Strike Above} \le \text{spot}$, tự động cộng thêm $5.0$).*
- **Kích hoạt Guard:**
  - Thiết lập `strike_above = Fine Strike Above` (Ví dụ: `4,027.5` $\rightarrow$ `strike_above = 4,030.0`).
  - Thiết lập bước giá tác chiến vi mô `step = 5.0`.
  - Cân chỉnh biên độ tiếp giáp để tránh trùng lặp hoặc nhảy bậc:
    $$\text{next\_above} = \min(\text{next\_above}, \text{strike\_above} + 5.0)$$
    $$\text{next\_below} = \max(\text{next\_below}, \text{strike\_below} - 5.0)$$
- **Gắn nhãn nhận diện:** Gắn cờ `is_micro_guarded = True`, hiển thị nhãn `(VI MÔ)` trên Visual Level Spine và bảng kịch bản tác chiến để trader nhận biết rõ ràng.
- **Kích hoạt Kịch bản KB-3 Đúng Chuẩn:** Khi giá vượt $\text{strike\_above} + 1.5 = 4,031.5$, tín hiệu BUY SQUEEZE lập tức bùng nổ, không bị trễ đến $4,051.5$.

### 3. Cơ chế Giám sát Tuổi Dữ liệu (Stale Data Detection)
- Đo lường tuổi file CSV:
  $$\text{File Age (Hours)} = \frac{\text{Current Time} - \text{mtime}}{3600}$$
- Khi $\text{File Age} > 6.0$ giờ:
  * Backend Python xuất cảnh báo đỏ nổi bật trên Console: `[CẢNH BÁO NGUY HIỂM] File Options CSV đã cũ X giờ!`.
  * Dashboard Frontend tự động hiển thị Badge cảnh báo viền đỏ nhấp nháy trên Header:
    `⚠️ OPTIONS DATA CŨ (X.Xh) - CẦN CÀO MỚI`.

### 4. Cơ chế Tự Động Đồng Bộ Dữ Liệu Khi Khởi Chạy (Auto-Sync Scraper Pipeline)
Trong `Chay_Live_Terminal.bat` (Mục `[1] CHAY LIVE TERMINAL`), hệ thống tích hợp đoạn script kiểm tra tuổi file tự động:
- Nếu file `data/options_prices_GCZ26.csv` chưa tồn tại hoặc đã cũ hơn 6 giờ, batch script **tự động gọi Playwright Chromium cào 1 lần duy nhất** để lấy chuỗi Options mới nhất của ngày hôm nay trước khi bước vào vòng lặp 15s.
- Toàn bộ quá trình hoàn toàn tự động (Zero-Touch), trader chỉ cần nhấp chọn `[1]` là hệ thống tự đảm bảo dữ liệu mới nhất.
