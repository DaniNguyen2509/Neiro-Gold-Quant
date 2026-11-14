# ADR-026: Đặc Tả Hệ Thống Dynamic Liquidity Vacuum (OHLCV Microstructure Proxy), Thực Thi Post-Sweep (V-Shape vs Pullback) & Tinh Gọn Kiến Trúc (Chống Trùng Lặp / Mã Chết)

## Status
**Accepted & Implemented** (Đã được chủ sở hữu phê duyệt và triển khai đầy đủ trên `dealer.py`, `neiro_terminal.py`, `html_dashboard.py`, `strategy.py`, `basis.py`)

## Date
2026-11-14

---

## 1. BỐI CẢNH & MỤC TIÊU (CONTEXT & OBJECTIVE)

Sau khi triển khai bộ lọc `ADR-025` (*Informed Quant Trader: Kyle OLS Lambda, VPIN, VRP & Bayesian SNR*), chủ sở hữu yêu cầu đánh giá nghiêm ngặt 2 tài liệu đặc tả tiếp theo:
1. `docs/tailieudacta/CÔNG THỨC TÍNH TOÁN/Liquidity Vacuum/LiquidityVacuum.html` (*Liquidity Vacuum, Optimal Execution Almgren-Chriss $\kappa$, Post-Sweep Execution Matrix & V-Shape vs Pullback*)
2. `docs/tailieudacta/CÔNG THỨC TÍNH TOÁN/Liquidity Vacuum chính là airpocket/LiquidityVacuumchnhlairpocket.html` (*Giới hạn Obizhaeva & Wang — Book Depth $D(P) \to 0$, Resilience $\rho$, Kyle $\lambda_t \to \infty$*)

Đồng thời, hệ thống phải giải quyết 3 yêu cầu cốt lõi chuẩn **Zero-BS**:
1. **Phân loại rạch ròi** công thức nào chạy **THẬT và CHÍNH XÁC** trên dữ liệu thực tế hiện có của Neiro-Gold-Quant (`GC=F` OHLCV từ Yahoo Finance + `COMEX Gold Options OI/Greeks` từ Barchart, **không có** CME MDP 3.0 Level 2 / Market-By-Order), và công thức nào là **bất khả thi hoặc mập mờ/lấp liếm** cần kiên quyết loại bỏ hoặc thay thế bằng **proxy học thuật đã được kiểm chứng**.
2. **Kiểm chứng độc lập bằng Deep Research học thuật** trước khi thiết kế công thức thay thế.
3. **Rà soát toàn bộ codebase (`src/`, `tests/`)** để phát hiện các bộ lọc trùng lặp, tín hiệu chồng chéo, mâu thuẫn toán học và mã chết (`dead code`) nhằm tinh gọn triệt để hệ thống.

---

## 2. KIỂM ĐỊNH KHOA HỌC & PHÂN LOẠI TÍNH KHẢ THI (DEEP RESEARCH VERIFICATION)

### 2.1. Tổng hợp Kiểm chứng Học thuật (Web Deep Research)
Qua đối chiếu các nghiên cứu thực nghiệm về cấu trúc vi mô thị trường trên dữ liệu hợp đồng tương lai tần suất cao chỉ có OHLCV (không có sổ lệnh L2/MBO):
1. **Bar-Level High-Frequency Amihud (2002) Illiquidity (`ILLIQ`):**
   $$\text{ILLIQ}_t = \frac{|\ln(C_t / C_{t-1})|}{\max(V_t, \, 1)} \quad \text{(chỉ tính trên nến có } V_t > 0\text{)}$$
   Các nghiên cứu thực nghiệm trên hợp đồng tương lai chứng minh `ILLIQ` kết hợp chuẩn hóa độ biến động là proxy đáng tin cậy nhất để đo **độ nông thanh khoản / tác động giá trên mỗi đơn vị khối lượng** khi không có Level 2 depth.
