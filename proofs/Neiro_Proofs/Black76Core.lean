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
import Mathlib.Tactic

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
theorem d1_atm_positive (F σ T : ℝ) (hF : 0 < F) (hσ : 0 < σ) (hT : 0 < T) :
    black76_d1 F F σ T = 0.5 * σ * Real.sqrt T := by
  unfold black76_d1
  rw [div_self (ne_of_gt hF), Real.log_one, zero_add]
  have hsqrt_pos : 0 < Real.sqrt T := Real.sqrt_pos.mpr hT
  have hdenom : σ * Real.sqrt T ≠ 0 := mul_ne_zero (ne_of_gt hσ) (ne_of_gt hsqrt_pos)
  have h_num : 0.5 * σ ^ 2 * T = (0.5 * σ * Real.sqrt T) * (σ * Real.sqrt T) := by
    rw [← Real.sq_sqrt (le_of_lt hT)]
    ring
  rw [h_num, mul_div_cancel_right₀ _ hdenom]

/-- d2 = d1 - σ·√T: quan hệ identity -/
theorem d2_eq_d1_minus_vol_time (F K σ T : ℝ) :
    black76_d2 F K σ T = black76_d1 F K σ T - σ * Real.sqrt T := by
  rfl

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
    · exact Real.sqrt_nonneg _
  · exact le_of_lt (Real.exp_pos _)

theorem normalPDF_pos (x : ℝ) : 0 < normalPDF x := by
  unfold normalPDF
  apply mul_pos
  · apply div_pos
    · norm_num
    · exact Real.sqrt_pos.mpr (by positivity)
  · exact Real.exp_pos _

-- ============================================================
-- §4. Giao diện chuẩn cho Normal CDF Φ(x)
--     (Mathlib v4.14.0 không export sẵn Real.erf, nên đóng gói
--      tiên đề xác suất chuẩn của Φ thành structure có kiểm soát)
-- ============================================================

/-- Hợp đồng toán học của hàm phân phối chuẩn tắc Φ(x) -/
structure NormalCDFSpec where
  cdf : ℝ → ℝ
  cdf_pos : ∀ x : ℝ, 0 < cdf x
  cdf_le_one : ∀ x : ℝ, cdf x ≤ 1
  cdf_zero : cdf 0 = 1 / 2

theorem normalCDF_range (spec : NormalCDFSpec) (x : ℝ) :
    0 ≤ spec.cdf x ∧ spec.cdf x ≤ 1 :=
  ⟨le_of_lt (spec.cdf_pos x), spec.cdf_le_one x⟩
