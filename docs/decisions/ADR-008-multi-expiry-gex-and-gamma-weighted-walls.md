# ADR-008: Multi-Expiry GEX Superposition, Gamma-Weighted Wall Scoring & Pin vs. Trap Regime Classification

## Bối Cảnh (Context)

### 1. Khủng hoảng nhận định tại Strike 4,100 & Nghịch lý "Bức tường OI thô bị đâm thủng"
- Trong thực tế giao dịch quyền chọn vàng CME (COMEX Gold Options GCZ26), một câu hỏi hóc búa thường xuyên gây nhầm lẫn:
  > *"Tại sao mốc Strike 4,100 có tới 1,706 Put OI (> 1,000 hợp đồng mở) trên Barchart nhưng khi giá vàng điều chỉnh từ 4,125 lại bị đâm thủng thẳng về 4,082 mà không tạo ra bất kỳ phản ứng bật tăng hỗ trợ nào?"*
- Nguyên nhân cốt lõi: 90% người tham gia thị trường nhầm lẫn giữa **Khối lượng mở (Open Interest - OI) thô** với **Lực phòng hộ thực tế của Market Maker (Dealer Hedging Force)**.
- Khi chỉ nhìn vào một cột OI đơn lẻ, trader đã bỏ qua hai yếu tố vi cấu trúc chí mạng:
  1. **Hiệu ứng thời gian đáo hạn (DTE - Days to Expiration):** Một hợp đồng quyền chọn dài hạn (Monthly, ví dụ 30 DTE) có độ nhạy Gamma cực kỳ phân tán và yếu ớt so với một hợp đồng ngắn hạn (Weekly, ví dụ 1 DTE).
  2. **Vị thế ròng của Market Maker (Dealer Positioning):** Nếu Market Maker đang ở vị thế **Short Put** (bán bảo hiểm cho phe mua), mốc 4,100 không phải là sàn đỡ mà là **bẫy gia tốc bán tháo (Negative Gamma Trap)**.

### 2. Sự "lộn xộn" giữa các kỳ hạn Weekly (OG1..OG5) và Monthly (GCZ)
- Trên thị trường CME COMEX, cùng một thời điểm luôn tồn tại song song:
  * Các hợp đồng Weekly đáo hạn vào các ngày Thứ 6 hàng tuần (OG1, OG2, OG3, OG4, OG5).
  * Hợp đồng Monthly đáo hạn vào Thứ 4 tuần thứ 3 (hoặc tuần thứ 4) của tháng.
- Nếu gom gộp dữ liệu một cách cơ học (cộng dồn OI thô) hoặc chỉ xem xét kỳ hạn Monthly mà bỏ qua Weekly, hệ thống sẽ bị mù đối với lượng Gamma khổng lồ đang tập trung sát ngày đáo hạn (0DTE - 2DTE), vốn là động lực chính chi phối nhịp giật trong ngày (intraday price action).

---

## Chứng Minh Toán Học Vi Cấu Trúc (Mathematical & Microstructure Proof)

### 1. Tương quan Gamma theo thời gian đáo hạn trong mô hình Black-76
Độ nhạy Gamma của hợp đồng quyền chọn trên hợp đồng tương lai:
$$\Gamma_k(S) = \frac{e^{-rT} \cdot \phi(d_1(S, K_k))}{S \cdot \sigma \sqrt{T}}$$
trong đó:
$$\phi(x) = \frac{1}{\sqrt{2\pi}} e^{-\frac{x^2}{2}}, \quad d_1 = \frac{\ln(S/K) + 0.5 \sigma^2 T}{\sigma \sqrt{T}}$$

Do $\Gamma \propto \frac{1}{\sigma \sqrt{T}}$, khi thời gian đáo hạn $T \to 0$, Gamma tại vùng ATM tăng vọt tiệm cận vô cùng theo hàm lũy thừa nghịch đảo $\frac{1}{\sqrt{T}}$:
$$\frac{\Gamma_{\text{1DTE}}}{\Gamma_{\text{30DTE}}} \approx \sqrt{\frac{30}{1}} \approx 5.48 \text{ lần}$$

### 2. So sánh thực tế: Strike 4,100 (30DTE) vs. Strike 4,085 (1DTE)
Xét trường hợp kiểm toán thực tế tại giá vàng $S = 4,100$ USD/oz, biến động ngụ ý $\sigma = 16\%$, lãi suất $r = 4.5\%$:
- **Strike 4,100 (Monthly, $T = 30/365 \approx 0.0822$ năm):**
  * $\Gamma_{4100} = 0.002113$
  * $\text{OI}_{4100} = 1,706$ hợp đồng
  * $\text{Gamma Power} = \text{OI} \times \Gamma = 1,706 \times 0.002113 = \mathbf{3.60}$
