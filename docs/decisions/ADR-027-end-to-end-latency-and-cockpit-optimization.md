# ADR-027: Đặc Tả Tối Ưu Hóa Toàn Trình (End-to-End Latency, Live Bridge & Scalping Cockpit Deduplication)

## Status
**Proposed — Execution Blueprint Ready** (Đã hoàn tất đo đạc thực nghiệm, phân tích gốc rễ và lập kế hoạch thực thi chi tiết 5 Phase cho AI Agent triển khai)

## Date
2026-11-14

---

## 1. BỐI CẢNH & RANH GIỚI KIẾN TRÚC (CONTEXT & ARCHITECTURAL BOUNDARY)

### 1.1. Mục tiêu Tối ưu hóa Toàn trình
Dưới góc độ một **Quantitative Intraday / Session Scalper** giao dịch **COMEX Gold Futures (`GC` / `GCZ26`)**, hệ thống đã hoàn thiện đầy đủ toàn bộ lõi toán học vi cấu trúc (`ADR-022` $\to$ `ADR-026`):
- Đa kỳ hạn COMEX (`Weekly` + `Monthly` + `Quarterly`) với giải nghiệm liên tục Zero Gamma Flip ($S^*$) bằng Dekker-Brent `_brentq`.
- Chữa lành Gamma Power Black-76 theo độ lệch Volatility Skew từng strike (`callIV`/`putIV`).
- Put-Call Parity Implied Forward ($\delta F$), Lee-Ready Signed Options Hedging Flow, BVC Cumulative Volume Delta (`CVD`), VPIN Toxicity, Hồi quy trượt Kyle's $\lambda_{\text{OLS}}$, Volatility Risk Premium (`VRP`), Chiết khấu Tín hiệu Bayesian ($\rho_{v,s}$), và Ma trận Dynamic Liquidity Vacuum + Institutional FVG `50%–75%` + `Post-Sweep` (`V-Shape` / `Pullback`).

Tuy nhiên, qua **đo đạc hiệu năng thực nghiệm từng hàm (millisecond-level profiling)** trên chuỗi dữ liệu thực tế `data/options_prices_GCZ26.csv` (`895` strikes tổng hợp từ 3 kỳ hạn `OG2X26`, `OG3X26`, `OGZ26`), hệ thống đang gặp **4 nút thắt cổ chai lớn về độ trễ thực thi, luồng cập nhật giá và trùng lặp DOM/UI**:
1. **Cold Pipeline mất `14,246 ms` (`~14.25 giây`):** Do đọc và chuẩn hóa CSV lặp lại **4 lần** bằng `df.iterrows()`, gọi `solve_black76_iv` trên toàn bộ 895 dòng thay vì chỉ dòng thiếu IV, gọi tuần tự 4 HTTP request trùng lặp lên Yahoo Finance, và đặc biệt là **dựng bức hình Plotly 4-Panel (`build_plotly_figure`: `2,756 ms` + `fig.to_html`: `~600 ms` = `3.35 giây`) rồi vứt bỏ hoàn toàn không gắn vào HTML**.
2. **Chế độ `--loop 15` thực chất mất `~29.25 giây/vòng` và ngốn I/O vô ích:** Dữ liệu Options OI/Greeks từ Barchart chỉ thay đổi khi chạy Scraper, nhưng mỗi vòng lặp 15 giây lại tính lại toàn bộ `895` strikes Black-76 Greeks và ghi đè file `1.14 MB` (`exports/index.html`) xuống ổ cứng / Google Drive.
3. **Độ trễ Tick Live `5.0 – 8.5 giây`:** Local Bridge (`127.0.0.1:8765/api/yahoo_gc`) dùng `HTTPServer` đơn luồng và gọi đồng bộ cả nến `1m`, `1h`, `1d` từ Yahoo mất `970 – 2,556 ms` mỗi lần client poll, kết hợp 2 bộ hẹn giờ chồng chéo trên trình duyệt (`5,000 ms` + `10,000 ms`).
4. **Phình đại Payload HTML (`1,135.4 KB`) & Trùng lặp giao diện:** Nhúng toàn bộ `895` strikes (`$1,350` đến `$10,000`) vào `window.INITIAL_OPTIONS` (`389.6 KB`) và `squeeze_ladder` (`74.3 KB`); render `320` dòng `<tr>` vào bảng Pinning trong khi chỉ hiển thị `±10` strikes (`21` dòng); và lặp lại 3 thẻ Orderflow (`Implied Forward`, `Lee-Ready`, `BVC CVD`) ở **KHỐI 5** không có DOM ID khiến số liệu bị đóng băng lệch với Floating HUD.

---

### 1.2. Ranh Giới Cứng Với `mt5/Indicators/Neiro-Liquidity-Map-v2.mq5` (KHÔNG Xâm Phạm Giai Đoạn C)

> [!IMPORTANT]
> **QUY TẮC BẤT DI BẤT DỊCH (AGENTS.md Rule 2 & Chỉ đạo trực tiếp của Owner):**
> Chủ sở hữu đã có công cụ chuyên biệt [`mt5/Indicators/Neiro-Liquidity-Map-v2.mq5`](../../mt5/Indicators/Neiro-Liquidity-Map-v2.mq5) đảm nhiệm hoàn toàn **Giai đoạn C (Price Action Liquidity Map, Session Boxes & HTF Candles)** trên nền tảng MetaTrader 5.

