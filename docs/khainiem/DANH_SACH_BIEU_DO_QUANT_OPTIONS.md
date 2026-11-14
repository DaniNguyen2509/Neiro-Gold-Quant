# HỆ THỐNG BIỂU ĐỒ ĐỊNH LƯỢNG QUANT OPTIONS TRADING (NEIRO-QUANT)

> **Tài liệu tham chiếu khái niệm & đặc tả biểu đồ**  
> **Lưu trữ tại:** `docs/khainiem/DANH_SACH_BIEU_DO_QUANT_OPTIONS.md`  
> **Áp dụng cho:** Giao dịch Hợp đồng Tương lai Vàng CME (Gold Futures GC) dựa trên Chuỗi Quyền chọn (Options Chain).

---

## MỤC LỤC TỔNG QUAN 13 BIỂU ĐỒ ĐỊNH LƯỢNG

| STT | Tên Biểu Đồ (Chuẩn Quốc Tế) | Phân Loại Rủi Ro / Dòng Tiền | Khả Năng Triển Khai Với Data Hiện Tại |
| :---: | :--- | :--- | :---: |
| **1** | [Implied Volatility (IV) Skew Comparison by Tenor](#1-implied-volatility-iv-skew-comparison-by-tenor) | Độ biến động ẩn (Volatility Surface) | 🟡 Khả thi 1 kỳ hạn (Cần thêm file đa kỳ hạn) |
| **2** | [OI & Volume Heatmap](#2-oi--volume-heatmap) | Thanh khoản & Phân bổ vị thế | 🟢 **Sẵn sàng vẽ ngay (100% data)** |
| **3** | [OI Change & EOD Volume](#3-oi-change--eod-volume) | Dòng tiền qua đêm & Tích lũy phiên | 🟡 Cần dữ liệu 2 phiên liên tiếp ($\Delta \text{OI}$) |
| **4** | [GEX Profile by Option Type (Call GEX vs Put GEX)](#4-gex-profile-by-option-type-call-gex-vs-put-gex) | Rủi ro Gamma Market Maker | 🟢 **Đã tích hợp trong hệ thống** |
| **5** | [GEX Decomposition by Expiry Group](#5-gex-decomposition-by-expiry-group) | Phân rã cấu trúc kỳ hạn (Term Structure) | 🟡 Cần thêm file dữ liệu đa kỳ hạn |
| **6** | [Gamma Gravity & Gamma Squeeze](#6-gamma-gravity--gamma-squeeze) | Lực hút giá & Điểm nén bứt phá | 🟢 **Sẵn sàng vẽ ngay (100% data)** |
| **7** | [GEX Profile & Gamma Speed with Risk Zones](#7-gex-profile--gamma-speed-with-risk-zones) | Gia tốc rủi ro bậc 3 ($\partial \Gamma / \partial S$) | 🟢 **Sẵn sàng vẽ ngay (100% data)** |
| **8** | [Vanna & Charm Risk Profile vs Price](#8-vanna--charm-risk-profile-vs-price) | Greeks bậc 2 (Biến động IV & Thời gian) | 🟢 **Sẵn sàng vẽ ngay (100% data)** |
| **9** | [Historical Net Vanna & Charm Exposure](#9-historical-net-vanna--charm-exposure) | Xu hướng rủi ro dài hạn | 🔴 Cần cơ sở dữ liệu chuỗi thời gian (EOD) |
| **10** | [Market Regime Dial (Đồng Hồ Trạng Thái Thị Trường)](#10-market-regime-dial-ng-h-o-trng-thi-th-trng) | Định vị chế độ Volatility & Gamma | 🟢 **Sẵn sàng vẽ ngay (100% data)** |
| **11** | [Vomma & Color Profile](#11-vomma--color-profile) | Greeks bậc 2 & 3 ($\partial \nu / \partial \sigma, \partial \Gamma / \partial t$) | 🟢 **Sẵn sàng vẽ ngay (100% data)** |
| **12** | [Smart Delta Flow (Delta Exposure - DEX)](#12-smart-delta-flow-delta-exposure---dex) | Dòng tiền phòng hộ Delta ròng | 🟢 **Sẵn sàng vẽ ngay (100% data)** |
| **13** | [Hedging Pressure & Liquidity Absorption Zones with Hedging Flow Triggers](#13-hedging-pressure--liquidity-absorption-zones-with-hedging-flow-triggers) | Áp lực tái cân bằng & Kích hoạt dòng tiền | 🟢 **Sẵn sàng vẽ ngay (100% data)** |

---

## CHI TIẾT ĐẶC TẢ TỪNG BIỂU ĐỒ

### 1. Implied Volatility (IV) Skew Comparison by Tenor
* **Tên tiếng Việt:** So sánh độ lệch biến động ẩn (IV Skew / Smile) theo các kỳ hạn đáo hạn.
* **Bản chất định lượng:** Trực quan hóa giá trị IV của từng Strike theo từng kỳ hạn (Tenor: 0DTE, 1 Tuần, 1 Tháng, 3 Tháng). Độ cong (Smile) và độ dốc (Skew) phản ánh nỗi sợ hãi hoặc kỳ vọng của thị trường. Nếu Put IV cao hơn Call IV mạnh ở các kỳ hạn gần, thị trường đang mua bảo hiểm sập giá khẩn cấp.
* **Công thức toán:** IV giải ngược từ mô hình Black-76 qua thuật toán Newton-Raphson:
  $$C_{\text{market}} = e^{-rT} [F \cdot N(d_1) - K \cdot N(d_2)] \implies \sigma_{\text{implied}}$$
* **Ứng dụng thực chiến:** Nhận biết khi nào thị trường bị lệch (skewed), cảnh báo trước cú sập bất ngờ hoặc đảo chiều thanh khoản.
* **Yêu cầu dữ liệu:** Chuỗi Options của từ 2 kỳ hạn đáo hạn trở lên.

---

### 2. OI & Volume Heatmap
* **Tên tiếng Việt:** Bản đồ nhiệt Khối lượng giao dịch và Vị thế mở theo Strike.
* **Bản chất định lượng:** Dùng ma trận màu sắc (Heatmap) thể hiện đồng thời 4 đại lượng: `Call Volume`, `Put Volume`, `Call OI`, `Put OI` trên toàn bộ trục Strike.
* **Ứng dụng thực chiến:** Nhìn 1 giây là phát hiện ngay "Cá Mập" đang dồn tiền tập trung vào Strike nào (màu rực sáng nhất). Phân biệt được khối lượng giao dịch ngắn hạn trong ngày (Volume) với vị thế nắm giữ dài hạn (Open Interest).
* **Yêu cầu dữ liệu:** Sẵn sàng 100% trong file `options_prices.csv`.

---

### 3. OI Change & EOD Volume
* **Tên tiếng Việt:** Biến động vị thế mở qua đêm ($\Delta \text{OI}$) và Khối lượng giao dịch chốt phiên.
* **Bản chất định lượng:** So sánh vị thế mở hôm nay với phiên liền trước:
  $$\Delta \text{OI}_k = \text{OI}_{k, t} - \text{OI}_{k, t-1}$$
  Kết hợp với EOD Volume để xác định vị thế mới được mở thêm (New Position) hay đang thanh lý đóng lệnh (Liquidation).
* **Ứng dụng thực chiến:** Nếu giá tiếp cận 4200 mà Call OI tăng vọt -> Bức tường cản được gia cố thêm; nếu Call OI giảm mạnh -> Phe bán Call đang tháo chạy, nguy cơ bứt phá (Breakout).
* **Yêu cầu dữ liệu:** Cần 2 snapshot của 2 ngày giao dịch liên tiếp.

---

### 4. GEX Profile by Option Type (Call GEX vs Put GEX)
* **Tên tiếng Việt:** Hồ sơ Gamma Exposure phân rã theo loại quyền chọn Call và Put.
* **Bản chất định lượng:** Tính riêng lượng đô-la mà Dealer phải mua/bán Futures cho mỗi 1% biến động giá:
  $$\text{Call GEX}_k = \Gamma_{\text{call}, k} \cdot \text{OI}_{\text{call}, k} \cdot 100 \cdot F^2 \cdot 0.01$$
  $$\text{Put GEX}_k = -\Gamma_{\text{put}, k} \cdot \text{OI}_{\text{put}, k} \cdot 100 \cdot F^2 \cdot 0.01$$
* **Ứng dụng thực chiến:** Call GEX tạo lực cản phía trên (chặn tăng), Put GEX tạo lực đỡ/đẩy phía dưới.
* **Trạng thái:** **Đã tích hợp hoàn thiện trong Neiro-Quant HUD**.

---

### 5. GEX Decomposition by Expiry Group
* **Tên tiếng Việt:** Phân rã GEX theo các nhóm kỳ hạn đáo hạn (0DTE, Weekly, Monthly).
* **Bản chất định lượng:** Gom tổng GEX của các Strike theo từng cụm kỳ hạn đáo hạn để xem dòng tiền ngắn hạn (0DTE/Weekly) hay dòng tiền quỹ (Monthly) đang chi phối thị trường.
* **Ứng dụng thực chiến:** 0DTE tạo biến động sốc trong phiên (Intraday volatility), Monthly tạo xu hướng và các bức tường cứng không thể xuyên phá trong nhiều tuần.
* **Yêu cầu dữ liệu:** Chuỗi Options đa kỳ hạn.

---

### 6. Gamma Gravity & Gamma Squeeze
* **Tên tiếng Việt:** Trọng lực Gamma giữ giá & Ngưỡng kích hoạt Short Squeeze.
* **Bản chất định lượng:** 
  * **Gravity (Trọng lực):** Véc-tơ gia tốc kéo giá hồi quy về strike có Net GEX dương lớn nhất (GEX Cushion / ATM Pivot) khi thị trường ở trạng thái Long Gamma.
  * **Squeeze (Bứt phá):** Khi giá vượt qua Major Call Wall (4200.00), Delta của Call tăng vọt về 1.0, buộc Dealer bán Call phải mua điên cuồng Hợp đồng Futures để phòng hộ, tạo lực đẩy dựng đứng.
* **Công thức kích hoạt:**
  $$\text{Trigger Squeeze} = K_{\text{Call Wall}} + 0.5 \times \text{ATR}_{15m}$$
* **Ứng dụng thực chiến:** Đánh chặn đảo chiều ở vùng Gravity (Mean Reversion), nhưng chuyển sang mua đuổi ngay khi kích hoạt Squeeze.
* **Yêu cầu dữ liệu:** Sẵn sàng 100% trong dữ liệu hiện tại.

---

### 7. GEX Profile & Gamma Speed with Risk Zones
* **Tên tiếng Việt:** Hồ sơ GEX kết hợp Tốc độ biến thiên Gamma (Speed) và Vùng rủi ro thanh khoản.
* **Bản chất định lượng:** Speed là đạo hàm bậc 3 của giá option theo giá Futures:
  $$\text{Speed} = \frac{\partial \Gamma}{\partial F} = -\frac{\Gamma}{F} \left( \frac{d_1}{\sigma \sqrt{T}} + 1 
ight)$$
* **Ứng dụng thực chiến:** Speed đo tốc độ "bốc hơi" hoặc "phình to" của Gamma. Kết hợp Speed với các dải Air Pocket (vùng mỏng OI) để xác định chính xác các "Vùng Rủi Ro Cao" (nơi giá có thể rơi tự do không có lực cản).
* **Yêu cầu dữ liệu:** Sẵn sàng 100% (tính từ mô hình Black-76).

---

### 8. Vanna & Charm Risk Profile vs Price
* **Tên tiếng Việt:** Hồ sơ rủi ro Hy Lạp bậc 2 (Vanna & Charm) theo các mức giá.
* **Bản chất định lượng:**
  * **Vanna Exposure (VEX):** Đo lường Delta của Dealer thay đổi thế nào khi Độ biến động ẩn (IV) tăng/giảm:
    $$\text{Vanna} = -e^{-rT} \cdot n(d_1) \cdot \frac{d_2}{\sigma}, \quad \text{VEX}_k = \text{Vanna}_k \cdot \text{OI}_k \cdot 100 \cdot F$$
  * **Charm Exposure (CHEX):** Đo lường Delta suy hao tự nhiên theo thời gian trôi qua mỗi giờ/ngày:
    $$\text{Charm} = e^{-rT} \left[ n(d_1) \left( \frac{r}{\sigma \sqrt{T}} - \frac{d_2}{2T} 
ight) - r N(d_1) 
ight], \quad \text{CHEX}_k = \text{Charm}_k \cdot \text{OI}_k \cdot 100 \cdot F$$
* **Ứng dụng thực chiến:** Dự báo hướng dòng tiền phòng hộ khi tin tức ra (IV giật) hoặc vào 2 tiếng cuối phiên (Charm decay ép đóng lệnh).
* **Yêu cầu dữ liệu:** Sẵn sàng 100% (tính từ mô hình Black-76).

---

### 9. Historical Net Vanna & Charm Exposure
* **Tên tiếng Việt:** Lịch sử biến thiên độ nhạy Vanna & Charm của Market Maker theo thời gian.
* **Bản chất định lượng:** Biểu đồ đường (Line chart) theo trục thời gian (Date/Time) ghi nhận giá trị tổng ròng Net VEX và Net CHEX qua từng ngày để nhận biết xu hướng nới lỏng hay thắt chặt vị thế của Dealer.
* **Yêu cầu dữ liệu:** Cần cơ sở dữ liệu lịch sử EOD nhiều ngày.

---

### 10. Market Regime Dial (Đồng Hồ Trạng Thái Thị Trường)
* **Tên tiếng Việt:** Đồng hồ đo trạng thái thị trường (Speedometer / Gauge).
* **Bản chất định lượng:** Tích hợp Tổng Net GEX, Tỷ lệ Put/Call Ratio, và Khoảng cách tới Gamma Flip thành 1 chỉ số định lượng tổng hợp chia làm 4 trạng thái:
  1. **Long Gamma (Pinning / Vùng an toàn):** Net GEX > +50M$, giá dao động hẹp quanh Pivot.
  2. **Neutral (Chuyển tiếp):** -20M$ < Net GEX < +50M$.
  3. **Short Gamma (Volatile / Biên độ lớn):** Net GEX < -20M$ (Hiện tại: **`-53.7M$`**).
  4. **Extreme Cascade Risk (Nguy cơ bán tháo sập hầm):** Giá thủng Put Wall và Gamma Flip.
* **Ứng dụng thực chiến:** Nhìn 1 giây là biết phiên hôm nay nên đánh Scalping hồi quy hay đánh Breakout theo sóng lớn.
* **Yêu cầu dữ liệu:** Sẵn sàng 100% trong dữ liệu hiện tại.

---

### 11. Vomma & Color Profile
* **Tên tiếng Việt:** Hồ sơ độ nhạy bậc 2 Vomma và bậc 3 Color theo Strike.
* **Bản chất định lượng:**
  * **Vomma (Volga):** Đạo hàm của Vega theo IV ($\frac{\partial \nu}{\partial \sigma} = \nu \frac{d_1 d_2}{\sigma}$). Thể hiện độ nhạy lồi của giá option khi IV bùng nổ (dùng để bắt các con sóng thiên nga đen).
  * **Color:** Tốc độ suy giảm Gamma theo thời gian ($\frac{\partial \Gamma}{\partial t}$).
* **Ứng dụng thực chiến:** Dành cho chiến lược giao dịch biến động (Volatility Trading) và xác định thời điểm các bức tường phòng hộ bắt đầu suy yếu.
* **Yêu cầu dữ liệu:** Sẵn sàng 100% (tính từ mô hình Black-76).

---

### 12. Smart Delta Flow (Delta Exposure - DEX)
* **Tên tiếng Việt:** Dòng chảy Delta thông minh & Vị thế Delta phòng hộ tích lũy.
* **Bản chất định lượng:** 
  $$\text{DEX}_k = \left( \Delta_{\text{call}, k} \cdot \text{OI}_{\text{call}, k} + \Delta_{\text{put}, k} \cdot \text{OI}_{\text{put}, k} 
ight) \cdot F \cdot 100$$
  Biểu diễn số lượng hợp đồng Futures tương đương mà Market Maker đang giữ để đạt trạng thái Delta Neutral (Trung lập Delta).
* **Ứng dụng thực chiến:** Cho biết thị trường đang bị nghiêng về phía Mua hay phía Bán, và mức giá nào sẽ buộc Dealer phải đảo chiều dòng tiền phòng hộ từ Long sang Short.
* **Yêu cầu dữ liệu:** Sẵn sàng 100% trong dữ liệu hiện tại.

---

### 13. Hedging Pressure & Liquidity Absorption Zones with Hedging Flow Triggers
* **Tên tiếng Việt:** Áp lực tái cân bằng Delta của Dealer, Vùng hấp thụ thanh khoản & Điểm kích hoạt dòng tiền phòng hộ.
* **Bản chất định lượng:** Mô phỏng ma trận tái cân bằng (Hedging Rebalance Matrix):
  $$\Delta \text{Hedge}(S \pm \Delta S) = \text{Net GEX} \times \frac{\Delta S}{S} \times 100$$
  Dự báo chính xác nếu giá Vàng tăng/giảm $5, $10, $20 thì Market Maker bắt buộc phải tung bao nhiêu hợp đồng Futures vào thị trường để cân bằng sổ lệnh.
* **Ứng dụng thực chiến:** Đón đầu các đợt "bơm" hoặc "hút" thanh khoản tự động của các quỹ định lượng thuật toán.
* **Yêu cầu dữ liệu:** Sẵn sàng 100% trong dữ liệu hiện tại.

---

## BẢNG TỔNG KẾT KHẢ NĂNG THỰC THI (ACTION PLAN)

| Mức Độ | Danh Sách Biểu Đồ | Kế Hoạch Triển Khai |
| :--- | :--- | :--- |
| **GIAI ĐOẠN 1 (Vẽ được ngay hôm nay)** | • OI & Volume Heatmap<br>• Market Regime Dial<br>• Vanna & Charm Risk Profile (VEX/CHEX)<br>• Smart Delta Flow (DEX)<br>• Gamma Gravity & Squeeze Triggers | Tích hợp dần vào thư viện `src/hud/` dưới dạng các hàm Python native Matplotlib chuẩn, xuất ảnh trong < 0.5s. |
| **GIAI ĐOẠN 2 (Cần thêm file kỳ hạn)** | • IV Skew Comparison by Tenor<br>• GEX Decomposition by Expiry Group | Chỉ cần nạp thêm các file CSV kỳ hạn Tuần/Tháng khác từ CME Barchart. |
| **GIAI ĐOẠN 3 (Cần lịch sử chuỗi ngày)** | • OI Change & EOD Volume ($\Delta \text{OI}$)<br>• Historical Net Vanna & Charm Exposure | Bật cơ chế lưu log EOD tự động vào thư mục `data/history/` qua từng ngày giao dịch. |
