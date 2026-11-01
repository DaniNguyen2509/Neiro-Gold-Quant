# Spec: Neiro-Gold-Quant — Quantitative Gold Options Trading System & Dual-View Terminal

> **Bản đặc tả kỹ thuật chi tiết (System Specification)**  
> **Tài sản mục tiêu:** COMEX Gold Futures (`GC` / `MGC`), Spot `XAUUSD` / `GOLD` (London OTC) & SPDR Gold Shares (`GLD`) Options Proxy.  
> **Kiến trúc:** Cloud-Native Zero-Touch Automation (GitHub Actions + GitHub Pages, thuần Python, Zero-Waste < 15MB).  
> **Tài liệu tham chiếu:** [docs/architecture.md](architecture.md), [docs/gold-options-architecture.md](file:///c:/Users/Daniel/Documents/My-Projects/Neiro-NQ-Quant/docs/gold-options-architecture.md), [config/settings.toml](../config/settings.toml).

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
4. **All-in-One Orderflow Terminal Canvas 60 FPS (Nhìn 1 Biểu Đồ Thấu Suốt Toàn Bộ):**
   - **Tab 1: ALL-IN-ONE ORDERFLOW FOOTPRINT CANVAS:** Tích hợp trực tiếp trên Canvas 60 FPS:
     * Air Pocket Vacuum Zones (`⚠️ AIR POCKET VACUUM [$min - $max]`) cảnh báo khoảng trống thanh khoản rỗng.
     * Net GEX Profile Bars (Xanh lá / Đỏ) & Net CHEX Profile Bars (Vàng / Tím) kèm nhãn hiển thị đầy đủ GEX, VEX, CHEX cạnh từng Strike trên thước đo giá.
     * Key Structural Boundary Lines (Call Wall, Put Wall kèm Siege Ratio, Zero Gamma Flip $S^*$, Squeeze/Waterfall Triggers).
     * Floating HUD & Băng giá M5 Orderflow Tape.
   - **Tab 2: 4-PANEL QUANT LADDER & MICROSTRUCTURE MATRIX:** Plotly Dark HUD trực quan gồm 4 Panel độc lập:
     * **Panel 1: Net GEX ($M)** & Mốc Chiến Thuật (SL/TP)
     * **Panel 2: Volume, OI & Sổ Sách Net Delta (HĐ)** (Dòng lệnh & Vị thế thực tế)
     * **Panel 3: Net VEX ($M/1% IV)** · Áp lực biến động Vanna Flow
     * **Panel 4: Net CHEX ($M/ngày)** · Dòng tiền tự động phân rã Delta Charm 24h
     * Bảng định lượng vi cấu trúc Greeks & Tâm bão Pinning, Bảng chiến lược lướt sóng trong ngày.
   - Đã loại bỏ hoàn toàn các khối rườm rà: PHẦN 2 Structural Swing Walls, Action Banner KB-2, Ma trận 6 Kịch bản.
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

# 4. Chạy Live Terminal liên tục (vòng lặp 60s tự giải phóng RAM)
python -m src.hud.html_dashboard --loop 60

# 5. Dọn dẹp cache không gian làm việc và thu hồi bộ nhớ RAM (< 15MB)
python -m src.hud.html_dashboard --clear-cache

# 6. Kiểm thử tự động (Unit Test & Math Verification - 124 Tests)
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
│   └── decisions/                    # 14 Architecture Decision Records (ADRs)
├── src/
│   ├── collector/
│   │   ├── scraper.py                # Playwright API Sniffer Barchart
│   │   ├── parser.py                 # Parser chuẩn hóa OptionsSnapshot
│   │   └── gold_collector.py         # Collector GLD / GC live feeds qua yfinance
│   ├── quant_engine/
│   │   ├── models.py                 # Dataclasses & kiểu dữ liệu
│   │   ├── loader.py                 # Ingestion & cleaning pipeline
│   │   ├── basis.py                  # Cost of Carry, Dynamic Basis & Live Feeds
│   │   ├── synthetic.py              # Put-Call Parity Implied Spot & Expected Move Bands
│   │   ├── dealer.py                 # Call/Put Walls, Zero Gamma Solver (_brentq), Wall Siege
│   │   ├── air_pocket.py             # Quét chân không thanh khoản (OI < 35% MA)
│   │   ├── institutional.py          # 25Δ Skew (RR/BF), Vol-Target Sizing, CTA Confluence
│   │   ├── level_state.py            # Level State Machine (DORMANT, TESTING, ABSORPTION, SLICED)
│   │   ├── scenario_engine.py        # 6 Kịch bản Hành vi Market Maker Realtime
│   │   └── strategy.py               # Ma trận chiến lược Scalping & Swing
│   └── hud/
│       ├── neiro_terminal.py         # Tab 1: NEIRO Orderflow Footprint (Canvas HTML5 60 FPS)
│       ├── html_dashboard.py         # Dual-View Terminal Generator (NEIRO Canvas + Plotly HUD)
│       └── chart_exporter.py         # Bộ xuất biểu đồ tĩnh PNG
├── data/
│   └── options_prices_GCZ26.csv      # Dataset Options Chain CME mới nhất
├── tests/                            # Unit Tests passed 100%
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
- [x] Bộ kiểm thử 133 unit test chạy sạch sẽ 100% không lỗi.
- [x] Triển khai Terminal Tác chiến Đa Chế Độ Dual-View: Tab 1 NEIRO Orderflow Footprint (HTML5 Canvas 60 FPS) kết hợp Tab 2 Plotly Dark HUD 3-Panel Quant Ladder.
- [x] Đảm bảo nghiêm ngặt Zero-Waste Mandate (< 15MB repo footprint, 0 MB rác).
