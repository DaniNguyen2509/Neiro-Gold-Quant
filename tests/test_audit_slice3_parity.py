"""Slice 3 regression tests: MQL5 ASCII compliance, Python-JS parity, and quant invariants."""
from __future__ import annotations

import datetime
import json
import pathlib
import re
import subprocess
import pandas as pd
import pytest


def _extract_neiro_script() -> str:
    from src.hud.neiro_terminal import render_neiro_orderflow_component

    meta = {
        "spot_price": 4020.0,
        "atm_strike": 4020.0,
        "call_wall": 4060.0,
        "put_wall": 3980.0,
        "strike_above": 4025.0,
        "next_above": 4050.0,
        "strike_below": 4015.0,
        "next_below": 4000.0,
        "zero_gamma_flip": 4010.0,
        "total_net_gex": 12.0,
        "regime": "LONG_GAMMA",
        "dte_days": 8.0,
        "step": 5.0,
        "atr_5m": 4.0,
        "air_pockets": [],
    }
    df = pd.DataFrame(
        [
            {"strike": 3980.0, "callOpenInterest": 200, "putOpenInterest": 1200, "callVolume": 20, "putVolume": 100, "netGEX": -10.0, "netVEX": -1.0, "netCHEX": -0.2},
            {"strike": 4020.0, "callOpenInterest": 800, "putOpenInterest": 800, "callVolume": 120, "putVolume": 100, "netGEX": 12.0, "netVEX": 1.0, "netCHEX": 0.2},
            {"strike": 4060.0, "callOpenInterest": 1500, "putOpenInterest": 200, "callVolume": 180, "putVolume": 30, "netGEX": 15.0, "netVEX": 1.5, "netCHEX": 0.4},
        ]
    )
    comp = render_neiro_orderflow_component(meta, df)
    raw_js = comp["neiro_js_script"]
    m = re.search(r"<script>([\s\S]*)</script>", raw_js)
    assert m is not None
    return m.group(1)


