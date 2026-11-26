/-
  WallSiege.lean — Neiro-Gold-Quant Formal Verification
  =======================================================
  Chứng minh các bất biến của Wall Siege Ratio và cơ chế cảnh báo:

    SiegeRatio = Volume / OI   (intraday pressure measure)
    SiegeVelocity = ΔSiegeRatio / Δt

  Lý do dùng Volume/OI thay vì Volume tuyệt đối:
    - OI tĩnh trong phiên (CME Clearing House chốt sau EOD)
    - Volume/OI > 1 nghĩa là "toàn bộ OI nền đã được giao dịch lại"
    - Chuẩn hóa so sánh được giữa các strikes có OI khác nhau

  Implementation: src/quant_engine/dealer.py (Wall dataclass, siege_ratio)
-/

import Mathlib.Order.Bounds.Basic
import Mathlib.Algebra.Order.Field.Basic
import Neiro_Proofs.GEXInvariants

open Real

-- ============================================================
-- §1. Wall Siege Ratio — Bất biến cơ bản
-- ============================================================

/-- Siege Ratio đã được định nghĩa trong GEXInvariants.lean:
    wall_siege_ratio (volume oi : ℝ) = volume / oi -/

/-- ✅ Nếu Volume = OI thì SiegeRatio = 1.0 (đúng ngưỡng cảnh báo) -/
theorem siege_ratio_at_full_capacity (oi : ℝ) (hoi : 0 < oi) :
    wall_siege_ratio oi oi = 1 := by
  unfold wall_siege_ratio
  exact div_self (ne_of_gt hoi)

/-- ✅ Siege Ratio > 1 khi Volume vượt OI (Under Siege!) -/
theorem siege_ratio_above_one (volume oi : ℝ)
    (hvol : oi < volume) (hoi : 0 < oi) :
    1 < wall_siege_ratio volume oi := by
  unfold wall_siege_ratio
  have h_eq : 1 = oi / oi := (div_self (ne_of_gt hoi)).symm
  rw [h_eq]
  exact div_lt_div_of_pos_right hvol hoi

/-- ✅ Siege Ratio đơn điệu tăng theo volume -/
theorem siege_ratio_monotone (v1 v2 oi : ℝ)
    (hv : v1 ≤ v2) (hoi : 0 < oi) :
    wall_siege_ratio v1 oi ≤ wall_siege_ratio v2 oi :=
  siege_ratio_monotone_volume v1 v2 oi hv hoi

-- ============================================================
-- §2. Siege Velocity (tốc độ tăng Siege Ratio)
-- ============================================================

/-- Siege Velocity: đạo hàm của SiegeRatio theo thời gian -/
noncomputable def siege_velocity (vol_t1 vol_t2 oi dt : ℝ) : ℝ :=
  (wall_siege_ratio vol_t2 oi - wall_siege_ratio vol_t1 oi) / dt

/-- ✅ Siege Velocity ≥ 0 khi Volume chỉ tăng (cumulative intraday volume) -/
theorem siege_velocity_nonneg
    (vol_t1 vol_t2 oi dt : ℝ)
    (hvol : vol_t1 ≤ vol_t2)
    (hoi : 0 < oi)
    (hdt : 0 < dt) :
    0 ≤ siege_velocity vol_t1 vol_t2 oi dt := by
  unfold siege_velocity
  apply div_nonneg _ (le_of_lt hdt)
  have hmon := siege_ratio_monotone vol_t1 vol_t2 oi hvol hoi
  linarith

-- ============================================================
-- §3. Alert Threshold Invariants
-- ============================================================

/-- Ngưỡng cảnh báo theo spec ADR-031: giá trong vòng $4.0 của Wall -/
def WALL_ALERT_DISTANCE : ℝ := 4.0

/-- ✅ Nếu giá trong vòng ALERT_DISTANCE của Wall → trigger cảnh báo -/
def wall_is_threatened (current_price wall_strike : ℝ) : Prop :=
  |current_price - wall_strike| < WALL_ALERT_DISTANCE

/-- ✅ Threat là đối xứng: giá tiếp cận từ trên hay dưới đều cảnh báo -/
theorem wall_threat_symmetric (p w : ℝ) :
    wall_is_threatened p w ↔ wall_is_threatened w p := by
  unfold wall_is_threatened
  rw [abs_sub_comm]

/-- ✅ Nếu giá trùng Wall → luôn bị threatened (|0| < 4) -/
theorem wall_threat_at_strike (w : ℝ) : wall_is_threatened w w := by
  unfold wall_is_threatened
  simp [WALL_ALERT_DISTANCE]
  norm_num

-- ============================================================
-- §4. OI Bất biến trong phiên (CME Rule)
-- ============================================================

/-- OI là bất biến trong phiên giao dịch intraday.
    Chỉ được phép cập nhật sau khi CME Clearing House chốt EOD.
    
    Tính chất này đảm bảo SiegeRatio có denominator ổn định trong phiên,
    tránh denominator jumping gây false signals. -/
def oi_is_session_static (oi_t1 oi_t2 : ℝ) (same_session : Prop) : Prop :=
  same_session → oi_t1 = oi_t2
