# ADR-032: Kiến Trúc 2-Panel Song Song Tách Rời Chart & Tích Hợp Session Volume Profile (POC / VAH / VAL)

## Trạng thái (Status)
Đã chấp thuận & Triển khai (Approved & Implemented) — Ngày 24/11/2026.

## Bối cảnh (Context)
1. **Vấn đề chồng lấn giao diện (UI Overlap Bottleneck):**
   Trước đây, Terminal sử dụng 1 thẻ `<canvas id="neiro-canvas">` duy nhất với thuộc tính `position: absolute; width: 100%` phủ đè lên toàn bộ biểu đồ nến TradingView/Lightweight Charts. Dàn 5 cột Greeks Profile (`FLOW | GEX | VEX | CHEX | THETA`) chiếm gần 340px ở phía mép phải.
   Hậu quả: Khi giá nến chạy về vùng hiện tại ở mép phải chart, các cây nến M1 mới nhất bị dàn thanh bar và nhãn số của Profile che khuất, làm giảm khả năng quan sát hành động giá (Price Action) của trader.
2. **Nhu cầu đối soát dòng tiền thực tế (Realized Volume at Price):**
   Bên cạnh các thành trì dự báo tương lai của Options (GEX/VEX/CHEX), trader cần một công cụ đo lường chính xác khối lượng khớp thực tế của các cây nến trong ngày (Session Volume Profile) để định vị **Point of Control (POC - Mức giá gom hàng nhiều nhất)**, **VAH (Value Area High)**, và **VAL (Value Area Low)**.

## Quyết định Kỹ thuật (Decision)
Triển khai kiến trúc **2-Panel Side-by-Side Tách Rời Hoàn Toàn**:

1. **Panel Trái: Pure Candlestick Chart (`#tv-chart-wrapper` - Chiếm ~70% bề ngang):**
   - Dành 100% không gian hiển thị cho nến cTrader (`XAUUSD-F`) sạch sẽ, không bị bất kỳ thanh bar nào đè lên.
   - Lớp phủ Canvas Overlay trên Panel Trái chỉ vẽ các đường cản/hỗ trợ tinh gọn:
     - **`POC` (Point of Control):** Đường vàng nét đứt nổi bật kèm nhãn `★ POC (Vol Max) $XXXX · XXXX HĐ`.
     - **`VAH` (Value Area High):** Đường xanh nét đứt (vùng giá trị trên 70%).
     - **`VAL` (Value Area Low):** Đường đỏ nét đứt (vùng giá trị dưới 70%).
     - Call Wall, Put Wall, Zero Gamma Flip và FVG (không vẽ nhãn CVD/VPIN đè lên đường giá realtime `F0 LIVE`).

2. **Panel Phải: Dedicated Orderflow & Greeks Matrix (`#neiro-profile-wrapper` - Chiếm ~30% / 340px):**
   - Đặt độc lập bên phải sát trục tung Y, có background `#080B12` và header riêng.
   - Thẻ `<canvas id="neiro-profile-canvas">` vẽ đầy đủ **6 cột**:
     1. **`VOL`**: Khối lượng khớp nến Volume-at-Price (tính từ 360 nến cTrader M1), tự động highlight rực rỡ màu vàng tại mức POC.
     2. **`FLOW`**: Net Options Volume vs Open Interest (Whale Tracker).
     3. **`GEX`**: Net Gamma Exposure (MM Hedging).
     4. **`VEX`**: Vanna Exposure.
     5. **`CHEX`**: Charm Exposure.
     6. **`THETA`**: Theta Decay.
   - Cột ngoài cùng bên phải hiển thị nhãn giá Strike tương ứng (`$2645`, `$2650`...).
   - **Đồng bộ trục Y (Y-Axis Lock):** Mỗi khi chart nến bên trái zoom in/out hoặc cuộn lên xuống, vị trí các thanh Profile ở Panel Phải tự động dịch chuyển khớp 100% theo pixel tọa độ giá (`priceToCoordinate`).

3. **Thuật toán Client-Side Session Volume Profile (`computeVolumeProfile`):**
   - Phân bổ 360 cây nến M1 cTrader vào các bin giá \$1.0.
   - Tìm $POC = \arg\max (\text{VolByBin})$.
   - Mở rộng vùng giá trị 70% từ POC sang 2 phía trên/dưới để xác định VAH và VAL.
   - Tổng hợp khối lượng nến theo từng bước Strike Options (\$5) để hiển thị trên cột `VOL`.
   - Thời gian tính toán: **< 0.15ms** trên client-side JavaScript.

4. **Nút Bật/Tắt Linh Hoạt (`#btn-toggle-profile`):**
   - Cho phép trader 1-click ẩn/hiện Panel Phải. Khi ẩn, chart nến Panel Trái tự động co giãn full 100% màn hình.
   - Responsive trên màn hình di động (< 900px): Mặc định ẩn Panel Phải để tránh tràn ngang màn hình (zero horizontal overflow).

## Kiểm Thử & Nghiệm Thu (Verification)
- **Unit Test:** `test_adr032_volume_profile_and_side_by_side_panels` trong `tests/test_neiro_terminal.py` pass 100% với Node.js benchmark.
- **Playwright E2E:** `test_adr029_chart_height_toggle_and_mobile_no_overflow` pass 100% (test click `#btn-toggle-profile`, chart tự động co giãn từ ~1060px lên 1400px, mobile zero overflow).
