# Spec: Neiro-Gold-Quant — Quantitative Gold Options Trading System & Realtime Tactical Cockpit

> **Bản đặc tả kỹ thuật chi tiết (System Specification)**  
> **Phiên bản:** v4.0 — Động Hóa 0s Toàn Diện (ADR-031), Cloudflare Edge Relay cTrader Live Feed (ADR-030) & Loại bỏ hoàn toàn Yahoo Finance  
> **Tài sản mục tiêu:** 100% Pure COMEX Gold Futures (`GC` / `XAUUSD-F`) & Options `GCZ26` *(không quy đổi Spot CFD `XAUUSD`)*.  
> **Kiến trúc:** Cloud-Native Serverless Automation (Cloudflare Worker Edge Relay + GitHub Actions + GitHub Pages, Zero-Waste < 15MB).  
> **Tài liệu tham chiếu:** [docs/architecture.md](architecture.md), [docs/TRADER_PLAYBOOK.md](TRADER_PLAYBOOK.md), [docs/system-honesty-audit.md](system-honesty-audit.md), [docs/decisions/ADR-031-realtime-vectorized-greeks-and-elastic-gex-engine.md](decisions/ADR-031-realtime-vectorized-greeks-and-elastic-gex-engine.md).

---

## 1. MỤC TIÊU HỆ THỐNG & TRIẾT LÝ VẬN HÀNH

Hệ thống **Neiro-Gold-Quant** được thiết kế để giải mã toàn diện cấu trúc vi mô thị trường (Market Microstructure), vị thế Dealer (Dealer Positioning) và áp lực dòng tiền quyền chọn (Options Flow) chuyên biệt cho thị trường Vàng thế giới:

1. **Thu thập Dữ liệu Nền Chuẩn CME COMEX (Options Chain Ingestion):**
   - Tự động bắt gói Options Chain CME Gold (`GCZ26`) từ Barchart qua Playwright Headless Chromium + Internal API Sniffer (`/proxies/core-api/v1/quotes/get` & `options/get`).
   - Tự động nhận diện và tính toán chu kỳ đáo hạn 5 tháng chẵn chuẩn CME Rule 120102.E (`resolve_front_month_cme_option`, `resolve_active_cme_futures`): **G (T2), J (T4), M (T6), Q (T8), Z (T12)**. Khi hợp đồng chính còn $\le 1$ ngày tới đáo hạn quyền chọn, hệ thống tự động rollover hợp đồng Futures active sang kỳ tiếp theo (VD: `GCZ26` $\rightarrow$ `GCG27`), nạp sẵn `NEXT_MONTHLY` (`OGF27`) + `QUARTERLY` (`OGG27`), cập nhật động toàn bộ nhãn hợp đồng trên HUD và tự tải lại khi `version.json` xuất bản kỳ hạn mới.
   - **Cơ chế Cào Tự động & Từ xa Theo Yêu Cầu (Remote On-Demand Sync):** Chốt số liệu EOD chính thức hàng ngày qua Lưới Cron GitHub Actions (07:15 VN = 00:15 UTC); đồng thời tích hợp nút bấm `[ ⚡ Sync CME ]` trên Terminal HUD trực tiếp phát webhook `repository_dispatch` tới GitHub Actions qua Cloudflare Worker `/api/trigger_sync` để cào số liệu mới ngay lập tức khi đang ở ngoài đường.

2. **Nguồn cấp Nến & Spot Thời Gian Thực 0s (Cloudflare Edge Relay & cTrader Feed):**
   - **100% Realtime 0s Latency:** Truy vấn trực tiếp luồng nến và tick từ Pepperstone cTrader Demo WebSocket (`wss://demo.ctraderapi.com:5036`) qua Cloudflare Worker Edge Relay (`https://neiro-gold-feed.dani-wind2509.workers.dev/api/yahoo_gc?tf=...`) phục vụ cặp `XAUUSD-F` (Gold Futures CFD 0s latency, chuẩn CME Gold Futures GC).
   - **Xóa bỏ hoàn toàn Yahoo Finance (`yfinance`):** Đã loại bỏ triệt để thư viện `yfinance` và nến trễ 10-15 phút của Yahoo khỏi toàn bộ mã nguồn. Chế độ `FEED_MODE = "ctrader_only"` khóa cứng nguồn nến 0s, ngắt hoàn toàn fallback để tránh làm loạn chỉ số VPIN và ma trận chiến lược KHỐI 6.

