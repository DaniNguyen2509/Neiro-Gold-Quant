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
    resolve_adaptive_tactical_strikes,
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
    assert "MA TRẬN 6 KỊCH BẢN" not in html
    assert "THƯỚC ĐO VỊ TRÍ GIÁ SO VỚI CÁC BỨC TƯỜNG CỦA MARKET MAKER" in html
    assert "TỪ ĐIỂN THUẬT NGỮ BỎ TÚI" in html
    assert "Sổ Sách Dealer (Net Delta / DEX)" in html
    assert "Net Delta / DEX (Sổ Sách Dealer)" in html
    assert "Lot Size ($10K, R: 1%)" in html
    # Check strategic tables (pure CME - simplified Type 2 labels)
    assert "THUẬN CHIỀU BUY (Phá cản" in html
    assert "ĐẢO CHIỀU SELL (Chạm cản" in html
    assert "ĐẢO CHIỀU BUY (Chạm sàn" in html
    assert "THUẬN CHIỀU SELL (Thủng sàn" in html
    assert "ƯU TIÊN ĐÁNH ĐẢO CHIỀU (GEX +)" in html
    assert "GEX (+): Đánh ĐẢO CHIỀU" in html
    assert "CHEX · HÚT GIÁ VỀ ĐÂY" in html
    assert "VEX · VÙNG BẬT / GIẬT SÓNG" in html
    assert "PHẦN 2: BẢNG TÁC CHIẾN PHỤC KÍCH THÀNH TRÌ" not in html
    assert "refreshWithCacheBuster()" in html
    # Check Microstructure Greeks & Pinning Table
    assert "BẢNG ĐỊNH LƯỢNG VI CẤU TRÚC GREEKS & TÂM BÃO PINNING" in html
    assert "Theta Bào Mòn" in html
    assert "Gamma Black-76" in html


def test_run_pipeline_end_to_end():
    """Verify run_pipeline outputs complete HTML file to target directory."""
    csv_path = "data/options_prices_GCZ26.csv"
    if not pathlib.Path(csv_path).exists():
        pytest.skip(f"Options test data {csv_path} not found")

    with (
        mock.patch("src.quant_engine.basis.fetch_live_cme_futures_price", return_value=4180.0),
        mock.patch("src.hud.html_dashboard.fetch_live_cme_m5_tape", return_value={}),
        tempfile.TemporaryDirectory() as tmpdir,
    ):
        out_html = pathlib.Path(tmpdir) / "test_dashboard.html"
        saved = run_pipeline(
            input_csv=csv_path,
            output_files=[str(out_html)],
            no_mt5=True,
            sync_cloud=False,
            write_root_json=False,
        )

        assert len(saved) >= 1
        assert out_html.exists()
        assert (pathlib.Path(tmpdir) / "version.json").exists()
        content = out_html.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content
        assert "GOLD OPTIONS TACTICAL TERMINAL" in content
        assert "BẢNG TÁC CHIẾN LƯỚT SÓNG TRONG NGÀY" in content
        assert "MA TRẬN 6 KỊCH BẢN" not in content
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


