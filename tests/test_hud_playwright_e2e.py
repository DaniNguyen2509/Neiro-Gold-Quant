"""Playwright E2E tests verifying ADR-029 sync guards, chart height, and mobile layout."""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from src.hud.html_dashboard import (  # noqa: E402
    build_volatility_smile_figure,
    generate_html_terminal,
    load_and_preprocess_options,
)

GC_SPOT = 4050.5


def _build_sample_html(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Render an offline dashboard HTML file inside tmp_path."""
    strikes = np.arange(3850.0, 4251.0, 25.0)
    n = len(strikes)
    csv_path = tmp_path / "options_prices_GCZ26.csv"
    df_csv = pd.DataFrame(
        {
            "strike": strikes,
            "callBid": np.where(strikes >= GC_SPOT, np.linspace(60, 1, n), 120.0),
            "callAsk": np.where(strikes >= GC_SPOT, np.linspace(62, 2, n), 122.0),
            "callMid": 0.0,
            "callLatest": 0.0,
            "callVolume": 25,
            "callOpenInterest": np.where(strikes >= GC_SPOT, 500, 100),
            "callGamma": 0.0005,
            "callIV": 0.18,
            "putBid": np.where(strikes <= GC_SPOT, np.linspace(1, 60, n), 120.0),
            "putAsk": np.where(strikes <= GC_SPOT, np.linspace(2, 62, n), 122.0),
            "putMid": 0.0,
            "putLatest": 0.0,
            "putVolume": 25,
            "putOpenInterest": np.where(strikes <= GC_SPOT, 500, 100),
            "putGamma": 0.0005,
            "putIV": 0.18,
        }
    )
    df_csv.to_csv(csv_path, index=False)

    now_sec = int(time.time()) - 300
    candles = [
        {
            "time": now_sec + i * 60,
            "open": GC_SPOT - 0.5,
            "high": GC_SPOT + 0.8,
            "low": GC_SPOT - 0.9,
            "close": GC_SPOT,
            "volume": 120,
        }
        for i in range(6)
    ]
    tape = {
        "available": True,
        "market_open": True,
        "latest_price": GC_SPOT,
        "chart_candles": candles,
        "tf_candles": {"1m": candles},
    }

    monkeypatch.setattr("src.quant_engine.basis.fetch_live_cme_futures_price", lambda: GC_SPOT)
    monkeypatch.setattr(
        "src.quant_engine.basis.fetch_live_spot_gold_price", lambda: GC_SPOT - 20.0
    )
    monkeypatch.setattr("src.quant_engine.basis.is_gold_spot_market_open", lambda: False)
    monkeypatch.setattr("src.hud.html_dashboard.fetch_live_cme_m5_tape", lambda **_kw: tape)

    df, meta = load_and_preprocess_options(str(csv_path), basis=0.0, no_mt5=True)
    fig_smile = build_volatility_smile_figure(df, meta)
    html = generate_html_terminal(df, meta, None, fig_smile=fig_smile)
    html_path = tmp_path / "index.html"
    html_path.write_text(html, encoding="utf-8")
    return html_path


_LW_CHARTS_STUB = """
window.LightweightCharts = {
  LineStyle: { Solid: 0, Dotted: 1, Dashed: 2, LargeDashed: 3 },
  CrosshairMode: { Normal: 0 },
  createChart: function(container, opts) {
    const inner = document.createElement('div');
    inner.className = 'tv-lightweight-charts';
    inner.style.width = (opts.width || 800) + 'px';
    inner.style.height = (opts.height || 540) + 'px';
    container.innerHTML = '';
    container.appendChild(inner);
    return {
      applyOptions: function(o) {
        if (o && o.width) inner.style.width = o.width + 'px';
        if (o && o.height) inner.style.height = o.height + 'px';
      },
      addCandlestickSeries: function() {
        return {
          setData: function() {},
          update: function() {},
          priceToCoordinate: function() { return 100; },
          createPriceLine: function() { return { applyOptions: function() {} }; },
          removePriceLine: function() {}
        };
      },
      timeScale: function() {
        return {
          fitContent: function() {},
          setVisibleLogicalRange: function() {},
          getVisibleLogicalRange: function() { return { from: 0, to: 100 }; },
          timeToCoordinate: function() { return 200; },
          subscribeVisibleTimeRangeChange: function() {},
          subscribeVisibleLogicalRangeChange: function() {}
        };
      },
      subscribeCrosshairMove: function() {}
    };
  }
};
"""


def _fulfill_common(route: sync_api.Route) -> bool:
    """Handle common local file and offline LightweightCharts stub routes."""
    url = route.request.url
    if url.startswith("file://"):
        route.continue_()
        return True
    if "lightweight-charts" in url:
        route.fulfill(
            status=200,
            content_type="application/javascript",
            body=_LW_CHARTS_STUB,
        )
        return True
    return False


def _block_external_routes(page: sync_api.Page) -> None:
    """Abort external CDNs/network during offline unit E2E runs."""

    def _handler(route: sync_api.Route) -> None:
        if not _fulfill_common(route):
            route.abort()

    page.route("**/*", _handler)


def test_adr029_chart_height_toggle_and_mobile_no_overflow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify #btn-chart-height expands/shrinks chart and mobile has zero X overflow."""
    html_path = _build_sample_html(tmp_path, monkeypatch)

    with sync_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as exc:  # pragma: no cover
            pytest.skip(f"Playwright Chromium unavailable: {exc}")

        try:
            # Desktop check: chart height toggle + no horizontal overflow
            ctx = browser.new_context(viewport={"width": 1440, "height": 900})
            page = ctx.new_page()
            _block_external_routes(page)
            page.goto(html_path.as_uri(), wait_until="domcontentloaded")
            page.wait_for_timeout(150)

            before_h = page.locator("#neiro-view-container").bounding_box()["height"]
            assert 535 <= before_h <= 550

            page.click("#btn-chart-height")
            page.wait_for_timeout(250)
            after_h = page.locator("#neiro-view-container").bounding_box()["height"]
            tv_h = page.locator("#neiro-tv-chart").bounding_box()["height"]
            assert after_h >= 690, f"Expected expanded container >= 690px, got {after_h}"
            assert tv_h >= 690, f"Expected expanded chart >= 690px, got {tv_h}"

            page.click("#btn-chart-height")
            page.wait_for_timeout(250)
            collapsed_h = page.locator("#neiro-view-container").bounding_box()["height"]
            assert collapsed_h <= 550

            overflow_desktop = page.evaluate(
                "() => document.documentElement.scrollWidth > window.innerWidth"
            )
            assert not overflow_desktop
            ctx.close()

            # Mobile check: zero horizontal overflow at 390x844
            mob = browser.new_context(viewport={"width": 390, "height": 844})
            mpage = mob.new_page()
            _block_external_routes(mpage)
            mpage.goto(html_path.as_uri(), wait_until="domcontentloaded")
            mpage.wait_for_timeout(150)
            metrics = mpage.evaluate(
                "() => ({sw: document.documentElement.scrollWidth, iw: window.innerWidth})"
            )
            assert metrics["sw"] <= metrics["iw"], (
                f"Mobile overflow: scrollWidth={metrics['sw']} > innerWidth={metrics['iw']}"
            )
            mob.close()
        finally:
            browser.close()


def test_adr029_stale_cloud_sync_does_not_overwrite_live_and_reads_label_vi(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify monotonic cloud timestamp guard, live-bridge priority, and dynamic_vacuum.label_vi."""
    html_path = _build_sample_html(tmp_path, monkeypatch)
    now_sec = int(time.time()) - 120
    yahoo_payload = {
        "available": True,
        "market_open": True,
        "latest_price": 4055.25,
        "vpin_pct": 38.0,
        "vpin_label": "VPIN 38.0%",
        "bvc_buy_pct": 54.0,
        "bvc_cvd_contracts": 42.0,
        "kyle_lambda_label": "NORMAL",
        "atr_5m": 4.0,
        "candles": [
            {
                "time": now_sec + i * 60,
                "open": 4054.0,
                "high": 4056.0,
                "low": 4053.5,
                "close": 4055.25 if i == 2 else 4054.5,
                "volume": 150,
            }
            for i in range(3)
        ],
    }
    version_state = {
        "payload": {
            "timestamp_utc": "2025-01-01T00:00:00+00:00",
            "spot_price": 3555.55,
            "call_wall": 3600.0,
            "dynamic_vacuum": {"vacuum_active": True, "label_vi": "STALE LABEL"},
            "post_sweep_execution": {"post_sweep_regime": "MONITORING", "label_vi": "STALE"},
        }
    }

    with sync_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as exc:  # pragma: no cover
            pytest.skip(f"Playwright Chromium unavailable: {exc}")

        try:
            ctx = browser.new_context(viewport={"width": 1440, "height": 900})
            page = ctx.new_page()

            def _route_handler(route: sync_api.Route) -> None:
                url = route.request.url
                if _fulfill_common(route):
                    return
                if "127.0.0.1:8765/api/yahoo_gc" in url:
                    route.fulfill(
                        status=200,
                        content_type="application/json",
                        body=json.dumps(yahoo_payload),
                    )
                elif "version.json" in url:
                    route.fulfill(
                        status=200,
                        content_type="application/json",
                        body=json.dumps(version_state["payload"]),
                    )
                else:
                    route.abort()

            page.route("**/*", _route_handler)
            page.goto(html_path.as_uri(), wait_until="domcontentloaded")
            page.wait_for_timeout(300)

            # Force a Yahoo bridge sync + manual checkCloudSyncNow against stale 2025 version.json
            page.evaluate("async () => { await pollLiveYahooChart('1m'); await checkCloudSyncNow(true); }")
            page.wait_for_timeout(150)

            ticker_after_stale = page.locator("#top-ticker-price").inner_text()
            meta_cw_after_stale = page.evaluate("() => window.INITIAL_META.call_wall")
            assert "4,055.25" in ticker_after_stale, (
                f"Stale version.json overwrote live price: {ticker_after_stale}"
            )
            assert meta_cw_after_stale != 3600.0

            # Now serve a strictly newer version.json (e.g. from cloud options update)
            version_state["payload"] = {
                "timestamp_utc": "2099-01-01T00:00:00+00:00",
                "spot_price": 3555.55,
                "call_wall": 4175.0,
                "dynamic_vacuum": {
                    "vacuum_active": True,
                    "label_vi": "REAL LABEL VI FROM PYTHON",
                },
                "post_sweep_execution": {
                    "post_sweep_regime": "POST_SWEEP_V_SHAPE",
                    "label_vi": "V-SHAPE REALTIME",
                },
            }
            page.evaluate("async () => { await checkCloudSyncNow(true); }")
            page.wait_for_timeout(150)

            vac_title = page.locator("#hud-post-sweep-val").get_attribute("title")
            ticker_after_newer = page.locator("#top-ticker-price").inner_text()
            meta_cw_after_newer = page.evaluate("() => window.INITIAL_META.call_wall")
            assert vac_title == "REAL LABEL VI FROM PYTHON", f"Got vac title: {vac_title!r}"
            assert meta_cw_after_newer == 4175.0
            assert "4,055.25" in ticker_after_newer, (
                f"Active live bridge price overwritten by cloud snapshot: {ticker_after_newer}"
            )
            ctx.close()
        finally:
            browser.close()