3. **Lõi Toán Định Lượng Black-76 & Động Cơ Động Hóa 0s (ADR-031):**
   - **Bản chất vật lý của Open Interest:** CME Clearing House chỉ chốt Open Interest (OI) một lần duy nhất trong ngày sau khi đóng phiên (~00:15 UTC / 07:15 sáng VN).
   - **Client-Side Vectorized Black-76 Engine (`recomputeLiveGreeksAndWalls`):** Mỗi khi nến cTrader nhảy (3s/lần), toàn bộ 35 strikes trong corridor tự động giải lại Black-76 trực tiếp trên JavaScript client (< 0.001ms/lần, 0% CPU tải):
     - **GEX Co Giãn Động (Dynamic GEX Elasticity):** Cột GEX phình to khi giá tiến sát strike (Gamma Clustering) và co rút lại khi giá rời xa.
     - **Zero Gamma Flip Di Động ($S^*_t$):** Thuật toán chia đôi (Bisection) giải nghiệm liên tục mốc phân định vị thế MM trôi theo giá nến thực.
     - **Tỷ lệ Công thành Intraday Wall Siege Velocity:** Tự động tăng tốc cảnh báo phá cản khi giá cTrader tiếp cận trong phạm vi \$4.0 của Call Wall hoặc Put Wall.

4. **Giao Diện Full-Bleed Canvas 60 FPS & Cockpit Tác Chiến 3 Giây:**
   - **TradingView Canvas (Full-bleed 100% & Múi Giờ Việt Nam `UTC+7`):** Biểu đồ Lightweight Charts 4.2 mở rộng 100% chiều ngang và chiều dọc, tích hợp Air Pocket Vacuum Zones (`[CẤM ĐỠ DAO]`), 5 cột profile (`FLOW | GEX | VEX | CHEX | THETA`) cố định theo trục giá nến với chuẩn hóa độ mở động (`Dynamic Visible Normalization`).
   - **Thanh Chỉ Huy Tác Chiến 3 Giây (4 Thẻ):** Thẻ Regime, Thẻ Wall, Thẻ Flow, Thẻ Action giúp trader đọc vị tức thì tình trạng thị trường trong 3 giây.
   - **Ma Trận Tác Chiến KHỐI 6 (4 Kèo Tiêu Chuẩn):** Tự động tính toán điểm kích hoạt, Entry, Hard Stop Loss ($\ge \$5.00$), Take Profit và Lots cho 4 kịch bản: (1) Squeeze thuận chiều, (2) Fade đảo chiều, (3) Rebound bật nảy, (4) Breakdown thủng sàn.
   - **Kiểm soát Giờ Phiên CME Globex:** Tự động nhận diện giờ nghỉ bảo trì hàng ngày (17:00–18:00 ET) và đóng cửa cuối tuần để khóa biểu đồ tại giá thanh toán chính thức (`● CME GLOBEX: CLOSED (SETTLED)`).

---

## 2. BẢNG THÔNG SỐ CỐT LÕI (GOLD SPECIFICATION TABLE)