def test_volatility_smile_figure_and_layout_ordering():
    """Verify standalone Volatility Smile panel and strict chart-first top-to-bottom layout sequence."""
    from src.hud.html_dashboard import build_volatility_smile_figure, generate_html_terminal
    import plotly.graph_objects as go

    df_sample = pd.DataFrame([
        {
            "strike": 4000.0,
            "callOpenInterest": 1500, "putOpenInterest": 6000,
            "callVolume": 100, "putVolume": 500,
            "callMid": 45.0, "putMid": 8.0,
            "callIV": 0.22, "putIV": 0.25,
            "netGEX": -30.0, "netVEX": 10.0, "netCHEX": -5.0,
        },
        {
            "strike": 4025.0,
            "callOpenInterest": 4000, "putOpenInterest": 4000,
            "callVolume": 800, "putVolume": 800,
            "callMid": 22.0, "putMid": 22.0,
            "callIV": 0.19, "putIV": 0.19,
            "netGEX": 80.0, "netVEX": 25.0, "netCHEX": 10.0,
        },
        {
            "strike": 4150.0,
            "callOpenInterest": 8000, "putOpenInterest": 1000,
            "callVolume": 1200, "putVolume": 100,
            "callMid": 5.0, "putMid": 40.0,
            "callIV": 0.26, "putIV": 0.21,
            "netGEX": 120.0, "netVEX": -15.0, "netCHEX": 8.0,
        },
    ])
    meta = {
        "spot_price": 4028.0,
        "atm_strike": 4025.0,
        "atm_straddle": 44.0,
        "sigma_atm": 0.193,
        "expected_move_1s": 207.23,
        "rule16_daily_move": 117.74,
        "call_wall": 4150.0,
        "call_wall_oi": 8000,
        "put_wall": 4000.0,
        "put_wall_oi": 6000,
        "total_net_gex": -108.1,
        "total_net_vex": 1.0,
        "total_net_chex": -4.5,
        "regime": "SHORT_GAMMA",
        "zero_gamma_flip": 4266.52,
        "basis": -24.0,
        "dte_days": 8.0,
        "expiration_date": "OGX26 (2026-10-27)",
        "skew_rr25": 0.0243,
        "skew_bf25": 0.0222,
        "skew_label": "BULLISH CALL SKEW",
        "m5_tape": {"candles": []},
    }

    fig_micro = go.Figure()
    fig_micro.add_trace(go.Bar(x=[4000, 4025, 4150], y=[10, 20, 30]))

    # 1. Test standalone Volatility Smile figure
    fig_smile = build_volatility_smile_figure(df_sample, meta)
    assert fig_smile is not None
    assert len(fig_smile.data) >= 1  # Malz continuous curve + scatter points
    # Check annotations on smile figure
    annot_texts = " ".join([a.text for a in fig_smile.layout.annotations if hasattr(a, "text") and a.text])
    assert "TÂM BÃO PINNING" in annot_texts
    assert "HỐ ĐEN GIẢM TỐC" in annot_texts
    assert "BẪY THUỐC NỔ" in annot_texts
    assert "CME GC" in annot_texts

    # 2. Test HTML layout sequence
    html = generate_html_terminal(df_sample, meta, fig_micro, fig_smile=fig_smile)
    pos_smile = html.find("KHỐI 1: BIỂU ĐỒ VOLATILITY SMILE & SKEW")
    pos_micro = html.find("KHỐI 2: 3 PANEL BIỂU ĐỒ VI MÔ GEX")
    pos_kpi = html.find("KHỐI 3: KPI THỐNG KÊ TOÀN CẢNH CME GOLD FUTURES")
    pos_orderflow = html.find("KHỐI 5: BĂNG GIÁ & XUNG LỰC VOLUME M5")
    pos_strategy = html.find("BẢNG TÁC CHIẾN LƯỚT SÓNG TRONG NGÀY")
    pos_glossary = html.find("TỪ ĐIỂN THUẬT NGỮ BỎ TÚI")

    assert pos_smile != -1, "Smile panel must be present"
    assert pos_micro != -1, "3-panel micro chart must be present"
    assert pos_kpi != -1, "7 KPI cards must be present"
    assert pos_orderflow != -1, "Orderflow must be present"
    assert pos_strategy != -1, "Strategy tables must be present"
    assert pos_glossary != -1, "Glossary must be present"

    # Enforce strict absence of removed legacy sections
    assert "KHỐI 7: BẢNG TÁC CHIẾN TỨC THÌ" not in html
    assert "KỊCH BẢN HIỆN TẠI" not in html
    assert "MA TRẬN 6 KỊCH BẢN" not in html
    assert "PHẦN 2: BẢNG TÁC CHIẾN PHỤC KÍCH THÀNH TRÌ" not in html

    # Enforce strict top-to-bottom layout ordering:
    # 1. Smile Panel -> 2. 3-Panel Micro Chart -> 3. 7 KPIs -> 4. Spine & Tape -> 5. Strategy -> 6. Glossary
    assert pos_smile < pos_micro < pos_kpi < pos_orderflow < pos_strategy < pos_glossary


def test_load_and_preprocess_options_empty_csv_fallback(tmp_path):
    """Verify that empty CSV does not crash load_and_preprocess_options and falls back safely."""
    empty_csv = tmp_path / "empty_options.csv"
    empty_csv.write_text("strike,callBid,callAsk,callMid,callOpenInterest,callVolume\n")

    df, meta = load_and_preprocess_options(str(empty_csv))
    assert not df.empty
    assert len(df) > 0
    assert meta["spot_price"] > 0
    assert meta["call_wall"] > 0
    assert meta["put_wall"] > 0


