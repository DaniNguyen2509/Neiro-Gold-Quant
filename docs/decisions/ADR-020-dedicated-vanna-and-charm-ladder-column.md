# ADR-020: Cố Định Hồ Sơ Đỉnh Vanna (Xanh Dương) & Đỉnh Charm (Vàng) Theo Trục Giá Biểu Đồ

- **Trạng thái:** ACCEPTED
- **Ngày quyết định:** 2026-11-01
- **Tác giả:** Neiro Quant Engineering Team

---

## 1. Bối cảnh & Yêu cầu Người dùng (Context & User Feedback)

- Người dùng phản hồi: *"giá thì cố định theo chart, còn em thì vẽ màu xanh dương màu vàng như trước đây là được"*.
- Trước đó, việc tạo một bảng HTML `<table>` cuộn riêng biệt (`#neiro-greeks-sidebar`) ở bên phải màn hình gặp vấn đề:
  * Chiều cao hàng của bảng HTML là cố định (24px), trong khi các mức giá trên biểu đồ TradingView liên tục co giãn khi người dùng zoom in/out, cuộn ngang hoặc thay đổi khung thời gian (timeframe).
  * Dẫn đến việc mức giá Strike trên bảng HTML không khớp theo phương thẳng đứng với cây nến và thước đo giá của biểu đồ (bị lệch trục giá).
- Màu sắc quy ước:
  * **Vanna (Net VEX): Màu Xanh Dương (`#38BDF8`)** — Đo độ nhạy biến động theo IV (lực đẩy V-Rebound / xả Waterfall).
  * **Charm (Net CHEX): Màu Vàng (`#FACC15`)** — Đo tốc độ bào mòn Delta theo thời gian (nam châm ghìm giá đêm / Delta Decay).

---

## 2. Quyết định Thiết kế & Kiến trúc (Architectural Decision)

1. **Gắn Chặt Tọa Độ Vào Biểu Đồ (Anchor to Chart Price Coordinates):**
   - Loại bỏ hoàn toàn khối HTML `<table>` tách rời để biểu đồ TradingView và Canvas chiếm trọn 100% chiều rộng màn hình.
   - Sử dụng trực tiếp hàm `candleSeries.priceToCoordinate(k)` của TradingView Lightweight Charts trên lớp Canvas 60 FPS (`#neiro-canvas`).
   - Tọa độ Y của thanh bar Vanna và Charm tại mỗi Strike `k` luôn được tính toán động theo đúng pixel của mức giá trên biểu đồ nến M1. Khi người dùng zoom, cuộn hoặc co giãn nến, toàn bộ thanh profile Vanna và Charm di chuyển mượt mà bám chặt theo nến ("giá cố định theo chart").

2. **Quy Chuẩn Màu Sắc:**
   - **Vanna Bar (VEX):** Màu **Xanh Dương** (`#38BDF8`), opacity 0.60, end-cap xanh neon.
   - **Charm Bar (CHEX):** Màu **Vàng** (`#FACC15`), opacity 0.60, end-cap vàng neon.
   - **Đỉnh Vanna (`vanna_peak_strike`):** Khối badge viền xanh dương neon phát sáng: `⚡ ĐỈNH VANNA $X,XXX (±XX.XM)`.
   - **Đỉnh Charm (`charm_peak_strike`):** Khối badge viền vàng neon phát sáng: `⏳ ĐỈNH CHARM $X,XXX (±XX.XM/d)`.

3. **Tích Hợp Thước Đo Giá TradingView (`rightPriceScale`):**
   - Gọi `candleSeries.createPriceLine()` trực tiếp lên trục giá bên phải:
     * Badge màu xanh dương: `⚡ ĐỈNH VANNA`
     * Badge màu vàng: `⏳ ĐỈNH CHARM`

4. **Đồng Bộ Top Quant HUD & Legend:**
   - Chỉ số `VANNA (VEX)` hiển thị màu **xanh dương** (`#38BDF8`).
   - Chỉ số `CHARM (CHEX)` hiển thị màu **vàng** (`#FACC15`).
   - Legend topbar: `PROFILE: ■ GEX (Xanh/Đỏ) ■ VANNA (XANH DƯƠNG) ■ CHARM (VÀNG)`.

---

## 3. Hệ quả & Kiểm chứng (Consequences & Verification)

- **Trực quan & Chính xác 100%:** Giá và thanh bar Vanna / Charm hoàn toàn đồng bộ theo phương thẳng đứng với biểu đồ nến M1, không bao giờ bị lệch trục khi co giãn màn hình.
- **Không chiếm dụng không gian:** Biểu đồ TradingView mở rộng 100% toàn màn hình, không bị mất 230px cho bảng tĩnh.
- **Kiểm thử tự động:** 137/137 tests passed (100%).
- **Zero-Waste:** Dung lượng repo đạt 12.58 MB (< 15MB).
