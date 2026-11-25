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
    assert "neiro-profile-wrapper" in comp["neiro_container_html"]
    assert "neiro-profile-canvas" in comp["neiro_container_html"]
    assert "btn-toggle-profile" in comp["nav_topbar_html"]
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
    assert "drawNeiroProfilePanel" in comp["neiro_js_script"]
    assert "computeVolumeProfile" in comp["neiro_js_script"]
    assert "toggleProfilePanel" in comp["neiro_js_script"]
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


def test_neiro_terminal_3sec_simplification_and_no_currenttfkey_bug():
    """Verify currentTfKey ReferenceError is fixed, canvas gauge removed, and realtime JS engines wired."""
    meta = {
        "spot_price": 4005.0,
        "atm_strike": 4000.0,
        "call_wall": 4050.0,
        "put_wall": 3980.0,
        "strike_above": 4025.0,
        "next_above": 4050.0,
        "strike_below": 4000.0,
        "next_below": 3975.0,
        "zero_gamma_flip": 4010.0,
        "total_net_gex": -15.0,
        "regime": "SHORT_GAMMA",
        "dte_days": 5.0,
        "step": 25.0,
        "atr_5m": 3.8,
        "air_pockets": [{"from": 4025.0, "to": 4050.0, "severity": "HIGH"}],
    }
    df = pd.DataFrame([
        {"strike": 3980.0, "callOpenInterest": 200, "putOpenInterest": 1200, "callVolume": 30, "putVolume": 180, "netGEX": -10.0, "netVEX": -1.0, "netCHEX": -0.2},
        {"strike": 4000.0, "callOpenInterest": 600, "putOpenInterest": 700, "callVolume": 100, "putVolume": 120, "netGEX": -5.0, "netVEX": 0.5, "netCHEX": 0.2},
        {"strike": 4025.0, "callOpenInterest": 900, "putOpenInterest": 300, "callVolume": 200, "putVolume": 40, "netGEX": 8.0, "netVEX": 1.2, "netCHEX": 0.4},
    ])
    comp = render_neiro_orderflow_component(meta, df)
    js = comp["neiro_js_script"]
    nav = comp["nav_topbar_html"]
    hud = comp["neiro_container_html"]

    # Dead currentTfKey bug must never reappear
    assert "currentTfKey" not in js
    assert "let currentTf = '1m'" in js

    # Overlapping Top-Center Canvas Gauge & live price-line CVD/VPIN badge must be removed
    assert "NẾN M1 Δ:" not in js
    assert "fpTxt" not in js

    # Toggle buttons & compact HUD controls
    assert "toggleOverlayMode()" in nav
    assert "toggleChartHeight()" in nav
    assert 'id="neiro-tf-badge"' in nav
    assert 'id="top-vpin-val"' in nav
    assert hud.count('class="hud-item"') == 5
    assert 'id="hud-4actions-val"' not in hud

    # Air Pockets and primary strike barriers (CẢN TRÊN / SÀN DƯỚI + Trạm Options) must always draw in Compact mode
    draw_fn_src = js[js.index("function drawNeiroOverlay") :]
    assert draw_fn_src.index("airPockets.forEach") < draw_fn_src.index("if (!overlayCompactMode)")
    keylevels_src = draw_fn_src[draw_fn_src.index("const keyLevels = [") :]
    for always_on_lvl in (
        "CẢN TRÊN $",
        "SÀN DƯỚI $",
        "TRẠM TRÊN $",
        "TRẠM DƯỚI $",
        "TƯỜNG LỚN ↑ $",
        "TƯỜNG LỚN ↓ $",
    ):
        assert keylevels_src.index(always_on_lvl) < keylevels_src.index("if (!overlayCompactMode)")
    for tier_lbl in (
        "RỖNG CỰC MẠNH",
        "RỖNG MẠNH",
        "MỎNG NHẸ",
        "rgba(249, 115, 22,",
        "rgba(56, 189, 248,",
        "rgba(148, 163, 184,",
    ):
        assert tier_lbl in draw_fn_src

    # Realtime ADR-028 JS parity engines & Cloud Worker dual-mode polling (ADR-030)
    for fn_name in (
        "computeLiveVpinBvcJs",
        "computeM5AtrJs",
        "resolveAdaptiveStrikesJs",
        "computeTacticalMatrixJs",
        "updateRealtimeTacticalCockpit",
        "updateSyncBadgeHonest",
        "normalizeCloudWorkerUrl",
        "getCloudFeedWorkerUrl",
        "promptCloudFeedUrl",
        "fetchJsonWithTimeout",
    ):
        assert fn_name in js
    assert 'id="btn-cloud-worker"' in nav
    assert "WORKER LIVE (XAUUSDF" in js
    assert "WORKER CLOUD (GC=F)" in js
    assert "cloud_feed_url" in js
    assert "127.0.0.1:8765" not in js
    assert "LIVE BRIDGE" not in js
    assert "lastBridgeSuccessEpoch" not in js


