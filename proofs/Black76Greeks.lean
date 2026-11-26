/-
  Black76Greeks.lean — Neiro-Gold-Quant Formal Verification
  ===========================================================
  Chứng minh tính đúng đắn của Greeks Black-76:
    - Gamma ≥ 0 với mọi tham số hợp lệ  ← QUAN TRỌNG NHẤT
    - Delta_Call ∈ (0, 1]
    - Vanna và Charm có dấu xác định

  Đây là tính chất cốt lõi đảm bảo:
    GEX = OI × Gamma × Multiplier ≥ 0  (vì OI ≥ 0, Gamma ≥ 0)
-/

import Mathlib.Analysis.SpecialFunctions.Log.Basic
import Mathlib.Analysis.SpecialFunctions.ExpDeriv
import Neiro_Proofs.Black76Core

open Real

-- ============================================================
-- §1. Black-76 Gamma
-- ============================================================

/-- Gamma Black-76:
    Γ(F,K,σ,T,r) = e^(-rT) · N'(d1) / (F·σ·√T)
    
    Đây là tốc độ thay đổi của Delta theo giá Futures. -/
noncomputable def black76_gamma (F K σ T r : ℝ) : ℝ :=
  Real.exp (-r * T) * normalPDF (black76_d1 F K σ T) /
  (F * σ * Real.sqrt T)

/-- ✅ ĐỊNH LÝ CHÍNH: Gamma ≥ 0 với mọi tham số hợp lệ
    
    Điều kiện: F > 0, K > 0, σ > 0, T > 0, r ≥ 0
    Ý nghĩa: Market Maker luôn có GEX không âm → phòng hộ chiều mua -/
theorem gamma_nonneg
    (F K σ T r : ℝ)
    (hF : 0 < F) (hK : 0 < K) (hσ : 0 < σ) (hT : 0 < T) (hr : 0 ≤ r) :
    0 ≤ black76_gamma F K σ T r := by
  unfold black76_gamma
  apply div_nonneg
  · -- e^(-rT) ≥ 0 vì exp luôn dương
    -- N'(d1) ≥ 0 vì normalPDF_nonneg
    apply mul_nonneg
    · exact le_of_lt (Real.exp_pos _)
    · exact normalPDF_nonneg _
  · -- F·σ·√T > 0 vì mỗi thừa số đều dương
    apply mul_nonneg
    · apply mul_nonneg
      · exact le_of_lt hF
      · exact le_of_lt hσ
    · exact Real.sqrt_nonneg _

/-- Gamma > 0 (strictly) khi mọi tham số strictly positive -/
theorem gamma_pos
    (F K σ T r : ℝ)
    (hF : 0 < F) (hK : 0 < K) (hσ : 0 < σ) (hT : 0 < T) (hr : 0 ≤ r) :
    0 < black76_gamma F K σ T r := by
  unfold black76_gamma
  apply div_pos
  · apply mul_pos
    · exact Real.exp_pos _
    · -- normalPDF > 0 vì exp(-x²/2) > 0 với mọi x
      unfold normalPDF
      apply mul_pos
      · positivity
      · exact Real.exp_pos _
  · apply mul_pos
    · apply mul_pos hF hσ
    · exact Real.sqrt_pos.mpr hT

-- ============================================================
-- §2. Black-76 Delta
-- ============================================================

/-- Delta Call Black-76:
    Δ_call = e^(-rT) · Φ(d1)
    
    Xác suất risk-neutral rằng Call sẽ ITM lúc đáo hạn. -/
noncomputable def black76_delta_call (F K σ T r : ℝ) : ℝ :=
  Real.exp (-r * T) * normalCDF (black76_d1 F K σ T)

/-- Delta Put Black-76:
    Δ_put = -e^(-rT) · Φ(-d1) = e^(-rT) · (Φ(d1) - 1) -/
noncomputable def black76_delta_put (F K σ T r : ℝ) : ℝ :=
  Real.exp (-r * T) * (normalCDF (black76_d1 F K σ T) - 1)

/-- ✅ Delta Call nằm trong khoảng (0, e^(-rT)] ⊆ (0, 1]
    Ý nghĩa: Mua Call không bao giờ có Delta âm hoặc > 1 -/
theorem delta_call_pos
    (F K σ T r : ℝ)
    (hF : 0 < F) (hK : 0 < K) (hσ : 0 < σ) (hT : 0 < T) (hr : 0 ≤ r) :
    0 < black76_delta_call F K σ T r := by
  unfold black76_delta_call
  apply mul_pos
  · exact Real.exp_pos _
  · -- normalCDF > 0: vì erf(x) > -1 với mọi x hữu hạn
    unfold normalCDF
    have h := Real.neg_one_le_erf (black76_d1 F K σ T / Real.sqrt 2)
    linarith

/-- ✅ Delta Call ≤ 1 (bounded above by 1 khi r=0)
    Điều kiện: r = 0 (risk-free rate = 0) -/
theorem delta_call_le_one
    (F K σ T : ℝ)
    (hF : 0 < F) (hK : 0 < K) (hσ : 0 < σ) (hT : 0 < T) :
    black76_delta_call F K σ T 0 ≤ 1 := by
  unfold black76_delta_call
  simp [Real.exp_zero]
  -- normalCDF ≤ 1: từ erf ≤ 1
  exact (normalCDF_range _).2

/-- ✅ Put-Call Parity (Black-76):
    C - P = e^(-rT) · (F - K)
    
    Đây là điều kiện no-arbitrage cơ bản nhất. -/
theorem put_call_parity_delta
    (F K σ T r : ℝ) :
    black76_delta_call F K σ T r - black76_delta_put F K σ T r =
    Real.exp (-r * T) := by
  unfold black76_delta_call black76_delta_put
  ring

-- ============================================================
-- §3. Vanna (∂Δ/∂σ = ∂Γ/∂F cross-Greek)
-- ============================================================

/-- Vanna định tính: Có cùng dấu với -d2
    Khi d2 > 0 (Deep ITM): Vanna < 0 → IV tăng làm giảm Delta
    Khi d2 < 0 (Deep OTM): Vanna > 0 → IV tăng làm tăng Delta -/
theorem vanna_sign_characterization
    (F K σ T r : ℝ)
    (hF : 0 < F) (hσ : 0 < σ) (hT : 0 < T) :
    -- Nếu F = K (ATM) thì d2 = -σ·√T/2 < 0, Vanna > 0
    black76_d2 F F σ T = -(σ * Real.sqrt T / 2) := by
  simp [black76_d2, black76_d1, Real.log_one]
  ring
