# Neiro-Gold-Quant — Lean 4 Formal Verification Suite

Bộ chứng minh toán học hình thức (Formal Verification) cho các bất biến định lượng cốt lõi của Neiro-Gold-Quant bằng ngôn ngữ **Lean 4 (v4.14.0)** và thư viện **Mathlib**.

## 1. Cấu trúc Suite (`proofs/Neiro_Proofs/`)

1. **`BasisConvention.lean`**: Xác thực bất biến đồng bộ 100% giá CME Gold Futures (GC / GCZ26), chứng minh độ lệch Basis và quan hệ biên sai số.
2. **`Black76Core.lean`**: Mô hình Black-76 cho COMEX Gold Futures Options, chứng minh tính đơn điệu của hàm $d_1, d_2$ và cấu trúc Normal CDF Axiomatic Spec.
3. **`Black76Greeks.lean`**: Bất biến Gamma $\Gamma \ge 0$, Vega $\mathcal{V} > 0$ của quyền chọn mua/bán theo Black-76.
4. **`BrentSolver.lean`**: Thuật toán Dekker-Brent giải nghiệm số liên tục cho mốc Zero Gamma Flip ($S^*$), chứng minh Root Bracketing Invariant, Bisection shrinkage và stopping criterion.
5. **`GEXInvariants.lean`**: Bất biến Gamma Exposure (GEX), Call Wall / Put Wall Microstructure.
6. **`WallSiege.lean`**: Tỷ lệ công thành Intraday Wall Siege Ratio $\text{Siege} = \frac{\text{Volume}}{\text{OI}}$, kiểm soát rủi ro đột phá thành trì.
7. **`ZeroGammaFlip.lean`**: Định lý giá trị trung gian (IVT) chứng minh sự tồn tại của mốc Zero Gamma Flip ($S^*$) phân tách hai trạng thái Long Gamma và Short Gamma.

## 2. Cách biên dịch & chạy kiểm chứng

### Trên Google Colab (Cloud-First):
Mở notebook: `notebooks/Lean4_Verification_Neiro.ipynb`
1. Cài đặt Elan & Lean 4 toolchain `v4.14.0`
2. Tải pre-built Mathlib cache (`lake exe cache get`)
3. Biên dịch toàn bộ 7 module:
   ```bash
   cd proofs && lake build
   ```
4. Chạy kiểm chứng song song Python + Hypothesis Property-Based Fuzz Tests (3,000+ test cases).
