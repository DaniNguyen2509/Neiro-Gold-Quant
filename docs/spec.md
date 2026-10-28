# Spec: Neiro-Quant - Quantitative Gold Options Trading System

## Objective

Xây dựng hệ thống định lượng dòng tiền quyền chọn (Options Flow), vị thế Dealer (Dealer Positioning) và cấu trúc vi mô thị trường (Market Microstructure) vận hành tự động 100% trên Cloud (Serverless Zero-Touch Automation):

1. **Thu thập:** Tự động bắt gói Options Chain CME Gold (GCZ26) từ Barchart qua Playwright Headless Chromium + Internal API Sniffer. Tự động tính toán và phân giải mã hợp đồng Front-Month theo lịch CME Rule 120102.E (`resolve_front_month_cme_option`), tự động rollover khi đến hạn.
2. **Giải mã:** Ma trận Greeks (Black-76, Net GEX, Net DEX, Net VEX, Net CHEX), Dynamic DTE tính thời gian đáo hạn chính xác theo phút, Synthetic ATM Pivot (Put-Call Parity kết hợp bộ lọc Liquid Strike Weighting) và biên độ kỳ vọng Expected Move (1.0σ & 0.85σ Bands).
3. **Phân tích Vi mô (Level State Engine & Air Pocket Pipeline):** [ĐÃ TRIỂN KHAI] Máy trạng thái hữu hạn giám sát tương tác động tại từng Level (`DORMANT`, `TESTING`, `ABSORPTION_DEFENDED`, `SLICED_VACUUM_RUN`), tự động quét vùng chân không thanh khoản (Air Pocket) và kích hoạt kịch bản Breakdown Slicing Runner mở rộng Target thẳng về Major Defense Wall tiếp theo.
4. **Xuất bản Độc lập:** Tự động sinh Plotly Tactical Terminal Dark Mode với Radar Vi Mô Level State Machine, chế độ hiển thị ATM ± 10 Strikes chuyên dụng cho Scalping và Swing trong ngày (chiều cao 900px bao trọn biên độ biến động rộng), xuất bản lên GitHub Pages (`https://daninguyen2509.github.io/Neiro-Quant/`) và Google Drive.

**Target Assets:** Gold Futures CME (`GCZ26`), COMEX Gold Options (`OGX26`, `OGZ26`...), XAUUSD Spot (Pepperstone / Exness / IC Markets) & E-mini Gold.

**Triết lý:**
- Quản trị rủi ro tuyệt đối — không dùng chỉ báo kỹ thuật trễ (RSI, MACD...), không đoán mò đỉnh đáy.
- Nhận diện vùng hấp thụ (Absorption) để FADE REVERSAL với Stop Loss siêu ngắn (1.5 - 2.5 giá).
- Nhận diện vùng chân không thanh khoản (Air Pockets) và rủi ro bị đâm thủng (Slicing Risk) -> CẤM ĐỠ DAO, kích hoạt BREAKOUT VACUUM RUNNER.

**Loại bỏ tuyệt đối:**
1. Cột Latest trên Barchart (stale prints). Luôn dùng Mid = (Bid + Ask) / 2.
2. Bảng Greeks mặc định của Barchart trong ngày 0DTE (IV = 0.00% sai lệch toàn bộ; tự giải ngược bằng Newton-Raphson / Brent).

---

## Tech Stack

| Layer | Technology | Role |
|---|---|---|
| Quant Engine | Python 3.12 / 3.14 | Mô hình Black-76, IV Solver, GEX/VEX/CHEX Core |
| Options Scraper | Playwright Headless Chromium | Bắt gói API JSON `/proxies/core-api/v1/quotes/get` & `options/get` (ADR-012) |
| Cloud Orchestration | GitHub Actions (Ubuntu) | Lưới Cron thích ứng 2 mùa (07:15 VN, London 2 nấc, New York) |
| Tactical Dashboard | Plotly HTML (Dark Theme) | Giao diện Web Terminal tương tác độc lập (mobile-ready) |
| Web Hosting | GitHub Pages | Host tĩnh `https://daninguyen2509.github.io/Neiro-Quant/` |
| Real-time Feeds | yfinance (`GC=F`) Native COMEX | 100% Pure CME Gold Futures Engine (ADR-006) |
| Broker Basis Bridge | MetaTrader 5 Python / MQL5 | Auto-Basis Sync Futures <-> Spot (tùy chọn) |

