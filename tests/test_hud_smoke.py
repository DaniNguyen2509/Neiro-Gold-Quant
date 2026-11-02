"""HUD smoke tests (Test Plan - Section 4: H1-H3).

Covers end-to-end dashboard generation from CSV -> HTML.
All network access is mocked (rule G1). Files use pytest tmp_path (rule G3).
"""
from __future__ import annotations

import os
import time
import unittest.mock as mock
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.hud.html_dashboard import (
    build_plotly_figure,
    build_volatility_smile_figure,
    generate_html_terminal,
    load_and_preprocess_options,
)

GC_REF = 4000.0

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
def _good_csv(path: Path, *, stale: bool = False, empty: bool = False) -> Path:
    """Write a realistic options CSV for smoke tests."""
    csv = path / "options_prices_GCZ26.csv"
    if empty:
        csv.write_text("strike,callOpenInterest,putOpenInterest\n")
        return csv

    strikes = np.arange(3500.0, 4501.0, 25.0)
    n = len(strikes)
    df = pd.DataFrame({
        "strike": strikes,
        "callBid": np.where(strikes >= GC_REF, np.linspace(80, 1, n), np.linspace(200, 100, n)),
        "callAsk": np.where(strikes >= GC_REF, np.linspace(82, 2, n), np.linspace(202, 102, n)),
        "callMid": 0.0,
        "callLatest": 0.0,
        "callVolume": 10,
        "callOpenInterest": np.where(strikes >= GC_REF, np.linspace(200, 50, n), 50).astype(int),
        "callGamma": 0.0005,
        "callIV": 0.18,
        "putBid": np.where(strikes <= GC_REF, np.linspace(1, 80, n), np.linspace(100, 200, n)),
        "putAsk": np.where(strikes <= GC_REF, np.linspace(2, 82, n), np.linspace(102, 202, n)),
        "putMid": 0.0,
        "putLatest": 0.0,
        "putVolume": 10,
        "putOpenInterest": np.where(strikes <= GC_REF, np.linspace(200, 50, n), 50).astype(int),
        "putGamma": 0.0005,
        "putIV": 0.18,
    })
    df.to_csv(csv, index=False)

    if stale:
        old = time.time() - 8 * 3600
        os.utime(csv, (old, old))

    return csv


@pytest.fixture()
def _mock_network(monkeypatch):
    """Block all network calls used by load_and_preprocess_options."""
    monkeypatch.setattr(
        "src.quant_engine.basis.fetch_live_cme_futures_price", lambda: GC_REF
    )
    monkeypatch.setattr(
        "src.quant_engine.basis.fetch_live_spot_gold_price", lambda: GC_REF - 24.0
    )
    monkeypatch.setattr(
        "src.quant_engine.basis.is_gold_spot_market_open", lambda: False
    )
    monkeypatch.setattr(
        "src.hud.html_dashboard.fetch_live_cme_m5_tape", lambda **_kw: []
    )


# ---------------------------------------------------------------------------
# H1 - End-to-end: CSV -> HTML with correct landmarks
# ---------------------------------------------------------------------------
def test_h1_generate_html_from_csv(tmp_path, _mock_network):
    """Smoke: generate full HTML terminal from a fixture CSV without crash."""
    csv = _good_csv(tmp_path)
    df, meta = load_and_preprocess_options(str(csv), basis=0.0, no_mt5=True)

    assert not df.empty
    assert meta["spot_price"] > 0

    fig = build_plotly_figure(df, meta)
    fig_smile = build_volatility_smile_figure(df, meta)
    html = generate_html_terminal(df, meta, fig, fig_smile)

    assert len(html) > 1000, "HTML output too short"

    # Key landmarks must appear in the rendered HTML
    assert str(int(meta["call_wall"])) in html, "Call Wall strike missing from HTML"
    assert str(int(meta["put_wall"])) in html, "Put Wall strike missing from HTML"

    # Zero Gamma Flip should appear if present
    if meta.get("zero_gamma_flip") is not None:
        s_star_str = f"{meta['zero_gamma_flip']:.0f}"
        # Either the exact number or a close rounding should be present
        assert any(
            s in html for s in [s_star_str, f"{meta['zero_gamma_flip']:.2f}"]
        ), f"Zero Gamma Flip {meta['zero_gamma_flip']} missing from HTML"


def test_h1_html_output_is_valid_html(tmp_path, _mock_network):
    """Output must be a self-contained HTML document."""
    csv = _good_csv(tmp_path)
    df, meta = load_and_preprocess_options(str(csv), basis=0.0, no_mt5=True)
    fig = build_plotly_figure(df, meta)
    html = generate_html_terminal(df, meta, fig)

    assert html.strip().startswith("<!DOCTYPE html>") or html.strip().startswith("<html"), \
        "Output is not valid HTML"
    assert "</html>" in html, "HTML is not properly closed"


