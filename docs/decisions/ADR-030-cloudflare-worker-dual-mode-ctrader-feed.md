# ADR-030: Cloudflare Worker Dual-Mode Relay & Pepperstone cTrader Demo Feed

- **Trạng thái:** Đã triển khai (Giai đoạn A — Cloudflare Worker + Dashboard Client + cTrader WebSocket JSON Engine)
- **Ngày:** 2026-11-15
- **Liên quan:** [ADR-027](ADR-027-end-to-end-latency-and-cockpit-optimization.md), [ADR-029](ADR-029-simplified-3sec-cockpit-and-full-realtime-sync.md)

## 1. Bối cảnh & Yêu cầu
- Dashboard tĩnh trên GitHub Pages và điện thoại cần cập nhật nến và bảng lệnh liên tục 24/7 với chi phí **\$0/tháng** (không thuê VPS).
- Chủ dự án sở hữu tài khoản cTrader Pepperstone (cung cấp mã `XAUUSDF` thời gian thực 0 giây) và chốt nguyên tắc **hiển thị trực tiếp giá thô `XAUUSD-F` (basis offset `= 0.00`, không tự ý cộng bù `+$3`)** để đồng bộ trực quan với biểu đồ TradingView đang xem.

## 2. Đánh giá phương án & Mô phỏng Free Tier
Đã đánh giá 6 phương án (`PA1–PA6`):
- **PA6 (94.60% — Được chọn):** Hybrid Cloudflare Worker + SQLite Durable Object (`CTraderFeedDO`):
  - **Chế độ A (Chạy ngay trong lúc chờ Spotware duyệt App 24–48h):** Proxy HTTPS có CORS tới Yahoo Finance `GC=F` (`1m`, `5m`, `15m`, `1h`, `1d`).
  - **Chế độ B (0 giây Real-Time):** Kết nối `wss://demo.ctraderapi.com:5036` qua flag chính thức `allow_custom_ports` (`compatibility_date = "2024-11-01"`), dùng **duy nhất quyền đọc `accounts`** (không dùng quyền `trading` hay tài khoản tiền thật), thực thi đúng chuỗi RPC JSON theo `OpenApiModelMessages.proto` (`2100/2101`, `2149/2150`, `2102/2103`, `2114/2115`, `2127/2128`, `2135`, `2137/2138`, `2131`, `2142`, `2147`).
  - Giải mã giá chuẩn `(low + delta) / 100000.0` với **`basisOffset = 0.0`** và giữ toàn bộ `CTRADER_CLIENT_ID`, `CTRADER_CLIENT_SECRET`, `Refresh Token` trong Cloudflare Encrypted Secrets + SQLite DO storage.
  - Cache 2.5s + tự ngắt WS sau 5 phút idle (`alarm()`), mô phỏng 8 giờ xem liên tục ngày cao điểm (4 ticks/giây) chỉ tiêu thụ **17,280 / 100,000 DO req/ngày (~17.28% gói Cloudflare Free)**.

## 3. Tích hợp Frontend
- `config/settings.toml`: trường `[cloud].live_feed_worker_url` đã gắn mặc định `https://neiro-gold-feed.dani-wind2509.workers.dev` (có thể override bằng biến môi trường `NEIRO_CLOUD_FEED_URL` hoặc `?worker=`).
- `src/hud/neiro_terminal.py`: nút `Cloud Feed` (`#btn-cloud-worker`), đọc query `?worker=https://...` lưu vào `localStorage`, fallback tự động trong `pollLiveYahooChart()` (`127.0.0.1:8765` -> Worker URL), tự reset series mượt mà khi đổi nguồn feed (`GC=F` <-> `XAUUSDF`) và tránh ghi đè nến live bởi `version.json`.

