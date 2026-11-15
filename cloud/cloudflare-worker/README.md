# Neiro-Gold-Quant Cloudflare Worker (Free Tier $0 · Real-Time Relay)

Worker này giúp Dashboard trên **GitHub Pages** và **điện thoại** nhận nến vàng liên tục 24/7 với chi phí **$0/tháng** (không cần thuê VPS), hỗ trợ 2 chế độ:

1. **Giai đoạn 1 (Chạy ngay trong 3 phút — Yahoo `GC=F`):** Không cần khóa API nào, bật lên là điện thoại tự cập nhật nến & VPIN/BVC/Air Pocket qua HTTPS CORS.
2. **Giai đoạn 2 (0 giây Real-Time — Pepperstone cTrader Demo `XAUUSDF`):** Dùng tài khoản **cTrader Demo** + scope **`accounts` (chỉ đọc)** qua cổng WebSocket JSON chính thức `wss://demo.ctraderapi.com:5036`. Giữ nguyên giá thô `XAUUSD-F` (**basis_offset = 0.0**, không cộng bù `+$3`). Tự động gia hạn Access Token 30 ngày vĩnh viễn và tự ngắt nghỉ sau 5 phút không ai xem để bảo toàn gói Cloudflare Free (ước tính ~17% giới hạn 100k req/ngày).

---

## Cách deploy nhanh từ GitHub (Không cần cài Node/CLI trên máy)

1. Đăng nhập [Cloudflare Dashboard](https://dash.cloudflare.com/) (miễn phí).
2. Vào **Workers & Pages -> Create -> Import a repository** -> chọn repo `Neiro-Gold-Quant`.
3. Ở phần cấu hình build:
   - **Root directory:** `cloud/cloudflare-worker`
   - **Deploy command:** `npx wrangler deploy`
4. Bấm **Save and Deploy**. Cloudflare sẽ cấp URL dạng:
   `https://neiro-gold-feed.<subdomain-cua-anh>.workers.dev`
5. Mở Dashboard bấm nút **`☁ Cloud Feed`** (hoặc mở kèm `?worker=https://neiro-gold-feed.<subdomain>.workers.dev`) để nối ngay chế độ Yahoo `GC=F` từ điện thoại!

*(Hoặc nếu muốn ghi cứng URL cho mọi máy không cần nhập lại, điền URL đó vào `live_feed_worker_url` trong `config/settings.toml` rồi build lại `index.html`.)*

---

## Kích hoạt Pepperstone cTrader Demo `XAUUSDF` (0 giây — sau khi Spotware duyệt App)

1. Vào [cTrader Open API Applications](https://openapi.ctrader.com/apps) -> **Edit** App `Neiro Gold Feed` -> thêm **Redirect URI**:
   `https://neiro-gold-feed.<subdomain-cua-anh>.workers.dev/callback`
2. Trong Cloudflare Worker -> **Settings -> Variables and Secrets -> Add Secret** (mã hóa tuyệt đối, không bao giờ đưa lên GitHub):
   - `CTRADER_CLIENT_ID` = *(Client ID của App)*
   - `CTRADER_CLIENT_SECRET` = *(Client Secret của App)*
   - *(Tùy chọn)* `CTRADER_ACCOUNT_ID` = *(ID tài khoản Demo Pepperstone; nếu bỏ trống Worker tự chọn tài khoản Demo đầu tiên)*
3. Mở `/auth/url` trên Worker của anh (`https://neiro-gold-feed.<subdomain-cua-anh>.workers.dev/auth/url`) để lấy sẵn link cấp quyền **chỉ đọc `accounts` (KHÔNG cấp `trading`)**:
   `https://id.ctrader.com/my/settings/openapi/grantingaccess/?client_id=<CLIENT_ID>&redirect_uri=https://neiro-gold-feed.<subdomain>.workers.dev/callback&scope=accounts&product=web`
   Chọn tài khoản **Demo Pepperstone** -> Accept. Worker tại `/callback` sẽ tự đổi code lấy Refresh Token và lưu kín trong SQLite Durable Object.
4. Kiểm tra trạng thái tại `https://neiro-gold-feed.<subdomain>.workers.dev/health` -> thấy `"ws_connected": true` và `"symbol": "XAUUSDF"` là xong vĩnh viễn!
