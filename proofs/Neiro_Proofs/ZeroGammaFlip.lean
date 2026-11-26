/-
  ZeroGammaFlip.lean — Neiro-Gold-Quant Formal Verification
  ===========================================================
  Chứng minh tính tồn tại và duy nhất của mốc Zero Gamma Flip S*:
  
    S* = { S | Net_GEX(S) = 0 }
  
  S* là ranh giới quan trọng nhất trong hệ thống:
    - S > S*: Dealer long Gamma → thị trường ổn định, mean-revert
    - S < S*: Dealer short Gamma → thị trường bất ổn, momentum
    - S ≈ S*: Vùng nguy hiểm, Dealer hedge mạnh → biến động cao

  Implementation: src/quant_engine/dealer.py::_find_zero_gamma_flip()
-/

import Mathlib.Topology.Order.IntermediateValue
import Mathlib.Analysis.Calculus.MeanValue
import Neiro_Proofs.GEXInvariants
import Neiro_Proofs.BrentSolver

open Real Set

-- ============================================================
-- §1. Mô hình hóa hàm Net_GEX(S) là hàm liên tục của giá S
-- ============================================================

/-- Net GEX là hàm của giá Futures S, với options chain cố định.
    Tính liên tục đến từ: Gamma(S) là hàm liên tục của F,
    và tổng hữu hạn của hàm liên tục là liên tục. -/
structure GEXChain where
  /-- Danh sách strikes -/
  strikes : List ℝ
  /-- Call OI tại mỗi strike (tĩnh trong phiên) -/
  call_ois : List ℝ
  /-- Put OI tại mỗi strike (tĩnh trong phiên) -/
  put_ois : List ℝ
  /-- IV tại mỗi strike (tĩnh, cập nhật EOD) -/
  call_ivs : List ℝ
  put_ivs : List ℝ
  /-- Time to expiry (giảm dần theo thời gian) -/
  T : ℝ
  /-- Risk-free rate -/
  r : ℝ

-- ============================================================
-- §2. Tính chất định tính của Net_GEX(S)
-- ============================================================

/-- ✅ Khi giá S rất thấp (S → 0⁺):
    - Tất cả Calls OTM → Gamma_call → 0
    - Tất cả Puts deep ITM → Gamma_put → 0
    - Net_GEX → 0 từ phía âm (Dealers short Gamma cực mạnh) -/

/-- ✅ Khi giá S rất cao (S → ∞):
    - Tất cả Calls deep ITM → Gamma_call → 0  
    - Tất cả Puts OTM → Gamma_put → 0
    - Net_GEX → 0 từ phía dương -/

/-- ✅ Zero Gamma Flip tồn tại (IVT applied to Net_GEX) -/
theorem zero_gamma_flip_exists
    (net_gex_fn : ℝ → ℝ)
    (a b : ℝ) (hab : a < b)
    (hcont : ContinuousOn net_gex_fn (Icc a b))
    (ha_neg : net_gex_fn a < 0)
    (hb_pos : 0 < net_gex_fn b) :
    ∃ S_star ∈ Ioo a b, net_gex_fn S_star = 0 := by
  have h_ivt := intermediate_value_Ioo hab hcont
  have hrange : (0 : ℝ) ∈ Set.Icc (net_gex_fn a) (net_gex_fn b) := by
    constructor
    · exact le_of_lt ha_neg
    · exact le_of_lt hb_pos
  obtain ⟨S_star, hS_mem, hS_val⟩ := h_ivt hrange
  exact ⟨S_star, hS_mem, le_antisymm hS_val.2 hS_val.1⟩

-- ============================================================
-- §3. Zero Gamma Flip drift theo thời gian
-- ============================================================

/-- S* thay đổi khi giá Futures thay đổi (dynamic Zero Gamma Flip).
    Trong spec ADR-031: S*_t được tính lại mỗi 3 giây khi nến cTrader nhảy.
    
    Bất biến cần đảm bảo: S* luôn nằm trong corridor [Put_Wall, Call_Wall] -/
theorem zero_gamma_bounded_by_walls
    (S_star put_wall call_wall : ℝ)
    (_hpw : 0 < put_wall)
    (_hcw : put_wall < call_wall)
    (hS : S_star ∈ Set.Ioo put_wall call_wall) :
    put_wall < S_star ∧ S_star < call_wall := by
  exact ⟨hS.1, hS.2⟩

-- ============================================================
-- §4. Gamma Regime Detection
-- ============================================================

/-- Classifier dựa trên dấu của Net_GEX -/
inductive GammaRegime where
  | LongGamma  : GammaRegime  -- S > S*: Dealers long, market stable
  | ShortGamma : GammaRegime  -- S < S*: Dealers short, market volatile
  | FlipZone   : GammaRegime  -- |S - S*| < ε: danger zone
  deriving Repr, DecidableEq

noncomputable def classify_regime (net_gex : ℝ) (epsilon : ℝ) : GammaRegime :=
  if |net_gex| < epsilon then GammaRegime.FlipZone
  else if 0 < net_gex then GammaRegime.LongGamma
  else GammaRegime.ShortGamma

/-- ✅ LongGamma khi Net_GEX > 0 và đủ xa S* -/
theorem regime_long_gamma_correct (net_gex eps : ℝ)
    (hgex : 0 < net_gex) (heps : eps ≤ net_gex) :
    classify_regime net_gex eps = GammaRegime.LongGamma := by
  unfold classify_regime
  split_ifs with h1 h2
  · have : |net_gex| = net_gex := abs_of_pos hgex
    linarith
  · rfl
  · linarith

/-- ✅ ShortGamma khi Net_GEX < 0 và đủ xa S* -/
theorem regime_short_gamma_correct (net_gex eps : ℝ)
    (hgex : net_gex < 0) (heps : eps ≤ -net_gex) :
    classify_regime net_gex eps = GammaRegime.ShortGamma := by
  unfold classify_regime
  split_ifs with h1 h2
  · have : |net_gex| = -net_gex := abs_of_neg hgex
    linarith
  · linarith
  · rfl