def test_neiro_terminal_live_candle_merge_no_future_gap_or_setdata_thrash(tmp_path):
    """Root-cause guard: polling delayed Yahoo candles (or unaligned 0-vol dots) must NOT
    fabricate a +10m future activeCandle from Date.now() or trigger setData() on subsequent updates."""
    import json
    import shutil
    import subprocess

    node_bin = shutil.which("node")
    if not node_bin:
        import pytest
        pytest.skip("Node.js not installed")

    meta = {"spot_price": 3850.0, "atm_strike": 3850.0, "call_wall": 4000.0, "put_wall": 3700.0}
    df = pd.DataFrame([
        {"strike": 3850.0, "callOpenInterest": 500, "putOpenInterest": 500, "callVolume": 50, "putVolume": 50, "netGEX": -10.0, "netVEX": 1.0, "netCHEX": -1.0},
    ])
    js_raw = render_neiro_orderflow_component(meta, df)["neiro_js_script"]
    js_body = js_raw.replace("<script>", "").replace("</script>", "")

    harness = """
let setDataCalls = 0;
let updateCalls = 0;
let lastSeriesTime = 0;
globalThis.window = globalThis;
globalThis.localStorage = { getItem: () => null, setItem: () => {}, removeItem: () => {} };
globalThis.requestAnimationFrame = () => {};
globalThis.setInterval = () => {};
globalThis.setTimeout = () => {};
globalThis.addEventListener = () => {};
globalThis.document = {
    getElementById: () => null,
    querySelectorAll: () => [],
};
globalThis.LightweightCharts = { LineStyle: { Dashed: 1, Solid: 0 } };
""" + js_body + """
candleSeries = {
    setData: (bars) => {
        setDataCalls += 1;
        if (bars.length) lastSeriesTime = bars[bars.length - 1].time;
    },
    update: (bar) => {
        if (bar.time < lastSeriesTime) {
            throw new Error("Cannot update oldest data: " + bar.time + " < " + lastSeriesTime);
        }
        lastSeriesTime = bar.time;
        updateCalls += 1;
    },
};

// Simulate 10m-delayed Yahoo candles with trailing unaligned 0-vol dots (:35, :40, :44)
const delayedBase = Math.floor(Date.now() / 1000) - 600;
const t1 = delayedBase - (delayedBase % 60) - 60;
const t2 = t1 + 60;
const poll1 = [
    { time: t1, open: 3849.5, high: 3850.3, low: 3849.5, close: 3850.1, volume: 89 },
    { time: t2, open: 3850.1, high: 3852.0, low: 3849.6, close: 3850.1, volume: 40 },
    { time: t2 + 35, open: 3851.7, high: 3851.7, low: 3851.7, close: 3851.7, volume: 0 },
    { time: t2 + 44, open: 3850.9, high: 3850.9, low: 3850.9, close: 3850.9, volume: 0 },
];
window.INITIAL_CANDLES = [poll1[0]];
lastSeriesTime = t1;
mergeLiveCandles(poll1, "1m", false);
applyLiveTick(3850.9, null, true);

// Poll 2 (3 seconds later) with updated price on t2
const poll2 = [
    poll1[0],
    { time: t2, open: 3850.1, high: 3852.0, low: 3849.6, close: 3851.2, volume: 55 },
    { time: t2 + 48, open: 3851.2, high: 3851.2, low: 3851.2, close: 3851.2, volume: 0 },
];
mergeLiveCandles(poll2, "1m", false);
applyLiveTick(3851.2, null, true);

console.log(JSON.stringify({
    setDataCalls,
    updateCalls,
    activeTime: activeCandle.time,
    expectedTime: t2,
    candleTimes: window.INITIAL_CANDLES.map(c => c.time),
    lastClose: activeCandle.close,
}));
"""
    script_path = tmp_path / "terminal_harness.js"
    script_path.write_text(harness, encoding="utf-8")
    out_path = tmp_path / "terminal_out.txt"
    err_path = tmp_path / "terminal_err.txt"
    with out_path.open("w", encoding="utf-8") as out_fh, err_path.open("w", encoding="utf-8") as err_fh:
        rc = subprocess.call(
            [node_bin, str(script_path)],
            stdin=subprocess.DEVNULL,
            stdout=out_fh,
            stderr=err_fh,
            timeout=15,
        )
    stdout_txt = out_path.read_text(encoding="utf-8")
    stderr_txt = err_path.read_text(encoding="utf-8")
    assert rc == 0, f"Node harness failed: {stderr_txt or stdout_txt}"
    res = json.loads(stdout_txt.strip())
    assert res["setDataCalls"] == 0, f"Expected 0 setData fallbacks, got {res}"
    assert res["activeTime"] == res["expectedTime"], f"Future gap bug: {res}"
    assert res["candleTimes"] == [res["expectedTime"] - 60, res["expectedTime"]], f"Unaligned dots leaked: {res}"
    assert res["lastClose"] == 3851.2