def test_python_js_r2_half_cent_and_tactical_matrix_parity() -> None:
    """JS r2() and computeTacticalMatrixJs must match Python compute_tactical_intraday_matrix even on .825 boundaries."""
    from src.quant_engine.strategy import compute_tactical_intraday_matrix

    script_body = _extract_neiro_script()
    # atr_5m = 3.53125 -> 0.8 * 3.53125 = 2.825 (exact half-cent edge)
    # 1.4 * 4.160714285714286 = 5.825 (exact half-cent edge)
    kwargs = dict(
        spot=4021.0,
        strike_above=4017.0,
        next_above=4025.0,
        strike_below=4015.0,
        next_below=4010.0,
        step=5.0,
        call_wall=4060.0,
        put_wall=3980.0,
        zero_gamma=4010.0,
        major_up_wall=4060.0,
        major_down_wall=3980.0,
        has_up_air_pocket=False,
        has_down_air_pocket=False,
        regime="LONG_GAMMA",
        vpin_pct=31.0,
        call_wall_siege=0.05,
        put_wall_siege=0.05,
        session_tag="NY_COMEX_DEEP",
        atr_5m=3.53125,
    )
    py_mat = compute_tactical_intraday_matrix(**kwargs)

    driver = """
const vm = require('vm');
const fs = require('fs');
const payload = JSON.parse(fs.readFileSync(0, 'utf8'));
const noop = () => {};
const ctxProxy = new Proxy({}, { get: (_, prop) => (prop === 'measureText' ? () => ({ width: 10 }) : noop) });
const elStub = () => ({
    style: {}, classList: { add: noop, remove: noop, toggle: noop, contains: () => false },
    addEventListener: noop, appendChild: noop, setAttribute: noop, getAttribute: () => '',
    querySelectorAll: () => [], querySelector: () => null, textContent: '', innerHTML: '',
    clientWidth: 800, clientHeight: 540, width: 800, height: 540,
    getContext: () => ctxProxy,
    getBoundingClientRect: () => ({ width: 800, height: 540, top: 0, left: 0, right: 800, bottom: 540 })
});
const sandbox = {
    console, Math, Number, String, Boolean, Array, Object, Date, JSON, Set, Map, RegExp, isFinite, isNaN, parseFloat, parseInt,
    location: { protocol: 'http:', href: 'http://127.0.0.1/' }, addEventListener: noop,
    INITIAL_META: {}, INITIAL_OPTIONS: [],
    document: { getElementById: () => elStub(), querySelectorAll: () => [], querySelector: () => null, addEventListener: noop, createElement: () => elStub() },
    localStorage: { getItem: () => null, setItem: noop },
    ResizeObserver: function() { return { observe: noop, disconnect: noop }; },
    setInterval: () => 1, clearInterval: noop, setTimeout: () => 1, clearTimeout: noop,
    requestAnimationFrame: noop, fetch: () => new Promise(() => {}),
    EventSource: undefined,
    LightweightCharts: null,
};
sandbox.window = sandbox;
vm.runInNewContext(payload.script + `
;this.__out = {
    r2_edges: [0.825, 2.825, 3.825, 4019.825, 4019.835].map(v => r2(v)),
    matrix: computeTacticalMatrixJs(payload.jsParams)
};`, Object.assign(sandbox, { payload }));
console.log(JSON.stringify(sandbox.__out));
"""
    js_params = {
        "spot": kwargs["spot"],
        "strikeAbove": kwargs["strike_above"],
        "nextAbove": kwargs["next_above"],
        "strikeBelow": kwargs["strike_below"],
        "nextBelow": kwargs["next_below"],
        "step": kwargs["step"],
        "callWall": kwargs["call_wall"],
        "putWall": kwargs["put_wall"],
        "zeroGamma": kwargs["zero_gamma"],
        "majorUpWall": kwargs["major_up_wall"],
        "majorDownWall": kwargs["major_down_wall"],
        "hasUpAirPocket": kwargs["has_up_air_pocket"],
        "hasDownAirPocket": kwargs["has_down_air_pocket"],
        "regime": kwargs["regime"],
        "vpinPct": kwargs["vpin_pct"],
        "callWallSiege": kwargs["call_wall_siege"],
        "putWallSiege": kwargs["put_wall_siege"],
        "sessionOpen": True,
        "isMicroGuarded": False,
        "atr5m": kwargs["atr_5m"],
    }
    raw_out = subprocess.check_output(
        ["node", "-e", driver],
        input=json.dumps({"script": script_body, "jsParams": js_params}).encode("utf-8"),
    ).decode("utf-8")
    out = json.loads(raw_out)

    # Half-cent parity check against 0.825 -> 0.82 and 4019.825 -> 4019.82
    assert out["r2_edges"] == [0.82, 2.82, 3.82, 4019.82, 4019.84]
    for key in ("squeeze", "fade", "rebound", "breakdown"):
        assert out["matrix"][key]["entry"] == py_mat[key]["entry"], f"Entry mismatch for {key}"
        assert out["matrix"][key]["sl"] == py_mat[key]["sl"], f"SL mismatch for {key}"
        assert out["matrix"][key]["tp"] == py_mat[key]["tp"], f"TP mismatch for {key}"
        assert out["matrix"][key]["active"] == py_mat[key]["active"], f"Active mismatch for {key}"


def test_vpin_toxic_label_matches_threshold_in_python_and_js() -> None:
    """VPIN >= 65% badge text must not falsely claim '>90%' when VPIN is e.g. 67%."""
    from src.quant_engine.dealer import compute_vpin_bvc

    toxic_candles = [
        {"open": 4000.0 + i, "high": 4002.0 + i, "low": 3999.9 + i, "close": 4001.8 + i, "volume": 500}
        for i in range(30)
    ]
    res = compute_vpin_bvc(toxic_candles)
    assert res["vpin_pct"] >= 65.0
    assert ">90%" not in res["vpin_label"]
    assert ">=65%" in res["vpin_label"]

    js_script = _extract_neiro_script()
    assert ">90%" not in js_script
    assert ">=65%" in js_script