2. **Rogers & Satchell (1991) Drift-Independent Range Volatility Estimator:**
   $$RS_t = \ln\!\left(\frac{H_t}{C_t}\right)\ln\!\left(\frac{H_t}{O_t}\right) + \ln\!\left(\frac{L_t}{C_t}\right)\ln\!\left(\frac{L_t}{O_t}\right), \qquad \hat{\sigma}_{RS, t} = \sqrt{\max(RS_t, \, 0)}$$
   Khác với Parkinson hoặc Garman-Klass (vốn giả định drift $\mu = 0$ và **đánh giá thấp sai lệch khi xảy ra thác trượt một chiều / Flash Crash**), ước lượng Rogers-Satchell hoàn toàn bất biến theo drift ($\mu \neq 0$), lý tưởng để bắt **cây nến trượt chân không có hướng (Directional Vacuum Cascade)** trên khung `1m` / `5m` của `GC=F`.
3. **Giới hạn của Almgren & Chriss (2001) Urgency ($\kappa$):**
   Tham số độ khẩn cấp chuẩn trong tài liệu 1 là:
   $$\kappa = \sqrt{\frac{\lambda_{\text{risk}} \sigma^2}{\eta}}$$
   Kiểm chứng tài liệu học thuật thực nghiệm (*Fayçal Drissi / Optimal Execution Literature*) khẳng định: **hệ số sợ rủi ro nội bộ ($\lambda_{\text{risk}}$) và hàm tác động tạm thời nội tại ($\eta$) là thông số riêng tư của từng quỹ thực thi**, không thể đo từ đồ thị OHLCV công khai. Tự bịa giá trị cho $\lambda_{\text{risk}}, \eta$ để tính $\kappa$ là hành vi "ngụy khoa học" (*Zero-BS violation*). Thay vào đó, phải thay thế bằng các biến **quan sát trực tiếp được**: động lượng hậu hấp thụ ($\lambda_{\text{post}}$), thời gian bán rã hồi phục (liquidation intensity proxy), chế độ thanh khoản phiên ($\sigma_u$ từ `resolve_cme_session_liquidity`), và `VRP` (biên bù rủi ro Vega Crush).
4. **Giới hạn của Obizhaeva & Wang (2013) Depth $D(P)$ & Resilience $\rho$:**
   Không thể tính $D(P)$ và tốc độ hồi sổ lệnh $\rho$ một cách trực tiếp khi thiếu dòng sự kiện Add/Cancel/Modify của CME MDP 3.0 L2/MBO. Tuy nhiên, hệ quả vĩ mô của $D(P) \to 0$ và $\rho \to 0$ biểu hiện trực tiếp thành **sự phình to bất thường của $(\text{ILLIQ}_t, \, \hat{\sigma}_{RS, t}, \, \lambda_{\text{bar}, t})$ trong phiên thanh khoản sâu (`LONDON_DEEP` / `NY_COMEX_DEEP`)**.
5. **Corwin & Schultz (2012) High-Low Spread Estimator (Lưu ý ranh giới áp dụng):**
   Ước lượng spread ẩn từ biên độ High-Low 2 nến liên tiếp rất hữu ích trên khung giờ thanh khoản dày (`1H` hoặc `5m` phiên Âu/Mỹ), nhưng **nhạy cảm cao với nến `1m` khối lượng $= 0$ / thanh khoản mỏng trên Yahoo `GC=F`**, dễ sinh ra giá trị ước lượng $= 0$ hoặc phóng đại sai. Chỉ nên sử dụng làm **chỉ báo phụ trợ có điều kiện Volume > 0** hoặc loại bỏ để giữ tính tối giản tin cậy.

---

### 2.2. Bảng Phân Loại: Cái Gì ĐƯỢC vs Cái Gì KHÔNG ĐƯỢC / MẬP MỜ

