# ADR-015: Kiến Trúc Định Lượng Quyền Chọn Vàng, Mô Hình Cost of Carry, Call Skew & Terminal Dual-View

> **Trạng thái:** ACCEPTED  
> **Ngày quyết định:** 01/11/2026  
> **Tài sản mục tiêu:** COMEX Gold Futures (`GC` / `MGC`), Spot `XAUUSD` / `GOLD` (London OTC) & SPDR Gold Shares (`GLD`).  
> **Tài liệu tham chiếu:** [`docs/spec.md`](../spec.md), [`docs/architecture.md`](../architecture.md), [`config/settings.toml`](../../config/settings.toml).

---

## 1. BỐI CẢNH (CONTEXT)

Sau khi chuẩn hóa và hoàn thiện hệ thống định lượng `Neiro-NQ-Quant` (E-mini Nasdaq-100 Futures), dự án mở rộng sang thị trường Vàng quốc tế (**`Neiro-Gold-Quant`**).  
Thị trường Vàng sở hữu những đặc thù vi cấu trúc và cơ chế định giá phái sinh hoàn toàn khác biệt so với chỉ số chứng khoán:
1. **Hệ số nhân lớn:** 1 hợp đồng tương lai vàng tiêu chuẩn COMEX `GC` đại diện cho 100 troy ounces vàng (Multiplier = $100.0/oz). Biến động $1.00 USD giá vàng tương đương $100.00 PnL/hợp đồng (đối với Micro `MGC` là 10 oz, Multiplier = $10.0/oz).
2. **Mô hình Cost of Carry:** Không có cổ tức ($d = 0$), nhưng vàng chịu chi phí lưu kho, kiểm định và bảo hiểm vật chất tại kho COMEX ($u \approx 0.2\%$/năm), đồng thời sinh lợi suất cho thuê vàng liên ngân hàng (Gold Lease Rate $y \approx 1.5\%$/năm).
3. **Độ dốc biến động hàm ý (IV Skew):** Khác với chứng khoán chịu Put Skew do mua bảo hiểm sập giá, Vàng chịu chi phối bởi **Call Skew** (nhu cầu mua Call OTM phòng hộ lạm phát, suy thoái kinh tế và rủi ro địa chính trị). Do đó, phía trần kháng cự Call Wall tiềm ẩn các đợt bùng nổ **Gamma Squeeze** cực mạnh khi giá vượt qua $Trigger_{Up} = CallWall + Call_{mid}$.
4. **Yêu cầu tác chiến đa chế độ Dual-View:** Trader cần quan sát đồng thời cả hai không gian:
   - *Tab 1 (NEIRO Orderflow Footprint):* Canvas HTML5 60 FPS vẽ sổ lệnh thang giá dọc DOM, Delta Footprint cụm nến 1M/5M, Tick tape.
   - *Tab 2 (3-Panel Quant Ladder & Playbook):* Plotly Dark HUD định vị thành trì Dealer, GEX/VEX/CHEX, Ma trận 6 Kịch bản Realtime và Bảng chiến lược Scalping/Swing.

---

## 2. QUYẾT ĐỊNH KIẾN TRÚC (DECISIONS)

### 2.1. Chuẩn hóa Bộ Tham Số và Tỷ Lệ Ánh Xạ Proxy (`config/settings.toml`)
- **Tài sản HĐTL:** `GC` (Standard, Multiplier = 100.0), `MGC` (Micro, Multiplier = 10.0).
- **Proxy Quyền chọn thanh khoản:** ETF `GLD` (SPDR Gold Shares).
- **Tỷ lệ ánh xạ Basis Ratio:** $\text{Basis Ratio} = \text{Spot}_{GC} / \text{Spot}_{GLD} \approx 10.8$ (khi Vàng 2,700 thì GLD $\approx 250$).
- **Chỉ số IV:** `^GVZ` (CBOE Gold Volatility Index).
- **Chu kỳ đáo hạn chính:** 5 tháng chẵn G (T2), J (T4), M (T6), Q (T8), Z (T12).