def test_compute_tactical_matrix_preserves_aggregated_vex_chex_and_sl_labels() -> None:
    """Aggregated multi-expiry netVEX/netCHEX must not be overwritten, and SL labels must reflect exact distances."""
    from src.quant_engine.loader import compute_tactical_matrix

    df = pd.DataFrame(
        [
            {
                "strike": 4000.0,
                "callBid": 30.0, "callAsk": 31.0, "callMid": 30.5, "callLatest": 30.5,
                "callVolume": 50, "callOpenInterest": 200, "callGamma": 0.004, "callIV": 0.20,
                "putBid": 10.0, "putAsk": 11.0, "putMid": 10.5, "putLatest": 10.5,
                "putVolume": 80, "putOpenInterest": 1800, "putGamma": 0.004, "putIV": 0.22,
                "callGEX": 1.0, "putGEX": -9.0, "netGEX": -8.0,
                "callVEX": 1.0, "putVEX": -10.5, "netVEX": -9.5,
                "callCHEX": 0.5, "putCHEX": -5.0, "netCHEX": -4.5,
            },
            {
                "strike": 4020.0,
                "callBid": 20.0, "callAsk": 21.0, "callMid": 20.5, "callLatest": 20.5,
                "callVolume": 100, "callOpenInterest": 800, "callGamma": 0.005, "callIV": 0.19,
                "putBid": 19.0, "putAsk": 20.0, "putMid": 19.5, "putLatest": 19.5,
                "putVolume": 100, "putOpenInterest": 800, "putGamma": 0.005, "putIV": 0.19,
                "callGEX": 6.4, "putGEX": -6.4, "netGEX": 0.0,
                "callVEX": 12.34, "putVEX": -2.34, "netVEX": 10.0,
                "callCHEX": 6.0, "putCHEX": -1.0, "netCHEX": 5.0,
            },
            {
                "strike": 4050.0,
                "callBid": 8.0, "callAsk": 9.0, "callMid": 8.5, "callLatest": 8.5,
                "callVolume": 120, "callOpenInterest": 2500, "callGamma": 0.003, "callIV": 0.21,
                "putBid": 38.0, "putAsk": 39.0, "putMid": 38.5, "putLatest": 38.5,
                "putVolume": 20, "putOpenInterest": 100, "putGamma": 0.003, "putIV": 0.21,
                "callGEX": 12.0, "putGEX": -0.5, "netGEX": 11.5,
                "callVEX": 15.0, "putVEX": -1.0, "netVEX": 14.0,
                "callCHEX": 8.0, "putCHEX": -0.5, "netCHEX": 7.5,
            },
        ]
    )
    df.attrs["is_aggregated"] = True
    res = compute_tactical_matrix(df, spot=4020.0, dte_days=10.0)
    assert res["total_net_vex"] == pytest.approx(14.5, abs=1e-6)
    assert res["total_net_chex"] == pytest.approx(8.0, abs=1e-6)

    table = res["tactical_table"]
    row_sell = table.loc[table["Chien Luoc"].str.contains("BAN DINH")].iloc[0]
    row_buy = table.loc[table["Chien Luoc"].str.contains("MUA DAY")].iloc[0]
    assert "($5.0)" in row_sell["Hard SL"]
    assert "($4.5)" in row_buy["Hard SL"]


def test_level_state_unsorted_strikes_adr028_sl_and_absorption_state() -> None:
    """Unsorted strikes must not yield negative/zero step; SL must satisfy ADR-028 >= $5; ABSORPTION_DEFENDED must trigger."""
    from src.quant_engine.level_state import LevelState, evaluate_tactical_level_states

    unsorted_df = pd.DataFrame(
        [
            {"strike": 4050.0, "callOpenInterest": 1500, "putOpenInterest": 100, "callVolume": 100, "putVolume": 10, "netGEX": 10.0},
            {"strike": 4000.0, "callOpenInterest": 200, "putOpenInterest": 1200, "callVolume": 20, "putVolume": 80, "netGEX": 8.0},
            {"strike": 4025.0, "callOpenInterest": 700, "putOpenInterest": 700, "callVolume": 50, "putVolume": 50, "netGEX": 4.0},
            {"strike": 4025.0, "callOpenInterest": 700, "putOpenInterest": 700, "callVolume": 50, "putVolume": 50, "netGEX": 4.0},
        ]
    )
    meta = {
        "atm_strike": 4025.0,
        "call_wall": 4050.0,
        "put_wall": 4000.0,
        "total_net_gex": 12.0,
        "atr_5m": 4.0,
    }
    evals = evaluate_tactical_level_states(4003.5, unsorted_df, meta)
    put_eval = next(e for e in evals if e.strike == 4000.0)
    assert put_eval.state == LevelState.ABSORPTION_DEFENDED

    testing_evals = evaluate_tactical_level_states(4001.0, unsorted_df, meta)
    put_testing = next(e for e in testing_evals if e.strike == 4000.0)
    assert put_testing.state == LevelState.TESTING
    # Support entry is lvl + 1.00 = 4001.0 -> ADR-028 SL >= 5.00 below entry
    assert (4001.0 - put_testing.hard_sl) >= 5.0


