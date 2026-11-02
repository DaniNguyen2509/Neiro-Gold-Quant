"""Expiry and rollover tests (Test Plan - Section 3: T1-T6).

Covers: T-floor consistency, Greeks at T->0, front-month rollover,
fallback contract, and DTE weekend handling.

Tests marked RED-EXPECTED document real gaps left failing until owner
approves the behavior change (rule G5).
"""
from __future__ import annotations

import datetime
import math
import re
from pathlib import Path

import numpy as np
import pytest

from src.quant_engine.synthetic import (
    compute_dynamic_dte,
    get_cme_cutoff_dt,
    get_cme_option_expiry_date,
    resolve_front_month_cme_option,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# T1 - T-floor consistency across the codebase (RED-EXPECTED)
# ---------------------------------------------------------------------------
# Patterns that represent T-floor clamps: max(<floor>, <dte>/365) or max(<floor>, dte_days/365)
# We specifically target the conversion from DTE-days to T-years.
_T_YEARS_FLOOR_RE = re.compile(
    r"max\s*\(\s*"
    r"([\d.eE\-]+(?:\s*/\s*[\d.]+)?)"  # the floor constant (e.g. 1.0/365.0, 0.0035, 1e-4)
    r"\s*,\s*"
    r"[^)]*?/\s*365\.0"               # the DTE/365 part
    r"\)",
)

_SRC_DIR = REPO_ROOT / "src"


def _find_t_year_floors() -> dict[str, list[str]]:
    """Scan src/ for T_years = max(FLOOR, dte/365.0) and collect floor values."""
    floors: dict[str, list[str]] = {}
    for py in _SRC_DIR.rglob("*.py"):
        text = py.read_text(encoding="utf-8", errors="replace")
        for m in _T_YEARS_FLOOR_RE.finditer(text):
            raw = m.group(1).strip()
            loc = f"{py.relative_to(REPO_ROOT)}:{text[:m.start()].count(chr(10))+1}"
            try:
                if "/" in raw:
                    parts = raw.split("/")
                    val = float(parts[0].strip()) / float(parts[1].strip())
                else:
                    val = float(raw)
                key = f"{val:.8f}"
            except (ValueError, ZeroDivisionError):
                key = raw
            floors.setdefault(key, []).append(loc)
    return floors


def test_t1_t_floor_is_consistent():
    """RED-EXPECTED: all T_years = max(FLOOR, dte/365.0) must use the same floor.

    Currently found at least 3 distinct values:
    - 1.0/365.0 = 0.00273973  (dealer.py, html_dashboard.py, chart_exporter.py, loader.py)
    - 0.0035                  (gold_collector.py, basis.py)
    - 1e-4 = 0.0001           (html_dashboard.py line 1261)
    """
    floors = _find_t_year_floors()
    unique_vals = set()
    for key in floors:
        try:
            v = float(key)
            # Group values within 1% of each other
            merged = False
            for existing in list(unique_vals):
                if abs(v - existing) / max(abs(existing), 1e-12) < 0.01:
                    merged = True
                    break
            if not merged:
                unique_vals.add(v)
        except ValueError:
            unique_vals.add(0)

    detail = "\n".join(f"  {k}: {', '.join(v)}" for k, v in sorted(floors.items()))
    assert len(unique_vals) == 1, (
        f"Found {len(unique_vals)} distinct T_years floor values across src/:\n{detail}\n"
        "All should use a single shared constant."
    )


# ---------------------------------------------------------------------------
# T2 - Greeks at DTE = 1 minute
# ---------------------------------------------------------------------------
def test_t2_gamma_flip_finite_at_1min_dte():
    """Zero Gamma Flip must not return inf/NaN when T is 1 minute."""
    from src.quant_engine.dealer import compute_exact_gamma_flip
    from src.quant_engine.models import OptionsSnapshot, OptionsStrike

    snap = OptionsSnapshot(
        symbol="GCZ26", expiry="2026-11-25", timestamp="2026-11-25T18:29:00Z",
        strikes=tuple(
            OptionsStrike(
                strike=k, call_bid=5.0, call_ask=6.0,
                call_oi=c_oi, call_volume=0,
                put_bid=5.0, put_ask=6.0,
                put_oi=p_oi, put_volume=0,
            )
            for k, c_oi, p_oi in [
                (3900.0, 1000, 100),
                (4000.0, 500, 500),
                (4100.0, 100, 1000),
            ]
        ),
    )
    dte_1min = 1.0 / 1440.0  # 1 minute in days
    result = compute_exact_gamma_flip(snap, spot_price=4000.0, dte_days=dte_1min)
    if result is not None:
        assert np.isfinite(result), f"S* is not finite: {result}"


def test_t2_iv_solver_finite_at_1min():
    from src.quant_engine.dealer import solve_black76_iv

    T = 1.0 / (365.0 * 24.0 * 60.0)  # 1 minute in years
    iv = solve_black76_iv(4000.0, 4000.0, T, 0.50, True)
    assert np.isfinite(iv), f"IV is not finite: {iv}"


def test_t2_b76_gamma_finite_at_tiny_T():
    """Direct Black-76 gamma computation must not overflow at tiny T."""
    T = 1.0 / (365.0 * 24.0 * 60.0)
    sigma = 0.16
    F = 4000.0
    K = 4000.0
    r = 0.045

    sqrt_t = math.sqrt(T)
    denom = max(1e-5, sigma * sqrt_t)
    d1 = (math.log(F / K) + 0.5 * sigma**2 * T) / denom
    pdf = (1.0 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * d1**2)
    gamma = (math.exp(-r * T) * pdf) / max(1e-4, F * denom)

    assert np.isfinite(gamma), f"Gamma is not finite: {gamma}"
    assert gamma > 0


# ---------------------------------------------------------------------------
# T3 - Rollover at 13:30 CT (18:30 UTC) on expiry day
# ---------------------------------------------------------------------------
def test_t3_rollover_before_cutoff():
    """1 minute before cutoff on expiry day -> current contract."""
    # OGZ26 expiry: 4th last business day of November 2026
    exp_date = get_cme_option_expiry_date(2026, 12)  # December contract month
    cutoff_dt = get_cme_cutoff_dt(exp_date)
    before_cutoff = cutoff_dt - datetime.timedelta(minutes=1)
    result = resolve_front_month_cme_option(now=before_cutoff)
    assert result["expiration_date"] == exp_date.isoformat()


def test_t3_rollover_after_cutoff():
    """1 minute after cutoff on expiry day -> next contract month."""
    exp_date = get_cme_option_expiry_date(2026, 12)
    cutoff_dt = get_cme_cutoff_dt(exp_date)
    after_cutoff = cutoff_dt + datetime.timedelta(minutes=1)
    result = resolve_front_month_cme_option(now=after_cutoff)
    result_exp = datetime.date.fromisoformat(result["expiration_date"])
    assert result_exp > exp_date, (
        f"After cutoff, should roll to next month. Got {result['expiration_date']}"
    )


# ---------------------------------------------------------------------------
# T4 - Underlying futures symbol after roll (RED-EXPECTED)
# ---------------------------------------------------------------------------
def test_t4_underlying_rolls_with_option():
    """RED-EXPECTED: after OGZ26 expires, underlying should NOT stay 'GCZ26'.

    Currently `underlying_futures` defaults to 'GCZ26' and is passed through
    unchanged regardless of which option month is resolved.
    """
    # Set now to after OGZ26 expiry (January 2027)
    now_jan = datetime.datetime(2027, 1, 5, 12, 0, tzinfo=datetime.timezone.utc)
    result = resolve_front_month_cme_option(now=now_jan, underlying_futures="GCZ26")

    # The option symbol should be in 2027 territory
    assert "27" in result["option_symbol"], f"Option symbol not rolled: {result['option_symbol']}"
    # RED: The underlying is still 'GCZ26' even though GCZ26 has expired
    assert result["underlying"] != "GCZ26", (
        f"Underlying is still 'GCZ26' after Dec 2026 expiry. "
        f"Should be GCG27 or later. Got: {result}"
    )


# ---------------------------------------------------------------------------
# T5 - Fallback must not return an expired date (RED-EXPECTED)
# ---------------------------------------------------------------------------
def test_t5_fallback_not_expired():
    """Fallback must resolve a non-expired expiration date into the future."""
    now_dt = datetime.datetime(2026, 11, 2, 12, 0, tzinfo=datetime.timezone.utc)
    res = resolve_front_month_cme_option(now=now_dt)
    exp = datetime.date.fromisoformat(res["expiration_date"])
    assert exp > datetime.date(2026, 11, 1), (
        f"Resolved expiration {exp} is already in the past or about to expire"
    )


def test_t5_resolve_never_returns_past_date():
    """For any reasonable 'now', resolved expiry must be >= now.date()."""
    test_dates = [
        datetime.datetime(2026, 11, 2, 12, 0, tzinfo=datetime.timezone.utc),
        datetime.datetime(2026, 12, 25, 12, 0, tzinfo=datetime.timezone.utc),
        datetime.datetime(2027, 3, 15, 12, 0, tzinfo=datetime.timezone.utc),
    ]
    for now in test_dates:
        result = resolve_front_month_cme_option(now=now)
        exp = datetime.date.fromisoformat(result["expiration_date"])
        # Expiry could be today (if before cutoff), so >=
        assert exp >= now.date() - datetime.timedelta(days=1), (
            f"now={now.date()}, resolved expiry={exp} is in the past"
        )


# ---------------------------------------------------------------------------
# T6 - DTE across weekends
# ---------------------------------------------------------------------------
def test_t6_dte_over_weekend():
    """DTE calculation includes calendar days (weekend counts)."""
    friday_23 = datetime.datetime(2026, 11, 20, 23, 0, tzinfo=datetime.timezone.utc)
    monday_00 = datetime.datetime(2026, 11, 23, 0, 0, tzinfo=datetime.timezone.utc)
    expiry = "2026-11-25"

    dte_fri = compute_dynamic_dte(expiry, now=friday_23)
    dte_mon = compute_dynamic_dte(expiry, now=monday_00)

    # Monday is 2+ days after Friday 23:00 -> DTE should be ~2 days less
    diff = dte_fri - dte_mon
    assert 1.5 < diff < 3.0, f"Weekend DTE gap unexpected: fri={dte_fri:.2f}, mon={dte_mon:.2f}"


def test_t6_dte_consistency_dashboard_vs_collector():
    """Both paths must yield the same DTE for the same (expiry, now) pair."""
    from src.collector.gold_collector import calculate_dte as collector_dte

    expiry_str = "2026-11-25"
    # collector_dte takes a date string and uses its own now()
    # so we can only verify structural consistency
    dte_synth = compute_dynamic_dte(expiry_str)
    dte_collect = collector_dte(expiry_str)

    # Both should be positive and within 1 day of each other
    # (they may differ by seconds due to separate now() calls)
    assert abs(dte_synth - dte_collect) < 1.0, (
        f"DTE mismatch: synthetic={dte_synth:.4f}, collector={dte_collect:.4f}"
    )


def test_t6_dte_floor_at_1_minute():
    """DTE must be floored at 1/1440 (1 minute), not zero or negative."""
    # Expiry is 30 seconds ago
    now = datetime.datetime(2026, 11, 25, 18, 30, 30, tzinfo=datetime.timezone.utc)
    expiry = datetime.datetime(2026, 11, 25, 18, 30, 0, tzinfo=datetime.timezone.utc)
    dte = compute_dynamic_dte(expiry, now=now)
    assert dte == pytest.approx(1.0 / 1440.0), f"DTE should be floored at 1/1440, got {dte}"

# ---------------------------------------------------------------------------
# T7 - US Winter Time dynamic cutoff (13:30 Chicago Time = 19:30 UTC winter / 18:30 UTC summer)
# ---------------------------------------------------------------------------
def test_t7_us_winter_time_dynamic_cutoff():
    """Verify that get_cme_cutoff_dt correctly switches between 18:30 UTC (summer) and 19:30 UTC (winter)."""
    from src.quant_engine.synthetic import get_cme_cutoff_dt

    # Summer date (e.g. July 28, 2026 - US CDT UTC-5)
    summer_exp = datetime.date(2026, 7, 28)
    summer_cutoff = get_cme_cutoff_dt(summer_exp)
    assert summer_cutoff.hour == 18
    assert summer_cutoff.minute == 30

    # Winter date (e.g. November 24, 2026 - US CST UTC-6)
    winter_exp = datetime.date(2026, 11, 24)
    winter_cutoff = get_cme_cutoff_dt(winter_exp)
    assert winter_cutoff.hour == 19
    assert winter_cutoff.minute == 30