def test_load_and_preprocess_options_disconnected_strikes_fallback(tmp_path):
    """Verify that disconnected strikes (e.g. max 2560 vs spot 4000) trigger fallback recovery."""
    corrupt_csv = tmp_path / "corrupt_strikes.csv"
    corrupt_csv.write_text("strike,callBid,callAsk,callMid,callOpenInterest,callVolume\n1080.0,0,0,0,0,0\n2560.0,0,0,0,0,0\n")

    with mock.patch("src.quant_engine.basis.fetch_live_cme_futures_price", return_value=4000.0):
        df, meta = load_and_preprocess_options(str(corrupt_csv))
        assert not df.empty
        # Recovered ATM strike must be close to spot (4000), NOT 2560
        assert abs(meta["atm_strike"] - 4000.0) <= 200.0


def test_resolve_adaptive_tactical_strikes_fine_strike_guard():
    """Verify Adaptive Micro-Strike Guard resolves 4030.0 when spot is 4027.5 on 1DTE."""
    import numpy as np

    # Case 1: Sparse strikes with $25 step, but spot is 4027.5 on 1DTE
    sparse_strikes = np.array([3975.0, 4000.0, 4025.0, 4050.0, 4075.0])
    spot = 4027.5
    strike_above, next_above, strike_below, next_below, step, is_guarded = resolve_adaptive_tactical_strikes(
        sparse_strikes, spot, dte_days=1.0, call_wall=4050.0, put_wall=4000.0
    )

    # Must resolve to 4030.0 (NOT 4050.0)
    assert strike_above == 4030.0
    assert next_above == 4035.0
    assert strike_below == 4025.0
    assert next_below == 4020.0
    assert step == 5.0
    assert is_guarded is True

    # Case 2: Standard DTE (> 10.0 days), respects natural chain strikes
    strike_above_far, _, _, _, _, is_guarded_far = resolve_adaptive_tactical_strikes(
        sparse_strikes, spot, dte_days=30.0, call_wall=4050.0, put_wall=4000.0
    )
    assert strike_above_far == 4050.0
    assert is_guarded_far is False


def test_load_and_preprocess_options_stale_data_detection(tmp_path):
    """Verify that file age and is_data_stale flag are recorded in meta."""
    import os
    import time

    sample_csv = tmp_path / "sample_options.csv"
    sample_csv.write_text("strike,callBid,callAsk,callMid,callOpenInterest,callVolume\n4000.0,10,12,11,100,20\n4025.0,5,7,6,200,30\n")

    # Artificially age the file to 10 hours ago
    past_time = time.time() - (10.0 * 3600.0)
    os.utime(sample_csv, (past_time, past_time))

    df, meta = load_and_preprocess_options(str(sample_csv))
    assert meta["file_age_hours"] >= 9.9
    assert meta["is_data_stale"] is True
    assert "strike_above" in meta
    assert "strike_below" in meta
    assert "is_micro_guarded" in meta


def test_multi_expiry_ignores_corrupt_sub_files(tmp_path):
    """Verify that load_multi_expiry_options discards corrupt sub-expiry files (e.g. strikes 500-1000)."""
    from src.quant_engine.loader import load_multi_expiry_options

    # Create valid master chain
    master_csv = tmp_path / "options_prices_GCZ26.csv"
    master_csv.write_text(
        "strike,callBid,callAsk,callMid,callOpenInterest,callVolume,callGamma,callIV,putBid,putAsk,putMid,putOpenInterest,putVolume,putGamma,putIV\n"
        "4000.0,10,12,11,100,20,0.003,0.18,5,7,6,150,30,0.003,0.18\n"
        "4025.0,8,10,9,120,25,0.003,0.18,7,9,8,140,25,0.003,0.18\n"
        "4050.0,6,8,7,140,30,0.003,0.18,9,11,10,120,20,0.003,0.18\n"
        "4075.0,4,6,5,160,35,0.003,0.18,11,13,12,100,15,0.003,0.18\n"
        "4100.0,2,4,3,180,40,0.003,0.18,13,15,14,80,10,0.003,0.18\n"
    )

    # Create corrupt sub-expiry file with strikes 500-1000
    corrupt_sub = tmp_path / "options_prices_GCZ26_OG1X26.csv"
    corrupt_sub.write_text(
        "strike,callBid,callAsk,callMid,callOpenInterest,callVolume,callGamma,callIV,putBid,putAsk,putMid,putOpenInterest,putVolume,putGamma,putIV,expirationDate\n"
        "500.0,100,105,102.5,10,0,0.001,0.20,0,0,0,0,0,0,0,2027-03-19\n"
        "525.0,90,95,92.5,10,0,0.001,0.20,0,0,0,0,0,0,0,2027-03-19\n"
        "550.0,80,85,82.5,10,0,0.001,0.20,0,0,0,0,0,0,0,2027-03-19\n"
    )

    df_loaded = load_multi_expiry_options(str(tmp_path))
    assert not df_loaded.empty
    # Must contain gold strikes (4000-4100), NOT corrupt strikes (500-550)
    assert float(df_loaded["strike"].min()) >= 3000.0


