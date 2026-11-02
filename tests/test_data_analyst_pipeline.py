"""Tests for Data Analyst options cleaning, sanitization, and normalization pipeline."""
from __future__ import annotations

import pandas as pd
import numpy as np
import pytest

from src.collector.validator import clean_and_sanitize_options_dataset, validate_options_frame


def test_clean_and_sanitize_removes_duplicates_and_sorts():
    """Verify that duplicate strikes are removed and rows are strictly sorted ascending."""
    raw = pd.DataFrame({
        "strike": [4000.0, 3950.0, 4000.0, 4100.0, 3900.0],
        "callOpenInterest": [100, 200, 150, 300, 50],
        "putOpenInterest": [120, 180, 160, 250, 60],
        "callMid": [20.0, 40.0, 20.0, 10.0, 60.0],
        "putMid": [20.0, 10.0, 20.0, 40.0, 5.0],
    })

    cleaned = clean_and_sanitize_options_dataset(raw)

    assert len(cleaned) == 4, f"Duplicates were not removed, len={len(cleaned)}"
    assert cleaned["strike"].is_monotonic_increasing, "Strikes are not monotonically increasing"
    assert cleaned["strike"].tolist() == [3900.0, 3950.0, 4000.0, 4100.0]


def test_clean_and_sanitize_heals_crossed_quotes():
    """When ask < bid (crossed market quote anomaly), quotes must be swapped so ask >= bid."""
    raw = pd.DataFrame({
        "strike": [3950.0, 4000.0],
        "callBid": [50.0, 25.0],
        "callAsk": [45.0, 26.0],  # 3950 has ask < bid (45 < 50)
        "putBid": [15.0, 30.0],
        "putAsk": [16.0, 28.0],   # 4000 has ask < bid (28 < 30)
        "callOpenInterest": [100, 200],
        "putOpenInterest": [120, 180],
    })

    cleaned = clean_and_sanitize_options_dataset(raw)

    assert (cleaned["callAsk"] >= cleaned["callBid"]).all(), "Call ask is less than bid"
    assert (cleaned["putAsk"] >= cleaned["putBid"]).all(), "Put ask is less than bid"
    assert cleaned.loc[0, "callBid"] == 45.0
    assert cleaned.loc[0, "callAsk"] == 50.0
    assert cleaned.loc[1, "putBid"] == 28.0
    assert cleaned.loc[1, "putAsk"] == 30.0


def test_clean_and_sanitize_clamps_negative_and_sanitizes_strings():
    """Negative volume/OI must be clamped to zero, and formatted currency/text must be parsed."""
    raw = pd.DataFrame({
        "strike": ["$3,900.00", "$4,000.00", "4100"],
        "callOpenInterest": ["1,500", -50, "#N/A"],
        "putOpenInterest": [1000, 2000, "-"],
        "callVolume": [-10, 50, "unch"],
        "putVolume": [20, -5, "100"],
        "callIV": ["18.5%", 0.20, -0.05],
        "putIV": [0.20, "22.0%", 0.15],
    })

    cleaned = clean_and_sanitize_options_dataset(raw)

    assert len(cleaned) == 3
    assert (cleaned["callOpenInterest"] >= 0).all()
    assert (cleaned["putOpenInterest"] >= 0).all()
    assert (cleaned["callVolume"] >= 0).all()
    assert (cleaned["putVolume"] >= 0).all()
    assert (cleaned["callIV"] >= 0).all()
    assert cleaned.loc[0, "callOpenInterest"] == 1500.0
    assert cleaned.loc[1, "callOpenInterest"] == 0.0
    assert cleaned.loc[2, "callOpenInterest"] == 0.0


def test_clean_and_sanitize_filters_absurd_non_gold_strikes():
    """Strikes outside [1000, 10000] are abnormal non-gold artifacts and must be dropped."""
    raw = pd.DataFrame({
        "strike": [5.0, 500.0, 3900.0, 4000.0, 15000.0],
        "callOpenInterest": [10, 20, 100, 200, 30],
        "putOpenInterest": [10, 20, 100, 200, 30],
    })

    cleaned = clean_and_sanitize_options_dataset(raw)

    assert len(cleaned) == 2
    assert cleaned["strike"].tolist() == [3900.0, 4000.0]


def test_clean_and_sanitize_empty_and_none():
    """Graceful handling of empty or None dataframes."""
    assert clean_and_sanitize_options_dataset(None).empty
    assert clean_and_sanitize_options_dataset(pd.DataFrame()).empty
    assert clean_and_sanitize_options_dataset(pd.DataFrame({"dummy": [1, 2]})).columns.tolist() == ["dummy"]

