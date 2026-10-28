# ADR-014: Quantitative Microstructure Greeks & Pinning Table (ATM & Dealer Walls)

## Status
Accepted

## Date
2026-10-28

## Context
1. **Thiếu thấu thị vi mô mức Strike (Strike-Level Blindspot):** Các chỉ số vĩ mô toàn cục (Net GEX, Net VEX, Net CHEX) cung cấp góc nhìn tổng quan về trạng thái thị trường (Long Gamma vs Short Gamma). Tuy nhiên, khi giá vàng nén biên độ siêu hẹp ($4,065–$4,070) trước các tin tức vĩ mô lớn (FOMC, Core PCE, GDP), trader không có cái nhìn cụ thể về từng mức Strike trọng yếu để hiểu *tại sao* giá không thể bứt phá.
2. **Cơ chế Pinning & Bào mòn Theta vô hình:** Trader nhỏ lẻ thường cho rằng giá đứng yên là do thị trường "chờ tin", mà không nhận ra đây là chiến lược chủ động của Market Maker nhằm tối đa hóa việc thu tiền phế quyền chọn qua đêm thông qua đỉnh bào mòn Theta ATM ($\Theta \approx \$158.03$/HĐ/ngày) và Gamma cực đại.
3. **Cần bảng định lượng chuẩn tắc trực quan:** Bổ sung một khối bảng vi cấu trúc chuyên dụng ngay trên Dashboard hiển thị chi tiết Call OI, Put OI, Volume, Gamma Black-76, Theta hàng ngày, Net GEX và phân loại tác chiến vi cấu trúc tự động.

## Decision
1. **Xây dựng hàm `build_microstructure_pinning_table_html()`:**
   - Được nhúng trực tiếp vào [src/hud/html_dashboard.py](../../src/hud/html_dashboard.py) tại Khối 6 (ngay dưới Băng giá M5 Orderflow Pulse và trên Bảng Chiến Lược Tác Chiến).
2. **Chọn lọc Strike tác chiến động (Dynamic Strike Selector):**
   - Luôn khóa trúng Sàn bê tông Put Wall ($4,000) và Trần cản tâm lý Call Barrier ($4,100).
   - Tự động quét các bước đệm thanh khoản lớn ($4,050, $4,080) và đệm mỏng ($4,030).
   - Tự động quét mịn bước giá vi mô $5 quanh ATM ($4,060, $4,065, $4,070, $4,075).
3. **Công thức định lượng Black-76 chuẩn xác:**
   - Gamma Black-76: $\Gamma = \frac{e^{-rT} \cdot \phi(d_1)}{F \cdot \sigma \cdot \sqrt{T}}$, hiển thị theo đơn vị $\times 10^{-4}$.
   - Theta bào mòn theo ngày (100 oz COMEX Contract): $\Theta_{\text{daily}} = \left( \frac{F \cdot \phi(d_1) \cdot \sigma}{2\sqrt{T}} \cdot e^{-rT} \right) \times \frac{100}{365}$.
   - Net GEX ($M/1% move): $GEX = (Call GEX - Put GEX)$.
4. **Nhận diện & Gắn nhãn Vi cấu trúc tự động:**
   - Strike gần Spot nhất được gắn badge vàng neon `SPOT $4,061.10`.
   - Strike đạt đỉnh Gamma và Theta được tô đậm vàng kim `#FACC15` kèm nhãn `TÂM BÃO PINNING (Theta cực đại)` / `(Gamma cực đại)`.
   - Các mức cản/đỡ được gắn nhãn tương ứng: `Sàn chính Put Wall`, `Hỗ trợ đệm vi mô dày đặc`, `Vùng vi mô Positive GEX`, `Chốt chặn đệm phe Call`, `Trần cản tâm lý số tròn`.

## Consequences
- **Trực quan hóa tức thời:** Trader nắm bắt chính xác lý do toán học giá bị giam cầm trong biên độ 5 giá.
- **Ngăn chặn cược bẫy (Anti-Chop Guard):** Cảnh báo trader không mua/bán đuổi trong vùng tâm bão Pinning khi Theta đang bào mòn cực đại.
- **Tương thích toàn diện:** Tự động đồng bộ mỗi 60 giây trong script chạy nền `Chay_Live_Terminal.bat` và trên Web Terminal GitHub Pages.
