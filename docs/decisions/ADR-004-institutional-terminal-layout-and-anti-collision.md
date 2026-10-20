# ADR-004: Institutional Market Maker Terminal Layout & Clean Anti-Collision Architecture

## Status
Accepted

## Date
2026-10-20

## Context
1. **Hiện tượng "Dính chùm" (Visual Clutter & Label Stacking) trên Panel 1:**
   - Khi mở rộng bộ lọc hiển thị lên `ATM ± 10 Strikes` (dải 21 strikes từ 4,050 đến 4,350), biểu đồ xuất hiện sự không đồng nhất về bước giá:
     - Vùng trung tâm (quanh ATM 4,150 - 4,200): bước giá dày đặc **$5** (11 strikes).
     - Vùng ngoại vi (dưới 4,150 và trên 4,200): bước giá giãn cách **$25** (4050, 4075, 4100, 4125...).
   - Trên trục Y số học tuyến tính (Linear Numeric Axis), 11 strike bước giá $5 bị nén chặt vào một khoảng không gian hẹp.
   - Việc nhồi nhét tới 5 hộp văn bản lớn (`[PUT WALL]`, `CỬA ẢI`, `SÀN ĐỠ`, `TRẠM NGHỈ`, `CME FUTURES`) chứa đầy đủ thông số Entry, SL, TP ngay trong lòng cột Bar của Panel 1 đã dẫn đến hiện tượng các hộp nhãn đè chồng lên nhau, che khuất thanh bar Net GEX và gây rối loạn thị giác cho trader.

2. **Khảo sát chuẩn mực hiển thị của các Market Maker & Institutional Desks:**
   - Các hệ thống định lượng tổ chức hàng đầu (như SpotGamma HERO/Trace, MenthorQ, Genesis Volatility, CBOE LiveVol):
     - **Biểu đồ là để đọc "Hình thái" (Shape & Distribution):** Thanh bar cần tuyệt đối sạch sẽ, thanh thoát để người quan sát nhận diện ngay điểm lồi lõm thanh khoản (Peaks, Valleys, Air Pockets), điểm đảo pha Gamma Flip, và vị trí các bức tường lớn (Major Walls).
     - **Không nhồi nhét văn bản tác chiến vào lòng biểu đồ:** Toàn bộ thông số chi tiết (Entry, Hard SL, Take Profit, Lot size, Cảnh báo Air Pocket) được bố trí khoa học tại **Bảng Ma Trận Tác Chiến (Execution Matrix)** và **Radar Vi Mô (Level State Engine)** ngay bên dưới.
     - **Nhãn trên biểu đồ chỉ dùng Margin Badges:** Chỉ đánh dấu đường kẻ mức giá then chốt kèm nhãn rút gọn (Right/Left Margin Badge) như `Call Wall $4,200`, `Put Wall $4,200`, `CME: $4,179.75`.

## Decision
1. **Tái cấu trúc hiển thị Panel 1 theo chuẩn Institutional Clean Layout:**
   - **Xóa bỏ các hộp văn bản cồng kềnh đè trong chart:** Loại bỏ các khối chú thích nhiều dòng (`ay=18`, `ay=-16`, `ax=0`) ở `x=0.03` gây dính chùm.
   - **Chuẩn hóa đường kẻ mức giá (Clean Strategic Level Lines):**
     - Đường tím nét đứt (`#A855F7`): Call Wall.
     - Đường ngọc nét đứt (`#34D399`): Put Wall.
     - Đường xanh neon (`#38BDF8`): CME Futures Price.
     - Nhãn mức giá được neo gọn gàng, thanh lịch ở mép lề với kích thước nhỏ gọn (Single-line Badges).
2. **Khai thác tối đa sức mạnh Tương tác (Interactive Hover Tooltips):**
   - Thiết lập `hovertemplate` phong phú trên Plotly: Khi trader rê chuột vào bất kỳ thanh bar nào, hệ thống lập tức hiển thị đầy đủ thông tin vi mô của Strike đó (Strike, Net GEX, Call OI, Put OI, Call Vol, Put Vol, Net VEX, Net CHEX) mà không làm rác biểu đồ tĩnh.
3. **Phân định trách nhiệm rõ ràng giữa Biểu đồ và Bảng tác chiến:**
   - **3 Panels phía trên:** Đóng vai trò Bản đồ Toàn cảnh Vi mô (Macroscopic Profile Map).
   - **Radar Vi mô (Tầng 4):** Giám sát trạng thái động của từng Level (`DORMANT`, `TESTING`, `DEFENDED`, `SLICED`).
   - **Bảng Tác Chiến Phần 1 & Phần 2:** Nơi cung cấp đầy đủ thông số hành động cụ thể (Trigger, Entry, SL, TP, Lot size, Ghi chú tâm lý Market Maker).

## Consequences
- **Giao diện đẳng cấp, không còn đè chữ:** Khắc phục 100% hiện tượng dính chùm ở vùng bước giá $5, biểu đồ trở nên chuyên nghiệp, thanh thoát đúng chuẩn Hedge Fund Terminal.
- **Trải nghiệm người dùng vượt trội:** Trader nhìn vào chart nhận diện ngay cấu trúc phân bổ Gamma trong 1 giây, sau đó nhìn xuống bảng bên dưới để lấy chính xác thông số vào lệnh.
- **Duy trì tính toàn vẹn toán học:** Giữ nguyên trục số thực tuyến tính để phản ánh trung thực khoảng cách giá và các vùng rỗng thanh khoản (Air Pockets).
