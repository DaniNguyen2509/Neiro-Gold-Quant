# Neiro-Quant — CẨM NANG TÁC CHIẾN THỰC CHIẾN DÀNH CHO TRADER (TRADER PLAYBOOK)

> **Phiên bản:** v1.1 (ADR-028 / ADR-029 Pure CME Futures)  
> **Dành cho:** Nhà giao dịch Vàng Phái sinh (**100% Pure CME Gold Futures `GC` / `MGC` / `GC=F`** — tuân thủ Rule 8, không quy đổi Spot `XAUUSD`).  
> **Tài liệu nền tảng:** [docs/architecture.md](architecture.md), [docs/spec.md](spec.md) & [docs/decisions/](decisions/).  
> **URL Tactical Web Terminal:** [https://daninguyen2509.github.io/Neiro-Gold-Quant/](https://daninguyen2509.github.io/Neiro-Gold-Quant/)

---

## MỤC LỤC TỔNG QUAN

1. [Triết Lý Cốt Lõi: Bản Chất Vi Cấu Trúc Khác Gì Phân Tích Kỹ Thuật?](#1-triết-lý-cốt-lõi-bản-chất-vi-cấu-trúc-khác-gì-phân-tích-kỹ-thuật)
2. [Quy Trình 3 Bước Đọc Bảng Điện Trong 30 Giây](#2-quy-trình-3-bước-đọc-bảng-điện-trong-30-giây)
3. [Giải Mã Chi Tiết 7 Thẻ KPI Thống Kê Đầu Bảng](#3-giải-mã-chi-tiết-7-thẻ-kpi-thống-kê-đầu-bảng)
4. [Bản Đồ Hành Động Chi Tiết 6 Kịch Bản Market Maker (KB-1 đến KB-6)](#4-bản-đồ-hành-động-chi-tiết-6-kịch-bản-market-maker-kb-1-đến-kb-6)
5. [Phân Biệt Sống Còn: Bounce Wall vs Magnet Wall (ADR-008)](#5-phân-biệt-sống-còn-bounce-wall-vs-magnet-wall-adr-008)
6. [Quét Túi Chân Không Thanh Khoản (Air Pocket) & Quy Tắc Cấm Đỡ Dao](#6-quét-túi-chân-không-thanh-khoản-air-pocket--quy-tắc-cấm-đỡ-dao)
7. [Đọc Hiểu Đường Cong Nụ Cười SVI Volatility Smile & Skew (ADR-009)](#7-đọc-hiểu-đường-cong-nụ-cười-svi-volatility-smile--skew-adr-009)
8. [Radar Xung Lực Orderflow M5: Nhận Diện Pinbar & Volume Spike](#8-radar-xung-lực-orderflow-m5-nhận-diện-pinbar--volume-spike)
9. [Quy Tắc Quản Trị Rủi Ro, Đi Tiền (Sizing GC/MGC) & Hard SL ADR-028](#9-quy-tắc-quản-trị-rủi-ro-đi-tiền-sizing-gcmgc--hard-sl-adr-028)
10. [Checklist Tác Chiến Mẫu Trong Ngày Cho Trader](#10-checklist-tác-chiến-mẫu-trong-ngày-cho-trader)

---

## 1. TRIẾT LÝ CỐT LÕI: BẢN CHẤT VI CẤU TRÚC KHÁC GÌ PHÂN TÍCH KỸ THUẬT?

Hầu hết các trader nhỏ lẻ trên thị trường đều sử dụng các công cụ kỹ thuật truyền thống:
- Vẽ các đường Hỗ trợ / Kháng cự chủ quan qua đỉnh đáy quá khứ.
- Dùng các chỉ báo trễ (RSI, MACD, Bollinger Bands, Moving Average) vốn chỉ là đạo hàm bậc 1 của giá đóng cửa.
- Khi giá chạm cản thì vội vã "bắt đỉnh, đỡ đáy" một cách mù quáng và bị quét sạch tài khoản khi thị trường xả lũ.

### Bản chất thực sự định hình đường đi của giá:
1. **Thị trường Vàng thế giới được dẫn dắt bởi Hợp đồng Tương lai CME (COMEX Gold Futures) và Chuỗi Quyền chọn (Options Chain).**
2. **Nhà tạo lập thị trường (Market Makers - MMs / Dealers):** Là những định chế tài chính khổng lồ bán quyền chọn (Calls & Puts) cho các quỹ phòng hộ và nhỏ lẻ. Để không phá sản vì biến động giá, Dealers **BẮT BUỘC PHẢI PHÒNG HỘ LIÊN TỤC (Dynamic Delta Hedging)** bằng Hợp đồng Tương lai COMEX (`GC`).
3. **Mỗi bước chuyển động của giá không phải ngẫu nhiên:** Đó là hệ quả trực tiếp từ việc Dealers phải mua hoặc bán hàng nghìn hợp đồng Futures để tái cân bằng trạng thái Delta-neutral.
4. **Hệ thống Neiro-Quant:** Không dự đoán tương lai bằng bói toán, mà **đo lường chính xác lượng hợp đồng Dealers buộc phải mua/bán tại từng mức giá**, qua đó xác định trước các chốt chặn phòng thủ vững chắc hoặc các bẫy chân không thanh khoản.

---

## 2. QUY TRÌNH 3 BƯỚC ĐỌC BẢNG ĐIỆN TRONG 30 GIÂY

Khi mở Tactical Terminal trên điện thoại hoặc máy tính, trader thực hiện đúng 3 bước theo thứ tự sau:

```
[BƯỚC 1: 10 GIÂY ĐẦU] ──► Quét 7 Thẻ KPI Thống Kê Đầu Bảng
                          - Xác định Chế độ Gamma (Positive hay Negative?)
                          - Xem mốc Zero Gamma Flip S* nằm ở đâu so với giá?
                          - Kiểm tra Sổ sách Dealer (Net Delta): Đang Long hay Short?
                                 │
                                 ▼
[BƯỚC 2: 10 GIÂY TIẾP] ─► Nhìn Thước Đo Mức Giá (Visual Level Spine) & Action Banner
                          - Giá hiện tại đang kẹp giữa Call Wall và Put Wall nào?
                          - Khoảng cách tới cản gần nhất là bao nhiêu USD?
                                 │
                                 ▼
[BƯỚC 3: 10 GIÂY CUỐI] ─► Kiểm tra Ma Trận 6 Kịch Bản MM Realtime
                          - Có thẻ nào đang BẬT SÁNG VIỀN & PHÁT TÍN HIỆU không?
                          - Nếu có: Đọc ngay Entry, Stop Loss (1.5 - 2.5 giá) và Take Profit.
                          - Nếu KHÔNG (các thẻ mờ 55%): Tiếp tục kiên nhẫn đứng ngoài.
```

---

## 3. GIẢI MÃ CHI TIẾT 7 THẺ KPI THỐNG KÊ ĐẦU BẢNG

Mỗi thẻ KPI trên bảng điện đóng vai trò như một đồng hồ đo áp suất trên buồng lái tàu ngầm:

### Thẻ 1: SPOT CME FUTURES (Giá Tương Lai Chuẩn)
- **Ý nghĩa:** Giá giao dịch thực tế của Hợp đồng Tương lai Vàng COMEX Front-Month (`GC=F` / `GCZ26`).
- **Lưu ý sống còn (Rule 8 — 100% Pure CME Futures):** Toàn bộ thuật toán, bảng kèo `KHỐI 6`, Strike Options và nến `GC=F` của Neiro-Quant neo **100% vào giá CME Gold Futures** (Single Source of Truth), khớp chuẩn `$0.01` với bảng Options COMEX mà **không** tự ý quy đổi sang Spot/CFD bên ngoài.

### Thẻ 2: NET GEX REGIME (Chế Độ Gamma Toàn Thị Trường)
- **Positive Net GEX ($> 0$):**  
  * *Bản chất:* Dealers đang ở trạng thái Long Gamma. Khi giá tăng, họ phải bán Futures ra; khi giá giảm, họ phải mua Futures vào.
  * *Tác động:* **Hấp thụ biến động, nén biên độ, thị trường đi vào vùng Mean-Reverting (hồi quy trung bình).**
  * *Chiến lược:* Ưu tiên đánh chặn FADE REVERSAL tại biên dải cản; TUYỆT ĐỐI KHÔNG đánh mua đuổi Breakout.
- **Negative Net GEX ($< 0$):**  
  * *Bản chất:* Dealers đang ở trạng thái Short Gamma. Khi giá tăng, họ bị ép phải mua đuổi; khi giá giảm, họ bị ép phải bán tháo.
  * *Tác động:* **Gia tốc biến động cực đại, nguy cơ quét thanh khoản 2 đầu, trượt giá tự do (High Volatility Cascade).**
  * *Chiến lược:* Giảm khối lượng vào lệnh 30-50%, nới rộng biên độ kỳ vọng, sẵn sàng kích hoạt lệnh Breakout/Breakdown theo đà xả lũ.

### Thẻ 3: DEALER BOOK (NET DELTA / DEX)
- **Chỉ số Net Delta ($HĐ GC):** Tổng số hợp đồng Futures quy đổi mà Dealers đang nắm giữ để phòng hộ.
- **Nếu Net Delta > 0 (Dealer Long Delta):**  
  Thị trường tổng thể đang Short. Nếu giá tiếp tục rơi, Dealer sẽ có xu hướng chốt bớt vị thế Long phòng hộ bằng cách bán ra, tạo thêm lực ép giảm.
- **Nếu Net Delta < 0 (Dealer Short Delta):**  
  Thị trường tổng thể đang Long Call. Khi giá tăng vượt các ngưỡng quan trọng, Dealer buộc phải ồ ạt mua hợp đồng để bù đắp Delta, kích hoạt Short Squeeze.

### Thẻ 4: ZERO GAMMA FLIP ($S^*$) & WALL SIEGE RATIO
- **Zero Gamma Flip ($S^*$):**  
  * Điểm cân bằng triệt tiêu hoàn toàn Net GEX, được giải bằng phương trình nghiệm số liên tục Dekker-Brent (`_brentq`).
  * **Nếu $Spot > S^*$:** Thị trường nằm trong vùng An toàn Positive Gamma (bền vững, ít nhiễu).
  * **Nếu $Spot < S^*$:** Thị trường rơi xuống vùng Nguy hiểm Negative Gamma (biến động bão táp, sập giá gia tốc).
- **Wall Siege Ratio (Tỷ lệ Công Thành = Volume / OI):**
  * Dữ liệu Open Interest (OI) của CME là tĩnh trong phiên (chỉ cập nhật qua đêm).
  * Do đó, vận tốc công phá bức tường trong ngày được đo bằng:  
    $$\text{Wall Siege Ratio} = \frac{\text{Intraday Volume}}{\text{Baseline OI}}$$
  * **Ratio < 0.5 (Tường Bê Tông):** Khối lượng tấn công yếu ớt, tường phòng thủ của MM sẽ đứng vững -> Đánh chặn Fade Reversal an toàn.
  * **Ratio $\ge 1.0$ (Tường Đang Vỡ):** Khối lượng giao dịch nội phiên đã vượt cả lượng vị thế mở nền -> Báo động đỏ vỡ đê, chuẩn bị cho cú bứt phá Squeeze hoặc sập lũ.

### Thẻ 5: EXPECTED MOVE & 1-SIGMA BANDS
- **Dải Biên Độ Kỳ Vọng Trong Ngày:**
  * Tính toán từ Synthetic ATM Straddle ($Call_{mid} + Put_{mid}$) nhân với hệ số điều chỉnh vi cấu trúc:
    $$\text{Upper Band (+1.0}\sigma) = S_{\text{Implied}} + \text{Straddle}$$
    $$\text{Lower Band (-1.0}\sigma) = S_{\text{Implied}} - \text{Straddle}$$
  * Trong 68.2% thời gian, giá sẽ dao động trọn vẹn bên trong dải $\pm 1.0\sigma$. Mép trên và mép dưới là các chốt chặn cực trị để chốt lời (Take Profit) các lệnh Swing.

### Thẻ 6: GREEKS BẬC 2 (VANNA & CHARM FLOWS)
- **Net VEX (Vanna Exposure):** Đo lường lượng Delta Dealer phải tái cân bằng khi độ biến động ngầm định (IV) thay đổi 1%.
  * Trước giờ tin vĩ mô (CPI, NFP), IV tăng vọt $\rightarrow$ Vanna kích hoạt dòng tiền gom/xả tức thì.
- **Net CHEX (Charm Exposure):** Tốc độ suy biến vị thế theo thời gian trôi qua mỗi ngày.
  * Càng về cuối phiên Mỹ (22:00 - 00:00 VN), hiệu ứng Charm càng mạnh, ép giá hồi quy về trục ATM Pivot.

### Thẻ 7: 25Δ SKEW (RISK REVERSAL & BUTTERFLY)
- **25Δ Risk Reversal ($RR_{25} = IV_{25\Delta C} - IV_{25\Delta P}$):**
  * **$RR_{25} > 0$:** Call IV đắt hơn Put IV $\rightarrow$ Giới tổ chức đang trả tiền cao để mua cược tăng giá (Bullish Skew).
  * **$RR_{25} < 0$:** Put IV đắt hơn Call IV $\rightarrow$ Thị trường đang lo sợ, chi tiền mua bảo hiểm sập giá khẩn cấp (Bearish Skew).

---

## 4. BẢN ĐỒ HÀNH ĐỘNG CHI TIẾT 6 KỊCH BẢN MARKET MAKER (KB-1 ĐẾN KB-6)

Tactical Dashboard trang bị Ma trận Đánh giá Kịch bản Realtime. Trader chỉ hành động khi thẻ kịch bản **BẬT SÁNG ĐẦY ĐỦ**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      MA TRẬN 6 KỊCH BẢN MARKET MAKER                        │
├───────────────────────┬─────────────────────────────┬───────────────────────┤
│ KB-1: NÉN BIÊN ĐỘ     │ KB-2: MM CHẶN BÁN (CALL)    │ KB-3: MM VỠ TRẬN SHORT│
│ [ĐỨNG NGOÀI]          │ [SELL BÁN ĐẢO CHIỀU - FADE] │ [BUY MUA ĐUỔI SQUEEZE]│
├───────────────────────┼─────────────────────────────┼───────────────────────┤
│ KB-4: MM ĐỆM MUA (PUT)│ KB-5: THỦNG SÀN XẢ LŨ       │ KB-6: VÙNG TRUNG LẬP  │
│ [BUY BẮT HỒI REBOUND] │ [CẤM BẮT ĐÁY / SELL FLUSH]  │ [KIÊN NHẪN CHỜ ĐỢI]   │
└───────────────────────┴─────────────────────────────┴───────────────────────┘
```

---

### 🛑 KB-1: GIẰNG CO NÉN BIÊN ĐỘ (Pinning Box - ATM Strangle Trap)

* **Bản chất vi mô:**  
  Giá đang bị kẹp chặt xung quanh trục ATM Pivot trong dải hẹp ($\pm 0.5 \times \text{Straddle}$). Net GEX toàn cục dương lớn. Market Maker kiếm lợi nhuận tối đa bằng cách ghìm giá đi ngang để ăn trọn phí quyền chọn (Theta Decay) của cả 2 đầu Call và Put.
* **Tín hiệu nhận diện trên Terminal:**
  - Thẻ KB-1 sáng viền vàng cam.
  - Vị trí giá nằm sát trung tâm ATM Pivot.
  - Orderflow M5 xuất hiện nến lưỡng lự giằng co (`is_churn`).
* **HÀNH ĐỘNG CỦA TRADER:**
  - **LỰA CHỌN TỐT NHẤT: ĐỨNG NGOÀI.** Bảo toàn vốn và phí giao dịch.
  - **TUYỆT ĐỐI CẤM:** Không đánh Breakout khi thấy giá chớm nhú ra khỏi nến M5, vì MM sẽ lập tức kéo giật ngược trở lại hộp nén.

---

### 🛡️ KB-2: MM CHẶN BÁN PHÒNG THỦ TRẦN (Call Wall Defense - Fade Sell)

* **Bản chất vi mô:**  
  Giá tăng tiếp cận sát Major Call Wall hoặc Front-line Call Resistance. Đây là khu vực tập trung Open Interest Call khổng lồ mà Market Maker đã bán khống trước đó. Để ngăn không cho giá xuyên thủng (khiến họ phải trả tiền bồi thường hợp đồng), MM đặt các lệnh Limit Sell khổng lồ và liên tục xả hợp đồng Futures để ghìm đầu giá xuống.
* **Tín hiệu nhận diện trên Terminal:**
  - Thẻ KB-2 sáng viền xanh dương/đỏ với nhãn `SELL BÁN ĐẢO CHIỀU (FADE)`.
  - Bức tường được phân loại là **`[BOUNCE_WALL]`** (Dealer Long Gamma).
  - Tỷ lệ công thành **Wall Siege Ratio < 0.5** (phe mua chưa đủ hỏa lực bẻ gãy tường).
  - Radar M5 ghi nhận nến đè đỉnh rút râu trên (`is_pinbar_bear`).
* **KẾ HOẠCH VÀO LỆNH (EXECUTION PLAN):**
  - **Lệnh:** SELL LIMIT hoặc SELL MARKET khi nến M5 đóng cửa rút chân.
  - **Vị trí Entry:** Ngay sát mép dưới Call Wall (VD: Call Wall 4200.00 $\rightarrow$ Entry: 4198.50 - 4199.50).
  - **Stop Loss BẮT BUỘC:** $Call\_Wall + 1.5 \text{ đến } 2.5 \text{ giá}$ (VD: 4202.00). *Vượt qua mốc này nghĩa là MM đã vỡ trận, phải cắt lỗ ngay lập tức!*
  - **Take Profit (TP):**
    * TP1: Trục ATM Pivot ($S_{\text{Implied}}$).
    * TP2: Mốc hỗ trợ liền kề phía dưới ($TP < Entry$).

---

### 🚀 KB-3: BÁO ĐỘNG ĐỎ: MM VỠ TRẬN SHORT (Gamma Squeeze Breakout)

* **Bản chất vi mô:**  
  Phe mua của các Quỹ đầu cơ dồn khối lượng khổng lồ đánh sập Call Wall. Khi giá vượt qua ngưỡng kích hoạt ($Call\_Wall + 0.5 \times ATR_{15m}$), Delta của các hợp đồng Call tăng dựng đứng về 1.0. Market Maker bị đẩy vào trạng thái Short Gamma âm nặng $\rightarrow$ **Họ bắt buộc phải quay ngoắt 180 độ, điên cuồng mua đuổi hợp đồng Futures bằng lệnh Market để tự cứu mình**. Lực mua phòng hộ này cộng hưởng với lực mua của quỹ tạo nên cú phóng thẳng đứng (Gamma Squeeze).
* **Tín hiệu nhận diện trên Terminal:**
  - Thẻ KB-3 sáng rực viền đỏ nhấp nháy với nhãn `BÁO ĐỘNG ĐỎ: MM VỠ TRẬN SHORT (Gamma Squeeze)`.
  - Tỷ lệ công thành **Wall Siege Ratio $\ge 1.0$** (Volume nội phiên vượt mốc OI).
  - Giá phá vỡ và đóng cửa dứt khoát trên Call Wall.
  - Radar M5 ghi nhận **Volume Spike ($\ge 1.4 \times MA_{20}$ và $\ge 350$ HĐ)**.
* **KẾ HOẠCH VÀO LỆNH (EXECUTION PLAN):**
  - **HÀNH ĐỘNG SINH TỬ: TUYỆT ĐỐI CẤM BÁN CHẶN ĐẦU TÀU HỎA!**
  - **Lệnh:** BUY STOP hoặc BUY MARKET đuổi theo dòng tiền cá mập.
  - **Stop Loss:** Ngay bên dưới Call Wall vừa bị xuyên thủng ($Call\_Wall - 1.5 \text{ giá}$).
  - **Take Profit:** Nhắm thẳng tới Upper Band +1.0σ hoặc Major Call Wall thứ cấp tiếp theo bên trên.

---

### 🛡️ KB-4: MM ĐỆM MUA BẢO VỆ SÀN ĐÁY (Put Wall Defense - Rebound Buy)

* **Bản chất vi mô:**  
  Giá giảm sâu tiếp cận Major Put Wall. Tại đây, Market Maker đã bán số lượng lớn hợp đồng bảo hiểm Put. Để bảo vệ thành trì, MM tung các lệnh Bid Limit dày đặc đón đỡ và liên tục mua gom hợp đồng Futures để cân bằng Delta, tạo nên tấm đệm lò xo bật giá.
* **Tín hiệu nhận diện trên Terminal:**
  - Thẻ KB-4 sáng viền xanh lá với nhãn `BUY BẮT HỒI (REBOUND)`.
  - Bức tường được phân loại là **`[BOUNCE_WALL]`** (Dealer Long Gamma).
  - Tỷ lệ công thành **Wall Siege Ratio < 0.5**.
  - Radar M5 xuất hiện nến rút chân hấp thụ đáy (`is_pinbar_bull`).
* **KẾ HOẠCH VÀO LỆNH (EXECUTION PLAN):**
  - **Lệnh:** BUY LIMIT hoặc BUY MARKET khi nến M5 rút chân xác nhận.
  - **Vị trí Entry:** Ngay sát mép trên Put Wall (VD: Put Wall 4150.00 $\rightarrow$ Entry: 4150.50 - 4151.50).
  - **Stop Loss BẮT BUỘC:** $Put\_Wall - 1.5 \text{ đến } 2.5 \text{ giá}$ (VD: 4148.00). *Thủng mốc này là kích hoạt xả lũ, cấm chần chừ!*
  - **Take Profit (TP):**
    * TP1: Trục ATM Pivot ($S_{\text{Implied}}$).
    * TP2: Mốc kháng cự liền kề phía trên ($TP > Entry$).

---

### 🌊 KB-5: BÁO ĐỘNG ĐỎ: THỦNG SÀN & XẢ LŨ (Air Pocket Slide / Vacuum Breakdown)

* **Bản chất vi mô:**  
  Phe bán chủ động công phá vỡ tan Put Wall. Nguy hiểm hơn, bên dưới Put Wall là một **Vùng Chân Không Thanh Khoản (Air Pocket)** — nơi Open Interest cạn kiệt (< 35% trung bình). Phía dưới không hề có người mua đỡ giá, trong khi Dealers bị rơi vào trạng thái Negative Gamma nghiêm trọng $\rightarrow$ **Dealers bị ép buộc phải bán tháo hàng nghìn hợp đồng Futures ra thị trường để phòng hộ rủi ro**, tạo thành một thác nước trượt giá không phanh (Liquidity Vacuum Cascade).
* **Tín hiệu nhận diện trên Terminal:**
  - Thẻ KB-5 sáng rực viền đỏ cảnh báo với nhãn `BÁO ĐỘNG ĐỎ: Thủng Sàn & Xả Lũ (Air Pocket Slide)`.
  - Giá đóng cửa thủng dưới Put Wall quá $0.5 \times ATR_{15m}$.
  - Vùng bên dưới hiển thị nhãn cảnh báo `[AIR POCKET GAP]`.
  - Tỷ lệ công thành **Wall Siege Ratio $\ge 1.0$**.
* **KẾ HOẠCH VÀO LỆNH (EXECUTION PLAN):**
  - **QUY TẮC BẤT DI BẤT DỊCH: TUYỆT ĐỐI CẤM BẮT ĐÁY / CẤM ĐỠ DAO!**
  - **Lệnh:** SELL STOP / SELL BREAKDOWN ăn trọn con sóng trượt giá tự do.
  - **Stop Loss:** Quay trở lại bên trên Put Wall vừa thủng ($Put\_Wall + 1.5 \text{ giá}$).
  - **Take Profit:** Chỉ chốt lời khi giá trượt chạm tới Cụm Put Wall vĩ mô tiếp theo (nơi có khối lượng OI lớn xuất hiện đón đỡ) hoặc mép Lower Band -1.0σ.

---

### ⏳ KB-6: VÙNG TRUNG LẬP (Neutral Floating)

* **Bản chất vi mô:**  
  Giá đang trôi lơ lửng ở khoảng trống giữa các mốc cản, chưa chạm tới bất kỳ biên tường Call hay Put nào. Không có xung lực phòng hộ khẩn cấp từ Market Maker.
* **HÀNH ĐỘNG CỦA TRADER:**
  - **KIÊN NHẪN CHỜ ĐỢI.**
  - Không mở vị thế lơ lửng ở lưng chừng trời. Giữ kỷ luật thép: Chỉ vào lệnh khi giá tiếp cận vùng ranh giới có xác suất cao.

---

## 5. PHÂN BIỆT SỐNG CÒN: BOUNCE WALL VS MAGNET WALL (ADR-008)

Sai lầm chết người của 90% trader định lượng là chỉ nhìn vào Strike có Open Interest (OI) lớn nhất rồi kết luận đó là cản cứng.  
Theo quyết định kiến trúc [ADR-008](decisions/ADR-008-multi-expiry-gex-and-gamma-weighted-walls.md), Neiro-Quant tính toán chỉ số **Gamma Power**:

$$\text{Gamma Power} = \text{Open Interest} \times \Gamma$$

Trên Dashboard, mỗi bức tường được phân loại rõ ràng thành 2 nhóm:

| Đặc Điểm | `[BOUNCE_WALL]` (Chốt Chặn Đàn Hồi) | `[MAGNET_WALL]` (Bẫy Nam Châm Xuyên Phá) |
|---|---|---|
| **Trạng thái Dealer** | **Dealer Long Gamma ($GEX > 0$)** | **Dealer Short Gamma ($GEX < 0$)** |
| **Hành vi MM** | Mua khi giá giảm, Bán khi giá tăng để ghìm giá lại. | Bị ép phải mua đuổi khi tăng, bán tháo khi giảm. |
| **Hiệu ứng giá** | Hoạt động như **Tấm nệm lò xo**, phản xạ đảo chiều cực mạnh. | Hoạt động như **Nam châm hút giá**, giá bị kéo tới và xuyên thủng! |
| **Hành động Trader** | **ĐƯỢC PHÉP ĐẶT LỆNH CHẶN (FADE REVERSAL)** với SL ngắn 1.5 - 2.5 giá. | **TUYỆT ĐỐI CẤM ĐẶT LIMIT ĐÓN ĐẦU!** Chuẩn bị lệnh đánh Breakout. |

---

## 6. QUÉT TÚI CHÂN KHÔNG THANH KHOẢN (AIR POCKET) & QUY TẮC CẤM ĐỠ DAO (ADR-021)

* **Túi chân không thanh khoản (Air Pocket):**  
  Là khoảng trống giữa các Strike mà tại đó tổng Open Interest Call và Put rơi xuống dưới **35% mức trung bình 20 Strike lân cận**:
  $$\text{Air Pocket}: \quad OI_k < 0.35 \times \text{MA}_{20}(OI)$$
* **Hiện tượng "Rơi tự do":**  
  Khi giá đi trong vùng có OI dày đặc, mỗi bước giá đều có người khớp lệnh mua bán nên giá đi chậm và tôn trọng hỗ trợ kháng cự. Nhưng khi giá lọt vào **Air Pocket**, không có lệnh đối ứng chờ sẵn $\rightarrow$ Chỉ cần một lực bán nhỏ cũng khiến giá rơi hàng chục giá trong vài phút.
* **Dấu hiệu nhận biết trực quan trên Terminal v3.2 (ADR-021):**
  - **Trên biểu đồ nến (Main Chart):** Dải cảnh báo màu hổ phách nét đứt quét ngang với nhãn:
    `⚠️ AIR POCKET VACUUM [$from - $to] · NGUY CƠ TRƯỢT DÀI (CẤM ĐỠ DAO)`.
  - **Trên cột 4 Profile Greeks bên phải (GEX | VEX | CHEX | THETA):** Dải cảnh báo hổ phách phủ trọn hàng Strike chân không, xuất hiện trực tiếp Badge cảnh báo:
    `[⚠️ AIR POCKET (CẤM ĐỠ) $from - $to]`.
  - **Khi rê chuột vào cột Greeks:** Bảng Tooltip Card sẽ hiển thị chi tiết số liệu của từng Strike, giúp trader nhận diện ngay các Strike có OI cạn kiệt.
* **Chiến thuật thực chiến:**
  - Khi thấy khoảng cách giữa giá hiện tại và mốc hỗ trợ tiếp theo là một dải Air Pocket: **ĐÓNG TẤT CẢ CÁC VỊ THẾ BUY NGAY LẬP TỨC**.
  - **Tuyệt đối cấm đặt lệnh Limit (Buy Limit / Sell Limit) đón đầu** ở lưng chừng các dải Air Pocket.
  - Kích hoạt chế độ `BREAKDOWN SLICING RUNNER` để thu lợi nhuận từ cú trượt chân không.

---

## 7. ĐỌC HIỂU ĐƯỜNG CONG NỤ CƯỜI SVI VOLATILITY SMILE & SKEW (ADR-009)

Hệ thống Neiro-Quant trang bị mô hình SVI (Stochastic Volatility Inspired) làm mượt toàn bộ chuỗi biến động ẩn (IV), tuân thủ nghiêm ngặt 3 bất biến vi cấu trúc:

```
                      ĐƯỜNG CONG SVI VOLATILITY SMILE
         IV (%)
           │
     28% ──┤      \                                   /
           │       \                                 /  (Cánh Call Wing)
     24% ──┤        \                               /
           │         \                             /
     20% ──┤          \                           /
           │           \___________•_____________/
     16% ──┤                      ATM
           └───────┬───────────────┬───────────────┬──────► Strike
                 4100            4180            4250
              (Deep OTM Put)    (ATM)       (Deep OTM Call)
```

### 3 Tình huống đọc Skew thực chiến:
1. **Put Wing dựng đứng (Put Skew dốc đứng):**  
   * *Ý nghĩa:* Dòng tiền tổ chức đang tranh nhau mua Put OTM để phòng hộ sụp đổ giá trước phiên Mỹ hoặc trước giờ ra tin CPI/NFP.
   * *Cảnh báo:* Rủi ro Flash Crash cực cao. Ưu tiên canh Sell theo MM.
2. **Call Wing vểnh cao (Call Skew):**  
   * *Ý nghĩa:* Lực cầu đầu cơ mua Call OTM bùng nổ, kỳ vọng giá Vàng bứt phá đỉnh All-Time High.
   * *Chiến lược:* Canh mua gia tốc khi giá tiếp cận Call Wall.
3. **Đường cong đối xứng đáy bằng (Smile phẳng):**  
   * *Ý nghĩa:* Thị trường yên ắng, không có sự kiện rủi ro đặc biệt. Chế độ Mean-Reversion trong hộp Pinning Box chiếm ưu thế tuyệt đối.

---

## 8. RADAR XUNG LỰC ORDERFLOW M5: NHẬN DIỆN PINBAR & VOLUME SPIKE

Bảng điện cập nhật trực tiếp luồng nến M5 từ sàn COMEX, giúp trader bắt trọn thời điểm xác nhận (Confirmation Timing):

1. **Volume Spike ($Volume \ge 1.4 \times MA_{20}$ và $Volume \ge 350$ HĐ):**  
   Cá mập tổ chức đã chính thức ra tay. Không bao giờ giao dịch ngược lại hướng nến của một thanh Volume Spike!
2. **Nến Hấp Thụ Đáy Rút Chân (`is_pinbar_bull`):**  
   Giá nhúng sâu qua Put Wall nhưng đóng cửa rút chân để lại bóng nến dưới dài $\ge 60\%$ thân nến. Khối lượng lớn chứng minh MM đã hấp thụ sạch lực bán tháo $\rightarrow$ Kích hoạt điểm vào lệnh **BUY REBOUND** an toàn nhất.
3. **Nến Đè Đỉnh Rút Râu Trên (`is_pinbar_bear`):**  
   Giá chọc lên Call Wall nhưng bị xả hàng dội ngược trở lại, để lại râu nến trên dài $\ge 60\%$ $\rightarrow$ Kích hoạt điểm vào lệnh **SELL FADE**.
4. **Nến Giằng Co Lưỡng Lự (`is_churn`):**  
   Khối lượng giao dịch cực lớn nhưng thân nến đóng cửa bé xíu $\rightarrow$ Phe mua và phe bán đang ghìm nhau nghẹt thở, tích lũy năng lượng chuẩn bị nổ vol.

---

## 9. QUY TẮC QUẢN TRỊ RỦI RO, ĐI TIỀN (SIZING GC/MGC) & HARD SL ADR-028

### 1. Quy tắc Cắt lỗ (Stop Loss) Hiệu Chỉnh Theo M5 ATR (ADR-028) & 4 Nhãn Tác Chiến Kiểu 2:
- **4 Nhãn Hành Động Trực Quan trên Command Bar 3s & `KHỐI 6`:**
  * `1. THUẬN CHIỀU BUY (Phá cản)`: Đánh thuận xu hướng lên khi phá vỡ cản trên (`SHORT_GAMMA` + Air Pocket + áp lực công thành).
  * `2. ĐẢO CHIỀU SELL (Chạm cản)`: Đánh đảo chiều xuống khi giá chạm cản trên trong `GEX (+)` / trên Flip (`VPIN < 58%`).
  * `3. ĐẢO CHIỀU BUY (Chạm sàn)`: Đánh đảo chiều bật lên khi giá chạm sàn dưới trong `GEX (+)` / gần Put Wall (`VPIN < 55%`).
  * `4. THUẬN CHIỀU SELL (Thủng sàn)`: Đánh thuận xu hướng xuống khi đâm thủng sàn dưới (`SHORT_GAMMA` dưới Flip + Air Pocket + áp lực xả).
- **Biên độ Hard SL tiêu chuẩn (`KHỐI 6`):**
  * **Breakout (`Squeeze` / `Breakdown`) & Mean-Reversion (`Fade` / `Rebound`):** Hard SL tối thiểu **`>= $5.00`** (`max(5.00, 1.5 * ATR5m)` cho Breakout và `max(5.00, 1.4 * ATR5m)` cho Mean-Reversion) để tránh bị quét râu M5 trước khi chạy thật.
- **Tại sao không đặt SL quá chặt ($1.5–$2.5) như cũ?**  
  Thực chiến phiên COMEX có biên độ râu quét thanh khoản M5 thường đạt `$2.50–$4.00`. Nếu SL quá sát tường sẽ dễ bị dừng lỗ non ngay tại điểm hấp thụ thanh khoản. Khi cấu trúc vượt qua vùng Hard SL hiệu chỉnh (`>= $5.00`), tường phòng thủ đã xác nhận vỡ thật sự.

### 2. Định cỡ Vị thế (Position Sizing `GC` / `MGC`) theo Chế độ Gamma & VPIN:
- **Trong Positive Net GEX (`VPIN < 40%`):** Đi khối lượng tiêu chuẩn `100%` theo quy mô rủi ro tài khoản (`GC = $100/pt`, `MGC = $10/pt`).
- **Trong Negative Net GEX hoặc `VPIN 40%–65%`:** Giảm khối lượng xuống `50%–70%`.
- **Khi `VPIN >= 65%` (`[ĐỘC TÍNH >=65% — CẤM CHẶN TÀU]`):** Ngưng hoàn toàn lệnh Limit bắt đảo chiều (`Fade`/`Rebound` bị `[TẠM KHÓA]`), chỉ theo dấu Breakout/Breakdown thuận dòng tiền.

### 3. Quy chuẩn Thực thi Trực Tiếp Trên CME Gold Futures (Rule 8):
Toàn bộ các mốc `Call Wall`, `Put Wall`, `Zero Gamma Flip S*`, `Entry`, `SL`, `TP` trên Terminal đã đồng bộ 100% theo **CME Gold Futures (`GC` / `GC=F` / `MGC`)**. Trader đặt lệnh trực tiếp theo đúng tọa độ giá Futures COMEX mà **không** cần quy đổi trung gian sang Spot CFD, loại bỏ hoàn toàn rủi ro trượt Contango Basis.

---

## 10. CHECKLIST TÁC CHIẾN MẪU TRONG NGÀY CHO TRADER

In checklist này ra bàn làm việc hoặc lưu vào ghi chú điện thoại để tuân thủ mỗi ngày:

```markdown
[ ] 07:15 VN (Chốt OI Ngày Mới):
    - Mở Web Terminal, kiểm tra Open Interest mới chốt từ CME Clearing.
    - Ghi nhận 3 mốc quan trọng nhất: Major Call Wall, Major Put Wall và Zero Gamma Flip S*.
    - Xác định Regime: Hôm nay thị trường Positive Gamma hay Negative Gamma?

[ ] 11:00 - 13:30 VN (Phiên Á & Bước Đệm Phiên Âu):
    - Kiểm tra xem phiên Á có tôn trọng vùng nén Pinning Box (KB-1) không.
    - Cập nhật số liệu nấc 1 trước khi phiên London mở cửa.

[ ] 14:30 - 15:30 VN (London Open Rush):
    - Quan sát phản ứng giá khi dòng tiền châu Âu đổ vào.
    - Kiểm tra xem giá có tiếp cận Bounce Wall để kích hoạt Fade Sell (KB-2) hoặc Rebound Buy (KB-4) không.
    - Quan sát Wall Siege Ratio: Nếu Ratio < 0.5 thì vào lệnh; nếu Ratio >= 1.0 thì đứng ngoài canh Squeeze/Breakdown.

[ ] 18:45 - 20:30 VN (Pre-US & Tin Vĩ Mô CPI/NFP):
    - Rà soát thẻ Greeks bậc 2 (Vanna) và 25Δ Skew.
    - Nếu Put Wing dựng đứng: Cảnh giác cao độ với kịch bản sập giá xuyên thủng Put Wall (KB-5).
    - Cài đặt sẵn cảnh báo giá tại các ngưỡng Squeeze Trigger và Air Pocket.

[ ] 20:30 - 23:45 VN (Phiên Mỹ Mở Cửa & London Fix 00:00 VN):
    - Giao dịch theo đúng Ma trận 6 kịch bản MM khi thẻ phát sáng.
    - Tuân thủ nghiêm ngặt Hard SL hiệu chỉnh ADR-028 trên `KHỐI 6` (`>= $5.00` cho cả Breakout lẫn Mean-Reversion).
    - Chốt lời các lệnh Intraday trước giờ London Fix để tránh giật giá cuối ngày.
```

---
*Tài liệu được phát triển và kiểm chứng bởi đội ngũ Neiro-Quant. Nghiêm cấm sửa đổi tham số mặc định của hệ thống.*