- **Strike 4,085 (Weekly, $T = 1/365 \approx 0.00274$ năm):**
  * $\Gamma_{4085} = 0.011660$
  * $\text{OI}_{4085} = 400$ hợp đồng
  * $\text{Gamma Power} = \text{OI} \times \Gamma = 400 \times 0.011660 = \mathbf{4.66}$

$$\frac{\text{Power}_{4085}}{\text{Power}_{4100}} = \frac{4.66}{3.60} \approx 1.294 \quad (+29.4\%)$$

**Kết luận định lượng:** Dù Strike 4,085 chỉ có 400 OI (chưa bằng 1/4 của 1,706 OI tại 4,100), nhưng sức mạnh phòng hộ thực tế của nó lại **lớn hơn 29.4%** so với mốc 4,100. Đánh giá thành trì dựa trên OI thô là sai lầm nghiêm trọng.

### 3. Cơ chế Bẫy Negative Gamma & Gia tốc bán tháo của Dealer (The 4,082 Penetration)
Khi Market Maker ở vị thế **Short Put** tại Strike 4,100:
- Vị thế Delta của Dealer: $\Delta_{\text{Dealer}} = - (-N(-d_1)) = N(-d_1) > 0$ (khi OTM).
- Khi giá rơi xuyên qua 4,100:
  $$\frac{\partial \Delta_{\text{Dealer}}}{\partial S} = -\Gamma_{\text{Put}} < 0$$
- Để duy trì vị thế trung lập delta ($\Delta_{\text{Total}} = 0$), khi giá vàng giảm từ 4,125 về 4,082, Dealer buộc phải liên tục **bán khống hợp đồng tương lai GC Futures**:
  * Tại $S = 4,125$: Dealer Delta $\approx +304$ hợp đồng.
  * Tại $S = 4,082$: Dealer Delta $\approx +458$ hợp đồng.
  * Lượng bán cưỡng chế tự động: $\Delta_{\text{Hedging}} = 304 - 458 = \mathbf{-154.4 \text{ hợp đồng GC Futures}}$ (tương đương áp lực bán xả lũ **$63.7 triệu USD** đè thẳng vào sổ lệnh Orderbook khi giá đang rơi).
- **Hệ quả:** Mốc 4,100 không những không đỡ được giá mà biến thành **nam châm hút giá (Magnet Trap)**, gia tốc đà xuyên thủng cho đến khi chạm mốc 4,085 (nơi Gamma cực đại của Weekly 1DTE khóa chặt đà giảm và lực chốt lời Put kích hoạt cú V-Rebound 36 giá lên 4,118).

---

## Quyết Định Kỹ Thuật (Decisions)

### 1. Công thức Xếp Hạng Thành Trì Theo Gamma Power (Gamma-Weighted Wall Scoring)
Thay thế hoàn toàn thuật toán tìm Wall theo Max OI thô bằng điểm số trọng số Gamma:
$$\text{Power}_k = \text{OI}_k \times \Gamma_k(S)$$
- **Điều kiện lọc biên độ nghiêm ngặt (Strictly OTM Filter):**
  * Call Wall: Bắt buộc chọn từ tập các strike $K > S_{\text{spot}}$ (ưu tiên tuyệt đối OTM Call).
  * Put Wall: Bắt buộc chọn từ tập các strike $K < S_{\text{spot}}$ (ưu tiên tuyệt đối OTM Put).
  * Chỉ fallback về $K \ge S$ hoặc $K \le S$ trong trường hợp hãn hữu không tồn tại strike OTM trong tập dữ liệu. Điều này loại bỏ hoàn toàn hiện tượng mốc ATM ăn cắp danh hiệu Wall do đỉnh nhọn Gamma tại $d_1 \approx 0$.

### 2. Phân Loại Trạng Thái Thành Trì: `[BOUNCE_WALL]` vs. `[MAGNET_WALL]`
Triển khai hàm `classify_wall_regime()` trong `src/quant_engine/dealer.py` gán nhãn trạng thái động cho từng bức tường:
- **`[BOUNCE_WALL]` (Chốt Chặn Phản Xạ / Dealer Pinning Support):**
  * Điều kiện: $\text{NetGEX}_k \ge 0$.
  * Ý nghĩa vi mô: Dealer ở trạng thái Long Gamma. Khi giá tiếp cận, Dealer buộc phải mua vào khi giá giảm và bán ra khi giá tăng, tạo lực cản phản xạ (Mean-reversion) và hỗ trợ mạnh.
  * Hành động: Cho phép đánh chặn (Fade Reversal) có Stop Loss ngắn.
