# 🪙 Neiro-Quant — Market Microstructure & Options Flow Terminal

[![Tactical Terminal](https://img.shields.io/badge/Web%20Terminal-Live%20Dashboard-00f2fe?style=for-the-badge&logo=github)](https://daninguyen2509.github.io/Neiro-Quant/)
[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Automated%20Sync-238636?style=for-the-badge&logo=github-actions)](https://github.com/DaniNguyen2509/Neiro-Quant/actions)
[![Python 3.12](https://img.shields.io/badge/Python-3.12%20%7C%203.14-blue?style=for-the-badge&logo=python)](https://www.python.org/)

Hệ thống Định lượng Vị thế Nhà tạo lập (Dealer Positioning), Gamma Exposure (GEX), Delta Exposure (DEX), Greeks bậc 2 (Vanna, Charm), Expected Move & Market Microstructure vận hành **tự động 100% trên Cloud (Serverless)** cho thị trường Vàng CME Futures (`GCZ26`) và chiếu lên XAUUSD Spot.

---

## ⚡ TRUY CẬP WEB TERMINAL TRÊN ĐIỆN THOẠI & MÁY TÍNH

- **URL Dashboard Trực Tuyến:** [https://daninguyen2509.github.io/Neiro-Quant/](https://daninguyen2509.github.io/Neiro-Quant/)
- **Cơ chế cập nhật:** Hoàn toàn tự động 24/5 trên GitHub Actions (không cần mở laptop, không cần tài nguyên máy cá nhân).
- **Lịch chạy tự động (Lưới Cron Pre-Session Radar & Dual-Stage thích ứng 2 mùa):**
  - **07:15 VN:** Chốt số liệu Open Interest (OI) chính thức ngày mới từ CME Clearing.
  - **11:00 VN:** Cập nhật phiên Á / Tokyo Midday & chuẩn bị bước đệm trước phiên Âu.
  - **Phiên Âu 2 nấc (12:30 / 13:30 & 14:30 / 15:30 VN):** Cào nấc 1 trước giờ G để lên bài tác chiến, cào nấc 2 sau khi London mở cửa 30p để cập nhật Greeks.
  - **18:45 VN (Pre-US) & 19:45, 20:45, 21:45, 22:45, 23:45 VN:** Đón đầu trước giờ ra tin vĩ mô (CPI/NFP) và bao trọn mở cửa NYSE, chốt giá London Fix (00:00 VN).

---

## 🚀 KHỞI CHẠY LIVE TERMINAL CỤC BỘ (1-CLICK LOCAL LIVE RUNNER)

Khi trader muốn theo dõi bảng điện và luồng nến M5 cập nhật liên tục 15 giây/lần trực tiếp trên máy:
- **Cách 1 (Nhanh nhất - 1 Click Windows):** Nhấp đúp chuột vào file `Chay_Live_Terminal.bat` tại thư mục gốc để mở Bảng Điều Khiển Trung Tâm 6-trong-1:
  - `[1]` Chạy Live Terminal Realtime (cập nhật 15s/lần + tự động dọn RAM)
  - `[2]` Cào dữ liệu CME Options Chain mới nhất (Multi-Expiry Scraper)
  - `[3]` Dọn sạch Cache & giải phóng bộ nhớ RAM
  - `[4]` Cập nhật Snapshot 1 lần
  - `[5]` Chạy toàn bộ 118 Unit Tests tự động
  - `[6]` Thoát
- **Cách 2 (Dòng lệnh CLI):**
  ```bash
  # Chạy Live Loop 15s/lần (Tự động giám sát RAM và giải phóng bộ nhớ)
  python -m src.hud.html_dashboard --loop 15

  # Cào dữ liệu Options Chain đa kỳ hạn từ CME Barchart
  python -m src.collector.scraper --output data/options_prices_GCZ26.csv

  # Dọn dẹp cache không gian làm việc và giải phóng RAM
  python -m src.hud.html_dashboard --clear-cache
  ```
- **Kiến trúc chống tràn RAM (Zero-Leak):**
  - Trình duyệt dùng `location.replace` thay vì `location.href` để ngăn chặn tích lũy hàng nghìn snapshot DOM trong History Stack.
  - Trang bị nút `Dọn RAM & Cache` trực tiếp trên thanh tác chiến của Dashboard.
  - Python engine thu hồi rác `gc.collect()` và xóa cache điểm giá sau mỗi vòng lặp 15s, giữ mức sử dụng RAM cố định ~90MB.

---

## 📚 TÀI LIỆU KIẾN TRÚC & QUYẾT ĐỊNH KỸ THUẬT

- **Kiến trúc Hệ thống v2.3 (Toàn cảnh 6 tầng, Multi-Expiry GEX Superposition & Pure CME Engine):** [docs/architecture.md](docs/architecture.md)
- **Đặc tả Kỹ thuật Hệ thống (Tech Stack & Pipeline Spec):** [docs/spec.md](docs/spec.md)
- **Quy chuẩn Đường cong Nụ cười Biến động (Volatility Smile & Skew Curve SVI) & 3 Bất biến Vi cấu trúc (ADR-009):** [docs/decisions/ADR-009-volatility-smile-and-skew-microstructure-invariants.md](docs/decisions/ADR-009-volatility-smile-and-skew-microstructure-invariants.md)
- **Quyết định Phân Tích GEX Đa Kỳ Hạn (Multi-Expiry) & Chấm Điểm Bức Tường Theo Gamma Power (ADR-008):** [docs/decisions/ADR-008-multi-expiry-gex-and-gamma-weighted-walls.md](docs/decisions/ADR-008-multi-expiry-gex-and-gamma-weighted-walls.md)
- **Quyết định Giải Nghiệm Số Zero Gamma Flip & Đo Vận Tốc Công Thành Wall Siege Ratio (ADR-007):** [docs/decisions/ADR-007-zero-gamma-flip-and-wall-siege-velocity.md](docs/decisions/ADR-007-zero-gamma-flip-and-wall-siege-velocity.md)
- **Quyết định Định vị Thuần CME Futures & Bộ Đánh Giá 6 Kịch Bản MM Realtime (ADR-006):** [docs/decisions/ADR-006-pure-cme-futures-and-realtime-scenario-engine.md](docs/decisions/ADR-006-pure-cme-futures-and-realtime-scenario-engine.md)
- **Quyết định Nguồn Giá Kép Realtime (yfinance GC=F + LBMA Spot) & Dynamic Basis (ADR-005):** [docs/decisions/ADR-005-realtime-dual-price-feed-and-dynamic-basis.md](docs/decisions/ADR-005-realtime-dual-price-feed-and-dynamic-basis.md)
- **Quyết định Tái Cấu Trúc Layout Chuẩn Market Maker & Chống Đè Chữ (ADR-004):** [docs/decisions/ADR-004-institutional-terminal-layout-and-anti-collision.md](docs/decisions/ADR-004-institutional-terminal-layout-and-anti-collision.md)
- **Quyết định Level State Engine & Quét Túi Chân Không Air Pocket (ADR-003):** [docs/decisions/ADR-003-level-state-engine-and-air-pocket-detection.md](docs/decisions/ADR-003-level-state-engine-and-air-pocket-detection.md)
- **Quyết định Rollover Tự động & Chế độ Scalping ATM ± 5 Strikes (ADR-002):** [docs/decisions/ADR-002-cme-front-month-auto-rollover-and-scalping-view.md](docs/decisions/ADR-002-cme-front-month-auto-rollover-and-scalping-view.md)
- **Quyết định Kiến trúc Cloud-Native (ADR-001):** [docs/decisions/ADR-001-cloud-native-tactical-terminal.md](docs/decisions/ADR-001-cloud-native-tactical-terminal.md)
- **Công thức Toán học Định lượng (Black-76, GEX, Vanna, Charm, Expected Move):** [docs/tailieudacta/CÔNG THỨC CẦN TÍNH TOÁN.md](docs/tailieudacta/CÔNG%20THỨC%20CẦN%20TÍNH%20TOÁN.md)

---

## 🛠️ CẤU TRÚC KHO LƯU TRỮ

```
Neiro-Quant/
├── .github/workflows/
│   └── daily_options_sync.yml   # Workflow cào Barchart, tính toán Greeks & xuất bản GitHub Pages
├── docs/
│   ├── architecture.md          # Tài liệu kiến trúc toàn cảnh v2.3 (Single Source of Truth)
│   ├── spec.md                  # Bản đặc tả kỹ thuật chi tiết
│   ├── decisions/               # 9 bản Architecture Decision Records (ADR-001 đến ADR-009)
│   └── tailieudacta/            # Công thức toán học và tài liệu đặc tả vi mô
├── src/
│   ├── collector/               # Playwright headless scraper & API interceptor
│   │   ├── scraper.py           # Bộ cào Options Chain đa kỳ hạn (Weekly + Monthly)
│   │   └── parser.py            # Chuẩn hóa OptionsSnapshot
│   ├── quant_engine/            # Lõi tính toán Black-76, IV solver, GEX, DEX, VEX, CHEX
│   │   ├── models.py            # Dataclasses & kiểu dữ liệu
│   │   ├── loader.py            # Ingestion, cleaning pipeline & benchmark fallback
│   │   ├── basis.py             # Realtime COMEX GC=F, Dynamic Basis & OTC Spot checking
│   │   ├── synthetic.py         # Put-Call Parity Implied Spot & Expected Move Bands
│   │   ├── dealer.py            # Gamma-Weighted Walls, Zero Gamma Flip (_brentq), Wall Siege
│   │   ├── air_pocket.py        # Quét chân không thanh khoản (Air Pocket)
│   │   ├── institutional.py     # 25Δ Skew (RR/BF), Vol-Targeted Sizing & CTA Confluence
│   │   ├── level_state.py       # Finite State Machine cho từng Level
│   │   ├── scenario_engine.py   # Ma trận 6 Kịch bản Hành vi Market Maker Realtime
│   │   └── strategy.py          # Ma trận chiến lược Scalping & Swing
│   ├── hud/                     # Giao diện Tactical Terminal
│   │   └── html_dashboard.py    # Standalone Plotly Dark Mode Terminal, Volatility Smile SVI
│   └── mt5_bridge/              # Cầu nối MetaTrader 5 (tùy chọn)
│       └── connector.py         # Kết nối MT5 & tính Auto-Basis Sync
├── data/
│   └── options_prices_GCZ26.csv # Dữ liệu CME Options Chain tự động cập nhật
├── tests/                       # 118 Unit & Integration tests (100% pass)
├── Chay_Live_Terminal.bat       # Bảng điều khiển trung tâm 6-trong-1 tiện lợi
├── AGENTS.md / GEMINI.md        # Quy tắc cốt lõi & Quy trình kích hoạt Skill
└── README.md                    # Hướng dẫn truy cập và tổng quan dự án
```

---

## 🧹 QUY TẮC BẢO TỒN DUNG LƯỢNG (ZERO-WASTE MANDATE)

Dự án tuân thủ nghiêm ngặt chuẩn dung lượng siêu nhẹ:
- Toàn bộ kho lưu trữ luôn duy trì **< 15MB** (hiện tại: ~9.95MB).
- Mọi dữ liệu tạm, scratch scripts, cache đều được tự động dọn dẹp sạch sẽ sau mỗi lần thực thi.
- Không lưu trữ tệp tin nhị phân nặng trên máy cục bộ của người dùng.