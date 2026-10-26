# ADR-011: Adaptive Micro-Strike Guard & Stale Options Data Detection

## Trạng Thái (Status)
**ĐÃ CHẤP NHẬN (ACCEPTED)** - Ngày 26/10/2026.

---

## 1. Bối Cảnh (Context)
1. **Lệch pha giữa Dữ liệu Options Tĩnh và Giá Futures Realtime:**
   - Hệ thống Neiro-Quant cập nhật giá Hợp đồng Tương lai COMEX Gold Futures (`GC=F` / `GCZ26`) realtime từng tick.
   - Tuy nhiên, chuỗi hợp đồng quyền chọn (Options Chain) lại được nạp từ file CSV tĩnh (`data/options_prices_GCZ26.csv`). Nếu người dùng chỉ chạy Dashboard Live Loop (`python -m src.hud.html_dashboard --loop 15`) mà không cào lại chuỗi Options Chain mới nhất trong ngày, Dashboard sẽ tính toán Greeks và cản vi mô dựa trên dữ liệu cũ của những ngày trước.
2. **Quy chế Niêm yết Strike $5 của CME (CME Fine Strikes near ATM):**
   - Trong các hợp đồng cận ngày đáo hạn (1DTE - 5DTE), sàn COMEX niêm yết các mức giá thực hiện bước giá hẹp **$5.0** (ví dụ: `4005, 4010, 4015, 4020, 4025, 4030, 4035, 4040, 4045, 4050`).
   - Nếu file dữ liệu cũ chỉ có các strike bước giá chuẩn **$25.0** (`4000, 4025, 4050`), thuật toán xác định `strike_above` khi giá ở `4027.5` sẽ nhảy vọt lên `4050.0` (cách tận 22.5 giá), bỏ lọt mốc chiến sự nóng `4030.0`!
   - Hệ quả: Kịch bản `KB-3 (BUY MUA ĐUỔI THEO MM / GAMMA SQUEEZE)` bị chậm kích hoạt tận 20 giá, gây rủi ro nghiêm trọng cho trader.

---

## 2. Quyết Định (Decisions)

### 2.1. Triển khai Thuật toán Adaptive Micro-Strike Guard
- Thêm hàm `resolve_adaptive_tactical_strikes()` vào `src/hud/html_dashboard.py`:
  * Khi hợp đồng là cận ngày ($\text{DTE} \le 10$ ngày), thuật toán kích hoạt lưới bảo vệ bước giá vi mô $5.0 cho vùng ATM.
  * Tự động giải mốc cản trên vi mô:
    $$\text{Fine Strike Above} = \lceil \text{spot} / 5.0 \rceil \times 5.0$$
    (Nếu $\text{Fine Strike Above} \le \text{spot}$ thì cộng thêm $5.0$).
  * Nếu khoảng cách từ giá Spot đến strike kế tiếp trong file CSV lớn hơn $5.0$ USD (phát hiện khoảng trống Fine Strike Gap):
    * Gán ngay `strike_above = Fine Strike Above` (ví dụ: `4,027.5` $\rightarrow$ `strike_above = 4,030.0`).
    * Gán `step = 5.0` và kích hoạt cờ `is_micro_guarded = True`.
    * Cân chỉnh biên vi mô:
      $$\text{next\_above} = \min(\text{next\_above}, \text{strike\_above} + 5.0)$$
      $$\text{next\_below} = \max(\text{next\_below}, \text{strike\_below} - 5.0)$$
  * Đảm bảo kịch bản `KB-3` kích hoạt ngay khi giá vượt qua $4,031.5$ thay vì chờ vượt $4,051.5$.
  * Hiển thị nhãn `(VI MÔ)` trên Visual Level Spine và bảng kịch bản để trader nhận diện ngay lập tức.

### 2.2. Cơ chế Phát hiện Dữ liệu Cũ & Tự Động Đồng Bộ (Auto-Sync Scraper)
- Đo lường tuổi thọ của file CSV:
  $$\text{File Age (Hours)} = \frac{\text{Current Time} - \text{mtime}}{3600}$$
- Nếu file CSV cũ hơn $6.0$ giờ:
  * Xuất cảnh báo nguy hiểm trên Console terminal: `[CẢNH BÁO NGUY HIỂM] File Options CSV đã cũ X giờ!`.
  * Hiển thị Badge cảnh báo màu đỏ trên thanh Header của Tactical Terminal:
    `⚠️ OPTIONS DATA CŨ (X.Xh) - CẦN CÀO MỚI`.
- **Tự động kích hoạt cào ngầm (Auto-Sync Scraper):** Trong `Chay_Live_Terminal.bat` (Mục `[1] CHAY LIVE TERMINAL`), nếu phát hiện file CSV cũ hơn 6 giờ hoặc chưa tồn tại, batch script sẽ **tự động gọi Playwright Chromium cào 1 lần duy nhất để đồng bộ chuỗi Options của ngày hôm nay** trước khi bước vào vòng lặp 15s siêu nhẹ. Người dùng không cần phải nhớ bấm thủ công Mục [2] nữa!

---

## 3. Hệ Quả (Consequences)
- **Độ chính xác vi cấu trúc:** Ngay cả khi dữ liệu CSV chưa kịp cào lại, hệ thống vẫn nhận diện chính xác mốc cản vi mô $4,030$ khi giá chạy ở $4,027.5$, bảo đảm kịch bản Gamma Squeeze (Buy đuổi) kích hoạt đúng từng tick giá.
- **Cảnh báo minh bạch:** Trader luôn biết rõ dữ liệu Options đang hiển thị là mới cào hôm nay hay là snapshot cũ từ phiên trước.
- **Khởi chạy thông minh 1-Click:** `Chay_Live_Terminal.bat` tự phục hồi dữ liệu mới mà không cần thao tác thủ công.
- **Kiểm thử tự động:** Toàn bộ 122 test cases của repository vượt qua 100%.
