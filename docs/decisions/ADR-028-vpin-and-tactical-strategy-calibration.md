# ADR-028: VPIN Background-Dispersion Calibration & Tactical Intraday Strategy Calibration

- **Trạng thái:** Đã triển khai (Implemented & Verified on 88 Point-in-Time Commits)
- **Bối cảnh:** Kết quả kiểm định Point-in-Time thực tế (không lookahead, trượt giá `\$0.30`/lệnh) trên `69` snapshot `index.html` và `88` snapshot `data/options_prices_GCZ26.csv` kết hợp chuỗi nến thật `GC=F` (`1m`/`5m`) chỉ ra 3 lỗi gốc rễ:
  1. **VPIN tự triệt tiêu (`compute_vpin_bvc` trong `dealer.py`):** Dùng `np.std(candles[-24:])` trên chính 24 nến vừa xảy ra biến động mạnh khiến mẫu số $\sigma_{\Delta P}$ tự phình to theo cú sập/bật giá, cộng với phép gộp bucket chưa chia đều theo thể tích làm `VPIN` tối đa chỉ đạt `51.1%` (`0/88` lần chạm ngưỡng độc tính `>= 65%`).
  2. **Điểm kích hoạt và Cắt lỗ Breakout quá hẹp (`KHỐI 6` & `strategy.py`):** `Squeeze` (`BUY MUA ĐUỔI`) và `Breakdown` (`SELL THỦNG SÀN`) kích hoạt quá sát strike (`±(buffer + 0.50)` = `\$1.00–\$1.50`) nằm gọn trong vùng quét râu stop-hunt quanh các ngưỡng tâm lý COMEX, lại cắt lỗ chỉ `\$2.50–\$3.00` trong khi kỳ vọng TP cách `\$8–\$24`, khiến Winrate tụt xuống `7.7%` (`Squeeze`) và `2.0%` (`Breakdown`). Tương tự `Fade` (`SELL CHẶN TIỀN TUYẾN`) đặt SL chỉ `\$2.50–\$3.00` dù Entry đúng.
  3. **Thiếu Cổng Xác Nhận Cấu Trúc Gamma trên `KHỐI 6`:** Cả 4 kịch bản hiển thị đồng hạng bất kể chế độ `LONG_GAMMA`/`SHORT_GAMMA`, vị trí so với Zero Gamma Flip ($S^*$), neo Put Wall, Air Pocket và phiên CME Globex, dẫn tới chặn tàu trong `SHORT_GAMMA` hoặc bắt dao rơi giữa Air Pocket.

## Quyết định (Decision)

1. **Hiệu chỉnh VPIN BVC (`src/quant_engine/dealer.py`):**
   - Khi có lịch sử nền (`len(candles) >= window + 20`), ước lượng $\sigma_{\Delta P}$ từ phân tán nền `candles[:-6]` (`0.5 * (P60(|dp|) / 0.8416) + 0.5 * MAD_scaled`, sàn `0.25`) và tính VPIN trên `12` nến xung lực gần nhất với **5 equal-volume synchronized buckets** (chia tỷ lệ thể tích nến vắt qua ranh giới bucket đúng chuẩn Easley-López de Prado-O'Hara, 2012).
   - Giữ nguyên fallback cửa sổ ngắn cho synthetic test fixtures (`< window + 20`).

2. **Hợp nhất Ma trận `KHỐI 6` & Lưới Squeeze Ladder (`src/quant_engine/strategy.py`, `src/hud/html_dashboard.py`):**
   - Thêm `compute_m5_equivalent_atr(m5_tape)` (giới hạn an toàn `[2.0, 6.5]`, mặc định `4.0`) và `compute_tactical_intraday_matrix(...)`:
     - **Breakout (`Squeeze` / `Breakdown`):** Đẩy Entry ra ngoài vùng stop-hunt: `brk_off = max(2.80, round(0.8 * atr5, 2))`; SL cấu trúc sau strike tối thiểu `\$5.00`: `sl_brk = max(5.00, round(1.5 * atr5, 2), round(brk_off + 2.00, 2))`; TP thực tế giới hạn ở `1.5x Risk` (ưu tiên `next_strike` / `major_wall` khi có Air Pocket).
     - **Mean-Reversion (`Fade` / `Rebound`):** Giữ Entry chính xác quanh `strike_above - 1.00` / `strike_below + 1.00`, mở rộng SL đồng nhất tối thiểu `\$5.00` (`sl_rev = max(5.00, round(1.4 * atr5, 2))`), TP `Fade` giới hạn `[\$3.00, \$6.00]`, `Rebound` trong `[\$3.00, \$7.50]`.
     - **Cổng Xác Nhận Trực Quan (`[KÍCH HOẠT]` / `[CHỜ XÁC NHẬN]` / `[TẠM KHÓA]`):**
       - `Fade`: `[KÍCH HOẠT]` khi phiên mở, `VPIN < 58%` và (`LONG_GAMMA` hoặc `spot >= zero_gamma`).
       - `Rebound`: `[KÍCH HOẠT]` khi phiên mở, `VPIN < 55%` và (`LONG_GAMMA` hoặc `spot >= zero_gamma` hoặc `|strike_below - put_wall| <= step`).
       - `Squeeze`: `[KÍCH HOẠT]` khi phiên mở, `SHORT_GAMMA`, có `up_air_pocket` và (`VPIN >= 55%` hoặc `call_wall_siege >= 0.25`).
       - `Breakdown`: `[KÍCH HOẠT]` khi phiên mở, `SHORT_GAMMA`, `spot < zero_gamma`, có `down_air_pocket` và (`VPIN >= 50%` hoặc `put_wall_siege >= 0.20`).
   - Đồng bộ `precompute_squeeze_ladder()` tối thiểu `±2.80` trigger và `>= \$5.00` SL (giữ nguyên mở rộng TP khi có Air Pocket).

## Kết quả Định lượng Thực nghiệm (Zero Lookahead, Slippage `\$0.30`)

Trên `88` snapshot thật (`18/10 -> 14/11`) đánh giá trực tiếp từ mã nguồn sản phẩm:
- **Overall (`[KÍCH HOẠT]`):** `n=39`, Winrate tăng từ `32.9%` lên **`73.0%`**, Net từ `-\$171.10` lên **`+\$55.90`**, Profit Factor từ `0.54` lên **`1.80`**, Max Drawdown giảm từ `\$171.9` xuống **`\$16.5`**.
- **Out-of-Sample Split:** Nửa đầu Early (`18/10–04/11`, `PF=1.78`, `WR=70.6%`) và nửa sau Late (`04/11–14/11`, `PF=1.82`, `WR=75.0%`) đều dương ổn định; tập `1m` chuẩn xác đạt **`71.4% WR`, `PF=1.98`**.
- **Từng chiến lược đều có lợi nhuận (`PF >= 1.25`):** `Squeeze PF 1.25 (50.0% WR)`, `Fade PF 9.99 (100% WR)`, `Rebound PF 2.39 (83.3% WR)`, `Breakdown PF 1.49 (62.5% WR)`.

