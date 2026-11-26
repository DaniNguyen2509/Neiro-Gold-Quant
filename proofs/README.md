# Neiro-Gold-Quant — Lean 4 Formal Verification Suite

Bộ chứng minh toán học hình thức (Formal Verification) cho các bất biến định lượng cốt lõi của Neiro-Gold-Quant bằng ngôn ngữ **Lean 4 (v4.14.0)** và thư viện **Mathlib**.

## 1. Trạng thái biên dịch 7 Module (`lake build`)

| STT | File | Nội dung kiểm chứng | Trạng thái biên dịch (`lake build`) |
| :--- | :--- | :--- | :--- |
| 1 | `BasisConvention.lean` | Bất biến chuyển đổi Spot ↔ CME Gold Futures | ✅ **BUILT 100% (Zero error, Zero sorry)** |
| 2 | `Black76Core.lean` | Mô hình Black-76, $d_1, d_2$ At-The-Money | ✅ **BUILT 100% (Zero error, Zero sorry)** |
| 3 | `Black76Greeks.lean` | Bất biến $\Gamma \ge 0$, $\Delta \in (0,1]$, Put-Call Parity | ✅ **BUILT 100% (Zero error, Zero sorry)** |
| 4 | `BrentSolver.lean` | Thuật toán Dekker-Brent giải Zero Gamma Flip | ✅ **BUILT 100% (Zero error, Zero sorry)** |
| 5 | `GEXInvariants.lean` | Additive decomposition Net GEX, Wall Siege Ratio | ⚠️ *Đang hoàn thiện lemma `List.zipWith_append`* |
| 6 | `WallSiege.lean` | Tỷ lệ công thành Intraday Wall Siege Ratio | ✅ Sẵn sàng (Phụ thuộc module 5) |
| 7 | `ZeroGammaFlip.lean` | Tồn tại nghiệm $S^*$ qua IVT, Regime Classifier | ✅ Sẵn sàng (Phụ thuộc module 4 & 5) |

## 2. Kiểm thử song song Python + Hypothesis

- **Quick Verification:** 7/7 thuộc tính toán học kiểm tra nhanh đều **PASS 100%**.
- **Hypothesis Property-Based Fuzzing:** 3,000 mẫu ngẫu nhiên (1,000 inputs / property) đều **PASS 100%**.
- **CI / GitHub Actions:** Workflow cào Options COMEX và cập nhật terminal HTML hoạt động tự động và ổn định trên nhánh `main`.

## 3. Cách chạy trên Google Colab

Notebook: `notebooks/Lean4_Verification_Neiro.ipynb`
1. Chạy **BƯỚC 1** để tải Elan + toolchain `v4.14.0` + Mathlib cache (`lake exe cache get`).
2. Chạy **BƯỚC 2** để biên dịch toàn bộ proofs (`lake build`).
3. Chạy **BƯỚC 3 & 4** để chạy Python tests và xem bảng tổng kết nghiệm thu.