| Thành phần trong 2 Tài liệu gốc | Trạng thái | Phân tích Kỹ thuật & Quyết định Kiến trúc |
|---|---|---|
| **Static Options OI Air Pocket (`OI < 35%–40%` vùng lân cận)** | **ĐƯỢC (Đã có)** | Có dữ liệu OI thật từng Strike COMEX Gold từ Barchart. Chỉ định rõ vùng thiếu thanh khoản phòng vệ (Gamma/Delta hedging void) quanh cụm Wall. |
| **Dynamic Liquidity Vacuum Proxy qua High-Freq Amihud + Rogers-Satchell + Bar Kyle $\lambda$** | **ĐƯỢC (Proxy chuẩn)** | Kết hợp `ILLIQ_t >= Q95`, $\hat{\sigma}_{RS, t} \ge \mu + 2\sigma$, và $\lambda_{\text{bar}, t}$ trên nến `GC=F` có **`Volume > 0`** trong phiên `LONDON_DEEP` / `NY_COMEX_DEEP`. Tách bạch được **Chân không thanh khoản thật (Adverse Selection)** khỏi giờ vắng khách phiên Á. |
| **Institutional FVG (Fair Value Gap) lọc theo Vacuum & Options Level** | **ĐƯỢC (Bổ sung mới)** | Khoảng trống giá 3 nến (`B1.high < B3.low` hoặc `B1.low > B3.high`) chỉ được công nhận khi nến giữa (`B2`) đạt ngưỡng **Dynamic Vacuum Gate** và neo gần Wall / Zero Gamma / Static Air Pocket. Loại bỏ triệt để FVG rác phiên Á. |
| **Post-Sweep Execution: Phân tách `V-Shape` vs `Pullback 50%–75%` bằng biến quan sát** | **ĐƯỢC (Bản điều chỉnh)** | Thay $\kappa$ giả định bằng cấu trúc quan sát được: **Bước 1:** Xác nhận Hấp thụ / Cạn kiệt quét (`ICEBERG_ABSORPTION` hoặc `PREDATORY_SWEEP_EXHAUSTION` tại Wall). **Bước 2:** Phân loại `POST_SWEEP_V_SHAPE` (phá H/L nến hấp thụ + $\lambda_{\text{post}}$ nở rộng đảo chiều + phiên sâu hoặc `VRP >= +4%`) vs `POST_SWEEP_PULLBACK` ($\lambda_{\text{post}}$ ổn định/trung tính $\rightarrow$ hồi quy về 50%–75% FVG). |
| **Đo trực tiếp Order Book Depth $D(P)$ & Resilience $\rho$ (Obizhaeva-Wang)** | **KHÔNG ĐƯỢC (Bỏ)** | Không có CME MDP 3.0 L2/MBO. Không mô phỏng giả lập L2 depth từ dữ liệu giá. |
| **Tính công thức $\kappa = \sqrt{\lambda_{\text{risk}} \sigma^2 / \eta}$ (Almgren-Chriss)** | **KHÔNG ĐƯỢC (Bỏ)** | $\lambda_{\text{risk}}$ và $\eta$ là tham số nội bộ không quan sát được trên chart. Không gán hằng số tùy tiện để giả dạng công thức học thuật. |
| **Vùng quét $[K - \text{Basis} - \delta, \, K - \text{Basis}]$ & quy đổi Spot CFD** | **KHÔNG ĐƯỢC (Cấm theo Rule 8)** | Vi phạm **Rule 8 (100% Pure CME Gold Futures Quote Invariant)**. Phải neo trực tiếp vùng săn quét là $[K - \delta, \, K]$ hoặc $[K, \, K + \delta]$ theo đơn vị **`GC=F`**, dùng `Parity Z-Score` ($Z_{\Delta F}$) nội tại của chuỗi Options thay cho `Futures-Spot Basis`. |
| **Rải 30%–50% Passive Limit đón đầu trước khi quét (Pre-Sweep Laddering)** | **KHÔNG AN TOÀN (Sửa)** | Nguy hiểm chết người khi dòng tiền độc hại **`VPIN >= 65%`**. Phải khóa bởi cổng VPIN (chỉ phép vào lệnh đảo chiều sau khi có xác nhận hấp thụ hoặc `VPIN < 65%`). |
| **Tick `kyleLambda` JS với khối lượng giả lập `vTick` (`neiro_terminal.py:637, 683`)** | **LỖI TOÁN HỌC (Phải sửa)** | Phát hiện lỗi nghiêm trọng: Khi Yahoo poll trả `tickVol === null` (`L1432`), `neiro_terminal.py:637` tự tính `vTick = Math.max(1, Math.round(2 + Math.abs(dp) * 25))`, dẫn đến `kyleLambda = |dp| / vTick` bị chặn trên toán học ở **`<= 0.04`**! Hệ quả là nhánh `kyleLambda >= 0.045` (`VACUUM MARKET SWEEP` ở `L687`) và `vTick >= 12 && |dp| <= 0.08` (`ICEBERG` ở `L683`) trở thành **nhánh chết bất khả thi** khi `tickVol === null`. |