### 2.2. Triển khai Mô hình Cost of Carry và Cơ chế EFP
Xây dựng hàm tính toán giá tương lai lý thuyết và độ lệch EFP trong `src/quant_engine/basis.py`:
$$F_{0, \text{lý thuyết}} = S_0 \times e^{(r + u - y)T}$$
$$\Delta F = F_{0, \text{thực tế}} - F_{0, \text{lý thuyết}}$$
- Khi $\Delta F > +3.0$ USD: Trạng thái `PREMIUM &bull; MUA ĐUỔI COMEX`. Kích hoạt nghiệp vụ EFP: Bullion Banks bán khống Futures COMEX và mua gom Spot London (XAUUSD), kéo giá Spot tăng đuổi theo.
- Khi $\Delta F < -3.0$ USD: Trạng thái `DISCOUNT &bull; BÁN XẢ COMEX`. Áp lực xả hàng phòng hộ của các mỏ vàng.
- Khi $|\Delta F| \le 3.0$ USD: Trạng thái `FAIR VALUE &bull; CÂN BẰNG`.

### 2.3. Bộ Thu Thập Dữ Liệu Proxy (`src/collector/gold_collector.py`)
- Cung cấp class `GoldCollector` quét trực tiếp chuỗi Options `GLD` và giá `GC=F` qua `yfinance`, quy đổi strike GLD sang GC Futures và tính analytical Black-76 Greeks với Multiplier 100.0.
- Tích hợp bộ dữ liệu chuẩn `generate_benchmark_gold_chain(spot=2700.0)` mô phỏng chính xác đặc thù Call Skew và các bức tường thành trì, đảm bảo hệ thống không bao giờ crash khi mất mạng.

### 2.4. Kiến Trúc Terminal Tác Chiến Đa Chế Độ Dual-View (`src/hud/neiro_terminal.py`)
- Tách biệt component NEIRO sang module chuyên biệt `src/hud/neiro_terminal.py` để giữ mã nguồn module hóa, tránh phình to file.
- Giao diện tích hợp thanh Topbar điều hướng chuyển tab tức thì không giật lag:
  - Tab 1: NEIRO Orderflow Footprint (HTML5 Canvas 60 FPS, TradingView Lightweight Charts 4.2, Brownian-bridge 1m/5m candles, Level Lines Call/Put Wall, Gamma Squeeze Up/Down, Zero Gamma Flip).
  - Tab 2: 3-Panel Quant Ladder & Playbook (Plotly Dark HUD, Nụ cười biến động Malz SVI, Ma trận 6 Kịch bản, Bảng Scalping/Swing, Bảng Microstructure Matrix).
- Bộ tính toán Black-76 phía trình duyệt (Pure JS) cập nhật động tick-by-tick.

### 2.5. Lưới Cron Đa Tầng Pre-Session Radar & Tiêu Chuẩn Zero-Waste
- Lưới Cron GitHub Actions 3 khối phục vụ 3 phiên Á, Âu, Mỹ.
- Bổ sung `yfinance` vào `requirements.txt` và workflow CI/CD.
- Duy trì dung lượng toàn repo dưới 15MB (thực tế ~10.6MB), không xả rác.

---

## 3. KẾT QUẢ ĐẠT ĐƯỢC (CONSEQUENCES & VERIFICATION)

1. **Bộ kiểm thử toàn diện:** Toàn bộ **133 Unit Tests** (bao gồm 6 tests `test_gold_collector.py`, 2 tests Cost of Carry `test_basis.py`, 1 test `test_neiro_terminal.py`, 13 tests `test_html_dashboard.py`) vượt qua 100%.
2. **Xuất bản Terminal thành công:** File `exports/index.html` sinh ra trọn vẹn (378 KB) chứa đầy đủ 10 thành phần bất biến của cả 2 Tab NEIRO Footprint và Plotly Quant Ladder.
3. **Hiệu năng & Tài nguyên:** Dung lượng repo duy trì ở mức 10.64 MB, đạt chuẩn Zero-Waste Mandate (< 15MB).

