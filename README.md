# 🪙 Neiro-Gold-Quant — Market Microstructure & All-in-One Realtime Terminal

[![Tactical Terminal](https://img.shields.io/badge/Web%20Terminal-Live%20Dashboard-00f2fe?style=for-the-badge&logo=github)](https://daninguyen2509.github.io/Neiro-Gold-Quant/)
[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Automated%20Sync-238636?style=for-the-badge&logo=github-actions)](https://github.com/DaniNguyen2509/Neiro-Gold-Quant/actions)
[![Python 3.12](https://img.shields.io/badge/Python-3.12%20%7C%203.14-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![Unit Tests](https://img.shields.io/badge/Tests-Pytest%20Verified-success?style=for-the-badge&logo=pytest)](tests/)
[![Zero-Waste](https://img.shields.io/badge/Zero--Waste-%3C%2015MB-green?style=for-the-badge)](docs/spec.md)

Hệ thống Định lượng Vị thế Nhà tạo lập (Dealer Positioning), Gamma Exposure (GEX), Delta Exposure (DEX), Greeks bậc 2 (Vanna, Charm), Cấu trúc Kỳ hạn Đa tầng & Market Microstructure vận hành **tự động 100% trên Cloud (Serverless Zero-Touch Automation)** cho **100% Pure COMEX Gold Futures (`GC` / `XAUUSD-F`)**.

---

## ⚡ TRUY CẬP ALL-IN-ONE REALTIME TERMINAL TRÊN ĐIỆN THOẠI & MÁY TÍNH

- **URL Dashboard Trực Tuyến:** [https://daninguyen2509.github.io/Neiro-Gold-Quant/](https://daninguyen2509.github.io/Neiro-Gold-Quant/)
- **Hệ Thống All-in-One Orderflow Terminal (Nhìn 1 Biểu Đồ Thấu Suốt Toàn Bộ):**
  - **TRADINGVIEW FULLSCREEN CANVAS 60 FPS:** Biểu đồ Canvas Lightweight Charts 4.2 tích hợp:
    * **Air Pocket Vacuum Zones:** Dải chân không thanh khoản quét xuyên suốt nến và cột Greeks với cảnh báo `[CẤM ĐỠ DAO]`.
    * **5 Cột Profile Greeks Cố Định Trục Giá:** `FLOW | GEX | VEX | CHEX | THETA` tự động co giãn theo giá Spot (Dynamic GEX Elasticity - ADR-031).
    * **Key Structural Boundary Lines:** Call Wall, Put Wall, Zero Gamma Flip $S^*$, Squeeze/Waterfall Triggers.
    * **Thanh Chỉ Huy Tác Chiến 3 Giây (4 Thẻ):** Đọc vị Regime, Wall, Flow, Action ngay lập tức.
    * **KHỐI 4 Spine & KHỐI 6:** Thước đo khoảng cách và Ma trận Tác chiến 4 Kèo (Squeeze, Fade, Rebound, Breakdown) kèm tính toán SL/TP/Lots tự động.
    * **Nút Bấm Cào Tức Thì `[ ⚡ Sync CME ]`:** Trực tiếp kích hoạt GitHub Actions cào dữ liệu mới từ COMEX Clearing House ngay trên điện thoại khi ở ngoài đường.

- **Lịch chạy tự động (Lưới Cron Pre-Session Radar thích ứng 2 mùa):**
  - **Khối 1 (07:15 VN - 00:15 UTC):** Chốt số liệu Open Interest (OI) chính thức ngày mới từ CME Clearing.
  - **Khối 2 (12:30/14:30 VN - 05:30/07:30 UTC):** Pre-Europe & In-Session Europe Radar.
  - **Khối 3 (18:45 - 02:45 VN):** Pre-US, COMEX Gold Pit Open (19:20 VN / 08:20 EST), London Fix & In-Session New York.

---

## 🚀 KHỞI CHẠY & VẬN HÀNH TERMINAL (DESKTOP & MOBILE 1 LUỒNG DUY NHẤT)

Cả máy tính (`exports/index.html`) và điện thoại (`GitHub Pages`) đều kết nối **1 luồng trực tiếp duy nhất** qua Cloudflare Worker Edge Relay mỗi 3 giây (kết nối trực tiếp Pepperstone cTrader Open API `XAUUSD-F` 0 giây latency, không dùng Yahoo Finance, không cần chạy server `--loop` nền trên laptop):

- **Cách 1 (Nhanh nhất - 1 Click Windows):** Nhấp đúp chuột vào file `Chay_Live_Terminal.bat` tại thư mục gốc để mở Bảng Điều Khiển Trung Tâm 8-trong-1:
  - `[1]` Mở Terminal Online 100% (GitHub Pages Cloud)
  - `[2]` Đồng bộ dữ liệu & code mới nhất từ GitHub Cloud (`git pull origin main`)
  - `[3]` Cào & đồng bộ dữ liệu CME Options Chain mới nhất lên Cloud
  - `[4]` Dọn sạch Cache & giải phóng bộ nhớ RAM
  - `[5]` Cập nhật Snapshot 1 lần (`exports/index.html`)
  - `[6]` Kiểm thử hệ thống toàn diện (`pytest`)
  - `[7]` Mở thư mục `data/` để kiểm tra file CSV
  - `[8]` Thoát
- **Cách 2 (Dòng lệnh CLI):**
  ```bash
  # Cào dữ liệu CME Options Chain đa kỳ hạn từ Barchart
  python -m src.collector.scraper --output data/options_prices_GCZ26.csv

  # Tạo lại Snapshot 1 lần (HTML + version.json + tactical_levels.json)
  python -m src.hud.html_dashboard --input data/options_prices_GCZ26.csv --output exports/latest_gold_dashboard.html exports/index.html index.html --no-mt5

  # Chạy toàn bộ Test Suite kiểm thử tự động
  python -m pytest tests/ -v --tb=short

  # Dọn dẹp cache không gian làm việc và giải phóng RAM (< 15MB)
  python -m src.hud.html_dashboard --clear-cache
  ```

---

## 📚 TÀI LIỆU KIẾN TRÚC & CẨM NANG THỰC CHIẾN

- **Cẩm nang Tác chiến Thực chiến cho Trader (Trader Playbook):** [docs/TRADER_PLAYBOOK.md](docs/TRADER_PLAYBOOK.md) *(Đọc hiểu Command Bar 3s, 7 KPI, KHỐI 6 ma trận 4 kịch bản SL `>= $5.00`, VPIN/BVC & Air Pocket)*
- **Báo cáo Đánh giá Tính Chân Thật Hệ Thống (Honesty Audit):** [docs/system-honesty-audit.md](docs/system-honesty-audit.md) *(Minh bạch dữ liệu thật vs mô hình xấp xỉ vi cấu trúc)*
- **Kiến trúc Hệ thống v4.0 (Động hóa 0s, cTrader Live Feed & Pure CME Engine):** [docs/architecture.md](docs/architecture.md)
- **Đặc tả Kỹ thuật Hệ thống (Tech Stack & Pipeline Spec):** [docs/spec.md](docs/spec.md)
- **Quyết định Động Hóa Vi Cấu Trúc Options Bằng Vectorized Black-76 Greeks & Elastic GEX Engine (ADR-031):** [docs/decisions/ADR-031-realtime-vectorized-greeks-and-elastic-gex-engine.md](docs/decisions/ADR-031-realtime-vectorized-greeks-and-elastic-gex-engine.md)
- **Quyết định Cloudflare Worker cTrader Live Feed Relay (ADR-030):** [docs/decisions/ADR-030-cloudflare-worker-dual-mode-ctrader-feed.md](docs/decisions/ADR-030-cloudflare-worker-dual-mode-ctrader-feed.md)
- **Quyết định Cockpit Tác Chiến 3 Giây & Đồng Bộ 100% Realtime JS/Python (ADR-029):** [docs/decisions/ADR-029-simplified-3sec-cockpit-and-full-realtime-sync.md](docs/decisions/ADR-029-simplified-3sec-cockpit-and-full-realtime-sync.md)
- **Quyết định Hiệu Chỉnh VPIN BVC & Ma Trận Tác Chiến KHỐI 6 (ADR-028):** [docs/decisions/ADR-028-vpin-and-tactical-strategy-calibration.md](docs/decisions/ADR-028-vpin-and-tactical-strategy-calibration.md)
- **Quyết định Tối Ưu Độ Trễ Toàn Trình & Live Bridge Đa Luồng (ADR-027):** [docs/decisions/ADR-027-end-to-end-latency-and-cockpit-optimization.md](docs/decisions/ADR-027-end-to-end-latency-and-cockpit-optimization.md)
- **Quyết định Dynamic Liquidity Vacuum, FVG & Post-Sweep (ADR-026):** [docs/decisions/ADR-026-liquidity-vacuum-and-architecture-dedup.md](docs/decisions/ADR-026-liquidity-vacuum-and-architecture-dedup.md)
- **Toàn bộ 31 Bản Quyết Định Kiến Trúc (ADR-001 đến ADR-031):** Xem chi tiết tại [docs/decisions/](docs/decisions/)

---

## 🛠️ CẤU TRÚC KHO LƯU TRỮ

```
Neiro-Gold-Quant/
├── .github/workflows/
│   └── daily_options_sync.yml   # Workflow cào Barchart, tính Greeks, dispatch webhook & deploy Pages
├── cloud/cloudflare-worker/     # Serverless Edge Relay nối cTrader Open API WebSocket & trigger sync
├── config/
│   └── settings.toml            # Cấu hình trung tâm cho Vàng (GC, Multiplier 100.0, GVZ)
├── docs/
│   ├── TRADER_PLAYBOOK.md       # Cẩm nang tác chiến thực chiến cho Trader
│   ├── system-honesty-audit.md  # Báo cáo đánh giá tính chân thật và phân định dữ liệu thật vs proxy
│   ├── architecture.md          # Tài liệu kiến trúc toàn cảnh v4.0 (Single Source of Truth)
│   ├── spec.md                  # Bản đặc tả kỹ thuật chi tiết
│   ├── decisions/               # 31 bản Architecture Decision Records (ADR-001 đến ADR-031)
│   └── tailieudacta/            # Công thức toán học và tài liệu đặc tả vi mô
├── src/
│   ├── collector/               # Thu thập Options Chain Barchart (scraper, parser, validator)
│   ├── quant_engine/            # Lõi tính toán Black-76, Zero Gamma (_brentq), Level State, Tactical Matrix
│   └── hud/                     # Giao diện Tactical Terminal (neiro_terminal.py, html_dashboard.py)
├── data/
│   └── options_prices_GCZ26.csv # Dữ liệu CME Options Chain tự động cập nhật
├── tests/                       # Bộ kiểm thử Unit, Integration, Parity & Playwright E2E (pytest)
├── Chay_Live_Terminal.bat       # Bảng điều khiển trung tâm 8-trong-1 tiện lợi
├── AGENTS.md / GEMINI.md        # Hiến pháp Workspace & Quy tắc cốt lõi
└── README.md                    # Hướng dẫn truy cập và tổng quan dự án
```

---

## 🧹 QUY TẮC BẢO TỒN DUNG LƯỢNG (ZERO-WASTE MANDATE)

Dự án tuân thủ nghiêm ngặt chuẩn dung lượng siêu nhẹ:
- Toàn bộ kho lưu trữ luôn duy trì **< 15MB** (hiện tại: ~10.64MB).
- Mọi dữ liệu tạm, scratch scripts, cache đều được tự động dọn dẹp sạch sẽ sau mỗi lần thực thi.
- Không lưu trữ tệp tin nhị phân nặng trên máy cục bộ của người dùng.