def test_neiro_terminal_live_candle_merge_backfills_multi_bar_gap_via_setdata(tmp_path):
    """Regression guard for chart drop-off bug: when live feed or version.json returns multiple
    new/missing bars ahead of what candleSeries currently renders (e.g. stale snapshot or tab sleep),
    mergeLiveCandles must call setData() once so intermediate candles are NOT skipped, then revert to
    update() on subsequent 3s ticks; and stale version.json must not clobber newer Worker candles."""
    import json
    import shutil
    import subprocess

    node_bin = shutil.which("node")
    if not node_bin:
        import pytest
        pytest.skip("Node.js not installed")

    meta = {"spot_price": 3851.2, "atm_strike": 3850.0, "call_wall": 4000.0, "put_wall": 3700.0}
    df = pd.DataFrame([
        {"strike": 3850.0, "callOpenInterest": 500, "putOpenInterest": 500, "callVolume": 50, "putVolume": 50, "netGEX": -10.0, "netVEX": 1.0, "netCHEX": -1.0},
    ])
    js_raw = render_neiro_orderflow_component(meta, df)["neiro_js_script"]
    js_body = js_raw.replace("<script>", "").replace("</script>", "")

    harness = """
let setDataCalls = 0;
let updateCalls = 0;
let renderedBars = [];
globalThis.window = globalThis;
globalThis.localStorage = { getItem: () => null, setItem: () => {}, removeItem: () => {} };
globalThis.requestAnimationFrame = () => {};
globalThis.setInterval = () => {};
globalThis.setTimeout = () => {};
globalThis.addEventListener = () => {};
globalThis.document = {
    getElementById: () => null,
    querySelectorAll: () => [],
};
globalThis.LightweightCharts = { LineStyle: { Dashed: 1, Solid: 0 } };
""" + js_body + """
let visibleRangeSetCalls = 0;
neiroChart = {
    timeScale: () => ({
        getVisibleLogicalRange: () => ({ from: 0, to: renderedBars.length + 8 }),
        setVisibleLogicalRange: () => { visibleRangeSetCalls += 1; },
    }),
};
candleSeries = {
    setData: (bars) => {
        setDataCalls += 1;
        renderedBars = bars.map(b => ({ ...b }));
    },
    update: (bar) => {
        const last = renderedBars[renderedBars.length - 1];
        if (last && bar.time < last.time) {
            throw new Error("Cannot update oldest data: " + bar.time + " < " + last.time);
        }
        if (last && last.time === bar.time) {
            renderedBars[renderedBars.length - 1] = { ...bar };
        } else {
            renderedBars.push({ ...bar });
        }
        updateCalls += 1;
    },
};

// 1. Initial stale snapshot ending at 03:49 VN
const tSnapshotEnd = 1794948540;
const initialSnap = [];
for (let i = 10; i >= 0; i--) {
    const t = tSnapshotEnd - i * 60;
    initialSnap.push({ time: t, open: 3852.0, high: 3853.0, low: 3850.6, close: 3851.2, volume: 30 });
}
window.INITIAL_CANDLES = initialSnap;
window.INITIAL_TF_CANDLES = { "1m": initialSnap.slice() };
buildHistoricalGoldBars(60, "1m");
const setDataAfterInit = setDataCalls;

// 2. Worker poll returns 20 newer bars after gap (e.g. 04:13..04:32) dropping to 3824.9
const gapBars = [];
const tGapStart = tSnapshotEnd + 24 * 60;
for (let i = 0; i < 20; i++) {
    const px = 3850.0 - i * 1.25;
    gapBars.push({ time: tGapStart + i * 60, open: px + 0.5, high: px + 0.8, low: px - 0.5, close: px, volume: 100 });
}
mergeLiveCandles(gapBars, "1m", false);
const renderedCountAfterGap = renderedBars.length;
const setDataAfterGap = setDataCalls;

// 3. Subsequent 3s live tick on the same last bar must use update(), NOT setData()
const updatedLast = { ...gapBars[gapBars.length - 1], close: 3824.9, low: 3824.0 };
mergeLiveCandles([...gapBars.slice(0, -1), updatedLast], "1m", false);
const setDataAfterTick = setDataCalls;
const updateAfterTick = updateCalls;

// 4. Tab-sleep case: 3 bars jump ahead at once
const sleepBars = [];
const tLast = updatedLast.time;
for (let i = 1; i <= 3; i++) {
    sleepBars.push({ time: tLast + i * 60, open: 3824.9, high: 3826.0, low: 3824.0, close: 3825.5, volume: 80 });
}
mergeLiveCandles([...gapBars, ...sleepBars], "1m", false);
const renderedCountAfterSleep = renderedBars.length;
const setDataAfterSleep = setDataCalls;

// 5. Stale version.json older than activeCandle must NOT revert currentGoldPrice backwards
lastCloudWorkerEpoch = 0;
hotPatchCloudMeta({
    timestamp_utc: "2026-11-18T01:19:13+00:00",
    spot_price: 3827.3,
    recent_candles: [gapBars[0]],
});

console.log(JSON.stringify({
    setDataAfterInit,
    renderedCountAfterGap,
    expectedAfterGap: initialSnap.length + gapBars.length,
    setDataAfterGap,
    setDataAfterTick,
    updateAfterTick,
    renderedCountAfterSleep,
    expectedAfterSleep: initialSnap.length + gapBars.length + sleepBars.length,
    setDataAfterSleep,
    priceAfterStalePatch: currentGoldPrice,
    activeTimeAfterStalePatch: activeCandle.time,
    expectedActiveTime: sleepBars[sleepBars.length - 1].time,
}));
"""
    script_path = tmp_path / "terminal_backfill_harness.js"
    script_path.write_text(harness, encoding="utf-8")
    out_path = tmp_path / "backfill_out.txt"
    err_path = tmp_path / "backfill_err.txt"
    with out_path.open("w", encoding="utf-8") as out_fh, err_path.open("w", encoding="utf-8") as err_fh:
        rc = subprocess.call(
            [node_bin, str(script_path)],
            stdin=subprocess.DEVNULL,
            stdout=out_fh,
            stderr=err_fh,
            timeout=15,
        )
    stdout_txt = out_path.read_text(encoding="utf-8")
    stderr_txt = err_path.read_text(encoding="utf-8")
    assert rc == 0, f"Node harness failed: {stderr_txt or stdout_txt}"
    res = json.loads(stdout_txt.strip())
    assert res["renderedCountAfterGap"] == res["expectedAfterGap"], f"Intermediate gap candles were dropped: {res}"
    assert res["setDataAfterGap"] == res["setDataAfterInit"] + 1
    assert res["setDataAfterTick"] == res["setDataAfterGap"], f"Repeated 3s tick caused setData thrash: {res}"
    assert res["updateAfterTick"] >= 1
    assert res["renderedCountAfterSleep"] == res["expectedAfterSleep"], f"Tab-sleep bars were skipped: {res}"
    assert res["setDataAfterSleep"] == res["setDataAfterGap"] + 1
    assert res["activeTimeAfterStalePatch"] == res["expectedActiveTime"]
    assert res["priceAfterStalePatch"] == 3825.5


