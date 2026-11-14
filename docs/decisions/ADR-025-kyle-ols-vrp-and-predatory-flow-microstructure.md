# ADR-025: Đặc Tả Hệ Thống "Informed Quant Trader" — Kyle (1985) OLS Lambda, VPIN Toxicity, VRP Vega Crush & Predatory Flow Engine

## Status
Accepted & Implemented

## Date
2026-11-14

## 1. Objective (Mục tiêu & Cơ sở Học thuật)
Chuyển hóa toàn bộ 2 tài liệu học thuật trong `docs/tailieudacta/CÔNG THỨC TÍNH TOÁN/`:
1. **Tài liệu 1:** *Informed & Quant Traders — Kyle (1985), Lead-Lag Ornstein-Uhlenbeck, Volatility Risk Premium (Carr & Wu 2009), Optimal Execution & Predatory Trading (Almgren & Chriss 2001; Brunnermeier & Pedersen 2005)*.
2. **Tài liệu 2:** *Làm sao để trở thành 1 Informed Trader — Bất cân xứng vị thế cấu trúc (Grossman & Stiglitz 1980; Gârleanu, Pedersen & Poteshman 2009), Bayesian Signal-to-Noise Ratio ($\text{SNR}$ & $\rho_{v,s}$), Chỉ số độc tính dòng lệnh VPIN (Easley, López de Prado & O'Hara 2012), và Quản trị vốn theo chế độ thanh khoản $\sigma_u$ & Fractional Kelly*.

Mục tiêu là biến **Neiro-Gold-Quant** thành một **Bộ Lọc Định Lượng Khép Kín (Closed-Loop Informed Quant Filter)** chạy 100% trên dữ liệu thật của **CME Gold Futures (`GC=F`) & COMEX Gold Options (`OG`/`GCZ26`)** (tuân thủ nghiêm ngặt **Rule 8** và **Chuẩn Zero-BS**):
- Không cần đua tốc độ cáp quang HFT, mà khai thác **Bất cân xứng thông tin về cấu trúc vị thế bắt buộc của Market Maker**:
  $$\text{Var}(v \mid \mathcal{F}_{\text{NeiroQuant}}) < \text{Var}(v \mid \mathcal{F}_{\text{public}}) = \Sigma_0$$

---

## 2. Năm Trụ Cột Toán Học Cốt Lõi (Mathematical Specification)

### Trụ cột 1: Hồi quy OLS Kyle's Lambda ($\lambda_{\text{OLS}}$) & Chế độ Thanh khoản Phiên ($\sigma_u$)
- **Công thức Kyle (1985):**
  $$\lambda = \frac{\sigma_v}{2\sigma_u}, \quad \mathbb{E}[\Pi_{\text{Informed}}] = \frac{\sigma_u \sigma_v}{2}$$
- **Ước lượng thực nghiệm trên chuỗi nến M1/M5 `GC=F` (`Rolling OLS Regression`):**
  Thay vì chia thô từng nến $|\Delta P| / V$, hệ thống giải hồi quy OLS cửa sổ trượt $N$ nến giữa biến động giá $\Delta P_k = P_{\text{close}, k} - P_{\text{open}, k}$ và dòng lệnh ròng có dấu $y_k = V_k^B - V_k^S$ (từ BVC):
  $$\Delta P_k = \alpha + \lambda_{\text{OLS}} \cdot y_k + \varepsilon_k \implies \lambda_{\text{OLS}} = \frac{\text{Cov}(\Delta P, \, y)}{\text{Var}(y)} \quad (\text{USD} / 1000 \text{ HĐ GC})$$
- **Bộ lọc Thanh khoản Nhiễu $\sigma_u$ theo Phiên Giao Dịch (CME Globex):**
  - **Phiên Á (`ASIAN_THIN_LIQUIDITY`, $\sigma_u$ thấp):** Khối lượng nhiễu thấp khiến $\lambda_{\text{OLS}}$ tự nhiên phình to. Cảnh báo: *Không dùng lệnh Market lớn, tránh bẫy trượt giá nội sinh*.
  - **Phiên Âu / Phiên Mỹ (`LONDON_NY_DEEP_LIQUIDITY`, $\sigma_u$ cao):** Khi $\sigma_u$ dồi dào mà $\lambda_{\text{OLS}} \ge 1.75 \times \overline{\lambda}$, hệ thống xác nhận **Market Maker đang rút thanh khoản (Widening Spread) vì phát hiện dòng tiền có thông tin (Toxic Informed Flow)**.

---

### Trụ cột 2: Chỉ số Độc Tính Dòng Lệnh VPIN (Easley, López de Prado & O'Hara, 2012)
- **Mục đích:** Bảo vệ Trader khỏi bị "cán nát" (Steamrolled) khi đặt lệnh Limit chặn đầu tàu tại Call Wall / Put Wall đúng lúc quỹ vĩ mô đang tung lệnh đâm xuyên tường.
- **Công thức BVC & Volume-Synchronized Buckets trên `GC=F`:**
  Phân tách khối lượng mua/bán chủ động trên từng thanh/xô khối lượng bằng hàm phân phối tích lũy chuẩn $\Phi(\cdot)$:
  $$V_\tau^B = V_\tau \cdot \Phi\left(\frac{\Delta P_\tau}{\sigma_{\Delta P}}\right), \quad V_\tau^S = V_\tau - V_\tau^B$$
  Chỉ số xác suất dòng tiền độc hại (**VPIN** $\in [0, 100\%]$) trên cửa sổ khối lượng chuẩn hóa:
  $$\text{VPIN} = \frac{\sum_{\tau=1}^{n} \left| V_\tau^B - V_\tau^S \right|}{\sum_{\tau=1}^{n} V_\tau}$$
- **Quy tắc Tác chiến tại Bức Tường Gamma (Call Wall / Put Wall):**
  - **Giá chạm Wall + $\text{VPIN} < 40\%$ + Phiên Âu/Mỹ:** Lực đẩy chỉ là đám đông nhiễu ($\sigma_u$), Market Maker kiểm soát hoàn toàn cuộc chơi $\rightarrow$ **TỰ TIN BÓP CÒ ĐẢO CHIỀU (MEAN-REVERSION FADE)**.
  - **Giá chạm Wall + $40\% \le \text{VPIN} < 65\%$:** Cảnh báo dòng lệnh bắt đầu lệch một chiều (`ELEVATED_IMBALANCE`).
  - **Giá chạm Wall + $\text{VPIN} \ge 65\%$ (vượt phân vị 90 chuẩn học thuật Easley et al., 2012) + $\lambda_{\text{OLS}}$ tăng vọt:** Dòng tiền tổ chức có thông tin đang quét sạch sổ lệnh một chiều $\rightarrow$ **HỦY LỆNH LIMIT CHẶN TÀU — CHUYỂN SANG ĐÁNH THUẬN CHIỀU GAMMA SQUEEZE**.

---

### Trụ cột 3: Định lượng Volatility Risk Premium (`VRP` — Carr & Wu, 2009) & Tín hiệu Vega Crush
- **Công thức:**
  $$VRP_{\text{var}} = IV_{\text{ATM}}^2 - RV_{\text{GC}}^2, \quad VRP_{\text{vol}} = IV_{\text{ATM}} - RV_{\text{GC}} \text{ (điểm \%)}$$
  Trong đó:
  - $IV_{\text{ATM}}$: Độ biến động hàm ý tại ATM của chuỗi quyền chọn COMEX Gold (`OG`/`GCZ26`).
  - $RV_{\text{GC}}$: Độ biến động thực tế (Realized Volatility) chuẩn hóa năm ($\sqrt{252}$) tính từ chuỗi nến `1D` thực tế của `GC=F` (kết hợp bộ đo Parkinson High-Low và Close-to-Close) kèm $RV_{\text{Intraday}}$ từ chuỗi nến `1H`.
- **Ứng dụng Thực Chiến:**
  - Khi $VRP_{\text{vol}} \ge +4.0\%$ hoặc $IV_{\text{ATM}} / RV_{\text{GC}} \ge 1.35$: Báo hiệu **`OVERPRICED VOLATILITY (CHỜ VEGA CRUSH)`** — Quyền chọn đang bị định giá quá đắt trước tin vĩ mô (CPI, FOMC, NFP). Ngay khi tin ra xong và VPIN hạ nhiệt, cú sập IV về lại RV sẽ kích hoạt toàn bộ cột **Net VEX (Vanna)** ép Market Maker mua/bán trả giá giật ngược về vùng cân bằng.
  - Khi $VRP_{\text{vol}} \le -2.0\%$ ($IV_{\text{ATM}} < RV_{\text{GC}}$): Báo hiệu **`UNDERPRICED GAMMA EXPLOSION`** — Biến động thực tế đang nổ mạnh hơn định giá của Options, ưu tiên chiến lược Breakout theo đà CTA.

---

### Trụ cột 4: Z-Score Put-Call Parity Lead-Lag ($Z_{\Delta F}$) & Predatory Flow (Brunnermeier & Pedersen, 2005)
- **Z-Score Dẫn dắt Options–Futures ($Z_{\Delta F}$ — 100% Pure CME COMEX):**
  Tuân thủ **Rule 8** (không dùng giá CFD Spot `XAUUSD`), hệ thống đo quá trình Ornstein-Uhlenbeck của độ lệch giữa **Giá Tương Lai Hàm Ý Từ Quyền Chọn ($F_{\text{opt}, k} = K + e^{rT}(C_k - P_k)$)** và **Giá Khớp Lệnh `GC=F` ($F_{\text{GC}}$)** qua các strike quanh ATM:
  $$Z_{\Delta F} = \frac{\Delta F_{\text{ATM}}}{\sigma_{\Delta F}}$$
  Khi $|Z_{\Delta F}| \ge 2.0$: Xác nhận dòng tiền Informed Trader trên sàn Options COMEX đang đi trước (Lead) sổ lệnh Futures `GC=F`.
- **Nhận diện Dòng tiền Săn mồi (`Predatory Flow / Liquidity Sweep`):**
  - **`PREDATORY_BREAKOUT_HUNT` (Đang săn mồi xuyên tường):** Vùng `SHORT_GAMMA` + Giá áp sát/thủng Wall + $\text{VPIN} \ge 68\%$ + $\lambda_{\text{OLS}}$ tăng đột biến $\rightarrow$ Các quỹ Quant đang bán khống/mua đuổi ép Market Maker cắt lỗ ở giá tệ nhất (**Cấm đỡ dao**).
  - **`PREDATORY_SWEEP_EXHAUSTION` (Hoàn tất quét thanh khoản — Đảo chiều):** Giá vừa quét qua Wall với Volume cực đại ($\ge 1.8 \times \overline{V}$), nhưng ngay sau đó $\lambda_{\text{OLS}}$ và $\text{VPIN}$ hạ nhiệt nhanh $\rightarrow$ Cú săn mồi đã cạn kiệt, **Kích hoạt điểm vào Đảo chiều ăn nhịp hồi phục**.

---

### Trụ cột 5: Hệ Số Thông Tin Bayesian ($\text{SNR}$ / $\rho_{v,s}$) & Ma Trận Thực Thi 4 Chế Độ + Fractional Kelly
- **Chiết khấu Bayesian theo Tỷ số Tín hiệu / Nhiễu ($\text{SNR}$):**
  $$\mathbb{E}[v - p_0 \mid s] = \left(\frac{\text{SNR}}{1 + \text{SNR}}\right) s, \quad \rho_{v,s} = \sqrt{\frac{\text{SNR}}{1 + \text{SNR}}} \in [0, 1]$$
  Hệ thống tổng hợp điểm đồng thuận $\rho_{v,s}$ từ 4 nguồn độc lập: **(1)** Áp lực phòng hộ bắt buộc của MM (`Net GEX/VEX/CHEX` & `Dealer Hedge Flow`), **(2)** Độ lệch dẫn dắt $Z_{\Delta F}$, **(3)** Độc tính dòng lệnh `VPIN` & $\lambda_{\text{OLS}}$, và **(4)** Độ dày thanh khoản phiên $\sigma_u$.
- **Bảng Ma Trận Hành Động Của Informed Trader (Hiển thị trực tiếp trên Terminal):**

| Chế độ Thị trường | Đặc trưng Tham số Vi mô Thực tế | Hành động Khuyến nghị (Informed Trader Action) | Hệ số Vốn Fractional Kelly ($\kappa_{\text{Informed}}$) |
|---|---|---|---|
| **1. Thanh khoản mỏng (Phiên Á)** | $\sigma_u$ thấp $\implies \lambda_{\text{OLS}}$ phình to ảo | **NGỪNG GIAO DỊCH / CHỜ PHIÊN ÂU.** Tránh trượt giá nội sinh và nhiễu ngẫu nhiên. | $0.25\times$ (Bảo toàn vốn) |
| **2. Mắt bão Trung hòa (ATM Noise)** | $|\text{Net GEX}|$ nhỏ, $|Z_{\Delta F}| < 1.0$, xa Wall | **ĐỨNG NGOÀI.** MM không bị ép phòng hộ cơ học; giá chạy Random Walk ($\mathbb{E}[\Pi] \approx 0$). | $0.25\times$ |
| **3. Chạm Wall + VPIN Thấp + Phiên Âu/Mỹ** | $\sigma_u$ lớn, $\text{VPIN} < 45\%$, $\lambda_{\text{OLS}}$ ổn định, Long Gamma | **KÍCH HOẠT LỆNH ĐẢO CHIỀU (MEAN-REVERSION).** Tựa lưng vào lực phòng hộ cơ học của MM. | $1.00\times$ (Tối đa hóa $\frac{\sigma_u \sigma_v}{2}$) |
| **4. Chạm Wall + VPIN Độc hại ($\ge 68\%$)** | $\text{VPIN} \ge 68\%$, $\lambda_{\text{OLS}}$ vọt cao, Short Gamma | **HỦY LIMIT CẢN TÀU — ĐÁNH THUẬN SQUEEZE** hoặc chờ `PREDATORY_SWEEP_EXHAUSTION`. | $0.50\times$ (Kiểm soát Tail Risk) |
| **5. Hậu Tin Vĩ Mô + VRP Cực Đại** | $VRP_{\text{vol}} \ge +4.0\%$, VPIN bắt đầu hạ nhiệt | **ĐÁNH NHỊP VANNA / VEGA CRUSH.** Đón lực đóng vị thế phòng hộ của MM khi IV sập về RV. | $0.75\times$ |

---

## 3. Commands (Lệnh kiểm thử & vận hành)
```powershell
# 1. Chạy bộ kiểm thử đơn vị cho mô hình Kyle OLS, VPIN, VRP & Informed Trader Matrix
python -m pytest tests/test_institutional.py tests/test_dealer.py tests/test_cngthctnhton_math_audit.py -v

# 2. Chạy toàn bộ bộ kiểm thử lõi và Dashboard Smoke Test
python -m pytest tests/test_html_dashboard.py tests/test_hud_smoke.py tests/test_data_gate.py tests/test_neiro_terminal.py -q

# 3. Tái tạo Terminal HTML & kiểm tra dung lượng bộ nhớ (< 15MB)
python -m src.hud.html_dashboard --input data/options_prices_GCZ26.csv --output index.html exports/index.html exports/latest_gold_dashboard.html --clear-cache
```

---

## 4. Project Structure (Các file dự kiến cập nhật)
```text
src/
├── quant_engine/
│   ├── dealer.py            # Nâng cấp reconstruct_institutional_orderflow(): Rolling OLS Kyle's Lambda, VPIN (BVC Volume Buckets), Parity Z-Score & Predatory Sweep state
│   └── institutional.py     # Bổ sung compute_vrp_metrics() (IV_ATM vs RV_GC) & evaluate_informed_trader_regime() (Bayesian SNR rho_vs, sigma_u session filter & 5-state Action Matrix)
├── hud/
│   ├── html_dashboard.py    # Nối VRP, VPIN, Kyle OLS & Informed Trader Action Matrix vào bảng Institutional Microstructure
│   └── neiro_terminal.py    # Hiển thị VPIN Toxicity, VRP Vega Crush & Informed Action Badge trên Floating HUD
tests/
└── test_institutional.py    # Unit tests kiểm định toán học cho Rolling OLS Kyle's Lambda, VPIN, VRP, Bayesian SNR và Predatory Flow
docs/
├── spec.md                  # Đồng bộ đặc tả hệ thống
└── decisions/
    └── ADR-025-kyle-ols-vrp-and-predatory-flow-microstructure.md
```

---

## 5. Code Style & Data Contracts

```python
@dataclass(frozen=True, slots=True)
class InformedTraderRegime:
    session_name: str              # ASIAN_THIN | LONDON_DEEP | NY_COMEX_DEEP | GLOBEX_CLOSED
    sigma_u_depth_score: float     # [0.0, 1.0] do day thanh khoan nhieu dam dong
    vpin_pct: float                # [0.0, 100.0] xac suat dong tien doc hai (Easley et al. 2012)
    kyle_lambda_ols: float         # He so hoi quy OLS Cov(dP, y) / Var(y)
    parity_z_score: float          # Z-Score do lech F_opt - F_GC
    vrp_spread_pct: float          # IV_ATM - RV_GC (%)
    bayesian_conviction_rho: float # He so tuong quan thong tin rho_{v,s} = sqrt(SNR / (1 + SNR))
    kelly_fraction_mult: float     # He so dieu chinh khoi luong Fractional Kelly [0.25, 1.00]
    regime_code: str               # THIN_BOOK_WAIT | ATM_RANDOM_WALK | WALL_MEAN_REVERSION | TOXIC_SQUEEZE_HUNT | VEGA_CRUSH_VANNA | PREDATORY_EXHAUSTION_REV
    action_badge_vi: str           # Nhan hanh dong tac chien hien thi tren HUD
    tactical_guidance_vi: str      # Huong dan chi tiet cho Informed Trader
```

---

## 6. Testing Strategy (Chiến lược Kiểm thử)
1. **Unit Tests Toán Học (`tests/test_institutional.py`):**
   - Kiểm chứng `compute_rolling_kyle_lambda_ols()` khớp nghiệm giải tích $\text{Cov}(\Delta P, y)/\text{Var}(y)$.
   - Kiểm chứng `VPIN` nằm trong $[0, 100\%]$: khi toàn bộ nến tăng mạnh một chiều $\rightarrow \text{VPIN} \to 100\%$ (`TOXIC_FLOW`); khi nến mua/bán cân bằng $\rightarrow \text{VPIN} < 45\%$ (`SAFE_MEAN_REVERSION`).
   - Kiểm chứng `compute_vrp_metrics()` nhận diện đúng `OVERPRICED_VEGA_CRUSH` ($IV \gg RV$) và `UNDERPRICED_GAMMA_EXPLOSION` ($IV < RV$).
   - Kiểm chứng `evaluate_informed_trader_regime()` phân loại đúng 5 chế độ thị trường trong bảng Ma trận Hành động và tính đúng hệ số $\rho_{v,s} = \sqrt{\text{SNR}/(1+\text{SNR})}$.
2. **Smoke & Regression Tests:**
   - Toàn bộ 64+ bài kiểm thử hiện tại tiếp tục PASS 100%.

---

## 7. Boundaries (Ranh giới Kỷ luật)
- **Always do:** Sử dụng 100% dữ liệu thực từ CME `GC=F` & Options `OG`/`GCZ26`; giữ dung lượng dự án `< 15MB`; cập nhật tài liệu đồng bộ.
- **Ask first:** Thay đổi công thức tính Hard SL / TP mặc định của bảng chiến lược.
- **Never do:** Không dùng giá CFD Spot `XAUUSD` (Rule 8); không bịa đặt dữ liệu ngẫu nhiên khi thiếu nến (Zero-BS).

---

## 8. Success Criteria (Tiêu chí Hoàn thành)
- [x] Triển khai đầy đủ 5 trụ cột toán học (`Kyle OLS Lambda`, `VPIN Toxicity`, `VRP Vega Crush`, `Parity Z-Score & Predatory Flow`, `Bayesian SNR & Informed Trader Action Matrix`).
- [x] Tích hợp trực quan lên bảng **Institutional Microstructure** (cửa sổ động `±10 strikes` quanh giá realtime `GC=F` tự động dịch chuyển `👉 SPOT` theo tick live) và **Floating HUD** của Terminal.
- [x] Unit tests kiểm định toàn bộ công thức đạt 100% PASS.