def test_zero_iv_chain_self_healing_black76(tmp_path):
    """Verify that options chains with 0.0 IVs are self-healed via Black-76 so skew curve is not flat."""
    sample_csv = tmp_path / "options_prices_zero_iv.csv"
    strikes = [3950.0 + i * 25.0 for i in range(10)]
    rows = ["strike,callBid,callAsk,callMid,callOpenInterest,callVolume,callGamma,callIV,putBid,putAsk,putMid,putOpenInterest,putVolume,putGamma,putIV,expirationDate"]
    for i, s in enumerate(strikes):
        c_mid = max(5.0, 100.0 - i * 10.0)
        p_mid = max(5.0, 10.0 + i * 10.0)
        rows.append(f"{s},{c_mid-1},{c_mid+1},{c_mid},200,20,0.003,0.0,{p_mid-1},{p_mid+1},{p_mid},200,20,0.003,0.0,2026-11-25")
    sample_csv.write_text("\n".join(rows))

    df, meta = load_and_preprocess_options(str(sample_csv))
    # ATM IV must be calibrated (> 8% lower clamp)
    assert meta["sigma_atm"] > 0.08
    # Butterfly curvature must be active (>= 0.005)
    assert meta["skew_bf25"] >= 0.005
    # Call/Put IVs in df must be self-healed from mid prices
    assert (df["callIV"] > 0.03).all()
    assert (df["putIV"] > 0.03).all()


def test_microstructure_table_plus_minus_10_strikes_and_informed_bar():
    """Verify ±10 strikes window around realtime spot and Informed Trader Action bar."""
    from src.hud.html_dashboard import build_microstructure_pinning_table_html

    # Create 35 strikes from $4,500 to $5,350 ($25 step), spot at $4,925 (middle strike)
    rows = []
    for i in range(35):
        stk = 4500.0 + i * 25.0
        rows.append({
            "strike": stk,
            "netGEX": 10.0,
            "callOpenInterest": 500,
            "putOpenInterest": 500,
            "callVolume": 50,
            "putVolume": 50,
            "netVEX": 1.0,
            "netCHEX": 0.5,
        })
    df_35 = pd.DataFrame(rows)
    meta = {
        "spot_price": 4925.0,
        "call_wall": 5100.0,
        "put_wall": 4750.0,
        "zero_gamma": 4900.0,
        "institutional_orderflow": {
            "vpin_pct": 32.5,
            "vpin_label": "🟢 VPIN AN TOÀN (32.5% < 40% - CÓ THỂ FADE WALL)",
            "vrp_spread_pct": 5.2,
            "vrp_label": "💎 VRP ĐẮT (+5.2% = IV 22.0% > RV 16.8%)",
            "informed_action_badge": "🟢 AN TOÀN ĐÁNH ĐẢO CHIỀU TẠI WALL (SAFE MEAN-REVERSION)",
            "informed_action_guidance": "VPIN thấp + VRP dương",
            "informed_action_color": "#4ADE80",
            "bayesian_conviction_rho": 0.68,
            "kelly_fraction_mult": 0.85,
        },
    }
    html = build_microstructure_pinning_table_html(df_35, meta)
    assert 'id="informed-trader-action-bar"' in html
    assert 'id="micro-vpin-val"' in html
    assert 'id="micro-vrp-val"' in html
    assert 'class="micro-strike-row row-spot"' in html
    assert '👉 SPOT: $4,925.00' in html
    # Out of 35 total rows, 21 rows (±10 around spot) are visible, and 14 have display:none
    assert html.count('data-strike="') == 35
    assert html.count('style="display:none; "') == 14


