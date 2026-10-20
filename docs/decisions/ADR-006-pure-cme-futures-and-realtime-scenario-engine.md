# ADR-006: Pure CME Gold Futures Positioning & Real-Time Market Maker Scenario Engine

## Bối Cảnh (Context)
Trong các phiên bản trước:
1. Hệ thống tìm Strike ATM bằng cách giải ngược chênh lệch Put-Call Parity `min(|Call_mid - Put_mid|)` trên dữ liệu chuỗi quyền chọn Barchart. Do dữ liệu quyền chọn thường là giá chốt sổ (Settlement) hoặc thanh khoản mỏng, mốc ATM bị neo vào mốc cũ (ví dụ 4,180 hoặc 4,200), lệch hẳn 30 - 50 giá so với giá tương lai thực tế ngoài thị trường (4,150).
2. Việc cố gắng tính toán và hiển thị giá Spot MT5 quy đổi từ Basis Contango gây nhiễu, do mỗi sàn MT5 (Exness, IC Markets, Pepperstone) có chênh lệch và thời gian cập nhật khác nhau. Trader giao dịch nhìn chart song song nên không cần cột MT5 quy đổi làm rối bảng tác chiến.
3. Dashboard chứa nhiều khối văn bản dài dòng, gây độ trễ nhận diện (Cognitive Latency), trader mất nhiều thời gian đọc hiểu thay vì nhìn thấy ngay hành động (Action) cần thực hiện trong 3 giây.

## Quyết Định (Decisions)
1. **Chuyển dịch 100% Thuần CME Gold Futures (`GC=F` / `GCZ26`):**
   - Loại bỏ hoàn toàn cột giá Spot MT5 và các nhãn quy đổi gây rối trên giao diện.
   - Kết nối trực tiếp luồng dữ liệu thời gian thực COMEX (`GC=F`) qua API gốc (zero dependencies, native urllib fallback), cập nhật giá realtime chính xác từng tick.
   - Khóa chặt Trục ATM trực tiếp theo giá Future realtime: `atm_strike = (strikes - live_futures).abs().idxmin()`.
2. **Triển khai Bộ Đánh Giá Kịch Bản Thời Gian Thực (Scenario Engine - `src/quant_engine/scenario_engine.py`):**
   - Định nghĩa 6 kịch bản hành vi Market Maker chuẩn hóa (KB-1 đến KB-6):
     * **KB-1: Giằng Co Nén Biên Độ (Pinning Box)** -> ĐỨNG NGOÀI (Cấm đánh breakout).
     * **KB-2: MM Chặn Bán Phòng Thủ Trần (Call Defense)** -> SELL BÁN ĐẢO CHIỀU (FADE).
     * **KB-3: BÁO ĐỘNG ĐỎ: MM Vỡ Trận Short (Gamma Squeeze)** -> BUY MUA ĐUỔI THEO MM.
     * **KB-4: MM Đệm Mua Bảo Vệ Sàn Đáy (Put Defense)** -> BUY BẮT HỒI (REBOUND).
     * **KB-5: BÁO ĐỘNG ĐỎ: Thủng Sàn & Xả Lũ (Air Pocket Slide)** -> CẤM BẮT ĐÁY / SELL BÁN THÁO.
     * **KB-6: Vùng Trung Lập (Neutral Floating)** -> KIÊN NHẪN CHỜ ĐỢI.
   - Khi giá realtime rơi vào kịch bản nào, dashboard tự động **BẬT SÁNG VIỀN & BÁO ĐỎ/BÁO XANH** kịch bản tương ứng.
3. **Thiết Kế Lại Giao Diện Dashboard Trực Quan - Siêu Tốc - Không Icon:**
   - Khối 1: Bảng Tác Chiến Tức Thì (Instant Action Command Banner) trên cùng hiển thị hành động trong 3 giây.
   - Khối 2: Thước đo vị trí giá so với chốt chặn MM (Visual Level Spine).
   - Khối 3: Ma trận 6 kịch bản thời gian thực.
   - Khối 4: KPI thống kê toàn cảnh.
   - Khối 5: Biểu đồ Plotly Net GEX & Greeks.
   - Khối 6: Bảng chiến lược lướt sóng Scalping & Swing thuần CME Futures.
   - Khối 7: Từ điển thuật ngữ bỏ túi 1 dòng ngắn gọn, tiếng Việt có dấu, tuyệt đối **không sử dụng icon trang trí**.

## Hệ Quả (Consequences)
- Loại bỏ hoàn toàn nguy cơ lệch giá ATM và sai lệch giá Spot MT5.
- Triệt tiêu hoàn toàn nghịch lý Take Profit cao hơn giá Sell hoặc thấp hơn giá Buy khi mốc biên chạm sát trục ATM.
- Trader nhìn vào màn hình trong 3 giây là biết ngay MM đang làm gì và action của mình là gì.
- Dung lượng repository tiếp tục được duy trì siêu nhẹ (< 10MB), 100% Cloud-Native không tốn RAM laptop.
- 100% kiểm thử pytest (93/93 tests) vượt qua thành công.
