# ADR-009: Volatility Smile & Skew Microstructure Invariants, Malz SVI Parametrization & 3-Panel Tactical Mapping

## Trạng Thái (Status)
**ĐÃ CHẤP NHẬN (ACCEPTED)** - Ngày 23/10/2026.

---

## 1. Bối Cảnh (Context)

### 1.1. Sự khác biệt giữa Lý thuyết Black-Scholes và Thực tế Thị trường (The Volatility Smile)
- Trong mô hình Black-Scholes / Black-76, giả định cơ bản là lợi suất giá tài sản tuân theo phân phối chuẩn (Gaussian log-normal) với độ biến động ngụ ý không đổi:
  $$\sigma(K) = \text{const}, \quad \forall K$$
  Theo lý thuyết này, đồ thị biểu diễn mối quan hệ giữa Độ biến động hàm ý ($IV$) và Mức giá thực hiện ($K$) là một đường thẳng nằm ngang.
- **Thực tế vi cấu trúc quyền chọn COMEX Gold (GC/OG):**
  Thị trường tài chính luôn tồn tại hiện tượng đuôi béo (Fat-tail / Leptokurtosis) do các cú sốc cực đoan (Thiên nga đen, chiến tranh địa chính trị, số liệu FOMC/CPI, rủi ro vỡ nợ ngân hàng).
  * **Tại vùng giá hiện tại (At-The-Money - ATM):** Biến động nằm trong tầm kiểm soát của Market Makers (MM), cung cầu cân bằng, rủi ro thanh lý tức thời thấp $\rightarrow$ MM định giá $IV$ thấp nhất.
  * **Càng đi xa về hai phía (Deep OTM Put và Deep OTM Call):** Các quỹ đầu cơ lớn và tổ chức đổ xô mua quyền chọn để phòng hiểm rủi ro sập hầm (mua OTM Put) hoặc phòng ngừa Vàng tăng dựng đứng mất nóc (mua OTM Call). Để tự bảo vệ khỏi phá sản, Market Maker buộc phải tăng mạnh giá bán (bơm $IV$ lên cực cao) ở hai đầu biên độ $\rightarrow$ Tạo thành đường cong hình cánh cung võng xuống ở giữa và vểnh cao lên ở hai đầu, gọi là **Đường cong Nụ cười Biến động (Volatility Smile)**.

### 1.2. Phân loại 3 Hình thái Đường cong Biến động trên Thị trường Thực chiến

| Loại đường cong | Hình dáng đồ thị | Thị trường đặc trưng | Ý nghĩa tâm lý đám đông & Dealer |
| :--- | :--- | :--- | :--- |
| **1. Volatility Smile chuẩn (Cân đối)** | Võng ở giữa, hai mép Trái - Phải vểnh cao tương đương nhau. | Ngoại hối (Forex) hoặc Vàng trong pha tích lũy nén biên độ chờ tin lớn. | Thị trường đánh giá rủi ro đột biến cân bằng ở cả hai chiều (tăng sốc hoặc giảm sâu). |
| **2. Reverse Skew / Put Skew (Lệch Trái)** | Mép trái ($K < S$) vểnh cao vút, mép phải ($K > S$) thấp lè tè hoặc dốc xuống. | Thị trường chứng khoán cổ phiếu (S&P 500, Nasdaq, Dow Jones). | Đám đông chỉ sợ thị trường sập sàn (Crash Fear) nên tranh nhau mua Put bảo hiểm, trong khi ít ai mua OTM Call xa. |
| **3. Forward Skew / Call Skew (Lệch Phải)** | Mép phải ($K > S$) vểnh cao vút, mép trái thấp hơn hoặc âm. | **Đặc sản của VÀNG (COMEX Gold GC/OG) trong chu kỳ tăng / bất ổn vĩ mô.** | Vàng là tài sản trú ẩn an toàn (Safe Haven). Khi có chiến tranh/lạm phát, đám đông FOMO tột độ sợ Vàng "bay mất nóc" nên mua Call OTM điên cuồng, đẩy Call IV cao hơn hẳn Put IV. |

