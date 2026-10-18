# BÁO CÁO THẨM ĐỊNH LOGIC TOÁN HỌC ĐỊNH LƯỢNG (DEEPSEEK AUDIT REPORT)

# BÁO CÁO THẨM ĐỊNH TOÁN HỌC & VI CẤU TRÚC — NEIRO-QUANT v2.0

**Auditor:** Senior Quantitative Finance & Market Microstructure Auditor
**Đối tượng:** Math Engine Spec v2.0 + Strategy Logic (Tier 5)
**Ngày thẩm định:** 18/10/2026

---

## 1. ĐÁNH GIÁ TÍNH ĐÚNG ĐẮN TOÁN HỌC (Mathematical Correctness)

### 1.1. Black-76 Engine — ✅ CHUẨN XÁC

| Hạng mục | Đánh giá | Ghi chú |
|---|---|---|
| Công thức $V_{call}, V_{put}$ | ✅ Đúng chuẩn Black (1976) | Hệ số chiết khấu $e^{-rT}$ áp lên toàn bộ payoff — chính xác cho options trên futures |
| $d_1, d_2$ | ✅ Đúng | Không có $q$ (dividend yield) — đúng vì futures đã hấp thụ carry |
| Delta Call $= e^{-rT}N(d_1)$ | ✅ Đúng | **Lưu ý quan trọng:** đây là $\partial V/\partial F$, không phải $\partial V/\partial S$ — phù hợp cho hedging futures |
| Delta Put $= -e^{-rT}N(-d_1)$ | ✅ Đúng | |
| Gamma $= \frac{e^{-rT}n(d_1)}{F\sigma\sqrt{T}}$ | ✅ Đúng | |
| Vega $= F e^{-rT} n(d_1)\sqrt{T}$ | ✅ Đúng | Đơn vị: $/1.00 IV change — cần chia 100 nếu muốn $/1% IV |
| Theta | ✅ Đúng cấu trúc | Nhưng **có vấn đề dấu** — xem §3.1 |
| Vanna $= -e^{-rT}n(d_1)\frac{d_2}{\sigma}$ | ✅ Đúng | |
| Charm | ⚠️ **CẦN KIỂM TRA** | Xem §3.2 |

**Kết luận:** Tầng 0 đạt chuẩn textbook (Haug, *The Complete Guide to Option Pricing Formulas*). Không có sai lệch lý thuyết.

### 1.2. Put-Call Parity cho Futures — ⚠️ CÓ SAI SỐ HỆ THỐNG

**Công thức trong spec:**
$$S_{Implied} = K_{ATM} + e^{rT}[C_{mid} - P_{mid}]$$

**Công thức trong notebook (thực thi):**
$$S_{Implied} = K_{ATM} + C_{mid} - P_{mid}$$

**🔴 ĐÂY LÀ ĐIỂM SAI QUAN TRỌNG NHẤT.**

Put-Call Parity cho European options trên futures là:
$$C - P = e^{-rT}(F - K) \quad \Rightarrow \quad F = K + e^{rT}(C - P)$$

- **Spec đúng** (có $e^{rT}$).
- **Notebook SAI** — bỏ mất hệ số $e^{rT}$.

**Mức độ ảnh hưởng thực tế:**
- Với $r = 4.5\%$, $T = 30/365$: $e^{rT} \approx 1.0037$ → sai số ~0.37% × $(C-P)$.
- Nếu $|C-P| \approx 5$ USD (ATM lệch nhẹ) → sai số ~0.02 USD — **chấp nhận được**.
- Nhưng với **0DTE** ($T \to 0$): $e^{rT} \to 1$ → sai số không đáng kể.
- Với **LEAPS** ($T = 1$ năm): $e^{rT} \approx 1.046$ → sai số ~4.6% × $(C-P)$ — **có thể lệch 1-2 USD trên Vàng**.

**Khuyến nghị:** Sửa notebook thành `S_Implied = K_ATM + exp(r*T) * (C_mid - P_mid)`. Nếu $r$ không có sẵn, dùng $r=0$ chỉ khi $T < 7$ ngày.

### 1.3. Straddle ≈ 1-Sigma Expected Move — ⚠️ XẤP XỈ THÔ

**Công thức:** $Upper/Lower = S_{Implied} \pm Straddle$

**Đánh giá:** Đây là **xấp xỉ heuristic phổ biến** trên trading desk, KHÔNG phải công thức chính xác.

