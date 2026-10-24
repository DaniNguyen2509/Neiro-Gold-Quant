# Neiro-Quant — HỎI ĐÁP THƯỜNG GẶP & HƯỚNG DẪN XỬ LÝ SỰ CỐ (FAQ & TROUBLESHOOTING)

> **Phiên bản:** v1.0 — 24/10/2026  
> **Áp dụng cho:** Toàn bộ hệ sinh thái Neiro-Quant (Tactical Web Terminal, Local Live Runner, MT5 & TradingView Indicators).  
> **Tài liệu tham chiếu:** [docs/TRADER_PLAYBOOK.md](TRADER_PLAYBOOK.md), [docs/HUONG_DAN_INDICATORS_MT5_TRADINGVIEW.md](HUONG_DAN_INDICATORS_MT5_TRADINGVIEW.md).

---

## PHẦN I: CÂU HỎI THƯỜNG GẶP (FAQ)

### Q1: Tại sao giá Vàng trên Terminal của Neiro-Quant lại cao hơn giá XAUUSD trên MT5 (Exness, IC Markets) từ 20 đến 30 USD?
* **Trả lời:**  
  * Giá trên Terminal là **Giá Hợp đồng Tương lai Vàng COMEX (CME Gold Futures `GCZ26` / `GC=F`)**, trong khi MT5 của các sàn bán lẻ là **Giá Vàng Giao Ngay (XAUUSD Spot)**.
  * Trong thị trường tài chính, giá Futures luôn cao hơn giá Spot một khoảng chênh lệch gọi là **Contango Basis Spread** (phản ánh lãi suất vốn, chi phí bảo hiểm và lưu kho thỏi vàng vật chất tại kho của sàn CME).
  * **Cách quy đổi:** Khi Terminal báo mức cản Call Wall ví dụ `4200.00`, anh chỉ cần lấy giá Futures trừ giá MT5 (ví dụ lệch 25 USD) thì mức cản tương ứng trên MT5 của anh sẽ là: $4200.00 - 25.00 = 4175.00 \text{ XAUUSD}$.

---