---

## 3. RÀ SOÁT TRÙNG LẶP, CHỒNG CHÉO & MÃ CHẾT TRONG HỆ THỐNG (CODEBASE AUDIT)

Quét toàn bộ `src/` và `tests/` ghi nhận **5 cụm trùng lặp / mã chết / chồng chéo nghiêm trọng**:

### 3.1. Ba bộ phát hiện `AirPocket` trùng lặp & lệch chuẩn schema
| Vị trí mã nguồn | Ký hiệu & Schema | Trạng thái sử dụng thực tế | Đề xuất xử lý |
|---|---|---|---|
| `src/quant_engine/air_pocket.py:7-72` | `detect_air_pockets(snapshot: OptionsSnapshot, ...)` $\rightarrow$ `models.AirPocket(low_strike, high_strike, avg_oi, threshold_pct)` | **0 caller trong `src/`** (chỉ gọi trong `tests/test_air_pocket.py`) | **XÓA / Hợp nhất** |
| `src/quant_engine/strategy.py:98-111, 318-375` | `class AirPocket(k_start, k_end, ...)` & `detect_air_pockets(quotes: Tuple[OptionQuote, ...])` | **0 caller ở production HUD** (chỉ dùng trong `strategy.py:generate_signals` & `tests/test_loader.py`) | **XÓA bản trùng `AirPocket`**, thay tham chiếu nếu còn giữ `strategy.py` |
| `src/quant_engine/level_state.py:27, 126-190` | `AirPocketZone` & `detect_strike_air_pockets(df, start_strike, end_strike, threshold_ratio=0.40)` | **Đang chạy chính thức** trong `src/hud/html_dashboard.py:1763-1772` | **GIỮ LÀM LÕI CHUẨN TẦNG 1 (Static OI Vacuum)** |

### 3.2. Các module, hàm và biến chết (Zero Production Consumers)
| File & Dòng | Thành phần | Bằng chứng thực tế | Đề xuất |
|---|---|---|---|
| `src/main.py:7-11` | `main()` (`raise NotImplementedError`) | Pipeline thực chạy qua `src/hud/html_dashboard.py` & `.github/workflows/daily_options_sync.yml`. File stub chết hoàn toàn. | **XÓA** |
| `src/hud/chart_exporter.py:20` | `export_quant_chart` | **0 caller** trong `src/` và workflows. | **XÓA** |
| `src/quant_engine/scenario_engine.py:60` | `evaluate_market_scenarios` (KB-1..KB-6) | **0 caller** trong `src/`, chỉ test độc lập ở `tests/test_scenario_engine.py`. Lại trùng ngữ nghĩa kịch bản với `evaluate_gamma_flip_integrity` + `evaluate_informed_trader_regime`. | **XÓA** (sau khi xác nhận với owner) |
| `src/quant_engine/basis.py:709-757` | `analyze_efp_spread()` | **0 caller** trong `src/`, chỉ ở `tests/test_basis.py`. (Cần rà luôn nếu vi phạm Rule 8 về EFP/Spot). | **XÓA** |
| `src/quant_engine/strategy.py:37-40, 224` | `XAUUSD_STOP_LOSS_*`, `compute_xauusd_stop_loss()` | Công thức quy đổi Spot `XAUUSD` cũ, **vi phạm Rule 8** (100% Pure CME Futures). | **XÓA** |
| `src/hud/html_dashboard.py:36, 48, 62` | Import thừa `resolve_dynamic_basis` (`L36`), `evaluate_tactical_level_states` (`L48` — `level_state.py:193` không hề được gọi ở đâu trong `src/`!), và hàm trùng `clean_val` (`L62` trùng `src/quant_engine/loader.py:79`) | Trùng lặp code & import rác gây tốn bộ nhớ/nhiễu bảo trì. | **DỌN SẠCH**, import dùng chung `clean_val` từ `loader.py` |
| `src/hud/html_dashboard.py:756` & `strategy.py:579` | `meta["squeeze_ladder"] = precompute_squeeze_ladder(...)` | Tính toán tốn CPU ở `html_dashboard.py:756` (và khóa bởi `tests/test_precomputed_squeeze.py`) nhưng **`meta["squeeze_ladder"]` KHÔNG HỀ ĐƯỢC ĐỌC** ở bất kỳ đâu trong `html_dashboard.py` hay `neiro_terminal.py`! | **Quyết định của Owner:** Nối dây lên Live JS HUD (`O(1)` lookup) HOẶC gỡ bỏ hoàn toàn để không tính phí công. |
| `src/hud/html_dashboard.py:2202` vs `basis.py:363-546` | Tiêu đề bảng `"Giờ VN (M5)"` vs `fetch_live_cme_m5_tape()` | `basis.py` thực chất fetch `interval=1m` trước, chỉ fallback về `5m` khi lỗi, nhưng bảng lại cứng nhắc ghi `"M5"`. | **SỬA** hiển thị động khung thời gian thật (`M1` / `M5`) |

