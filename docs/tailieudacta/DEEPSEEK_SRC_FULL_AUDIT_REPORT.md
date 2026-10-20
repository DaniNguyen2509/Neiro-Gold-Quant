# BÁO CÁO THẨM VẤN & KIỂM ĐỊNH TOÀN DIỆN MÃ NGUỒN (DEEPSEEK-R1 ADVERSARIAL AUDIT)
> **Dự án:** Neiro-Quant v2.0 — Quantitative Gold Options Trading System  
> **Auditor Độc lập:** DeepSeek-Reasoner (R1 - Chain-of-Thought Full Adversarial Audit)  
> **Phương pháp luận:** Kỹ năng `doubt-driven-development` (Chế độ Phản biện Tuyệt đối — Anti-Rationalization Gate)  
> **Phạm vi kiểm định:** Toàn bộ thư mục `src/` (4 Cụm Module: Lõi Toán Vi cấu trúc, Máy trạng thái & Kịch bản MM, Pipeline Thu thập Dữ liệu, HUD Terminal)  
> **Ngày thực hiện:** 20/10/2026  

---

## 1. TỔNG QUAN PHIÊN THẨM VẤN ĐỐI KHÁNG

Phiên thẩm vấn được thực hiện bởi mô hình suy luận sâu **DeepSeek-Reasoner (R1)** thông qua API trực tiếp. Thay vì đánh giá hời hợt hoặc khen ngợi, prompt được cấu hình theo tư thế đối kháng nghiêm ngặt: **giả định tác giả quá tự tin, chủ động tìm kiếm các điểm gãy toán học, góc chết vi cấu trúc vàng CME/LBMA, lỗi đảo ngược hướng lệnh TP/SL, và vi phạm khế ước kỹ thuật (`docs/spec.md`)**.

### Bảng điểm Đánh giá Tín nhiệm Từng Phân khu

| Phân khu Module | Điểm số | Trạng thái | Ghi chú Trọng tâm |
|---|:---:|:---:|---|
| **Cụm 1A: Lõi Toán & Vi cấu trúc** (`synthetic.py`, `basis.py`, `dealer.py`, `institutional.py`, `air_pocket.py`) | **7.5 / 10** | ⚠️ Cần gia cố | Lỗi bỏ qua ngày lễ CME; thiếu chặn giờ đáo hạn 13:30 CT; chọn Wall thiếu lọc OTM; ATM chọn nhầm strike 0-bid; lan truyền NaN. |
| **Cụm 1B: Kịch bản MM & State Machine** (`level_state.py`, `scenario_engine.py`, `strategy.py`, `loader.py`) | **6.5 / 10** | 🔴 Nhiều lỗi Critical | KB-3/KB-5 kích hoạt nhầm trên strike lân cận thay vì Wall; TP đảo ngược hướng lệnh; điền hằng số fake Gamma 0.0037; fallback âm thầm dữ liệu benchmark. |
| **Cụm 2: Pipeline Cào & Chuẩn hóa** (`scraper.py`, `parser.py`, `collector/main.py`, `src/main.py`) | **7.0 / 10** | ⚠️ Vi phạm Spec | Fallback sang giá `Latest` (stale print) vi phạm nghiêm trọng Spec; tự bơm Gamma 0.0005; URL stale khi import; `src/main.py` chưa nối dây. |
| **Cụm 3: Tactical HUD & Terminal** (`html_dashboard.py`, `chart_exporter.py`) | **6.0 / 10** | 🔴 Lỗi Logic Invariant | Lỗi nghịch đảo TP > Entry ở lệnh Bán (SELL Fade & Call Wall Fade); lệch khoảng cách SL thực tế ($3.0) vs công thức Lot Size ($4.5). |

### 🎯 ĐIỂM SỐ TỔNG THỂ TOÀN BỘ CODEBASE: **6.8 / 10**
*(Đánh giá: Nền tảng kiến trúc rất tốt, 93/93 unit test đang chạy pass nhưng còn nhiều góc chết logic vi cấu trúc và lỗi bất biến TP/SL cần vá ngay trước khi live).*

---

## 2. DANH MỤC CÁC LỖI NGHIÊM TRỌNG (CRITICAL BUGS)

