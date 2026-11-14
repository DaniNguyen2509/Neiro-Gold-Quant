# Spec: Neiro-Gold-Quant — Quantitative Gold Options Trading System & TradingView Fullscreen Realtime Terminal

> **Bản đặc tả kỹ thuật chi tiết (System Specification)**  
> **Tài sản mục tiêu:** COMEX Gold Futures (`GC` / `MGC`), Spot `XAUUSD` / `GOLD` (London OTC) & SPDR Gold Shares (`GLD`) Options Proxy.  
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
     * **End-to-End Pipeline Latency, Threaded Live Bridge & Scalping Cockpit Optimization (Đã lập kế hoạch thực thi — [ADR-027](decisions/ADR-027-end-to-end-latency-and-cockpit-optimization.md)):** Đặc tả 5 giai đoạn tối ưu hóa toàn trình giảm thời gian chạy lạnh từ `14.25s` xuống `< 1.65s`, chu kỳ `--loop` từ `~29.2s` xuống `< 300ms` (nhờ cache chuỗi quyền chọn tĩnh theo `mtime`), cầu nối `/api/yahoo_gc` đa luồng RAM-cached (`< 8ms`), cắt bỏ biểu đồ Plotly 4-Panel bóng ma (`3.35s` CPU) và tinh gọn `40%` dung lượng DOM/JSON mà không xâm phạm ranh giới công cụ MT5 `Neiro-Liquidity-Map-v2.mq5`.
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
| **Tài sản Cơ sở Spot / Sàn Quỹ CFD** | **`XAUUSD`** / **`GOLD`** | Báo giá Spot London OTC qua tỷ giá USD. |
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

# 6. Kiểm thử tự động (Unit Test & Math Verification - 137 Tests)
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
│   └── decisions/                    # 27 Architecture Decision Records (ADR-001 -> ADR-027)
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
│   │   └── strategy.py               # Ma trận chiến lược, precompute_squeeze_ladder (O(1) HUD Lookup)
│   └── hud/
│       ├── neiro_terminal.py         # Canvas Orderflow Footprint 60 FPS, Institutional FVG & Floating HUD
│       └── html_dashboard.py         # Dual-View Terminal Generator (NEIRO Canvas + Plotly 4-Panel)
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
- [x] Bộ kiểm thử 137 unit test chạy sạch sẽ 100% không lỗi.
- [x] Khung kiểm thử toàn diện ADR-022, ADR-023 & ADR-024: 277 test suite toàn diện (258 passed, 19 skipped, 0 failed), bao phủ cổng dữ liệu (D1-D10), lõi toán (M1-M11), Rollover & Múi giờ mùa đông (T1-T7), Smoke render Dashboard (H1-H3), Quy trình Data Analyst (`test_data_analyst_pipeline.py`), Ma trận Squeeze tính sẵn (`test_precomputed_squeeze.py`) và Chữa lành Gamma Power Black-76 + Tự động nhận diện 3 tầng kỳ hạn (`test_gamma_weighted_walls.py`).
- [x] Động cơ tính toán sẵn & Chuẩn hóa Data Analyst (ADR-024): Tính sẵn 100% Ma trận Gamma Squeeze Ladder cho tra cứu O(1) thời gian thực, khử trùng lặp, ép đơn điệu, chữa lỗi chào giá chéo và tự động chữa lành `callGammaPower`/`putGammaPower` bằng Black-76 theo độ lệch Volatility Skew (`callIV`/`putIV` từng strike) khi phát hiện dummy flat gamma (`0.0037`).
- [x] Đồng bộ Múi giờ Mùa đông Hoa Kỳ & Tự Động Hóa 3 Tầng Đáo Hạn (ADR-023): Tự động nhận diện 3 tầng đáo hạn (`WEEKLY` + `MONTHLY` + `QUARTERLY` chu kỳ chính `G, J, M, Q, Z`) kèm Lịch Nghỉ Lễ CME (`get_cme_holidays`), tự động chuyển đổi hợp đồng cơ sở (`GCZ26` -> `GCG27`), tính 13:30 Chicago Time (18:30 UTC hè / 19:30 UTC đông) và tự động làm giàu Black-76 IV theo từng kỳ hạn con trước khi gộp Multi-Expiry tại Scraper.
- [x] Triển khai TradingView Fullscreen Zero-Tabs Realtime Terminal: Mặc định nến M1, layout tràn màn hình 100%, tích hợp Realtime Tick Engine không reload trang, Unified Greeks Matrix (GEX, VEX, CHEX, Net Delta) và Plotly 4-Panel trên cùng 1 màn hình.
- [x] Triển khai Dynamic Liquidity Vacuum, Institutional FVG & Post-Sweep Execution Classifier (ADR-026): Hợp nhất Static Air Pocket về `level_state.py`, bổ sung High-Freq Amihud `ILLIQ` + Rogers-Satchell + FVG `50%–75%` + `Post-Sweep` khóa bởi `VPIN < 65%`, nối dây `squeeze_ladder` vào Live HUD (`updateSqueezeHud`), loại bỏ `vTick` giả tạo trong `applyLiveTick()` và dọn sạch 6 file mã chết / trùng lặp.
- [x] Đảm bảo nghiêm ngặt Zero-Waste Mandate (< 15MB repo footprint, 0 MB rác).
