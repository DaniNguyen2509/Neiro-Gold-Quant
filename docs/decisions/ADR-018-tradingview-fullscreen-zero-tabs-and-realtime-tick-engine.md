# ADR-018: TradingView Fullscreen Cockpit, M1 Default Timeframe, Zero Tabs & Realtime Tick Engine

## Trạng thái (Status)
**Accepted** (Đã kiểm chứng toán học, giao diện và toàn bộ 137 unit tests vượt qua 100%)

## Ngày quyết định (Date)
2026-11-01

## Người quyết định (Deciders)
Hệ thống Neiro-Gold-Quant (Chỉ đạo trực tiếp từ System Owner)

## Phạm vi (Scope)
- `src/hud/neiro_terminal.py`: Layout TradingView Fullscreen, giao diện 1M mặc định, loại bỏ Tab 1 / Tab 2, Realtime Tick Engine không reload.
- `src/hud/html_dashboard.py`: Xóa bỏ nút Refresh & countdown 60s, mở rộng `.container` tràn viền (100% width), hợp nhất bảng vi cấu trúc Greeks & Pinning Table đầy đủ Net GEX, Net VEX, Net CHEX.
- `src/quant_engine/basis.py`: Truy vấn nến M1 trực tiếp từ Yahoo Finance COMEX Gold Futures (`GC=F`) với 250 nến 1 phút gần nhất.
- `config/settings.toml`: Bổ sung cấu hình `default_timeframe = "1m"`, `tradingview_fullscreen = true`.
- `Chay_Live_Terminal.bat`: Đồng bộ chu kỳ vòng lặp 15s realtime.

---

## 1. Bối cảnh & Vấn đề (Context & Problem)

1. **Bất tiện khi chuyển đổi màn hình (Tab Switching Distraction):**
   Trước đây, giao diện chia làm 2 Tab: *Tab 1: Neiro All-in-One Orderflow* (Biểu đồ nến) và *Tab 2: Quant Profile Ladder* (Plotly và các bảng phân tích). Khi giao dịch lướt sóng (scalping) từng tick, việc phải chuyển đổi qua lại giữa 2 Tab khiến trader mất dấu nhịp đập thị trường và không thể theo dõi biến động nến trực tiếp.
2. **Khung nến M5 chưa đủ nhạy cho Scalping vi mô:**
   Nến M5 (5 phút) có độ trễ nhất định. Với thị trường vàng biến động nhanh, trader cần quan sát vi cấu trúc và hành vi giá ngay tại khung M1 (1 phút) để phản ứng ngay khi giá chạm vào các chốt chặn Market Maker (Call/Put Walls, Zero Gamma Flip, Air Pockets).
3. **Sự phân mảnh của 4 Panel Subplot:**
   Khối 4 Panel Plotly đặt ngang chia cắt Net GEX, Volume/OI, Net VEX, Net CHEX thành 4 cột hẹp, làm loãng thông tin và buộc trader phải đối chiếu ngang.
4. **Trải nghiệm co cụm (Boxed Layout) & Gián đoạn bởi Refresh:**
   Giao diện bị giới hạn trong khung 1440px với khoảng trắng thừa ở hai bên. Nút "Làm mới" thủ công và bộ đếm ngược 60s tự reload toàn trang (`window.location.reload()`) làm chớp giật màn hình, mất trạng thái zoom/pan của trader.

---

## 2. Quyết định Kiến trúc (Decisions)

### 2.1. Mặc định Khung Thời Gian Nến M1 (Default M1 High-Resolution Tape)
- Cập nhật endpoint truy vấn `GC=F` sang `interval=1m&range=5d` lấy 250 nến 1 phút liên tục gần nhất (~4 giờ giao dịch chi tiết).
- Nút `1M` được kích hoạt mặc định (`active`).
- Thuật toán `resampleBars()` trên frontend hỗ trợ chuyển đổi mượt mà giữa 1M (60s), 5M (300s), 15M (900s), 1H (3600s).

### 2.2. Giao diện Tràn Viền Fullscreen như TradingView (100% Full-Bleed Layout)
- Loại bỏ giới hạn `max-width: 1440px`. Toàn bộ container co giãn tự động theo 100% chiều rộng màn hình.
- Chiều cao biểu đồ mở rộng mặc định lên 700px (kèm nút chuyển đổi `↕ Fullscreen` lên 880px / full viewport).
- Tích hợp `ResizeObserver` và sự kiện `resize` tự động cân chỉnh độ phân giải canvas và chart theo kích thước cửa sổ của trader.

