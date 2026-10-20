# ADR-005: Real-Time Dual-Feed Architecture & Adaptive Contango Basis Engine

## Status
Accepted

## Date
2026-10-20

## Context
1. **Hạn chế của phương pháp tính giá tĩnh từ Options Chain Snapshot:**
   - Trước đây, giá hợp đồng tương lai CME (`spot_price`) được tính gián tiếp bằng công thức Put-Call Parity:
     $$\text{Futures} = \text{ATM Strike} + e^{r \cdot T}(C_{\text{ATM}} - P_{\text{ATM}})$$
   - Vì bảng Options Chain của Barchart chỉ được đồng bộ định kỳ theo các mốc phiên (07:15, 12:30, 18:45 VN), khi thị trường biến động mạnh trong phiên (ví dụ: Vàng rơi từ $4,180 về $4,135), giá trên Tactical Dashboard bị trễ so với thị trường trực tiếp nếu không có feed giá liên tục.

2. **Khảo sát giải pháp lấy giá tự động:**
   - **Investing.com / vn.investing.com:** Bị loại bỏ vì không có Public API miễn phí, đặt toàn bộ hệ thống sau tường lửa Cloudflare Bot Management & TLS Fingerprinting (trả về lỗi `403 Forbidden` đối với mọi script tự động).
   - **cTrader OpenAPI (Pepperstone):** Đã tạo App (`Neiro-Quant-Live`) nhưng phải chờ xét duyệt KYC từ Spotware (1-3 ngày làm việc).
   - **Yahoo Finance (`yfinance` với mã `GC=F`):** Cung cấp feed giá CME Gold Futures thời gian thực (<1.5s latency), hoàn toàn miễn phí, không yêu cầu API key, không bị tường lửa và tiêu hao 0 MB dung lượng ổ cứng.
   - **Gold-API & Binance PAXG:** Hệ thống đã có sẵn module lấy giá vật chất giao ngay Spot XAU/USD chuẩn LBMA Luân Đôn.

## Decision
1. **Triển khai Kiến trúc Nguồn Giá Kép Độc Lập (Dual-Feed Engine):**
   - **Kênh 1 - CME Gold Futures (GCZ26):**
     - Hàm `fetch_live_cme_futures_price()` truy vấn trực tiếp qua `yfinance.fast_info` với ticker `GC=F`.
     - Bộ đệm In-Memory Thread-Safe Cache với TTL 5.0 giây chống spam network.
     - Fallback an toàn: Nếu mất mạng hoặc API lỗi, hệ thống tự động fallback về công thức Put-Call Parity từ Options Snapshot.
   - **Kênh 2 - Spot Gold XAU/USD (Chuẩn LBMA / MT5):**
     - Hàm `fetch_live_spot_gold_price()` truy vấn `Gold-API` (LBMA) với fallback thứ cấp `Binance PAXG`.

2. **Chuẩn hóa động cơ tính Dynamic Contango Basis:**
   - Tính toán Basis chênh lệch thực tế:
     $$\text{Basis} = \text{Spot XAU/USD} - \text{CME Futures}$$
   - Mở rộng biên kiểm duyệt tính hợp lệ (Plausibility Band) từ `[12.0, 32.0]` xuống `[5.0, 32.0]` USD để tiếp nhận trung thực các biến động co giãn chênh lệch Contango trong ngày mà không bị kẹp cưỡng bức về mức cố định `-24.0 USD`.
   - Cơ chế gắn nhãn nguồn minh bạch: `LIVE`, `CALIBRATED`, `WEEKEND_FALLBACK`.

3. **Tích hợp vào Tactical HUD Dashboard:**
   - Panel 1 hiển thị đường giá `◄ CME FUTURES: $X,XXX.XX` phản ánh giá thị trường hiện tại.
   - Thẻ KPI hiển thị song song cả 2 giá: `CME Gold Futures (GCZ26) ↔ Spot XAU/USD (Quy Đổi)` kèm nhãn Basis động `[LIVE]`.

## Consequences
- **Không còn độ trễ giá:** Terminal luôn phản ánh đúng nhịp đập thị trường vàng thế giới tại thời điểm mở trang.
- **Hoàn toàn tự động & 0 MB dung lượng:** Không cần bật phần mềm MT5, không cần chờ cấp quyền KYC cTrader, tuân thủ nghiêm ngặt tôn chỉ Zero-Waste Mandate (<15MB).
- **Tính toán chuẩn xác chiến thuật:** Các mốc quy đổi sang giá MT5/Pepperstone được cập nhật theo đúng chênh lệch Basis thực tế từng phút.