# ---------------------------------------------------------------------------
# H2 - Stale data banner
# ---------------------------------------------------------------------------
def test_h2_stale_data_shows_banner(tmp_path, _mock_network):
    """RED-EXPECTED: When CSV is older than 6h, HTML must contain a visible stale warning.

    Bug found: In src/hud/html_dashboard.py (lines 1591-1593), `stale_badge_html` is
    computed but never interpolated into the HTML template string!
    """
    csv = _good_csv(tmp_path, stale=True)
    df, meta = load_and_preprocess_options(str(csv), basis=0.0, no_mt5=True)

    assert meta["is_data_stale"] is True, "Stale flag not set for 8h-old file"

    fig = build_plotly_figure(df, meta)
    html = generate_html_terminal(df, meta, fig)

    # The stale badge text pattern from html_dashboard.py line 1593
    stale_markers = ["OPTIONS DATA", "STALE", "stale", "data_stale"]
    assert any(m.lower() in html.lower() for m in stale_markers), (
        "Stale data banner not found in HTML output: `stale_badge_html` is defined in "
        "src/hud/html_dashboard.py:1593 but never inserted into the HTML template!"
    )


def test_h2_fresh_data_no_stale_banner(tmp_path, _mock_network):
    """Fresh CSV should NOT show stale warning."""
    csv = _good_csv(tmp_path, stale=False)
    df, meta = load_and_preprocess_options(str(csv), basis=0.0, no_mt5=True)

    assert meta["is_data_stale"] is False
    fig = build_plotly_figure(df, meta)
    html = generate_html_terminal(df, meta, fig)

    # The specific stale badge should not be present
    assert "OPTIONS DATA CU" not in html.upper().replace("Ũ", "U"), \
        "Stale banner shown for fresh data"


# ---------------------------------------------------------------------------
# H3 - Empty/corrupt CSV
# ---------------------------------------------------------------------------
def test_h3_empty_csv_does_not_crash(tmp_path, _mock_network):
    """Empty CSV must not crash the pipeline. It may fall back to benchmark data."""
    csv = _good_csv(tmp_path, empty=True)
    df, meta = load_and_preprocess_options(str(csv), basis=0.0, no_mt5=True)

    # Pipeline must survive
    assert not df.empty, "Pipeline returned empty df (acceptable if benchmark loaded)"
    assert meta["spot_price"] > 0


def test_h3_empty_csv_must_not_silently_use_benchmark(tmp_path, _mock_network):
    """RED-EXPECTED: when CSV is empty/corrupt, the dashboard must NOT silently
    load benchmark data (load_options_data) and display it as if it were real.

    Lines 186-189 of html_dashboard.py do exactly this: if df is empty after
    cleaning, it loads the hardcoded benchmark and proceeds without any warning.
    """
    csv = _good_csv(tmp_path, empty=True)
    df, meta = load_and_preprocess_options(str(csv), basis=0.0, no_mt5=True)

    # If the pipeline loaded benchmark data silently, the user sees a dashboard
    # with zero indication that it's not real market data.
    # At minimum, meta should flag this.
    is_benchmark = meta.get("is_benchmark_fallback", False)
    assert is_benchmark is True, (
        "Pipeline silently loaded benchmark data for an empty CSV without "
        "setting 'is_benchmark_fallback' flag in meta. The user sees a fake "
        "dashboard with no warning."
    )

def test_dashboard_atm_fallback_with_zero_mids_does_not_select_1350(tmp_path):
    """Verify that html_dashboard fallback ATM selection does not collapse to 1350 when bids/asks are zero."""
    from src.hud.html_dashboard import load_and_preprocess_options
    csv_file = tmp_path / "options_prices_GCZ26.csv"
    strikes = [1350.0, 2000.0, 3960.0, 4000.0, 5000.0]
    df = pd.DataFrame({
        "strike": strikes,
        "callBid": [0.0] * len(strikes),
        "callAsk": [0.0] * len(strikes),
        "callMid": [0.0] * len(strikes),
        "callLatest": [0.0] * len(strikes),
        "putBid": [0.0] * len(strikes),
        "putAsk": [0.0] * len(strikes),
        "putMid": [0.0] * len(strikes),
        "putLatest": [0.0] * len(strikes),
        "callOpenInterest": [100] * len(strikes),
        "putOpenInterest": [100] * len(strikes),
        "callVolume": [0] * len(strikes),
        "putVolume": [0] * len(strikes),
        "callGamma": [0.0] * len(strikes),
        "putGamma": [0.0] * len(strikes),
        "callIV": [0.20] * len(strikes),
        "putIV": [0.20] * len(strikes),
    })
    df.to_csv(csv_file, index=False)

    df_out, meta = load_and_preprocess_options(str(csv_file))
    assert meta["atm_strike"] > 3000.0, f"ATM strike collapsed to {meta['atm_strike']}"