---

## Commands

```bash
# Setup môi trường cục bộ (tùy chọn)
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium

# Cào dữ liệu Options Chain thủ công
python -m src.collector.scraper --output data/options_prices_GCZ26.csv

# Sinh Plotly Tactical Web Terminal (Dark Mode - 1 lần)
python -m src.hud.html_dashboard --input data/options_prices_GCZ26.csv --output exports/index.html

# Chạy Live Terminal liên tục (Cập nhật 15s/lần + Giám sát RAM + Tự giải phóng bộ nhớ)
python -m src.hud.html_dashboard --loop 15

# Dọn dẹp cache không gian làm việc và thu hồi bộ nhớ RAM
python -m src.hud.html_dashboard --clear-cache

# Hoặc khởi chạy 1-Click nhanh chóng qua batch script Windows (Bộ điều khiển trung tâm 6-trong-1):
.\Chay_Live_Terminal.bat
# [1] Chạy Live Loop 15s | [2] Cào Options Chain | [3] Dọn Cache & RAM
# [4] Snapshot 1 lần    | [5] Chạy 122 Unit Tests | [6] Thoát

# Kiểm thử tự động (Unit Test & Math Verification - 122 Tests)
python -m pytest tests/ -v --tb=short

# Kiểm tra quy chuẩn mã nguồn (Lint & Format)
python -m ruff check src/ tests/
python -m ruff format src/ tests/
```

---

## Project Structure

```
Neiro-Quant/
├── .github/workflows/
│   └── daily_options_sync.yml    # Workflow cào Barchart, tính Greeks & xuất bản GitHub Pages
├── .agents/skills/               # 24 bộ kỹ năng kỹ thuật chuẩn (Agent Skills)
├── docs/
│   ├── TRADER_PLAYBOOK.md        # Cẩm nang tác chiến thực chiến cho Trader (Playbook)
│   ├── HUONG_DAN_INDICATORS_MT5_TRADINGVIEW.md # Hướng dẫn cài đặt & hợp lưu bộ đôi Indicator
│   ├── thuat_ngu_quant.md        # Từ điển thuật ngữ Quant Options & Vi cấu trúc bỏ túi
│   ├── FAQ_VA_XU_LY_SU_CO.md     # Hỏi đáp thường gặp & hướng dẫn khắc phục sự cố
│   ├── architecture.md           # Tài liệu kiến trúc toàn cảnh v2.4 (Single Source of Truth)
│   ├── spec.md                   # Bản đặc tả kỹ thuật chi tiết
│   ├── decisions/                # Architecture Decision Records (ADRs)
│   │   ├── ADR-001-cloud-native-tactical-terminal.md
│   │   ├── ADR-002-cme-front-month-auto-rollover-and-scalping-view.md
│   │   ├── ADR-003-level-state-engine-and-air-pocket-detection.md
│   │   ├── ADR-004-institutional-terminal-layout-and-anti-collision.md
│   │   ├── ADR-005-realtime-dual-price-feed-and-dynamic-basis.md
│   │   ├── ADR-006-pure-cme-futures-and-realtime-scenario-engine.md
│   │   ├── ADR-007-zero-gamma-flip-and-wall-siege-velocity.md
│   │   ├── ADR-008-multi-expiry-gex-and-gamma-weighted-walls.md
│   │   ├── ADR-009-volatility-smile-and-skew-microstructure-invariants.md
│   │   ├── ADR-010-multi-tier-data-armor-and-self-healing-architecture.md
│   │   ├── ADR-011-adaptive-micro-strike-guard-and-stale-options-detection.md
│   │   └── ADR-012-barchart-routing-and-quotes-api-interception.md
│   └── tailieudacta/             # Công thức toán học, báo cáo kiểm toán Math/Audit
│       ├── CÔNG THỨC CẦN TÍNH TOÁN.md
│       ├── DEEPSEEK_MATH_AUDIT_REPORT.md
│       └── DEEPSEEK_SRC_FULL_AUDIT_REPORT.md
├── src/
│   ├── collector/                # Thu thập dữ liệu Options Chain
│   │   ├── scraper.py            # Playwright API Sniffer (/proxies/core-api/v1/quotes/get & options/get)
│   │   └── parser.py             # Chuẩn hóa OptionsSnapshot
│   ├── quant_engine/             # Lõi tính toán định lượng
│   │   ├── models.py             # Dataclasses & kiểu dữ liệu
│   │   ├── loader.py             # Ingestion & cleaning pipeline, đa kỳ hạn & benchmark fallback
│   │   ├── basis.py              # Realtime COMEX GC=F, Dynamic Basis & OTC Spot checking
│   │   ├── synthetic.py          # Put-Call Parity Implied Spot & Expected Move Bands
│   │   ├── dealer.py             # Call/Put Walls, Gamma Flip, Squeeze Triggers, Wall Siege Ratio
│   │   ├── air_pocket.py         # Quét chân không thanh khoản (OI < 35% MA)
│   │   ├── institutional.py      # 25Δ Skew (RR/BF), Vol-Targeted Sizing & CTA Confluence
│   │   ├── level_state.py        # Finite State Machine cho từng Level
│   │   ├── scenario_engine.py    # Ma trận 6 Kịch bản Hành vi Market Maker Realtime
│   │   └── strategy.py           # Ma trận chiến lược Scalping & Swing
│   ├── hud/                      # Giao diện Tactical Terminal
│   │   ├── html_dashboard.py     # Pure CME Terminal, Volatility Smile SVI, Action Banner
│   │   └── chart_exporter.py     # Bộ xuất biểu đồ tĩnh 3-Panel Matplotlib PNG
│   └── mt5_bridge/               # Thư mục giao tiếp MetaTrader 5 (tùy chọn)
├── data/
│   └── options_prices_GCZ26.csv  # Chuỗi Options Chain mới nhất từ CME
├── tests/                        # 119 Unit & Integration tests (100% pass)
├── Chay_Live_Terminal.bat        # Bảng điều khiển trung tâm 6-trong-1 tiện lợi
├── AGENTS.md / GEMINI.md         # Quy tắc cốt lõi & Quy trình kích hoạt Skill
└── README.md                     # Hướng dẫn truy cập và tổng quan dự án
```

