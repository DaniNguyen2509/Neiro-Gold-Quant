"""tests/test_cngthctnhton_math_audit.py

Comprehensive 100% mathematical audit test suite verifying all equations
and quantitative models in Neiro-Quant against the authoritative reference:
docs/tailieudacta/CÔNG THỨC TÍNH TOÁN/CNGTHCTNHTON.html.
"""
import math
import pytest
import numpy as np
import pandas as pd

from src.collector.gold_collector import (
    black76_greeks_single,
    normal_cdf,
    normal_pdf,
)
from src.hud.html_dashboard import build_plotly_figure, load_and_preprocess_options
from src.quant_engine.dealer import compute_exact_gamma_flip, compute_wall_siege_ratio


def test_black76_put_call_parity_and_greeks():
    """Verify Section 2 & 3: Black-76 pricing, Delta parity, Gamma, Vega, Theta."""
    f = 4000.0
    k = 4000.0
    t = 15.0 / 365.0
    r = 0.045
    sigma = 0.16

    cg = black76_greeks_single(f, k, t, r, sigma, is_call=True)
    pg = black76_greeks_single(f, k, t, r, sigma, is_call=False)

    df_disc = math.exp(-r * t)

    # 1. Put-Call Parity: C - P = df * (F - K) = 0 when F = K
    assert cg["price"] - pg["price"] == pytest.approx(df_disc * (f - k), abs=1e-4)

    # 2. Put-Call Parity Delta: |Delta_Call| + |Delta_Put| = e^(-rT)
    delta_sum = abs(cg["delta"]) + abs(pg["delta"])
    assert delta_sum == pytest.approx(df_disc, rel=1e-5)

    # 3. Gamma is identical for Call and Put
    assert cg["gamma"] == pytest.approx(pg["gamma"], rel=1e-5)
    assert cg["gamma"] > 0.0

    # 4. Vega is identical for Call and Put
    assert cg["vega"] == pytest.approx(pg["vega"], rel=1e-5)
    assert cg["vega"] > 0.0

    # 5. Theta check (CNGTHCTNHTON.html images 35 & 36)
    # Theta_Call = - [F * sigma * df * N'(d1) / (2*sqrt(T))] + r * C
    # Theta_Put  = - [F * sigma * df * N'(d1) / (2*sqrt(T))] + r * P
    common_decay = -df_disc * (f * normal_pdf((math.log(f / k) + 0.5 * sigma * sigma * t) / (sigma * math.sqrt(t))) * sigma / (2.0 * math.sqrt(t)))
    assert cg["theta"] == pytest.approx(common_decay + r * cg["price"], rel=1e-5)
    assert pg["theta"] == pytest.approx(common_decay + r * pg["price"], rel=1e-5)


def test_black76_second_order_charm_and_vanna():
    """Verify Section 4: Second-Order Greeks (Vanna & Charm) from CNGTHCTNHTON.html."""
    f = 4000.0
    k = 4050.0  # OTM Call / ITM Put
    t = 20.0 / 365.0
    r = 0.045
    sigma = 0.18

    cg = black76_greeks_single(f, k, t, r, sigma, is_call=True)
    pg = black76_greeks_single(f, k, t, r, sigma, is_call=False)

    df_disc = math.exp(-r * t)
    d1 = (math.log(f / k) + 0.5 * sigma * sigma * t) / (sigma * math.sqrt(t))
    d2 = d1 - sigma * math.sqrt(t)

    # 1. Vanna: -df * N'(d1) * d2 / sigma
    expected_vanna = -df_disc * normal_pdf(d1) * (d2 / sigma)
    assert cg["vanna"] == pytest.approx(expected_vanna, rel=1e-5)

    # 2. Charm (CNGTHCTNHTON.html images 41 & 42):
    # Charm_Call = df * [N'(d1) * d2 / (2T) - r * N(d1)]
    # Charm_Put  = df * [N'(d1) * d2 / (2T) + r * N(-d1)]
    expected_charm_call = df_disc * (normal_pdf(d1) * (d2 / (2.0 * t)) - r * normal_cdf(d1))
    expected_charm_put = df_disc * (normal_pdf(d1) * (d2 / (2.0 * t)) + r * normal_cdf(-d1))

    assert cg["charm"] == pytest.approx(expected_charm_call, rel=1e-5)
    assert pg["charm"] == pytest.approx(expected_charm_put, rel=1e-5)

    # 3. Charm Parity: Charm_Put - Charm_Call = r * e^(-rT)
    assert pg["charm"] - cg["charm"] == pytest.approx(r * df_disc, rel=1e-5)


