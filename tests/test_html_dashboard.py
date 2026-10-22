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
    assert "netDeltaContracts" in df.columns
    assert "skew_rr25" in meta
    assert "skew_bf25" in meta
    assert "cta_badge" in meta
    assert "total_net_delta_contracts" in meta
    assert "max_tilt_strike" in meta

    # 2. Test with positive spread passed (should normalize to negative basis)
    df2, meta2 = load_and_preprocess_options(csv_path, basis=24.0)
    assert meta2["basis"] == -24.0

    # 3. Test with mocked auto-resolved basis
    quote = SpotQuote(price=4156.0, source="Mock", fetched_at=pd.Timestamp.now("UTC"))
    with mock.patch("src.quant_engine.basis.fetch_live_cme_futures_price", return_value=4180.0):
        with mock.patch("src.quant_engine.basis.fetch_live_spot_gold_price", return_value=quote):
            with mock.patch("src.quant_engine.basis.is_gold_spot_market_open", return_value=True):
                df3, meta3 = load_and_preprocess_options(csv_path, basis=None)
                expected_basis = round(4156.0 - meta3["spot_price"], 2)
                assert meta3["basis"] == expected_basis
                assert "GC=F" in meta3["futures_feed"]


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
        "skew_rr25": 0.015,
        "skew_bf25": 0.008,
        "skew_sentiment": "BULLISH CALL SKEW (DÒNG TIỀN QUỸ GOM CALL CƯỢC PHÁ ĐỈNH)",
        "cta_badge": "INDEPENDENT DEALER WALLS",
        "cta_description": "Các chốt chặn hiện tại do Market Maker độc lập phòng thủ trong biên độ thông thường.",
        "zero_gamma_flip": 4175.5,
        "call_wall_siege": 0.21,
        "put_wall_siege": 0.85,
    }

    import plotly.graph_objects as go
    fig = go.Figure()
    fig.add_trace(go.Bar(x=[4150, 4180, 4200], y=[10, 20, 30]))

    html = generate_html_terminal(df, meta, fig)

    # Check key indicators in pure CME HTML
    assert "CME Gold Futures GCZ26 (COMEX)" in html
    assert "$4,180.00" in html
    assert "Zero Gamma Flip" in html
    assert "$4,175.50" in html
    assert "Siege" in html
    assert "MA TRẬN 6 KỊCH BẢN HÀNH VI MARKET MAKER" in html
    assert "THƯỚC ĐO VỊ TRÍ GIÁ SO VỚI CÁC BỨC TƯỜNG CỦA MARKET MAKER" in html
    assert "TỪ ĐIỂN THUẬT NGỮ BỎ TÚI" in html
    assert "Sổ Sách Dealer (Net Delta / DEX)" in html
    assert "Net Delta / DEX (Sổ Sách Dealer)" in html
    assert "Lot Size ($10K, R: 1%)" in html
    # Check strategic tables (pure CME)
    assert "BUY MUA ĐUỔI" in html
    assert "SELL CHẶN TIỀN TUYẾN" in html
    assert "BUY BẮT SÀN ATM" in html
    assert "SELL THỦNG SÀN" in html
    assert "BÁN ĐỈNH CALL WALL" in html
    assert "MUA ĐÁY PUT WALL" in html
    assert "refreshWithCacheBuster()" in html


def test_run_pipeline_end_to_end():
    """Verify run_pipeline outputs complete HTML file to target directory."""
    csv_path = "data/options_prices_GCZ26.csv"
    if not pathlib.Path(csv_path).exists():
        pytest.skip(f"Options test data {csv_path} not found")

    with mock.patch("src.quant_engine.basis.fetch_live_cme_futures_price", return_value=4180.0):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_html = pathlib.Path(tmpdir) / "test_dashboard.html"
            saved = run_pipeline(input_csv=csv_path, output_files=[str(out_html)], no_mt5=True)

            assert len(saved) >= 1
            assert out_html.exists()
            content = out_html.read_text(encoding="utf-8")
            assert "<!DOCTYPE html>" in content
            assert "GOLD OPTIONS TACTICAL TERMINAL" in content
            assert "MA TRẬN 6 KỊCH BẢN HÀNH VI MARKET MAKER" in content
            assert "refreshWithCacheBuster()" in content


