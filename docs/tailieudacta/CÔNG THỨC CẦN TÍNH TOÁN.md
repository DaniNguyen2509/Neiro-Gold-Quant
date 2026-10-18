# Neiro-Quant — ĐẶC TẢ BỘ CÔNG THỨC TOÁN HỌC ĐỊNH LƯỢNG (MATH ENGINE SPEC)

> **Phiên bản:** v2.0 — 18/10/2026 (Nâng cấp toàn diện tích hợp Black-76, Greeks, GEX/DEX, VEX, CHEX, Microstructure)  
> **Tài liệu liên kết:** [KIEN_TRUC_DU_AN.md](KIEN_TRUC_DU_AN.md)

---

## TẦNG 0: MÔ HÌNH ĐỊNH GIÁ & GREEKS CỐT LÕI (BLACK-76 ENGINE)

> [!IMPORTANT]
> Vì đối tượng là Options trên Hợp đồng Tương lai (Gold Futures CME), hệ thống **BẮT BUỘC dùng mô hình Black-76** (thay vì Black-Scholes gốc), bởi Futures price đã phản ánh chi phí lưu kho và lãi suất vốn (cost of carry).

### 1. Định giá Options (Black-76 Formula)
$$\begin{aligned}
V_{call} &= e^{-rT} \left[ F \cdot N(d_1) - K \cdot N(d_2) \right] \\
V_{put}  &= e^{-rT} \left[ K \cdot N(-d_2) - F \cdot N(-d_1) \right]
\end{aligned}$$

Trong đó:
$$\begin{aligned}
d_1 &= \frac{\ln(F/K) + \frac{\sigma^2}{2} T}{\sigma \sqrt{T}} \\
d_2 &= d_1 - \sigma \sqrt{T}
\end{aligned}$$

- $F$: Giá Hợp đồng Tương lai hiện tại (Futures Price, VD: GCZ26).
- $K$: Giá thực hiện quyền chọn (Strike Price).
- $T$: Thời gian đến đáo hạn (năm) = $\frac{\text{Days to Expiration}}{365}$ (hoặc tính theo số phút còn lại cho 0DTE: $\frac{\text{Minutes}}{365 \times 1440}$).
- $r$: Lãi suất phi rủi ro (Risk-Free Rate, lấy từ US Treasury 3-Month).
- $\sigma$: Biến động ngầm định (Implied Volatility - IV).
- $N(\cdot)$: Hàm phân phối tích lũy chuẩn tắc (Standard Normal CDF).
- $n(\cdot)$: Hàm mật độ xác suất chuẩn tắc (Standard Normal PDF) = $\frac{1}{\sqrt{2\pi}} e^{-x^2/2}$.

---

### 2. Bộ Greeks Đạo hàm Bậc 1 & Bậc 2 (Black-76 Greeks)

| Greek | Ký hiệu | Công thức Black-76 | Ý nghĩa thực chiến |
|---|---|---|---|
| **Delta Call** | $\Delta_{call}$ | $e^{-rT} \cdot N(d_1)$ | Số lượng Hợp đồng Futures Dealer cần phòng hộ khi Long Call |
| **Delta Put** | $\Delta_{put}$ | $-e^{-rT} \cdot N(-d_1)$ | Số lượng Hợp đồng Futures Dealer cần phòng hộ khi Long Put |
| **Gamma** | $\Gamma$ | $\frac{e^{-rT} \cdot n(d_1)}{F \cdot \sigma \sqrt{T}}$ | Gia tốc thay đổi của Delta khi giá Futures di chuyển $1 (Dùng tính GEX) |
| **Theta Call** | $\Theta_{call}$ | $-\frac{F e^{-rT} n(d_1) \sigma}{2\sqrt{T}} - r F e^{-rT} N(d_1) + r K e^{-rT} N(d_2)$ | Tốc độ hao mòn giá trị thời gian của Call mỗi ngày |
| **Vega** | $\nu$ | $F \cdot e^{-rT} \cdot n(d_1) \cdot \sqrt{T}$ | Độ nhạy của giá option khi IV thay đổi 1% |
| **Vanna** | $\frac{\partial \Delta}{\partial \sigma}$ | $-e^{-rT} \cdot n(d_1) \cdot \frac{d_2}{\sigma}$ | Độ nhạy của Delta khi IV thay đổi (Dùng tính VEX) |
| **Charm** | $-\frac{\partial \Delta}{\partial T}$ | $e^{-rT} \left[ n(d_1) \left( \frac{r}{\sigma \sqrt{T}} - \frac{d_2}{2T} \right) - r N(d_1) \right]$ | Tốc độ suy biến của Delta theo thời gian (Dùng tính CHEX) |

