# ADR-029: 3-Second Tactical Cockpit Simplification & Full Realtime Bridge Parity

- **Trạng thái:** Đã triển khai (Implemented & Parity-Verified)
- **Bối cảnh:** Kiểm định trải nghiệm vận hành Cockpit sau ADR-028 chỉ ra 3 điểm nghẽn nghiêm trọng làm giảm tốc độ ra quyết định của trader khi theo dõi CME Gold Futures (`GC=F`):
  1. **Lỗi Runtime JavaScript ngầm ngắt đồng bộ Realtime (`currentTfKey` ReferenceError):** Hàm `pollLiveYahooChart` và một số nhánh cập nhật nến trong `src/hud/neiro_terminal.py` tham chiếu biến chưa khai báo `currentTfKey` (4 vị trí) thay vì `currentTf`, làm gãy vòng polling `2.5s` và khiến thanh trạng thái/HUD có thể đóng băng sau lượt render đầu.
  2. **Ngữ cảnh Tác chiến Tĩnh & Quá tải Thông tin 4 Lần:** Sau khi tải trang, chỉ cây nến M1 nhảy giá, còn `KHỐI 4 Spine` (khoảng cách Strike), `KHỐI 6` (Entry/SL/TP/Lot và cổng `[KÍCH HOẠT]`/`[TẠM KHÓA]`/`[CHỜ XÁC NHẬN]`), HUD nổi và VPIN/BVC không tự tính lại theo nhịp giá live. Đồng thời Top-Center Canvas Gauge bị đè lên chart chính, chiều cao canvas `700px` đẩy bảng kèo khỏi khung nhìn đầu, và các khối phụ (`Pinning`, `KHỐI 1 Smile`, `KHỐI 3 KPI`, `KHỐI 5 Orderflow`, `KHỐI 7 Glossary`) dàn trải gây ngộp chữ.
  3. **Thiếu micro-payload trực tiếp trên Bridge & Cảnh báo Trạng thái Đồng bộ Mơ hồ:** Bridge `/api/yahoo_gc` và `_run_lightweight_live_tick()` chưa phát trực tiếp bộ VPIN/BVC/Kyle/ATR5m mới nhất; badge trạng thái chưa tách bạch rạch ròi 3 chế độ (`LIVE BRIDGE (2.5s)` / `CLOUD SYNC (LIVE)` / `OFFLINE SNAPSHOT` / `CME GLOBEX: CLOSED (SETTLED)`).

## Quyết định (Decision)

1. **Thanh Chỉ Huy 3 Giây (`#tactical-3s-command-bar`) & Bố Cục 2 Tầng Flexbox (`src/hud/html_dashboard.py`):**
   - Bổ sung thanh `#tactical-3s-command-bar` gồm 4 ô ngay bên dưới biểu đồ (`cmd-regime-card`, `cmd-wall-card`, `cmd-flow-card`, `cmd-action-card`) trả lời tức thời trong 3 giây: *(1) Chế độ Dealer Gamma*, *(2) Tường gần nhất & Air Pocket*, *(3) Dòng lệnh VPIN/BVC/Siege*, *(4) Kèo `[KÍCH HOẠT]` ưu tiên hoặc đứng ngoài*.
   - Sắp xếp hiển thị bằng CSS Flexbox `order` trên `.container`: Chart stage (`order: 1`) -> Command Bar 3s (`order: 2`) -> `KHỐI 4 Spine` (`order: 3`) -> `KHỐI 6` mở sẵn mặc định (`order: 4`), đồng thời thu gọn toàn bộ khối kiểm toán phụ (`Pinning` `order: 6`, `KHỐI 1 Smile` `order: 7`, `KHỐI 3 KPI` `order: 8`, `KHỐI 5 Orderflow` `order: 9`, `KHỐI 7 Glossary` `order: 10`) vào `<details class="table-box drawer-box">` đóng mặc định mà **không thay đổi thứ tự substring landmark** trong HTML thô (`pos_smile < pos_micro < pos_kpi < pos_orderflow < pos_strategy < pos_glossary`).

2. **Động cơ JS Chiến Lược & Vi Cấu Trúc Đồng Bộ 100% Với Python ADR-028 (`src/hud/neiro_terminal.py`):**
   - Sửa triệt để cả 4 lỗi `currentTfKey` -> `currentTf`.
   - Cổng hóa hoàn chỉnh các hàm JS thuần khớp 1:1 với Python (`strategy.py` / `dealer.py` / `institutional.py`):
     - `computeLiveVpinBvcJs`: chuẩn hóa phân tán nền `candles[:-6]` (`0.5 * P60(|dp|)/0.8416 + 0.5 * MAD_scaled`, nội suy tuyến tính `percentileSortedJs`) và chia đều 5 equal-volume buckets có triệt tiêu dấu trong từng bucket.
     - `computeM5AtrJs`, `resolveAdaptiveStrikesJs`, `sizeXauusdJs`, `computeTacticalMatrixJs`, `updateRealtimeTacticalCockpit`, `updateSyncBadgeHonest`.
   - Khi nến `GC=F` biến động, `updateRealtimeTacticalCockpit()` tự động tính lại `VPIN`, `BVC Buy%`, `CVD`, `ATR M5`, Strike neo adaptive, toàn bộ 4 ô Command Bar, các khoảng cách trên `KHỐI 4 Spine`, 4 dòng `KHỐI 6` (`k6-row-{sq,fd,rb,bd}` & `k6-*-{label,gate,trig,entry,sl,tp,lot}`) và vẽ lại đường `ENTRY / SL / TP` của kèo `[KÍCH HOẠT]` ngay trên Canvas.