**Lý thuyết chuẩn:**
- Expected absolute move (E|ΔF|) cho GBM $\approx \sigma F \sqrt{2T/\pi} \approx 0.7979 \cdot \sigma F\sqrt{T}$
- ATM Straddle $\approx 0.7979 \cdot \sigma F\sqrt{T}$ (Brenner-Subrahmanyam)
- **1-Sigma move** = $\sigma F\sqrt{T}$ (độ lệch chuẩn, không phải kỳ vọng trị tuyệt đối)

**Do đó:** $Straddle \approx 0.8\sigma$, KHÔNG phải $1.0\sigma$.

**Hệ quả:**
- Dải "1-Sigma" trong spec thực chất là **~0.8σ** → hẹp hơn thực tế ~20%.
- Dải "0.85σ" thực chất là **~0.68σ** → rất hẹp, dễ bị vi phạm.

**Khuyến nghị:**
- Nếu muốn đúng 1σ: dùng $Band = S_{Implied} \pm \frac{Straddle}{0.7979} \approx S_{Implied} \pm 1.2533 \cdot Straddle$.
- Hoặc đổi nhãn thành "Expected Move (Brenner-Subrahmanyam)" thay vì "1-Sigma" để tránh hiểu nhầm.
- **Đây là lỗi ngữ nghĩa, không phải lỗi logic** — nhưng ảnh hưởng đến việc đặt TP/SL.

### 1.4. GEX Formula — ✅ CHUẨN CME GOLD

$$GEX = \Gamma \cdot OI \cdot 100 \cdot F^2 \cdot 0.01 / 10^6$$

**Kiểm tra đơn vị:**
- $\Gamma$: $1/\$$ (đơn vị $1/F$)
- $OI$: số hợp đồng
- Multiplier: 100 troy oz/contract ✅ (đúng CME GC)
- $F^2 \cdot 0.01$: chuyển sang $/1\%$ move
- $/10^6$: ra triệu USD

**Đơn vị cuối:** $\frac{1}{\$} \cdot \text{contract} \cdot \frac{\text{oz}}{\text{contract}} \cdot \$^2 \cdot 0.01 / 10^6 = \$$ per 1% move ✅

**Dấu:** Call GEX dương, Put GEX âm — ✅ đúng convention dealer **long call / short put** (giả định dealer là người bán cho khách hàng mua call và mua put). **Lưu ý:** giả định này chỉ đúng nếu dealer net short options — cần kiểm tra thực tế.

**Một điểm cần lưu ý:** Công thức chuẩn của SpotGamma là $GEX = \Gamma \cdot OI \cdot 100 \cdot S^2 \cdot 0.01$ — dùng $S$ (spot) chứ không phải $F$. Với Vàng, $F \approx S$ (basis nhỏ) nên sai số không đáng kể, nhưng về mặt lý thuyết nên dùng $F$ vì options settle theo futures. **Spec đã đúng.**

### 1.5. Air Pockets — ⚠️ ĐỊNH NGHĨA CHƯA NHẤT QUÁN

**Spec:** $OI_k < 0.35 \times \text{Mean}(OI_{all})$
**Notebook:** $(Call\_OI + Put\_OI) < 0.35 \times Mean\_OI\_All$

**Vấn đề:**
- Spec dùng $OI_k$ (không rõ là Call, Put, hay tổng).
- Notebook dùng tổng Call+Put — **hợp lý hơn** vì phản ánh tổng thanh khoản tại strike.
- Nhưng `Mean_OI_All` cần định nghĩa rõ: mean của tổng OI mỗi strike, hay mean của tất cả các strike trong chuỗi?

**Khuyến nghị:** Chuẩn hóa: $OI_k^{total} = Call\_OI_k + Put\_OI_k$; $Mean = \frac{1}{N}\sum_k OI_k^{total}$; ngưỡng 0.35 là hợp lý (dưới 1/3 trung bình).

### 1.6. Basis Sync — ✅ ĐÚNG

$$Basis = Median_{60s}(F - S), \quad Level_{Spot} = Level_{Futures} - Basis$$

Dùng median 60s để khử nhiễu tick-by-tick — **chuẩn thực chiến**. ✅

---

## 2. ĐÁNH GIÁ LOGIC VI MÔ & DEALER HEDGING

### 2.1. Gamma Squeeze / Waterfall Trigger — ⚠️ CÓ VẤN ĐỀ KHÁI NIỆM