| Hạng mục | Quy chuẩn Neiro-Gold-Quant | Ghi chú & Giải thích |
|---|---|---|
| **Tài sản HĐTL Chuẩn (Standard Futures)** | **`GC` / `XAUUSD-F`** | 100 troy ounces / hợp đồng, sàn COMEX / CME Group. |
| **Hệ số nhân Chuẩn (Multiplier)** | **$100.0** / điểm | $1.0 biến động = $100.0 PnL / hợp đồng. |
| **Mã HĐTL Micro (Micro Futures)** | **`MGC`** | 10 troy ounces / hợp đồng, Multiplier = $10.0 / điểm. |
| **Chuẩn giá Tham chiếu Terminal** | **100% Pure CME Gold Futures (`GC` / `XAUUSD-F`)** | Đồng bộ tuyệt đối chuẩn COMEX USD/oz theo Rule 8 (không quy đổi Spot `XAUUSD`). |
| **Nguồn Cấp Nến & Spot Thời Gian Thực** | **Pepperstone cTrader Demo (`XAUUSD-F`)** | WebSocket 0s latency qua Cloudflare Worker Edge Relay (`https://neiro-gold-feed.dani-wind2509.workers.dev`). |
| **Nguồn Cấp CME Options Chain & OI** | **COMEX / Barchart (`GCZ26`)** | Chốt 1 lần/ngày bởi CME Clearing House; hỗ trợ nút bấm từ xa `[ ⚡ Sync CME ]`. |
| **Độ dốc Biến động (IV Skew)** | **Call Skew** | Nhu cầu mua Call OTM phòng hộ tăng vọt làm cong vểnh cánh Call IV. |
| **Chu kỳ Đáo hạn Chính (Rollover)** | 5 tháng chẵn: **G, J, M, Q, Z** | Tháng 2, 4, 6, 8, 12 (Tháng 12 Z và Tháng 6 M là 2 kỳ hạn thanh khoản lớn nhất). |
| **Lõi Toán Options & Động Hóa 0s** | **Black-76 Vectorized Engine (ADR-031)** | Lõi giải tích thuần Python & JavaScript, 0.001ms/lần, GEX co giãn động. |
| **Giao Diện & Volume Profile (ADR-032)** | **2-Panel Side-by-Side + Session VP** | Tách chart nến sạch 70% và panel Profile 6 cột 30% [VOL|FLOW|GEX|VEX|CHEX|THETA], POC/VAH/VAL. |
| **Chỉ số Biến động Hàm ý (IV)** | **`GVZ`** (`^GVZ`) | CBOE Gold Volatility Index (đo lường IV kỳ hạn 30 ngày của Vàng). |

---

## 3. TECH STACK & ARCHITECTURE LAYERS

| Layer | Công nghệ | Vai trò & Nhiệm vụ |
|---|---|---|
| **Quant Engine Core** | Python 3.12 / 3.14 | Black-76 Greeks, Dekker-Brent Zero Gamma Solver (`_brentq`), Level State Machine, Tactical Matrix |
| **Realtime Feed Relay** | Cloudflare Worker + SQLite Durable Object | Kết nối WebSocket cTrader Open API (`XAUUSD-F`), cấp 360 nến 1M thời gian thực 0s latency |
| **Client-Side Greeks Engine** | Vectorized JavaScript (Pure Math) | Tái tính toán $\Gamma, \Delta, \text{Vanna}, \text{Charm}$, Net GEX và Zero Gamma Flip mỗi 3s (<0.001ms, 0% CPU) |
| **Data Ingestion** | Playwright Headless + Barchart API | Scraper Options Chain CME Gold COMEX (`GCZ26`) đa kỳ hạn, tự động làm sạch và chuẩn hóa |
| **TradingView Canvas HUD** | HTML5 Canvas 60 FPS + Lightweight Charts 4.2 | Biểu đồ nến full-bleed, 5 cột profile Greeks, dải Air Pocket, Pinned Wall Badges, Floating HUD |
| **Tactical Cockpit UI** | CSS Flexbox + Pure JavaScript | Thanh Chỉ Huy Tác Chiến 3 Giây, KHỐI 4 Spine, KHỐI 6 Ma trận 4 Kèo kèm SL/TP/Lots |
| **Cloud Automation** | GitHub Actions (Ubuntu) | Lưới Cron 3 tầng đa phiên (Pre-Session Radar) & Webhook `repository_dispatch` |
| **Static Deployment** | GitHub Pages | Host trực tuyến độc lập responsive, 100% Mobile Ready |

---

## 4. COMMANDS & VẬN HÀNH

```bash
# 1. Kích hoạt môi trường
.venv\Scripts\activate

# 2. Cào dữ liệu Options Chain COMEX Gold (GCZ26) từ Barchart
python -m src.collector.scraper --output data/options_prices_GCZ26.csv

# 3. Tạo Terminal Tác chiến Snapshot (tự động kết nối Cloudflare Worker 3s trên trình duyệt)
python -m src.hud.html_dashboard --input data/options_prices_GCZ26.csv --output exports/latest_gold_dashboard.html exports/index.html index.html --no-mt5

# 4. Chạy toàn bộ Test Suite kiểm thử tự động
python -m pytest tests/ -v --tb=short

# 5. Dọn dẹp cache không gian làm việc và giải phóng RAM (< 15MB Zero-Waste)
python -m src.hud.html_dashboard --clear-cache
```