def test_recompute_live_greeks_and_walls_vectorized_js(tmp_path):
    import json
    import shutil
    import subprocess
    meta = {
        "spot_price": 2640.0,
        "atm_strike": 2640.0,
        "call_wall": 2700.0,
        "call_wall_oi": 5200,
        "call_wall_siege": 0.18,
        "put_wall": 2600.0,
        "put_wall_oi": 4800,
        "put_wall_siege": 0.12,
        "total_net_gex": 18.5,
        "total_net_vex": 4.2,
        "total_net_chex": 1.5,
        "expected_move_1s": 32.0,
        "rule16_daily_move": 14.5,
        "strike_above": 2660.0,
        "next_above": 2680.0,
        "strike_below": 2620.0,
        "next_below": 2600.0,
        "zero_gamma_flip": 2630.0,
        "dte_days": 8.0,
        "air_pockets": [],
    }
    df = pd.DataFrame([
        {"strike": 2600.0, "callOpenInterest": 600, "putOpenInterest": 3500, "callVolume": 150, "putVolume": 600, "netGEX": -12.0, "netVEX": -1.2, "netCHEX": -0.5},
        {"strike": 2640.0, "callOpenInterest": 3200, "putOpenInterest": 1200, "callVolume": 800, "putVolume": 750, "netGEX": 25.0, "netVEX": 3.1, "netCHEX": 1.1},
        {"strike": 2680.0, "callOpenInterest": 4500, "putOpenInterest": 300, "callVolume": 900, "putVolume": 200, "netGEX": 18.0, "netVEX": 2.3, "netCHEX": 0.8},
    ])
    comp = render_neiro_orderflow_component(meta, df)
    js = comp["neiro_js_script"]
    assert "recomputeLiveGreeksAndWalls" in js
    assert "recomputeLiveGreeksAndWalls(spot)" in js

    node_bin = shutil.which("node")
    if not node_bin:
        return

    js_body = js.split("<script>", 1)[1].rsplit("</script>", 1)[0]
    harness = r"""
global.window = global;
global.localStorage = { getItem: () => null, setItem: () => {}, removeItem: () => {} };
global.requestAnimationFrame = () => {};
global.setInterval = () => {};
global.setTimeout = () => {};
global.addEventListener = () => {};
global.LightweightCharts = { LineStyle: { Dashed: 1, Solid: 0 } };
""" + js_body + r"""
let docElements = {};
global.document = {
    getElementById: (id) => {
        if (!docElements[id]) docElements[id] = { innerText: '', style: {} };
        return docElements[id];
    },
    querySelectorAll: () => []
};

// 1. Initial State at 2640
recomputeLiveGreeksAndWalls(2640.0);
const gex2640_at2640 = window.INITIAL_OPTIONS.find(o => o.strike === 2640).currentNetGEX;
const gex2680_at2640 = window.INITIAL_OPTIONS.find(o => o.strike === 2680).currentNetGEX;
const totalGex_at2640 = window.INITIAL_META.total_net_gex;

// 2. Price jumps to 2680
recomputeLiveGreeksAndWalls(2680.0);
const gex2640_at2680 = window.INITIAL_OPTIONS.find(o => o.strike === 2640).currentNetGEX;
const gex2680_at2680 = window.INITIAL_OPTIONS.find(o => o.strike === 2680).currentNetGEX;
const totalGex_at2680 = window.INITIAL_META.total_net_gex;

console.log(JSON.stringify({
    gex2640_at2640,
    gex2680_at2640,
    totalGex_at2640,
    gex2640_at2680,
    gex2680_at2680,
    totalGex_at2680,
    callWall: window.INITIAL_META.call_wall,
    putWall: window.INITIAL_META.put_wall,
    zeroGammaFlip: window.INITIAL_META.zero_gamma_flip
}));
"""
    script_path = tmp_path / "test_greeks_harness.js"
    script_path.write_text(harness, encoding="utf-8")
    out_path = tmp_path / "greeks_out.txt"
    err_path = tmp_path / "greeks_err.txt"
    with out_path.open("w", encoding="utf-8") as out_fh, err_path.open("w", encoding="utf-8") as err_fh:
        rc = subprocess.call(
            [node_bin, str(script_path)],
            stdin=subprocess.DEVNULL,
            stdout=out_fh,
            stderr=err_fh,
            timeout=15,
        )
    stdout_txt = out_path.read_text(encoding="utf-8")
    stderr_txt = err_path.read_text(encoding="utf-8")
    assert rc == 0, f"Node harness failed: {stderr_txt or stdout_txt}"
    res = json.loads(stdout_txt.strip())
    assert res["gex2680_at2680"] > res["gex2680_at2640"], f"GEX elasticity failed: {res}"
    assert res["gex2640_at2640"] > res["gex2640_at2680"], f"GEX elasticity failed: {res}"
    assert res["callWall"] >= 2640.0
    assert res["putWall"] <= 2680.0


