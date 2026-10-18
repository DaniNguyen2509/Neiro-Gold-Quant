# BẢN THẨM ĐỊNH ĐỘC LẬP — NEIRO-QUANT MATH ENGINE v2.0

**Người thẩm định:** Senior Quantitative Finance Researcher & Options Market Making Auditor  
**Đối tượng:** Math Engine Spec v2.0 (Black-76, Greeks, GEX/DEX/VEX/CHEX, Pivot/Bands, Microstructure)  
**Phạm vi ứng dụng mục tiêu:** CME Gold Options (GC/OG) & XAUUSD Spot  
**Ngày thẩm định:** 18/10/2026

---

## PHẦN 1 — ĐÁNH GIÁ TÍNH CHÍNH XÁC TỪNG CÔNG THỨC

### 1.1. Black-76 Formula — ✅ CHÍNH XÁC

$$\begin{aligned}
V_{call} &= e^{-rT}[F N(d_1) - K N(d_2)] \\
V_{put}  &= e^{-rT}[K N(-d_2) - F N(-d_1)] \\
d_1 &= \frac{\ln(F/K) + \tfrac{\sigma^2}{2}T}{\sigma\sqrt{T}}, \quad d_2 = d_1 - \sigma\sqrt{T}
\end{aligned}$$

- **Đúng chuẩn Black (1976).** Việc dùng $F$ thay vì $S$ và bỏ dividend yield là chính xác cho options trên futures.
- **Lựa chọn mô hình đúng:** Với GC futures, cost-of-carry đã nằm trong $F$; dùng Black-Scholes gốc sẽ tạo sai lệch có hệ thống ở các tenor xa (đặc biệt khi $r$ cao như 2024–2026).
- **Lưu ý nhỏ:** Công thức giả định $r$ và $\sigma$ hằng số, không có skew — chấp nhận được cho mục đích GEX/positioning, **không** dùng để định giá exotic.

**Điểm:** 9.5/10

---

### 1.2. Greeks Bậc 1 & Bậc 2 — ⚠️ CÓ LỖI QUAN TRỌNG

| Greek | Đánh giá | Ghi chú |
|---|---|---|
| **Delta Call** $e^{-rT}N(d_1)$ | ✅ Đúng | |
| **Delta Put** $-e^{-rT}N(-d_1)$ | ✅ Đúng | |
| **Gamma** $\dfrac{e^{-rT}n(d_1)}{F\sigma\sqrt{T}}$ | ✅ Đúng | |
| **Vega** $F e^{-rT} n(d_1)\sqrt{T}$ | ✅ Đúng (per 1.00 vol) | Cần quy ước rõ "per 1% vol" = chia 100 |
| **Vanna** $-e^{-rT}n(d_1)\dfrac{d_2}{\sigma}$ | ✅ Đúng | |
| **Theta Call** | ❌ **SAI DẤU & SAI CẤU TRÚC** | Xem 1.2.1 |
| **Charm** | ⚠️ **SAI DẤU** | Xem 1.2.2 |

#### 1.2.1. Theta Call — LỖI NGHIÊM TRỌNG

Công thức trong spec:
$$\Theta_{call} = -\frac{F n(d_1)\sigma}{2\sqrt{T}}e^{-rT} - rKe^{-rT}N(d_2) + rFe^{-rT}N(d_1)$$

**Vấn đề:**
1. **Dấu của số hạng thứ 3 sai.** Với Black-76, Theta (đạo hàm theo $t$, tức $-\partial V/\partial T$) của call là:
$$\Theta_{call} = -\frac{F e^{-rT} n(d_1)\sigma}{2\sqrt{T}} + rKe^{-rT}N(d_2) - rFe^{-rT}N(d_1)$$
Số hạng thứ 2 và thứ 3 trong spec **bị đảo dấu** so với chuẩn. Hệ quả: Theta bị **over-estimate** (bớt âm hơn thực tế) ở vùng ITM, và **sai hoàn toàn** khi $r$ lớn (như hiện tại $r \approx 4\text{–}5\%$).
2. **Thiếu quy ước "per day" vs "per year".** Spec không nêu rõ đơn vị — nếu dùng cho 0DTE mà không chia 365, sai số khổng lồ.

**Điểm:** 3/10 cho Theta.

#### 1.2.2. Charm — SAI DẤU

Công thức spec:
$$\text{Charm} = e^{-rT}\left[n(d_1)\left(\frac{r}{\sigma\sqrt{T}} - \frac{d_2}{2T}\right) - rN(d_1)\right]$$

Charm chuẩn (Black-76, $\partial\Delta/\partial T$ với dấu "time decay" thông thường) là:
$$\text{Charm}_{call} = -e^{-rT}\left[n(d_1)\left(\frac{r}{\sigma\sqrt{T}} - \frac{d_2}{2T}\right) - rN(d_1)\right]$$

Spec **thiếu dấu âm ngoài cùng** (hoặc định nghĩa $\partial\Delta/\partial T$ thay vì $-\partial\Delta/\partial T$ — nhưng bảng ghi rõ "$-\partial\Delta/\partial T$" nên công thức phải âm). Hệ quả: **CHEX bị đảo dấu toàn bộ** → dự báo dòng tiền re-hedge cuối phiên bị ngược chiều.

**Điểm:** 4/10 cho Charm.

---

### 1.3. IV Solver (Newton-Raphson + Brent) — ✅ ĐÚNG VỀ KIẾN TRÚC

$$\sigma_{n+1} = \sigma_n - \frac{V_{B76}(\sigma_n) - P_{mid}}{\nu(\sigma_n)}$$

