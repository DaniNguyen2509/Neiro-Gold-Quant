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
  - **Phiên Âu 2 nấc (12:30 / 13:30 & 14:30 / 15:30 VN):** Cào nấc 1 trước giờ G để lên bài tác chiến, cào nấc 2 sau khi London mở cửa 30p để cập nhật Greeks.
  - **18:45 VN (Pre-US) & 19:45, 20:45, 21:45, 22:45, 23:45 VN:** Đón đầu trước giờ ra tin vĩ mô (CPI/NFP) và bao trọn mở cửa NYSE, chốt giá London Fix (00:00 VN).

---

## 📚 TÀI LIỆU KIẾN TRÚC & QUYẾT ĐỊNH KỸ THUẬT

- **Kiến trúc Hệ thống v2.0 (Toàn cảnh 6 tầng & Level State Engine):** [docs/architecture.md](docs/architecture.md)
- **Đặc tả Kỹ thuật Hệ thống (Tech Stack & Pipeline Spec):** [docs/spec.md](docs/spec.md)
- **Quyết định Kiến trúc Cloud-Native (ADR-001):** [docs/decisions/ADR-001-cloud-native-tactical-terminal.md](docs/decisions/ADR-001-cloud-native-tactical-terminal.md)
- **Quyết định Rollover Tự động & Chế độ Scalping ATM ± 5 Strikes (ADR-002):** [docs/decisions/ADR-002-cme-front-month-auto-rollover-and-scalping-view.md](docs/decisions/ADR-002-cme-front-month-auto-rollover-and-scalping-view.md)
- **Quyết định Level State Engine & Quét Túi Chân Không Air Pocket (ADR-003):** [docs/decisions/ADR-003-level-state-engine-and-air-pocket-detection.md](docs/decisions/ADR-003-level-state-engine-and-air-pocket-detection.md)
- **Công thức Toán học Định lượng (Black-76, GEX, Vanna, Charm, Expected Move):** [docs/tailieudacta/CÔNG THỨC CẦN TÍNH TOÁN.md](docs/tailieudacta/CÔNG%20THỨC%20CẦN%20TÍNH%20TOÁN.md)

---

## 🛠️ CẤU TRÚC KHO LƯU TRỮ

```
Neiro-Quant/
├── .github/workflows/
│   └── daily_options_sync.yml   # Workflow cào Barchart, tính toán Greeks & xuất bản GitHub Pages
├── docs/
│   ├── architecture.md          # Tài liệu kiến trúc hệ thống chính (v2.0)
│   ├── spec.md                  # Bản đặc tả kỹ thuật chi tiết
│   ├── decisions/               # Architecture Decision Records (ADRs)
│   └── tailieudacta/            # Công thức toán học và tài liệu đặc tả vi mô
├── src/
│   ├── collector/               # Playwright headless scraper & API interceptor
│   ├── quant_engine/            # Lõi Black-76, IV solver, GEX, Vanna, Charm, Expected Move
│   └── hud/                     # Plotly Dark Mode tactical dashboard generator
├── data/
│   └── options_prices_GCZ26.csv # Dữ liệu CME Options Chain tự động cập nhật
└── notebooks/                   # File nghiên cứu cũ (đã chuyển giao sang Cloud Pipeline)
```

---

## 🧹 QUY TẮC BẢO TỒN DUNG LƯỢNG (ZERO-WASTE MANDATE)

Dự án tuân thủ nghiêm ngặt chuẩn dung lượng siêu nhẹ:
- Toàn bộ kho lưu trữ luôn duy trì **< 15MB** (hiện tại: ~8.4MB).
- Mọi dữ liệu tạm, scratch scripts, cache đều được tự động dọn dẹp sạch sẽ sau mỗi lần thực thi.
- Không lưu trữ tệp tin nhị phân nặng trên máy cục bộ của người dùng.