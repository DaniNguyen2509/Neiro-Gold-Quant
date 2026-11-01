# ADR-016: All-in-One Orderflow Tactical Terminal & Multi-Expiry Greeks Term Structure

- **Trạng thái:** ACCEPTED
- **Ngày quyết định:** 2026-11-01
- **Người quyết định:** Hệ thống Neiro-Gold-Quant (Chỉ đạo trực tiếp từ System Owner)
- **Phạm vi:** `src/hud/neiro_terminal.py`, `src/hud/html_dashboard.py`, `src/quant_engine/loader.py`, `src/quant_engine/basis.py`, `config/settings.toml`.

---

## 1. BỐI CẢNH (CONTEXT)

1. **Sự phân mảnh giao diện (Fragmented Charts):** Trước đây, trader phải quan sát 2-3 biểu đồ rời rạc (Canvas Footprint, Plotly 3-Panel GEX Ladder, Bảng ma trận 6 kịch bản, Bảng thành trì Swing) gây chậm trễ trong quyết định tác chiến vi mô (Orderflow scalping).
2. **Kịch bản giả định chưa kiểm chứng:** Khối "Kịch bản hiện tại KB-2", "Ma trận 6 kịch bản", và "Bảng tác chiến thành trì swing" chứa nhiều giả định chủ quan, không phản ánh trực diện dòng chảy lệnh thực tế.
3. **Sự bất cập của giá Spot & Binance PAXG:** Giá vàng Spot XAUUSD và token crypto Binance PAXG không thể quy đổi tương đương sang giá CME Gold Futures do độ lệch cơ sở (Basis/Contango/EFP), độ trễ báo giá web và sự khác biệt về thanh khoản.
4. **Cấu trúc kỳ hạn phức tạp của Hợp đồng Vàng (Multi-Expiry Term Structure):** Hợp đồng Vàng COMEX bao gồm nhiều kỳ hạn đáo hạn (Monthly G, J, M, Q, Z và Weekly OG1..OG5) với các mức DTE ($T_e$) và độ lệch biến động ($\sigma_e$) hoàn toàn khác nhau. Việc gộp dữ liệu mà dùng chung 1 DTE sẽ bóp méo nghiêm trọng độ nhạy Greeks bậc 1 và bậc 2 (Delta, Gamma, Vega, Vanna, Charm, Theta).

---

## 2. QUYẾT ĐỊNH KIẾN TRÚC (DECISIONS)

### 2.1. Hợp nhất thành All-in-One NEIRO Orderflow Terminal Canvas (60 FPS)
Toàn bộ thông số định lượng được hiển thị trực tiếp trên một biểu đồ duy nhất:
1. **Air Pocket Vacuum Zones:** Vùng túi chân không thanh khoản rỗng được vẽ trực tiếp dạng băng dải viền đứt đoạn đỏ mờ (`⚠️ AIR POCKET VACUUM [$min - $max]`) cảnh báo giá có thể trượt dốc không phanh.
2. **Net GEX & Greeks Profile Bars:** Vẽ thanh ngang cạnh từng Strike (xanh cho Long Gamma / đỏ cho Short Gamma) kèm nhãn `GEX +X.XM | VEX +Y.YM` trực quan.
3. **Key Structural Boundary Lines:** Call Wall, Put Wall (hiển thị kèm Siege Ratio $Volume / OI$), Zero Gamma Flip ($S^*$), và các ngưỡng kích hoạt Squeeze/Waterfall.
4. **Floating HUD & Orderflow Tape:** Thông số PnL, Delta ròng, Chênh lệch Mua/Bán (Net Delta), Tỷ lệ Siege hiển thị tức thì trên canvas.

### 2.2. Loại bỏ triệt để các khối dư thừa (Zero-Distraction Purge)
1. **Gỡ bỏ hoàn toàn:**
   - "PHẦN 2: BẢNG TÁC CHIẾN PHỤC KÍCH THÀNH TRÌ (STRUCTURAL SWING WALLS - ĐÁNH SÓNG LỚN)".
   - "KỊCH BẢN HIỆN TẠI KB-2: MM CHẶN BÁN PHÒNG THỦ TRẦN (CALL DEFENSE)".
   - "MA TRẬN 6 KỊCH BẢN THỜI GIAN THỰC".
