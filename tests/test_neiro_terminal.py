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

    # Verify key elements in HTML components (standardized with Neiro-NQ-Quant)
    assert "NEIRO ORDERFLOW" in comp["nav_topbar_html"]
    assert "SPOT CME:" in comp["nav_topbar_html"]
    assert "M1 INTRADAY" in comp["nav_topbar_html"]

    assert "neiro-view-container" in comp["neiro_container_html"]
    assert "neiro-tv-chart" in comp["neiro_container_html"]
    assert "neiro-canvas" in comp["neiro_container_html"]
    assert "GAMMA SQUEEZE" in comp["neiro_container_html"]
    assert "neiro-floating-hud" in comp["neiro_container_html"]

    assert "switchTerminalView" in comp["neiro_js_script"]
    assert "initNeiroGoldChart" in comp["neiro_js_script"]
    assert "INITIAL_CANDLES" in comp["neiro_js_script"]
    assert "INITIAL_TF_CANDLES" in comp["neiro_js_script"]
    assert "isCmeGlobexMarketOpen" in comp["neiro_js_script"]
    assert "pollLiveYahooChart" in comp["neiro_js_script"]
    assert "formatVnTimestamp" in comp["neiro_js_script"]
    assert "resampleBars" in comp["neiro_js_script"]
    assert "generateRealisticGoldCandles" in comp["neiro_js_script"]
    assert "drawNeiroOverlay" in comp["neiro_js_script"]
    assert "AIR POCKET VACUUM" in comp["neiro_js_script"]


def test_neiro_terminal_adr026_zero_fake_vtick_fvg_and_squeeze_ladder():
    """Verify ADR-026: no synthetic vTick fabrication, O(1) squeeze_ladder lookup, FVG & Post-Sweep HUD."""
    meta = {
        "spot_price": 4005.0,
        "atm_strike": 4005.0,
        "call_wall": 4050.0,
        "put_wall": 3980.0,
        "strike_above": 4020.0,
        "next_above": 4050.0,
        "strike_below": 3990.0,
        "next_below": 3980.0,
        "zero_gamma_flip": 4000.0,
        "air_pockets": [{"from": 4020.0, "to": 4045.0, "severity": "HIGH"}],
        "squeeze_ladder": {
            "4000.0": {
                "strike": 4000.0,
                "squeeze_trigger": 4003.0,
                "squeeze_tp": 4020.0,
                "squeeze_sl": 3998.5,
                "waterfall_trigger": 3997.0,
                "waterfall_tp": 3981.0,
                "waterfall_sl": 4001.5,
                "regime": "SHORT_GAMMA_ACCELERATOR",
            }
        },
        "institutional_orderflow": {
            "dynamic_vacuum": {
                "vacuum_active": True,
                "regime": "DYNAMIC_LIQUIDITY_VACUUM",
                "label_vi": "CHÂN KHÔNG ĐỘNG (Q95)",
            },
            "institutional_fvgs": [
                {
                    "direction": "BULLISH",
                    "low": 3995.0,
                    "high": 4002.0,
                    "midpoint_50": 3998.5,
                    "zone_75": 3996.75,
                    "vacuum_backed": True,
                    "level_backed": True,
                }
            ],
            "post_sweep_execution": {
                "post_sweep_regime": "POST_SWEEP_V_SHAPE",
                "allow_reversal": True,
                "direction": "BULLISH",
                "entry_style": "MARKET_OR_STOP_BREAK",
                "target_zone": [4005.0, 4005.0],
                "label_vi": "V-SHAPE BULLISH: VÀO LỆNH XÁC NHẬN ($4,005.00)",
            },
        },
    }
    df = pd.DataFrame([
        {"strike": 3990.0, "callOpenInterest": 200, "putOpenInterest": 900, "callVolume": 50, "putVolume": 120, "netGEX": -8.0, "netVEX": -1.0, "netCHEX": -0.2},
        {"strike": 4000.0, "callOpenInterest": 800, "putOpenInterest": 800, "callVolume": 150, "putVolume": 150, "netGEX": 12.0, "netVEX": 1.5, "netCHEX": 0.4},
        {"strike": 4020.0, "callOpenInterest": 1200, "putOpenInterest": 300, "callVolume": 200, "putVolume": 40, "netGEX": 16.0, "netVEX": 2.0, "netCHEX": 0.5},
    ])

    comp = render_neiro_orderflow_component(meta, df)
    js = comp["neiro_js_script"]
    hud = comp["neiro_container_html"]

    # Zero synthetic tick volume math
    assert "Math.round(2 + Math.abs(dp) * 25)" not in js
    assert "lastBar.volume || 120" not in js

    # Wired O(1) squeeze ladder & HUD IDs
    assert 'id="hud-sqz-up"' in hud
    assert 'id="hud-sqz-down"' in hud
    assert 'id="hud-post-sweep-val"' in hud
    assert "squeeze_ladder" in js
    assert "updateSqueezeHud" in js

    # Dynamic Vacuum / FVG / Post-Sweep HUD & Canvas wiring
    assert "institutional_fvgs" in js
    assert "FVG 50%" in js or "INSTITUTIONAL FVG" in js
    assert "V-SHAPE BULLISH" in hud

    # Ensure artificial random walk, Binance PAXG proxy, and forced page reloads were eliminated
    assert "Math.random()" not in comp["neiro_js_script"]
    assert "paxgusdt@aggTrade" not in comp["neiro_js_script"]
    assert "window.location.reload()" not in comp["neiro_js_script"]