### Q2: Tôi không bật máy tính, chỉ xem điện thoại thì Terminal có tự cập nhật không?
* **Trả lời:**  
  * **CÓ, 100% TỰ ĐỘNG.** Hệ thống Neiro-Quant vận hành theo kiến trúc Cloud-Native (Serverless) trên máy chủ GitHub Actions.
  * Lưới Cron tự động kích hoạt cào dữ liệu, tính toán Greeks và cập nhật website [https://daninguyen2509.github.io/Neiro-Quant/](https://daninguyen2509.github.io/Neiro-Quant/) theo các mốc:
    - **07:15 VN:** Chốt số liệu Open Interest chính thức từ CME Clearing.
    - **11:00 VN:** Cập nhật phiên Á & chuẩn bị bước đệm phiên Âu.
    - **12:30 & 14:30 VN (hoặc 13:30 & 15:30 VN theo mùa):** 2 nấc phiên London.
    - **18:45 VN:** Đón đầu trước giờ ra tin vĩ mô Mỹ (CPI/NFP).
    - **19:45, 20:45, 21:45, 22:45, 23:45 VN:** Bao trọn mở cửa phiên New York và chốt giá London Fix (00:00 VN).

---

### Q3: Khi nào tôi nên dùng "Bảng điều khiển 1-Click" `Chay_Live_Terminal.bat` trên máy tính?
* **Trả lời:**  
  * Dùng khi anh đang ngồi trực tiếp trước màn hình máy tính trong phiên giao dịch sôi động và muốn **bảng điện tự động làm mới liên tục 15 giây/lần** với luồng nến M5 realtime từ COMEX.
  * File `Chay_Live_Terminal.bat` được trang bị kiến trúc tự động thu hồi bộ nhớ `gc.collect()`, giữ mức sử dụng RAM cố định ~90MB, hoàn toàn không gây nóng máy hay đơ trình duyệt.

---

### Q4: Nếu Barchart đổi cấu trúc làm GitHub Actions tạm thời chưa cào được thì tôi lấy data thế nào?
* **Trả lời:**  
  * Anh chỉ mất **0.2 giây** bằng cách sử dụng **Super Bookmarklet 1-Click** đã được viết sẵn trong [docs/tailieudacta/HUONG_DAN_LAY_DATA_BARCHART_1CLICK.md](tailieudacta/HUONG_DAN_LAY_DATA_BARCHART_1CLICK.md).
  * Mở trang Barchart Options trên trình duyệt, ấn vào Bookmarklet trên thanh dấu trang. File dữ liệu `options_prices_GCZ26.csv` chuẩn sẽ tự động tải về máy. Anh chỉ việc thả vào thư mục `data/` là Terminal chạy ngay lập tức.

---

## PHẦN II: HƯỚNG DẪN XỬ LÝ SỰ CỐ KỸ THUẬT (TROUBLESHOOTING)

### 1. Sự cố: Nhấp đúp vào `Chay_Live_Terminal.bat` bị tắt ngấm hoặc báo lỗi "python is not recognized"
* **Nguyên nhân:** Máy tính chưa cài đặt Python hoặc chưa tích chọn ô "Add Python to PATH" khi cài đặt.
* **Cách khắc phục:**
  1. Tải và cài đặt Python phiên bản 3.12 hoặc 3.14 từ trang chủ `python.org`.
  2. **Quan trọng:** Trong màn hình cài đặt đầu tiên, bắt buộc phải tích chọn ô vuông **"Add Python to PATH"**.
  3. Mở Command Prompt (cmd) gõ `python --version` để kiểm tra.

---

### 2. Sự cố: Chạy cào dữ liệu báo lỗi "Playwright Executable Doesn't Exist"
* **Nguyên nhân:** Thư viện Playwright chưa tải trình duyệt Chromium không đầu (headless browser).
* **Cách khắc phục:**  
  Mở terminal tại thư mục dự án và chạy dòng lệnh sau (chỉ cần chạy 1 lần duy nhất):
  ```bash
  python -m playwright install chromium
  ```

---

### 3. Sự cố: Trình duyệt bị tích lũy hàng nghìn tab/snapshot khi chạy Live Terminal liên tục
* **Nguyên nhân:** Các dashboard web thông thường dùng `window.location.reload()` hoặc `location.href` khiến lịch sử trình duyệt phình to chiếm hàng GB RAM.
* **Giải pháp độc quyền của Neiro-Quant:**
  * Neiro-Quant sử dụng cơ chế `location.replace()` triệt tiêu hoàn toàn History Stack.
  * Đồng thời trên thanh tác chiến của Dashboard đã trang bị sẵn nút **"Dọn RAM & Cache"**.
  * Anh cũng có thể chọn mục `[3] DON SACH CACHE & GIAI PHONG BO NHO` trong file `Chay_Live_Terminal.bat`.

---

### 4. Sự cố: Cài Indicator vào MT5 bị báo lỗi biên dịch (Compilation Error)
* **Nguyên nhân:** Thiếu thư mục thư viện `Include\Neiro\`.
* **Cách khắc phục:**
  1. Mở MT5 $\rightarrow$ **File** $\rightarrow$ **Open Data Folder** $\rightarrow$ `MQL5\Include\`.
  2. Đảm bảo thư mục `Neiro` (chứa `crb_engine.mqh`, `crb_liquidity.mqh`, `physics_engine.mqh`) đã được copy vào đúng vị trí này.
  3. Khởi động lại MT5 hoặc ấn phím `F7` trong MetaEditor để biên dịch lại file `.mq5`.

---

### 5. Sự cố: Dán code vào TradingView bị báo lỗi phiên bản Pine Script
* **Nguyên nhân:** Dùng phiên bản Pine Script cũ (v4 hoặc v5).
* **Cách khắc phục:**  
  Cả 2 indicator của Neiro-Quant đều được viết bằng **Pine Script v6** mới nhất (dòng đầu tiên có `//@version=6`). Anh hãy mở một cửa sổ mới trong Pine Editor của TradingView, xóa trắng toàn bộ nội dung mẫu ban đầu rồi mới dán code vào.