2. Giữ lại duy nhất bảng tác chiến lướt sóng trong ngày (Intraday Scalping), Băng giá M5 Orderflow Tape, Bảng Ma trận Vi cấu trúc từng Strike và Từ điển thuật ngữ bỏ túi.

### 2.3. Nguyên lý Xếp chồng Tuyến tính Đa Kỳ Hạn (Multi-Expiry Linear Superposition)
Greeks tổng hợp tại mỗi mức Strike $K$ được tính toán độc lập theo từng kỳ hạn $e$ ($T_e, \sigma_{e, K}$) và cộng dồn tuyến tính:
$$\text{NetGEX}(K) = \sum_{e} \text{NetGEX}_e(K)$$
$$\text{NetVEX}(K) = \sum_{e} \text{NetVEX}_e(K)$$
$$\text{NetCHEX}(K) = \sum_{e} \text{NetCHEX}_e(K)$$
$$\text{Vega}(K) = \sum_{e} \text{Vega}_e(K), \quad \text{Theta}(K) = \sum_{e} \text{Theta}_e(K)$$

Mốc Zero Gamma Flip ($S^*$) được tìm nghiệm trên hàm liên tục tổng đa kỳ hạn bằng thuật toán Dekker-Brent (`_brentq`).

### 2.4. 100% Pure CME Gold Futures (`GC=F`) - Xóa bỏ Spot & Binance PAXG
1. Hủy bỏ hoàn toàn việc cào giá Spot từ các bên thứ ba (Binance PAXG, Gold-API). Hàm `fetch_live_spot_gold_price()` trả về `None` theo thiết kế.
2. Nguồn dữ liệu thời gian thực duy nhất là hợp đồng CME Gold Futures (`GC=F`) qua Yahoo Finance (`query1.finance.yahoo.com`), đảm bảo dữ liệu miễn phí, tốc độ cao, không phụ thuộc tài khoản sàn.
3. Cập nhật `config/settings.toml`: `show_spot = false`.

### 2.5. Tích hợp Nến Thật 100% từ Yahoo Finance COMEX Gold Futures (`GC=F`)
1. **Loại bỏ nến ngẫu nhiên:** Thay thế hoàn toàn cơ chế sinh nến ngẫu nhiên (`generateRealisticGoldCandles` dùng `Math.random()`) bằng luồng nến thực tế được nạp vào `window.INITIAL_CANDLES` từ API Yahoo Finance.
2. **Khắc phục khoảng trống dữ liệu ngoài giờ / cuối tuần:** Cập nhật endpoint truy vấn sang `range=5d` (thay vì `range=1d` vốn trả về rỗng khi thị trường đóng cửa cuối tuần), đảm bảo luôn sẵn sàng 150 nến M5 gần nhất (~12.5 giờ giao dịch liên tục).
3. **Resample Đa Khung Thời Gian (Multi-Timeframe):** Thuật toán `resampleBars()` trên frontend gom cụm nến 5M thành 15M và 1H chính xác theo chuẩn thời gian, đảm bảo hình thái nến (Open, High, Low, Close, Volume) khớp 100% với biểu đồ Yahoo Finance và TradingView COMEX Gold.

---

## 3. HỆ QUẢ & BẢO TOÀN KIẾN TRÚC (CONSEQUENCES)

- **Ưu điểm:**
  - Nhìn 1 biểu đồ là thấu suốt toàn bộ cấu trúc vi mô, không cần chuyển qua lại giữa 2-3 màn hình.
  - Loại bỏ hoàn toàn các thông tin suy đoán thiếu căn cứ thực tế.
  - Tính toán Greeks đa kỳ hạn chuẩn xác theo lý thuyết định giá Black-76 cho Options on Futures.
  - Duy trì chuẩn Zero-Waste: Toàn bộ repository sạch sẽ, kích thước chỉ ~11.8 MB (< 15MB).
- **Tuân thủ Kiểm thử:** 133/133 Unit Tests vượt qua 100%.

