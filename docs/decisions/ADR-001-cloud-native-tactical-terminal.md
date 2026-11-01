# ADR-001: 100% Cloud-Native Automation & Plotly Tactical Web Terminal

## Status
Accepted

## Date
2026-10-19

## Context
Hệ thống Neiro-Quant cần theo dõi và giải mã cấu trúc dòng tiền quyền chọn (Options Flow, Net GEX, Greeks bậc 2 Vanna/Charm, Expected Move) cho hợp đồng Vàng CME Futures (`GCZ26`) và chiếu lên mốc giá XAUUSD Spot.

Các rào cản kỹ thuật của kiến trúc cũ:
1. **Phụ thuộc vào Laptop của người dùng:** Ban đầu dự kiến chạy daemon cục bộ trên máy tính cá nhân. Điều này không khả thi khi người dùng di chuyển, tắt máy hoặc mất điện/rớt mạng.
2. **Hạn chế của Google Colab (`Neiro_Quant.ipynb`):** Colab yêu cầu người dùng phải mở trình duyệt, bấm chạy từng cell thủ công, mount Google Drive và thường xuyên bị ngắt kết nối runtime khi nhàn rỗi (idle timeout).
3. **Thách thức khi cào dữ liệu Barchart:** Barchart sử dụng Cloudflare bot protection (HTTP 403 / 202) và bảng ảo `bc-data-grid` chỉ render các dòng hiển thị trên màn hình, khiến các công cụ cào HTML truyền thống (BeautifulSoup, Requests) bị chặn hoặc thiếu strikes.
4. **Trải nghiệm theo dõi cơ động (Mobile-First):** Trader cần xem bức tranh thị trường và các chốt chặn Wall/Squeeze/Air Pocket trực tiếp trên điện thoại vào đầu phiên Âu và suốt phiên Mỹ.

## Decision
Chuyển đổi toàn diện hệ thống sang mô hình **100% Serverless Cloud-Native Pipeline**:

1. **GitHub Actions làm Orchestrator:**
   - Sử dụng runner `ubuntu-latest` chạy ngầm hoàn toàn độc lập 24/5.
   - Thiết lập **Lưới Cron Thích Ứng 2 Mùa & Pre-Session Radar (Dual-Stage Cron)** theo giờ UTC:
     - `15 0 * * 1-5`: **07:15 VN** (Chốt số liệu Open Interest ngày mới từ CME Clearing).
     - `30 5,6,7,8 * * 1-5`: **Phiên Âu 2 nấc** thích ứng cả 2 mùa:
       - 12:30 VN (Pre-Europe Mùa Hè) & 13:30 VN (Pre-Europe Mùa Đông): Chuẩn bị bản đồ tác chiến trước giờ G.
       - 14:30 VN (In-Session Mùa Hè) & 15:30 VN (In-Session Mùa Đông): Cập nhật Greeks sau mở cửa.
     - `45 11,12,13,14,15,16 * * 1-5`: **Phiên Mỹ đón đầu**:
       - 18:45 VN (Pre-US: trước tin vĩ mô CPI/NFP 19:30 hè / 20:30 đông 45 phút).
       - 19:45, 20:45, 21:45, 22:45, 23:45 VN (Bao trọn mở cửa NYSE và chốt giá London Fix 00:00 VN).

2. **Playwright Headless Chromium + Internal API Sniffer:**
   - Khởi chạy trình duyệt Chromium không giao diện (headless) để bypass Cloudflare và lấy session cookie/token hợp lệ.
   - Đánh chặn trực tiếp endpoint API nội bộ `/proxies/core-api/v1/options/get` thay vì parse DOM bảng ảo, lấy trọn vẹn 56+ strikes trong 1 lần gọi (thời gian thực thi 60–90 giây).

3. **Plotly Tactical Web Terminal Độc Lập (`src/hud/html_dashboard.py`):**
   - Sinh file HTML độc lập chứa toàn bộ dữ liệu Plotly tương tác cao cấp (Dark Mode, 3 panels, KPI Cards, Bảng Intraday Scalping & Structural Swing).
   - Áp dụng thuật toán chống va chạm nhãn (Label Anti-Collision): Tách rời Legend (y=1.07), phân tầng độ cao cho Vanna/Charm trùng strike, đảo biên nhãn Spot.

4. **Static Hosting qua GitHub Pages & Artifacts:**
   - Tự động xuất bản `exports/index.html` lên `https://daninguyen2509.github.io/Neiro-Gold-Quant/`.
   - Lưu trữ bản backup dữ liệu CSV và HTML 7 ngày qua GitHub Actions Artifacts.

## Alternatives Considered

### 1. Giữ Google Colab làm Engine chính (`Neiro_Quant.ipynb`)
- **Ưu điểm:** Có sẵn môi trường Python, không cần cài đặt.
- **Nhược điểm:** Không có cơ chế cron tự động đáng tin cậy mà không mở trình duyệt; phụ thuộc kết nối Google Drive; dễ lỗi phiên.
- **Kết luận:** **REJECTED.** File notebook được chuyển sang trạng thái đã nghỉ hưu (retired/obsolete).

### 2. Thuê VPS Linux (AWS EC2 / DigitalOcean) chạy 24/7
- **Ưu điểm:** Toàn quyền kiểm soát server, có thể chạy cron daemon liên tục.
- **Nhược điểm:** Tốn chi phí duy trì hàng tháng ($5 - $20/tháng); phát sinh rủi ro bảo mật và công việc quản trị hệ thống (patching, OS updates); vi phạm nguyên tắc tinh gọn (Zero-Waste Mandate).
- **Kết luận:** **REJECTED.**

### 3. Streamlit Cloud / Hugging Face Spaces
- **Ưu điểm:** Dễ dựng giao diện Python nhanh.
- **Nhược điểm:** Cold-start latency cao (phải chờ 30-60 giây khi ứng dụng ngủ); giới hạn RAM dễ gây crash với biểu đồ Plotly nặng; không tối ưu cho mobile web dạng static.
- **Kết luận:** **REJECTED.**

## Consequences
- **Chi phí vận hành: 0 VNĐ ($0/month).** 11 lần chạy/ngày $\times$ 1.5 phút $\approx$ 360 phút/tháng, chỉ chiếm ~18% hạn mức 2,000 phút miễn phí hàng tháng của GitHub Actions (hoàn toàn miễn phí).
- **Độc lập 100% với laptop cá nhân:** Dữ liệu vẫn được cào, xử lý toán học và xuất bản ngay cả khi laptop của trader tắt nguồn hoặc không có mạng.
- **Bảo tồn dung lượng (Zero-Waste Compliance):** Không sinh file rác trên ổ cứng cá nhân; repository giữ nguyên độ tinh gọn (< 9 MB, vượt chuẩn yêu cầu < 15 MB).
- **Nghỉ hưu các file dư thừa:** File `H:\My Drive\Neiro-Quant\notebooks\Neiro_Quant.ipynb` và notebook cũ trong repo không còn nhiệm vụ trong pipeline vận hành chính.
