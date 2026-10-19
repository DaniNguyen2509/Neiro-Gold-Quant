"""Unit and integration tests for HTML Dashboard and Tactical HUD."""
from __future__ import annotations

import pathlib
import tempfile
import unittest.mock as mock
import pandas as pd
import pytest

from src.hud.html_dashboard import (
    load_and_preprocess_options,
    generate_html_terminal,
    run_pipeline,
)
from src.quant_engine.basis import clear_spot_cache, SpotQuote


@pytest.fixture(autouse=True)
def reset_cache():
    clear_spot_cache()
    yield
    clear_spot_cache()


def test_load_and_preprocess_options_with_basis():
    """Verify options CSV preprocessing with dynamic basis."""
    csv_path = "data/options_prices_GCZ26.csv"
    if not pathlib.Path(csv_path).exists():
        pytest.skip(f"Options test data {csv_path} not found")

    # 1. Test with explicit negative basis
    df, meta = load_and_preprocess_options(csv_path, basis=-24.0)
    assert meta["basis"] == -24.0
    assert meta["spot_price"] > 0
    assert meta["call_wall"] > 0
    assert meta["put_wall"] > 0
    assert "strike" in df.columns
    assert "netGEX" in df.columns

    # 2. Test with positive spread passed (should normalize to negative basis)
    df2, meta2 = load_and_preprocess_options(csv_path, basis=24.0)
    assert meta2["basis"] == -24.0

    # 3. Test with mocked auto-resolved basis
    quote = SpotQuote(price=4156.0, source="Mock", fetched_at=pd.Timestamp.now("UTC"))
    with mock.patch("src.quant_engine.basis.fetch_live_spot_gold_price", return_value=quote):
        with mock.patch("src.quant_engine.basis.is_gold_spot_market_open", return_value=True):
            df3, meta3 = load_and_preprocess_options(csv_path, basis=None)
            expected_basis = round(4156.0 - meta3["spot_price"], 2)
            assert meta3["basis"] == expected_basis


def test_generate_html_terminal_content():
    """Verify terminal HTML content and correct spot MT5 conversions."""
    # Create minimal realistic dataframe with camelCase columns matching loader/scraper schema
    df = pd.DataFrame([
        {
            "strike": 4150.0,
            "callOpenInterest": 1000,
            "putOpenInterest": 6000,
            "callVolume": 200,
            "putVolume": 1200,
            "callMid": 5.0,
            "putMid": 35.0,
            "netGEX": -50.0,
            "netVEX": 10.0,
            "netCHEX": -5.0,
        },
        {
            "strike": 4180.0,
            "callOpenInterest": 4000,
            "putOpenInterest": 4000,
            "callVolume": 800,
            "putVolume": 800,
            "callMid": 25.0,
            "putMid": 25.0,
            "netGEX": 120.0,
            "netVEX": 25.0,
            "netCHEX": 10.0,
        },
        {
            "strike": 4200.0,
            "callOpenInterest": 7000,
            "putOpenInterest": 1500,
            "callVolume": 1500,
            "putVolume": 300,
            "callMid": 45.0,
            "putMid": 5.0,
            "netGEX": 80.0,
            "netVEX": -15.0,
            "netCHEX": 8.0,
        },
    ])

    meta = {
        "spot_price": 4180.0,
        "atm_strike": 4180.0,
        "atm_straddle": 50.0,
        "sigma_atm": 0.15,
        "expected_move_1s": 35.0,
        "rule16_daily_move": 15.0,
        "call_wall": 4200.0,
        "call_wall_oi": 7000,
        "put_wall": 4150.0,
        "put_wall_oi": 6000,
        "total_net_gex": 150.0,
        "total_net_vex": 20.0,
        "total_net_chex": 13.0,
        "regime": "LONG GAMMA (VOLATILITY SUPPRESSION / MEAN REVERSION)",
        "squeeze_trigger": 4202.5,
        "waterfall_trigger": 4147.5,
        "basis": -24.0,
        "dte_days": 8.5,
        "expiration_date": "OGX26 (2026-10-27)",
    }

    import plotly.graph_objects as go
    fig = go.Figure()
    fig.add_trace(go.Bar(x=[4150, 4180, 4200], y=[10, 20, 30]))

    html = generate_html_terminal(df, meta, fig)

    # Check key indicators in HTML
    assert "Spot CME Futures ↔ Spot MT5 (Quy Đổi)" in html
    assert "$4,180.00" in html
    # MT5 Spot = 4180.0 + (-24.0) = 4156.00
    assert "MT5: ~$4,156.00" in html
    assert "Basis MT5 Spot: <b>-24.00 USD</b>" in html
    # Check strategic tables
    assert "BUY MUA ĐUỔI" in html
    assert "SELL CHẶN TIỀN TUYẾN" in html
    assert "BUY BẮT SÀN ATM" in html
    assert "SELL THỦNG SÀN" in html
    assert "BÁN ĐỈNH CALL WALL" in html
    assert "MUA ĐÁY PUT WALL" in html
    # Check that MT5 converted price is inside table
    assert "4156" in html or "4,156" in html


def test_run_pipeline_end_to_end():
    """Verify run_pipeline outputs complete HTML file to target directory."""
    csv_path = "data/options_prices_GCZ26.csv"
    if not pathlib.Path(csv_path).exists():
        pytest.skip(f"Options test data {csv_path} not found")

    with tempfile.TemporaryDirectory() as tmpdir:
        out_html = pathlib.Path(tmpdir) / "test_dashboard.html"
        saved = run_pipeline(input_csv=csv_path, output_files=[str(out_html)], basis=-24.0)

        assert len(saved) >= 1
        assert out_html.exists()
        content = out_html.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content
        assert "GOLD OPTIONS TACTICAL TERMINAL" in content
        assert "4,156" in content or "4156" in content
