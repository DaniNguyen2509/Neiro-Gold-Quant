# Spec: Neiro-Quant - Quantitative Gold Options Trading System

## Objective

Xây dựng hệ thống định lượng dòng tiền quyền chọn (Options Flow), vị thế Dealer (Dealer Positioning) và cấu trúc vi mô thị trường (Market Microstructure) vận hành tự động 100% trên Cloud (Serverless Zero-Touch Automation):

1. **Thu thập:** Tự động bắt gói Options Chain CME Gold (GCZ26) từ Barchart qua Playwright Headless Chromium + Internal API Sniffer. Tự động tính toán và phân giải mã hợp đồng Front-Month theo lịch CME Rule 120102.E (`resolve_front_month_cme_option`), tự động rollover khi đến hạn.
2. **Giải mã:** Ma trận Greeks (Black-76, Net GEX, Net DEX, Net VEX, Net CHEX), Dynamic DTE tính thời gian đáo hạn chính xác theo phút, Synthetic ATM Pivot (Put-Call Parity kết hợp bộ lọc Liquid Strike Weighting) và biên độ kỳ vọng Expected Move (1.0σ & 0.85σ Bands).
3. **Phân tích Vi mô (Level State Engine & Air Pocket Pipeline):** [ĐÃ TRIỂN KHAI] Máy trạng thái hữu hạn giám sát tương tác động tại từng Level (`DORMANT`, `TESTING`, `ABSORPTION_DEFENDED`, `SLICED_VACUUM_RUN`), tự động quét vùng chân không thanh khoản (Air Pocket) và kích hoạt kịch bản Breakdown Slicing Runner mở rộng Target thẳng về Major Defense Wall tiếp theo.
4. **Xuất bản Độc lập:** Tự động sinh Plotly Tactical Terminal Dark Mode với Radar Vi Mô Level State Machine, chế độ hiển thị ATM ± 5 Strikes chuyên dụng cho Scalping trong ngày, xuất bản lên GitHub Pages (`https://daninguyen2509.github.io/Neiro-Quant/`) và Google Drive.

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
| Options Scraper | Playwright Headless Chromium | Bắt gói API JSON `/proxies/core-api/v1/options/get` |
| Cloud Orchestration | GitHub Actions (Ubuntu) | Lưới Cron thích ứng 2 mùa (07:15 VN, London 2 nấc, New York) |
| Tactical Dashboard | Plotly HTML (Dark Theme) | Giao diện Web Terminal tương tác độc lập (mobile-ready) |
| Web Hosting | GitHub Pages | Host tĩnh `https://daninguyen2509.github.io/Neiro-Quant/` |
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

# Sinh Plotly Tactical Web Terminal (Dark Mode)
python -m src.hud.html_dashboard --input data/options_prices_GCZ26.csv --output exports/index.html

# Kiểm thử tự động (Unit Test & Math Verification)
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
│   ├── architecture.md           # Tài liệu kiến trúc toàn cảnh v2.0 (Single Source of Truth)
│   ├── spec.md                   # Bản đặc tả kỹ thuật chi tiết
│   ├── decisions/                # Architecture Decision Records (ADRs)
│   │   └── ADR-001-cloud-native-tactical-terminal.md
│   └── tailieudacta/             # Công thức toán học, báo cáo kiểm toán Math/Audit
│       ├── CÔNG THỨC CẦN TÍNH TOÁN.md
│       └── DEEPSEEK_MATH_AUDIT_REPORT.md
├── src/
│   ├── collector/                # Thu thập dữ liệu Options Chain
│   │   ├── scraper.py            # Playwright API Sniffer (/proxies/core-api/v1/options/get)
│   │   └── parser.py             # Chuẩn hóa OptionsSnapshot
│   ├── quant_engine/             # Lõi tính toán định lượng
│   │   ├── models.py             # Dataclasses & kiểu dữ liệu
│   │   ├── synthetic.py          # Put-Call Parity Implied Spot & Expected Move Bands
│   │   ├── dealer.py             # Call/Put Walls, Gamma Flip, Squeeze Triggers
│   │   ├── air_pocket.py         # Quét chân không thanh khoản (OI < 35% MA)
│   │   ├── institutional.py      # 25Δ Skew (RR/BF), Vol-Targeted Sizing & CTA Confluence
│   │   └── strategy.py           # Ma trận chiến lược Scalping & Swing
│   ├── hud/                      # Giao diện Tactical Terminal
│   │   ├── html_dashboard.py     # Plotly Dark Theme generator (Anti-Collision Labels)
│   │   └── chart_exporter.py     # Xuất biểu đồ tĩnh
│   └── mt5_bridge/               # Cầu nối MetaTrader 5 (tùy chọn)
│       └── connector.py          # Kết nối MT5 & tính Auto-Basis Sync
├── data/
│   └── options_prices_GCZ26.csv  # Chuỗi Options Chain mới nhất từ CME
├── tests/                        # Bộ kiểm thử pytest
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
| Unit | pytest | quant_engine (synthetic, dealer, air_pocket, basis) | >= 90% |
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

- [ ] Collector tu dong quet Options Chain Barchart moi 5-15 phut, parse thanh cong
- [ ] Quant Engine tinh dung: Synthetic ATM Pivot, Straddle, Bands, Walls, Air Pockets, Gamma Triggers
- [ ] Auto-Basis Sync quy doi chinh xac giua Futures va Spot
- [ ] MT5 indicator Neiro-Quant-Overlay ve dung levels len chart
- [ ] Mini-HUD hien thi bang quy doi nhanh tren terminal
- [ ] He thong chay on dinh >= 24h lien tuc, CPU < 5%, RAM khong tang
- [ ] Unit test coverage >= 90% cho quant_engine

---

## Open Questions

1. Barchart data source: Scrape HTML truc tiep hay co API endpoint JSON an?
2. MT5 communication: Global Variables, Named Pipes, hay file-based?
3. TradingView data sync: Pine Script khong co HTTP - dung Google Sheets bridge hay manual input?
4. Expiry selection: [ĐÃ GIẢI QUYẾT] Tự động giải mã Front-Month Options theo CME Rule 120102.E (`resolve_front_month_cme_option`) và tự động Rollover.
5. Multiple broker support: Chi Pepperstone + Exness hay mo rong?