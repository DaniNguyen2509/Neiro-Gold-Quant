/-
  Black76Greeks.lean — Neiro-Gold-Quant Formal Verification
  ===========================================================
  Chứng minh tính đúng đắn của Greeks Black-76:
    - Gamma ≥ 0 với mọi tham số hợp lệ  ← QUAN TRỌNG NHẤT
    - Delta_Call ∈ (0, 1]
    - Put-Call Parity cho Delta
    - Vanna tại ATM (d2 < 0)
-/

import Mathlib.Analysis.SpecialFunctions.Log.Basic
import Mathlib.Analysis.SpecialFunctions.ExpDeriv
import Neiro_Proofs.Black76Core

open Real

-- ============================================================
-- §1. Black-76 Gamma
-- ============================================================

/-- Gamma Black-76:
    Γ(F,K,σ,T,r) = e^(-rT) · N'(d1) / (F·σ·√T) -/
noncomputable def black76_gamma (F K σ T r : ℝ) : ℝ :=
  Real.exp (-r * T) * normalPDF (black76_d1 F K σ T) /
  (F * σ * Real.sqrt T)

/-- ✅ ĐỊNH LÝ CHÍNH: Gamma ≥ 0 với mọi tham số hợp lệ -/
theorem gamma_nonneg
    (F K σ T r : ℝ)
    (hF : 0 < F) (_hK : 0 < K) (hσ : 0 < σ) (_hT : 0 < T) (_hr : 0 ≤ r) :
    0 ≤ black76_gamma F K σ T r := by
  unfold black76_gamma
  apply div_nonneg
  · apply mul_nonneg
    · exact le_of_lt (Real.exp_pos _)
    · exact normalPDF_nonneg _
  · apply mul_nonneg
    · apply mul_nonneg (le_of_lt hF) (le_of_lt hσ)
    · exact Real.sqrt_nonneg _

/-- Gamma > 0 (strictly) khi mọi tham số strictly positive -/
theorem gamma_pos
    (F K σ T r : ℝ)
    (hF : 0 < F) (_hK : 0 < K) (hσ : 0 < σ) (hT : 0 < T) (_hr : 0 ≤ r) :
    0 < black76_gamma F K σ T r := by
  unfold black76_gamma
  apply div_pos
  · apply mul_pos
    · exact Real.exp_pos _
    · exact normalPDF_pos _
  · apply mul_pos
    · apply mul_pos hF hσ
    · exact Real.sqrt_pos.mpr hT

-- ============================================================
-- §2. Black-76 Delta
-- ============================================================

/-- Delta Call Black-76: Δ_call = e^(-rT) · Φ(d1) -/
noncomputable def black76_delta_call (Φ : NormalCDFSpec) (F K σ T r : ℝ) : ℝ :=
  Real.exp (-r * T) * Φ.cdf (black76_d1 F K σ T)

/-- Delta Put Black-76: Δ_put = e^(-rT) · (Φ(d1) - 1) -/
noncomputable def black76_delta_put (Φ : NormalCDFSpec) (F K σ T r : ℝ) : ℝ :=
  Real.exp (-r * T) * (Φ.cdf (black76_d1 F K σ T) - 1)

/-- ✅ Delta Call > 0 với mọi tham số hợp lệ -/
theorem delta_call_pos
    (Φ : NormalCDFSpec) (F K σ T r : ℝ) :
    0 < black76_delta_call Φ F K σ T r := by
  unfold black76_delta_call
  exact mul_pos (Real.exp_pos _) (Φ.cdf_pos _)

/-- ✅ Delta Call ≤ 1 khi r ≥ 0 và T > 0 -/
theorem delta_call_le_one
    (Φ : NormalCDFSpec) (F K σ T r : ℝ)
    (hT : 0 < T) (hr : 0 ≤ r) :
    black76_delta_call Φ F K σ T r ≤ 1 := by
  unfold black76_delta_call
  have hexp_le : Real.exp (-r * T) ≤ 1 := by
    rw [Real.exp_le_one_iff]
    nlinarith
  have hcdf_nonneg : 0 ≤ Φ.cdf (black76_d1 F K σ T) := le_of_lt (Φ.cdf_pos _)
  calc
    Real.exp (-r * T) * Φ.cdf (black76_d1 F K σ T)
        ≤ 1 * 1 := mul_le_mul hexp_le (Φ.cdf_le_one _) hcdf_nonneg zero_le_one
    _ = 1 := one_mul 1

/-- ✅ Put-Call Parity cho Delta: Δ_call - Δ_put = e^(-rT) -/
theorem put_call_parity_delta
    (Φ : NormalCDFSpec) (F K σ T r : ℝ) :
    black76_delta_call Φ F K σ T r - black76_delta_put Φ F K σ T r =
    Real.exp (-r * T) := by
  unfold black76_delta_call black76_delta_put
  ring

-- ============================================================
-- §3. Vanna tại ATM (F = K)
-- ============================================================

/-- Tại ATM (F = K): d2 = -(σ·√T / 2) < 0 -/
theorem vanna_sign_characterization
    (F σ T : ℝ)
    (hF : 0 < F) (hσ : 0 < σ) (hT : 0 < T) :
    black76_d2 F F σ T = -(σ * Real.sqrt T / 2) := by
  unfold black76_d2
  rw [d1_atm_positive F σ T hF hσ hT]
  ring