### 1.3. Khảo sát thực tế trên Sổ lệnh Quyền chọn Vàng (CME GCZ26 / OG)
Quan sát chuỗi giá quyền chọn thực tế trên bảng Barchart/CME:
```
  Độ biến động (IV)
  ^
35%|  * (3,900: IV ~25-42%)                             * (4,275: Call IV 27.58%)
   |    *                                             *
25%|       * (4,000: IV ~25%)                     * (4,150: Call IV 26.87%)
   |           *                               *
19%|               *   *   *   *   *   *   * 
   |                 (Đáy Nụ Cười: 4,025 - 4,035)
   |                 (IV thấp nhất: ~18.9% - 19.9%)
   +---------------------------------------------------------> Mức giá Strike (K)
    3,900        4,000       4,030 (ATM)     4,150      4,275
```
- **Đáy Nụ cười (Vùng mắt bão 4,025 – 4,035):** $IV$ của cả Call và Put đều tụt xuống mức thấp nhất quanh 18.96% – 19.97%, $IV$ Skew xấp xỉ 0%. Đây là nơi MM hưởng lợi tối đa từ suy giảm thời gian (Theta Harvesting).
- **Mép phải (Call Skew):** Lên các mốc $4,150 - $4,275, Call $IV$ bị bơm vọt lên 26.87% – 27.58%, Call $IV$ Skew dương $+4.89\%$ đến $+7.49\%$.
- **Mép trái (Put Skew):** Xuống các mốc $3,985 - $3,800, Put $IV$ vọt lên 25.60% – 28.85%, Put $IV$ Skew dương $+3.02\%$ đến $+8.45\%$.

---

## 2. Nền Tảng Toán Học & Định Lượng Vi Cấu Trúc (Mathematical Foundation)

### 2.1. Phân rã Đường cong Nụ cười: Tham số hóa Malz (1997) & 25-Delta Metrics
Để đưa đường cong phi tuyến tính $IV(K)$ vào thuật toán xử lý với thời gian thực tính bằng micro-giây, hệ thống Neiro-Quant áp dụng mô hình phân rã Malz (1997) chuẩn hóa quốc tế dựa trên $25$-Delta Call và Put:

$$\begin{aligned}
RR25 &= IV(Call_{25\Delta}) - IV(Put_{25\Delta}) \\
BF25 &= \frac{IV(Call_{25\Delta}) + IV(Put_{25\Delta})}{2} - IV_{ATM}
\end{aligned}$$

- **Độ dốc lệch (Risk Reversal - $RR25$):**
  * Đo lường tính bất đối xứng (Asymmetry / Skew) của nụ cười.
  * $RR25 > 0$: **Forward Call Skew** (Nghiêng Call Bullish). Thị trường chấp nhận trả phí cao vượt trội cho quyền chọn mua tăng giá.
  * $RR25 < 0$: **Reverse Put Skew** (Nghiêng Put Bearish). Thị trường chấp nhận trả phí cao cho quyền chọn bán bảo hiểm sập.
- **Độ cong vểnh (Butterfly - $BF25$):**
  * Đo lường độ cong (Curvature / Smile Depth), tương đương với mô-men bậc 4 (Kurtosis) của hàm mật độ xác suất giá.
  * $BF25$ càng lớn, nụ cười càng sâu và hai mép càng vểnh dốc đứng, phản ánh thị trường đang định giá phần bù rủi ro đuôi (Tail Risk Premium) cực đoan.

### 2.2. Mối Tương Quan Giữa Volatility Smile và Greeks Bậc 2 (Vanna & Charm)
Trong mô hình định giá Black-76, các độ nhạy bậc hai kết nối mật thiết với hình thái của Nụ cười biến động:
- **Vanna ($\mathcal{V}_{\text{anna}} = \frac{\partial \Delta}{\partial \sigma} = \frac{\partial \mathcal{V}}{\partial S}$):**
  * Đo lường sự thay đổi của vị thế Delta khi $IV$ biến động theo đường cong nụ cười.
  * Khi giá tiệm cận đáy nụ cười (ATM), $IV$ sụt giảm ($\Delta \sigma < 0$). Vị thế Long Vanna của Dealer ép họ phải giao dịch ngược pha (mua khi giá giảm, bán khi giá tăng), tạo lực ghìm chặt biên độ giá (Pinning Force).