**Spec:** $Trigger_{Up} = Call\_Wall + Call_{mid}(CallWall)$

**Vấn đề logic:**
- Call Wall là strike có **OI lớn nhất**, không phải strike có **gamma lớn nhất**.
- Dealer hedging pain point thực sự nằm ở **Absolute Gamma Strike** (max $|Net GEX_k|$), không phải max OI.
- Cộng thêm $Call_{mid}$ (premium) vào strike là **heuristic**, không có cơ sở lý thuyết. Premium phụ thuộc IV, thời gian — không phản ánh "điểm đau" hedging.

**Cơ chế hedging thực tế:**
- Dealer short gamma: khi $F$ tăng qua strike, delta của short call trở nên âm hơn → dealer phải **mua futures** để hedge → tạo feedback loop.
- Điểm kích hoạt thực sự là khi **gamma tăng đột biến** — thường gần ATM của strike có gamma lớn nhất, không phải tại strike + premium.

**Khuyến nghị:**
- Dùng $Trigger_{Up} = \text{Absolute Gamma Strike} + k \cdot \sigma_{M5}$ (với $k \approx 1.5$–$2$), hoặc
- Dùng $Trigger_{Up} = Call\_Wall + 0.5 \cdot (\text{Strike spacing})$ — đơn giản và có cơ sở hơn.
- **Bỏ premium** khỏi công thức trigger — nó gây méo mó khi IV biến động.

### 2.2. Stop Loss 1.5–2.0 giá — ⚠️ CẦN ĐỊNH LƯỢNG THEO VOL

**Vấn đề:** SL cố định 1.5–2.0 USD trên Vàng là **quá hẹp** trong nhiều regime.

- Vàng hiện tại (2026): ATR M5 thường 2–5 USD, ATR H1 8–15 USD.
- SL 2.0 USD = 1 ATR M5 → **xác suất bị quét nhiễu rất cao** (>60%).
- Trong phiên NY open hoặc tin tức (NFP, CPI, FOMC), ATR M5 có thể 8–15 USD → SL 2.0 chắc chắn bị hit.

**Khuyến nghị:**
- SL nên là **hàm của ATR**: $SL = k \cdot ATR_{M5}$ với $k = 1.5$–$2.0$.
- Hoặc dùng **structural SL**: dưới swing low gần nhất + buffer.
- Với Vàng, SL tối thiểu nên là **3–5 USD** trong điều kiện bình thường, **8–12 USD** trong phiên tin tức.

### 2.3. TP1 = Synthetic Pivot — ✅ HỢP LÝ

TP1 về pivot là **mean-reversion target hợp lý** khi fade wall. ✅

### 2.4. TP2 = Wall đối diện — ⚠️ RỦI RO

- Nếu giá đã đi từ Put Wall đến Call Wall, đó là **full range** — thường mất nhiều giờ, có thể qua phiên.
- Trong regime Negative Gamma, giá có thể **không bao giờ đến** wall đối diện mà đảo chiều giữa đường.
- **Khuyến nghị:** TP2 nên là **0.7–0.8 × range** hoặc dùng trailing stop sau TP1.

### 2.5. Fade Logic — ✅ ĐÚNG CƠ CHẾ

Fade tại wall khi Net GEX > 0 là **chuẩn desk**. Dealer long gamma sẽ bán khi giá tăng (ghìm) và mua khi giá giảm (đỡ) → fade hiệu quả. ✅

### 2.6. Breakout Runner — ⚠️ CẦN ĐIỀU KIỆN CHẶT HƠN

Spec yêu cầu "vỡ Wall > 1.5 giá + Net GEX < 0 + Air Pocket phía sau" — **đúng logic**. Nhưng code **không kiểm tra** điều kiện Net GEX < 0 và Air Pocket trước khi kích hoạt Breakout Runner. Đây là **lỗi thực thi** — setup được tạo ra bất kể regime.

**Khuyến nghị:** Trong `build_quant_execution_plan`, chỉ append Breakout/Breakdown Runner nếu `total_net_gex < 0` VÀ có air pocket liền kề.

---

## 3. CÁC ĐIỂM CẦN LƯU Ý / TỐI ƯU HÓA

### 3.1. Theta — Kiểm tra dấu

Công thức spec:
$$\Theta_{call} = -\frac{F e^{-rT} n(d_1)\sigma}{2\sqrt{T}} - rF e^{-rT}N(d_1) + rK e^{-rT}N(d_2)$$