def test_adr032_volume_profile_and_side_by_side_panels(tmp_path):
    """Verify ADR-032: 2-Panel Side-by-Side architecture & Volume Profile math."""
    import shutil
    import subprocess
    import json

    meta = {
        "spot_price": 2650.0,
        "atm_strike": 2650.0,
        "call_wall": 2680.0,
        "put_wall": 2620.0,
        "zero_gamma_flip": 2650.0,
        "air_pockets": [],
    }
    df = pd.DataFrame([
        {"strike": 2640.0, "callVolume": 50, "putVolume": 50, "callOpenInterest": 100, "putOpenInterest": 100, "netGEX": -2.0, "netVEX": 0.5, "netCHEX": 0.1},
        {"strike": 2650.0, "callVolume": 100, "putVolume": 100, "callOpenInterest": 500, "putOpenInterest": 500, "netGEX": 10.0, "netVEX": 2.0, "netCHEX": 0.5},
        {"strike": 2660.0, "callVolume": 30, "putVolume": 30, "callOpenInterest": 200, "putOpenInterest": 200, "netGEX": 4.0, "netVEX": 0.8, "netCHEX": 0.2},
    ])
    comp = render_neiro_orderflow_component(meta, df)
    js = comp["neiro_js_script"]
    html = comp["neiro_container_html"]
    topbar = comp["nav_topbar_html"]

    # 1. Structural checks
    assert "id=\"tv-chart-wrapper\"" in html
    assert "id=\"neiro-profile-wrapper\"" in html
    assert "id=\"neiro-profile-canvas\"" in html
    assert "id=\"profile-poc-tag\"" in html
    assert "id=\"btn-toggle-profile\"" in topbar
    assert "toggleProfilePanel" in js
    assert "computeVolumeProfile" in js
    assert "drawNeiroProfilePanel" in js
    assert "POC (Vol Max)" in js
    assert "VAH (Vùng Giá Trị 70%)" in js
    assert "VAL (Vùng Giá Trị 70%)" in js

    # 2. Node.js unit execution of computeVolumeProfile algorithm
    node_bin = shutil.which("node")
    if not node_bin:
        return

    # Extract computeVolumeProfile function definition
    fn_idx = js.find("function computeVolumeProfile(candles)")
    assert fn_idx != -1
    fn_end = js.find("function drawNeiroOverlay()", fn_idx)
    assert fn_end != -1
    fn_code = js[fn_idx:fn_end].strip()

    harness = f"""
    let window = {{
        INITIAL_OPTIONS: [
            {{ strike: 2640.0 }},
            {{ strike: 2650.0 }},
            {{ strike: 2660.0 }}
        ]
    }};
    let document = {{
        getElementById: function(id) {{
            return {{ innerText: '' }};
        }}
    }};
    let sessionPocPrice = null;
    let sessionVahPrice = null;
    let sessionValPrice = null;
    let sessionPocVol = 0;
    let sessionTotalVol = 0;
    let sessionVolByStrike = {{}};

    {fn_code}

    const testCandles = [
        {{ time: 100, open: 2649.0, high: 2651.0, low: 2648.5, close: 2650.5, volume: 500 }},
        {{ time: 160, open: 2650.0, high: 2652.0, low: 2649.5, close: 2651.0, volume: 600 }},
        {{ time: 220, open: 2651.0, high: 2658.0, low: 2651.0, close: 2657.0, volume: 150 }},
        {{ time: 280, open: 2648.0, high: 2649.0, low: 2641.0, close: 2642.0, volume: 200 }},
    ];

    computeVolumeProfile(testCandles);

    console.log(JSON.stringify({{
        poc: sessionPocPrice,
        pocVol: sessionPocVol,
        vah: sessionVahPrice,
        val: sessionValPrice,
        totalVol: sessionTotalVol,
        volByStrike: sessionVolByStrike
    }}));
    """
    script_path = tmp_path / "test_vp_harness.js"
    script_path.write_text(harness, encoding="utf-8")
    out_path = tmp_path / "vp_out.txt"
    err_path = tmp_path / "vp_err.txt"
    with out_path.open("w", encoding="utf-8") as out_fh, err_path.open("w", encoding="utf-8") as err_fh:
        rc = subprocess.call(
            [node_bin, str(script_path)],
            stdin=subprocess.DEVNULL,
            stdout=out_fh,
            stderr=err_fh,
            timeout=15,
        )
    out_txt = out_path.read_text(encoding="utf-8")
    err_txt = err_path.read_text(encoding="utf-8")
    assert rc == 0, f"Node harness failed: {err_txt or out_txt}"
    res = json.loads(out_txt.strip())

    assert res["poc"] is not None
    assert res["pocVol"] > 0
    assert res["totalVol"] == 1450
    assert res["val"] <= res["poc"] <= res["vah"]
    assert res["volByStrike"]["2650"] > res["volByStrike"]["2660"]