### 3.3. Chồng chéo 4 Luồng Trạng thái Vi cấu trúc (Signal Overlap)
Hiện tại, cùng một biến động giá/volume đang bị diễn giải bởi **4 luồng nhãn độc lập** dễ gây nhiễu quyết định trader:
1. `dealer.py:638` (`evaluate_gamma_flip_integrity` — 8 trạng thái Flip + bản sao JS `computeLiveFlipVerdict` tại `neiro_terminal.py:515`)
2. `institutional.py:427` (`evaluate_informed_trader_regime` — Ma trận 5+ chế độ + Bayesian $\rho$ + Kelly)
3. `dealer.py:1088` (`compute_rolling_kyle_lambda_ols` — `ICEBERG_ABSORPTION`, `PREDATORY_SWEEP_EXHAUSTION`, `LIQUIDITY_VACUUM_SWEEP`, `NORMAL_LIQUIDITY`)
4. `basis.py:469-486` (`m5_tape` table notes — `[ĐỘT BIẾN GIẰNG CO]`, `[HẤP THỤ ĐÁY RÚT CHÂN]`, `[CHẶN BÁN ĐÈ ĐỈNH]`, `[ĐỘT BIẾN KHỐI LƯỢNG]`, `[THANH KHOẢN CẠN KIỆT]`)

**Giải pháp ADR-026:** Phân tầng rạch ròi 3 lớp không dẫm chân lên nhau (xem Mục 4.4).

---

## 4. THIẾT KẾ KIẾN TRÚC ĐỀ XUẤT (ADR-026 SPECIFICATION)

### 4.1. Kiến trúc Hợp nhất `Liquidity Vacuum Engine` (3 Tầng)
Mọi logic phát hiện chân không thanh khoản quy về một đầu mối thống nhất (không giữ 3 hàm `detect_air_pockets` song song):

#### Tầng 1: Static Structural OI Vacuum (Giữ & Chuẩn hóa từ `level_state.py`)
- Dùng `detect_strike_air_pockets()` quét chuỗi `OptionsSnapshot` / DataFrame đã chuẩn hóa.
- Khẳng định lại định nghĩa: Đây là **Vùng Trống Phòng Vệ Options (Structural Gamma/OI Void)** — nơi giá dễ tăng tốc trượt vì thiếu bức tường hedging tĩnh của Dealer.
- **Loại bỏ** hoàn toàn bản trùng trong `src/quant_engine/air_pocket.py` và `src/quant_engine/strategy.py`.

#### Tầng 2: Dynamic OHLCV Liquidity Vacuum & Institutional FVG (`detect_dynamic_liquidity_vacuum`)
Chạy trên chuỗi nến **`1m` / `5m` `GC=F` đã hoàn tất** có **`Volume > 0`** (loại bỏ hoàn toàn nến khối lượng $= 0$ và **tuyệt đối không chạy trên synthetic `vTick`**):
1. **Bar-Level High-Frequency Amihud Illiquidity:**
   $$\text{ILLIQ}_t = \frac{\left|\ln(C_t / C_{t-1})\right|}{\max(V_t, \, 1)}$$
