# Spec: Neiro-Gold-Quant — Quantitative Gold Options Trading System & TradingView Fullscreen Realtime Terminal

> **Bản đặc tả kỹ thuật chi tiết (System Specification)**  
> **Tài sản mục tiêu:** 100% Pure COMEX Gold Futures (`GC` / `MGC` / `GC=F`) & SPDR Gold Shares (`GLD`) Options Proxy *(không tự ý quy đổi Spot CFD `XAUUSD`)*.  
> **Kiến trúc:** Cloud-Native Zero-Touch Automation (GitHub Actions + GitHub Pages, thuần Python, Zero-Waste < 15MB).  
> **Tài liệu tham chiếu:** [docs/architecture.md](architecture.md), [docs/decisions/ADR-018-tradingview-fullscreen-zero-tabs-and-realtime-tick-engine.md](decisions/ADR-018-tradingview-fullscreen-zero-tabs-and-realtime-tick-engine.md), [config/settings.toml](../config/settings.toml).

---

## 1. MỤC TIÊU HỆ THỐNG & TRIẾT LÝ VẬN HÀNH

Hệ thống **Neiro-Gold-Quant** được thiết kế để giải mã toàn diện cấu trúc vi mô thị trường (Market Microstructure), vị thế Dealer (Dealer Positioning) và áp lực dòng tiền quyền chọn (Options Flow) chuyên biệt cho thị trường Vàng thế giới:

1. **Thu thập Tự động (Cloud-Native Data Ingestion):**
   - Tự động bắt gói Options Chain CME Gold (GCZ26 / OG) từ Barchart qua Playwright Headless Chromium + Internal API Sniffer (`/proxies/core-api/v1/quotes/get` & `options/get`).
   - Tích hợp bộ thu thập Proxy ETF Vàng thanh khoản cao `GLD` (SPDR Gold Shares) qua `yfinance` với tỷ lệ ánh xạ chuẩn $\text{Basis Ratio} = \text{Spot}_{GC} / \text{Spot}_{GLD} \approx 10.8$.
   - Tự động nhận diện và tính toán chu kỳ đáo hạn 5 tháng chẵn chuẩn CME Rule 120102.E (`resolve_front_month_cme_option`): **G (T2), J (T4), M (T6), Q (T8), Z (T12)**. Tự động rollover khi đến hạn.
2. **Lõi Toán Định Lượng Black-76 & Cấu Trúc Kỳ Hạn Đa Tầng (Multi-Expiry Term Structure):**
   - Bộ Greeks giải tích bậc 1 & bậc 2 chuẩn xác: Delta ($\Delta$), Gamma ($\Gamma$), Vega ($\nu$), Vanna ($VEX$), Charm ($CHEX = -\partial \Delta / \partial T$), Theta ($\Theta$).
   - Hợp đồng Vàng gồm nhiều kỳ hạn (Monthly G, J, M, Q, Z và Weekly OG1..OG5) với DTE ($T_e$) và $\sigma_e$ khác nhau. Tổng Greeks tại từng Strike $K$ được tính theo nguyên lý xếp chồng tuyến tính (Linear Superposition):
     $$\text{NetGEX}(K) = \sum_e \text{NetGEX}_e(K), \quad \text{NetVEX}(K) = \sum_e \text{NetVEX}_e(K), \quad \text{NetCHEX}(K) = \sum_e \text{NetCHEX}_e(K)$$
   - Thuật toán giải ngược IV lai (Newton-Raphson + Dekker-Brent `_brentq` thuần Python).
   - Put-Call Parity Synthetic Pivot: $S_{\text{Implied}} = K_{\text{ATM}} + e^{rT}(C_{\text{ATM}} - P_{\text{ATM}})$.
   - Dynamic DTE theo múi giờ New York, xử lý `clean_num()` / `clean_val()` khử bỏ triệt để NaN và giá trị rác.
   - Nguồn dữ liệu thời gian thực 100% là CME Gold Futures (`GC=F`) từ Yahoo Finance, hủy bỏ cào giá Spot thứ ba (Binance PAXG, Gold-API) để loại bỏ sai lệch cơ sở và suy đoán không kiểm chứng.
