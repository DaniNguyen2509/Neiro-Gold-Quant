/-
  BasisConvention.lean — Neiro-Gold-Quant Formal Verification
  =============================================================
  Chứng minh tính nhất quán (consistency) của quy ước Basis:

    basis := spot_price - futures_price   (CME/LBMA Standard)
    
  Từ đó suy ra:
    spot = futures + basis
    futures = spot - basis

  Quy ước dấu:
    Contango (futures > spot)     → basis < 0
    Backwardation (futures < spot) → basis > 0

  Đây là quy ước bắt buộc trong toàn bộ Neiro-Gold-Quant.
  Tham chiếu: src/quant_engine/basis.py

  CRITICAL: Nếu dùng sai dấu (basis = futures - spot), toàn bộ
  conversion spot↔futures sẽ sai chiều → sai mức Entry/SL/TP.
-/

import Mathlib.Data.Real.Basic
import Mathlib.Tactic

-- ============================================================
-- §1. Định nghĩa Basis Convention
-- ============================================================

/-- Basis theo chuẩn CME/LBMA -/
noncomputable def basis (spot futures : ℝ) : ℝ :=
  spot - futures

-- ============================================================
-- §2. Round-Trip Identity
-- ============================================================

/-- ✅ ROUND-TRIP 1: spot = futures + basis
    Từ definition: basis = spot - futures
    Suy ra:        spot = futures + (spot - futures) = spot ✓ -/
theorem spot_eq_futures_plus_basis (spot futures : ℝ) :
    spot = futures + basis spot futures := by
  unfold basis; ring

/-- ✅ ROUND-TRIP 2: futures = spot - basis
    Từ definition: basis = spot - futures
    Suy ra:        futures = spot - (spot - futures) = futures ✓ -/
theorem futures_eq_spot_minus_basis (spot futures : ℝ) :
    futures = spot - basis spot futures := by
  unfold basis; ring

/-- ✅ BASIS ANTISYMMETRY: basis(spot, futures) = -basis(futures, spot)
    Đảm bảo không nhầm chiều tính -/
theorem basis_antisymmetric (spot futures : ℝ) :
    basis spot futures = -basis futures spot := by
  unfold basis; ring

/-- ✅ IDENTITY: basis(x, x) = 0 (khi spot = futures, basis = 0) -/
theorem basis_zero_when_equal (x : ℝ) : basis x x = 0 := by
  unfold basis; ring

-- ============================================================
-- §3. Contango & Backwardation Sign Convention
-- ============================================================

/-- ✅ Contango: futures > spot → basis < 0 -/
theorem contango_negative_basis (spot futures : ℝ)
    (h : spot < futures) :
    basis spot futures < 0 := by
  unfold basis; linarith

/-- ✅ Backwardation: futures < spot → basis > 0 -/
theorem backwardation_positive_basis (spot futures : ℝ)
    (h : futures < spot) :
    0 < basis spot futures := by
  unfold basis; linarith

/-- ✅ Fair value: futures = spot → basis = 0 -/
theorem fair_value_zero_basis (price : ℝ) :
    basis price price = 0 := basis_zero_when_equal price

-- ============================================================
-- §4. Conversion Functions Correctness
-- ============================================================

/-- Chuyển đổi từ Futures sang Spot -/
noncomputable def futures_to_spot (futures_price basis_val : ℝ) : ℝ :=
  futures_price + basis_val

/-- Chuyển đổi từ Spot sang Futures -/
noncomputable def spot_to_futures (spot_price basis_val : ℝ) : ℝ :=
  spot_price - basis_val

/-- ✅ futures_to_spot và spot_to_futures là nghịch đảo nhau -/
theorem conversion_round_trip (price basis_val : ℝ) :
    spot_to_futures (futures_to_spot price basis_val) basis_val = price := by
  unfold futures_to_spot spot_to_futures; ring

theorem conversion_round_trip_reverse (price basis_val : ℝ) :
    futures_to_spot (spot_to_futures price basis_val) basis_val = price := by
  unfold futures_to_spot spot_to_futures; ring

/-- ✅ Nếu áp dụng basis đúng chuẩn thì spot = futures_to_spot(futures, basis(spot, futures)) -/
theorem spot_recovery_via_conversion (spot futures : ℝ) :
    futures_to_spot futures (basis spot futures) = spot := by
  unfold futures_to_spot basis; ring

/-- ✅ Nếu áp dụng basis đúng chuẩn thì futures = spot_to_futures(spot, basis(spot, futures)) -/
theorem futures_recovery_via_conversion (spot futures : ℝ) :
    spot_to_futures spot (basis spot futures) = futures := by
  unfold spot_to_futures basis; ring

-- ============================================================
-- §5. Sanity Check: Basis Tolerance (5% rule)
-- ============================================================

/-- Theo spec: basis hợp lệ khi |basis| ≤ 5% × futures_price
    (_BASIS_REL_TOLERANCE = 0.05 trong basis.py) -/
def basis_within_tolerance (spot futures : ℝ) : Prop :=
  |basis spot futures| ≤ 0.05 * futures

/-- ✅ Nếu basis trong tolerance thì spot và futures gần nhau -/
theorem within_tolerance_implies_close (spot futures : ℝ)
    (hfut : 0 < futures)
    (htol : basis_within_tolerance spot futures) :
    |spot - futures| ≤ 0.05 * futures := by
  unfold basis_within_tolerance basis at htol
  exact htol