2. **Rogers-Satchell Drift-Independent Range Volatility ($\hat{\sigma}_{RS, t}$):**
   $$\hat{\sigma}_{RS, t} = \sqrt{\max\!\left(\ln\!\left(\frac{H_t}{C_t}\right)\ln\!\left(\frac{H_t}{O_t}\right) + \ln\!\left(\frac{L_t}{C_t}\right)\ln\!\left(\frac{L_t}{O_t}\right), \, 0\right)}$$
3. **Ngưỡng Kích Hoạt Dynamic Vacuum Gate (Cửa sổ trượt $N = 60$ nến hợp lệ):**
   Một nến $t$ đạt trạng thái `DYNAMIC_LIQUIDITY_VACUUM` khi thỏa đồng thời:
   - `Volume_t > 0` và Phiên giao dịch thuộc **`LONDON_DEEP`** hoặc **`NY_COMEX_DEEP`** (khử nhiễu `ASIAN_THIN` / `GLOBEX_CLOSED`).
   - $\text{ILLIQ}_t \ge Q_{95}(\text{ILLIQ}_{t-N..t-1})$ (hoặc $Z_{\text{ILLIQ}} \ge +2.0$) **VÀ** $\hat{\sigma}_{RS, t} \ge \mu_{RS} + 2.0 \cdot \sigma_{RS}$.
   - Xác nhận chéo dòng lệnh: $\lambda_{\text{bar}, t}$ thuộc top 5% ($Q_{95}$) hoặc biên độ nến $\ge 1.8 \times \text{ATR}_{20}$.
4. **Institutional FVG Validation (3-Bar Imbalance Filter):**
   Khoảng trống giá 3 nến (`Bullish FVG`: $H_{t-2} < L_t$; `Bearish FVG`: $L_{t-2} > H_t$) chỉ được đánh dấu là **`INSTITUTIONAL_VACUUM_FVG`** nếu:
   - Nến giữa ($t-1$) đạt `DYNAMIC_LIQUIDITY_VACUUM` **HOẶC** vùng FVG giao thoa với `[Wall ± δ]`, `Zero Gamma Flip`, hay `Static OI Air Pocket`.
   - Các FVG sinh ra trong `ASIAN_THIN` không có đột biến `ILLIQ/RS` bị **lọc bỏ tự động** trên biểu đồ để giữ giao diện sạch.

#### Tầng 3: Post-Sweep Execution Classifier (`V-Shape` vs `Pullback 50%–75%` — Zero Fake $\kappa$)
Thay thế công thức $\kappa$ giả định của Almgren-Chriss bằng máy trạng thái thực nghiệm thuần CME Futures (tuân thủ Rule 8):
1. **Bán kính Săn Quét Chuẩn Pure `GC=F`:** Sử dụng trực tiếp **`[K - δ, K]`** (Call Wall) và **`[K, K + δ]`** (Put Wall), **tuyệt đối không trừ `Basis` Spot CFD**.
2. **Điều kiện Tiên quyết (Sweep + Absorption Trigger):**
   - Giá quét chạm/vượt biên Wall và xuất hiện `ICEBERG_ABSORPTION` hoặc `PREDATORY_SWEEP_EXHAUSTION` (`dealer.py`), **kèm điều kiện khóa an toàn:** chỉ cho phép kích hoạt lệnh đảo chiều khi **`VPIN < 65%`**. Khi `VPIN >= 65%`, chặn toàn bộ Limit/đảo chiều ("CẤM CẢN TÀU — TOXIC CASCADE").