3. **Đặc Thù Vi Cấu Trúc Vàng (Gold Call Skew & Gamma Squeeze):**
   - Vàng mang đặc tính **Call Skew** (phe mua Call OTM phòng hộ lạm phát & địa chính trị đẩy IV Call lên cao), kích hoạt các đợt bùng nổ **Gamma Squeeze** phía trần kháng cự khi vượt qua $Trigger_{Up} = CallWall + Call_{mid}(CallWall)$.
   - Bất biến Zero Gamma Flip ($S^*$) bắt buộc giải nghiệm liên tục bằng Dekker-Brent `_brentq` trên hàm tổng đa kỳ hạn.
   - Đo lường áp lực công thành Intraday Wall Siege Velocity Ratio: $\text{Wall Siege Ratio} = \text{Volume} / \text{Baseline OI}$.
4. **TradingView Fullscreen Zero-Tabs Realtime Terminal (Nhìn 1 Màn Hình Thấu Suốt Toàn Bộ Giá Tick & Greeks):**
   - **Đồng bộ 1:1 Nến Đa Khung Thời Gian Yahoo `GC=F` (`1m`, `5m`, `15m`, `1h`, `1d`):** Hệ thống truy vấn trực tiếp nến thực tế từ COMEX Gold Futures `GC=F` trên Yahoo Finance cho cả khung Intraday (`1m`, `5m`, `15m`) và HTF (`1h` 30 ngày, `1d` 6 tháng) qua `window.INITIAL_TF_CANDLES`, bảo toàn nguyên vẹn giá OHLC của cây nến cuối và đồng bộ 100% với `regularMarketPrice`.
   - **Bộ Kiểm Soát Giờ Phiên CME Globex (`is_cme_globex_market_open` / `isCmeGlobexMarketOpen`):** Tự động nhận diện giờ nghỉ bảo trì hàng ngày (17:00–18:00 ET) và giờ đóng cửa cuối tuần (Thứ Sáu 17:00 ET đến Chủ Nhật 18:00 ET). Khi sàn CME đóng cửa, biểu đồ khóa chặt tại giá chốt phiên chính thức của `GC=F` (`● CME GLOBEX: CLOSED (SETTLED)`), ngắt hoàn toàn các tick nhiễu ngoại lai.
   - **Fullscreen TradingView Canvas (Full-bleed 100% & Múi Giờ Việt Nam `UTC+7`):** Bố cục giao diện mở rộng tràn toàn bộ chiều ngang và chiều dọc (700px mặc định, tùy chọn ↕ Fullscreen 880px), trục thời gian và Crosshair hiển thị chuẩn giờ Việt Nam (`UTC+7`), thanh Topbar chuẩn TradingView với badge `● LIVE CME GC=F` và hệ số nhân `$100.0/oz`.
   - **Giao diện Không Tab (Zero Tabs):** Loại bỏ toàn bộ các nút tab chuyển màn hình. Toàn bộ thông tin hiển thị liền mạch trên 1 trang cuộn duy nhất:
     * Khối 1: Canvas Lightweight Charts 60 FPS tích hợp Air Pocket Vacuum Zones (hiển thị xuyên suốt cả biểu đồ nến và cột Greeks Profile với nhãn cảnh báo [CẤM ĐỠ DAO]), 4-Column Greeks Profile (GEX, VEX, CHEX, THETA với Dynamic Visible Normalization & Sublinear Boost giúp hiển thị sắc nét Vanna/Charm ở mọi khung zoom, kèm Tooltip trực quan khi rê chuột), Wall Lines, Floating HUD, Live Price Line.
     * Khối 2: Unified Greeks & Orderflow Matrix (tích hợp đầy đủ Net GEX, Net VEX, Net CHEX, Net Delta, OI, Volume, Pinning Pressure).
     * Khối 3: Plotly 4-Panel Quant Ladder (GEX, Volume/OI, VEX, CHEX) hiển thị song song ngay phía dưới.
   - **Realtime Tick Engine & Local/Cloud Bridge (Zero Reload & Zero Proxy Contamination):** Gỡ bỏ hoàn toàn `window.location.reload()`, bộ sinh nến ngẫu nhiên (`Math.random()`) và luồng WebSocket proxy `paxgusdt@aggTrade`. Giá và nến mới được cập nhật trực tiếp tại chỗ (`mergeLiveCandles` & `candleSeries.update(...)`) 100% từ Yahoo `GC=F` qua cầu nối HTTP CORS nội bộ (`127.0.0.1:8765/api/yahoo_gc` khi chạy `--loop`) và `version.json` (kèm `recent_candles`), bảo toàn nguyên vẹn tọa độ zoom/pan của trader. Đồng thời:
     * **20-Day Donchian CTA Breakout (`H20` / `L20`):** Tính toán trực tiếp từ đỉnh/đáy 20 phiên thực tế của nến `1D` `GC=F` (`daily_candles`).
     * **Strict Lee-Ready Quote Classification:** Chỉ phân loại hướng chủ động (`w_c`, `w_p`) khi tồn tại báo giá 2 chiều `Bid` và `Ask` hợp lệ (`Bid > 0`, `Ask > Bid`), gán `0.0` cho các strike thiếu thanh khoản báo giá thay vì đoán trọng số giả định.
     * **Auto-Sync Cloud Options CSV:** Tự động đồng bộ `data/options_prices_GCZ26.csv` mới nhất từ GitHub Cloud nếu file cục bộ đã cũ quá 2 giờ.
     * **Informed Quant Trader Closed-Loop Engine (Đang đề xuất — [ADR-025](decisions/ADR-025-kyle-ols-vrp-and-predatory-flow-microstructure.md)):** Tổng hợp 5 trụ cột toán học: **(1)** Hồi quy tuyến tính trượt Kyle (1985) $\lambda_{\text{OLS}} = \text{Cov}(\Delta P, y) / \text{Var}(y)$ kèm bộ lọc thanh khoản phiên ($\sigma_u$), **(2)** Chỉ số độc tính dòng lệnh **VPIN** (Easley, López de Prado & O'Hara 2012) từ BVC Volume Buckets để lọc bẫy cản tàu tại Gamma Wall, **(3)** Định lượng Volatility Risk Premium ($VRP = IV_{\text{ATM}} - RV_{\text{GC}}$) báo hiệu Vega Crush, **(4)** Z-Score Put-Call Parity Lead-Lag ($Z_{\Delta F}$) & Predatory Sweep Exhaustion, và **(5)** Chiết khấu Bayesian $\rho_{v,s} = \sqrt{\text{SNR}/(1+\text{SNR})}$ kết hợp Ma trận Thực thi 5 Chế độ & Quản trị vốn Fractional Kelly.
     * **Dynamic Liquidity Vacuum, Post-Sweep V-Shape/Pullback & Architecture Deduplication (Đã triển khai — [ADR-026](decisions/ADR-026-liquidity-vacuum-and-architecture-dedup.md)):** Hợp nhất hệ thống Air Pocket về `level_state.py`, bổ sung 3 tầng thuần `GC=F` OHLCV (`Static OI Vacuum` + `Dynamic High-Freq Amihud ILLIQ & Rogers-Satchell Vacuum` + `Institutional FVG 50%–75%` + `Post-Sweep V-Shape/Pullback` khóa bởi cổng an toàn `VPIN < 65%`), nối `precompute_squeeze_ladder` vào Live HUD (`updateSqueezeHud`), dọn sạch 6 file mã chết (`dead code`) và loại bỏ hoàn toàn `vTick` giả lập trên client JS.
     * **End-to-End Pipeline Latency, Threaded Live Bridge & Scalping Cockpit Optimization (Đã triển khai — [ADR-027](decisions/ADR-027-end-to-end-latency-and-cockpit-optimization.md)):** Triển khai đầy đủ 5 giai đoạn tối ưu hóa toàn trình: vector hóa `loader.py` & `dealer.py`, chữa lành IV chọn lọc, cache HTF `1h`/`1d` tải song song + nén HTTP gzip `_read_yahoo_json`, cầu nối `ThreadingHTTPServer` RAM-cached (`/api/yahoo_gc` `< 8ms`), bỏ gọi `build_plotly_figure` trên đường chạy chính (giữ nguyên hàm cho tests), tách chu kỳ tĩnh/động trong `--loop`, cắt tỉa hành lang `±$600` (`INITIAL_OPTIONS` & `squeeze_ladder`), giới hạn DOM Pinning `±35 strikes` (`<= 71` dòng) và khử trùng lặp 3 thẻ Orderflow tĩnh ở `KHỐI 5`, không xâm phạm `mt5/Indicators/*.mq5`.
     * **VPIN Background Dispersion & KHỐI 6 Strategy Calibration (Đã triển khai — [ADR-028](decisions/ADR-028-vpin-and-tactical-strategy-calibration.md)):** Hiệu chỉnh `compute_vpin_bvc` (chuẩn hóa phân tán nền `candles[:-6]` + chia đều 5 equal-volume buckets), đẩy Entry Breakout `Squeeze`/`Breakdown` ra ngoài vùng quét râu (`>= ±2.80`), nâng Hard SL tối thiểu `\$5.00` theo ATR `M5`, giới hạn TP `<= 1.5x Risk` và bổ sung huy hiệu `[KÍCH HOẠT]` / `[CHỜ XÁC NHẬN]` / `[TẠM KHÓA]` theo Gamma Regime / Zero Gamma / Put Wall / Air Pocket / VPIN trên `KHỐI 6`.
     * **Cockpit Tác chiến 3 Giây & Đồng bộ 100% Realtime JS/Python (Đã triển khai — [ADR-029](decisions/ADR-029-simplified-3sec-cockpit-and-full-realtime-sync.md)):** Sửa triệt để lỗi `currentTfKey` chặn polling, bổ sung thanh `#tactical-3s-command-bar` (4 ô ngay dưới chart), đơn giản hóa nhãn chiến lược & chế độ theo 4 kèo trực quan (`ƯU TIÊN ĐÁNH ĐẢO CHIỀU (GEX +)` / `ƯU TIÊN ĐÁNH THUẬN CHIỀU (GEX -)` và `1. THUẬN CHIỀU BUY (Phá cản)`, `2. ĐẢO CHIỀU SELL (Chạm cản)`, `3. ĐẢO CHIỀU BUY (Chạm sàn)`, `4. THUẬN CHIỀU SELL (Thủng sàn)` + nhãn `CHEX · HÚT GIÁ VỀ ĐÂY` / `VEX · VÙNG BẬT / GIẬT SÓNG` & tooltip GEX), bố cục 2 tầng CSS Flexbox `order` (đẩy `KHỐI 4 Spine` & `KHỐI 6` mở sẵn lên ngay dưới Command Bar và thu gọn các bảng kiểm toán vào `<details>` giữ nguyên thứ tự landmark), cổng hóa 1:1 `computeLiveVpinBvcJs` & `computeTacticalMatrixJs` với Python ADR-028, thu gọn HUD 5 dòng, gỡ Canvas Gauge đè hình và thêm chế độ `Lớp phủ: Tinh gọn / Đầy đủ` + payload `_compute_live_microstructure_payload` trên `/api/yahoo_gc`.
5. **Lưới Cron Đa Tầng Pre-Session Radar (3 Khối):**
   - **Khối 1 (07:15 VN - 00:15 UTC):** Chốt Open Interest chính thức từ CME Clearing.
   - **Khối 2 (12:30/14:30 VN - 05:30/07:30 UTC):** Pre-Europe & In-Session Europe Radar.
   - **Khối 3 (18:45 - 02:45 VN):** Pre-US, COMEX Pit Open (19:20 VN / 08:20 EST), London Fix & In-Session New York.

---

## 2. BẢNG THÔNG SỐ CỐT LÕI (GOLD SPECIFICATION TABLE)

| Hạng mục | Quy chuẩn Neiro-Gold-Quant | Ghi chú & Giải thích |
|---|---|---|
| **Tài sản HĐTL Chuẩn (Standard Futures)** | **`GC` / `GC=F`** | 100 troy ounces / hợp đồng, sàn COMEX / CME Group. |
| **Hệ số nhân Chuẩn (Multiplier)** | **$100.0** / điểm | $1.0 biến động = $100.0 PnL / hợp đồng. |
| **Mã HĐTL Micro (Micro Futures)** | **`MGC`** | 10 troy ounces / hợp đồng, Multiplier = $10.0 / điểm. |
| **Mã TradingView liên tục** | `GC1!` | Continuous Front Month Futures. |
| **Chuẩn giá Tham chiếu Terminal** | **100% Pure CME Gold Futures (`GC` / `GC=F`)** | Đồng bộ tuyệt đối chuẩn COMEX USD/oz theo Rule 8 (không quy đổi Spot `XAUUSD`). |
| **Proxy Quyền chọn Thanh khoản** | **`GLD`** (SPDR Gold Shares) / **`IAU`** | ETF vàng lớn nhất thế giới, chuỗi Options dồi dào và có Weekly Options. |
| **Tỷ lệ Ánh xạ Proxy (Basis Ratio)** | $GC \approx 10.8 \times GLD$ | Khi Gold $GC = 2,700$, ETF $GLD \approx 250$ USD/cp $\rightarrow$ Tỷ lệ $\approx 10.8$. |
| **Chỉ số Biến động Hàm ý (IV)** | **`GVZ`** (`^GVZ`) | CBOE Gold Volatility Index (đo lường IV kỳ hạn 30 ngày của GLD). |
| **Chu kỳ Đáo hạn Chính (Rollover)** | 5 tháng chẵn: **G, J, M, Q, Z** | Tháng 2, 4, 6, 8, 12 (Tháng 12 Z và Tháng 6 M là 2 kỳ hạn thanh khoản lớn nhất). |
| **Độ dốc Biến động (IV Skew)** | **Call Skew** | Nhu cầu mua Call OTM phòng hộ tăng vọt làm cong vểnh cánh Call IV. |
| **Cơ chế Định giá Cost of Carry** | $F_{0} = S_0 \cdot e^{(r + u - y)T}$ | $u \approx 0.2\%$ (lưu kho/bảo hiểm), $y \approx 1.5\%$ (Gold Lease Rate). |

---

## 3. TECH STACK & ARCHITECTURE LAYERS

| Layer | Công nghệ | Vai trò & Nhiệm vụ |
|---|---|---|
| **Quant Engine Core** | Python 3.12 / 3.14 | Black-76 Greeks, Dekker-Brent IV/Zero Gamma Solver, Cost of Carry, Level State |
| **Data Ingestion** | Playwright Headless + yfinance | Scraper Barchart API JSON & Free Live GLD/GC Feeds |
| **Orderflow Footprint** | HTML5 Canvas 60 FPS + TradingView Lightweight Charts 4.2 | Thang giá dọc, Footprint Delta, Micro-candles, Tick-by-Tick tape |
| **Quant HUD Terminal** | Plotly HTML Dark Mode | 3-Panel GEX/VEX/CHEX Ladder, Microstructure Matrix, Playbook |
| **Cloud Automation** | GitHub Actions (Ubuntu) | Lưới Cron 3 tầng đa phiên (Pre-Session Radar) |
| **Static Deployment** | GitHub Pages | Host trực tuyến độc lập, responsive mobile-friendly |
| **Microstructure Invariants** | Pure Python Zero-Dependency | Dekker-Brent `_brentq`, Wall Siege Ratio, Dynamic DTE NY timezone |

---

## 4. COMMANDS & VẬN HÀNH

```bash
# 1. Kích hoạt môi trường
.venv\Scripts\activate

# 2. Cào dữ liệu Options Chain COMEX Gold (GCZ26)
python -m src.collector.scraper --output data/options_prices_GCZ26.csv

# 3. Sinh Terminal Tác chiến Dual-View (Snapshot 1 lần)
python -m src.hud.html_dashboard --input data/options_prices_GCZ26.csv --output exports/index.html

# 4. Chạy Live Terminal liên tục (vòng lặp 15s tự giải phóng RAM)
python -m src.hud.html_dashboard --loop 15

# 5. Dọn dẹp cache không gian làm việc và thu hồi bộ nhớ RAM (< 15MB)
python -m src.hud.html_dashboard --clear-cache

# 6. Kiểm thử tự động (Unit, Math, Parity & Playwright E2E Suite)
python -m pytest tests/ -v --tb=short

# 7. Kiểm tra chuẩn mã nguồn
python -m ruff check src/ tests/
python -m ruff format src/ tests/
```

---

## 5. PROJECT STRUCTURE

```
Neiro-Gold-Quant/
├── .github/workflows/
│   └── daily_options_sync.yml        # Lưới Cron 3 khối: 07:15 VN, London 2 nấc, New York
├── .agents/skills/                   # Hệ thống kỹ năng Agent Skills chuẩn
├── config/
│   └── settings.toml                 # Cấu hình Vàng (GC, GLD, Multiplier 100.0, GVZ, Cost of Carry)
├── docs/
│   ├── spec.md                       # Bản đặc tả kỹ thuật chi tiết Neiro-Gold-Quant
│   ├── architecture.md               # Kiến trúc toàn cảnh hệ thống v3.0 Dual-View
│   ├── TRADER_PLAYBOOK.md            # Cẩm nang tác chiến thực chiến cho Trader Vàng
│   ├── HUONG_DAN_INDICATORS_MT5_TRADINGVIEW.md # Hướng dẫn cài đặt Indicator
│   ├── thuat_ngu_quant.md            # Từ điển thuật ngữ Quant Options & Vi cấu trúc
│   ├── FAQ_VA_XU_LY_SU_CO.md         # Hỏi đáp thường gặp & hướng dẫn khắc phục sự cố
│   └── decisions/                    # 29 Architecture Decision Records (ADR-001 -> ADR-029)
├── src/
│   ├── collector/
│   │   ├── scraper.py                # Playwright API Sniffer Barchart
│   │   ├── parser.py                 # Parser chuẩn hóa OptionsSnapshot
│   │   └── gold_collector.py         # Collector GLD / GC live feeds qua yfinance
│   ├── quant_engine/
│   │   ├── models.py                 # Dataclasses & kiểu dữ liệu
│   │   ├── loader.py                 # Ingestion & cleaning pipeline
│   │   ├── basis.py                  # Cost of Carry & Live CME M1/M5 Tape Feeds
│   │   ├── synthetic.py              # Put-Call Parity Implied Spot & Expected Move Bands
│   │   ├── dealer.py                 # Zero Gamma (_brentq), Wall Siege, Kyle OLS, VPIN, Dynamic Vacuum & FVG, Post-Sweep
│   │   ├── institutional.py          # 25Δ Skew (RR/BF), Vol-Target Sizing, VRP, Session Filter, Bayesian SNR
│   │   ├── level_state.py            # Level State Machine & Static OI Air Pocket Zones (hợp nhất)
│   │   └── strategy.py               # Ma trận chiến lược KHỐI 6, compute_tactical_intraday_matrix, precompute_squeeze_ladder
│   └── hud/
│       ├── neiro_terminal.py         # Canvas 60 FPS, 5-line HUD, Lớp phủ Tinh gọn/Đầy đủ & JS ADR-028 Live Engine
│       └── html_dashboard.py         # 3s Command Bar, 2-tier Flex Cockpit Generator & Live Bridge Micro-Payload
├── data/
│   └── options_prices_GCZ26.csv      # Dataset Options Chain CME mới nhất
├── tests/                            # Systematic Testing Rig & Unit/Integration Suite
│   ├── test_data_gate.py             # Cổng kiểm định dữ liệu đầu vào & CI Guard (D1-D9)
│   ├── test_math_core.py             # Lõi toán Black-76, Dekker-Brent _brentq, Zero Gamma Flip (M1-M11)
│   ├── test_expiry_rollover.py       # Tính nhất quán T_floor, DTE vi mô T->0 & Rollover hợp đồng (T1-T6)
│   ├── test_liquidity_vacuum.py      # Dynamic Vacuum (Amihud + RS), Institutional FVG & Post-Sweep Classifier
│   └── test_hud_smoke.py             # Smoke test end-to-end Dashboard render & cờ Stale/Benchmark (H1-H3)
├── Chay_Live_Terminal.bat            # Trình điều khiển trung tâm Windows tiện lợi
├── AGENTS.md / GEMINI.md             # Bộ quy tắc cốt lõi & Quy trình kích hoạt Skill
└── README.md                         # Tài liệu giới thiệu và cổng truy cập Dashboard
```

---

## 6. TIÊU CHÍ HOÀN THÀNH (SUCCESS CRITERIA)

- [x] Thiết lập file cấu hình `config/settings.toml` cho Vàng với đầy đủ tham số GC, MGC, GLD, GVZ, Multiplier 100.0, Cost of Carry ($u \approx 0.2\%$, $y \approx 1.5\%$).
- [x] Lõi toán Black-76 giải tích bậc 1 & bậc 2 chính xác, bộ giải ngược IV lai (Newton-Raphson + Dekker-Brent `_brentq`), loại bỏ triệt để NaN.
- [x] Bất biến Zero Gamma Flip ($S^*$) giải liên tục bằng Dekker-Brent `_brentq` thuần Python, đo lường Wall Siege Ratio ($Volume / OI$).
- [x] Hoàn thiện tài liệu kiến trúc và đặc tả chuyên biệt cho Vàng (`docs/spec.md` & `docs/architecture.md`).
- [x] Bộ kiểm thử tự động toàn hệ thống (`pytest tests/` — bao gồm ADR-022..029: Data Gate D1-D10, Math Core M1-M11, Rollover & Múi giờ mùa đông T1-T7, Dashboard Smoke H1-H3, Data Analyst Pipeline, Precomputed Squeeze, Black-76 Gamma Healing + 3-tier Auto-Discovery, JS/Python `r2`/VPIN Parity, và Playwright E2E Desktop/Mobile) pass sạch sẽ không lỗi.
- [x] Động cơ tính toán sẵn & Chuẩn hóa Data Analyst (ADR-024): Tính sẵn 100% Ma trận Gamma Squeeze Ladder cho tra cứu O(1) thời gian thực, khử trùng lặp, ép đơn điệu, chữa lỗi chào giá chéo và tự động chữa lành `callGammaPower`/`putGammaPower` bằng Black-76 theo độ lệch Volatility Skew (`callIV`/`putIV` từng strike) khi phát hiện dummy flat gamma (`0.0037`).
- [x] Đồng bộ Múi giờ Mùa đông Hoa Kỳ & Tự Động Hóa 3 Tầng Đáo Hạn (ADR-023): Tự động nhận diện 3 tầng đáo hạn (`WEEKLY` + `MONTHLY` + `QUARTERLY` chu kỳ chính `G, J, M, Q, Z`) kèm Lịch Nghỉ Lễ CME (`get_cme_holidays`), tự động chuyển đổi hợp đồng cơ sở (`GCZ26` -> `GCG27`), tính 13:30 Chicago Time (18:30 UTC hè / 19:30 UTC đông) và tự động làm giàu Black-76 IV theo từng kỳ hạn con trước khi gộp Multi-Expiry tại Scraper.
- [x] Triển khai TradingView Fullscreen Zero-Tabs Realtime Terminal: Mặc định nến M1, layout tràn màn hình 100%, tích hợp Realtime Tick Engine không reload trang, Unified Greeks Matrix (GEX, VEX, CHEX, Net Delta) và Plotly 4-Panel trên cùng 1 màn hình.
- [x] Triển khai Dynamic Liquidity Vacuum, Institutional FVG & Post-Sweep Execution Classifier (ADR-026): Hợp nhất Static Air Pocket về `level_state.py`, bổ sung High-Freq Amihud `ILLIQ` + Rogers-Satchell + FVG `50%–75%` + `Post-Sweep` khóa bởi `VPIN < 65%`, nối dây `squeeze_ladder` vào Live HUD (`updateSqueezeHud`), loại bỏ `vTick` giả tạo trong `applyLiveTick()` và dọn sạch 6 file mã chết / trùng lặp.
- [x] Triển khai Tối ưu hóa Độ trễ Toàn trình, Cầu nối Đa luồng & Tinh gọn Cockpit (ADR-027): Vector hóa `loader.py`/`dealer.py`, giải IV chọn lọc, song song hóa HTF + RAM cache + HTTP gzip (`_read_yahoo_json`), `ThreadingHTTPServer` bridge, `run_pipeline(..., no_mt5=True)` bỏ Plotly 4-Panel dư thừa, tách chu kỳ tĩnh/động trong `--loop`, cắt tỉa hành lang `±$600` & giới hạn DOM Pinning `<= 71` dòng (`±35 strikes`), khử trùng lặp thẻ Orderflow tĩnh ở `KHỐI 5`.
- [x] Hiệu chỉnh VPIN BVC & Tối ưu Ma trận Tác Chiến `KHỐI 6` (ADR-028): chuẩn hóa $\sigma_{\Delta P}$ theo phân tán nền `candles[:-6]` + chia đều 5 equal-volume buckets, nới Entry Breakout tránh quét râu (`>= ±2.80`), nâng sàn Hard SL `\$5.00` theo ATR `M5`, đồng bộ `precompute_squeeze_ladder` và gắn cổng trạng thái Gamma/Zero-Gamma/Air-Pocket/VPIN trên `KHỐI 6`.
- [x] Tinh gọn Cockpit Tác chiến 3 Giây & Đồng bộ 100% Realtime JS/Python (ADR-029): sửa lỗi `currentTfKey`, triển khai `#tactical-3s-command-bar`, bố cục 2 tầng Flexbox `order`, thu gọn khối kiểm toán vào `<details>`, gỡ Canvas Gauge đè hình, HUD 5 dòng, chế độ `Lớp phủ: Tinh gọn / Đầy đủ`, và động cơ JS `computeLiveVpinBvcJs`/`computeTacticalMatrixJs` khớp 1:1 với Python ADR-028 qua payload `/api/yahoo_gc`.
- [x] Đảm bảo nghiêm ngặt Zero-Waste Mandate (< 15MB repo footprint, 0 MB rác).