**Kiểm tra:** Với call, theta thường âm. Số hạng 1 âm ✅. Số hạng 2 âm ✅. Số hạng 3 dương (nhỏ). Tổng âm ✅. **Đúng.**

Nhưng **lưu ý:** Theta trong spec là **per year** — cần chia 365 để ra per day. Code không thấy chia → **có thể sai đơn vị** nếu dùng trực tiếp.

### 3.2. Charm — Cần verify

$$\text{Charm} = e^{-rT}\left[n(d_1)\left(\frac{r}{\sigma\sqrt{T}} - \frac{d_2}{2T}\right) - rN(d_1)\right]$$

Đây là $\partial\Delta/\partial T$ (không phải $-\partial\Delta/\partial T$ như spec ghi). **Dấu có thể ngược.** Cần test với case đơn giản ($r=0$): Charm phải $= -e^{-rT}n(d_1)\frac{d_2}{2T}$ — công thức trên cho $n(d_1)(-d_2/2T)$ ✅ khớp. Vậy spec đúng về magnitude, nhưng **nhãn "−∂Δ/∂T" gây nhầm lẫn** — nên ghi rõ là $\partial\Delta/\partial T$ hoặc $\partial\Delta/\partial\tau$ với $\tau = T-t$.

### 3.3. IV Solver — Newton-Raphson có thể fail

- Newton-Raphson trên Black-76 có thể **diverge** khi vega → 0 (deep OTM, gần expiry).
- Spec nói "kết hợp Brent's Method" — tốt, nhưng code không thấy fallback.
- **Khuyến nghị:** Bắt buộc fallback Brent với bracket $[0.01, 5.0]$; nếu vẫn fail → trả về NaN và loại strike khỏi GEX.

### 3.4. 0DTE Edge Cases

- $T \to 0$: $\sigma\sqrt{T} \to 0$ → $d_1, d_2$ có thể $\pm\infty$ → NaN.
- **Khuyến nghị:** Floor $T$ tại $1/(365 \cdot 1440)$ (1 phút) và cap $\sigma$ tại $[0.01, 5.0]$.
- Với 0DTE, IV từ Barchart thường $= 0$ → solver phải chạy. Nhưng nếu bid-ask quá rộng (mid không đáng tin), IV solve ra rác.

### 3.5. GEX Sign Convention — Cần xác nhận

Code giả định **dealer long call, short put** (call GEX +, put GEX −). Đây là convention phổ biến nhưng **không phải lúc nào cũng đúng**. Nếu dealer net long put (hedge fund mua put bảo vệ), dấu ngược lại.

**Khuyến nghị:** Thêm flag `dealer_position_assumption` và cho phép đảo dấu. Hoặc dùng **OI-weighted delta** để suy ra vị thế dealer thực tế.

### 3.6. Basis Sync — Thiếu xử lý contract roll

Khi GCZ26 roll sang GCH27, basis nhảy vọt. Code không có logic phát hiện roll → **basis sẽ sai trong 1–2 ngày roll**.

**Khuyến nghị:** Detect roll bằng cách so sánh basis với rolling median; nếu lệch > 3σ → reset basis window.

### 3.7. Air Pocket — Thiếu điều kiện "liền kề"

Spec nói "chuỗi Strike liên tiếp $[K_1 \to K_2]$" nhưng code chỉ list các strike đơn lẻ. Cần **cluster** các strike liền kề thành vùng, và chỉ cảnh báo khi giá **đi vào vùng** đó.

### 3.8. Risk/Reward Calculation — Có bug tiềm ẩn

```python
rr_buy = round(abs(fade_buy_tp1 - fade_buy_entry) / max(0.5, abs(fade_buy_entry - fade_buy_sl)), 2)
```

- `max(0.5, ...)` để tránh chia 0 — tốt.
- Nhưng nếu `fade_buy_tp1 < fade_buy_entry` (TP dưới entry cho lệnh BUY) → RR âm ngầm. Cần **assert** $TP > Entry$ cho BUY, $TP < Entry$ cho SELL.
- Logic `fade_buy_tp1 = max(synthetic_pivot_spot, put_wall_spot + 5.0) if put_wall_spot >= synthetic_pivot_spot else ...` — **rối và có thể sai**. Nếu Put Wall **trên** pivot (thị trường đã giảm qua pivot), TP1 nên là pivot (dưới entry) — nhưng code lại chọn `max(pivot, wall+5)` → TP **trên** entry → sai hướng.

