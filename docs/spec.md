# Spec: Neiro-Quant - Quantitative Gold Options Trading System

## Objective

Xay dung he thong dinh luong chay ngam tu dong 100% (Zero-Touch Automation) tren may tinh ca nhan:

1. **Thu thap** chuoi du lieu Options Chain vang tu Barchart
2. **Giai ma** cau truc vi the Dealer (Dealer Positioning) va bien do ky vong (Implied Expectations)
3. **Dong bo** do lech gia (Auto-Basis Sync) giua Futures va Spot
4. **Hien thi** truc tiep len bieu do MT5 / TradingView va bang Mini-HUD quy doi

**Target Assets:** Gold Futures/Forward (GC CME / XAUUSDF TradingView / XAUUSD-F MT5 Pepperstone) va Gold Spot (XAUUSDc / XAUUSD MT5 Exness).

**Triet ly:**
- Quan tri rui ro tuyet doi - khong chi bao ky thuat tre (RSI, MACD...), khong du doan cam tinh
- Chi dinh vi nut that thanh khoan xac suat cao (Walls, +/-1 Sigma) de vao lenh an toan
- Nhan dien vung trong thanh khoan (Air Pockets) de toi uu gong loi

**Loai bo tuyet doi:**
1. Cot Latest tren Barchart (stale prints). Luon dung Mid = (Bid + Ask) / 2
2. Bang Greeks mac dinh cua Barchart trong ngay 0DTE (IV = 0.00% sai lech toan bo)

---

## Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Quant Engine | Python | 3.12 / 3.14 |
| Options Scraper | Playwright (headless Chromium) | latest |
| Tactical Dashboard | Plotly HTML (Dark Theme) | 6.x |
| Cloud Automation | GitHub Actions + GitHub Pages | v4 |
| MT5 Bridge | MetaTrader5 Python package | latest |
| Async Runtime | asyncio + aiohttp | stdlib |
| MT5 Indicator | MQL5 | MT5 build 5xxx+ |
| TV Indicator | Pine Script v6 | TradingView |
| Config | TOML | stdlib (tomllib) |

---

## Commands

`ash
# Setup
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Run collector daemon
python -m src.collector.main

# Run full system (collector + bridge + HUD)
python -m src.main

# Test
python -m pytest tests/ -v --tb=short

# Lint
python -m ruff check src/ tests/
python -m ruff format src/ tests/
`

---

## Project Structure

`
Neiro-Quant/
+-- .agents/skills/          -> Junction -> agent-skills
+-- AGENTS.md / GEMINI.md / CLAUDE.md
+-- README.md
+-- requirements.txt
+-- pyproject.toml
+-- config/
|   +-- settings.toml        -> Cau hinh runtime
+-- src/
|   +-- __init__.py
|   +-- main.py              -> Entry point
|   +-- quant_engine/        -> Loi tinh toan (Tier 1-2-3)
|   |   +-- models.py        -> Dataclasses
|   |   +-- synthetic.py     -> Tier 2: ATM Pivot, Straddle, Bands
|   |   +-- dealer.py        -> Tier 3: Walls, Pin Risk, Gamma
|   |   +-- air_pocket.py    -> Tier 3: OI Air Pocket detection
|   |   +-- basis.py         -> Auto-Basis Sync
|   +-- collector/           -> Thu thap Options Chain
|   |   +-- main.py          -> Collector daemon
|   |   +-- scraper.py       -> Playwright/httpx scraper
|   |   +-- parser.py        -> Parse HTML/JSON -> OptionsSnapshot
|   +-- mt5_bridge/          -> Cau noi Python <-> MT5
|   |   +-- connector.py     -> MetaTrader5 wrapper
|   |   +-- price_feed.py    -> Event-driven tick listener
|   |   +-- chart_writer.py  -> Ghi levels len chart MT5
|   +-- hud/                 -> Mini-HUD quy doi
|       +-- console_hud.py   -> Terminal-based HUD (ATAS-style)
+-- mt5/Indicators/          -> 2TC-v10.mq5, NLM-v2.mq5, Neiro-Quant-Overlay.mq5
+-- mt5/Include/Neiro/       -> quant_levels.mqh
+-- tradingview/             -> Pine scripts
+-- data/                    -> Runtime data (git-ignored)
+-- logs/                    -> Runtime logs (git-ignored)
+-- docs/                    -> spec.md, architecture.md, math-reference.md
+-- tests/                   -> pytest test files
+-- tools/                   -> manual_scrape.py
`

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

### Auto-Basis Sync

- Basis = Price_Spot(Exness) - Price_Futures(Implied_ATM_or_MT5_Forward)
- Quy doi toan bo moc sang ca 2 he quy chieu: Futures/Forward va Spot (Exness Cent)

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
4. Expiry selection: Luon lay hop dong som nhat (front-month) hay cho phep chon?
5. Multiple broker support: Chi Pepperstone + Exness hay mo rong?