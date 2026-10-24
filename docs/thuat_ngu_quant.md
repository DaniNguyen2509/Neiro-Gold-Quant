# Neiro-Quant — TỪ ĐIỂN THUẬT NGỮ QUANT OPTIONS & VI CẤU TRÚC THỊ TRƯỜNG

> **Phiên bản:** v1.0 — 24/10/2026  
> **Mục tiêu:** Cung cấp tài liệu tra cứu bỏ túi nhanh, chuẩn mực quốc tế về tài chính định lượng, quyền chọn phái sinh và vi cấu trúc thị trường (Market Microstructure) cho cả con người và các AI Agent khi làm việc trong hệ thống Neiro-Quant.  
> **Tài liệu tham chiếu:** [docs/architecture.md](architecture.md), [docs/tailieudacta/CÔNG THỨC CẦN TÍNH TOÁN.md](tailieudacta/CÔNG%20THỨC%20CẦN%20TÍNH%20TOÁN.md).

---

## A. CÁC ĐỊNH CHẾ & VỊ THẾ CỐT LÕI

### 1. Market Maker (Nhà tạo lập thị trường - MM / Dealer)
- **Định nghĩa:** Các ngân hàng đầu tư và định chế tài chính lớn (Goldman Sachs, Citadel, Jane Street, J.P. Morgan) cam kết cung cấp thanh khoản liên tục bằng cách yết giá chào mua (Bid) và chào bán (Ask) cho các hợp đồng quyền chọn.
- **Mục tiêu:** Ăn chênh lệch giá Bid/Ask (Spread) và phí thời gian (Theta Decay). Họ **không muốn đoán hướng đi của thị trường** và luôn tìm cách giữ danh mục ở trạng thái trung lập rủi ro (Delta-Neutral).

### 2. Dynamic Delta Hedging (Phòng hộ Delta động)
- **Định nghĩa:** Cơ chế sống còn của Market Maker. Khi MM bán một hợp đồng Call hoặc Put cho khách hàng, họ bị chịu rủi ro hướng đi. Để triệt tiêu rủi ro này, MM phải liên tục mua hoặc bán hợp đồng Hàng hóa Tương lai COMEX Gold Futures (`GC`) để đưa Delta tổng về 0.
- **Hệ quả vi mô:** Khối lượng phòng hộ của Dealers tạo ra các đợt sóng mua/bán khổng lồ trên thị trường Futures và chi phối đường đi của giá Vàng.

### 3. Open Interest (Vị thế mở - OI)
- **Định nghĩa:** Tổng số lượng hợp đồng quyền chọn đang còn hiệu lực và chưa được tất toán hay thanh lý.
- **Đặc thù CME:** Dữ liệu Open Interest của sàn CME là **tĩnh trong phiên** (chỉ được Trung tâm Bù trừ CME Clearing House cập nhật chính thức 1 lần mỗi ngày vào sáng sớm ~07:15 VN).

### 4. Volume (Khối lượng giao dịch trong phiên)
- **Định nghĩa:** Số lượng hợp đồng được sang tay khớp lệnh trực tiếp trong ngày giao dịch hiện tại.
- **So sánh với OI:** OI là lượng tiền lưu kho dài hạn; Volume là dòng tiền tấn công ngắn hạn trong ngày.

---

## B. BỘ CHỈ SỐ GREEKS ĐỊNH LƯỢNG (BLACK-76 MODEL)

Vì đối tượng là Quyền chọn trên Hợp đồng Tương lai Vàng (Options on COMEX Gold Futures), hệ thống Neiro-Quant sử dụng chuẩn mực mô hình **Black-76** (thay vì Black-Scholes gốc):

### 1. Delta ($\Delta$)
- Đo lường mức độ thay đổi giá của Option khi giá Futures di chuyển 1 USD:
  $$\Delta = \frac{\partial V}{\partial F}$$
- Đối với Call: $\Delta \in (0, 1)$. Đối với Put: $\Delta \in (-1, 0)$.

### 2. Gamma ($\Gamma$) & Gamma Exposure (GEX)
- **Gamma:** Đạo hàm bậc 2 của giá Option theo giá Futures, đo tốc độ thay đổi của Delta:
  $$\Gamma = \frac{\partial^2 V}{\partial F^2}$$
- **Gamma Exposure (GEX):** Lượng giá trị đô la mà Dealer bắt buộc phải mua hoặc bán Futures cho mỗi 1% biến động của giá thị trường:
  $$\text{GEX}_{\text{call}} = +\left(\Gamma_{\text{call}} \cdot OI_{\text{call}} \cdot 100 \cdot F^2 \cdot 0.01\right)$$
  $$\text{GEX}_{\text{put}} = -\left(\Gamma_{\text{put}} \cdot OI_{\text{put}} \cdot 100 \cdot F^2 \cdot 0.01\right)$$
- **Chế độ Net GEX:**
  * **Positive Gamma ($GEX > 0$):** Dealer mua khi giảm, bán khi tăng $\rightarrow$ Hấp thụ biến động, nén giá (Mean-reverting).
  * **Negative Gamma ($GEX < 0$):** Dealer bị ép mua đuổi khi tăng, bán tháo khi giảm $\rightarrow$ Gia tốc biến động cực đại, nguy cơ quét sóng 2 đầu.