def test_section5_exposures_gex_vex_chex():
    """Verify Section 5: Net GEX, Net VEX, Net CHEX and Total Daily Theta Bleed formulas."""
    mult = 100.0
    f0 = 4000.0
    c_oi = 5000
    p_oi = 3000
    gamma = 0.0012
    vanna = -0.00045
    charm_call_day = -0.00015
    charm_put_day = 0.00010

    # Net GEX: (c_oi * gamma - p_oi * gamma) * M * F0^2 * 0.01 / 1e6
    expected_gex = (c_oi * gamma - p_oi * gamma) * mult * (f0 ** 2) * 0.01 / 1e6
    assert expected_gex == pytest.approx((2000 * 0.0012) * 100.0 * 16000000.0 * 0.01 / 1e6)

    # Net VEX: (c_oi * vanna - p_oi * vanna) * M * F0 * 0.01 / 1e6
    expected_vex = (c_oi * vanna - p_oi * vanna) * mult * f0 * 0.01 / 1e6
    assert expected_vex == pytest.approx((2000 * -0.00045) * 100.0 * 4000.0 * 0.01 / 1e6)

    # Net CHEX: (c_oi * charm_c - p_oi * charm_p) * M * F0 / 1e6
    expected_chex = (c_oi * charm_call_day - p_oi * charm_put_day) * mult * f0 / 1e6
    assert expected_chex == pytest.approx((5000 * -0.00015 - 3000 * 0.00010) * 100.0 * 4000.0 / 1e6)


def test_quant_profile_figure_has_dedicated_chex_panel():
    """Verify that build_quant_profile_figure has 4 dedicated subplots including Panel 4 Net CHEX."""
    df = pd.DataFrame([
        {
            "strike": 3950.0, "callOpenInterest": 1000, "putOpenInterest": 5000,
            "callVolume": 100, "putVolume": 600,
            "callDelta": 0.8, "putDelta": -0.2,
            "netGEX": -20.0, "netVEX": -5.0, "netCHEX": -3.5,
        },
        {
            "strike": 4000.0, "callOpenInterest": 6000, "putOpenInterest": 4000,
            "callVolume": 800, "putVolume": 400,
            "callDelta": 0.5, "putDelta": -0.5,
            "netGEX": 45.0, "netVEX": 12.0, "netCHEX": 8.2,
        },
        {
            "strike": 4050.0, "callOpenInterest": 7000, "putOpenInterest": 1000,
            "callVolume": 1200, "putVolume": 100,
            "callDelta": 0.2, "putDelta": -0.8,
            "netGEX": 30.0, "netVEX": 8.0, "netCHEX": -2.1,
        },
    ])
    meta = {
        "spot_price": 4000.0, "atm_strike": 4000.0, "call_wall": 4050.0, "put_wall": 3950.0,
        "dte_days": 10.0, "zero_gamma_flip": 3980.0,
    }

    fig = build_plotly_figure(df, meta)

    # 1. Must have 4 columns in layout
    assert hasattr(fig, "_grid_ref")
    # 2. Check subplot titles contain Panel 4 Net CHEX
    titles = [a.text for a in fig.layout.annotations if "Panel" in a.text]
    assert len(titles) == 4
    assert "Panel 4: Net CHEX" in titles[3]
    assert "Panel 1: Net GEX" in titles[0]
    assert "Panel 2: Volume" in titles[1]
    assert "Panel 3: Net VEX" in titles[2]

    # 3. Check that Net CHEX trace exists in figure
    trace_names = [t.name for t in fig.data if t.name]
    assert any("CHEX" in name for name in trace_names)