- **Đúng phương pháp.** Newton-Raphson với Vega làm đạo hàm là chuẩn công nghiệp.
- **Fallback Brent hợp lý** cho deep OTM/ITM nơi Vega → 0.
- **Thiếu:** (a) điều kiện khởi tạo $\sigma_0$ (nên dùng IV của strike lân cận hoặc ATM IV); (b) giới hạn $\sigma \in [0.01, 5.0]$; (c) xử lý arbitrage-free check (nếu $P_{mid}$ vi phạm no-arbitrage bound → reject, không solve).
- **0DTE:** Khi $T \to 0$, Vega $\to 0$ rất nhanh → Newton dễ diverge. **Bắt buộc** phải có Brent fallback + clamp. Spec có Brent nhưng không nêu rõ trigger condition.

**Điểm:** 8/10

---

### 1.4. Put-Call Parity cho Futures — ⚠️ ĐÚNG NHƯNG THIẾU

Công thức dùng:
$$S_{Implied} = K_{ATM} + Call_{mid} - Put_{mid}$$

Đây là **parity đúng cho futures** ($C - P = e^{-rT}(F - K)$, nên $F = K + e^{rT}(C-P)$). Spec **bỏ qua $e^{rT}$** — với $r=5\%$, $T=0.25$ (3 tháng), sai số $\approx 1.25\%$ trên chênh lệch $C-P$. Với Vàng $F \approx 4000$, sai số có thể **$5–50$ USD** tùy độ rộng $C-P$.

**Khuyến nghị:** Dùng $F_{implied} = K + e^{rT}(C_{mid} - P_{mid})$ hoặc ít nhất ghi rõ đây là xấp xỉ $rT \approx 0$.

**Điểm:** 6.5/10

---

### 1.5. ATM Straddle & 1σ Bands — ⚠️ XẤP XỈ THÔ

$$Upper = S_{Implied} + Straddle, \quad Lower = S_{Implied} - Straddle$$

- **Đây là approximation**, không phải 1σ chính xác. 1σ move chuẩn là $F \cdot \sigma\sqrt{T}$ (hoặc $S \cdot \sigma\sqrt{T}$). Straddle $\approx 0.8 \cdot F\sigma\sqrt{T}$ (với ATM, $2 \cdot V_{ATM} \approx 0.8 F\sigma\sqrt{T}$).
- **Hệ quả:** Band trong spec **hẹp hơn ~20%** so với 1σ thực. Với 0DTE, sai số này khiến trader đánh giá thấp rủi ro breakout.
- **Hệ số 0.85 cho 0DTE:** Hợp lý về mặt "conservative" nhưng **không có cơ sở toán học** — nên thay bằng band dựa trên $\sigma\sqrt{T}$ trực tiếp từ IV solver.

**Điểm:** 6/10

---

### 1.6. GEX — ⚠️ CÔNG THỨC ĐÚNG NHƯNG QUY ƯỚC DẤU CẦN KIỂM CHỨNG

$$GEX_{call,k} = +\Gamma_k \cdot OI_k \cdot M \cdot F^2 \cdot 0.01$$
$$GEX_{put,k}  = -\Gamma_k \cdot OI_k \cdot M \cdot F^2 \cdot 0.01$$

- **Đơn vị "dollar per 1% move" đúng** ($\Gamma \cdot F^2 \cdot 0.01$ là chuẩn SpotGamma-style).
- **Quy ước dấu:** Giả định Dealer **long call, short put** (customer long call, long put). Đây là **giả định phổ biến nhưng KHÔNG phải lúc nào cũng đúng** — đặc biệt với Vàng, nơi:
  - Central bank / miner hedging tạo **short call** tự nhiên (producer hedging).
  - Retail XAUUSD CFD flow thường **long call** thuần túy.
- **Thiếu:** (a) hệ số $\gamma$ của Dealer position (thường giả định 100% nhưng thực tế có thể 60–80%); (b) phân biệt **OI vs Volume** (OI là snapshot, không phản ánh intraday flow); (c) xử lý **0DTE** — OI 0DTE thường rất nhỏ buổi sáng, tăng vọt cuối phiên → GEX 0DTE **không ổn định** và spec không có cơ chế weighting.

**Điểm:** 7/10

---

### 1.7. DEX — ✅ ĐÚNG

$$DEX_k = \Delta_k \cdot OI_k \cdot M \cdot F$$

Đúng đơn vị (dollar notional). Lưu ý: nên dùng **$\Delta \cdot OI \cdot M \cdot F$** với $\Delta$ đã bao gồm $e^{-rT}$ — spec dùng $\Delta$ từ bảng Greeks (đã có $e^{-rT}$) → OK.

**Điểm:** 9/10

---

### 1.8. VEX / CHEX — ⚠️ KẾ THỪA LỖI TỪ VANNA/CHARM

$$VEX_k = \text{Vanna}_k \cdot OI_k \cdot M, \quad CHEX_k = \text{Charm}_k \cdot OI_k \cdot M$$

- **VEX:** OK vì Vanna đúng. Nhưng **thiếu $F$** — Vanna exposure nên nhân thêm $F$ để ra dollar-per-1%-vol (tương tự GEX logic). Hiện tại đơn vị là "delta per 1% vol × OI" — không phải dollar.
- **CHEX:** Kế thừa **lỗi dấu Charm** → toàn bộ CHEX đảo chiều. **Nghiêm trọng** vì CHEX dùng để dự báo re-hedge cuối phiên.

**Điểm:** 5/10

---

### 1.9. Walls / Triggers / Air Pockets — ✅ HỢP LÝ

- **Call/Put Wall** theo max OI: chuẩn.
- **Absolute Gamma Strike** theo max $|Net G