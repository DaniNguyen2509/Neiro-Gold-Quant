# 🪙 Neiro-Gold-Quant — Market Microstructure & All-in-One Orderflow Terminal

[![Tactical Terminal](https://img.shields.io/badge/Web%20Terminal-Live%20Dashboard-00f2fe?style=for-the-badge&logo=github)](https://daninguyen2509.github.io/Neiro-Gold-Quant/)
[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Automated%20Sync-238636?style=for-the-badge&logo=github-actions)](https://github.com/DaniNguyen2509/Neiro-Gold-Quant/actions)
[![Python 3.12](https://img.shields.io/badge/Python-3.12%20%7C%203.14-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![Unit Tests](https://img.shields.io/badge/Tests-137%20Passed-success?style=for-the-badge&logo=pytest)](tests/)
[![Zero-Waste](https://img.shields.io/badge/Zero--Waste-%3C%2015MB-green?style=for-the-badge)](docs/spec.md)

Hệ thống Định lượng Vị thế Nhà tạo lập (Dealer Positioning), Gamma Exposure (GEX), Delta Exposure (DEX), Greeks bậc 2 (Vanna, Charm), Cấu trúc Kỳ hạn Đa tầng (Multi-Expiry Term Structure) & Market Microstructure vận hành **tự động 100% trên Cloud (Serverless Zero-Touch Automation)** cho **COMEX Gold Futures (`GC` / `MGC`) và ETF `GLD` Options Proxy**.

---

## ⚡ TRUY CẬP ALL-IN-ONE ORDERFLOW TERMINAL TRÊN ĐIỆN THOẠI & MÁY TÍNH

- **URL Dashboard Trực Tuyến:** [https://daninguyen2509.github.io/Neiro-Gold-Quant/](https://daninguyen2509.github.io/Neiro-Gold-Quant/)
- **Hệ Thống All-in-One Orderflow Terminal (Nhìn 1 Biểu Đồ Thấu Suốt Toàn Bộ):**
  - **Tab 1: NEIRO ALL-IN-ONE ORDERFLOW CANVAS:** Canvas HTML5 60 FPS tích hợp trực tiếp:
    * Air Pocket Vacuum Zones (`⚠️ AIR POCKET VACUUM [$min - $max]`) phát hiện khoảng trống thanh khoản.
    * Net GEX Profile Bars & nhãn VEX hiển thị song hành cạnh từng Strike trên thước đo giá.
    * Key Structural Boundary Lines (Call Wall, Put Wall kèm Wall Siege Ratio, Zero Gamma Flip $S^*$, Squeeze/Waterfall Triggers).
    * Sổ lệnh thang giá dọc DOM, Delta Footprint cụm nến 1M/5M, Tick-by-Tick tape (Multiplier = $100.0/oz cho GC, $10.0/oz cho MGC).
  - **Tab 2: 3-PANEL QUANT LADDER & MICROSTRUCTURE MATRIX:** Plotly Dark HUD trực quan (Net GEX Profile, OI Concentration, Vanna/Charm Flow, Bảng cấu trúc vi mô Strike Pinning Matrix, Bảng tác chiến Scalping lướt sóng trong ngày).
  - Đã loại bỏ hoàn toàn các khối kịch bản suy đoán (PHẦN 2 Structural Swing Walls, Action Banner KB-2, Ma trận 6 Kịch bản) để tối ưu độ tập trung cho trader.
- **Lịch chạy tự động (Lưới Cron Pre-Session Radar thích ứng 2 mùa):**
  - **Khối 1 (07:15 VN - 00:15 UTC):** Chốt số liệu Open Interest (OI) chính thức ngày mới từ CME Clearing.
  - **Khối 2 (12:30/14:30 VN - 05:30/07:30 UTC):** Pre-Europe & In-Session Europe Radar.
  - **Khối 3 (18:45 - 02:45 VN):** Pre-US, COMEX Gold Pit Open (19:20 VN / 08:20 EST), London Fix & In-Session New York.

---

## 🚀 KHỞI CHẠY LIVE TERMINAL CỤC BỘ (1-CLICK LOCAL LIVE RUNNER)

Khi trader muốn theo dõi bảng điện và luồng nến M5 cập nhật liên tục 60 giây/lần trực tiếp trên máy:
- **Cách 1 (Nhanh nhất - 1 Click Windows):** Nhấp đúp chuột vào file `Chay_Live_Terminal.bat` tại thư mục gốc để mở Bảng Điều Khiển Trung Tâm 7-trong-1:
  - `[1]` Chạy Live Terminal Realtime (cập nhật 15s/lần + tự động dọn RAM)
  - `[2]` Cào dữ liệu CME Options Chain mới nhất (Multi-Expiry Scraper)
  - `[3]` Dọn sạch Cache & giải phóng bộ nhớ RAM
  - `[4]` Cập nhật Snapshot 1 lần
  - `[5]` Chạy toàn bộ 137 Unit Tests tự động
  - `[6]` Mở thư mục data để thả file
  - `[7]` Thoát
- **Cách 2 (Dòng lệnh CLI):**
  ```bash
  # Chạy Live Loop 15s/lần (Tự động giám sát RAM và giải phóng bộ nhớ)
  python -m src.hud.html_dashboard --loop 15

  # Cào dữ liệu Options Chain đa kỳ hạn từ CME Barchart
  python -m src.collector.scraper --output data/options_prices_GCZ26.csv

  # Thu thập chuỗi Options Proxy GLD & tính Cost of Carry
  python -m src.collector.gold_collector

  # Dọn dẹp cache không gian làm việc và giải phóng RAM
  python -m src.hud.html_dashboard --clear-cache
  ```

---

## 📚 TÀI LIỆU KIẾN TRÚC & CẨM NANG THỰC CHIẾN

- **Cẩm nang Tác chiến Thực chiến cho Trader (Trader Playbook):** [docs/TRADER_PLAYBOOK.md](docs/TRADER_PLAYBOOK.md) *(Đọc hiểu 7 KPI, bản đồ 6 kịch bản MM, SL/TP & Air Pocket)*
- **Kiến trúc Hệ thống v3.0 (Toàn cảnh 6 tầng, Dual-View Terminal & Pure CME Engine):** [docs/architecture.md](docs/architecture.md)
- **Đặc tả Kỹ thuật Hệ thống (Tech Stack & Pipeline Spec):** [docs/spec.md](docs/spec.md)
- **Quyết định Tích Hợp Air Pocket Lên Cột Greeks & Dynamic Visible Scale Vanna/Charm (ADR-021):** [docs/decisions/ADR-021-cross-canvas-air-pocket-matrix-and-dynamic-visible-greeks-normalization.md](docs/decisions/ADR-021-cross-canvas-air-pocket-matrix-and-dynamic-visible-greeks-normalization.md)
- **Quyết định Chuẩn Hóa 1:1 Cockpit Với Neiro-NQ-Quant & 4 Cột Profile Greeks Trên Canvas (ADR-020):** [docs/decisions/ADR-020-dedicated-vanna-and-charm-ladder-column.md](docs/decisions/ADR-020-dedicated-vanna-and-charm-ladder-column.md)
- **Quyết định Giao diện Fullscreen TradingView, Mặc Định Nến M1, Zero Tabs & Realtime Tick Engine (ADR-018):** [docs/decisions/ADR-018-tradingview-fullscreen-zero-tabs-and-realtime-tick-engine.md](docs/decisions/ADR-018-tradingview-fullscreen-zero-tabs-and-realtime-tick-engine.md)
- **Quyết định Định lượng Quyền chọn Vàng, Mô hình Cost of Carry, Call Skew & Terminal Dual-View (ADR-015):** [docs/decisions/ADR-015-gold-options-cost-of-carry-call-skew-and-dual-view-terminal.md](docs/decisions/ADR-015-gold-options-cost-of-carry-call-skew-and-dual-view-terminal.md)
- **Quyết định Định Lượng Vi Cấu Trúc Greeks & Tâm Bão Pinning (ADR-014):** [docs/decisions/ADR-014-quantitative-microstructure-greeks-and-pinning-table.md](docs/decisions/ADR-014-quantitative-microstructure-greeks-and-pinning-table.md)
- **Quyết định Hiệu Chỉnh Black-76 IV Qua Forward Nội Suy (ADR-013):** [docs/decisions/ADR-013-options-chain-synthetic-forward-iv-calibration.md](docs/decisions/ADR-013-options-chain-synthetic-forward-iv-calibration.md)
- **Quyết định Định Tuyến URL Barchart & Đánh Chặn API Nội Bộ Quotes/Get (ADR-012):** [docs/decisions/ADR-012-barchart-routing-and-quotes-api-interception.md](docs/decisions/ADR-012-barchart-routing-and-quotes-api-interception.md)
- **Quyết định Bảo Vệ Bước Giá Vi Mô $5 (Adaptive Micro-Strike Guard) & Phát Hiện Dữ Liệu Cũ (ADR-011):** [docs/decisions/ADR-011-adaptive-micro-strike-guard-and-stale-options-detection.md](docs/decisions/ADR-011-adaptive-micro-strike-guard-and-stale-options-detection.md)
- **Quy chuẩn Đường cong Nụ cười Biến động (Volatility Smile & Skew Curve SVI) (ADR-009):** [docs/decisions/ADR-009-volatility-smile-and-skew-microstructure-invariants.md](docs/decisions/ADR-009-volatility-smile-and-skew-microstructure-invariants.md)
- **Quyết định Phân Tích GEX Đa Kỳ Hạn & Chấm Điểm Gamma Power (ADR-008):** [docs/decisions/ADR-008-multi-expiry-gex-and-gamma-weighted-walls.md](docs/decisions/ADR-008-multi-expiry-gex-and-gamma-weighted-walls.md)
- **Quyết định Giải Nghiệm Số Zero Gamma Flip & Wall Siege Ratio (ADR-007):** [docs/decisions/ADR-007-zero-gamma-flip-and-wall-siege-velocity.md](docs/decisions/ADR-007-zero-gamma-flip-and-wall-siege-velocity.md)

---

## 🛠️ CẤU TRÚC KHO LƯU TRỮ

```
Neiro-Gold-Quant/
├── .github/workflows/
│   └── daily_options_sync.yml   # Workflow cào Barchart, tính toán Greeks & xuất bản GitHub Pages
├── config/
│   └── settings.toml            # Cấu hình trung tâm cho Vàng (GC, GLD, Multiplier 100.0, GVZ)
├── docs/
│   ├── TRADER_PLAYBOOK.md       # Cẩm nang tác chiến thực chiến cho Trader (Playbook)
│   ├── HUONG_DAN_INDICATORS_MT5_TRADINGVIEW.md # Hướng dẫn cài đặt & hợp lưu bộ đôi Indicator
│   ├── thuat_ngu_quant.md       # Từ điển thuật ngữ Quant Options & Vi cấu trúc bỏ túi
│   ├── FAQ_VA_XU_LY_SU_CO.md    # Hỏi đáp thường gặp & hướng dẫn khắc phục sự cố
│   ├── architecture.md          # Tài liệu kiến trúc toàn cảnh v3.0 (Single Source of Truth)
│   ├── spec.md                  # Bản đặc tả kỹ thuật chi tiết
│   ├── decisions/               # 15 bản Architecture Decision Records (ADR-001 đến ADR-015)
│   └── tailieudacta/            # Công thức toán học và tài liệu đặc tả vi mô
├── src/
│   ├── collector/               # Thu thập Options Chain Barchart & yfinance GLD Proxy
│   │   ├── gold_collector.py    # Live GLD Options Proxy & Black-76 Greeks Mapper
│   │   ├── scraper.py           # Bộ cào Options Chain đa kỳ hạn Barchart
│   │   └── parser.py            # Chuẩn hóa OptionsSnapshot
│   ├── quant_engine/            # Lõi tính toán Black-76, Cost of Carry, Zero Gamma, GEX
│   │   ├── models.py            # Dataclasses & kiểu dữ liệu
│   │   ├── loader.py            # Ingestion, cleaning pipeline & benchmark fallback
│   │   ├── basis.py             # Cost of Carry (u=0.2%, y=1.5%), Dynamic Basis & EFP Analyzer
│   │   ├── synthetic.py         # Put-Call Parity Implied Spot & Expected Move Bands
│   │   ├── dealer.py            # Gamma-Weighted Walls, Zero Gamma Flip (_brentq), Wall Siege
│   │   ├── air_pocket.py        # Quét chân không thanh khoản (Air Pocket)
│   │   ├── institutional.py     # 25Δ Skew (RR/BF), Vol-Targeted Sizing & CTA Confluence
│   │   ├── level_state.py       # Finite State Machine cho từng Level
│   │   ├── scenario_engine.py   # Ma trận 6 Kịch bản Hành vi Market Maker Realtime
│   │   └── strategy.py          # Ma trận chiến lược Scalping & Swing
│   ├── hud/                     # Giao diện Tactical Terminal
│   │   ├── neiro_terminal.py    # Tab 1: NEIRO Orderflow Footprint (Canvas HTML5 60 FPS)
│   │   ├── html_dashboard.py    # Tab 2: 3-Panel Quant Ladder, Smile SVI, Dual-View Generator
│   │   └── chart_exporter.py    # Bộ xuất biểu đồ tĩnh 3-Panel Matplotlib PNG
│   └── mt5_bridge/              # Thư mục giao tiếp MetaTrader 5 (tùy chọn)
├── data/
│   └── options_prices_GCZ26.csv # Dữ liệu CME Options Chain tự động cập nhật
├── tests/                       # 133 Unit & Integration tests (100% pass)
├── Chay_Live_Terminal.bat       # Bảng điều khiển trung tâm 7-trong-1 tiện lợi
├── AGENTS.md / GEMINI.md        # Quy tắc cốt lõi & Quy trình kích hoạt Skill
└── README.md                    # Hướng dẫn truy cập và tổng quan dự án
```

---

## 🧹 QUY TẮC BẢO TỒN DUNG LƯỢNG (ZERO-WASTE MANDATE)

Dự án tuân thủ nghiêm ngặt chuẩn dung lượng siêu nhẹ:
- Toàn bộ kho lưu trữ luôn duy trì **< 15MB** (hiện tại: ~10.64MB).
- Mọi dữ liệu tạm, scratch scripts, cache đều được tự động dọn dẹp sạch sẽ sau mỗi lần thực thi.
- Không lưu trữ tệp tin nhị phân nặng trên máy cục bộ của người dùng.
