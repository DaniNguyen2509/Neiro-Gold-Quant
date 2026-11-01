"""Unit tests for src/hud/neiro_terminal.py."""
import pandas as pd
from src.hud.neiro_terminal import render_neiro_orderflow_component


def test_render_neiro_orderflow_component():
    meta = {
        "spot_price": 2700.0,
        "atm_strike": 2700.0,
        "call_wall": 2740.0,
        "call_wall_oi": 5200,
        "call_wall_siege": 0.18,
        "put_wall": 2660.0,
        "put_wall_oi": 4800,
        "put_wall_siege": 0.12,
        "total_net_gex": 18.5,
        "total_net_vex": 4.2,
        "total_net_chex": 1.5,
        "expected_move_1s": 32.0,
        "rule16_daily_move": 14.5,
        "strike_above": 2720.0,
        "next_above": 2740.0,
        "strike_below": 2680.0,
        "next_below": 2660.0,
        "zero_gamma_flip": 2695.0,
        "dte_days": 7.0,
        "gvz_iv": 18.2,
        "air_pockets": [{"from": 2660.0, "to": 2640.0, "severity": "HIGH"}],
    }

    df = pd.DataFrame([
        {"strike": 2680.0, "callOpenInterest": 1200, "putOpenInterest": 3500, "callVolume": 150, "putVolume": 600, "netGEX": -12.0, "netVEX": -1.2, "netCHEX": -0.5},
        {"strike": 2700.0, "callOpenInterest": 3000, "putOpenInterest": 2800, "callVolume": 800, "putVolume": 750, "netGEX": 25.0, "netVEX": 3.1, "netCHEX": 1.1},
        {"strike": 2720.0, "callOpenInterest": 4500, "putOpenInterest": 1100, "callVolume": 900, "putVolume": 200, "netGEX": 18.0, "netVEX": 2.3, "netCHEX": 0.8},
    ])

    comp = render_neiro_orderflow_component(meta, df)

    assert "neiro_css" in comp
    assert "nav_topbar_html" in comp
    assert "neiro_container_html" in comp
    assert "neiro_js_script" in comp

    # Verify key elements in HTML components
    assert "NEIRO ALL-IN-ONE ORDERFLOW & GREEKS TERMINAL" in comp["nav_topbar_html"]
    assert "$100.0/oz" in comp["nav_topbar_html"]

    assert "neiro-view-container" in comp["neiro_container_html"]
    assert "neiro-tv-chart" in comp["neiro_container_html"]
    assert "neiro-canvas" in comp["neiro_container_html"]
    assert "GAMMA SQUEEZE ↑" in comp["neiro_container_html"]

    assert "switchTerminalView" in comp["neiro_js_script"]
    assert "initNeiroGoldChart" in comp["neiro_js_script"]
    assert "INITIAL_CANDLES" in comp["neiro_js_script"]
    assert "resampleBars" in comp["neiro_js_script"]
    assert "generateRealisticGoldCandles" in comp["neiro_js_script"]
    assert "drawNeiroOverlay" in comp["neiro_js_script"]
    assert "AIR POCKET VACUUM" in comp["neiro_js_script"]