Qua kiểm toán mã nguồn [`Neiro-Liquidity-Map-v2.mq5`](../../mt5/Indicators/Neiro-Liquidity-Map-v2.mq5#L1-L335), công cụ MT5 này đã bao phủ đầy đủ:
1. **Mốc Thanh Khoản Ngày & Tuần (`L119-140`):** All-Time High (`ATH`), Previous Week High/Low (`PWH`/`PWL`), Current Week High/Low, Previous Day High/Low (`PDH`/`PDL`), 2 Days Ago High/Low, Today High/Low, và Midnight Open `00:00 NY` (`MNO`).
2. **5 Khung Phiên Giao Dịch & Hộp Session Range (`L142-208`):** Tokyo (`00:00–02:00 NY`), London (`02:00–09:30 NY`), NY AM (`09:30–11:00 NY`), NY Lunch (`11:00–13:00 NY`), NY PM (`13:30–16:00 NY`) kèm cơ chế lưu vết phiên trước (`p-` prefix).
3. **Cấu Trúc Đỉnh/Đáy & Thanh Khoản Quét (`L209-252`):** Equal Highs / Equal Lows (`EQH`/`EQL` với dung sai `$0.25`), Unswept `H1` & `M15` Pivots, hiệu ứng chuyển nét đứt xám khi bị quét (`Swept Level Memory`) và cảnh báo âm thanh/alert khi quét thanh khoản.
4. **Nến Đa Khung Phóng Chiếu & ICT 20m Macros (`L254-335`):** Hiển thị cụm nến `W / D / H4 / H1` bên lề phải kèm đồng hồ đếm ngược đóng nến (`InpDcTimer`) và 5 khung giờ vàng ICT 20-Minute Macro (`09:50–10:10`, `10:50–11:10`, `02:50–03:10`, `03:50–04:10`, `06:50–07:10` NY).

**Hệ quả Kiến trúc:**
- **TUYỆT ĐỐI KHÔNG** đưa các tính năng Session Box Á/Âu/Mỹ, PDH/PDL, PWH/PWL, Midnight Open, EQH/EQL, hay nến phóng chiếu HTF vào Web Quant Terminal (`neiro_terminal.py` / `html_dashboard.py`).
- **TUYỆT ĐỐI KHÔNG** chỉnh sửa bất kỳ tham số hay dòng code nào của [`mt5/Indicators/Neiro-Liquidity-Map-v2.mq5`](../../mt5/Indicators/Neiro-Liquidity-Map-v2.mq5) và [`mt5/Indicators/2TC-v10.mq5`](../../mt5/Indicators/Neiro-Liquidity-Map-v2.mq5).
- Web Quant Terminal tập trung **100% tài nguyên CPU và diện tích hiển thị** vào **Định lượng Vi cấu trúc Quyền chọn & Dòng lệnh Tổ chức COMEX (`GC=F`)**: GEX/VEX/CHEX/DEX, Zero Gamma Flip ($S^*$), Wall Siege, Put-Call Parity $\delta F$, Lee-Ready Options Flow, BVC CVD/VPIN, Kyle $\lambda_{\text{OLS}}$, VRP, Bayesian Sizing và Dynamic Liquidity Vacuum FVG.

---

### 1.3. Bất Biến 100% Pure CME Futures (`GC=F` / `GCZ26`) — Bỏ Qua Hoàn Toàn Giá Spot (`XAUUSD`)

> [!IMPORTANT]
> **CHỈ ĐẠO TRỰC TIẾP CỦA OWNER & AGENTS.md RULE 8 (100% PURE CME GOLD FUTURES QUOTE INVARIANT):**
> Chủ sở hữu **chỉ giao dịch Hợp đồng Tương lai Vàng CME (`GC` / `GC=F` / `GCZ26`)**, hoàn toàn **KHÔNG cần giá Spot (`XAUUSD`)** hay quy đổi Basis sang MT5 Spot. Nếu giá Spot không lấy được tự động thì bỏ qua hoàn toàn, tuyệt đối không cào, không hỏi, không cảnh báo lỗi (`WARNING`) và không quy đổi.

**Quy tắc bắt buộc cho AI thực thi:**
1. **Giải thích tên biến lịch sử:** Trong mã nguồn Python (`html_dashboard.py`, `loader.py`, `dealer.py`), biến mang tên `spot` / `spot_price` / `meta["spot_price"]` thực chất lưu **100% giá Hợp đồng Tương lai CME Gold Futures (`GC=F`)** (hoặc giá Implied Forward $F_{\text{chain}} = K_{\text{ATM}} + e^{rT}(C_{\text{ATM}} - P_{\text{ATM}})$ nội suy từ chuỗi quyền chọn COMEX khi mất mạng). AI thực thi không được nhầm biến này với giá Spot `XAUUSD`.
2. **Đặt mặc định `no_mt5: bool = True` trong `run_pipeline()` ([`src/hud/html_dashboard.py:2420`](../../src/hud/html_dashboard.py#L2420)):**
   - Hiện tại `run_pipeline()` đang để `no_mt5: bool | None = None`, khiến khi gọi `run_pipeline()` trực tiếp (không qua CLI `main()`), hàm `load_and_preprocess_options` (`L566`) vẫn chạy vào nhánh `resolve_dynamic_basis_with_source()` để tìm giá Spot và bắn `logger.warning("Live spot quote unavailable...")`.
   - **Cách sửa:** Đổi chữ ký `run_pipeline(..., no_mt5: bool = True)` để mặc định luôn chạy ở chế độ `CME_ONLY` (`basis = 0.0`, bỏ qua hoàn toàn việc tìm giá Spot và quy đổi Basis).
   - **Lưu ý bảo toàn Unit Test:** Giữ nguyên giá trị mặc định `no_mt5: bool = False` ở hàm cấp thấp `load_and_preprocess_options(csv_path, basis=None, no_mt5=False)` (`L122`) để bài test cũ `test_load_and_preprocess_options_with_basis` trong [`tests/test_html_dashboard.py:26-60`](../../tests/test_html_dashboard.py#L26-L60) (vốn dùng `mock.patch` để test hàm tính basis) vẫn pass 100%. Đồng thời hạ `logger.warning` tại [`src/quant_engine/basis.py:608`](../../src/quant_engine/basis.py#L608) xuống `logger.debug` để không bao giờ in cảnh báo thừa khi không có giá Spot.

---

## 2. BẢNG ĐO ĐẠC THỰC NGHIỆM & PHÂN TÍCH GỐC RỄ (EMPIRICAL PROFILING)

### 2.1. Bảng Benchmark Hiện Trạng vs Mục Tiêu Sau Tối Ưu

| Hạng mục / Giai đoạn Thực thi | Hiện trạng (Đo thực tế) | Nguyên nhân Gốc rễ (Root Cause) | Mục tiêu Sau Tối ưu | Mức Cải thiện |
|---|---|---|---|---|
| **1. `load_multi_expiry_options("data")`** | **`4,683 ms`** | Đọc mỗi file CSV **2 lần** (`loader.py:931` & `959`), gọi `normalize_options_df` (`df.iterrows()`) **3 lần**, kèm 1 lệnh HTTP ngầm lấy giá Spot (`993 ms`). | **`< 180 ms`** (Offline) | **Nhanh gấp ~26x** |
| **2. `to_options_snapshot` + `compute_exact_gamma_flip`** | **`1,335 ms`** | Bản thân `_brentq` chỉ mất **`< 15 ms`**, nhưng `to_options_snapshot` (`loader.py:1220`) gọi lại `normalize_options_df` lần thứ 4 và dùng `df.iterrows()` tạo 895 object `OptionsStrike`. | **`< 35 ms`** | **Nhanh gấp ~38x** |
| **3. `solve_black76_iv` + Sanitization + `find_gamma_weighted_walls` + `reconstruct_institutional_orderflow`** | **`1,308 ms`** | `html_dashboard.py:339-354` duyệt `df.iterrows()` cả 895 dòng khi chỉ vài dòng thiếu IV; `dealer.py:354` & `846` dùng `df.iterrows()` thay vì mảng NumPy vector hóa. | **`< 120 ms`** | **Nhanh gấp ~11x** |
| **4. Truy vấn Live Yahoo `GC=F` (`Spot` + `1m/5m` + `1h` + `1d`)** | **`3,082 ms`** | Gọi `fetch_live_cme_futures_price` (`993 ms`) rồi lại gọi tuần tự `fetch_live_cme_m5_tape(include_htf=True)` (`2,089 ms`: `1m` + `1h` + `1d` nối đuôi nhau, không cache HTF). | **`< 950 ms`** (Cold) / **`< 15 ms`** (Cached) | **Giảm 70% – 99%** |
| **5. `build_plotly_figure` + `fig.to_html` (Mã chết chưa gỡ)** | **`3,356 ms`** | `run_pipeline()` (`L2430`) dựng biểu đồ Plotly 4-Panel (`2,756 ms`) và `generate_html_terminal()` (`L1948`) xuất `plotly_div` (`600 ms`), nhưng **biến `plotly_div` KHÔNG HỀ ĐƯỢC CHÈN vào chuỗi HTML trả về**! | **`0 ms`** (Skip mặc định) | **Tiết kiệm 100% (`3.35s`)** |
| **6. `generate_html_terminal` (DOM & JSON Serialization)** | **`1,518 ms`** | Xuất toàn bộ `895` strikes vào `INITIAL_OPTIONS` (`389.6 KB`), `squeeze_ladder` (`74.3 KB`), và `320` dòng `<tr>` bằng `df.iterrows()`. | **`< 350 ms`** | **Nhanh gấp ~4.3x** |
| **TỔNG THỜI GIAN CHẠY LẠNH (`Cold Run`)** | **`14,246 ms` (`14.25s`)** | Cộng dồn 6 nút thắt trên. | **`< 1,650 ms` (`~1.6s`)** | **Nhanh gấp ~8.6x** |
| **TỔNG CHU KỲ VÒNG LẶP `--loop 15` (Khi CSV không đổi)** | **`~29,250 ms` (`14.25s` work + `15s` sleep)** | Mỗi vòng xóa cache Spot và chạy lại toàn bộ `run_pipeline()` từ đầu, ghi đè file `1.14 MB` xuống đĩa dù CSV `mtime` không đổi. | **`< 280 ms` work / chu kỳ** | **Nhanh gấp ~50x, CPU < 1%** |
| **ĐỘ TRỄ CẦU NỐI LIVE TICK (`/api/yahoo_gc`)** | **`970 – 2,556 ms` / request (`5–8s` lag)** | `HTTPServer` đơn luồng chặn I/O, mỗi request của trình duyệt lại kéo trực tiếp Yahoo Finance và tải lại cả `1h`/`1d`. | **`< 8 ms`** (Đọc từ RAM Cache) | **Cập nhật giá `< 1.5s`** |
| **DUNG LƯỢNG FILE `exports/index.html`** | **`1,135.4 KB` (`320` `<tr>`)** | Chứa `600+` strikes rác cách giá hiện tại hàng nghìn USD (`$1,350` – `$10,000`). | **`~680 KB` (`<= 71` `<tr>`)** | **Nhẹ hơn ~40% DOM/JSON** |

---

## 3. RÀNG BUỘC KIỂM THỬ BẤT BIẾN (MANDATORY TEST INVARIANTS FOR EXECUTING AGENT)

> [!CAUTION]
> **CẢNH BÁO BẮT BUỘC CHO AI THỰC THI:**
> Bộ kiểm thử hiện tại có **277 tests (`258 passed, 19 skipped, 0 failed`)**. Khi thực hiện tối ưu hóa theo 5 Task dưới đây, AI thực thi **BẮT BUỘC PHẢI BẢO TOÀN** các hợp đồng hàm và chuỗi HTML sau đây để không làm gãy bất kỳ unit test nào:

1. **Không được xóa hàm `build_plotly_figure(df, meta)` trong [`src/hud/html_dashboard.py`](../../src/hud/html_dashboard.py#L714):**
   - Các file test [`tests/test_hud_smoke.py`](../../tests/test_hud_smoke.py#L18) (`L18, 94, 117, 139, 156`) và [`tests/test_cngthctnhton_math_audit.py`](../../tests/test_cngthctnhton_math_audit.py#L17) (`L17, 140`) import và gọi trực tiếp `build_plotly_figure(df, meta)`.
   - **Giải pháp chuẩn:** Giữ nguyên hàm `build_plotly_figure(df, meta)` để phục vụ test kiểm định toán học, nhưng trong [`generate_html_terminal(df, meta, fig=None, fig_smile=None)`](../../src/hud/html_dashboard.py#L1486) đổi tham số `fig: go.Figure | None = None` thành tùy chọn và **xóa bỏ lệnh gọi `fig = build_plotly_figure(df_raw, meta)` trong `run_pipeline()` (`L2430`) cũng như xóa `plotly_div = fig.to_html(...)` (`L1948-1952`)**.
2. **Bảo toàn thứ tự xuất hiện (`pos_smile < pos_micro < pos_kpi < pos_orderflow < pos_strategy < pos_glossary`) trong [`tests/test_html_dashboard.py`](../../tests/test_html_dashboard.py#L160-L184) và [`L372-395`](../../tests/test_html_dashboard.py#L372-L395):**
   - HTML xuất ra bắt buộc phải chứa các chuỗi tiêu đề sau theo đúng thứ tự từ trên xuống dưới:
     1. `"KHỐI 1: BIỂU ĐỒ VOLATILITY SMILE & SKEW"`
     2. `"KHỐI 2: 3 PANEL BIỂU ĐỒ VI MÔ GEX"` *(Dòng comment HTML `<!-- KHỐI 2: 3 PANEL BIỂU ĐỒ VI MÔ GEX ... -->` tại `html_dashboard.py:2067` đã thỏa mãn điều kiện này — **TUYỆT ĐỐI KHÔNG XÓA comment này**!)*
     3. `"KHỐI 3: KPI THỐNG KÊ TOÀN CẢNH CME GOLD FUTURES"`
     4. `"KHỐI 5: BĂNG GIÁ & XUNG LỰC VOLUME M5"`
     5. `"BẢNG TÁC CHIẾN LƯỚT SÓNG TRONG NGÀY"`
     6. `"TỪ ĐIỂN THUẬT NGỮ BỎ TÚI"`
   - Ngoài ra phải giữ nguyên các chuỗi: `"GOLD OPTIONS TACTICAL TERMINAL"`, `"BẢNG ĐỊNH LƯỢNG VI CẤU TRÚC GREEKS & TÂM BÃO PINNING"`, `"Theta Bào Mòn"`, `"Gamma Black-76"`, `"refreshWithCacheBuster()"`, `'id="informed-trader-action-bar"'`, `'id="micro-vpin-val"'`, `'id="micro-vrp-val"'`, `'class="micro-strike-row row-spot"'`, `'👉 SPOT: $'`.
3. **Bảo toàn điều kiện đếm dòng của `test_microstructure_table_plus_minus_10_strikes_and_informed_bar` ([`tests/test_html_dashboard.py:521-565`](../../tests/test_html_dashboard.py#L521-L565)):**
   - Test này truyền vào một DataFrame 35 dòng (`df_35`) và kiểm tra:
     - `html.count('data-strike="') == 35`
     - `html.count('style="display:none; "') == 14` (tức `35 - 21 = 14` dòng ẩn).
   - **Giải pháp chuẩn:** Khi giới hạn số dòng DOM xuất ra trong `build_microstructure_pinning_table_html()`, hãy lọc các dòng nằm trong bán kính **`±35 strikes` quanh `spot_row_idx`** (`abs(row_idx - spot_row_idx) <= 35`) trước khi render `<tr>`, còn điều kiện hiển thị mặc định vẫn giữ nguyên `abs(row_idx - spot_row_idx) <= 10`.
   - Khi đó: với `df_35` (35 dòng), cả 35 dòng đều nằm trong `±35` nên `html.count('data-strike="') == 35` và `14` dòng ẩn **pass 100%**; còn trên dữ liệu thực tế `320` strikes, bảng DOM giảm từ `320` dòng xuống tối đa `71` dòng (`±35 strikes` quanh Spot, đủ cho thanh trượt `±10 / ±20 / ±35 Strikes`)!

---

## 4. KẾ HOẠCH THỰC THI CHI TIẾT 5 GIAI ĐOẠN (STEP-BY-STEP IMPLEMENTATION PLAN)

AI thực thi cần triển khai tuần tự **5 Task (Slices)** độc lập dưới đây. Sau mỗi Task, chạy `python -m pytest tests/ -q` để xác nhận 100% xanh trước khi chuyển sang Task tiếp theo.

---

### TASK 1: Vector Hóa Tầng Nạp Dữ Liệu & Triệt Tiêu Đọc/Chuẩn Hóa Lặp 4 Lần (`src/quant_engine/loader.py`)
**Mục tiêu:** Giảm thời gian `load_multi_expiry_options` + `to_options_snapshot` từ **`6,018 ms` xuống `< 215 ms`**.

#### 1.1. Loại bỏ đọc CSV lặp 2 lần trong `load_multi_expiry_options` ([`src/quant_engine/loader.py:907-975`](../../src/quant_engine/loader.py#L907-L975))
- **Hiện trạng (`L931-963`):**
  - Vòng lặp 1 (`L931-943`) gọi `d_check = _load_from_path(f)` cho từng file `_OG*.csv` chỉ để kiểm tra `_is_valid_gold_chain(d_check)`, sau đó vứt bỏ `d_check`.
  - Vòng lặp 3 (`L957-963`) lại gọi `d = _load_from_path(f)` lần thứ 2 trên đúng các file đó.
- **Cách sửa:**
  - Trong vòng lặp 1, lưu các `DataFrame` hợp lệ vào `preloaded_dfs: dict[Path, pd.DataFrame] = {}` ngay khi `_is_valid_gold_chain(d_check)` trả về `True`.
  - Ở vòng lặp 3 (`L957-963`), lấy trực tiếp `d = preloaded_dfs.get(f) or _load_from_path(f)` thay vì đọc lại từ ổ cứng và chuẩn hóa lại.

#### 1.2. Vector hóa `normalize_options_df` và gắn cờ `df.attrs["is_normalized"] = True` ([`src/quant_engine/loader.py:168-300`](../../src/quant_engine/loader.py#L168-L300))
- **Hiện trạng:**
  - `normalize_options_df(df)` được gọi lặp lại **4 lần** trên cùng dữ liệu:
    1. Trong `_load_from_path()` (`L654`).
    2. Trong `aggregate_options_dataframes()` (`L726`).
    3. Trong `to_options_snapshot()` (`L1220`).
    4. Cộng thêm bước `clean_and_sanitize_options_dataset` + `.apply(clean_val)` trong `html_dashboard.py:169-189`.
  - Bản thân `normalize_options_df` dùng `for _, r in df.iterrows():` (`L202-295`), gọi closure `get_num(r, ...)` 16 lần mỗi dòng.
- **Cách sửa:**
  1. Ở đầu `normalize_options_df(df: pd.DataFrame) -> pd.DataFrame`:
     - Kiểm tra nhanh: nếu `df.attrs.get("is_normalized") is True` và tập cột chuẩn (`{"strike", "call_oi", "put_oi", "call_volume", "put_volume", "call_iv", "put_iv", "dte"}`) đã tồn tại trong `df.columns`, trả về `df.copy()` ngay lập tức (`O(1)`).
  2. Thay thế vòng lặp `for _, r in df.iterrows():` (`L202-295`) bằng xử lý cột vector hóa Pandas/NumPy:
     - Viết hàm phụ `_extract_numeric_series(df: pd.DataFrame, col_map: dict[str, str], keys: list[str], default: float = 0.0, is_percent: bool = False) -> pd.Series`: tìm cột đầu tiên khớp trong `keys`, dùng `pd.to_numeric(s.astype(str).str.replace(",", "", regex=False).str.replace("%", "", regex=False).str.replace("$", "", regex=False).str.strip(), errors="coerce").fillna(default)`.
     - Tính vector hóa cho các cột `strike`, `call_oi`, `put_oi`, `call_volume`, `put_volume`, `call_iv`, `put_iv`, `call_bid`, `call_ask`, `call_last`, `put_bid`, `put_ask`, `put_last`, `call_gamma_power`, `put_gamma_power`, `call_theta_power`, `put_theta_power`, `dte`.
     - Quy đổi IV: `call_iv = np.where(call_iv > 3.0, call_iv / 100.0, call_iv)` và `put_iv = np.where(put_iv > 3.0, put_iv / 100.0, put_iv)`.
     - Lọc `df_out = df_out[df_out["strike"] > 0].sort_values("strike").reset_index(drop=True)`.
     - Đánh dấu `df_out.attrs["is_normalized"] = True` trước khi return.

#### 1.3. Loại bỏ truy vấn HTTP ngầm trong `aggregate_options_dataframes` và Vector hóa `to_options_snapshot` ([`src/quant_engine/loader.py:702-835, 1213-1255`](../../src/quant_engine/loader.py#L702-L835))
- **Trong `aggregate_options_dataframes` (`L726, L744`):**
  - Chỉ gọi `normalize_options_df(d)` nếu `not d.attrs.get("is_normalized")`.
  - Tại `L742-745`: nếu `spot_price is None`, truyền `allow_network=False` (hoặc suy diễn trực tiếp từ Put-Call Parity / Median Strike của `valid_dfs[0]` mà không gọi `fetch_live_cme_futures_price()` qua mạng), vì `html_dashboard.py` sẽ lấy giá Spot live một lần duy nhất ngay sau đó và truyền vào. Đặt `out.attrs["is_normalized"] = True`.
- **Trong `to_options_snapshot` (`L1213-1255`):**
  - Bỏ gọi lại `normalize_options_df(df)` nếu `df.attrs.get("is_normalized")` hoặc đã có đủ cột chuẩn.
  - Thay `for _, r in norm.iterrows():` (`L1239`) bằng `itertuples(index=False)` hoặc trích xuất mảng `.to_numpy()` + list comprehension tạo `OptionsStrike(...)` (nhanh hơn `iterrows()` gấp 25–30 lần).

---

### TASK 2: Vector Hóa Lõi Toán Dealer & Chữa Lành IV Có Chọn Lọc (`src/quant_engine/dealer.py` & `src/hud/html_dashboard.py`)
**Mục tiêu:** Giảm thời gian tính toán vi cấu trúc trong `load_and_preprocess_options` từ **`1,308 ms` xuống `< 120 ms`**.

#### 2.1. Chữa lành Black-76 IV chỉ trên các dòng thực sự thiếu IV ([`src/hud/html_dashboard.py:335-355`](../../src/hud/html_dashboard.py#L335-L355))
- **Hiện trạng (`L339-354`):**
  ```python
  if needs_c_iv.any():
      df["callIV"] = [
          solve_black76_iv(...) if (row["callIV"] <= 1e-4 and row["call_mid"] > 0) else row["callIV"]
          for _, row in df.iterrows()
      ]
  ```
  Khi chỉ 1–5 dòng OTM thiếu IV, đoạn code này vẫn ép Pandas mở gói `df.iterrows()` qua toàn bộ `895` dòng cho cả Call và Put (`431 ms`).
- **Cách sửa:**
  Chỉ lặp trên các chỉ mục `idx` mà `needs_c_iv` (hoặc `needs_p_iv`) bằng `True`:
  ```python
  if needs_c_iv.any():
      c_idx = df.index[needs_c_iv]
      df.loc[c_idx, "callIV"] = [
          solve_black76_iv(spot, float(k), float(t), r_rate, float(m), is_call=True)
          for k, t, m in zip(df.loc[c_idx, "strike"], df.loc[c_idx, "T"], df.loc[c_idx, "call_mid"])
      ]
  if needs_p_iv.any():
      p_idx = df.index[needs_p_iv]
      df.loc[p_idx, "putIV"] = [
          solve_black76_iv(spot, float(k), float(t), r_rate, float(m), is_call=False)
          for k, t, m in zip(df.loc[p_idx, "strike"], df.loc[p_idx, "T"], df.loc[p_idx, "put_mid"])
      ]
  ```
- Đồng thời tại `html_dashboard.py:169-189`: nếu `df_raw.attrs.get("is_normalized") is True`, bỏ qua vòng lặp `.apply(clean_val)` trên 17 cột số đã sạch.

#### 2.2. Vector hóa `find_gamma_weighted_walls` ([`src/quant_engine/dealer.py:305-404`](../../src/quant_engine/dealer.py#L305-L404))
- **Hiện trạng (`L354`):** Dùng `for _, row in df.iterrows():` để duyệt từng dòng tính `c_gex`, `p_gex`, `oi_score`, `gamma_score`.
- **Cách sửa:**
  Trích xuất mảng NumPy 1 chiều (`.to_numpy(dtype=float)`) cho `strike`, `callOpenInterest`, `putOpenInterest`, `callVolume`, `putVolume`, `callGammaPower`, `putGammaPower` (hoặc tính vector hóa Black-76 gamma khi thiếu), lọc bằng boolean mask `(strikes >= lower_bound) & (strikes <= upper_bound)`, và dùng `np.argmax(...)` để tìm `call_wall`, `put_wall`, `major_call_oi_wall`, `major_put_oi_wall`. Bảo toàn chính xác 100% công thức điểm số `0.70 * norm_gex + 0.30 * norm_oi * siege_boost` và các khóa trả về trong dict.

#### 2.3. Vector hóa `reconstruct_institutional_orderflow` ([`src/quant_engine/dealer.py:815-925`](../../src/quant_engine/dealer.py#L815-L925))
- **Hiện trạng (`L846`):** Dùng `for _, row in df.iterrows():` qua 895 dòng để tính trọng số Lee-Ready `w_c`, `w_p` và `delta_c`, `delta_p`.
- **Cách sửa:**
  Dùng `np.where` trên các mảng NumPy `c_bid`, `c_ask`, `c_last`, `p_bid`, `p_ask`, `p_last`, `c_vol`, `p_vol`, `strikes`, `c_iv`, `p_iv` (dùng `scipy.special.erf` hoặc `np.vectorize(math.erf)` trên mảng `d1`), giữ nguyên tuyệt đối điều kiện `Strict Lee-Ready Quote Classification` (`(c_bid > 0) & (c_ask > c_bid)`) và kết quả đầu ra.

---

### TASK 3: Khử Trùng Lặp Yahoo Live Feed, Song Song Hóa HTF & Đa Luồng Hóa RAM Bridge (`src/quant_engine/basis.py`, `src/hud/html_dashboard.py`, `src/hud/neiro_terminal.py`)
**Mục tiêu:** Giảm thời gian lấy dữ liệu mạng từ **`3,082 ms` xuống `< 950 ms` (Cold) / `< 15 ms` (Warm)** và giảm độ trễ cầu nối `/api/yahoo_gc` từ **`2,556 ms` xuống `< 8 ms`**.

#### 3.1. Cache RAM cho nến HTF (`1h`, `1d`) và tải song song trong `fetch_live_cme_m5_tape` ([`src/quant_engine/basis.py:295-465`](../../src/quant_engine/basis.py#L295-L465))
- **Hiện trạng (`L418-452`):** Mỗi lần gọi `fetch_live_cme_m5_tape(limit=8, include_htf=True)` đều tải tuần tự `1m (range=5d)` $\to$ `1h (range=1mo)` $\to$ `1d (range=6mo)`. Nến `1h` và `1d` thay đổi rất chậm nhưng lại tốn `~1,120 ms` mỗi lần gọi.
- **Cách sửa trong `src/quant_engine/basis.py`:**
  1. Thêm bộ nhớ đệm cấp module `_HTF_TAPE_CACHE: dict[str, tuple[float, list[dict]]] = {}` với `HTF_CACHE_TTL_SEC = 60.0` (và xóa nó khi gọi `clear_spot_cache()`).
  2. Khi `include_htf=True`: nếu `"1h"` và `"1d"` trong `_HTF_TAPE_CACHE` còn hạn `< 60s`, dùng lại ngay (`0 ms`) và chỉ cập nhật giá `close`/`high`/`low` của cây nến cuối theo `latest_price` vừa lấy từ `1m`.
  3. Khi cache HTF hết hạn, dùng `concurrent.futures.ThreadPoolExecutor(max_workers=3)` để tải đồng thời `1m`, `1h`, `1d` trong cùng 1 nhịp RTT mạng (`~900 ms` tổng cộng thay vì `2,089 ms`).

#### 3.2. Tái sử dụng kết quả `m5_tape` cho giá Spot trong `load_and_preprocess_options` ([`src/hud/html_dashboard.py:230-245, 570-585`](../../src/hud/html_dashboard.py#L230-L245))
- **Hiện trạng:** `load_and_preprocess_options` gọi `fetch_live_cme_futures_price()` ở `L234` (tốn 1 HTTP request `GC=F?interval=1m&range=1d`), sau đó ở `L576` lại gọi `fetch_live_cme_m5_tape(limit=8, include_htf=True)` (tốn thêm 1 HTTP request `GC=F?interval=1m&range=5d`).
- **Cách sửa:**
  Trong `fetch_live_cme_m5_tape()`, ngay khi lấy được `latest_price > 0` từ response `1m`, cập nhật luôn `_LIVE_SPOT_CACHE["GC_FUTURES"] = (time.time(), float(latest_price), "YAHOO_GC_LIVE")`. Trong `load_and_preprocess_options()`, gọi `fetch_live_cme_m5_tape(limit=8, include_htf=True)` **trước** (hoặc khi `manual_spot is None` và `_LIVE_SPOT_CACHE` trống), nhờ đó `fetch_live_cme_futures_price()` lấy ngay giá từ `_LIVE_SPOT_CACHE` mà không phát sinh HTTP request thứ hai.
  - **Lưu ý Kiểm thử:** Giữ nguyên lời gọi `fetch_live_cme_futures_price()` tại `L234` để các unit test có `monkeypatch.setattr(..., "fetch_live_cme_futures_price", ...)` vẫn hoạt động 100% như cũ; chỉ cần khi `fetch_live_cme_m5_tape` chạy hoặc ngược lại, chia sẻ cache thông minh khi không bị monkeypatch.

#### 3.3. Nâng cấp `start_local_live_bridge_server` lên `ThreadingHTTPServer` + `2.0s` RAM Cache ([`src/hud/html_dashboard.py:2548-2615`](../../src/hud/html_dashboard.py#L2548-L2615))
- **Hiện trạng (`L2554-2607`):** Dùng `HTTPServer` đơn luồng và gọi trực tiếp `fetch_live_cme_m5_tape(limit=8, include_htf=(tf != "1m"))` trong `do_GET`, chặn luồng 1–2.5 giây mỗi lần trình duyệt poll.
- **Cách sửa:**
  1. Đổi `HTTPServer` sang `ThreadingHTTPServer` (từ `http.server import ThreadingHTTPServer`).
  2. Thêm bộ đệm RAM `_BRIDGE_RESPONSE_CACHE: dict[str, tuple[float, bytes]] = {}` với `TTL = 1.8` giây (và tận dụng `_HTF_TAPE_CACHE` 60 giây của Task 3.1).
  3. Khi trình duyệt gọi `/api/yahoo_gc?tf=1m`, nếu bản ghi trong `_BRIDGE_RESPONSE_CACHE` mới hơn `1.8s`, trả về ngay lập tức trong `< 2 ms`.

#### 3.4. Hợp nhất bộ hẹn giờ Polling trên trình duyệt ([`src/hud/neiro_terminal.py:1645-1699`](../../src/hud/neiro_terminal.py#L1645-L1699))
- **Hiện trạng:**
  - `connectLiveGoldOrderflowStream` (`L1650`) đặt `setInterval(pollLiveYahooChart, 5000)`.
  - `checkCloudSyncNow` (`L1691, 1697`) đặt `setInterval(checkCloudSyncNow, 10000)` và bên trong lại gọi `pollLiveYahooChart(true)` lần nữa.
- **Cách sửa:**
  - Khi đang chạy trên Local Bridge (`window.location.protocol === 'file:'` hoặc `localhost` / `127.0.0.1`), cho phép `pollLiveYahooChart` nhịp **`2500 ms`** (`2.5 giây`) vì server đã có RAM cache.
  - Trong `checkCloudSyncNow` (`L1691`), chỉ kiểm tra `version.json` để phát hiện bản build Options Chain mới (và chỉ gọi `pollLiveYahooChart(true)` nếu lần poll gần nhất đã cách `> 4000 ms`), tránh 2 request chồng nhau.

---

### TASK 4: Loại Bỏ Biểu Đồ Plotly 4-Panel "Bóng Ma" & Cơ Chế `--loop` Thông Minh Theo `mtime` (`src/hud/html_dashboard.py`)
**Mục tiêu:** Tiết kiệm ngay **`3,356 ms`** mỗi lần chạy và giảm chu kỳ `--loop` từ **`14.25s` xuống `< 300 ms`** khi file CSV không đổi.

#### 4.1. Ngắt lời gọi `build_plotly_figure` thừa trong `run_pipeline` & `generate_html_terminal` ([`src/hud/html_dashboard.py:1486, 1945-1953, 2430`](../../src/hud/html_dashboard.py#L1486))
- **Hiện trạng:**
  - `generate_html_terminal(df: pd.DataFrame, meta: dict, fig: go.Figure, fig_smile: go.Figure | None = None)` (`L1486`) tạo `plotly_div = fig.to_html(...)` ở `L1948-1952`, nhưng biến `plotly_div` **không được sử dụng ở bất kỳ đâu** trong f-string HTML (`L1955-2345`).
  - `run_pipeline()` (`L2430`) gọi `fig = build_plotly_figure(df_raw, meta)` tốn `2,756 ms` vô ích.
- **Cách sửa:**
  1. Đổi chữ ký hàm tại `L1486` thành:
     ```python
     def generate_html_terminal(
         df: pd.DataFrame,
         meta: dict,
         fig: go.Figure | None = None,
         fig_smile: go.Figure | None = None,
     ) -> str:
     ```
  2. Xóa đoạn `plotly_div = fig.to_html(...)` tại `L1948-1952` (vì `plotly_div` là biến chết không dùng).
  3. Trong `run_pipeline()` (`L2430`), truyền `fig=None` vào `generate_html_terminal(df_raw, meta, None, fig_smile)` thay vì gọi `build_plotly_figure(df_raw, meta)`.
  4. **Giữ nguyên hàm `build_plotly_figure(df, meta)` tại `L714`** để đảm bảo 100% tương thích với `tests/test_hud_smoke.py` và `tests/test_cngthctnhton_math_audit.py`.

#### 4.2. Tách Chu Kỳ Tĩnh (`Static Options Chain`) và Chu Kỳ Động (`Live Spot/Orderflow`) trong `--loop` ([`src/hud/html_dashboard.py:2640-2665`](../../src/hud/html_dashboard.py#L2640-L2665))
- **Hiện trạng (`L2641-2662`):**
  Trong vòng lặp `while True:`, mỗi 15 giây hệ thống gọi `clear_spot_cache()` rồi gọi `run_pipeline()` tính lại toàn bộ CSV Options Chain và ghi đè file `1.14 MB` `exports/index.html` + copy sang Google Drive.
- **Cách sửa:**
  1. Tạo bộ nhớ đệm cấp module `_STATIC_CHAIN_CACHE: dict[str, Any] = {}` lưu `(input_csv_path, mtime_tuple)` của `data/options_prices*.csv` cùng kết quả `df_normalized` đã chuẩn hóa.
  2. Trong `load_and_preprocess_options()`: nếu tập file `data/options_prices*.csv` có cùng `mtime_tuple` với `_STATIC_CHAIN_CACHE`, tái sử dụng ngay bản sao `df_raw = cached_df.copy(deep=True)` (`< 2 ms`) thay vì đọc lại CSV từ đĩa.
  3. Trong vòng lặp `if args.loop > 0:` (`L2641`):
     - Theo dõi `last_csv_mtime` và `last_full_html_ts`.
     - Chỉ render và ghi lại file nặng `exports/index.html` (+ đồng bộ Google Drive) khi:
       - Là vòng lặp đầu tiên (`iteration == 1`), HOẶC
       - `csv_mtime != last_csv_mtime` (có dữ liệu Options mới từ Scraper/Cloud), HOẶC
       - Đã qua `300 giây` (`5 phút`) kể từ lần ghi HTML cuối cùng.
     - Ở các nhịp lặp trung gian (mỗi 15 giây khi CSV không đổi): chỉ lấy giá live `GC=F` mới nhất và cập nhật nhẹ 2 file JSON (`exports/version.json` chứa `recent_candles`, `spot_price`, `updated_at` và `exports/tactical_levels.json` cho MT5 EA), mất **`< 250 ms`** và giảm **95% lượng ghi đĩa SSD / Google Drive**!

---

### TASK 5: Tinh Gọn Payload DOM/JSON & Khử Trùng Lặp Giao Diện Tác Chiến (`src/hud/neiro_terminal.py` & `src/hud/html_dashboard.py`)
**Mục tiêu:** Giảm dung lượng `exports/index.html` từ **`1,135 KB` xuống `~680 KB`**, giảm thời gian render HTML từ **`1,518 ms` xuống `< 350 ms`**, và loại bỏ các khối UI trùng lặp gây nhiễu mắt Scalper.

#### 5.1. Cắt tỉa `window.INITIAL_OPTIONS` & `squeeze_ladder` theo Hành lang Tác chiến (`Active Corridor`) ([`src/hud/neiro_terminal.py:305-335`](../../src/hud/neiro_terminal.py#L305-L335) & [`src/hud/html_dashboard.py:675-690`](../../src/hud/html_dashboard.py#L675-L690))
- **Hiện trạng:**
  - `neiro_terminal.py:308` dùng `for _, r in df.sort_values("strike").iterrows():` xuất toàn bộ `895` strikes (từ `$1,350` đến `$10,000`) vào `window.INITIAL_OPTIONS` (`389.6 KB`).
  - `meta["squeeze_ladder"]` xuất toàn bộ `895` strikes (`74.3 KB`).
- **Cách sửa:**
  1. Trong `neiro_terminal.py:305-335`:
     - Lọc hành lang tác chiến rộng `corridor_df`: giữ mọi strike nằm trong khoảng **`[spot - 600.0, spot + 600.0]`** HOẶC trùng với các mốc trụ cột (`call_wall`, `put_wall`, `gamma_flip`, `max_pain`, `major_call_oi_wall`, `major_put_oi_wall`). (Khoảng `±$600` tức `1,200` giá Vàng đã bao phủ gấp 10 lần biên độ giao dịch trong ngày nhưng loại bỏ được `> 60%` các strike rác ở `$1,350` hay `$10,000`).
     - Thay `iterrows()` bằng `df_corridor.to_dict(orient="records")` hoặc `itertuples(index=False)` để tạo `options_records` nhanh gấp 20 lần.
  2. Tương tự cho `squeeze_ladder`: chỉ giữ các khóa nằm trong hành lang `[spot - 600.0, spot + 600.0]` (giảm kích thước `INITIAL_META` từ `75.4 KB` xuống `< 22 KB`).

#### 5.2. Giới hạn số dòng DOM `<tr>` trong `build_microstructure_pinning_table_html` ([`src/hud/html_dashboard.py:1500-1615`](../../src/hud/html_dashboard.py#L1500-L1615))
- **Hiện trạng (`L1509`):** Duyệt `for row_idx, (_, row) in enumerate(df_sorted.iterrows()):` và xuất toàn bộ `320` dòng `<tr class="micro-strike-row" ...>` vào HTML, dù chỉ hiển thị `±10` dòng quanh Spot (`21` dòng).
- **Cách sửa:**
  - Sau khi xác định `spot_row_idx` (`L1504`), chỉ render các dòng có **`abs(row_idx - spot_row_idx) <= 35`** (tức tối đa `71` dòng quanh Spot, đủ cho mọi chế độ lọc `±10 / ±20 / ±35 Strikes` trên thanh công cụ).
  - Giữ nguyên logic `is_within_10 = abs(row_idx - spot_row_idx) <= 10` và `row_display_style = "" if is_within_10 else "display:none; "` cho các dòng được render.
  - **Kiểm chứng Bất biến Test:** Trong `test_microstructure_table_plus_minus_10_strikes_and_informed_bar`, `df_35` có `35` dòng $\implies$ mọi dòng đều thỏa mãn `abs(row_idx - spot_row_idx) <= 35`, do đó `html.count('data-strike="') == 35` và `html.count('style="display:none; "') == 14` **đạt 100%**.
  - Thay `df_sorted.iterrows()` bằng truy cập mảng/dict (`df_sorted.to_dict("records")`) để tăng tốc vòng lặp tạo chuỗi HTML.

#### 5.3. Khử trùng lặp 3 Thẻ Orderflow Tĩnh ở `KHỐI 5` & Thu Gọn Khối Nghiên Cứu Phụ Trợ ([`src/hud/html_dashboard.py:2045-2345`](../../src/hud/html_dashboard.py#L2045-L2345))
- **Hiện trạng:**
  - Ba chỉ số `Options Implied Forward`, `Lee-Ready Signed Options Hedging Pressure`, `BVC Cumulative Volume Delta & Kyle's λ` đang xuất hiện ở **3 nơi**:
    1. **Floating HUD trên Canvas** (`neiro_terminal.py:285-291` — có ID cập nhật realtime).
    2. **Thanh Header Bảng Pinning** (`html_dashboard.py:1622-1648` — nằm ngay cạnh bảng Strike).
    3. **3 Thẻ lớn trong KHỐI 5** (`html_dashboard.py:2177-2199` — **không có ID DOM**, dẫn đến số liệu bị đóng băng và lệch với HUD khi giá chạy live!).
- **Cách sửa:**
  1. Tại **KHỐI 5 (`html_dashboard.py:2171-2202`)**: Giữ nguyên tiêu đề `"KHỐI 5: BĂNG GIÁ & XUNG LỰC VOLUME M5"` (để thỏa mãn `test_html_dashboard.py:173`), nhưng **thay thế 3 thẻ trùng lặp không có ID (`L2177-2199`)** bằng một thanh trạng thái gọn nhẹ có gắn đúng các phản chiếu hoặc dẫn chiếu trực tiếp tới bảng Pinning & HUD, hoặc gắn `<details>` thu gọn cho các khối nghiên cứu dài bên dưới (`KHỐI 1: Volatility Smile`, `KHỐI 6: Bảng Tác Chiến`, `KHỐI 7: Từ Điển Thuật Ngữ Bỏ Túi`) để màn hình Scalping gọn trên 1 tầm mắt.
  2. **Lưu ý Bất biến Test:** Khi bọc `<details>` cho các khối phụ trợ, **BẮT BUỘC giữ nguyên toàn bộ văn bản tiêu đề và thứ tự xuất hiện trong mã nguồn HTML** (`KHỐI 1` $\to$ `KHỐI 2` comment $\to$ `KHỐI 3` $\to$ `KHỐI 5` $\to$ `BẢNG TÁC CHIẾN LƯỚT SÓNG TRONG NGÀY` $\to$ `TỪ ĐIỂN THUẬT NGỮ BỎ TÚI`) để `test_html_dashboard.py` pass 100%.

---

## 5. QUY TRÌNH KIỂM ĐỊNH & NGHIỆM THU CHO AI THỰC THI (VERIFICATION CHECKLIST)

AI thực thi sau khi hoàn tất 5 Task trên **BẮT BUỘC** chạy bộ lệnh nghiệm thu sau và báo cáo kết quả thực tế:

```powershell
# 1. Kiểm tra cú pháp và chuẩn định dạng Ruff
.venv\Scripts\python.exe -m compileall src tests
.venv\Scripts\python.exe -m ruff check src/ tests/

# 2. Chạy toàn bộ 277 Unit & Integration Tests (Bắt buộc 0 failed)
.venv\Scripts\python.exe -m pytest tests/ -q

# 3. Đo Benchmark Thực Nghiệm Cold Run & Warm Cached Run
.venv\Scripts\python.exe -c "import time; from src.hud.html_dashboard import run_pipeline; t0=time.perf_counter(); run_pipeline('data/options_prices_GCZ26.csv', 'exports/index.html'); t1=time.perf_counter(); run_pipeline('data/options_prices_GCZ26.csv', 'exports/index.html'); t2=time.perf_counter(); print(f'Cold Run: {(t1-t0)*1000:.1f} ms | Warm Run: {(t2-t1)*1000:.1f} ms')"

# 4. Kiểm tra dung lượng file exports/index.html (< 750 KB) và dung lượng toàn repo (< 15 MB)
```

### Tiêu chí Nghiệm thu Đạt (Definition of Done):
- [ ] `pytest tests/` đạt **100% pass (`258+ passed, 0 failed`)**.
- [ ] Cold Run giảm từ `14,246 ms` xuống **`< 2,000 ms`**; Warm Run (khi CSV `mtime` không đổi và HTF cache còn hạn) đạt **`< 400 ms`**.
- [ ] Dung lượng `exports/index.html` giảm từ `1,135.4 KB` xuống **`< 750 KB`**, số dòng `data-strike` trên dữ liệu thực tế `<= 71` dòng.
- [ ] Tuyệt đối không đụng chạm tới `mt5/Indicators/Neiro-Liquidity-Map-v2.mq5` và `mt5/Indicators/2TC-v10.mq5`.
- [ ] Cập nhật trạng thái `ADR-027` từ `Proposed` sang `Accepted & Implemented` trong `docs/decisions/ADR-027-end-to-end-latency-and-cockpit-optimization.md` và `docs/spec.md` sau khi hoàn thành.