**Đây là bug logic nghiêm trọng.** Cần viết lại rõ ràng:
```python
if put_wall_spot < synthetic_pivot_spot:
    tp1 = synthetic_pivot_spot  # TP trên entry (BUY)
else:
    tp1 = put_wall_spot + 5.0  # fallback
```

### 3.9. Prohibitions — Tốt nhưng thiếu

- Thiếu: "CẤM vào lệnh trong 5 phút trước/sau tin tức High Impact (NFP, CPI, FOMC)".
- Thiếu: "CẤM vào lệnh khi spread > 2× median spread" (thanh khoản kém).
- Thiếu: "CẤM vào lệnh khi IV > 90th percentile" (event risk).

### 3.10. Thiếu Session Awareness

Vàng có 3 phiên (Asia, London, NY) với behavior khác nhau:
- Asia: range-bound, fade hiệu quả.
- London: breakout.
- NY: volatile, tin tức.

Code không phân biệt session → **cùng một setup cho mọi phiên là rủi ro**.

---

## 4. KẾT LUẬN & ĐIỂM SỐ TÍN NHIỆM

### Bảng tổng hợp

| Hạng mục | Điểm | Ghi chú |
|---|---|---|
| **Black-76 & Greeks** | 9.5/10 | Chuẩn textbook, chỉ cần verify Charm/Theta đơn vị |
| **Put-Call Parity** | 6/10 | Spec đúng, notebook thiếu $e^{rT}$ — sai số nhỏ nhưng cần sửa |
| **Straddle → 1σ** | 6/10 | Xấp xỉ thô, nhãn "1σ" gây hiểu nhầm (thực chất ~0.8σ) |
| **GEX Formula** | 9/10 | Chuẩn CME, đúng đơn vị; cần xác nhận dealer sign convention |
| **Trigger Logic** | 6/10 | Heuristic premium-based thiếu cơ sở; nên dùng ATR/gamma strike |
| **SL/TP** | 5/10 | SL cố định 1.5–2.0 quá hẹp cho Vàng; TP2 quá xa; có bug logic TP1 |
| **Air Pockets** | 7/10 | Định nghĩa chưa nhất quán spec vs code; thiếu clustering |
| **Basis Sync** | 8/10 | Tốt, thiếu xử lý roll |
| **Code Quality** | 7/10 | Có bug logic TP1, thiếu điều kiện regime cho Breakout, thiếu session awareness |
| **Risk Management** | 6/10 | Thiếu news filter, spread filter, IV filter |

### 🎯 ĐIỂM SỐ TỔNG THỂ: **7.0 / 10**

**Phân loại:** *Production-ready với điều kiện sửa các lỗi Critical.*

### 🔴 CRITICAL (phải sửa trước khi live):
1. **Put-Call Parity thiếu $e^{rT}$** trong notebook.
2. **Bug logic TP1** trong `fade_buy_tp1` / `fade_sell_tp1` — có thể tạo TP sai hướng.
3. **Breakout Runner không kiểm tra regime** (Net GEX < 0) và Air Pocket.
4. **SL cố định 1.5–2.0 USD** — phải chuyển sang ATR-based.

### 🟡 HIGH (nên sửa sớm):
5. Đổi nhãn "1-Sigma" → "Expected Move" hoặc scale bằng $1/0.7979$.
6. Trigger dùng ATR thay vì premium.
7. Thêm news/spread/IV filters vào prohibitions.
8. Thêm session awareness (Asia/London/NY).
9. Xử lý contract roll trong basis sync.
10. IV solver fallback Brent + NaN handling.

### 🟢 NICE-TO-HAVE:
11. Dealer position assumption flag.
12. Air pocket clustering.
13. Charm/Theta unit tests.

---

**Kết luận cuối:** Hệ thống có **nền tảng lý thuyết vững** (Black-76, GEX, Put-Call Parity đều đúng chuẩn), nhưng **phần thực thi (Tier 5) có vài lỗi logic nghiêm trọng** có thể dẫn đến **đặt lệnh sai hướng** hoặc **SL bị quét nhiễu**. Với Vàng — một tài sản có ATR cao và nhạy tin tức — việc dùng SL cố định 1.5–2.0 USD là **không khả thi trong thực chiến**. Sau khi sửa 4 lỗi Critical, hệ thống có thể đạt **8.5/10** và sẵn sàng cho paper trading có giám sát.