### 3. Vanna ($\frac{\partial \Delta}{\partial \sigma}$) & VEX (Vanna Exposure)
- Đo lường độ nhạy của Delta khi Biến động ngầm định (Implied Volatility - IV) tăng/giảm 1%.
- Khi có tin tức vĩ mô bất ngờ (CPI/NFP/FOMC), IV tăng vọt kích hoạt hiệu ứng Vanna, ép Dealer tái cân bằng hàng nghìn hợp đồng chỉ trong vài giây.

### 4. Charm ($-\frac{\partial \Delta}{\partial T}$) & CHEX (Charm Exposure)
- Tốc độ suy biến của Delta theo dòng thời gian trôi qua mỗi ngày (Delta Decay).
- Càng về cuối phiên (đặc biệt các ngày thứ Sáu đáo hạn tuần hoặc 0DTE), hiệu ứng Charm càng mạnh, kéo giá về phía các bức tường thanh khoản dày đặc nhất.

---

## C. CÁC MỐC CẤU TRÚC VI MÔ CỦA NEIRO-QUANT

### 1. Major Call Wall (Trần Phòng Ngự Call)
- Mức Strike tập trung Open Interest Call lớn nhất ngoài biên giá hiện tại ($Strike \ge Spot$).
- Đây là trần nhà cứng nơi Market Maker bảo vệ các vị thế bán Call của mình bằng các lệnh chặn bán mạnh mẽ.

### 2. Major Put Wall (Sàn Phòng Ngự Put)
- Mức Strike tập trung Open Interest Put lớn nhất dưới biên giá hiện tại ($Strike \le Spot$).
- Đây là nền móng bê tông nơi Market Maker mua gom hợp đồng để đỡ giá.

### 3. Gamma-Weighted Wall Scoring (ADR-008)
- Thay vì lấy mốc OI thô, hệ thống xếp hạng thành trì bằng chỉ số **Gamma Power**:
  $$\text{Gamma Power} = \text{Open Interest} \times \Gamma$$
- **`[BOUNCE_WALL]`:** Bức tường nằm trong vùng Dealer Long Gamma $\rightarrow$ Đóng vai trò lò xo đàn hồi đẩy lùi giá, an toàn cho lệnh Fade Reversal.
- **`[MAGNET_WALL]`:** Bức tường nằm trong vùng Dealer Short Gamma $\rightarrow$ Đóng vai trò nam châm hút giá và xuyên thủng, cấm đặt Limit bắt đáy đỉnh.

### 4. Zero Gamma Flip ($S^*$) (ADR-007)
- Điểm đảo pha mà tại đó Net GEX của toàn thị trường chuyển từ Dương sang Âm (hoặc ngược lại).
- Được giải nghiệm số liên tục chính xác tuyệt đối bằng thuật toán Dekker-Brent (`_brentq` thuần Python), triệt tiêu sai số làm tròn của phương pháp xấp xỉ thô.

### 5. Wall Siege Ratio (Tỷ Lệ Công Thành) (ADR-007)
- Thước đo vận tốc tấn công bức tường phòng thủ trong ngày:
  $$\text{Wall Siege Ratio} = \frac{\text{Intraday Volume}}{\text{Baseline OI}}$$
- **Ratio < 0.5:** Tường kiên cố, tấn công thất bại $\rightarrow$ Đánh chặn đảo chiều.
- **Ratio $\ge 1.0$:** Báo động đỏ, tường bị phá vỡ $\rightarrow$ Đánh bứt phá Squeeze/Breakdown.

### 6. Air Pocket (Túi Chân Không Thanh Khoản) (ADR-003)
- Vùng khoảng trống giữa các Strike có Open Interest rớt xuống dưới **35% mức trung bình** 20 Strike lân cận.
- Tại vùng này không có thanh khoản đối ứng $\rightarrow$ Giá rơi tự do không phanh. **Quy tắc bất biến: Tuyệt đối cấm đỡ dao rơi!**

### 7. Synthetic ATM Pivot ($S_{\text{Implied}}$) & Expected Move
- Dựa trên nguyên lý Ngang giá Quyền chọn (Put-Call Parity):
  $$S_{\text{Implied}} = K_{\text{ATM}} + e^{rT} \cdot [Call_{\text{mid}} - Put_{\text{mid}}]$$
- Trục cân bằng phản ánh kỳ vọng thực tế của dòng tiền tổ chức mà không bị méo mó bởi các lệnh ảo.

---

## D. CÁC THUẬT NGỮ THỊ TRƯỜNG PHÁI SINH QUAN TRỌNG

### 1. Contango Basis (Độ lệch Tương lai - Giao ngay)
- Giá Hợp đồng Tương lai (`GC=F`) cao hơn giá Vàng Giao ngay XAUUSD Spot do phản ánh chi phí vốn, lưu kho, bảo hiểm và thời gian đáo hạn.
- Độ lệch chuẩn thông thường: từ **15 đến 30 USD/oz**.

### 2. SVI (Stochastic Volatility Inspired) & Volatility Smile (ADR-009)
- Mô hình tham số hóa đường cong nụ cười biến động ngầm định (IV), đảm bảo tính trơn tru và không tạo ra cơ hội kinh doanh chênh lệch giá (No-Arbitrage Invariants).
- **Put Skew:** Cánh Put bên trái vểnh cao hơn cánh Call bên phải $\rightarrow$ Thị trường lo sợ sập giá.

### 3. Gamma Squeeze
- Khi giá vượt qua Call Wall phòng hộ của MM, MM bị ép phải nhảy vào mua đuổi hợp đồng Futures bằng lệnh Market để tự cứu mình, tạo nên ngọn nến dựng đứng quét sạch phe bán.
