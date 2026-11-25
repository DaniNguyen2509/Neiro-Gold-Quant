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


def _run_node_worker_harness(
    tmp_path: pathlib.Path, js_body: str, *, expose_default_entry: bool = False
) -> dict:
    """Execute ESM harness against worker.js by stubbing `cloudflare:workers` in memory."""
    node_bin = shutil.which("node")
    if not node_bin:
        pytest.skip("Node.js runtime not installed on PATH")

    src = WORKER_JS.read_text(encoding="utf-8")
    patched = src.replace(
        'import { DurableObject } from "cloudflare:workers";',
        "class DurableObject { constructor(ctx, env) { this.ctx = ctx; this.env = env; } }",
    )
    if expose_default_entry:
        patched = patched.replace("export default {", "const workerEntry = {")
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
    assert 'FEED_MODE = "ctrader_only"' in toml_txt
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


def test_worker_normalize_yahoo_strips_trailing_zero_vol_dot_and_aligns_close(tmp_path: pathlib.Path):
    """Root-cause guard: Yahoo appends a trailing regularMarketTime snapshot dot (unaligned seconds,
    0 volume, high==low). normalizeYahooChart must drop that dot and align the last real bar's close."""
    harness = """
const yahoo = normalizeYahooChart({
    chart: {
        result: [{
            meta: { regularMarketPrice: 3850.9 },
            timestamp: [1794923340, 1794923400, 1794923444],
            indicators: {
                quote: [{
                    open:   [3849.5, 3850.1, 3850.9],
                    high:   [3850.3, 3852.0, 3850.9],
                    low:    [3849.5, 3849.6, 3850.9],
                    close:  [3850.1, 3850.1, 3850.9],
                    volume: [89,     45,     0]
                }]
            }
        }]
    }
}, "1m");
console.log(JSON.stringify(yahoo));
"""
    res = _run_node_worker_harness(tmp_path, harness)
    assert res["available"] is True
    assert res["latest_price"] == 3850.9
    assert [c["time"] for c in res["candles"]] == [1794923340, 1794923400]
    assert res["candles"][-1]["close"] == 3850.9
    assert res["candles"][-1]["high"] == 3852.0
    assert res["candles"][-1]["low"] == 3849.6


def test_resolve_cloud_feed_worker_url_from_env(monkeypatch):
    monkeypatch.setenv("NEIRO_CLOUD_FEED_URL", "https://neiro-gold-feed.demo.workers.dev/")
    assert _resolve_cloud_feed_worker_url() == "https://neiro-gold-feed.demo.workers.dev"
    monkeypatch.delenv("NEIRO_CLOUD_FEED_URL", raising=False)
    assert _resolve_cloud_feed_worker_url() == "https://neiro-gold-feed.dani-wind2509.workers.dev"


def test_worker_auto_mode_routes_to_do_with_oauth_secrets_only(tmp_path: pathlib.Path):
    # Verify FEED_MODE="auto" + client secrets (without env tokens) forwards /api/yahoo_gc to FEED_DO
    # so OAuth tokens stored inside Durable Object storage activate automatically after /callback.
    harness = """
let doCalls = 0;
const fakeEnv = {
    FEED_MODE: "auto",
    CTRADER_CLIENT_ID: "test_id",
    CTRADER_CLIENT_SECRET: "test_secret",
    FEED_DO: {
        idFromName: (k) => k,
        get: () => ({ fetch: async () => { doCalls += 1; return new Response(JSON.stringify({ routed: true }), { status: 200 }); } }),
    },
};
const r1 = await workerEntry.fetch(new Request("https://example.workers.dev/api/yahoo_gc?tf=5m"), fakeEnv);
const j1 = await r1.json();
const rAuth = await workerEntry.fetch(new Request("https://example.workers.dev/auth/url"), fakeEnv);
const jAuth = await rAuth.json();
console.log(JSON.stringify({ doCalls, j1, jAuth }));
"""
    out = _run_node_worker_harness(tmp_path, harness, expose_default_entry=True)
    assert out["doCalls"] == 1
    assert out["j1"] == {"routed": True}
    assert out["jAuth"]["ok"] is True
    assert out["jAuth"]["scope"] == "accounts"
    assert "scope=accounts" in out["jAuth"]["authorize_url"]