### 🔴 CRITICAL-01: Lỗi Đảo ngược Hướng Chốt Lời (TP Inversion) Trong Bảng Chiến Lược HUD
- **Vị trí:** `src/hud/html_dashboard.py` (Hàm `generate_html_terminal`, Strategy Table)
- **Bản chất lỗi:**
  1. **SELL Fade `strike_above`:** `Entry = strike_above - 1.00`, nhưng lại đặt `TP = spot`. Khi giá Spot tiệm cận sát bên dưới `strike_above` (khoảng cách < $1.0, ví dụ Spot = 4199.5, Strike = 4200 -> Entry = 4199.0), lệnh BÁN SHORT có `TP = 4199.5 > Entry = 4199.0`! Lệnh Bán nhưng chốt lời nằm trên điểm vào!
  2. **SELL Call Wall Fade:** Khi `call_wall == strike_above`, code đặt `TP = strike_above = call_wall`, trong khi `Entry = call_wall - 1.00`. Lệnh Bán lại có TP cao hơn Entry.
  3. **BUY Put Wall Fade:** Code đặt `TP = spot / strike_above`. Nếu giá Spot đang đè sát đáy Put Wall, `spot < Entry = put_wall + 0.50`, tạo ra lệnh Mua có TP thấp hơn Entry!
- **Hệ quả vi cấu trúc:** Nếu trader hoặc bot thực thi theo HUD, lệnh sẽ chốt lời âm ngay lập tức hoặc không thể khớp lệnh hợp lệ trên sàn MT5/cTrader.
- **Giải pháp triệt để:** Bắt buộc áp dụng bất biến toán học:
  ```python
  # Invariant enforcement
  if is_sell:
      assert tp < entry, f"SELL TP ({tp}) must be strictly below Entry ({entry})"
      tp = min(tp, entry - min_tp_distance)
  elif is_buy:
      assert tp > entry, f"BUY TP ({tp}) must be strictly above Entry ({entry})"
      tp = max(tp, entry + min_tp_distance)
  ```

### 🔴 CRITICAL-02: Kịch bản Vỡ trận (KB-3 & KB-5) Kích hoạt Sai trên Strike Thường Thay vì Wall Cấu Trúc
- **Vị trí:** `src/quant_engine/scenario_engine.py` (Hàm `evaluate_market_maker_scenarios`)
- **Bản chất lỗi:**
  - Điều kiện kích hoạt `KB-3 (MM Vỡ trận Short - Gamma Squeeze)` hiện tại được code là: `spot >= strike_above + buffer`.
  - Điều kiện kích hoạt `KB-5 (MM Vỡ trận Long - Waterfall)` là: `spot <= strike_below - buffer`.
  - Trong đó `strike_above` và `strike_below` chỉ là strike liền kề hiện tại (cách Spot chỉ 5–10 USD).
- **Hệ quả vi cấu trúc:** Bất kỳ nhịp dao động 1.5 giá thông thường nào vượt qua strike con lân cận cũng làm còi báo động "Market Maker vỡ trận Squeeze/Waterfall" hú vang, gây nhiễu loạn chiến lược và kích hoạt lệnh đuổi breakout sai thời điểm. MM chỉ thực sự bị ép vỡ trận khi giá xuyên thủng **Call Wall / Put Wall cấu trúc** (Strike có OI áp đảo) trong regime Short Gamma.
- **Giải pháp:** Chuyển điều kiện kích hoạt `KB-3` về `spot >= call_wall + buffer` và `KB-5` về `spot <= put_wall - buffer` (hoặc kiểm tra OI tại strike đó phải đạt chuẩn Wall).

### 🔴 CRITICAL-03: Chọn Tường Dealer (Call/Put Walls) Bỏ qua Bộ lọc OTM
- **Vị trí:** `src/quant_engine/dealer.py` & `src/quant_engine/strategy.py`
- **Bản chất lỗi:**
  - Hàm `find_walls` quét toàn bộ chuỗi Option để lấy strike có OI lớn nhất mà không kiểm tra vị thế OTM: Call Wall phải có $K \ge Spot$, Put Wall phải có $K \le Spot$.
- **Hệ quả vi cấu trúc:** Nếu một strike ITM sâu trong quá khứ còn tồn đọng OI lớn chưa đóng, nó sẽ bị chọn làm Call Wall (nằm dưới giá hiện tại) hoặc Put Wall (nằm trên giá hiện tại). Điều này làm điểm kích hoạt Squeeze (`call_wall + 1.80`) rơi xuống dưới giá Spot, gây kích hoạt Squeeze giả mạo ngay lập tức.
- **Giải pháp:** Lọc danh sách OTM trước khi tìm cực đại OI:
  ```python
  otm_calls = [q for q in quotes if q.strike >= spot]
  otm_puts = [q for q in quotes if q.strike <= spot]
  call_wall = max(otm_calls, key=lambda q: q.call_oi)
  put_wall = max(otm_puts, key=lambda q: q.put_oi)
  ```

