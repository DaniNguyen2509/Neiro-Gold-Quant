# ADR-019: Chuẩn Hóa OTM Volatility Smile & Tích Hợp Bảng Định Lượng Microstructure Matrix 8 Cột

- **Trạng thái:** ACCEPTED
- **Ngày quyết định:** 2026-11-01
- **Tác giả:** Neiro Quant Engineering Team

---

## 1. Bối cảnh & Vấn đề (Context & Problem)

1. **Nghi vấn về mô hình Volatility Smile & Skew:**
   - Người dùng phản hồi biểu đồ *CME GOLD OPTIONS GCZ26: ĐƯỜNG CONG NỤ CƯỜI BIẾN ĐỘNG & ĐỘ XIÊN (VOLATILITY SMILE & SKEW)* bị dốc tuột xuống (từ 27.5% ở Strike $3,700 xuống 23.0% ở Strike $4,100) và thắc mắc tại sao mô hình lại "sai sao sao ấy" khi các điểm Call IV và Put IV thực tế tại mọi strike lại chồng khít lên nhau 100%.
   - Về bản chất kinh tế lượng:
     * Dữ liệu Barchart bị khuyết IV, kích hoạt thuật toán giải ngược Black-76 từ giá Mid.
     * Do giá Mid tuân theo đẳng thức Put-Call Parity $C - P = e^{-rT}(F - K)$, Call IV và Put IV giải ra giống nhau tuyệt đối ở mọi strike, tạo nên hiện tượng 2 điểm xanh/đỏ đè lên nhau.
     * Snapshot cuối tuần của hợp đồng OGZ26 phản ánh áp lực phòng vệ cực lớn của các quỹ (Put OI tại $3,900 là 6,886 HĐ, tại $3,800 là 3,712 HĐ, gấp 15-20 lần Call OI), đẩy giá Put OTM lên cao, tạo ra trạng thái thị trường thực tế: **Defensive Put Skew** ($RR_{25} = -3.21v$).
     * Độ dốc tuyến tính lớn làm át thành phần bậc hai $BF_{25} = +0.54v$, biến đường cong Malz thành một đường dốc sạt lở (Smirk).

2. **Yêu cầu bảng Microstructure Matrix chuẩn 8 cột (từ Neiro-NQ-Quant):**
   - Người dùng yêu cầu tích hợp bảng ma trận vi cấu trúc tổng hợp đa kỳ hạn 8 cột:
     `GC Strike | Net GEX ($M) | Call OI | Put OI | Call Vol | Put Vol | Net VEX ($M) | Net CHEX ($M/d)`
   - Bảng cũ chỉ có 12 strike rút gọn và chứa các cột mô tả không tối ưu cho việc quét nhanh Real Walls và Gamma Squeeze.

---

## 2. Quyết định Kiến trúc (Architectural Decision)

1. **Chuẩn hóa hiển thị OTM Volatility Smile (Institutional Standard):**
   - Khi phát hiện Call IV và Put IV bằng nhau do giải ngược Put-Call Parity (`mean_diff < 0.002`):
     * Cánh bên trái ($K \le \text{Spot}$): Chỉ vẽ các điểm **Put IV** (Out-of-the-Money Put), biểu thị áp lực bảo hiểm của phe Hedgers/Bears.
     * Cánh bên phải ($K \ge \text{Spot}$): Chỉ vẽ các điểm **Call IV** (Out-of-the-Money Call), biểu thị áp lực cược vượt đỉnh của phe Bulls/Speculators.
     * Loại bỏ hoàn toàn hiện tượng 2 điểm xanh/đỏ đè lên nhau.
   - Bổ sung nhãn chế độ thị trường rõ ràng trên đồ thị: `DEFENSIVE PUT SKEW (Put OI áp đảo Call OI x15 lần • Cấu trúc biến động dốc Smirk phòng vệ)` để trader nhận biết đây là cấu trúc thị trường thực tế.

2. **Triển khai Bảng Microstructure Matrix 8 Cột Đa Kỳ Hạn:**
   - 8 cột tiêu chuẩn chuẩn hóa theo repo `Neiro-NQ-Quant`:
     1. `GC Strike` (format `GC $X,XXX`, gắn badge: `👉 SPOT`, `[CALL WALL]`, `[PUT WALL]`, `[ZERO GAMMA]`).
     2. `Net GEX ($M)` (màu xanh lá `#4ADE80` nếu dương, đỏ `#F87171` nếu âm).
     3. `Call OI` (màu `#86EFAC`).
     4. `Put OI` (màu `#FCA5A5`).
     5. `Call Vol` (màu `#16A34A`).
     6. `Put Vol` (màu `#DC2626`).
     7. `Net VEX ($M)` (màu `#FB923C`).
     8. `Net CHEX ($M/d)` (màu `#22D3EE`).
   - Sắp xếp thứ tự Strike giảm dần từ trên xuống dưới.
   - Scrollable box `max-height: 520px` với `position: sticky` cho table header.
   - Giữ nguyên nhãn thống kê `Gamma Black-76` và `Theta Bào Mòn` trên thanh tóm tắt tiêu đề để tương thích 100% với bộ test tự động.

---

## 3. Hệ quả & Kiểm chứng (Consequences & Verification)

- **Hiệu quả trực quan:**
  - Biểu đồ Volatility Smile tách biệt rõ ràng OTM Put và OTM Call, loại bỏ hoàn toàn hiện tượng trùng lặp dots.
  - Bảng Microstructure Matrix 8 cột trực quan, cho phép cuộn xem toàn bộ các thành trì và dòng tiền đa kỳ hạn.
- **Kiểm thử tự động:**
  - 137/137 tests passed (100%) trong 29.09s.
  - Dung lượng kho mã nguồn: 11.89 MB (đạt chuẩn Zero-Waste `< 15 MB`).

