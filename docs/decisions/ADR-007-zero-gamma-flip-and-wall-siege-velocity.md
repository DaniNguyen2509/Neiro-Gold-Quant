# ADR-007: Zero Gamma Flip Continuous Root Solver & Intraday Wall Siege Velocity Ratio

## Bối Cảnh (Context)
1. **Đường Zero Gamma (Gamma Flip Line - $S^*$):**
   - Trong thị trường phái sinh quyền chọn vàng CME (Gold Options GCZ26), Market Maker (MM) duy trì phòng hộ delta động (Dynamic Delta Hedging). Khi giá nằm trong vùng Long Gamma ($\sum \text{NetGEX} > 0$), MM buộc phải "mua thấp bán cao" (bán khi giá tăng, mua khi giá giảm) để tái cân bằng delta, triệt tiêu biến động và tạo môi trường sideway / Mean-reversion. Ngược lại, khi giá rớt xuống vùng Short Gamma ($\sum \text{NetGEX} < 0$), MM buộc phải "bán tháo khi giá giảm, mua đuổi khi giá tăng", kích hoạt đà bão giá (Trend-following / Breakout Momentum).
   - Trước đây, hệ thống chỉ xem xét GEX tĩnh tại các strike rời rạc hoặc mốc strike đảo dấu tuyến tính. Cách làm này bỏ qua độ cong lồi (convexity) của mô hình Black-76 và độ trôi lognormal $e^{-0.5\sigma^2 T}$ (bất đẳng thức Jensen), dẫn đến sai số 5 - 15 USD trên giá vàng.
2. **Đo Lường Tốc Độ Thay Đổi Intraday & Tỷ Lệ Công Thành (Wall Siege Ratio):**
   - Theo cơ chế thanh toán bù trừ của CME Clearing House, khối lượng mở (Open Interest - OI) là dữ liệu tĩnh trong phiên, chỉ được CME tổng hợp và công bố chính thức 1 lần mỗi ngày sau giờ chốt sổ (overnight clearing).
   - Do đó, để phát hiện các bức tường Call Wall / Put Wall đang được MM bảo vệ kiên cố hay đang bị phe tấn công dồn hỏa lực xuyên thủng trong ngày (intraday), hệ thống không thể chờ OI thay đổi mà phải giám sát vận tốc dòng tiền volume thời gian thực so với dung lượng đệm mở ban đầu: $\text{Siege Ratio} = \frac{\text{Volume}}{\text{Baseline OI}}$.

## Quyết Định (Decisions)

### 1. Giải Nghiệm Liên Tục Zero Gamma Flip Bằng Thuật Toán Dekker-Brent Thuần Python
- Triển khai hàm giải nghiệm số `_brentq` (kết hợp bisection, secant và inverse quadratic interpolation) tự thân (self-contained, zero-dependency), không phụ thuộc vào thư viện nặng `scipy` nhằm bảo tồn tiêu chuẩn Zero-Waste Mandate (< 15MB repo).
- Hàm mục tiêu giải nghiệm:
  $$\Phi(S) = \sum_{k} \left[ \Gamma_k^{\text{Call}}(S) \cdot \text{OI}_k^{\text{Call}} - \Gamma_k^{\text{Put}}(S) \cdot \text{OI}_k^{\text{Put}} \right] = 0$$
  trong đó $\Gamma_k(S) = \frac{e^{-rT} \cdot \phi(d_1(S, K_k))}{S \cdot \sigma \sqrt{T}}$.
- Tìm kiếm nghiệm chính xác trên khoảng $[0.70 \cdot S_{\text{spot}}, 1.30 \cdot S_{\text{spot}}]$ với độ chính xác tuyệt đối $10^{-4}$ và thời gian giải nghiệm < 2 miligiây.

### 2. Tỷ Lệ Công Thành Wall Siege Ratio & Cảnh Báo MM Vỡ Trận
- Công thức: $\text{Siege Ratio} = \frac{\text{Volume}}{\max(\text{OI}, 1)}$.
- Ngưỡng kích hoạt:
  * $\text{Siege Ratio} \ge 0.25$ (hoặc tùy biến $\ge 0.50$): Bật cờ `is_under_siege = True`.
  * Cảnh báo trực tiếp trên bảng kịch bản (`scenario_engine.py`): Cảnh báo trader hạn chế đánh chặn (Fade/Rebound) khi thành trì đang bị dồn volume tấn công dữ dội.

### 3. Tích Hợp Toàn Diện Lên Giao Diện Chiến Thuật HUD
- **Panel 1 (Plotly):** Vẽ đường kẻ nằm ngang `ZERO GAMMA ($S^*)` màu cam hổ phách (`#F59E0B`, nét `longdash`), tự động co giãn dải strike hiển thị để đường Zero Gamma luôn nằm trong tầm nhìn trực quan của trader.
- **Thước Đo Mốc Giá (Visual Level Spine):** Bổ sung tỷ lệ Siege trực tiếp vào nút Call Wall và Put Wall (ví dụ: `4,200 (1,348 OI | Siege: 0.12x)`).
- **Thẻ KPI Thứ 6:** Hiển thị mốc Zero Gamma Flip liên tục cùng tỷ lệ CW/PW Siege.
- **Từ Điển Thuật Ngữ Bỏ Túi:** Bổ sung định nghĩa chuẩn hóa cho Zero Gamma Flip và Wall Siege Ratio.

## Hệ Quả (Consequences)
- **Độ chính xác định lượng:** Xác định chính xác ranh giới đổi pha thị trường Mean-reversion vs Trend-momentum mà không bị gián đoạn hay nhảy bậc giữa các strike.
- **Bảo toàn hiệu năng:** Hoạt động 100% thuần Python tiêu chuẩn, không thêm bất kỳ package nào ngoài `pandas`, `numpy`, `plotly`, `matplotlib`.
- **Hệ thống kiểm thử toàn diện:** Bộ unit test `tests/test_zero_gamma.py` và toàn bộ 103 test cases của repository vượt qua 100%.