3. **Tinh gọn Canvas Overlay, HUD Nổi & Payload Cầu Nối (`html_dashboard.py` & `neiro_terminal.py`):**
   - Gỡ bỏ Top-Center Canvas Gauge đè hình, thu gọn `.neiro-floating-hud` xuống 5 dòng cốt lõi (`hud-item`), đặt `.neiro-body-container` mặc định `540px` (`.expanded` `700px`) kèm 2 nút trên Topbar (`#btn-overlay-mode`: `Lớp phủ: Tinh gọn / Đầy đủ`, `#btn-chart-height`: `↕ Mở rộng Chart`).
   - Mặc định chế độ `Tinh gọn` chỉ vẽ 3 đường cấu trúc lõi (`CALL WALL`, `PUT WALL`, `GAMMA FLIP`) + các đường `ENTRY / SL / TP` đang `[KÍCH HOẠT]`; Vanna, Charm, Air Pockets, FVG và Squeeze chỉ hiện khi bật `Đầy đủ` (`syncSecondaryPriceLines()`).
   - Hợp nhất `_compute_live_microstructure_payload(tape)` ở backend (tái sử dụng `compute_vpin_bvc` & `compute_rolling_kyle_lambda_ols`) nối vào `/api/yahoo_gc`, `_run_lightweight_live_tick()` và `run_pipeline()` (`version.json`); mở rộng `meta` với `next_above`, `next_below`, `step`, `major_up_wall`, `major_down_wall`, `has_up_air_pocket`, `has_down_air_pocket`, `atr_5m`.

4. **Đơn giản hóa Nhãn Hành Động Theo 4 Kèo Trực Quan (Kiểu 2):**
   - Quy chuẩn lại tên chiến lược trên `#tactical-3s-command-bar` (`Ô 1`, `Ô 4`), `KHỐI 6` (`k6-row-{sq,fd,rb,bd}`) và đồng bộ `computeTacticalMatrixJs()` thành 4 nhãn hành động gắn điểm vào CME:
     - `1. THUẬN CHIỀU BUY (Phá cản {strike})` *(trước đây: `BUY MUA ĐUỔI / Squeeze`)*
     - `2. ĐẢO CHIỀU SELL (Chạm cản {strike})` *(trước đây: `SELL CHẶN TIỀN TUYẾN / Fade`)*
     - `3. ĐẢO CHIỀU BUY (Chạm sàn {strike})` *(trước đây: `BUY BẮT SÀN ATM / Rebound`)*
     - `4. THUẬN CHIỀU SELL (Thủng sàn {strike})` *(trước đây: `SELL THỦNG SÀN / Breakdown`)*
   - Ô chế độ `cmd-regime-val` hiển thị trực diện `ƯU TIÊN ĐÁNH ĐẢO CHIỀU (GEX +)` / `ƯU TIÊN ĐÁNH THUẬN CHIỀU (GEX -)` / `CHỜ XÁC NHẬN (CHUYỂN PHA)`.
   - Canvas & Tooltip hiển thị nhãn bình dân (`VEX · VÙNG BẬT / GIẬT SÓNG`, `CHEX · HÚT GIÁ VỀ ĐÂY`, cùng dòng gợi ý `-> GEX (+): Đánh ĐẢO CHIỀU` / `-> GEX (-): Đánh THUẬN CHIỀU` khi di chuột qua 5 cột Greeks).

## Xác minh & Tính Toàn Vẹn (Verification)

- Kiểm thử đối chiếu chéo JS (Node `vm` trên `exports/index.html`) vs Python (`dealer.py` & `strategy.py`):
  - **VPIN & Orderflow:** `VPIN 60.6% == 60.6%`, `BuyPct 59.9% == 59.9%`, `CVD 175.1 == 175.1` khớp chính xác 100%.
  - **Ma trận `KHỐI 6` (`squeeze`, `fade`, `rebound`, `breakdown`):** Khớp chính xác 100% toàn bộ `entry`, `sl`, `sl_dist`, `tp`, `active`, `badge`, `reason` và `lots` trên cả `GLOBEX_CLOSED` lẫn `NY_COMEX_DEEP`.
- Dung lượng bản build thực tế `exports/index.html`: `554,540` bytes (`541.5 KB`), toàn bộ workspace (loại trừ `.git`/cache) giữ dưới ngưỡng Zero-Waste `15 MB`; không sửa đổi `mt5/Indicators/*.mq5` và giữ nguyên toàn bộ hằng số định lượng ADR-028.