def test_3sec_command_bar_flex_ordering_and_live_microstructure_payload(tmp_path):
    """Verify 3-Second Tactical Command Bar, above-the-fold flex ordering, and live VPIN/ATR helper."""
    from src.hud.html_dashboard import (
        _compute_live_microstructure_payload,
        build_volatility_smile_figure,
        generate_html_terminal,
    )

    rows = [
        {"strike": 3950.0, "callOpenInterest": 200, "putOpenInterest": 1800, "callVolume": 40, "putVolume": 300, "netGEX": -12.0, "netVEX": -1.5, "netCHEX": -0.3, "netDeltaContracts": -200.0},
        {"strike": 4000.0, "callOpenInterest": 900, "putOpenInterest": 900, "callVolume": 150, "putVolume": 150, "netGEX": 15.0, "netVEX": 1.8, "netCHEX": 0.4, "netDeltaContracts": 100.0},
        {"strike": 4050.0, "callOpenInterest": 2200, "putOpenInterest": 250, "callVolume": 400, "putVolume": 50, "netGEX": 28.0, "netVEX": 3.0, "netCHEX": 0.8, "netDeltaContracts": 450.0},
    ]
    df_sample = pd.DataFrame(rows)
    meta = {
        "spot_price": 4010.0,
        "atm_strike": 4000.0,
        "regime": "LONG_GAMMA",
        "total_net_gex": 31.0,
        "total_net_vex": 3.3,
        "total_net_chex": 0.9,
        "expected_move_1s": 30.0,
        "rule16_daily_move": 14.0,
        "call_wall": 4050.0,
        "call_wall_oi": 2200,
        "put_wall": 3950.0,
        "put_wall_oi": 1800,
        "zero_gamma_flip": 3985.0,
        "m5_tape": {"market_open": True, "candles": []},
        "institutional_orderflow": {"vpin_pct": 31.5, "session_name": "NY_COMEX_DEEP"},
    }
    fig_smile = build_volatility_smile_figure(df_sample, meta)
    html = generate_html_terminal(df_sample, meta, None, fig_smile=fig_smile)

    # 1. 3-Second Tactical Command Bar IDs
    for elem_id in (
        'id="tactical-3s-command-bar"',
        'id="cmd-regime-val"',
        'id="cmd-wall-val"',
        'id="cmd-flow-val"',
        'id="cmd-action-val"',
        'id="spine-strike-above"',
        'id="spine-strike-below"',
        'id="k6-row-sq"',
        'id="k6-sq-entry"',
        'id="k6-fd-gate"',
        'id="k6-rb-tp"',
        'id="k6-bd-lot"',
    ):
        assert elem_id in html

    # 2. Flex ordering prioritizes Chart (order: 1) -> 3s Bar (order: 2) -> Spine (order: 3) -> KHỐI 6 open (order: 4)
    assert '<div class="cockpit-stage" style="order: 1;">' in html
    assert '<div id="tactical-3s-command-bar" class="cmd-3s-grid" style="order: 2;">' in html
    assert '<div class="spine-container" style="order: 3;' in html
    assert '<details open class="table-box" style="order: 4;' in html

    # 3. Live microstructure helper computes non-empty VPIN, BVC, Kyle, ATR from 1m tape
    fake_candles = [
        {"open": 4000.0 + (i % 3) * 0.2, "high": 4001.5, "low": 3999.5, "close": 4000.3 + (i % 2) * 0.2, "volume": 120 + i}
        for i in range(50)
    ]
    live_micro = _compute_live_microstructure_payload({"chart_candles": fake_candles})
    assert 5.0 <= live_micro["vpin_pct"] <= 99.0
    assert 0.0 <= live_micro["bvc_buy_pct"] <= 100.0
    assert 2.0 <= live_micro["atr_5m"] <= 6.5
    assert "λ" in live_micro["kyle_lambda_label"]