3. **Phân nhánh Tốc độ Sau Hấp Thụ (Post-Absorption Regime):**
   - **`POST_SWEEP_V_SHAPE` (Đảo chiều chữ V — Bắn thị trường / Breakout nến xác nhận):**
     * Nến ngay sau nến hấp thụ phá vỡ High (đối với Bullish sweep đáy) hoặc Low (đối với Bearish sweep đỉnh) của chính nến hấp thụ.
     * $\lambda_{\text{post}}$ nở rộng đột biến theo chiều ngược lại (khẳng định thanh khoản bên ngược đã rút rỗng), xảy ra trong phiên sâu (`LONDON_DEEP` / `NY_COMEX_DEEP`) **hoặc** đang kích hoạt `VRP >= +4.0%` (*Vega Crush Snapback*), **kèm** `Parity Z-Score` ($Z_{\Delta F}$) đảo dấu cùng chiều hồi phục.
   - **`POST_SWEEP_PULLBACK` (Hồi quy thanh khoản 50%–75% — Đặt Limit trong FVG / Cân bằng):**
     * Sau hấp thụ, $\lambda_{\text{post}}$ ổn định/trung tính, không có nến phá cấu trúc tức thời; cho phép chờ giá hồi quy về **50%–75% vùng `INSTITUTIONAL_VACUUM_FVG` vừa tạo**.

### 4.2. Sửa lỗi Toán học `applyLiveTick` & Đồng bộ JS/Python (`src/hud/neiro_terminal.py`)
- **Chấm dứt tính `kyleLambda` / `ICEBERG` bằng `vTick` giả tạo:** Khi `tickVol === null` (`L1432`), hàm `applyLiveTick` (`L637`, `L683-687`) **chỉ cập nhật giá realtime**, tuyệt đối không sinh `vTick` nhân tạo để gán nhãn `ICEBERG` hay `VACUUM MARKET SWEEP`.
- Chỉ tính toán `Dynamic Vacuum`, `Kyle Lambda` và `Institutional FVG` trên **nến OHLCV hoàn tất mang Volume thật** (từ backend Python `dealer.py` + luồng cập nhật `mergeLiveCandles` chứa volume thật của Yahoo `GC=F`).

### 4.3. Phân Tầng Tín Hiệu 3 Cấp Không Chồng Chéo (Unified Signal Hierarchy)
Quy hoạch lại 4 nguồn text cạnh tranh hiện tại thành 3 tầng rõ trách nhiệm:
1. **Cấp 1 — Macro Regime & Risk Sizing (`institutional.py:evaluate_informed_trader_regime`):** Quyền lực tối cao quyết định **ĐƯỢC PHÉP CẢN TÀU HAY KHÔNG** (`VPIN`, `VRP`, `Bayesian ρ`, `Kelly Multiplier`).
2. **Cấp 2 — Structural Magnet & Flip Context (`dealer.py:evaluate_gamma_flip_integrity`):** Quyết định **bối cảnh cấu trúc quanh Zero Gamma** (`TRUE_BULLISH_FLIP`, `FAKE_BULL_TRAP`, v.v.).
3. **Cấp 3 — Execution Micro-State (Hợp nhất `dealer.py` + `Dynamic Vacuum` + `Post-Sweep` + Bảng Tape):** Hiển thị thống nhất 1 nhãn vi mô nến mới nhất kèm nhãn thời gian chính xác (`M1`/`M5`) thay vì mỗi nơi dùng một bộ từ khóa riêng lẻ.

---

## 5. RÀNG BUỘC KỸ THUẬT & TIÊU CHÍ NGHIỆM THU (CONSTRAINTS & SUCCESS CRITERIA)