---

## Kien truc ly thuyet va Cong thuc toan hoc (3-Tier Knowledge Tree)

### Tier 1 (Root - Market Microstructure)

Doc truc tiep so lenh quyen chon thong qua cap Bid/Ask va Open Interest (OI) de dich nguoc ra ky vong dong tien to chuc va rui ro hang ton kho Dealer.

### Tier 2 (Branches - Implied Valuation)

1. **Synthetic ATM Pivot (synthetic_atm_pivot):**
   - Tim Strike trung tam (K_ATM) noi |Call_mid - Put_mid| nho nhat
   - S_Implied = K_ATM + Call_mid - Put_mid

2. **Implied Move / ATM Straddle (implied_straddle_move):**
   - Straddle = Call_mid(ATM) + Put_mid(ATM)

3. **1-Sigma Intraday Bands (sigma_1_upper, sigma_1_lower):**
   - Upper Band (+1s) = S_Implied + Straddle (muc chuan: 0.85 x Straddle)
   - Lower Band (-1s) = S_Implied - Straddle (muc chuan: 0.85 x Straddle)

### Tier 3 (Trunk - Dealer Positioning)

1. **Key Structural Walls (call_wall_1, put_wall_1, secondary_walls):**
   - Call Wall #1: Strike co Call_OI lon nhat -> Tran khang cu Positive Gamma
   - Put Wall #1: Strike co Put_OI lon nhat -> Be phong ho tro

2. **Option Pinning / Strike Magnet (pin_risk_magnet):**
   - Hieu ung ho den ghim gia khi tai cung Strike co ca Call_OI va Put_OI deu Top 2

3. **Gamma Squeeze Triggers:**
   - Trigger_Up = Strike_CallWall + Call_mid(CallWall)
   - Trigger_Down = Strike_PutWall - Put_mid(PutWall)

4. **OI Air Pockets (oi_air_pocket_zones):**
   - Dai Strike giua ATM va Walls co OI < 30-40% muc trung binh -> Vung chan khong

