/-
  GEXInvariants.lean — Neiro-Gold-Quant Formal Verification
  ===========================================================
  Chứng minh các bất biến của Gamma Exposure (GEX):

    GEX_i = OI_i × Gamma_i × Multiplier
    Net_GEX = Σ_i(Call_GEX_i) - Σ_i(Put_GEX_i)

  Bất biến quan trọng:
    1. GEX_i ≥ 0  (vì OI ≥ 0 và Gamma ≥ 0)
    2. Net_GEX có thể âm hoặc dương
    3. Net_GEX là tuyến tính (additive decomposition)
    4. Wall Siege Ratio = Volume / OI ≥ 0 khi OI > 0
-/

import Mathlib.Algebra.BigOperators.Group.Finset
import Mathlib.Data.List.Basic
import Neiro_Proofs.Black76Greeks

open BigOperators Real

-- ============================================================
-- §1. GEX cho từng strike
-- ============================================================

/-- Multiplier của CME Gold Futures: $100 per point -/
def CME_GOLD_MULTIPLIER : ℝ := 100.0

/-- GEX của một strike (Call hoặc Put):
    GEX = OI × Gamma × Multiplier
    
    Đây là lượng hàng Dealer cần hedge khi giá di chuyển 1 điểm. -/
noncomputable def gex_at_strike (oi : ℝ) (gamma : ℝ) : ℝ :=
  oi * gamma * CME_GOLD_MULTIPLIER

/-- ✅ GEX ≥ 0 khi OI ≥ 0 và Gamma ≥ 0 -/
theorem gex_nonneg (oi gamma : ℝ) (hoi : 0 ≤ oi) (hgamma : 0 ≤ gamma) :
    0 ≤ gex_at_strike oi gamma := by
  unfold gex_at_strike CME_GOLD_MULTIPLIER
  exact mul_nonneg (mul_nonneg hoi hgamma) (by norm_num)

-- ============================================================
-- §2. Net GEX = Σ Call_GEX - Σ Put_GEX
-- ============================================================

/-- Net GEX trên toàn bộ options chain:
    Dương = Dealer long Gamma → thị trường ổn định (mean-revert)
    Âm   = Dealer short Gamma → thị trường bất ổn (trend-following) -/
noncomputable def net_gex
    (call_ois call_gammas put_ois put_gammas : List ℝ) : ℝ :=
  let call_gex := (call_ois.zipWith (· * ·) call_gammas).map (· * CME_GOLD_MULTIPLIER)
  let put_gex  := (put_ois.zipWith (· * ·) put_gammas).map (· * CME_GOLD_MULTIPLIER)
  call_gex.sum - put_gex.sum

/-- ✅ Tính chất tuyến tính: Net GEX = Call GEX sum - Put GEX sum
    Cho phép tính incremental khi thêm/bỏ một strike -/
theorem net_gex_additive
    (c_ois c_gs p_ois p_gs : List ℝ)
    (c_ois' c_gs' p_ois' p_gs' : List ℝ)
    (hc : c_ois.length = c_gs.length)
    (hp : p_ois.length = p_gs.length) :
    net_gex (c_ois ++ c_ois') (c_gs ++ c_gs') (p_ois ++ p_ois') (p_gs ++ p_gs') =
    net_gex c_ois c_gs p_ois p_gs +
    net_gex c_ois' c_gs' p_ois' p_gs' := by
  unfold net_gex
  dsimp only
  rw [List.zipWith_append hc, List.zipWith_append hp]
  simp only [List.map_append, List.sum_append]
  ring

/-- ✅ Net GEX = 0 khi options chain rỗng -/
theorem net_gex_empty : net_gex [] [] [] [] = 0 := by
  simp [net_gex]

-- ============================================================
-- §3. Wall Siege Ratio
-- ============================================================

/-- Wall Siege Ratio: đo áp lực công phá thành trì intraday
    
    Lý do dùng Volume/OI thay vì Volume thuần:
    - OI là "nền" tĩnh (chốt sau phiên bởi CME Clearing House)
    - Volume/OI > 1 → khối lượng giao dịch vượt OI nền → áp lực cực mạnh
    - Không thể dùng Volume tuyệt đối vì OI ở mỗi strike khác nhau -/
noncomputable def wall_siege_ratio (volume oi : ℝ) : ℝ :=
  volume / oi

/-- ✅ Siege Ratio ≥ 0 khi volume ≥ 0 và OI > 0 -/
theorem siege_ratio_nonneg (volume oi : ℝ) (hvol : 0 ≤ volume) (hoi : 0 < oi) :
    0 ≤ wall_siege_ratio volume oi := by
  unfold wall_siege_ratio
  exact div_nonneg hvol (le_of_lt hoi)

/-- ✅ Siege Ratio bằng 0 khi không có volume (không hoạt động) -/
theorem siege_ratio_zero_when_no_volume (oi : ℝ) (_hoi : 0 < oi) :
    wall_siege_ratio 0 oi = 0 := by
  simp [wall_siege_ratio]

/-- Siege ratio tăng tuyến tính với volume (ceteris paribus) -/
theorem siege_ratio_monotone_volume (v1 v2 oi : ℝ)
    (hv : v1 ≤ v2) (hoi : 0 < oi) :
    wall_siege_ratio v1 oi ≤ wall_siege_ratio v2 oi := by
  unfold wall_siege_ratio
  exact div_le_div_of_nonneg_right hv (le_of_lt hoi)