- **Charm ($\mathcal{C}_{\text{harm}} = -\frac{\partial \Delta}{\partial t}$ - Delta Decay):**
  * Đo lường sự trôi dạt của vị thế phòng hộ Delta khi thời gian tiến dần về 0 ($t \to T$).
  * Tại đáy nụ cười, tốc độ bào mòn giá trị thời gian (Theta Decay) đạt cực đại, giải thích hành vi ghìm giá tại chỗ của MM để ăn trọn phí quyền chọn đã bán.

---

## 3. Ba Bất Biến Tác Chiến Vi Cấu Trúc (Three Tactical Invariants)

Neiro-Quant thiết lập 3 bất biến giao dịch dựa trên hình thái Volatility Smile:

### Bất Biến 1: "Tâm Bão" (Sweet Spot / Dealer Pinning Center)
- **Định vị định lượng:** Đáy thấp nhất của đường cong nụ cười, nơi $IV$ đạt giá trị nhỏ nhất toàn chuỗi và $IV$ Skew xấp xỉ $0\%$ hoặc âm nhẹ quanh ATM.
- **Cơ chế vi mô:** Đây là mốc giá tối ưu hóa lợi nhuận tuyệt đối của Market Maker (vùng hội tụ Gamma ròng dương cực đại, Vanna ghìm giá và thu trọn phí Theta). MM có động cơ tài chính tối đa để ghìm giá vàng đứng yên tại đây trong ngày đáo hạn.
- **Quy tắc tác chiến:**
  * Kích hoạt trạng thái **Sideway / Mean-Reversion**.
  * Nghiêm cấm đánh Breakout mua đuổi / bán đuổi khi giá đang dao động quanh đáy nụ cười.
  * Ưu tiên chiến thuật Fade Range (bán tại mép trên cản, mua tại mép dưới sàn).

### Bất Biến 2: "Hố Đen Giảm Tốc" (Bức Tường Thật / Structural Skew Dip)
- **Định vị định lượng:** Mốc giá xuất hiện vết lõm sâu bất thường trên đồ thị $IV$ Skew so với quy luật vểnh tự nhiên của nụ cười (Ví dụ: tại mốc $4,045 - $4,050, Put $IV$ Skew bị lõm âm sâu $-4.60\%$ và $-8.81\%$).
- **Cơ chế vi mô:** Theo lý thuyết, càng rời xa ATM thì đường cong $IV$ phải vểnh lên (Skew dương). Nếu tại một mức giá cản mà Skew bị **lõm âm sâu**, điều đó chứng minh Market Maker đang **chủ động bán khống khối lượng lớn quyền chọn (Short Volatility / Short Vega)** để đè bẹp biến động và thiết lập thành trì phòng thủ.
- **Quy tắc tác chiến:**
  * Đây là **Điểm đặt lệnh Limit đánh đảo chiều (Fade Bounce) an toàn nhất!**
  * Động thái bán đè quyền chọn của MM sẽ triệt tiêu động lượng của phe tấn công, tạo ra phản xạ dội ngược giá rõ rệt.

### Bất Biến 3: "Bẫy Thuốc Nổ" (Mép Vểnh / Volatility Squeeze Danger Zone)
- **Định vị định lượng:** Vùng hai bên cánh vểnh cao vút của nụ cười, nơi $IV$ Skew dương vọt cực đại ($> +6.0\%$ đến $+9.0\%$, ví dụ vùng trên $4,060$ hoặc dưới $3,985$).
- **Cơ chế vi mô:** Tại các mốc này, Market Maker định giá rủi ro vỡ bờ cực lớn. Nếu giá xuyên thủng tường cản và lọt vào vùng mép vểnh, MM rơi vào trạng thái Short Gamma hoảng loạn. Để tránh cháy tài khoản, MM buộc phải **mua đuổi hoặc bán xả lũ hợp đồng tương lai COMEX Futures** để phòng hộ delta, kích hoạt chuỗi phản ứng dây chuyền bão giá (**Gamma Squeeze / Slicing Momentum**).
- **Quy tắc tác chiến:**
  * **VÙNG BẮT BUỘC ĐẶT STOP LOSS (CẮT LỖ)!**
  * Nghiêm cấm tuyệt đối việc gồng lỗ, đặt limit bình quân giá hoặc cản đầu xu hướng khi giá đã phá vỡ thành trì và lọt vào mép vểnh của nụ cười.

