"""Data-gate tests (Test Plan - Section 1: D1-D9).

Covers the ingestion boundary: Barchart scrape -> CSV -> CI verify -> dashboard
stale detection. All network access is mocked (rule G1) and every file lives in
pytest's ``tmp_path`` (rule G3).

Tests marked "RED-EXPECTED" document real gaps that are intentionally left
failing until the owner approves the corresponding behavior change (rule G5).
"""
from __future__ import annotations

import datetime
import os
import time
import unittest.mock as mock
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.collector import scraper as scraper_mod

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "daily_options_sync.yml"
REFERENCE_GC = 4000.0  # Reference CME Gold Futures (GC) price used across fixtures


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
class _NoDrivePath(type(Path())):
    """Path subclass that hides the owner's Google Drive mirror (H:/) from tests."""

    def exists(self, *args, **kwargs):  # noqa: D401
        if str(self).replace("\\", "/").upper().startswith("H:/"):
            return False
        return super().exists(*args, **kwargs)


@pytest.fixture(autouse=True)
def _isolate_drive_mirror(monkeypatch):
    """Never touch the real Google Drive mirror during tests."""
    monkeypatch.setattr(scraper_mod, "Path", _NoDrivePath)


def _barchart_json(strikes: list[float], oi: int = 100) -> dict:
    """Build a minimal Barchart core-api style payload (Call + Put per strike)."""
    data = []
    for k in strikes:
        for opt_type in ("Call", "Put"):
            data.append(
                {
                    "raw": {
                        "strikePrice": f"{k:,.2f}",
                        "optionType": opt_type,
                        "bidPrice": "10.00",
                        "askPrice": "11.00",
                        "lastPrice": "10.50",
                        "volume": "5",
                        "openInterest": str(oi),
                        "gamma": "0.0005",
                        "volatility": "18.0%",
                    }
                }
            )
    return {"count": len(data), "total": len(data), "data": data}


def _good_frame(lo: float = 3500.0, hi: float = 4500.0, step: float = 25.0) -> pd.DataFrame:
    strikes = np.arange(lo, hi + step, step)
    return pd.DataFrame(
        {
            "strike": strikes,
            "callOpenInterest": 100.0,
            "putOpenInterest": 100.0,
            "callVolume": 5.0,
            "putVolume": 5.0,
        }
    )


def _write_good_master(path: Path) -> str:
    _good_frame().to_csv(path, index=False)
    return path.read_text()


def _async_return(payload):
    async def _fake(*_args, **_kwargs):
        return payload

    return _fake


def _async_raise(exc: Exception):
    async def _fake(*_args, **_kwargs):
        raise exc

    return _fake


def _validate(df: pd.DataFrame, reference_price: float | None = REFERENCE_GC):
    """Proposed contract: src.collector.validator.validate_options_frame."""
    try:
        from src.collector.validator import validate_options_frame
    except ImportError:
        pytest.fail(
            "RED-EXPECTED: src/collector/validator.py::validate_options_frame "
            "does not exist yet (contract for D2-D5)."
        )
    return validate_options_frame(df, reference_price=reference_price)


# ---------------------------------------------------------------------------
# D1 - Strike-band guard in the real scrape path (multi-expiry, as run by CI)
# ---------------------------------------------------------------------------
def test_d1_multi_expiry_rejects_chain_not_covering_gc(tmp_path, monkeypatch):
    """RED-EXPECTED: chain [1500, 3200] with GC ~4000 must NOT overwrite master.

    Current guards (per-expiry 3000-5000 and master 2600-2800) both accept it.
    """
    master = tmp_path / "options_prices_GCZ26.csv"
    before = _write_good_master(master)

    expirations = [
        {
            "option_symbol": "OGZ26",
            "barchart_url": "https://example.invalid/options",
            "name": "Monthly",
            "expiration_date": "2026-11-24",
            "dte": 22.0,
        }
    ]
    bad_strikes = list(np.arange(1500.0, 3225.0, 25.0))
    monkeypatch.setattr(
        "src.quant_engine.synthetic.resolve_active_expirations",
        lambda **_kw: expirations,
    )
    monkeypatch.setattr(
        scraper_mod, "fetch_barchart_options_playwright", _async_return(_barchart_json(bad_strikes))
    )

    scraper_mod.scrape_multi_expiry_and_save(output_dir=str(tmp_path), underlying_futures="GCZ26")

    assert master.read_text() == before, "Master CSV was overwritten by a chain that does not cover GC"


# ---------------------------------------------------------------------------
# D2-D5 - Validator contract (new module, approved in test plan)
# ---------------------------------------------------------------------------
def test_d2_validator_accepts_chain_covering_gc():
    res = _validate(_good_frame(3500.0, 4500.0))
    assert res.ok, res.errors


def test_d2_validator_rejects_chain_not_covering_gc():
    res = _validate(_good_frame(1500.0, 3200.0))
    assert not res.ok
    assert res.errors


def test_d3_validator_rejects_empty_frame():
    empty = _good_frame().iloc[0:0]
    res = _validate(empty)
    assert not res.ok
    assert res.errors


def test_d4_validator_reports_missing_column_by_name():
    df = _good_frame().drop(columns=["callOpenInterest"])
    res = _validate(df)
    assert not res.ok
    assert any("callOpenInterest" in e for e in res.errors)


def test_d5_validator_rejects_zero_total_oi():
    df = _good_frame()
    df["callOpenInterest"] = 0.0
    df["putOpenInterest"] = 0.0
    res = _validate(df)
    assert not res.ok


def test_d5_validator_rejects_negative_oi():
    df = _good_frame()
    df.loc[3, "putOpenInterest"] = -50.0
    res = _validate(df)
    assert not res.ok


