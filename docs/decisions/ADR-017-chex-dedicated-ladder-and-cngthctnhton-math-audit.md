# ADR-017: Dedicated Net CHEX Ladder Panel & 100% Mathematical Alignment with CNGTHCTNHTON.html

## Trạng thái (Status)
**Accepted** (Đã kiểm chứng toán học 100% & toàn bộ 137 unit tests vượt qua)

## Ngữ cảnh & Vấn đề (Context & Problem)
1. **Thiếu biểu đồ trực quan độc lập cho Net CHEX:**
   Người dùng đặt câu hỏi: *"ủa biểu đồ CHEX ĐÂU?"*. Trên giao diện trước đó, tại Tab 2 (Quant Profile Ladder), chỉ số Net VEX ($M/1% IV) và Net CHEX ($M/ngày) bị vẽ chung vào cột Panel 3. Do Plotly vẽ theo cơ chế overlay/relative và đơn vị của hai chỉ số khác biệt, các thanh CHEX bị thanh VEX đè khuất, khiến nhà giao dịch không quan sát được đường cong phân rã Charm theo từng Strike. Tại Tab 1 (Canvas HTML5), nhãn trên nến chỉ ghi `GEX ... | VEX ...` và thiếu nhãn cũng như thanh đo Net CHEX.
2. **Yêu cầu rà soát toán học 100%:**
   Người dùng yêu cầu đối chiếu toàn diện 100% công thức trong toàn bộ codebase với tài liệu chuẩn `docs/tailieudacta/CÔNG THỨC TÍNH TOÁN/CNGTHCTNHTON.html` (kèm hệ thống ảnh công thức `image1.png` đến `image62.png`).

## Phân tích & Lỗ hổng Toán học Đã Tìm Thấy & Khắc Phục (Math Audit Findings & Corrections)
Qua đối chiếu chi tiết từng phương trình đạo hàm:
1. **Công thức Charm trong Black-76 (Ảnh image40, image41, image42):**
   - *Lỗi cũ trong code:* Sao chép công thức Black-Scholes cho cổ phiếu cơ sở có phần bù lãi suất $r / (\sigma\sqrt{T})$: `charm_call = - df_disc * (pdf_d1 * (r / denom - d2 / (2.0 * T_years)) - r * cdf_d1)`.
   - *Chuẩn Black-76 CME trong `CNGTHCTNHTON.html`:*
     $$\text{Charm}_{Call} = -\frac{\partial \Delta_{Call}}{\partial T} = \frac{e^{-rT} \left[ n(d_1) \frac{d_2}{2T} - r N(d_1) \right]}{365}$$
     $$\text{Charm}_{Put} = -\frac{\partial \Delta_{Put}}{\partial T} = \frac{e^{-rT} \left[ n(d_1) \frac{d_2}{2T} + r N(-d_1) \right]}{365}$$
     Không hề có số hạng $r / (\sigma\sqrt{T})$ vì hợp đồng Futures đã chiết khấu chi phí vốn vào giá tương lai.
   - *Quan hệ đẳng thức Charm Put-Call:*
     $$\text{Charm}_{Put} - \text{Charm}_{Call} = \frac{r e^{-rT}}{365}$$
2. **Công thức Theta trong Black-76 (Ảnh image35, image36):**
   - *Lỗi cũ trong code:* Chỉ tính phần suy hao độ biến động $\text{decay} = -\frac{F_0 \sigma e^{-rT} n(d_1)}{2\sqrt{T}}$, thiếu số hạng lãi suất $+ r C$ (Call) và $+ r P$ (Put).
   - *Chuẩn `CNGTHCTNHTON.html`:*
     $$\Theta_{Call} = -\frac{F_0 \sigma e^{-rT} n(d_1)}{2\sqrt{T}} + r C$$
     $$\Theta_{Put} = -\frac{F_0 \sigma e^{-rT} n(d_1)}{2\sqrt{T}} + r P$$
     (Đơn vị năm; chia 365 để ra đơn vị mỗi ngày).
