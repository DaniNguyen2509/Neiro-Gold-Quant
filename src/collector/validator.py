"""Options chain validator for Neiro-Gold-Quant.

Enforces structural invariants before data is accepted into the engine:
- Non-empty dataframe
- Required columns present (strike, callOpenInterest, putOpenInterest)
- Strike coverage surrounding active CME Gold Futures price
- Non-zero total open interest
- Non-negative open interest values
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import pandas as pd


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.ok


def validate_options_frame(
    df: pd.DataFrame,
    reference_price: float | None = 4000.0,
    min_strike_count: int = 10,
    required_columns: tuple[str, ...] = ("strike", "callOpenInterest", "putOpenInterest"),
) -> ValidationResult:
    """Validate that an options dataframe satisfies structural invariants."""
    errors: list[str] = []

    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return ValidationResult(ok=False, errors=["Options dataframe is empty or None"])

    # 1. Required columns
    for col in required_columns:
        if col not in df.columns:
            errors.append(f"Missing required column: '{col}'")

    if errors:
        return ValidationResult(ok=False, errors=errors)

    # 2. Strike filtering and count
    strikes = df["strike"].dropna()
    strikes = strikes[strikes > 0]
    if len(strikes) < min_strike_count:
        errors.append(f"Strike count {len(strikes)} is below required minimum {min_strike_count}")

    # 3. Strike coverage surrounding reference GC price
    if not strikes.empty and reference_price is not None and reference_price > 0:
        min_k = float(strikes.min())
        max_k = float(strikes.max())
        # The chain must span across the reference price with safety margins
        # E.g. min_strike <= reference_price and max_strike >= reference_price
        if min_k > reference_price * 0.95:
            errors.append(
                f"Min strike ({min_k:.1f}) is too high to cover reference GC price ({reference_price:.1f})"
            )
        if max_k < reference_price * 1.05:
            errors.append(
                f"Max strike ({max_k:.1f}) is too low to cover reference GC price ({reference_price:.1f})"
            )

    # 4. Open Interest invariants
    try:
        c_oi = df["callOpenInterest"].fillna(0).astype(float)
        p_oi = df["putOpenInterest"].fillna(0).astype(float)

        if (c_oi < 0).any() or (p_oi < 0).any():
            errors.append("Negative Open Interest detected in chain")

        total_oi = float(c_oi.sum() + p_oi.sum())
        if total_oi <= 0:
            errors.append("Total Open Interest across all strikes is zero or non-positive")
    except Exception as e:
        errors.append(f"Failed to calculate Open Interest sums: {e}")

    return ValidationResult(ok=len(errors) == 0, errors=errors)