def test_otm_wall_selection_filtering():
    """Verify that OTM Wall selection never selects an ITM strike as a Dealer Wall.
    - Call Wall MUST be OTM: strike >= spot_price
    - Put Wall MUST be OTM: strike <= spot_price
    """
    df_sample = pd.DataFrame([
        {
            "strike": 4100.0,
            "callOpenInterest": 9000,  # ITM Call (huge OI)
            "putOpenInterest": 2000,   # OTM Put
            "callBid": 50.0, "callAsk": 52.0, "putBid": 2.0, "putAsk": 3.0,
        },
        {
            "strike": 4150.0,
            "callOpenInterest": 1000,
            "putOpenInterest": 1000,
            "callBid": 15.0, "callAsk": 16.0, "putBid": 15.0, "putAsk": 16.0,
        },
        {
            "strike": 4200.0,
            "callOpenInterest": 3000,  # OTM Call
            "putOpenInterest": 8000,   # ITM Put (huge OI)
            "callBid": 2.0, "callAsk": 3.0, "putBid": 50.0, "putAsk": 52.0,
        },
    ])

    with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
        df_sample.to_csv(f.name, index=False)
        temp_csv = f.name

    try:
        with mock.patch("src.quant_engine.basis.fetch_live_cme_futures_price", return_value=4150.0):
            df_res, meta = load_and_preprocess_options(temp_csv)
            # Spot is 4150.0
            # Call Wall must be chosen from strikes >= 4150 -> 4200 (OI 3000), NOT 4100 (even though 4100 has OI 9000)
            assert meta["call_wall"] >= 4150.0
            assert meta["call_wall"] == 4200.0

            # Put Wall must be chosen from strikes <= 4150 -> 4100 (OI 2000), NOT 4200 (even though 4200 has OI 8000)
            assert meta["put_wall"] <= 4150.0
            assert meta["put_wall"] == 4100.0
    finally:
        pathlib.Path(temp_csv).unlink(missing_ok=True)


def test_clear_workspace_cache_and_memory_tracker():
    """Verify memory tracking and workspace cache cleaner."""
    from src.hud.html_dashboard import clear_workspace_cache, get_process_memory_mb

    # 1. Test get_process_memory_mb
    ram_mb = get_process_memory_mb()
    assert isinstance(ram_mb, float)
    assert ram_mb >= 0.0

    # 2. Test clear_workspace_cache removes temporary scratch files
    scratch_dir = pathlib.Path("scratch")
    scratch_dir.mkdir(exist_ok=True)
    dummy_tmp = scratch_dir / "temp_test_cache.tmp"
    dummy_tmp.write_text("temporary test data", encoding="utf-8")
    assert dummy_tmp.exists()

    removed = clear_workspace_cache()
    assert removed >= 1
    assert not dummy_tmp.exists()


def test_html_terminal_contains_clear_cache_controls():
    """Verify generated terminal contains zero-leak cache clearing script and buttons."""
    from src.hud.html_dashboard import generate_html_terminal
    import plotly.graph_objects as go

    df_sample = pd.DataFrame([
        {
            "strike": 4150.0,
            "callOpenInterest": 1000, "putOpenInterest": 1000,
            "callVolume": 100, "putVolume": 100,
            "callMid": 10.0, "putMid": 10.0,
            "netGEX": 50.0, "netVEX": 10.0, "netCHEX": 5.0,
        },
        {
            "strike": 4200.0,
            "callOpenInterest": 2000, "putOpenInterest": 500,
            "callVolume": 200, "putVolume": 50,
            "callMid": 20.0, "putMid": 5.0,
            "netGEX": 80.0, "netVEX": -5.0, "netCHEX": 2.0,
        },
    ])
    meta = {
        "spot_price": 4150.0,
        "atm_strike": 4150.0,
        "atm_straddle": 40.0,
        "sigma_atm": 0.15,
        "expected_move_1s": 30.0,
        "rule16_daily_move": 15.0,
        "call_wall": 4200.0,
        "call_wall_oi": 2000,
        "put_wall": 4150.0,
        "put_wall_oi": 1000,
        "total_net_gex": 130.0,
        "total_net_vex": 5.0,
        "total_net_chex": 7.0,
        "regime": "LONG GAMMA (VOLATILITY SUPPRESSION / MEAN REVERSION)",
        "basis": -24.0,
        "dte_days": 8.0,
        "expiration_date": "OGX26 (2026-10-27)",
        "m5_tape": {"candles": []},
    }
    fig = go.Figure()
    html = generate_html_terminal(df_sample, meta, fig)

    assert "clearHistoryAndCache()" in html
    assert "Dọn RAM & Cache" in html
    assert "location.replace" in html