---

### 3. Thuật toán Giải ngược Implied Volatility (IV Solver)
Khi trang web không cung cấp IV (đặc biệt vào ngày đáo hạn 0DTE Barchart trả $IV = 0.00\%$), hệ thống tự động tìm $\sigma$ từ giá Mid thị trường bằng thuật toán Newton-Raphson kết hợp Brent's Method:

$$\sigma_{n+1} = \sigma_n - \frac{V_{Black76}(F, K, T, r, \sigma_n) - P_{mid}}{\nu(\sigma_n)}$$
*Dừng lặp khi:* $|V_{Black76} - P_{mid}| < 10^{-6}$.

---

## TẦNG 1: THỐNG KÊ BIÊN ĐỘ & TRỤC CÂN BẰNG (SYNTHETIC PIVOT & BANDS)

### 1. Giá Trung bình Thực tế (Mid-Price)
Triệt tiêu độ trễ của giá khớp gần nhất (Last Price) bằng trung bình cộng lệnh chờ tốt nhất của Market Maker:
$$Mid = \frac{Bid + Ask}{2}$$

### 2. Trục Cân bằng Ngầm định (Implied ATM Pivot - Synthetic Futures)
Dựa trên nguyên lý Ngang giá Quyền chọn (Put-Call Parity):
- **Bước 1:** Quét bảng tìm Strike $K_{ATM}$ có độ lệch $|Call_{mid} - Put_{mid}|$ nhỏ nhất.
- **Bước 2:** Tính giá trị trục cân bằng thực tế:
$$S_{Implied} = K_{ATM} + e^{rT} \cdot [Call_{mid}(ATM) - Put_{mid}(ATM)]$$

### 3. Biên độ Dao động Kỳ vọng (ATM Straddle / Implied Move)
Tổng chi phí mua bảo hiểm hai đầu tại trục ATM:
$$Straddle = Call_{mid}(ATM) + Put_{mid}(ATM)$$

### 4. Dải Băng Phòng ngự (1-Sigma Bands)
$$Upper\ Band\ (+1.0\sigma) = S_{Implied} + Straddle$$
$$Lower\ Band\ (-1.0\sigma) = S_{Implied} - Straddle$$
- **Hệ số điều chỉnh 0DTE (Conservative):**
$$Upper\ Band\ (0.85\sigma) = S_{Implied} + 0.85 \cdot Straddle$$
$$Lower\ Band\ (0.85\sigma) = S_{Implied} - 0.85 \cdot Straddle$$

---

## TẦNG 2: VỊ THẾ NHÀ TẠO LẬP (DEALER POSITIONING & GEX PROFILE)

### 1. Delta Exposure (DEX)
Tổng giá trị đô la Futures mà Dealer phải tái cân bằng để giữ vị thế Delta-neutral:
$$DEX_k = \Delta_k \cdot OI_k \cdot \text{Multiplier} \cdot F$$
*(Multiplier = 100 troy oz cho hợp đồng Vàng CME)*

### 2. Gamma Exposure (GEX — Đô la di chuyển trên mỗi 1% biến động giá)
$$GEX_{call, k} = + \left( \Gamma_{call, k} \cdot OI_{call, k} \cdot \text{Multiplier} \cdot F^2 \cdot 0.01 \right)$$
$$GEX_{put, k}  = - \left( \Gamma_{put, k} \cdot OI_{put, k} \cdot \text{Multiplier} \cdot F^2 \cdot 0.01 \right)$$

**Net GEX tại mỗi Strike:**
$$Net\ GEX_k = GEX_{call, k} + GEX_{put, k}$$

**Net GEX toàn thị trường:**
$$Total\ Net\ GEX = \sum_k Net\ GEX_k$$