1. **Zero-BS & Rule 8 Compliance:** 100% tính trên `GC=F` Futures. Không tồn tại bất kỳ hằng số $\lambda_{\text{risk}}, \eta$, công thức `D(P)/ρ` giả lập, hay tham số quy đổi `XAUUSD` nào trong lõi định lượng mới.
2. **Performance Constraints:** Thuật toán Rogers-Satchell + Amihud + FVG chạy vector hóa / vòng lặp $O(N)$ cố định trên tối đa 120–240 nến gần nhất (`RAM cố định`, `CPU < 5%`, `Zero memory leak`).
3. **Zero-Waste Mandate:** Dọn sạch mã chết & file trùng lặp, đảm bảo tổng dung lượng repo giữ mức siêu nhẹ (`< 15MB`) và **0 test thất bại** sau khi hợp nhất test suite.
4. **Criteria kiểm chứng khi chuyển sang Phase Thực thi:**
   - Unit tests bao phủ: (a) Phiên Á vắng thanh khoản `Volume > 0` nhỏ KHÔNG kích hoạt nhầm `DYNAMIC_LIQUIDITY_VACUUM`; (b) Nến `Volume == 0` bị loại an toàn không chia cho 0; (c) FVG thiếu Vacuum & thiếu Options level bị lọc bỏ; (d) `VPIN >= 65%` khóa cứng mọi tín hiệu vào lệnh ngược chiều tại Post-Sweep; (e) Đủ test cho `POST_SWEEP_V_SHAPE` vs `POST_SWEEP_PULLBACK`; (f) JS client-side khi `tickVol === null` không bao giờ tự chế nhãn `ICEBERG`/`VACUUM`.
   - `python -m pytest tests/ -v --tb=short` và `python -m ruff check src/ tests/` đạt **100% xanh**.
   - Xuất terminal qua `python -m src.hud.html_dashboard --input data/options_prices_GCZ26.csv --output exports/index.html --no-mt5` chạy sạch không lỗi.

---

## 6. KẾT QUẢ TRIỂN KHAI & QUYẾT ĐỊNH ĐÃ CHỐT (IMPLEMENTATION RECORD)

Chủ sở hữu đã phê duyệt toàn bộ phương án trong ADR-026 và các thành phần sau đã được triển khai:
1. **Dọn sạch 6 file mã chết / trùng lặp & hợp nhất chuẩn một nguồn duy nhất:**
   - Xóa `src/main.py`, `src/hud/chart_exporter.py`, `src/quant_engine/scenario_engine.py`, `tests/test_scenario_engine.py`, `src/quant_engine/air_pocket.py`, `tests/test_air_pocket.py`.
   - Loại bỏ `analyze_efp_spread()` trong `src/quant_engine/basis.py`, các hằng số/hàm `XAUUSD_STOP_LOSS_*` và `class AirPocket` trùng trong `src/quant_engine/strategy.py` (chuyển sang dùng `level_state.AirPocketZone`, `detect_strike_air_pockets()` và `GC_STOP_LOSS_DEFAULT = 4.0`).
   - Loại bỏ biến/import dư trong `src/hud/html_dashboard.py` (giữ `clean_val` tái xuất từ `src.quant_engine.loader`) và chuẩn hóa nhãn khung thời gian động (`timeframe_label`: `"M1"`/`"M5"`) từ `fetch_live_cme_m5_tape()`.
2. **Định lượng Dynamic Liquidity Vacuum, Institutional FVG & Post-Sweep (`src/quant_engine/dealer.py`):**
   - Triển khai `compute_rogers_satchell_bar()`, `_extract_valid_vacuum_bars()`, `compute_dynamic_liquidity_vacuum()`, `detect_institutional_fvgs()`, và `classify_post_sweep_execution()`, tích hợp trực tiếp vào `reconstruct_institutional_orderflow()`.
   - Bỏ qua Corwin-Schultz (2012) để tránh nhiễu trên nến `1m` có `Volume == 0`.
3. **Nối dây `squeeze_ladder`, Vẽ FVG & Sửa `applyLiveTick` (`src/hud/neiro_terminal.py` & `src/hud/html_dashboard.py`):**
   - Nối `meta["squeeze_ladder"]` vào `updateSqueezeHud(price)` tìm kiếm nhị phân theo giá realtime trên `#hud-sqz-up` / `#hud-sqz-down`.
   - Chấm dứt tạo `vTick` giả khi `tickVol === null` trong `applyLiveTick()` và `volume: 120` giả trong `mergeLiveCandles()`; bổ sung `evaluateBarOrderflow()` chỉ đánh giá trên nến `volume > 0`.
   - Vẽ hộp `INSTITUTIONAL FVG 50% | 75%` trực tiếp trên Canvas `#neiro-canvas` và đồng bộ live qua `version.json` (`hotPatchCloudMeta`) tới `#hud-post-sweep-val` và `#micro-post-sweep-val`.

