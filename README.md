# 🪙 Neiro-Quant — Market Microstructure & GEX Terminal

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/DaniNguyen2509/Neiro-Quant/blob/main/notebooks/Neiro_Quant.ipynb)
[![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

Hệ thống Định lượng Vị thế Nhà tạo lập (Dealer Positioning), Gamma Exposure (GEX), Delta Exposure (DEX) & Tích hợp Trí tuệ Nhân tạo DeepSeek trước 3 phiên giao dịch (Á • Âu • Mỹ).

---

## 🚀 TÁC CHIẾN NHANH TRÊN GOOGLE COLAB (1-CLICK RUN)

Chỉ cần bấm nút **[Open in Colab]** ở trên, anh có thể chạy toàn bộ hệ thống ngay trên điện thoại, iPad hoặc máy tính:
1. **Nạp số liệu:** Dùng sẵn dữ liệu mẫu trong data/sample_options_chain.csv hoặc tải file CSV Options Chain từ Barchart lên.
2. **Quy đổi Spot:** Nhập giá Spot XAUUSD trên sàn anh trade -> Hệ thống tự động trừ Basis quy đổi tất cả các mốc cản sang giá Spot.
3. **Xem biểu đồ ATAS:** Trực quan hóa GEX Profile, Call Wall, Put Wall, ATM Pivot, Dải $\pm 1\sigma$ và các vùng Chân không thanh khoản (Air Pockets).
4. **Trợ lý AI DeepSeek:** Tự động phân tích cấu trúc vi mô và xuất Kế hoạch vào lệnh, SL, TP sắc bén trước mỗi phiên.

---

## 📚 TÀI LIỆU ĐẶC TẢ & HỆ THỐNG CÔNG THỨC

- **Kiến trúc hệ thống 6 tầng & State Machine:** [docs/tailieudacta/KIEN_TRUC_DU_AN.md](docs/tailieudacta/KIEN_TRUC_DU_AN.md)
- **Đặc tả toàn bộ công thức toán học (Black-76, Greeks, GEX):** [docs/tailieudacta/CÔNG THỨC CẦN TÍNH TOÁN.md](docs/tailieudacta/CÔNG%20THỨC%20CẦN%20TÍNH%20TOÁN.md)

---

## 🛠️ CẤU TRÚC KHO LƯU TRỮ

`
Neiro-Quant/
├── notebooks/
│   └── Neiro_Quant.ipynb       # Google Colab Notebook chính
├── data/
│   └── sample_options_chain.csv # Dữ liệu mẫu chuẩn CME Gold Options
├── docs/
│   └── tailieudacta/            # Toàn bộ tài liệu đặc tả & công thức toán
├── src/
│   ├── quant_engine/            # Lõi toán định lượng
│   ├── collector/               # Thu thập dữ liệu Barchart & CME
│   └── mt5_bridge/              # Kết nối MT5 Spot & Futures
└── config/
    └── settings.toml            # Cấu hình hệ thống
`