**Ý nghĩa Chế độ (Regime):**
- **$Total\ Net\ GEX > 0$ (Positive Gamma):** Market Maker giao dịch ngược chiều giá (Bán khi tăng, Mua khi giảm) $\rightarrow$ **Hấp thụ biến động, nén biên độ (Mean-reverting)**.
- **$Total\ Net\ GEX < 0$ (Negative Gamma):** Market Maker giao dịch thuận chiều giá (Mua khi tăng, Bán khi giảm) $\rightarrow$ **Khuếch đại đà rơi/tăng, dễ bùng nổ trượt giá (Trending/Volatile)**.

### 3. Điểm Đảo Chiều Gamma (Gamma Flip Point)
Mức giá $F^*$ nơi $Total\ Net\ GEX(F^*) = 0$. Vượt qua điểm này, thị trường đổi trạng thái từ nén giá sang phóng dao.

### 4. VEX (Vanna Exposure) & CHEX (Charm Exposure)
$$VEX_k = \text{Vanna}_k \cdot OI_k \cdot \text{Multiplier}$$
$$CHEX_k = \text{Charm}_k \cdot OI_k \cdot \text{Multiplier}$$
Dự báo dòng tiền tái phòng hộ khi IV tăng vọt hoặc vào thời khắc cuối phiên giao dịch.

---

## TẦNG 3: CẤU TRÚC KHÔNG GIAN (WALLS, AIR POCKETS & SQUEEZE TRIGGERS)

### 1. Bức tường Quyền chọn Lớn (Major Walls)
$$Call\ Wall = \text{Strike có } \max(OI_{Call})$$
$$Put\ Wall  = \text{Strike có } \max(OI_{Put})$$
$$Absolute\ Gamma\ Strike = \text{Strike có } \max(|Net\ GEX_k|)$$

### 2. Điểm Kích hoạt Squeeze / Hedging Runaway (Gamma Triggers)
$$Trigger_{Up}   = Call\ Wall\ Strike + Call_{mid}(CallWall)$$
$$Trigger_{Down} = Put\ Wall\ Strike - Put_{mid}(PutWall)$$
Khi nến M5 đóng cửa vượt qua các mốc này, Dealer buộc phải quét lệnh khẩn cấp để stop loss.

### 3. Vùng Chân không Thanh khoản (OI Air Pockets)
Tìm chuỗi Strike liên tiếp $[K_1 \rightarrow K_2]$ thỏa mãn:
$$OI_k < 0.35 \times \text{Mean}(OI_{all})$$
Đây là các vùng rỗng thanh khoản cản trở. Khi giá rơi vào đây, tốc độ trượt giá sẽ đạt cực đại do thiếu lực đỡ.

---

## TẦNG 4: ĐỒNG BỘ THỜI GIAN THỰC (AUTO-BASIS SYNC SPOT ↔ FUTURES)

### 1. Độ lệch Giá (Basis Spread)
$$Basis(t) = \text{Median}_{60s}\left( Price_{Futures}(t) - Price_{Spot}(t) \right)$$

### 2. Quy đổi Tọa độ Sang Biểu đồ MT5 Spot
Mọi mức tính toán từ Options CME được chiếu thẳng lên biểu đồ nến MT5 của Broker:
$$Level_{Spot} = Level_{Futures} - Basis$$

---

## TẦNG 5: ĐẶC TẢ TÍN HIỆU VI MÔ (ENTRY, SL, TP MATRIX)

| Tình huống | Điều kiện Định lượng | Lệnh thực thi | Điểm Stop Loss (SL) | Điểm Take Profit (TP) |
|---|---|---|---|---|
| **🛡️ Trụ vững (Absorption / Reversal)** | Test Wall + $Net\ GEX > 0$ + Delta phân kỳ kiệt sức | **Fade Reversal** (Buy khi test Put Wall / Sell khi test Call Wall) | Mép ngoài của Wall $\pm 1.5$ đến $2.5$ giá | TP1: $S_{Implied}$ (Pivot) <br> TP2: Wall đối diện |
| **⚡ Bị đâm thủng (Vacuum Cascade)** | Vỡ Wall $> 1.5$ giá + $Net\ GEX < 0$ + Phía sau là Air Pocket | **Breakout Runner** (Sell Stop khi thủng Put Wall / Buy Stop khi phá Call Wall) | Ngược lại trên/dưới Wall vừa vỡ $1.0 - 1.5$ giá | Biên trên của Cụm OI dày tiếp theo sau Air Pocket |