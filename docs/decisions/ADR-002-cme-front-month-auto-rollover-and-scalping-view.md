# ADR-002: Dynamic CME Front-Month Auto-Rollover Engine & ATM ± 5 Strikes Scalping View

## Status
Accepted

## Date
2026-10-19

## Context
1. **Lệch bước giá Strike & Thiếu mốc 4180:**
   - Bot cào dữ liệu trước đây trỏ vào hợp đồng Tuần (Weekly Option `IG4V26`), sàn CME chỉ mở bước giá $25 (`4150, 4175, 4200`), làm khuyết mất mốc chiến thuật trọng yếu $4,180.00.
   - Hợp đồng Tháng chuẩn (`OGX26`) mở bước giá dày $5 quanh ATM (`4160, 4165, 4170, 4175, 4180, 4185, 4190, 4195, 4200, 4205`), cần thiết tuyệt đối cho giao dịch Scalping trong ngày.
2. **Nguy cơ chết hợp đồng khi đáo hạn (Rollover Fragility):**
   - Hợp đồng `OGX26` đáo hạn vào ngày 27/10/2026. Nếu hardcode mã hợp đồng, hệ thống sẽ bị tê liệt hoặc cào dữ liệu rỗng sau ngày 27/10.
   - Cần cơ chế tự động nhận diện và rollover sang `OGZ26` (Tháng 12), `OGF27` (Tháng 1/2027)... theo lịch sàn CME.
3. **Thang đo đồ thị bị loãng (Display Dilution):**
   - Chế độ hiển thị cũ vẽ 14–16 strikes (từ 4000 đến 4350), khiến các thanh GEX, Volume/OI của các mốc $5 bị thu nhỏ, khó theo dõi khi scalping nhanh.
4. **Sai lệch mốc ATM do báo giá đóng băng (Stale Quotes Distortion):**
   - Các mốc OTM xa thanh khoản thấp (ví dụ 4205) có thể có giá Call/Put cũ tình cờ sát nhau, đánh lừa công thức Put-Call Parity thông thường.

## Decision
1. **Động cơ tính lịch đáo hạn CME (Rulebook 120102.E):**
   - Cài đặt hàm `get_cme_option_expiry_date(year, contract_month)`: Tự động đếm lùi ngày làm việc thứ 4 trước ngày làm việc cuối cùng của tháng (M-1).
2. **Động cơ phân giải mã hợp đồng tự động (`resolve_front_month_cme_option`):**
   - Tự động quét lịch thời gian thực và sinh ra mã Front-Month active:
     - Trước 27/10/2026: `OGX26` (Tháng 11).
     - Từ 28/10/2026: Tự động chuyển sang `OGZ26` (Tháng 12).
     - Từ 26/11/2026: Tự động chuyển sang `OGF27` (Tháng 1/2027).
   - Tự động tạo URL Barchart tương ứng cho bộ cào Playwright.
3. **Dynamic DTE Engine:**
   - Tính toán thời gian đáo hạn DTE chính xác theo từng phút thay vì dùng hằng số cố định 38 ngày hay 30 ngày.
4. **Bộ lọc ATM theo thanh khoản thực (Liquid Strike Weighting):**
   - Áp dụng ngưỡng phân vị Open Interest + Volume (P50) trước khi tính Put-Call Parity, loại bỏ hoàn toàn các mốc "rác" thanh khoản thấp, khóa chặt mốc ATM tại đúng $4,180.00.
5. **Cửa sổ hiển thị ATM ± 5 Strikes (Scalping View):**
   - Giới hạn đồ thị ở đúng 5 mốc dưới ATM, mốc ATM, và 5 mốc trên ATM (`half = 5`), khớp hoàn hảo với góc nhìn `5 Strikes +/-` của Barchart.

## Consequences
- **Tự trị 100% (Zero Maintenance):** Không bao giờ cần can thiệp thủ công vào mã hợp đồng hay ngày đáo hạn khi thị trường chuyển tháng.
- **Tối ưu Scalping:** Đồ thị to, rõ, tập trung toàn bộ năng lực vào vùng chiến sự 20–25 giá quanh Spot.
- **Toán học chính xác:** Greeks bậc 2 (Vanna, Charm) và Gamma Walls phản ánh đúng 8.2 ngày còn lại của hợp đồng thay vì con số giả định 30 ngày.