5. **Continuous Zero Gamma Flip ($S^*$):**
   - Nghiệm giải phương trình liên tục $\sum_k \text{NetGEX}_k(S^*) = 0$ bằng thuật toán Dekker-Brent (`_brentq`, pure Python zero-dependency).
   - Ranh giới đổi pha thị trường: Giá > $S^*$ $\Rightarrow$ Long Gamma (Mean-reversion / Hấp thụ biến động); Giá < $S^*$ $\Rightarrow$ Short Gamma (Trend-momentum / Breakout).

6. **Intraday Wall Siege Velocity Ratio (Tỷ Lệ Công Thành):**
   - Đo lường áp lực tấn công trực tiếp trong ngày: $\text{Siege Ratio} = \frac{\text{Volume}}{\max(\text{Baseline OI}, 1)}$.
   - Ngưỡng $\ge 0.25$: Cảnh báo `is_under_siege = True`, MM có nguy cơ vỡ trận hoặc buông phòng thủ.

7. **Dealer Net Delta Position & Book Tilt (DEX - Sổ Sách Hợp Đồng Ròng):**
   - Định lượng số lượng hợp đồng Futures CME ròng mà Dealer đang gánh trên sổ sách tại mỗi Strike:
     $$\text{Net Delta}_K = \left( \text{OI}_{\text{Call}, K} \times \Delta_{\text{Call}, K} \right) + \left( \text{OI}_{\text{Put}, K} \times \Delta_{\text{Put}, K} \right)$$
   - Xác định tổng độ lệch toàn thị trường (`Total Net Delta Contracts`) và tâm chấn lệch cực đại (`Max Tilt Strike`).
   - Phân loại chế độ:
     - `Total Net Delta > +200 HĐ`: Sổ sách nghiêng Call (Bullish Tilt).
     - `Total Net Delta < -200 HĐ`: Sổ sách nghiêng Put (Bearish Tilt).
     - $|Total Net Delta| \le 200 HĐ`: Trạng thái Delta Neutral cân bằng.
   - Trực quan hóa: Thẻ KPI `NET DELTA BIAS` đầu trang và thanh ngang `Net Delta Bar` kèm Tooltip đa tầng trên Panel 2 biểu đồ Plotly.

### Tier 4 (Hedge Fund Quantitative Mechanisms - src/quant_engine/institutional.py)

1. **25-Delta Risk Reversal ($RR_{25}$) & Butterfly ($BF_{25}$) Volatility Skew:**
   - Nội suy tuyến tính Implied Volatility theo độ nhạy Delta: $\Delta_{\text{Call}} = +0.25$ và $\Delta_{\text{Put}} = -0.25$.
   - **Risk Reversal:** $RR_{25} = IV(\text{Call}_{25\Delta}) - IV(\text{Put}_{25\Delta})$.
     - $RR_{25} > +0.5\%$: **BULLISH CALL SKEW** (Quỹ đầu cơ dồn vốn mua Call Out-of-the-Money cược bứt phá đỉnh).
     - $RR_{25} < -0.5\%$: **BEARISH PUT SKEW** (Tổ chức gom Put phòng hộ rủi ro sập giá / Black Swan).
     - $|RR_{25}| \le 0.5\%$: **BALANCED / NEUTRAL SKEW** (Thị trường kỳ vọng phân phối chuẩn).
   - **Butterfly (Smile Curvature / Tail Risk):** $BF_{25} = \frac{IV(\text{Call}_{25\Delta}) + IV(\text{Put}_{25\Delta})}{2} - IV(\text{ATM})$.

2. **Volatility-Targeted Position Sizing with GEX Regime Adjustment for MT5 XAUUSD:**
   - Tài khoản chuẩn: Equity = \$10,000, Rủi ro mục tiêu = 1.0\% (\$100).
   - Quy chuẩn XAUUSD MT5: 1 standard lot = 100 troy oz $\Rightarrow$ biến động \$1.0 USD giá vàng = \$100.0 PnL/lot.
   - **Base Sizing:**
     $$\text{Base Lots} = \frac{\text{Equity} \times \text{Risk\%} / 100}{100 \times \text{SL USD}}$$
   - **GEX Regime Multiplier:**
     - **Long Gamma Regime:** Nhân hệ số $1.0\times$ (Biến động ổn định, dealer dập tắt dao động).
     - **Short Gamma Regime:** Nhân hệ số $0.5\times$ (Bảo toàn vốn tối đa trước nguy cơ dealer bán tháo khuếch đại đà rơi và trượt giá slippage).
     - Giới hạn sàn: Tối thiểu 0.01 lot MT5.

3. **CTA Momentum Breakout Confluence (20-Day Breakout Window):**
   - Giám sát vùng phá vỡ đỉnh/đáy 20 phiên của các quỹ theo xu hướng (CTA Trend-Following Models: 20D High / 20D Low) đối chiếu trực tiếp với Options Dealer Walls.
   - **Trạng thái hợp lưu:**
     - `SUPER_SQUEEZE_CONFLUENCE`: 20D Breakout High $\ge$ Call Wall $\Rightarrow$ Hợp lưu kép: CTA kích hoạt lệnh Long mua đuổi theo đà + Market Maker vỡ trần Short Gamma bị ép mua Futures phòng hộ $\Rightarrow$ Siêu sóng tăng tốc cực mạnh.
     - `SUPER_BREAKDOWN_CASCADE`: 20D Breakdown Low $\le$ Put Wall $\Rightarrow$ Hợp lưu kép xả lũ bán tháo.
     - `INDEPENDENT_DEALER_WALLS`: Dealer Walls nằm độc lập trong biên độ thường, các chốt chặn phát huy tối đa vai trò cản kỹ thuật.

### Auto-Basis Sync & Live Spot Feed (DeepSeek Hardened)
- **Live Spot Ingestion:** Tự động gọi API thời gian thực với cơ chế multi-source fallback (Gold-API LBMA-blended `api.gold-api.com/price/XAU` làm nguồn chính, Binance `PAXGUSDT` làm proxy dự phòng).
- **Quy ước dấu chuẩn CME/LBMA:**
  $$\text{Basis} = \text{Price}_{\text{Spot}}(\text{XAU/USD}) - \text{Price}_{\text{Futures}}(\text{CME GCZ26})$$
  - Thị trường Contango (Futures > Spot) $\Rightarrow \text{Basis} < 0$ (ví dụ: $4,156.0 - 4,180.0 = -24.0$ USD).
  - Độ lệch giá tuyệt đối (Spread): $\text{Spread} = |\text{Basis}| \approx 24.0$ USD.
  - Công thức quy đổi: $\text{Level}_{\text{Spot}} = \text{Level}_{\text{Futures}} + \text{Basis}$.
- **Cơ chế an toàn Production (Hardening theo DeepSeek Audit):**
  - **Thread-safe TTL Cache (5.0s):** Bảo vệ API không bị dội request/rate-limit khi tick chạy liên tục.
  - **Exponential Backoff & Retries:** 2 lần thử, timeout 5.0s, log lỗi rõ ràng (không nuốt exception).
  - **Kiểm soát giờ mở cửa OTC Spot Gold:** Thị trường đóng cửa từ Thứ 6 22:00 UTC đến Chủ Nhật 22:00 UTC. Vào cuối tuần, hệ thống tự động fallback về basis tham chiếu, tránh dùng proxy crypto bị lệch giá.
  - **CME Contango Plausibility Band [21.0, 27.0] USD & Calibrated Contango Anchor:**
    - Theo lý thuyết Cost-of-Carry $F = S \times e^{(r-q)T}$, độ lệch Contango chuẩn giữa CME Gold Futures và MT5 Spot (XAUUSD) là $\approx 23.8 - 24.2$ USD (fair value chuẩn: **$-24.00$ USD**).
    - Các API web miễn phí (Gold-API, Binance PAXG) thường bị trễ hoặc lệch từ 10 - 20 USD (dẫn đến spread nhảy lên -35$ hoặc -48$).
    - **Cơ chế Plausibility Band:** Hệ thống giới hạn nghiêm ngặt dải chênh lệch hợp lệ trong khoảng `[21.0, 27.0] USD`. Mọi báo giá API ngoài dải này bị lập tức từ chối và tự động khóa chặt về **Calibrated Contango (-24.00 USD)**, tuyệt đối không để lọt các giá trị sai lệch vô lý.
    - **Hỗ trợ cờ `--no-mt5`:** Cho phép trader tắt quy đổi MT5 để xem 100% mức giá thuần CME Futures khi cần.
    - **Gắn nhãn nguồn tin cậy:** KPI Card hiển thị rõ nhãn `[LIVE]`, `[CALIBRATED CONTANGO]` hoặc `[MANUAL]` để trader luôn nắm rõ độ tin cậy của Basis.
  - **Zero-Crash Fault Tolerance & Runtime Hardening (PM Maintenance Standard):**
    - **Safe Benchmark Fallback cho Empty/Corrupted Dataframe:** Khi file CSV đầu vào rỗng hoặc không có strike hợp lệ, `load_and_preprocess_options` và `compute_tactical_matrix` tự động kích hoạt nạp bộ dữ liệu chuẩn định chế `BENCHMARK_GCZ26_DATA`, triệt tiêu hoàn toàn ngoại lệ `ValueError: attempt to get argmin of an empty sequence`.
    - **Scraper Fallback Network Hardening:** Bổ sung đầy đủ namespace `pandas` trong scraper và bọc an toàn các khối cào đa kỳ hạn (`scrape_multi_expiry_and_save`), đảm bảo khi Barchart rớt mạng, hệ thống tự động tải file sub-expiry đã cache mà không nuốt lỗi hay dừng tiến trình.
    - **Zero-Waste Memory Hygiene:** Vòng lặp `--loop` tự động thu hồi RAM, xóa cache báo giá (`clear_spot_cache()`) và dọn dẹp các tệp tạm thời mỗi 20 chu kỳ.

### Tier 5 (Multi-Expiry GEX Superposition & Gamma-Weighted Wall Scoring - ADR-008)
- **Giải mã nghịch lý đâm thủng Strike OI lớn:** Giải quyết triệt để tình huống Strike 4,100 có >1,000 Put OI nhưng vẫn bị đâm thủng về 4,082 do:
  1. Hợp đồng dài hạn (Monthly 30DTE) có $\Gamma \propto \frac{1}{\sqrt{T}}$ nhỏ gấp 5.5 lần so với ngắn hạn (Weekly 1DTE). Strike 4,085 (1DTE, 400 OI) có $\text{Power} = 4.66 > \text{Power}_{4100} = 3.60$.
  2. Dealer ở vị thế Short Put $\Rightarrow$ Negative Gamma Trap. Khi giá sập qua 4,100, Dealer bị ép bán tháo -154.4 HĐ GC Futures (~$63.7M) để delta-hedge, biến mốc này thành Magnet Wall gia tốc đà giảm.
- **Gamma-Weighted Wall Scoring:** $\text{Power}_k = \text{OI}_k \times \Gamma_k(S)$ kết hợp bộ lọc strictly OTM ($K > S$ cho Call, $K < S$ cho Put).
- **Phân loại Wall Regime:**
  - `[BOUNCE_WALL]` ($\text{NetGEX} \ge 0$): Dealer Long Gamma pin/hỗ trợ phản xạ dội ngược.
  - `[MAGNET_WALL]` ($\text{NetGEX} < 0$): Dealer Short Put/Negative Gamma trap gia tốc xuyên phá $\Rightarrow$ **CẤM ĐẶT LIMIT CHẶN ĐẦU BẮT DAO RƠI!**
- **Cơ chế Phân giải Đa kỳ hạn (Multi-Expiry Superposition):** `resolve_active_expirations()` tự động quét hợp đồng Weekly (OG1..OG5) và Monthly, gộp Greeks tuyến tính qua `aggregate_options_dataframes()`.

---

## Code Style

- Naming: snake_case cho ham/bien, PascalCase cho class
- Docstrings: Google style
- Type hints: Bat buoc cho moi ham public
- Max line length: 100 chars
- Formatter: ruff format
- Luon dung Mid = (Bid + Ask) / 2, KHONG BAO GIO dung cot Latest

---

## Testing Strategy

| Level | Framework | Target | Coverage |
|---|---|---|---|
| Unit | pytest | quant_engine (synthetic, dealer, air_pocket, basis, multi_expiry) | >= 90% |
| Integration | pytest | collector -> parser -> engine pipeline | >= 70% |
| Manual | tools/manual_scrape.py | Barchart scraping end-to-end | Visual verify |

---

## Boundaries

### Always do:
- Dung Mid = (Bid + Ask) / 2, KHONG BAO GIO dung cot Latest
- Type hints cho moi ham public
- Logging co level (DEBUG/INFO/WARNING/ERROR)
- deque(maxlen=N) cho chuoi thoi gian
- Giai phong tai nguyen ro rang (context managers)

### Ask first:
- Thay doi cau truc thu muc
- Them dependency moi
- Thay doi tham so mac dinh cua indicator
- Thay doi cong thuc toan hoc

### Never:
- Su dung cot Latest Barchart
- Su dung Greeks mac dinh Barchart ngay 0DTE
- Commit secrets (.env, API keys)
- Sua mac dinh indicator ma khong hoi owner
- DataFrame.append() hoac noi chuoi phinh to trong vong lap
- Quet Barchart lien tuc moi giay (chi 5-15 phut/lan)

---

## Performance Constraints

1. Luong Macro (Barchart): 5-15 phut/lan
2. Luong Micro (MT5 tick): Event-driven, chi tinh lai Basis khi gia thay doi
3. CPU < 5%
4. RAM co dinh - deque(maxlen=N)
5. Zero memory leak

---

## Success Criteria

- [x] Collector tự động quét Options Chain Barchart (JSON API Sniffer) & tự động Rollover (OGX26 -> OGZ26).
- [x] Quant Engine tính đúng: Black-76, GEX, VEX (Vanna), CHEX (Charm), Level State Machine, Air Pockets.
- [x] Pure CME Gold Futures Realtime & Dynamic Scenario Engine (ADR-006): Định vị chính xác 100% theo giá COMEX GC=F, tự động kích hoạt 6 kịch bản hành vi Market Maker. Khóa chuẩn Invariant cho Take-Profit (KB-2 TP < Entry, KB-4 TP > Entry), triệt tiêu hoàn toàn nghịch lý TP ngược khi giá chạm sát mốc ATM.
- [x] Băng Giá & Xung Lực Volume M5 Realtime (Orderflow Pulse): Tự động phát hiện Volume Spike (>= 1.4x MA20 và Volume >= 350 HĐ), lọc bỏ tick ảo Yahoo Finance, đối xứng hóa nhận diện vi mô hấp thụ đáy rút chân (`is_pinbar_bull`), chặn bán đè đỉnh (`is_pinbar_bear`) và đột biến giằng co lưỡng lự (`is_churn`). Fallback đỉnh/đáy ngày chuẩn hóa cực trị toàn phiên.
- [x] Khóa chuẩn OTM Dealer Boundary Walls: Call Wall bắt buộc là OTM Call ($strike \ge spot$), Put Wall bắt buộc là OTM Put ($strike \le spot$), triệt tiêu hoàn toàn lỗi nhận nhầm strike ITM.
- [x] Cloud-Native Tactical Terminal xuất bản thành công lên GitHub Pages (`https://daninguyen2509.github.io/Neiro-Quant/`).
- [x] Khai tử hoàn toàn Spot Gold & Hiệu chỉnh Basis: Loại bỏ 100% việc lấy giá vàng giao ngay (Spot XAU/USD từ Gold-API / Binance PAXG). Toàn bộ hệ thống neo chuẩn 100% theo giá hợp đồng tương lai vàng CME GCZ26 (COMEX GC=F), triệt tiêu hoàn toàn sai số hiệu chỉnh và báo động kịch bản giả.
- [x] DeepSeek-R1 Adversarial Audit & Hardening (20/10/2026): Thẩm tra toàn diện mã nguồn src/ bằng DeepSeek-Reasoner (R1), vá triệt để 5 lỗi Critical (Invariant TP/SL HUD, OTM Wall filtering, giải ngược Black-76 Gamma loại bỏ hằng số fake 0.0037/0.0005, Expiry cutoff 18:30 UTC rollover và ưu tiên liquid strike cho ATM).
- [x] Zero Gamma Flip Solver & Wall Siege Ratio (ADR-007): Giải nghiệm liên tục $S^*$ bằng Dekker-Brent `_brentq` thuần Python (<2ms), giám sát tỷ lệ công thành Intraday Wall Siege ($Volume / OI$) cảnh báo trước nguy cơ vỡ trận.
- [x] Multi-Expiry GEX Superposition & Gamma-Weighted Wall Scoring (ADR-008): Tự động phân giải và xếp chồng tuyến tính Greeks giữa Weekly (OG1..OG5) và Monthly, phân loại chính xác `[BOUNCE_WALL]` vs `[MAGNET_WALL]`, xóa bỏ điểm mù OI thô.
- [x] Volatility Smile & Skew Microstructure Invariants (ADR-009): Khóa 3 bất biến tác chiến vi cấu trúc (Tâm bão Pinning ATM, Hố đen giảm tốc Skew Dip và Bẫy thuốc nổ mép vểnh), tham số hóa Malz SVI (RR25 & BF25) kết nối chặt chẽ với Vanna & Charm. Thiết lập Panel độc lập toàn màn hình hiển thị trực quan Nụ cười biến động lên đầu trang Dashboard, sắp xếp thứ tự chart-first tối ưu trải nghiệm đọc lệnh trước kịch bản tác chiến.
- [x] Volatility Smile & Skew Self-Healing & Sub-Expiry Armor (28/10/2026): Khóa chặn phạm vi strike vàng [3000, 5000] cho toàn bộ sub-expiry options files, ngăn ngừa triệt để dữ liệu rác từ Barchart redirect làm lệch DTE/Expiry. Tự động giải ngược Black-76 Implied Volatility thuần Python (`solve_black76_iv` qua Dekker-Brent `_brentq`) từ giá Mid khi dữ liệu cào khuyết IV, bảo vệ đường cong Malz SVI và 25Δ Skew luôn cong mềm mại, không bao giờ bị đứng hoặc phẳng lì ở 8.00%.
- [x] 100% Zero-Waste: Dung lượng repo luôn < 15MB (hiện tại ~10.5MB), 0 MB rác trên laptop cá nhân.
- [x] Unit test coverage: 13/13 dashboard test cases & 120+ test cases toàn repo passed 100%.