# ---------------------------------------------------------------------------
# D6 - Garbage values never leak NaN/inf into the engine
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "raw, expected",
    [
        ("N/A", 0.0),
        ("-", 0.0),
        ("--", 0.0),
        ("1,234", 1234.0),
        ("$4,181.10", 4181.10),
        (float("nan"), 0.0),
        (float("inf"), 0.0),
        (None, 0.0),
        ("", 0.0),
    ],
)
def test_d6_clean_val_sanitizes_garbage(raw, expected):
    from src.hud.html_dashboard import clean_val

    out = clean_val(raw)
    assert np.isfinite(out)
    assert out == pytest.approx(expected)


# ---------------------------------------------------------------------------
# D7 - Stale detection must not depend on file mtime
# ---------------------------------------------------------------------------
def _load_meta(csv_path: Path) -> dict:
    from src.hud.html_dashboard import load_and_preprocess_options

    with mock.patch("src.quant_engine.basis.fetch_live_cme_futures_price", return_value=REFERENCE_GC), \
         mock.patch("src.hud.html_dashboard.fetch_live_cme_m5_tape", return_value=[]):
        _df, meta = load_and_preprocess_options(str(csv_path), basis=0.0, no_mt5=True)
    return meta


def test_d7_stale_detected_from_old_mtime(tmp_path):
    """Characterization: current mtime-based check flags an 8h-old file."""
    csv = tmp_path / "options_prices_GCZ26.csv"
    _good_frame().to_csv(csv, index=False)
    old = time.time() - 8 * 3600
    os.utime(csv, (old, old))

    assert _load_meta(csv)["is_data_stale"] is True


def test_d7_stale_detected_from_embedded_timestamp_even_if_mtime_fresh(tmp_path):
    """RED-EXPECTED: after `git checkout` on CI the mtime is always "now".

    Staleness must be derived from an embedded `scraped_at_utc` timestamp.
    """
    csv = tmp_path / "options_prices_GCZ26.csv"
    df = _good_frame()
    scraped_at = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=8)
    df["scraped_at_utc"] = scraped_at.isoformat()
    df.to_csv(csv, index=False)  # mtime == now

    assert _load_meta(csv)["is_data_stale"] is True


# ---------------------------------------------------------------------------
# D8 - CI verify step must fail loudly, not silently revert
# ---------------------------------------------------------------------------
def _verify_step_text() -> str:
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    start = text.index("Verify Generated Options File")
    end = text.index("- name:", start)
    return text[start:end]


def test_d8_ci_verify_step_surfaces_failure():
    """RED-EXPECTED: on failure the step must emit a GitHub annotation or exit non-zero."""
    step = _verify_step_text()
    loud_markers = ("::error", "::warning", "sys.exit(1)", "exit 1")
    assert any(m in step for m in loud_markers), (
        "Verify step only prints and reverts silently; the job stays green on bad data."
    )


# ---------------------------------------------------------------------------
# D9 - Broken scrape must never overwrite a good dataset
# ---------------------------------------------------------------------------
def test_d9_fetch_failure_preserves_existing_csv(tmp_path, monkeypatch):
    master = tmp_path / "options_prices_GCZ26.csv"
    before = _write_good_master(master)
    monkeypatch.setattr(
        scraper_mod,
        "fetch_barchart_options_playwright",
        _async_raise(RuntimeError("Cloudflare captcha page")),
    )

    scraper_mod.scrape_and_save(output_path=str(master), page_url="https://example.invalid")

    assert master.read_text() == before


def test_d9_empty_payload_preserves_existing_csv(tmp_path, monkeypatch):
    master = tmp_path / "options_prices_GCZ26.csv"
    before = _write_good_master(master)
    monkeypatch.setattr(
        scraper_mod, "fetch_barchart_options_playwright", _async_return({"count": 0, "data": []})
    )

    try:
        scraper_mod.scrape_and_save(output_path=str(master), page_url="https://example.invalid")
    except Exception:
        pass  # Raising is acceptable; overwriting good data is not.

    assert master.read_text() == before

# ---------------------------------------------------------------------------
# D10 - Scraper automated Black-76 IV enrichment
# ---------------------------------------------------------------------------
def test_d10_scraper_enriches_zero_iv_with_black76():
    """When Barchart provides 0.0 for callIV/putIV, scraper must enrich them with calibrated Black-76 IV."""
    raw_df = pd.DataFrame({
        "strike": [3900.0, 4000.0, 4100.0],
        "callMid": [125.0, 50.0, 15.0],
        "putMid": [15.0, 48.0, 118.0],
        "callBid": [124.0, 49.0, 14.0],
        "callAsk": [126.0, 51.0, 16.0],
        "putBid": [14.0, 47.0, 117.0],
        "putAsk": [16.0, 49.0, 119.0],
        "callIV": [0.0, 0.0, 0.0],
        "putIV": [0.0, 0.0, 0.0],
        "callOI": [1000, 2000, 1500],
        "putOI": [1200, 1800, 1400],
        "callVolume": [100, 200, 150],
        "putVolume": [120, 180, 140],
    })

    enriched = scraper_mod._enrich_options_iv_and_greeks(raw_df, dte_days=23.0)

    assert (enriched["callIV"] > 0.05).all(), f"callIV was not enriched: {enriched['callIV']}"
    assert (enriched["putIV"] > 0.05).all(), f"putIV was not enriched: {enriched['putIV']}"
    assert (enriched["callIV"] < 0.50).all(), f"callIV is unrealistically high: {enriched['callIV']}"
    assert (enriched["putIV"] < 0.50).all(), f"putIV is unrealistically high: {enriched['putIV']}"
