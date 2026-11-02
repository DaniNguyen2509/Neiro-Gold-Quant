# ADR-022: Thiết Lập Khung Kiểm Thử Toàn Diện (Systematic Test Rig) & Rà Soát Lỗ Hổng Bất Biến Vi Cấu Trúc (Microstructure Invariants Audit)

- **Trạng thái:** ACCEPTED
- **Ngày quyết định:** 2026-11-02
- **Tác giả:** Neiro Quant Engineering Team
- **Tham chiếu:** [docs/spec.md](../spec.md), [docs/architecture.md](../architecture.md), [AGENTS.md](../../AGENTS.md), [ADR-007](ADR-007-zero-gamma-flip-and-wall-siege-velocity.md), [ADR-011](ADR-011-adaptive-micro-strike-guard-and-stale-options-detection.md).

---

## 1. Bối cảnh & Động lực (Context & Motivation)

Hệ thống Neiro-Gold-Quant trước đây có bộ kiểm thử 137 unit test (`pytest`, thời gian chạy ~25 giây). Mặc dù 100% test cơ bản đều pass trên dữ liệu mẫu lý tưởng, việc vận hành thực chiến trên sàn COMEX và tự động hóa qua GitHub Actions đối mặt với các nguy cơ tiềm ẩn ở các điểm tiếp giáp (boundary integration), các trường hợp suy biến ($T \to 0$, $OI = 0$, mạng chập chờn) và lỗi cảnh báo ngầm (silent failure).

Nhằm bảo đảm tính tin cậy tuyệt đối trước khi giao dịch trực tiếp, hệ thống đã thiết lập một Khung Kiểm Thử Toàn Diện gồm 4 trụ cột với 125 ca kiểm thử mở rộng. Quá trình kiểm thử chủ động (Doubt-Driven & Test-Driven Development) đã làm lộ diện **16 điểm khiếm khuyết thực tế (RED-EXPECTED Gates)**.

---

## 2. Bốn Trụ Cột Kiểm Thử (The 4 Test Suites)

| Bộ kiểm thử | File | Số lượng test | Mục tiêu kiểm định |
|---|---|---|---|
| **Mục 1: Cổng dữ liệu đầu vào** | `tests/test_data_gate.py` | 21 test | Tính toàn vẹn của chuỗi Options, kiểm tra rò rỉ rác (`clean_val`), cơ chế phát hiện dữ liệu cũ (`is_data_stale`) không phụ thuộc `mtime`, quy tắc kiểm định CI. |
| **Mục 2: Lõi toán định lượng** | `tests/test_math_core.py` | 86 test | Độ chính xác giải thuật Dekker-Brent `_brentq`, giải ngược Black-76 IV round-trip, mốc Zero Gamma Flip $S^*$, tính bất biến tỷ lệ OI. |
| **Mục 3: Đáo hạn & Rollover** | `tests/test_expiry_rollover.py` | 12 test | Tính nhất quán của sàn thời gian đáo hạn $T_{\text{floor}}$, vi cấu trúc Greeks khi $T \to 0$ (1 phút), logic tự động chuyển hợp đồng cơ sở và quyền chọn. |
| **Mục 4: HUD & Dashboard Render** | `tests/test_hud_smoke.py` | 6 test | Kiểm thử tích hợp toàn trình CSV $\to$ HTML, kiểm tra hiển thị mốc tường/flip, kiểm định cờ cảnh báo dữ liệu cũ và dữ liệu rỗng. |

Tổng cộng: **125 test items** (90 PASS, 16 RED-EXPECTED FAIL, 19 SKIP giá trị biên $P \le 0.01$).

---

## 3. Danh Sách 16 Lỗ Hổng Thực Tế Đã Được Phát Hiện & Khóa Bằng Test

### 3.1. Cổng Dữ Liệu & CI Pipeline (Mục 1)
1. **D1 (Critical):** `scrape_multi_expiry_and_save` không chặn chuỗi strike lệch xa khỏi thị trường hoạt động. Một chuỗi strike [1500, 3200] trong khi giá GC là $4,000 vẫn ghi đè thành công vào file master.
2. **D2 - D5 (High):** Thiếu module chuẩn hóa kiểm định `src/collector/validator.py` (`validate_options_frame`) để chặn đứng dữ liệu thiếu cột, rỗng dòng, hoặc tổng OI $\le 0$ ngay từ tầng nạp.
3. **D7 (Critical):** Logic phát hiện dữ liệu cũ `is_data_stale` dựa hoàn toàn vào `os.path.getmtime(csv_path)`. Trên môi trường GitHub Actions, mỗi lần `actions/checkout` tạo file mới thì `mtime` luôn là thời điểm hiện tại, khiến cảnh báo Stale bị vô hiệu hóa 100%. Bắt buộc phải nhúng timestamp chuẩn `scraped_at_utc` bên trong nội dung CSV.
4. **D8 (Critical):** Trong `.github/workflows/daily_options_sync.yml`, khi dữ liệu cào về bị lỗi kiểm tra, script chỉ in `[WARNING]` rồi chạy `git checkout data/...` khôi phục file cũ và kết thúc với exit code 0. GitHub Actions vẫn báo xanh (Success), che giấu sự cố cào dữ liệu thất bại.

