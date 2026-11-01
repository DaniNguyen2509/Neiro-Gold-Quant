# ADR-020: Thiết Kế Cột Hồ Sơ Riêng Biệt Cho Đỉnh Vanna & Đỉnh Charm Cạnh Thước Đo Giá

- **Trạng thái:** ACCEPTED
- **Ngày quyết định:** 2026-11-01
- **Tác giả:** Neiro Quant Engineering Team

---

## 1. Bối cảnh & Yêu cầu (Context & Requirements)

- Người dùng phản hồi trên biểu đồ nến TradingView M1 toàn màn hình không nhìn thấy vị trí của **Đỉnh Charm** và **Đỉnh Vanna** ở đâu.
- Người dùng đề xuất: *"em vẽ riêng 1 cột ở ngay bên phải cột giá được mà"*.
- Trong vi cấu trúc phái sinh COMEX Gold:
  * **Đỉnh Vanna ($S^*_{VEX}$):** Mức giá Strike có $|VEX|$ (Net Vanna Exposure) lớn nhất. Đây là điểm xoay chuyển nhạy cảm khi độ biến động IV thay đổi (khi IV hạ sẽ kích hoạt lực đẩy V-Rebound, khi IV tăng vọt sẽ gây áp lực xả bán Waterfall).
  * **Đỉnh Charm ($S^*_{CHEX}$):** Mức giá Strike có $|CHEX|$ (Net Charm Exposure) lớn nhất. Đây là điểm nam châm ghìm giá đêm khi thời gian đáo hạn tiến gần (Delta Decay), buộc Market Maker phải liên tục mua/bán bù Delta vào giờ chốt phiên.
- Trước đây, hai mốc này bị ẩn trong nhãn chuỗi text vi mô và thiếu sự nhận diện trực quan tức thì.

---

## 2. Quyết định Thiết kế & Kiến trúc (Architectural Decision)

1. **Cột Riêng Biệt Bên Phải Cột Giá (`#neiro-greeks-sidebar`):**
   - Thiết kế layout flex cho container biểu đồ:
     * Khu vực chính (`flex: 1`): Chứa TradingView Candlestick Chart, thước đo giá (`rightPriceScale`), và Canvas 60 FPS.
     * Cột bên phải (`width: 230px`, `#neiro-greeks-sidebar`): Đặt ngay bên phải cột giá của TradingView.
   - Nội dung cột bao gồm:
     * **Header:** `⚡ VANNA & ⏳ CHARM PROFILE`.
     * **Thẻ Đỉnh Vanna:** Nhãn viền cam neon `#FB923C`, hiển thị Strike đỉnh Vanna, Net VEX ($M/1% IV) và ý nghĩa tác chiến.
     * **Thẻ Đỉnh Charm:** Nhãn viền tím neon `#C084FC`, hiển thị Strike đỉnh Charm, Net CHEX ($M/ngày) và ý nghĩa ghìm giá.
     * **Bảng Ladder Từng Strike (Scrollable):** Hiển thị chi tiết Strike, VEX bar, CHEX bar, tự động gắn badge `⚡` (Đỉnh Vanna), `⏳` (Đỉnh Charm), `👉` (Spot CME).

2. **Tích hợp PriceLine Trực Tiếp Lên Cột Giá (TradingView Right Price Scale):**
   - Sử dụng `candleSeries.createPriceLine()` chính thức của Lightweight Charts:
     * Badge màu cam: `⚡ ĐỈNH VANNA $X,XXX`
     * Badge màu tím: `⏳ ĐỈNH CHARM $X,XXX`
   - Hiển thị trực tiếp nhãn giá ngay trên trục thước đo giá bên phải màn hình.

3. **Đường Mức Kẻ Ngang Canvas Toàn Biểu Đồ:**
   - Bổ sung `vanna_peak_strike` và `charm_peak_strike` vào danh sách `keyLevels` của Canvas Overlay, kẻ đường nét đứt kèm nhãn giải thích tác chiến.

4. **Đồng bộ Top HUD Header:**
   - Cột Vanna: `VANNA (VEX): +$X.XM (Đỉnh: $X,XXX · +$Y.YM)`
   - Cột Charm: `CHARM (CHEX): -$X.XM/d (Đỉnh: $X,XXX · -$Y.YM)`

---

## 3. Hệ quả & Kiểm chứng (Consequences & Verification)

- **Trực quan:** Trader nhìn vào màn hình là thấy ngay vị trí Đỉnh Vanna và Đỉnh Charm ở 4 vị trí: Cột giá, Cột riêng bên phải, Đường kẻ trên chart, và Top HUD.
- **Kiểm thử tự động:** 137/137 tests passed (100%) trong 24.48s.
- **Zero-Waste:** Dung lượng repo đạt 12.00 MB (< 15MB).