def test_synthetic_fallback_sep_oct_maps_to_z_and_finds_walls_around_5000() -> None:
    """Synthetic Sep/Oct futures contract code fallback uses 'Z'; dealer wall fallback anchors near median strike."""
    from src.quant_engine import synthetic, dealer
    from src.quant_engine.models import OptionsSnapshot, OptionsStrike

    # Force the ultimate fallback branch by mocking compute_dynamic_dte/get_cme_cutoff_dt check to fail loop once
    orig_cutoff = synthetic.get_cme_cutoff_dt
    try:
        synthetic.get_cme_cutoff_dt = lambda _d: datetime.datetime(1999, 1, 1, tzinfo=datetime.timezone.utc)
        sep_res = synthetic.resolve_front_month_cme_option(now=datetime.date(2026, 8, 15))
        oct_res = synthetic.resolve_front_month_cme_option(now=datetime.date(2026, 9, 15))
        assert sep_res["underlying"].startswith("GCZ")
        assert oct_res["underlying"].startswith("GCZ")
    finally:
        synthetic.get_cme_cutoff_dt = orig_cutoff

    snap_5000 = OptionsSnapshot(
        symbol="GCZ26",
        expiry="2026-11-25",
        timestamp=datetime.datetime(2026, 11, 14, tzinfo=datetime.timezone.utc),
        strikes=[
            OptionsStrike(
                strike=4950.0,
                call_bid=60.0, call_ask=62.0, call_volume=10, call_oi=100,
                put_bid=10.0, put_ask=12.0, put_volume=50, put_oi=3000,
            ),
            OptionsStrike(
                strike=5000.0,
                call_bid=25.0, call_ask=27.0, call_volume=40, call_oi=800,
                put_bid=24.0, put_ask=26.0, put_volume=40, put_oi=800,
            ),
            OptionsStrike(
                strike=5050.0,
                call_bid=10.0, call_ask=12.0, call_volume=60, call_oi=3500,
                put_bid=60.0, put_ask=62.0, put_volume=10, put_oi=100,
            ),
        ]
    )
    cw, pw = dealer.find_gamma_weighted_walls(snap_5000, spot_price=None)
    assert cw[0].strike == 5050.0
    assert pw[0].strike == 4950.0


def test_mt5_files_obey_ascii_rule3_except_chart_markers() -> None:
    """All .mq5/.mqh files under mt5/ must be pure ASCII except functional chart markers ▲/▼."""
    allowed = {"\u25b2", "\u25bc"}
    for p in sorted(pathlib.Path("mt5").rglob("*")):
        if p.suffix in {".mq5", ".mqh"}:
            txt = p.read_text(encoding="utf-8")
            bad = [
                (i, c)
                for i, line in enumerate(txt.splitlines(), 1)
                for c in line
                if ord(c) > 127 and c not in allowed
            ]
            assert not bad, f"Non-ASCII text found in {p}: {bad[:10]}"


def test_collector_main_uses_auto_underlying_and_handles_cli(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> None:
    """Collector main.run_one_shot delegates multi-expiry collection with AUTO underlying and handles errors cleanly."""
    from src.collector import main as cmain

    calls: list[dict[str, object]] = []

    def _fake_multi(*, output_dir: str, underlying_futures: str) -> list[str]:
        calls.append({"output_dir": output_dir, "underlying_futures": underlying_futures})
        return [str(tmp_path / "options_prices_GCZ26.csv")]

    monkeypatch.setattr(cmain, "scrape_multi_expiry_and_save", _fake_multi)
    assert cmain.run_one_shot(output_path=str(tmp_path / "options_prices_GCZ26.csv"), multi_expiry=True) is True
    assert calls == [{"output_dir": str(tmp_path), "underlying_futures": "AUTO"}]

    monkeypatch.setattr(cmain, "scrape_multi_expiry_and_save", lambda **_kw: (_ for _ in ()).throw(RuntimeError("net err")))
    assert cmain.run_one_shot(output_path=str(tmp_path / "options_prices_GCZ26.csv"), multi_expiry=True) is False
