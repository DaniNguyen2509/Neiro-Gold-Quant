# Neiro-Gold-Quant Cloudflare Worker (Free Tier $0 · Real-Time Relay)

Worker này giúp Dashboard trên **GitHub Pages** và **điện thoại** nhận nến vàng liên tục 24/7 với chi phí **$0/tháng** (không cần thuê VPS), hỗ trợ 2 chế độ:

1. **Giai đoạn 1 (Chạy ngay trong lúc chờ Spotware duyệt App — Yahoo `GC=F`):** Không cần khóa API nào, bật lên là cả điện thoại và máy tính tự cập nhật nến & VPIN/BVC/Air Pocket mỗi 3 giây qua Cloudflare Worker (không cần bật cầu nối `--loop` trên laptop).
2. **Giai đoạn 2 (0 giây Real-Time & Chống Trộn Nến — Pepperstone cTrader Demo `XAUUSDF`):** Dùng tài khoản **cTrader Demo** + scope **`accounts` (chỉ đọc)** qua cổng WebSocket JSON chính thức `wss://demo.ctraderapi.com:5036`. Giữ nguyên giá thô `XAUUSD-F` (**basis_offset = 0.0**, không cộng bù `+$3`). Tự động gia hạn Access Token 30 ngày vĩnh viễn và tự ngắt nghỉ sau 5 phút không ai xem để bảo toàn gói Cloudflare Free (ước tính ~17% giới hạn 100k req/ngày). **Chống trộn dữ liệu (Zero-Mixing Guarantee):** ngay sau khi cấp quyền OAuth xong (`tok` đã lưu trong Durable Object) hoặc đặt `FEED_MODE = "ctrader_only"`, Worker **tuyệt đối không fallback về nến Yahoo `-10m`** nếu WS cTrader chập chờn — trả HTTP `503` (`available: false`) để giao diện giữ nguyên nến Pepperstone gần nhất và tránh làm nhiễu `VPIN` / `KHỐI 6`.

---

## Cách deploy nhanh từ GitHub (Không cần cài Node/CLI trên máy)

1. Đăng nhập [Cloudflare Dashboard](https://dash.cloudflare.com/) (miễn phí).
2. Vào **Workers & Pages -> Create application -> Import a repository -> Continue with GitHub** -> chọn repo `Neiro-Gold-Quant`.
3. Ở phần cấu hình **Set up your application**:
   - **Project name:** `neiro-gold-feed`
   - **Build command:** để trống
   - **Deploy command:** `npx wrangler deploy`
   - Mở **Advanced settings -> Path:** `cloud/cloudflare-worker`
4. Bấm **Deploy**. Endpoint production của hệ thống là:
   `https://neiro-gold-feed.dani-wind2509.workers.dev`
5. Đường dẫn này đã được gắn mặc định vào `live_feed_worker_url` trong `config/settings.toml` để mọi điện thoại / GitHub Pages tự nối ngay; hoặc anh có thể đổi/override tạm bằng nút **`Cloud Feed`** hoặc `?worker=https://...`.

---

## Kích hoạt Pepperstone cTrader Demo `XAUUSDF` (0 giây — sau khi Spotware duyệt App)

1. Vào [cTrader Open API Applications](https://openapi.ctrader.com/apps) -> **Edit** App `Neiro Gold Feed` -> thêm **Redirect URI**:
   `https://neiro-gold-feed.dani-wind2509.workers.dev/callback`
2. Trong Cloudflare Worker -> **Settings -> Variables and Secrets -> Add Secret** (mã hóa tuyệt đối, không bao giờ đưa lên GitHub):
   - `CTRADER_CLIENT_ID` = *(Client ID của App)*
   - `CTRADER_CLIENT_SECRET` = *(Client Secret của App)*
   - *(Tùy chọn)* `CTRADER_ACCOUNT_ID` = *(ID tài khoản Demo Pepperstone; nếu bỏ trống Worker tự chọn tài khoản Demo đầu tiên)*
3. Mở `https://neiro-gold-feed.dani-wind2509.workers.dev/auth/url` để lấy sẵn link cấp quyền **chỉ đọc `accounts` (KHÔNG cấp `trading`)**:
   Chọn tài khoản **Demo Pepperstone** -> Accept. Worker tại `/callback` sẽ tự đổi code lấy Refresh Token và lưu kín trong SQLite Durable Object.
4. Kiểm tra trạng thái tại `https://neiro-gold-feed.dani-wind2509.workers.dev/health` -> thấy `"ws_connected": true` và `"symbol": "XAUUSDF"` là xong vĩnh viễn!