### 🔴 CRITICAL-04: Parser và Loader Bơm Hằng số Fake Gamma (0.0037 & 0.0005) và Fallback Giá `Latest`
- **Vị trí:** `src/collector/parser.py`, `src/quant_engine/loader.py`, `src/hud/html_dashboard.py`
- **Bản chất lỗi:**
  - Khi cột `gamma` trong CSV bị thiếu hoặc bằng 0, code tự động điền `0.0037` (trong loader) và `0.0005` (trong parser).
  - Khi Bid hoặc Ask bằng 0, parser fallback sang lấy giá `c_last` (Latest).
- **Hệ quả:**
  - Vi phạm trực tiếp tuyên ngôn của Spec: *"Loại bỏ tuyệt đối: Cột Latest trên Barchart (stale prints)"* và *"Bảng Greeks mặc định 0DTE... phải tự giải ngược"*.
  - Việc bơm gamma giả tạo ra phân phối GEX "ma" trên toàn bộ các strike, bóp méo hoàn toàn vị thế Dealer Positioning và Gamma Flip.
- **Giải pháp:** Nếu thiếu gamma hoặc ở ngày 0DTE, bắt buộc gọi hàm giải ngược Black-76 IV và tính gamma toán học từ $d_1$; nếu strike không có thanh khoản (Bid/Ask = 0), đánh dấu `INVALID_QUOTE` và loại khỏi tính toán thay vì lấy giá Latest.

### 🔴 CRITICAL-05: Thuật toán Xác định Ngày Đáo hạn Bỏ qua Lễ CME và Giờ Cutoff 13:30 CT
- **Vị trí:** `src/quant_engine/synthetic.py` (`get_cme_option_expiry_date`, `resolve_front_month_cme_option`)
- **Bản chất lỗi:**
  - Hàm đếm lùi ngày làm việc chỉ xét `weekday < 5` mà không có lịch nghỉ lễ CME (Thanksgiving, Christmas, Good Friday), gây lệch 1 ngày đáo hạn thực tế.
  - Hàm kiểm tra đáo hạn chỉ so sánh `exp_date >= now.date()`. Vào ngày đáo hạn (Expiration Day), sau 13:30 CT (khi hợp đồng đã tất toán), hệ thống vẫn trả về hợp đồng cũ cho tới nửa đêm thay vì tự động rollover sang hợp đồng tháng kế tiếp!
- **Hệ quả:** Trong buổi chiều ngày đáo hạn, hệ thống tiếp tục cào và hiển thị dữ liệu của một hợp đồng đã chết.
- **Giải pháp:** Thêm danh sách ngày lễ COMEX và kiểm tra mốc thời gian cutoff `13:30 CT` (`18:30 UTC`).

---

## 3. DANH MỤC CÁC LỖI MỨC ĐỘ CAO (HIGH SEVERITY)

