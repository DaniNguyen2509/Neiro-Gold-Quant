/-
  Black76Core.lean — Neiro-Gold-Quant Formal Verification
  =========================================================
  Chứng minh các bất biến cốt lõi của mô hình Black-76
  dùng cho định giá quyền chọn Vàng COMEX (GCZ26).

  Định nghĩa chính:
    d1(F, K, σ, T) = (ln(F/K) + 0.5·σ²·T) / (σ·√T)
    d2(F, K, σ, T) = d1 - σ·√T

  Quy ước:
    F > 0  : Giá Futures hiện tại (CME Gold GC)
    K > 0  : Strike price
    σ > 0  : Implied Volatility (annualized)
    T > 0  : Time to expiry (years)
    r ≥ 0  : Risk-free rate
-/

import Mathlib.Analysis.SpecialFunctions.Log.Basic
import Mathlib.Analysis.SpecialFunctions.Pow.Real
import Mathlib.Analysis.SpecialFunctions.Sqrt

open Real

-- ============================================================
-- §1. Định nghĩa cơ sở Black-76
-- ============================================================

/-- d1 trong Black-76: tham số định giá quyền chọn -/
noncomputable def black76_d1 (F K σ T : ℝ) : ℝ :=
  (Real.log (F / K) + 0.5 * σ ^ 2 * T) / (σ * Real.sqrt T)

/-- d2 = d1 - σ·√T -/
noncomputable def black76_d2 (F K σ T : ℝ) : ℝ :=
  black76_d1 F K σ T - σ * Real.sqrt T

-- ============================================================
-- §2. Bất biến cơ bản
-- ============================================================

/-- Khi F = K (At-The-Money), d1 = 0.5·σ·√T > 0
    Ý nghĩa trading: ATM Call luôn có d1 dương nhỏ → Delta nhỉnh hơn 0.5 -/
theorem d1_atm_positive (σ T : ℝ) (hσ : 0 < σ) (hT : 0 < T) :
    black76_d1 1 1 σ T = 0.5 * σ * Real.sqrt T := by
  simp [black76_d1, Real.log_one, Real.div_eq_iff]
  ring_nf
  rw [Real.sqrt_pos.mpr hT |>.ne']
  field_simp
  ring

/-- d2 = d1 - σ·√T: quan hệ identity -/
theorem d2_eq_d1_minus_vol_time (F K σ T : ℝ) :
    black76_d2 F K σ T = black76_d1 F K σ T - σ * Real.sqrt T := by
  simp [black76_d2]

/-- Khi T → 0⁺ (đáo hạn), nếu F > K thì d1 → +∞
    Ý nghĩa: Deep ITM call về 1 khi sắp đáo hạn -/
theorem d1_itm_dominates (F K : ℝ) (hF : 0 < F) (hK : 0 < K) (hFK : K < F) :
    ∀ ε > 0, ∃ δ > 0, ∀ T : ℝ, 0 < T → T < δ →
    1 / Real.sqrt T ≤ black76_d1 F K 1 T + ε := by
  intro ε hε
  use ε ^ 2
  constructor
  · positivity
  · intro T hT hTd
    simp [black76_d1]
    sorry -- Proof sketch: log(F/K) > 0 dominates as T→0

-- ============================================================
-- §3. Lemma hỗ trợ: Normal PDF N'(d) ≥ 0
-- ============================================================

/-- Normal PDF: φ(x) = (1/√(2π)) · exp(-x²/2) ≥ 0 với mọi x ∈ ℝ -/
noncomputable def normalPDF (x : ℝ) : ℝ :=
  (1 / Real.sqrt (2 * Real.pi)) * Real.exp (- x ^ 2 / 2)

theorem normalPDF_nonneg (x : ℝ) : 0 ≤ normalPDF x := by
  unfold normalPDF
  apply mul_nonneg
  · apply div_nonneg
    · norm_num
    · apply Real.sqrt_nonneg
  · exact le_of_lt (Real.exp_pos _)

-- ============================================================
-- §4. Normal CDF qua erf (theo thoả thuận trong spec)
--     Φ(x) := (1 + erf(x / √2)) / 2
-- ============================================================

/-- Normal CDF định nghĩa qua hàm erf của Mathlib4 -/
noncomputable def normalCDF (x : ℝ) : ℝ :=
  (1 + Real.erf (x / Real.sqrt 2)) / 2

/-- Normal CDF nằm trong [0, 1] -/
theorem normalCDF_range (x : ℝ) : 0 ≤ normalCDF x ∧ normalCDF x ≤ 1 := by
  constructor
  · unfold normalCDF
    have h := Real.neg_one_le_erf (x / Real.sqrt 2)
    linarith
  · unfold normalCDF
    have h := Real.erf_le_one (x / Real.sqrt 2)
    linarith

/-- Φ(0) = 0.5: Đối xứng của phân phối chuẩn -/
theorem normalCDF_zero : normalCDF 0 = 1 / 2 := by
  unfold normalCDF
  simp [Real.erf_zero]
  ring