def test_out_of_range_csv_benchmark_fallback_sets_flag(tmp_path: pathlib.Path) -> None:
    """Out-of-range CSV falling back to BENCHMARK_GCZ26_DATA must set is_benchmark_fallback=True."""
    bad_csv = tmp_path / "out_of_range.csv"
    pd.DataFrame(
        [
            {"strike": 1000.0, "callOpenInterest": 100, "putOpenInterest": 100, "callMid": 10.0, "putMid": 1.0},
            {"strike": 1025.0, "callOpenInterest": 100, "putOpenInterest": 100, "callMid": 5.0, "putMid": 2.0},
            {"strike": 1050.0, "callOpenInterest": 100, "putOpenInterest": 100, "callMid": 2.0, "putMid": 5.0},
        ]
    ).to_csv(bad_csv, index=False)

    with (
        mock.patch("src.quant_engine.basis.fetch_live_cme_futures_price", return_value=4180.0),
        mock.patch("src.hud.html_dashboard.fetch_live_cme_m5_tape", return_value={}),
    ):
        _df, meta = load_and_preprocess_options(str(bad_csv), no_mt5=True)
    assert meta.get("is_benchmark_fallback") is True


def test_sync_latest_cloud_options_csv_rejects_corrupt_payload(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """sync_latest_cloud_options_csv must validate downloaded CSV with validate_options_frame."""
    import io
    import os
    from src.hud import html_dashboard as hd

    target = tmp_path / "options_prices_GCZ26.csv"
    valid_seed = "strike,callOpenInterest,putOpenInterest\n4000,500,500\n"
    target.write_text(valid_seed, encoding="utf-8")
    old_t = 1000.0
    os.utime(target, (old_t, old_t))
    hd._CLOUD_CSV_SYNC_TS.clear()

    corrupt_rows = ["strike,callOpenInterest,putOpenInterest"] + [
        f"{100 + i},0,0" for i in range(12)
    ]
    corrupt_bytes = ("\n".join(corrupt_rows)).encode("utf-8")

    class _Resp(io.BytesIO):
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

    monkeypatch.setattr("urllib.request.urlopen", lambda *_a, **_kw: _Resp(corrupt_bytes))
    monkeypatch.setattr("src.quant_engine.basis.fetch_live_cme_futures_price", lambda: 4000.0)

    synced = hd.sync_latest_cloud_options_csv(str(target), max_age_hours=0.1)
    assert synced is False
    assert target.read_text(encoding="utf-8") == valid_seed


def test_lightweight_live_tick_updates_tactical_strikes_and_forward_dislocation(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_run_lightweight_live_tick refreshes tactical strikes and delta-F cleanly."""
    import json
    from src.hud import html_dashboard as hd

    exports_dir = tmp_path / "exports"
    exports_dir.mkdir()
    csv_path = tmp_path / "options_prices_GCZ26.csv"
    pd.DataFrame(
        [
            {"strike": 4000.0},
            {"strike": 4025.0},
            {"strike": 4050.0},
        ]
    ).to_csv(csv_path, index=False)

    seed = {
        "spot_price": 4010.0,
        "implied_forward_price": 4035.5,
        "forward_dislocation_usd": 25.5,
        "call_wall": 4050.0,
        "put_wall": 4000.0,
        "zero_gamma_flip": 4020.0,
        "dte_days": 30.0,
        "strike_above": 4025.0,
        "strike_below": 4000.0,
        "dealer_hedge_futures_flow": 120.0,
    }
    (exports_dir / "version.json").write_text(json.dumps(seed), encoding="utf-8")

    fake_tape = {
        "available": True,
        "latest_price": 4031.25,
        "market_open": True,
        "chart_candles": [
            {"open": 4029.0, "high": 4032.0, "low": 4028.5, "close": 4031.25, "volume": 150}
            for _ in range(30)
        ],
    }
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(hd, "fetch_live_cme_m5_tape", lambda limit=8, include_htf=False: fake_tape)

    written = hd._run_lightweight_live_tick(input_csv=str(csv_path))
    assert written
    updated = json.loads((exports_dir / "version.json").read_text(encoding="utf-8"))
    assert updated["spot_price"] == 4031.25
    assert updated["strike_above"] == 4050.0
    assert updated["strike_below"] == 4025.0
    assert updated["forward_dislocation_usd"] == 4.25
    assert updated["flip_integrity_label"] != ""