1. **Lỗi Độ rộng Dải Basis Quá Rộng:** `src/quant_engine/basis.py` cài đặt dải kiểm tra spread từ `5.0` đến `32.0` USD (Spec quy định `21.0 - 27.0` USD), đồng thời không kiểm tra dấu Contango (có thể chấp nhận nhầm giá trị Backwardation dương).
2. **Lỗi Đồng bộ Múi giờ trong Tin tức Blackout:** `src/quant_engine/strategy.py:check_news_blackout` so sánh trực tiếp `now_utc` và `event`. Nếu một bên là naive datetime và một bên là timezone-aware, Python sẽ crash với lỗi `TypeError`.
3. **Lỗi Sai số Dải 0.85-Sigma:** `src/quant_engine/strategy.py:compute_expected_move` tính `0.85 * straddle`. Do Straddle theo công thức Brenner-Subrahmanyam chỉ bằng $\approx 0.7979\sigma$, nên dải này thực chất chỉ là $0.678\sigma$ (độ tin cậy chỉ 50%, không phải 60% / 0.85σ).
4. **Lỗi Mislabeled "Delta Flow":** `src/quant_engine/loader.py:compute_tactical_matrix` tính `callDeltaFlow = callVolume * MULT * scale` mà hoàn toàn không nhân với hệ số Delta nào, gây hiểu nhầm Volume quy đổi thành Delta Flow.
5. **Lỗi Lệch Khoảng cách SL vs Lot Size trên HUD:** Bảng chiến lược hiển thị `Hard SL ($4.5)` nhưng thực tế điểm SL đặt cách Entry chỉ $3.0. Hàm tính lot size lại dùng tham số $4.5, gây sai lệch tỷ lệ rủi ro/vốn.
6. **Lỗi State Machine không phát ra `ABSORPTION_DEFENDED`:** `src/quant_engine/level_state.py` định nghĩa enum `ABSORPTION_DEFENDED` theo Spec nhưng code logic chỉ luôn phát ra `WALL_DEFENDED`.
7. **Lỗi Âm thầm Nạp Dữ liệu Benchmark Mẫu:** `src/quant_engine/loader.py:load_options_data` khi không tìm thấy file thay vì raise Exception hoặc cảnh báo rõ ràng thì lại âm thầm trả về `BENCHMARK_GCZ26_DATA`, tiềm ẩn nguy cơ xuất bản dữ liệu giả lập lên web live.
8. **Lỗi URL Scraper Bị Cố định khi Import:** `src/collector/scraper.py` gán `DEFAULT_BARCHART_URL = get_dynamic_barchart_url()` ở phạm vi toàn cục khi import module, khiến URL không được cập nhật động khi chạy daemon qua ngày rollover.

---

## 4. KẾ HOẠCH HÀNH ĐỘNG KHẮC PHỤC (RECONCILIATION PLAN)

Theo nguyên tắc của kỹ năng `doubt-driven-development`, các phát hiện trên đã được thẩm tra và đối chiếu trực tiếp vào từng dòng mã nguồn. Kế hoạch vá lỗi được phân thành 3 đợt:

### Đợt 1: Vá Khẩn cấp các Lỗi Critical Invariant & Microstructure
- [ ] **Patch 1 (HUD Strategy Invariants):** Sửa toàn bộ logic tính TP trong `src/hud/html_dashboard.py` đảm bảo bất biến $TP < Entry$ cho Short và $TP > Entry$ cho Long; đồng bộ khoảng cách SL thực tế vào hàm tính Lot.
- [ ] **Patch 2 (Scenario Engine Walls):** Chuyển điều kiện kích hoạt `KB-3` và `KB-5` trong `src/quant_engine/scenario_engine.py` sang bám theo `call_wall` và `put_wall` cấu trúc thay vì strike con.
- [ ] **Patch 3 (OTM Walls Enforcement):** Thêm bộ lọc bắt buộc Call Wall phải OTM ($K \ge Spot$) và Put Wall phải OTM ($K \le Spot$) trong `dealer.py` và `strategy.py`.
- [ ] **Patch 4 (Zero Fake Greeks & No Latest):** Loại bỏ việc điền default gamma 0.0037/0.0005 và fallback `Latest` trong `parser.py` và `loader.py`.
- [ ] **Patch 5 (CME Cutoff & Expiry Roll):** Cập nhật `synthetic.py` để rollover hợp đồng ngay sau 13:30 CT vào ngày đáo hạn và tích hợp kiểm tra ngày lễ.

### Đợt 2: Tinh chỉnh Định lượng & Đồng bộ Spec
- [ ] Chuẩn hóa công thức 0.85-Sigma Move nhân đúng hệ số $1 / 0.7979$.
- [ ] Khắc phục lỗi so sánh múi giờ trong `check_news_blackout`.
- [ ] Siết chặt dải kiểm tra Basis $[21.0, 27.0]$ USD và kiểm tra dấu âm Contango.
- [ ] Kích hoạt trạng thái `ABSORPTION_DEFENDED` trong `level_state.py`.
- [ ] Cảnh báo rõ ràng và không cho phép âm thầm nạp benchmark giả lập trong môi trường Production.

### Đợt 3: Kiểm thử Hồi quy TDD Toàn diện
- [ ] Bổ sung các bài test mới vào `tests/` mô phỏng chính xác các tình huống biên do DeepSeek-R1 phát hiện.
- [ ] Chạy lại toàn bộ bộ kiểm thử để đảm bảo 100% tests vượt qua chuẩn mực thể chế.
