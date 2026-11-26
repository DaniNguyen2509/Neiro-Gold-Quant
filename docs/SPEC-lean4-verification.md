# Spec: Lean 4 Formal Verification System — Neiro-Gold-Quant
> **Phiên bản:** v1.0 — 2026-11-26  
> **Mục tiêu kép:** (1) Chứng minh công thức đúng về lý thuyết toán học, (2) Đảm bảo Python implementation khớp chính xác với spec toán học đã được Lean 4 xác nhận.  
> **Nền tảng vận hành:** Google Colab (Cloud-first, Zero-install trên máy local, khai thác GPU/TPU nếu cần).  
> **Zero-Waste Mandate:** Không để lại file build artifact trong repo. Chỉ commit file `.lean` và Colab notebook.

---

## 1. MỤC TIÊU & TRIẾT LÝ

### 1.1. Vấn đề cần giải quyết

Hệ thống Neiro-Gold-Quant triển khai nhiều công thức định lượng phức tạp (Black-76, Dekker-Brent, GEX) trực tiếp trong Python và JavaScript. Hiện tại:
- **Rủi ro lý thuyết:** Không có bằng chứng hình thức rằng các công thức toán học là đúng (e.g., Black-76 Gamma không âm, Brent luôn hội tụ).
- **Rủi ro implementation:** Code Python có thể lệch khỏi spec toán học do lỗi đặc tả hoặc edge case.
- **Hậu quả trading:** Sai số tính toán Greeks → sai Wall → tín hiệu giao dịch sai → thua lỗ thực tế.

### 1.2. Giải pháp

Xây dựng **hệ thống chứng minh hình thức (Formal Verification)** dùng ngôn ngữ Lean 4 + thư viện Mathlib4, chạy hoàn toàn trên Google Colab để:
1. **Chứng minh tính đúng đắn toán học** của từng công thức (compiler Lean = oracle tuyệt đối).
2. **Sinh ra Property-Based Tests** từ các định lý đã chứng minh để kiểm tra code Python.

### 1.3. Thành công trông như thế nào

- Lean compiler chấp nhận ✅ toàn bộ `.lean` proof files (không có `sorry`).
- Mỗi theorem Lean tương ứng với một property test Python pass 100%.
- Colab notebook có thể chạy end-to-end từ đầu với 0 lỗi.

---

## 2. CAPABILITY MAP

```
Module id          Trách nhiệm                              Phụ thuộc
─────────────────────────────────────────────────────────────────────────────
lean-foundation    Cài Lean 4 + Mathlib4 trên Colab;        —
                   scaffolding project, test "hello proof"

black76-proofs     Chứng minh Black-76 Greeks:              lean-foundation
                   Gamma ≥ 0, Delta ∈ (0,1], Vanna, Charm

brent-proofs       Chứng minh Dekker-Brent hội tụ:          lean-foundation
                   root bracketing, convergence rate

gex-proofs         Chứng minh GEX invariants:               black76-proofs
                   Net GEX = Σ(Call GEX - Put GEX),
                   Wall Siege Ratio = Volume / OI ≥ 0

basis-proofs       Chứng minh Basis Convention:             lean-foundation
                   spot = futures + basis, signed invariant

python-bridge      Sinh property tests từ Lean theorems;    tất cả proofs
                   kiểm tra Python code khớp Lean
```

**Build order:** `lean-foundation` → (`black76-proofs`, `brent-proofs`, `basis-proofs`) → `gex-proofs` → `python-bridge`

---

## 3. CÔNG THỨC CẦN CHỨNG MINH (THEO THỨ TỰ ƯU TIÊN)

### P1 — Black-76 Greeks & GEX

| Công thức | Điều cần chứng minh | File Lean |
|---|---|---|
| `d1 = (ln(F/K) + 0.5σ²T) / (σ√T)` | Hội tụ khi F→K | `Black76Core.lean` |
| `Gamma = e^(-rT) × N'(d1) / (F×σ×√T)` | **Gamma ≥ 0** với mọi F,K,σ,T > 0 | `Black76Greeks.lean` |
| `Delta_Call ∈ (0, 1]` | Bounded invariant | `Black76Greeks.lean` |
| `GEX_i = OI_i × Gamma_i × Multiplier` | GEX ≥ 0 (vì OI ≥ 0, Gamma ≥ 0) | `GEXInvariants.lean` |
| `Net_GEX = Σ Call_GEX_i - Σ Put_GEX_i` | Linearity, additive decomposition | `GEXInvariants.lean` |

### P2 — Zero Gamma Flip (Dekker-Brent)

| Công thức | Điều cần chứng minh | File Lean |
|---|---|---|
| `f(a) × f(b) < 0` | Root bracketing invariant | `BrentSolver.lean` |
| `|b - a| → 0` | Convergence (superlinear) | `BrentSolver.lean` |
| `S* = argmin |Net_GEX(S)|` | Existence of zero crossing | `ZeroGammaFlip.lean` |