def test_worker_strict_no_yahoo_mixing_after_oauth_or_ctrader_only(tmp_path) -> None:
    """Guarantees Yahoo is never mixed after OAuth authorization or in ctrader_only mode."""
    import json
    import pathlib
    import shutil
    import subprocess

    node_bin = shutil.which("node")
    if not node_bin:
        import pytest
        pytest.skip("Node.js not installed")

    worker_src = pathlib.Path("cloud/cloudflare-worker/worker.js").read_text(encoding="utf-8")
    patched_src = worker_src.replace(
        'import { DurableObject } from "cloudflare:workers";',
        "class DurableObject { constructor(ctx, env) { this.ctx = ctx; this.env = env; } }",
    )
    mod_path = tmp_path / "worker_test.mjs"
    mod_path.write_text(patched_src, encoding="utf-8")

    runner_js = f"""
import {{ CTraderFeedDO }} from {json.dumps(mod_path.resolve().as_uri())};
import workerDefault from {json.dumps(mod_path.resolve().as_uri())};

let yahooCalled = 0;
globalThis.fetch = async () => {{
    yahooCalled += 1;
    const nowSec = Math.floor(Date.now() / 1000);
    return new Response(JSON.stringify({{
        chart: {{
            result: [{{
                meta: {{ regularMarketPrice: 4123.5 }},
                timestamp: [nowSec - 300, nowSec],
                indicators: {{ quote: [{{
                    open: [4120, 4122], high: [4124, 4125], low: [4119, 4121], close: [4122, 4123.5], volume: [10, 12]
                }}] }}
            }}]
        }}
    }}), {{ status: 200, headers: {{ "Content-Type": "application/json" }} }});
}};

const makeCtx = (storedTokens) => ({{
    storage: {{
        async get(k) {{ return k === "tokens" ? storedTokens : null; }},
        async put() {{}},
        async setAlarm() {{}},
    }},
}});

// Case A: FEED_MODE="auto" with NO OAuth token yet -> uses Yahoo GC=F cleanly
yahooCalled = 0;
const doNoTokAuto = new CTraderFeedDO(makeCtx(null), {{ FEED_MODE: "auto", CTRADER_ENV: "demo", CTRADER_SYMBOL: "XAUUSDF" }});
const rA = await doNoTokAuto.fetch(new Request("https://w.test/api/yahoo_gc?tf=5m"));
const bA = await rA.json();
if (rA.status !== 200 || bA.source !== "yahoo_gcf" || !bA.available || yahooCalled !== 1) {{
    throw new Error("Case A failed: " + JSON.stringify(bA));
}}

// Case B: FEED_MODE="ctrader_only" with NO OAuth token -> 503, NEVER Yahoo
yahooCalled = 0;
const doNoTokStrict = new CTraderFeedDO(makeCtx(null), {{ FEED_MODE: "ctrader_only", CTRADER_ENV: "demo", CTRADER_SYMBOL: "XAUUSDF" }});
const rB = await doNoTokStrict.fetch(new Request("https://w.test/api/yahoo_gc?tf=5m"));
const bB = await rB.json();
if (rB.status !== 503 || bB.available !== false || bB.source !== "ctrader_demo_xauusdf" || yahooCalled !== 0) {{
    throw new Error("Case B failed: " + JSON.stringify(bB));
}}

// Case C: FEED_MODE="auto" WITH OAuth token + WS error -> 503, NEVER falls back to Yahoo
yahooCalled = 0;
const doWithTok = new CTraderFeedDO(
    makeCtx({{ accessToken: "acc", refreshToken: "ref", expiresAtMs: Date.now() + 3600000 }}),
    {{ FEED_MODE: "auto", CTRADER_ENV: "demo", CTRADER_SYMBOL: "XAUUSDF", CTRADER_CLIENT_ID: "id", CTRADER_CLIENT_SECRET: "sec" }}
);
doWithTok.ensureConnected = async () => {{ throw new Error("WS closed 1006"); }};
const rC = await doWithTok.fetch(new Request("https://w.test/api/yahoo_gc?tf=5m"));
const bC = await rC.json();
if (rC.status !== 503 || bC.available !== false || bC.source !== "ctrader_demo_xauusdf" || bC.candles.length !== 0 || !String(bC.error).includes("WS closed 1006") || yahooCalled !== 0) {{
    throw new Error("Case C failed: " + JSON.stringify(bC));
}}

// Case D: default.fetch with FEED_MODE="ctrader_only" & missing secrets -> 503, NEVER Yahoo
yahooCalled = 0;
const rD = await workerDefault.fetch(new Request("https://w.test/api/yahoo_gc?tf=5m"), {{ FEED_MODE: "ctrader_only", CTRADER_ENV: "demo", CTRADER_SYMBOL: "XAUUSDF" }});
const bD = await rD.json();
if (rD.status !== 503 || bD.available !== false || bD.source !== "ctrader_demo_xauusdf" || yahooCalled !== 0) {{
    throw new Error("Case D failed: " + JSON.stringify(bD));
}}

console.log(JSON.stringify({{ ok: true, cases: ["A", "B", "C", "D"] }}));
"""
    runner_path = tmp_path / "runner.mjs"
    runner_path.write_text(runner_js, encoding="utf-8")
    out_path = tmp_path / "out.txt"
    err_path = tmp_path / "err.txt"
    with out_path.open("w", encoding="utf-8") as out_fh, err_path.open("w", encoding="utf-8") as err_fh:
        rc = subprocess.call(
            [node_bin, str(runner_path)],
            stdin=subprocess.DEVNULL,
            stdout=out_fh,
            stderr=err_fh,
        )
    stdout_txt = out_path.read_text(encoding="utf-8")
    stderr_txt = err_path.read_text(encoding="utf-8")
    assert rc == 0, f"Node runner failed: {stderr_txt or stdout_txt}"
    assert json.loads(stdout_txt.strip())["ok"] is True