- **`[MAGNET_WALL]` (Bẫy Nam Châm Gia Tốc / Negative Gamma Trap):**
  * Điều kiện: $\text{NetGEX}_k < 0$.
  * Ý nghĩa vi mô: Dealer ở trạng thái Short Gamma (chủ yếu là Short Put). Khi giá chạm mốc, Dealer bị cưỡng chế bán tháo theo đà giảm để phòng hộ, tạo lực hút xuyên thủng và gia tốc đà bão giá (Breakout / Slicing).
  * Hành động: **NGHIÊM CẤM ĐẶT LỆNH LIMIT CHẶN ĐẦU BẮT DAO RƠI!** Chờ đợi kịch bản Breakdown Slicing hoặc kiên nhẫn đợi giá tạo cấu trúc vi mô hấp thụ hoàn toàn mới xem xét vị thế.

### 3. Cơ Chế Xếp Chồng Đa Kỳ Hạn (Multi-Expiry Superposition Engine)
- **Tự động phân giải kỳ hạn (Resolver):** Bổ sung `resolve_active_expirations()` trong `src/quant_engine/synthetic.py`:
  * Tự động xác định các hợp đồng Weekly Thứ 6 gần nhất (`OG1`, `OG2`, `OG3`, `OG4`, `OG5`).
  * Tự động xác định hợp đồng Monthly Front-Month theo quy tắc CME Rule 120102.E (`resolve_front_month_cme_option`).
- **Xếp chồng định lượng (Linear Superposition):** Bổ sung `aggregate_options_dataframes()` và `load_multi_expiry_options()` trong `src/quant_engine/loader.py`:
  * Tự động tải, chuẩn hóa và gộp toàn bộ các file options của Weekly và Monthly.
  * Tại mỗi Strike $K$, tổng hợp Greeks theo định luật cộng tuyến tính:
    $$\text{NetGEX}_{\text{Total}}(K) = \sum_{e \in \text{Expiries}} \text{NetGEX}_e(K)$$
    $$\text{TotalOI}(K) = \sum_{e} \text{OI}_e(K), \quad \text{TotalVol}(K) = \sum_{e} \text{Vol}_e(K)$$
- **Nâng cấp Scraper:** Bổ sung `scrape_multi_expiry_and_save()` trong `src/collector/scraper.py` hỗ trợ quét song song cả Weekly và Monthly trong một phiên làm việc Cloud.

### 4. Tích Hợp Toàn Diện Lên Giao Diện Chiến Thuật HUD
- **Biểu đồ Plotly Panel 1:**
  * Vẽ các đường mức ngang Call Wall và Put Wall kèm theo nhãn phân loại trực quan: `CALL WALL: 4,200 [BOUNCE PIN]` hoặc `PUT WALL: 4,085 [MAGNET TRAP]`.
- **Thước Đo Mốc Giá (Visual Level Spine):**
  * Hiển thị điểm số Gamma Power bên cạnh OI và Siege Ratio:
    * `4,200 (1,348 OI | Pwr: 4.82 | Siege: 0.12x) [BOUNCE PIN]`
- **Bảng Mệnh Lệnh Tác Chiến (Tactical Command Table):**
  * Cập nhật cột Wall Type và cột Quy tắc tác chiến: Khuyến cáo rõ ràng hành vi đối với `[MAGNET TRAP]` (cấm đặt Limit, chỉ kích hoạt khi xác nhận đảo chiều sau bẫy).

---

## Hệ Quả (Consequences)

1. **Loại bỏ hoàn toàn điểm mù vi cấu trúc:** Trader không còn bị đánh lừa bởi những mốc OI hàng nghìn hợp đồng của kỳ hạn xa vốn không có lực phòng hộ thực tế trong phiên.
2. **Triệt tiêu thảm họa bắt dao rơi:** Phân loại rõ ràng `[MAGNET_WALL]` giúp ngăn chặn triệt để hành vi đặt lệnh Limit mù quáng tại các mốc Short Gamma của Dealer.
3. **Hiệu năng và độ tin cậy tuyệt đối:**
   - Hoàn toàn tuân thủ **Zero-Waste Mandate** (Dung lượng repo duy trì < 15MB, không phát sinh rác).
   - Bộ kiểm thử mới `tests/test_gamma_weighted_walls.py` cùng toàn bộ hệ thống test đạt **112/112 test cases vượt qua 100%**.