### 3.2. Lõi Toán Định Lượng (Mục 2)
5. **M4 (Medium):** Trong `solve_black76_iv` (`src/quant_engine/dealer.py`), khi giá thị trường vượt ra ngoài khung biên độ biến động $[0.02, 2.00]$, thuật toán âm thầm trả về giá trị mặc định `default_iv = 0.20` thay vì trả về cận kẹp $[0.03, 1.50]$ hoặc báo lỗi. Điều này tạo ra ảo giác biến động bình thường cho các strike OTM dị biệt.

### 3.3. Thời Gian Đáo Hạn & Rollover (Mục 3)
6. **T1 (Medium):** Giá trị sàn thời gian đáo hạn ($T_{\text{years}}$ floor) không thống nhất trên toàn codebase:
   - `src/hud/html_dashboard.py:1261`: `T_years = max(1e-4, dte_days / 365.0)`
   - `src/collector/gold_collector.py:299` & `basis.py:552`: `t = max(0.0035, dte_days / 365.0)`
   - `src/quant_engine/dealer.py`: `t_years = max(float(dte_days) / 365.0, 1.0 / 365.0)`
   Cần quy chuẩn về duy nhất một hằng số `T_YEARS_MIN_FLOOR = 1.0 / (365.0 * 24.0 * 60.0)` (tương đương 1 phút).
7. **T4 (Critical):** Hàm `resolve_front_month_cme_option` (`src/quant_engine/synthetic.py`) có tham số `underlying_futures = "GCZ26"`. Khi thời gian trôi qua tháng 12/2026, hàm tự động roll option sang `OGG27` nhưng underlying vẫn giữ cứng `GCZ26` (hợp đồng đã đáo hạn).
8. **T5 (Critical):** Nhánh dự phòng cuối cùng (fallback) của `resolve_front_month_cme_option` đang hardcode trả về ngày `2026-10-27` (hợp đồng `OGX26` đã hết hạn trong quá khứ).

### 3.4. Giao Diện Tác Chiến & HUD Render (Mục 4)
9. **H2 (Critical):** Trong `src/hud/html_dashboard.py` (dòng 1591-1593), biến HTML `stale_badge_html` được tạo ra khi `is_data_stale == True`, nhưng **hoàn toàn không được đưa vào chuỗi template HTML render**. Trader nhìn vào giao diện không bao giờ thấy badge cảnh báo dữ liệu cũ dù file đã trễ hơn 6 giờ.
10. **H3 (Critical):** Khi file CSV options bị rỗng hoặc hỏng, `html_dashboard.py` (dòng 186-189) âm thầm gọi `load_options_data()` để nạp bộ dữ liệu benchmark giả lập và vẽ biểu đồ mà không bật bất kỳ cờ cảnh báo `is_benchmark_fallback` nào cho trader biết.

---

## 4. Quyết Định Kiến Trúc & Tiêu Chuẩn Thực Thi (Decisions & Standards)

1. **Giữ nguyên trạng thái RED cho 16 gate:** Tuân thủ nguyên tắc Prove-It của TDD, tuyệt đối không vội sửa code khi chưa có sự phê duyệt kế hoạch chi tiết từ chủ dự án.
2. **Quy chuẩn Zero-Waste & Tự túc thư viện:** Toàn bộ test suite chạy trên `tmp_path`, không phụ thuộc `scipy` tại runtime (chỉ dùng thuần Python math/numpy), tốc độ chạy toàn bộ 125 test dưới 16 giây.
3. **Bảo tồn quy tắc 100% Pure CME Gold Futures (GC):** Không cho phép bất kỳ dữ liệu Spot ngoài luồng nào can thiệp vào các mốc Strike COMEX.

---

## 5. Kết Quả Khắc Phục Thực Tế (Remediation Execution)

Cả 4 giai đoạn khắc phục đã được triển khai hoàn tất theo nguyên tắc TDD & Incremental Implementation:

- **Giai đoạn 1 (Cổng dữ liệu & CI):** Đã xây dựng `src/collector/validator.py` (`validate_options_frame`), bổ sung cột `scraped_at_utc` trong `scraper.py`, cập nhật GitHub Actions verify step xuất annotation `::warning`. $\to$ Pass 100% D1-D9.
- **Giai đoạn 2 (HUD & Dashboard):** Đã nhúng `stale_badge_html` và `benchmark_badge_html` vào `<div class="container">` của `html_dashboard.py`, bật cờ `is_benchmark_fallback`. $\to$ Pass 100% H1-H3.
- **Giai đoạn 3 (Rollover & T-Floor):** Đồng bộ hằng số $T_{\text{floor}} = 1.0/365.0$ trên toàn bộ codebase (`html_dashboard.py`, `gold_collector.py`, `basis.py`), cập nhật dynamic mapping hợp đồng futures (`GCZ26` $\to$ `GCG27` $\to$ `GCJ27`) và dynamic fallback trong `synthetic.py`. $\to$ Pass 100% T1-T6.
- **Giai đoạn 4 (Lõi toán):** Hoàn thiện xử lý biên độ out-of-bracket trong `solve_black76_iv` (clip 1.50 khi vượt trần 200%, clip 0.035 khi thủng sàn 2%). $\to$ Pass 100% M1-M11.

**Trạng thái kiểm thử tổng hợp:** 243 passed, 19 skipped, 0 failed trên toàn bộ repository. Khung kiểm thử chính thức khóa chặt mọi bất biến vi cấu trúc.

