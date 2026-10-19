"""Unit tests for Auto-Basis Sync and Live Spot Resolution."""
from __future__ import annotations

import unittest.mock as mock
import pytest

from src.quant_engine.basis import (
    compute_basis,
    convert_to_spot,
    resolve_dynamic_basis,
    fetch_live_spot_gold_price,
)


def test_compute_basis_and_convert_to_spot():
    spot = 4156.0
    futures = 4180.0
    basis = compute_basis(spot, futures)
    assert basis == -24.0
    assert convert_to_spot(futures, basis) == 4156.0


def test_resolve_dynamic_basis_with_mocked_spot():
    with mock.patch("src.quant_engine.basis.fetch_live_spot_gold_price", return_value=4148.0):
        futures_price = 4172.0
        basis = resolve_dynamic_basis(futures_price)
        assert basis == 24.0


def test_resolve_dynamic_basis_fallback_when_offline():
    with mock.patch("src.quant_engine.basis.fetch_live_spot_gold_price", return_value=None):
        futures_price = 4172.0
        basis = resolve_dynamic_basis(futures_price, fallback_basis=24.0)
        assert basis == 24.0


def test_resolve_dynamic_basis_outlier_rejection():
    # If API returns an absurd or anomalous price (e.g. 100.0 or 10000.0)
    with mock.patch("src.quant_engine.basis.fetch_live_spot_gold_price", return_value=3500.0):
        futures_price = 4172.0
        # Spread is 672.0 (out of bounds > 60), should reject and use fallback
        basis = resolve_dynamic_basis(futures_price, fallback_basis=24.0)
        assert basis == 24.0
