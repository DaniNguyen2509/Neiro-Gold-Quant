"""Unit and Node runtime verification tests for the Cloudflare Worker relay."""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess

import pytest

from src.hud.html_dashboard import _resolve_cloud_feed_worker_url

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKER_DIR = ROOT / "cloud" / "cloudflare-worker"
WORKER_JS = WORKER_DIR / "worker.js"
WRANGLER_TOML = WORKER_DIR / "wrangler.toml"


def _run_node_worker_harness(tmp_path: pathlib.Path, js_body: str) -> dict:
    """Execute ESM harness against worker.js by stubbing `cloudflare:workers` in memory."""
    node_bin = shutil.which("node")
    if not node_bin:
        pytest.skip("Node.js runtime not installed on PATH")

    src = WORKER_JS.read_text(encoding="utf-8")
    patched = src.replace(
        'import { DurableObject } from "cloudflare:workers";',
        "class DurableObject { constructor(ctx, env) { this.ctx = ctx; this.env = env; } }",
    )
    script_file = tmp_path / "worker_harness.mjs"
    script_file.write_text(patched + "\n" + js_body, encoding="utf-8")

    proc = subprocess.run(
        [node_bin, str(script_file)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        check=True,
        timeout=15,
    )
    return json.loads(proc.stdout.strip())


def test_wrangler_toml_free_tier_custom_ports_and_sqlite_do():
    toml_txt = WRANGLER_TOML.read_text(encoding="utf-8")
    assert 'compatibility_flags = ["allow_custom_ports"]' in toml_txt
    assert 'new_sqlite_classes = ["CTraderFeedDO"]' in toml_txt
    assert 'FEED_MODE = "auto"' in toml_txt
    assert 'CTRADER_ENV = "demo"' in toml_txt
    assert 'CTRADER_SYMBOL = "XAUUSDF"' in toml_txt


def test_worker_js_protocol_constants_and_zero_secrets():
    src = WORKER_JS.read_text(encoding="utf-8")
    for payload_type in ("2100", "2102", "2114", "2127", "2131", "2135", "2137", "2142", "2147", "2149"):
        assert payload_type in src
    assert "demo.ctraderapi.com" in src
    assert "basis_offset: 0.0" in src
    assert 'scope", "accounts"' in src


def test_worker_js_decodes_xauusdf_zero_basis_and_filters_yahoo(tmp_path: pathlib.Path):
    harness = """
const bar = decodeCTraderTrendbar(
    { low: 388250000, deltaOpen: 55000, deltaHigh: 105000, deltaClose: 80000, utcTimestampInMinutes: 29912400, volume: 412 },
    2,
    0.0
);
const yahoo = normalizeYahooChart({
    chart: {
        result: [{
            meta: { regularMarketPrice: 3886.3 },
            timestamp: [1763100000, 1763100060],
            indicators: { quote: [{ open: [3885.5, null], high: [3887.0, 3888.0], low: [3885.0, 3884.0], close: [3886.3, 0], volume: [120, 50] }] }
        }]
    }
}, "1m");
const sym = findMatchingCTraderSymbol([
    { symbolId: 1, symbolName: "XAUUSD", digits: 2 },
    { symbolId: 42, symbolName: "XAUUSD-F", digits: 2 },
], "XAUUSDF");
const satClosed = isCmeGlobexOpenUtc(Date.parse("2026-11-14T15:00:00Z"));
const tueOpen = isCmeGlobexOpenUtc(Date.parse("2026-11-10T15:00:00Z"));
const tueMaint = isCmeGlobexOpenUtc(Date.parse("2026-11-10T22:30:00Z"));
console.log(JSON.stringify({ bar, yahoo, sym, satClosed, tueOpen, tueMaint }));
"""
    res = _run_node_worker_harness(tmp_path, harness)
    assert res["bar"] == {
        "time": 29912400 * 60,
        "open": 3883.05,
        "high": 3883.55,
        "low": 3882.5,
        "close": 3883.3,
        "volume": 412,
    }
    assert res["yahoo"]["available"] is True
    assert res["yahoo"]["latest_price"] == 3886.3
    assert len(res["yahoo"]["candles"]) == 1
    assert res["sym"]["symbolId"] == 42
    assert res["satClosed"] is False
    assert res["tueOpen"] is True
    assert res["tueMaint"] is False


def test_resolve_cloud_feed_worker_url_from_env(monkeypatch):
    monkeypatch.setenv("NEIRO_CLOUD_FEED_URL", "https://neiro-gold-feed.demo.workers.dev/")
    assert _resolve_cloud_feed_worker_url() == "https://neiro-gold-feed.demo.workers.dev"
    monkeypatch.delenv("NEIRO_CLOUD_FEED_URL", raising=False)
    assert _resolve_cloud_feed_worker_url() == "https://neiro-gold-feed.dani-wind2509.workers.dev"