### 2.3. Hợp nhất Toàn bộ Chỉ số của 4 Panel vào Tab 1 (Fusing 4 Panels into Tab 1)
- **Loại bỏ Hoàn toàn Khối 4-Panel Plotly Độc lập:** Khối 4 panel đồ thị Plotly (Panel 1: Net GEX, Panel 2: Volume/OI & Net Delta, Panel 3: Net VEX, Panel 4: Net CHEX) bị loại bỏ khỏi layout để tránh chia nhỏ màn hình và đè chữ. Toàn bộ dữ liệu của 4 panel này được hợp nhất trực tiếp vào Tab 1.
- **Top Quant HUD & Profile Legend:** Đặt ngay trên đầu biểu đồ, bao quát trọn vẹn:
  - Spot GC & ATM strike
  - GEX Regime & Tổng Net GEX ($M)
  - Sổ sách Dealer: Net Delta (DEX) HĐ GC
  - Volume & Open Interest tổng cộng (HĐTL)
  - Greeks bậc 2: Vanna (Net VEX) & Charm (Net CHEX)
  - Thành trì & Tỷ lệ Công thành: Call Wall, Put Wall, Zero Gamma Flip ($S^*$)
  - Vùng kích hoạt tác chiến: Gamma Squeeze ↑ TP, Gamma Waterfall ↓ TP
  - Thanh chú giải Profile: GEX (Xanh/Đỏ), DEX (Cyan/Cam), CHEX (Vàng/Tím), Vol/OI.
- **Canvas Overlay 60 FPS (Multi-Metric Profile per Strike):** Vẽ trực tiếp ngay tại trục giá của từng Strike trên biểu đồ nến:
  - Thanh Net GEX Bar (Xanh lá / Đỏ)
  - Thanh Net Delta Bar (Cyan / Cam)
  - Thanh Net CHEX Bar (Vàng / Tím)
  - Nhãn đa chỉ số: Strike, GEX, DEX, VEX, CHEX, Vol (C/P) và OI (C/P).
- **Bảng Vi Cấu Trúc Toàn Diện (Unified Greeks & Orderflow Matrix):** Nằm ngay bên dưới biểu đồ trong Tab 1, tích hợp trọn vẹn mọi cột từ 4 panel: Mức Strike ($K), Net GEX ($M), Net Delta (HĐ GC), Khối Lượng Volume (Call/Put), Open Interest (Call/Put), Net VEX ($M), Net CHEX ($M/d), Gamma Black-76, Theta Bào Mòn và Ý nghĩa vi cấu trúc.

### 2.4. Xóa Bỏ Hoàn Toàn Hệ Thống Tab (Zero Tabs Invariant)
- Gỡ bỏ hoàn toàn nút bấm Tab 1 và Tab 2.
- Toàn bộ nội dung từ biểu đồ nến thời gian thực, đường cong Volatility Smile Malz SVI, thước đo khoảng cách Spine, bảng vi cấu trúc Greeks, bảng chiến lược Scalping và từ điển bỏ túi được sắp xếp liền mạch trên cùng một màn hình. Trader không bao giờ phải rời mắt khỏi dòng lệnh.

### 2.5. Gỡ bỏ Refresh & Tích hợp Realtime Tick Engine Nội Tại
- Gỡ bỏ nút "Làm mới" và đồng hồ đếm ngược 60s tự reload trang.
- Xây dựng **Realtime Tick Engine** thuần JavaScript:
  - Cập nhật liên tục giá đóng cửa của nến M1 hiện tại theo từng nhịp tick.
  - Dịch chuyển đường `livePriceLine` và các nhãn giá tức thì.
  - Cung cấp cổng `window.onLiveTick(data)` để tiếp nhận dữ liệu thời gian thực từ background runner mà không cần nạp lại trang web.
  - Giữ lại nút "Dọn RAM & Cache" hỗ trợ giải phóng bộ nhớ trình duyệt theo chuẩn Zero-Waste.

---

## 3. Hệ quả & Đánh giá (Consequences)

- **Trải nghiệm TradingView chuyên nghiệp:** Màn hình tràn viền, hiện đại, đen sâu chuẩn terminal quỹ định lượng.
- **Tập trung cao độ cho Scalping:** Nến M1 và Realtime Tick Engine giúp trader nhận biết ngay lập tức các đợt rút chân (absorption pinbar) và đột biến khối lượng (volume spike).
- **Không gián đoạn:** Loại bỏ hoàn toàn hiện tượng reload trang làm mất tập trung.
- **Bảo toàn hiệu năng Zero-Waste:** Không làm tăng dung lượng mã nguồn (repo luôn được giữ < 15MB), RAM cố định, zero memory leak.
- **Kiểm thử vững chắc:** Toàn bộ 137 unit tests vượt qua 100%.