---

## Real-Time Synchronization & Cadence

1. **Chu kỳ cập nhật Options Chain (Cloud Cron Grid):**
   - **07:15 VN:** Chốt Open Interest chính thức ngày mới từ CME Clearing.
   - **11:00 VN:** Cập nhật phiên Á / Tokyo Midday & chuẩn bị bước đệm trước phiên Âu.
   - **Phiên Âu (12:30/13:30 & 14:30/15:30 VN):** Cập nhật biến động trước và sau khi London mở cửa.
   - **Phiên Mỹ (18:45 VN & 19:45 - 23:45 VN):** Cập nhật định kỳ 60 phút/lần xuyên suốt giờ mở cửa NYSE & London Fix.
2. **Cập nhật Giá Realtime:**
   - Mỗi lần workflow thực thi, giá CME Futures (`GC=F`) và Spot XAU/USD (`Gold-API`) được truy vấn trực tiếp theo thời gian thực để tính Basis Contango chuẩn xác.
3. **Cơ chế Refresh phía Trình duyệt (Client-Side Cache-Busting):**
   - Thẻ `<meta http-equiv="refresh" content="300">` tự động làm mới trang mỗi 5 phút.
   - Nút `Làm mới` tích hợp hàm JavaScript `refreshWithCacheBuster()` kèm chuỗi truy vấn timestamp động `?t=...`, buộc trình duyệt xóa sạch cache cục bộ và tải dữ liệu mới nhất.

---

## Open Questions Status

1. Barchart data source: [ĐÃ GIẢI QUYẾT] Bắt gói API JSON `/proxies/core-api/v1/options/get` qua Playwright Chromium headless.
2. MT5 communication: [ĐÃ GIẢI QUYẾT] Tách biệt độc lập, không cần MT5 bật vẫn chạy 100% nhờ Cloud Web Terminal & Dual REST Feeds.
3. Expiry selection: [ĐÃ GIẢI QUYẾT] Tự động giải mã Front-Month Options theo CME Rule 120102.E (`resolve_front_month_cme_option`) và tự động Rollover.
4. Web Hosting: [ĐÃ GIẢI QUYẾT] Xuất bản trực tuyến qua GitHub Pages nhánh `gh-pages` tại `https://daninguyen2509.github.io/Neiro-Quant/`.