def test_neiro_terminal_strike_oi_badges_and_js_python_parity(tmp_path):
    """Verify tactical strike lines and Spine HUD display OI + MỎNG/VỪA/DÀY tags matching Python."""
    import json
    import shutil
    import subprocess
    from src.hud.html_dashboard import summarize_strike_oi

    df = pd.DataFrame([
        {"strike": 3500.0, "callOpenInterest": 233, "putOpenInterest": 6000, "callVolume": 10, "putVolume": 200, "netGEX": -20.0, "netVEX": -1.0, "netCHEX": -0.2},
        {"strike": 3540.0, "callOpenInterest": 20,  "putOpenInterest": 269,  "callVolume": 5,  "putVolume": 11,  "netGEX": -2.0,  "netVEX": -0.1, "netCHEX": -0.05},
        {"strike": 3545.0, "callOpenInterest": 76,  "putOpenInterest": 842,  "callVolume": 4,  "putVolume": 52,  "netGEX": -5.0,  "netVEX": -0.3, "netCHEX": -0.1},
        {"strike": 3550.0, "callOpenInterest": 338, "putOpenInterest": 2329, "callVolume": 85, "putVolume": 423, "netGEX": 12.0,  "netVEX": 1.1,  "netCHEX": 0.4},
        {"strike": 3555.0, "callOpenInterest": 58,  "putOpenInterest": 241,  "callVolume": 15, "putVolume": 21,  "netGEX": 1.0,   "netVEX": 0.2,  "netCHEX": 0.05},
    ])
    meta = {
        "spot_price": 3551.45,
        "atm_strike": 3550.0,
        "call_wall": 3600.0,
        "put_wall": 3500.0,
        "strike_above": 3555.0,
        "next_above": 3560.0,
        "strike_below": 3550.0,
        "next_below": 3545.0,
        "zero_gamma_flip": 3580.0,
    }
    comp = render_neiro_orderflow_component(meta, df)
    js = comp["neiro_js_script"]

    assert "summarizeStrikeOiJs" in js
    assert "saOi.tag" in js
    assert "sbOi.tag" in js
    assert "spine-below-oi" in js
    assert "spine-above-oi" in js

    # Parity check between JS summarizeStrikeOiJs and Python summarize_strike_oi
    py_3540 = summarize_strike_oi(df, 3540.0, 3551.45)
    py_3545 = summarize_strike_oi(df, 3545.0, 3551.45)
    py_3550 = summarize_strike_oi(df, 3550.0, 3551.45)
    py_missing = summarize_strike_oi(df, 3560.0, 3551.45)

    assert py_3540 == (289, "MỎNG", "OI 289 (MỎNG)")
    assert py_3545 == (918, "VỪA", "OI 918 (VỪA)")
    assert py_3550 == (2667, "DÀY", "OI 2,667 (DÀY)")
    assert py_missing == (0, "MỎNG", "OI 0 (MỎNG)")

    node_bin = shutil.which("node")
    if not node_bin:
        return

    fn_start = js.index("function summarizeStrikeOiJs")
    fn_end = js.index("function sizeXauusdJs")
    fn_code = js[fn_start:fn_end]
    opts_json = js.split("window.INITIAL_OPTIONS = ")[1].split(";\n")[0]

    harness = f"""
    const window = {{ INITIAL_OPTIONS: {opts_json}, INITIAL_META: {{ spot: 3551.45 }} }};
    {fn_code}
    console.log(JSON.stringify({{
        s3540: summarizeStrikeOiJs(3540.0, 3551.45),
        s3545: summarizeStrikeOiJs(3545.0, 3551.45),
        s3550: summarizeStrikeOiJs(3550.0, 3551.45),
        s3560: summarizeStrikeOiJs(3560.0, 3551.45),
    }}));
    """
    script_path = tmp_path / "test_oi_tag_harness.js"
    script_path.write_text(harness, encoding="utf-8")
    out_path = tmp_path / "oi_tag_out.txt"
    with out_path.open("w", encoding="utf-8") as fh:
        rc = subprocess.call([node_bin, str(script_path)], stdin=subprocess.DEVNULL, stdout=fh, stderr=subprocess.STDOUT, timeout=15)
    assert rc == 0, out_path.read_text(encoding="utf-8")
    res = json.loads(out_path.read_text(encoding="utf-8").strip())
    assert (res["s3540"]["oi"], res["s3540"]["tier"], res["s3540"]["tag"]) == py_3540
    assert (res["s3545"]["oi"], res["s3545"]["tier"], res["s3545"]["tag"]) == py_3545
    assert (res["s3550"]["oi"], res["s3550"]["tier"], res["s3550"]["tag"]) == py_3550
    assert (res["s3560"]["oi"], res["s3560"]["tier"], res["s3560"]["tag"]) == py_missing
    assert "dispatchGithubSyncDirect" in js
    assert "localStorage.removeItem('NEIRO_GITHUB_PAT')" in js