3. **Phơi nhiễm Net CHEX (Ảnh image54):**
   $$\text{NetCHEX}_K = \sum_{i=1}^n \left( \text{OI}_{Call, K, i} \times \text{Charm}_{Call, K, i} - \text{OI}_{Put, K, i} \times \text{Charm}_{Put, K, i} \right) \times M_{contract} \times F_0$$
   (Quy đổi ra triệu USD bằng cách chia $10^6$).
4. **Phơi nhiễm Net GEX (Ảnh image50):**
   $$\text{NetGEX}_K = \sum_{i=1}^n \left( \text{OI}_{Call, K, i} \times \Gamma_{K, i} - \text{OI}_{Put, K, i} \times \Gamma_{K, i} \right) \times M_{contract} \times F_0^2 \times 0.01$$
5. **Phơi nhiễm Net VEX (Ảnh image53):**
   $$\text{NetVEX}_K = \sum_{i=1}^n \left( \text{OI}_{Call, K, i} \times \text{Vanna}_{K, i} - \text{OI}_{Put, K, i} \times \text{Vanna}_{K, i} \right) \times M_{contract} \times F_0 \times 0.01$$
6. **Tổng tiền phí thời gian (Total Daily Theta Bleed - Section 5):**
   $$\text{Total Theta}_K = \left( \text{OI}_{Call, K} \times |\Theta_{Call, K}| + \text{OI}_{Put, K} \times |\Theta_{Put, K}| \right) \times M_{contract}$$

## Quyết định Kiến trúc & Giao diện (Decisions)
1. **Tách Subplot Tab 2 thành 4 Panel độc lập (4-Panel Subplot Layout):**
   - `rows=1, cols=4, column_widths=[0.27, 0.27, 0.23, 0.23]`
   - **Panel 1: Net GEX ($M)** (Thang đo Gamma & Mốc chiến thuật TP/SL)
   - **Panel 2: Volume, OI & Net Delta Sổ Sách (HĐ)** (Dòng lệnh & Vị thế thực tế)
   - **Panel 3: Net VEX ($M/1% IV) · Vanna Flow** (Áp lực điều chỉnh phòng hộ khi độ biến động giật)
   - **Panel 4: Net CHEX ($M/ngày) · Charm Delta Decay 24h** (Biểu đồ độc lập thể hiện dòng tiền phân rã Delta mỗi ngày)
   - Toàn bộ các mốc cản/hỗ trợ trọng yếu (`CALL WALL`, `PUT WALL`, `ZERO GAMMA`, `CME LIVE`) đều được đồng bộ kẻ ngang xuyên suốt cả 4 Panel.
2. **Hiển thị CHEX trực tiếp trên Canvas Tab 1 (`neiro_terminal.py`):**
   - Nhãn Strike mở rộng: `$K · GEX ±X.XM | VEX ±Y.YM | CHEX ±Z.ZM/d`.
   - Vẽ thanh ngang Net CHEX (Vàng `#FACC15` cho dương / Tím `#C084FC` cho âm) ngay dưới thanh Net GEX.
3. **Bộ Test Toán học Toàn diện:**
   Tạo mới `tests/test_cngthctnhton_math_audit.py` bao phủ:
   - Put-Call Parity price & delta
   - Vanna & Charm second-order analytical derivatives
   - Charm Parity ($\text{Charm}_P - \text{Charm}_C = r e^{-rT}$)
   - Net GEX, VEX, CHEX scaling factors
   - 4-Panel Subplot layout verification

## Hệ quả & Đánh giá (Consequences)
- Người dùng có thể nhìn thấy ngay lập tức biểu đồ CHEX riêng biệt ở Panel 4 (không bị che khuất).
- Toán học mô hình Black-76 và Greeks khớp 100% với tài liệu đặc tả `CNGTHCTNHTON.html`.
- Toàn bộ 137 unit tests vượt qua, đảm bảo không có rủi ro hồi quy logic.