### P3 — Wall Siege Ratio

| Công thức | Điều cần chứng minh | File Lean |
|---|---|---|
| `SiegeRatio = Volume / OI` | `OI > 0 → SiegeRatio ≥ 0` | `WallSiege.lean` |
| `SiegeRatio ∈ [0, ∞)` | Không âm vô điều kiện | `WallSiege.lean` |

### P4 — Basis Convention

| Công thức | Điều cần chứng minh | File Lean |
|---|---|---|
| `basis = spot - futures` | Signed: Contango ⟹ basis < 0 | `BasisConvention.lean` |
| `spot = futures + basis` | Consistency: round-trip identity | `BasisConvention.lean` |
| `futures = spot - basis` | Inverse bijection | `BasisConvention.lean` |

---

## 4. TECH STACK

| Layer | Công nghệ | Lý do chọn |
|---|---|---|
| Proof Language | **Lean 4** + **Mathlib4** | Standard for formal math; Google DeepMind đã dùng (AlphaProof) |
| Proof Environment | **Google Colab** (Python + bash cells) | Zero-install, Cloud-first, free GPU |
| Python Bridge | **hypothesis** (property-based testing) | Translate Lean theorems → Python fuzzing |
| CI (optional) | Colab-as-script / GitHub Actions | Có thể trigger từ repo nếu cần sau này |

---

## 5. CẤU TRÚC FILE

```
Neiro-Gold-Quant/
├── proofs/                          ← CHỈ file .lean (không có build artifacts)
│   ├── lakefile.toml                ← Lean project config (khai báo Mathlib4)
│   ├── Black76Core.lean
│   ├── Black76Greeks.lean
│   ├── GEXInvariants.lean
│   ├── BrentSolver.lean
│   ├── ZeroGammaFlip.lean
│   ├── WallSiege.lean
│   └── BasisConvention.lean
│
├── notebooks/                       ← Colab notebooks
│   └── Lean4_Verification_Neiro.ipynb  ← Notebook chạy toàn bộ trên Colab
│
└── tests/
    └── test_formal_properties.py    ← Property-based tests sinh từ Lean theorems
```

> **Zero-Waste:** `.lake/` (build cache của Lean) PHẢI thêm vào `.gitignore`. Tổng file `.lean` ước tính < 50KB.

---

## 6. BOUNDARIES

**Always do:**
- Mỗi theorem Lean phải có docstring giải thích toán học bằng tiếng Việt.
- Không dùng `sorry` trong file proof (sorry = bỏ qua chứng minh, vô nghĩa với verification).
- Mỗi Lean theorem phải có ít nhất 1 property test Python tương ứng.

**Ask first (phải hỏi owner trước):**
- Thêm dependency Lean ngoài Mathlib4 chuẩn.
- Thay đổi công thức toán học core (Black-76, Brent) — vì ảnh hưởng trading thực tế.
- Thêm CI pipeline tự động chạy Lean (tốn GitHub Actions minutes).

**Never do:**
- Commit `.lake/` folder hoặc bất kỳ compiled binary Lean vào repo.
- Dùng `sorry` như workaround để "pass" proof.
- Sửa logic Python dựa trên Lean proof mà chưa được owner duyệt.
- Cài Lean4 trực tiếp lên máy local (phải dùng Colab).

---

## 7. SUCCESS CRITERIA (CỤ THỂ, ĐO ĐƯỢC)

- [ ] **SC-1:** Colab notebook chạy từ cell đầu đến cuối không có lỗi (0 exception).
- [ ] **SC-2:** Lean compiler in ra `✅ All theorems proved` cho tất cả `.lean` files.
- [ ] **SC-3:** Không có `sorry` trong bất kỳ `.lean` file nào (grep check).
- [ ] **SC-4:** `pytest tests/test_formal_properties.py` pass 100% (hypothesis default 100 examples).
- [ ] **SC-5:** Tổng dung lượng `proofs/` < 500KB (ước tính thực tế < 50KB).
- [ ] **SC-6:** `proofs/.lake/` đã có trong `.gitignore` (kiểm tra bằng `git check-ignore`).

---

## 8. OPEN QUESTIONS

1. **Mathlib4 coverage:** Một số định nghĩa Black-76 (Normal CDF N(d1)) có thể cần tự prove từ đầu vì Mathlib4 có `erf` nhưng không có `Φ` trực tiếp. Có chấp nhận `Φ(x) := (1 + erf(x/√2)) / 2` như một định nghĩa?
2. **Brent convergence:** Chứng minh hội tụ đầy đủ của Brent trong Lean rất phức tạp (~500 dòng). Có chấp nhận chứng minh **weaker** (root bracketing invariant + bisection fallback đảm bảo |b-a| → 0) thay vì rate superlinear đầy đủ?
3. **JavaScript mirror:** Lõi Greeks cũng được implement lại trong JS (`recomputeLiveGreeksAndWalls`). Có yêu cầu verify cả phía JS không, hay chỉ Python?
