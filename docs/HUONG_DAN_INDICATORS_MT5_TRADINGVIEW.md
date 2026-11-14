# Neiro-Quant — HƯỚNG DẪN CÀI ĐẶT & SỬ DỤNG BỘ ĐÔI INDICATOR MT5 & TRADINGVIEW

> **Phiên bản:** v1.1  
> **Áp dụng cho:** Hệ sinh thái phân tích kỹ thuật và định lượng Vàng COMEX (**100% Pure CME Gold Futures `GC` / `GC1!` / `GC=F`**).  
> **Bộ chỉ báo bao gồm:**  
> 1. `2TC-v10` (Tín hiệu Judas Swing + Turtle Soup + CRB Sweep & Engulf + Slope Meter + OLHC Candlestick Structure).  
> 2. `Neiro-Liquidity-Map-v2` (Bản đồ thanh khoản ICT Macros + Session Ranges + Daily/Weekly Extremes + Equal Highs/Lows + Swept Memory).  
> **Tài liệu liên kết:** [docs/TRADER_PLAYBOOK.md](TRADER_PLAYBOOK.md), [docs/architecture.md](architecture.md).

---

## MỤC LỤC

1. [Tổng Quan Vai Trò Trong Hệ Sinh Thái Neiro-Quant](#1-tổng-quan-vai-trò-trong-hệ-sinh-thái-neiro-quant)
2. [Hướng Dẫn Cài Đặt Chi Tiết Trên MetaTrader 5 (MT5)](#2-hướng-dẫn-cài-đặt-chi-tiết-trên-metatrader-5-mt5)
3. [Hướng Dẫn Cài Đặt Chi Tiết Trên TradingView (Pine Script v6)](#3-hướng-dẫn-cài-đặt-chi-tiết-trên-tradingview-pine-script-v6)
4. [Giải Phẫu Chỉ Báo 1: 2TC-v10 (Tín Hiệu Vào Lệnh & Động Lượng)](#4-giải-phẫu-chỉ-báo-1-2tc-v10-tín-hiệu-vào-lệnh--động-lượng)
5. [Giải Phẫu Chỉ Báo 2: Neiro-Liquidity-Map-v2 (Bản Đồ Thanh Khoản Vi Mô)](#5-giải-phẫu-chỉ-báo-2-neiro-liquidity-map-v2-bản-đồ-thanh-khoản-vi-mô)
6. [Công Thức Hợp Lưu 3-Trong-1 (Confluence Strategy): Terminal + Map + 2TC](#6-công-thức-hợp-lưu-3-trong-1-confluence-strategy-terminal--map--2tc)
7. [Các Lưu Ý & Quy Tắc Bất Biến (Rules of Engagement)](#7-các-lưu-ý--quy-tắc-bất-biến-rules-of-engagement)

---

## 1. TỔNG QUAN VAI TRÒ TRONG HỆ SINH THÁI NEIRO-QUANT

Để đạt được tỷ lệ thắng cao và tỷ lệ Risk:Reward tối ưu (SL theo ma trận `KHỐI 6` ADR-028 `>= $5.00` calibrated theo `M5 ATR`, TP 15 - 40 giá theo vùng tường/Air Pocket), trader cần sự phối hợp nhịp nhàng giữa **3 tầng công cụ**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. TẦNG VĨ MÔ & VỊ THẾ MM: NEIRO-QUANT TACTICAL WEB TERMINAL                │
│    - Cung cấp: Net GEX Regime, Call/Put Walls, Zero Gamma Flip S*, 6 Kịch bản│
│    - Trả lời câu hỏi: "HÔM NAY MM ĐANG PHÒNG THỦ HAY BỊ DỒN VÀO ĐƯỜNG CÙNG?" │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. TẦNG BẢN ĐỒ THANH KHOẢN: NEIRO-LIQUIDITY-MAP-V2 (MT5 / TRADINGVIEW)       │
│    - Cung cấp: ICT Macros, Khung giờ Á/Âu/Mỹ, Equal Highs/Lows, Swept Memory│
│    - Trả lời câu hỏi: "THANH KHOẢN DỪNG LỖ CỦA NHỎ LẺ ĐANG NẰM Ở ĐÂU?"      │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. TẦNG BẤM CÒ KÍCH HOẠT: 2TC-V10 (MT5 / TRADINGVIEW)                       │
│    - Cung cấp: Tín hiệu Judas Swing, Turtle Soup, Nến OLHC, Slope Meter M5  │
│    - Trả lời câu hỏi: "CHÍNH XÁC NẾN NÀO LÀ ĐIỂM VÀO LỆNH (TRIGGER ENTRY)?"  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. HƯỚNG DẪN CÀI ĐẶT CHI TIẾT TRÊN METATRADER 5 (MT5)

Thư mục mã nguồn trong kho lưu trữ:
- Indicators: `mt5/Indicators/2TC-v10.mq5`, `mt5/Indicators/Neiro-Liquidity-Map-v2.mq5` (kèm file đã biên dịch `.ex5`).
- Thư viện Include bắt buộc: `mt5/Include/Neiro/` (`crb_engine.mqh`, `crb_liquidity.mqh`, `physics_engine.mqh`).

### Quy trình cài đặt 4 bước:

1. **Bước 1: Mở thư mục dữ liệu MT5:**
   - Mở phần mềm MetaTrader 5 trên máy tính.
   - Trên thanh menu trên cùng, chọn **File** $\rightarrow$ **Open Data Folder** (hoặc ấn phím tắt `Alt + F` rồi ấn `D`).
2. **Bước 2: Sao chép thư viện Include:**
   - Mở thư mục `MQL5\Include\` trong Data Folder vừa hiện ra.
   - Copy toàn bộ thư mục `Neiro` (nằm tại đường dẫn `mt5/Include/Neiro` của dự án) và dán vào `MQL5\Include\`.  
     *(Đảm bảo đường dẫn đích là: `MQL5\Include\Neiro\crb_engine.mqh`)*.
3. **Bước 3: Sao chép Indicators:**
   - Mở thư mục `MQL5\Indicators\` trong Data Folder.
   - Copy 4 file: `2TC-v10.mq5`, `2TC-v10.ex5`, `Neiro-Liquidity-Map-v2.mq5`, `Neiro-Liquidity-Map-v2.ex5` vào `MQL5\Indicators\`.
4. **Bước 4: Tải lại và gắn lên biểu đồ:**
   - Quay lại giao diện MT5, tại cửa sổ **Navigator** (phím tắt `Ctrl + N`), chuột phải vào mục **Indicators** chọn **Refresh**.
   - Kéo thả `Neiro-Liquidity-Map-v2` và `2TC-v10` vào biểu đồ Vàng Futures (`GC` / Gold Futures của broker) khung M5 hoặc M15.
   - Trong tab **Common**, tích chọn ô **Allow DLL imports** (nếu có yêu cầu) và nhấn **OK**.

---

## 3. HƯỚNG DẪN CÀI ĐẶT CHI TIẾT TRÊN TRADINGVIEW (PINE SCRIPT V6)

Mã nguồn được viết bằng ngôn ngữ Pine Script v6 chuẩn mực:
- `tradingview/2TC-v10.pine`
- `tradingview/Neiro-Liquidity-Map-v2.pine`

### Quy trình cài đặt:

1. Mở trình duyệt và truy cập biểu đồ Vàng trên [TradingView](https://www.tradingview.com/chart/) (mã CME Futures `GC1!`).
2. Nhìn xuống thanh công cụ dưới đáy màn hình, nhấp vào tab **Pine Editor**.
3. Mở file `tradingview/2TC-v10.pine` trong dự án bằng trình soạn thảo văn bản (Notepad, VS Code), nhấn `Ctrl + A` để copy toàn bộ nội dung.
4. Xóa sạch mọi code cũ trong khung Pine Editor của TradingView, dán toàn bộ mã vừa copy vào.
5. Nhấp vào nút **Save** (Đặt tên: `2TC-v10`), sau đó nhấp vào nút **Add to chart** (Thêm vào biểu đồ).
6. Lặp lại bước tương tự cho file `tradingview/Neiro-Liquidity-Map-v2.pine` (Đặt tên: `Neiro-Liquidity-Map-v2`).

---

## 4. GIẢI PHẪU CHỈ BÁO 1: 2TC-V10 (TÍN HIỆU VÀO LỆNH & ĐỘNG LƯỢNG)

`2TC-v10` là hệ thống phát hiện hành vi bẫy thanh khoản của Market Maker với 5 khối tính toán cốt lõi:

### 1. Judas Swing (Bẫy Quét Đầu Phiên)
- **Cơ chế:** Đầu các phiên Á, Âu (London Open 14:00 - 15:30 VN), New York (19:30 - 21:00 VN), Market Maker thường đẩy một cú bứt phá giả (Fakeout) lên đỉnh hoặc xuống đáy ngày để kích thích nhỏ lẻ đu bám và quét thanh khoản Stop Loss.
- **Tín hiệu trên chart:** Nhãn `JD` kèm mũi tên định hướng. Khi xuất hiện `JD` tại biên hỗ trợ/kháng cự, đó là tín hiệu chuẩn bị cho cú quay đầu thần tốc.

### 2. Turtle Soup (Canh Rùa - Săn Quét Đỉnh Đáy Cũ)
- **Cơ chế:** Dựa trên chiến thuật kinh điển của Linda Raschke: Giá quét qua đỉnh hoặc đáy của 20 nến gần nhất (Liquidity Sweep) nhưng không thể đóng cửa bên ngoài mà lập tức rút râu quay ngược trở vào trong range.
- **Tín hiệu trên chart:** Nhãn `TS`. Đây là tín hiệu FADE đảo chiều có xác suất thắng cực cao khi hợp lưu với `Put Wall` hoặc `Call Wall` của Neiro-Quant Terminal.

### 3. CRB (Candle Range Buffer / Sweep & Engulf)
- **Cơ chế:** Tự động vẽ các hộp khối thanh khoản (CRB Box). Khi giá quét sạch thanh khoản của nến trước rồi hình thành một cây nến nhấn chìm (Engulfing), hộp CRB chuyển màu xanh (Buy) hoặc đỏ (Sell) xác nhận phe hấp thụ đã làm chủ tình thế.

### 4. Slope Meter (Đồng Hồ Đo Độ Dốc Động Lượng)
- **Toán học vi cấu trúc:** Sử dụng hồi quy tuyến tính bậc 1 để lấy độ dốc của toàn bộ cửa sổ nến, kết hợp hồi quy parabol bậc 2 để đo gia tốc tại cây nến hiện tại ($\partial^2 P / \partial t^2$), chuẩn hóa toàn bộ theo dải biến động ATR.
- **Đọc bảng Dashboard Slope:**
  * `TANG` / `GIAM`: Xu hướng động lượng rõ ràng.
  * `DI NGANG` / `GIA LOAN`: Thị trường không có xu hướng, nén biên độ (tương thích kịch bản KB-1).
  * `DANG CONG`: Gia tốc đang bẻ lái chuẩn bị đảo chiều.

### 5. Cấu Trúc Nến OLHC / OHLC
- Tự động nhận diện cấu trúc nến tạo đà: Open-Low-High-Close (nến tăng chuẩn) và Open-High-Low-Close (nến giảm chuẩn), loại bỏ hoàn toàn các thanh nến nhiễu không có dòng tiền.

---

## 5. GIẢI PHẪU CHỈ BÁO 2: NEIRO-LIQUIDITY-MAP-V2 (BẢN ĐỒ THANH KHOẢN VI MÔ)

Bản đồ `Neiro-Liquidity-Map-v2` tự động chiếu các mốc thanh khoản của tổ chức lên màn hình mà không cần trader phải kẻ vẽ thủ công:

### 1. ICT Macros (5 Cửa Sổ Thời Gian Vàng New York)
Hệ thống tự động đóng khung và làm nổi bật 5 cửa sổ thời gian mà thuật toán định chế (Algos) bắt buộc phải tái cân bằng dòng tiền:
- Macro 1: 02:33 - 03:00 NY (London Open Drive)
- Macro 2: 04:03 - 04:30 NY (London Midday Shift)
- Macro 3: 08:50 - 09:10 NY (Pre-NY Stock Open)
- Macro 4: 09:50 - 10:10 NY (Post-Open Reversal)
- Macro 5: 10:50 - 11:10 NY (London Close Squeeze)

### 2. Session Ranges & Extremes
- **Khung biên độ 4 phiên:** Tokyo, London, New York AM, New York PM.
- **Các chốt chặn vĩ mô tự động:**
  * `ATH`: Đỉnh mọi thời đại (All-Time High).
  * `PWH` / `PWL`: Đỉnh/Đáy tuần trước (Previous Week High/Low).
  * `PDH` / `PDL`: Đỉnh/Đáy ngày hôm trước (Previous Day High/Low).
  * `Midnight Open (NY 00:00)`: Giá mở cửa nửa đêm New York — ranh giới phân định trạng thái Premium (trên Open) hay Discount (dưới Open).

### 3. Equal Highs & Equal Lows (EQH / EQL - Nam Châm Thanh Khoản)
- Khi trên thị trường xuất hiện 2 đỉnh hoặc 2 đáy bằng nhau (trong khoảng sai số cực nhỏ), đây không phải là cản cứng mà là **Bẫy Thanh Khoản (Liquidity Pool)**.
- Đằng sau EQH/EQL là hàng nghìn lệnh Stop Loss của nhỏ lẻ. Thị trường luôn bị hút về phía EQH/EQL như một thỏi nam châm trước khi quay đầu.

### 4. Swept Liquidity Memory
- Khi một mức đỉnh/đáy bị quét (Swept), đường kẻ không biến mất ngay mà chuyển sang màu xám mờ và lưu vết (Memory Trace) để cảnh báo trader rằng thanh khoản tại mốc này đã bị hấp thụ sạch.

---

## 6. CÔNG THỨC HỢP LƯU 3-TRONG-1 (CONFLUENCE STRATEGY): TERMINAL + MAP + 2TC

Đây là bí quyết tạo nên chuỗi giao dịch thành công của các Quant Trader:

```
                    CÔNG THỨC VÀO LỆNH HOÀN HẢO (A+ SETUP)
┌─────────────────────────────────────────────────────────────────────────────┐
│ ĐIỀU KIỆN 1 (VĨ MÔ): Giá tiếp cận mốc BOUNCE PUT WALL trên Neiro Terminal   │
│                      + Net GEX dương + Wall Siege Ratio < 0.5.              │
│                                    │                                        │
│                                    ▼                                        │
│ ĐIỀU KIỆN 2 (BẢN ĐỒ): Giá quét qua mốc EQL hoặc PDL trên Liquidity Map      │
│                      + Rơi vào đúng khung giờ ICT Macro New York.            │
│                                    │                                        │
│                                    ▼                                        │
│ ĐIỀU KIỆN 3 (BẤM CÒ): Chỉ báo 2TC-v10 xuất hiện tín hiệu TURTLE SOUP (TS)   │
│                      hoặc JUDAS (JD) + Nến M5 rút chân xanh.                 │
│                                    │                                        │
│                                    ▼                                        │
│ ===> KÍCH HOẠT LỆNH BUY REBOUND NGAY TỨC THÌ (SL >= $4.50 / $5.00 THEO ADR-028) <=== │
└─────────────────────────────────────────────────────────────────────────────┘
```

### So sánh Hiệu quả:
- **Nếu chỉ dùng Indicator thông thường:** Trader thấy tín hiệu `TS` nhưng không biết bên dưới là `Air Pocket` chân không $\rightarrow$ Bắt đáy và bị xả lũ cháy tài khoản.
- **Nếu hợp lưu cùng Neiro Terminal:** Khi Terminal cảnh báo `KB-5 Thủng sàn xả lũ / Air Pocket`, trader lập tức **bỏ qua mọi tín hiệu Buy của indicator**, thậm chí kích hoạt lệnh Sell đón đầu sóng rơi.

---

## 7. CÁC LƯU Ý & QUY TẮC BẤT BIẾN (RULES OF ENGAGEMENT)

1. **Tuyệt đối không tự ý thay đổi tham số mặc định:**
   - Cấu hình mặc định của `2TC-v10` và `Neiro-Liquidity-Map-v2` đã được tinh chỉnh qua hàng trăm ngày giao dịch thực chiến của Owner trên thị trường Vàng. Mọi hành vi tự ý sửa đổi thông số bên trong sẽ làm sai lệch logic nhận diện bẫy giá.
2. **Quy chuẩn mã nguồn:**
   - Phiên bản MT5 (`.mq5`, `.mqh`): Toàn bộ chú thích viết bằng tiếng Việt không dấu chuẩn ASCII thấu suốt, tuyệt đối không dùng emoji trang trí trong code.
   - Phiên bản TradingView (`.pine`): Dùng tiếng Việt có dấu trong giao diện cài đặt và tooltip để người dùng dễ đọc.
3. **Kỷ luật Stop Loss:**
   - Tuân thủ nghiêm ngặt Hard SL đã hiệu chỉnh theo `M5 ATR` trên `KHỐI 6` (`>= $5.00` cho Breakout/Fade, `>= $4.50` cho Rebound theo ADR-028) để tránh bị quét râu M5 mà vẫn bảo vệ tài khoản khi cấu trúc vi mô bị bẻ gãy.