---

## 4. Ánh Xạ Kiến Trúc Lên Hệ Thống Neiro-Quant

Học thuyết Volatility Smile & Skew được ánh xạ hoàn chỉnh vào các module của hệ thống:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        VOLATILITY SMILE & SKEW ARCHITECTURE                            │
└───────────────────────────────────┬────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┴───────────────────────────┐
        ▼                                                       ▼
┌─────────────────────────────────┐   ┌─────────────────────────────────────────────────┐
│ [Định Lượng Lõi Malz SVI]        │   │ [Ánh Xạ Tactical HUD 3 Panel]                   │
│ (src/quant_engine/institutional)│   │ (src/hud/html_dashboard.py)                     │
│                                 │   │                                                 │
│ • RR25: Risk Reversal Tilt      │   │ • Panel 1: Đáy Nụ Cười = Pinning Spot           │
│ • BF25: Smile Curvature         │   │   Vết lõm Skew = [BOUNCE PIN] Hố đen giảm tốc   │
│ • SkewRegime: Bullish / Bearish │   │   Mép vểnh Skew = [MAGNET TRAP] Bẫy thuốc nổ     │
│ • Vol-Targeted Sizing           │   │ • Panel 2: Sổ Sách Net Delta & Siege Ratio       │
│                                 │   │ • Panel 3: Greeks Bậc 2 (Vanna & Charm)         │
│                                 │   │ • KPI Card: 25Δ Skew & Smile Curvature Badge    │
└─────────────────────────────────┘   └─────────────────────────────────────────────────┘
```

1. **Module Tính Toán Định Lượng ([src/quant_engine/institutional.py](file:///c:/Users/Daniel/Documents/My-Projects/Neiro-Quant/src/quant_engine/institutional.py)):**
   - Hàm `extract_rr_bf()` trích xuất liên tục $RR25$ và $BF25$ từ chuỗi dữ liệu options CME.
   - Hàm `detect_cta_confluence()` phối hợp giữa độ lệch Skew của nụ cười và biên độ phá vỡ của các Quỹ CTA Momentum.
2. **Module Hiển Thị Terminal ([src/hud/html_dashboard.py](file:///c:/Users/Daniel/Documents/My-Projects/Neiro-Quant/src/hud/html_dashboard.py)):**
   - Panel 1 hiển thị các mốc Thành trì chiến thuật phân định rõ `[BOUNCE PIN]` (Hố đen giảm tốc) và `[MAGNET TRAP]` (Bẫy mép vểnh gia tốc).
   - Panel 3 trực quan hóa độ phơi nhiễm Vanna và Charm dọc theo các mức Strike quanh nụ cười biến động.
   - Thẻ Institutional Metrics Card hiển thị nhãn Skew và tỷ lệ lệch hướng dòng tiền.

---

## 5. Hệ Quả & Đánh Giá (Consequences)

### Tích Cực (Positive):
1. **Lý thuyết hóa toàn diện:** Chấm dứt hoàn toàn việc nhìn nhận quyền chọn như các con số rời rạc, thiết lập khung tư duy vi cấu trúc chuẩn xác theo các Volatility Desk Phố Wall.
2. **Kỷ luật rủi ro tuyệt đối:** Bất biến "Bẫy thuốc nổ mép vểnh" đưa ra tiêu chuẩn toán học không thể bàn cãi cho vị trí đặt Stop Loss.
3. **Hiệu suất tính toán siêu nhẹ:** Sử dụng phép nội suy tuyến tính 25-Delta thay vì giải mô hình tối ưu hóa phi tuyến SVI phức tạp, đảm bảo CPU < 5%, RAM cố định và Zero-Waste.

### Hạn chế & Giám sát (Trade-offs & Monitoring):
1. **Phụ thuộc chất lượng dữ liệu nguồn:** Tại các chuỗi kỳ hạn rất xa hoặc thanh khoản kém, $IV$ của các strike Deep OTM có thể bị thiếu hoặc nhiễu. Hệ thống duy trì thuật toán fallback nội suy ATM an toàn trong `extract_rr_bf()`.
