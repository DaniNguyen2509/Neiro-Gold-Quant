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

def clean_and_sanitize_options_dataset(
    df: pd.DataFrame,
    reference_price: float | None = 4000.0,
) -> pd.DataFrame:
    """Rigorous Data Analyst cleaning & normalization pipeline for CME Options datasets.

    Enforces data purity before quant calculations:
    1. Strips leading/trailing whitespaces from all column headers.
    2. Removes duplicate strikes (keeps first occurrence).
    3. Coerces numeric columns using clean_val (stripping currency, commas, formula errors).
    4. Drops null, NaN, and negative strike rows; filters realistic Gold band [1000, 10000].
    5. Enforces strict ascending monotonicity (sorted by strike).
    6. Verifies spread integrity: when both bid and ask > 0, ensures ask >= bid (swaps crossed quotes).
    7. Clamps open interest, volume, and IV to non-negative bounds.
    """
    if df is None or not isinstance(df, pd.DataFrame):
        return pd.DataFrame()

    clean_df = df.copy()

    # 1. Clean column headers
    clean_df.columns = [str(c).strip() for c in clean_df.columns]

    if clean_df.empty or "strike" not in clean_df.columns:
        return clean_df

    # 2. Sanitize strike column
    from src.quant_engine.loader import clean_val
    clean_df["strike"] = clean_df["strike"].apply(clean_val)
    clean_df = clean_df[clean_df["strike"] > 0]
    clean_df = clean_df[(clean_df["strike"] >= 1000.0) & (clean_df["strike"] <= 10000.0)]

    # 3. Deduplicate strikes
    clean_df = clean_df.drop_duplicates(subset=["strike"], keep="first")

    # 4. Strict ascending sorting (monotonicity)
    clean_df = clean_df.sort_values("strike").reset_index(drop=True)

    # 5. Sanitize numeric columns
    numeric_cols = [
        "callOpenInterest", "putOpenInterest", "callVolume", "putVolume",
        "callBid", "callAsk", "callMid", "callLatest", "callIV", "callGamma",
        "putBid", "putAsk", "putMid", "putLatest", "putIV", "putGamma",
        "callGEX", "putGEX", "netGEX", "callVEX", "putVEX", "netVEX",
        "callCHEX", "putCHEX", "netCHEX",
    ]
    for col in numeric_cols:
        if col in clean_df.columns:
            clean_df[col] = clean_df[col].apply(clean_val)

    # 6. Spread sanity (Ask >= Bid)
    if "callBid" in clean_df.columns and "callAsk" in clean_df.columns:
        crossed_call = (clean_df["callBid"] > 0) & (clean_df["callAsk"] > 0) & (clean_df["callAsk"] < clean_df["callBid"])
        if crossed_call.any():
            clean_df.loc[crossed_call, ["callBid", "callAsk"]] = clean_df.loc[crossed_call, ["callAsk", "callBid"]].values

    if "putBid" in clean_df.columns and "putAsk" in clean_df.columns:
        crossed_put = (clean_df["putBid"] > 0) & (clean_df["putAsk"] > 0) & (clean_df["putAsk"] < clean_df["putBid"])
        if crossed_put.any():
            clean_df.loc[crossed_put, ["putBid", "putAsk"]] = clean_df.loc[crossed_put, ["putAsk", "putBid"]].values

    # 7. Clamp non-negative bounds for volumes and OIs
    for non_neg in ["callOpenInterest", "putOpenInterest", "callVolume", "putVolume", "callIV", "putIV"]:
        if non_neg in clean_df.columns:
            clean_df[non_neg] = clean_df[non_neg].clip(lower=0.0)

    return clean_df