def test_worker_normalize_yahoo_preserves_up_to_360_1m_bars(tmp_path: pathlib.Path):
    """Ensure 1m Yahoo feed keeps 360 bars (6 hours) to bridge cron intervals cleanly."""
    harness = """
const baseTs = 1794940020;
const timestamps = [];
const opens = [], highs = [], lows = [], closes = [], volumes = [];
for (let i = 0; i < 400; i++) {
    timestamps.push(baseTs + i * 60);
    opens.push(3850.0);
    highs.push(3851.0);
    lows.push(3849.0);
    closes.push(3850.5);
    volumes.push(25);
}
const yahoo = normalizeYahooChart({
    chart: {
        result: [{
            meta: { regularMarketPrice: 3850.5 },
            timestamp: timestamps,
            indicators: { quote: [{ open: opens, high: highs, low: lows, close: closes, volume: volumes }] }
        }]
    }
}, "1m");
console.log(JSON.stringify({ count: yahoo.candles.length, first: yahoo.candles[0].time, last: yahoo.candles[yahoo.candles.length - 1].time }));
"""
    res = _run_node_worker_harness(tmp_path, harness)
    assert res["count"] == 360
    assert res["last"] - res["first"] == 359 * 60


def test_worker_trigger_sync_missing_token_returns_401(tmp_path: pathlib.Path):
    """Verifies /api/trigger_sync returns 401 with clear hint when GITHUB_DISPATCH_TOKEN is missing."""
    harness = """
const r = await workerEntry.fetch(new Request("https://w.test/api/trigger_sync"), {});
const b = await r.json();
console.log(JSON.stringify({ status: r.status, ok: b.ok, error: b.error }));
"""
    res = _run_node_worker_harness(tmp_path, harness, expose_default_entry=True)
    assert res["status"] == 401
    assert res["ok"] is False
    assert "Missing GITHUB_DISPATCH_TOKEN" in res["error"]


def test_worker_cors_allows_post_and_authorization_preflight(tmp_path: pathlib.Path):
    """Ensure CORS headers allow POST and Authorization for browser-supplied PAT on /api/trigger_sync."""
    harness = """
const r = await workerEntry.fetch(
    new Request("https://w.test/api/trigger_sync", {
        method: "OPTIONS",
        headers: {
            "Origin": "https://daninguyen2509.github.io",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type"
        }
    }),
    {}
);
console.log(JSON.stringify({
    status: r.status,
    methods: r.headers.get("Access-Control-Allow-Methods"),
    headers: r.headers.get("Access-Control-Allow-Headers")
}));
"""
    res = _run_node_worker_harness(tmp_path, harness, expose_default_entry=True)
    assert res["status"] == 204
    assert "POST" in res["methods"]
    assert "Authorization" in res["headers"]



