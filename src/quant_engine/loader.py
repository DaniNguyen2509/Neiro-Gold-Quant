"""
================================================================================
NEIRO-QUANT: AUTOMATED DATA INGESTION & CLEANING PIPELINE
================================================================================
Module: src/quant_engine/loader.py
Description:
  High-performance data ingestion, anomaly cleaning, strike alignment,
  and tactical quant matrix computation for CME Gold Futures Options (GCZ26).

Supported Data Sources:
  1. Bookmarklet 1-Click CSV (Barchart Internal API export)
  2. Bookmarklet TSV / Clipboard TSV
  3. Barchart multi-column / stacked table exports (Type column / Strike C/P)
  4. Legacy dual-file / line dumps (options_prices.csv + volatility-greeks.csv)
  5. Fallback institutional benchmark dataset for GCZ26
================================================================================
"""

from __future__ import annotations

import io
import os
import re
import glob
import math
from typing import Optional, Union, Dict, Any, Tuple
import numpy as np
import pandas as pd

from .dealer import (
    compute_exact_gamma_flip,
    compute_wall_siege_ratio,
    find_gamma_weighted_walls,
    classify_wall_regime,
    find_walls,
)
from .models import OptionsSnapshot, OptionsStrike, QuantLevels, Wall
from .strategy import MarketSnapshot, OptionQuote, compute_implied_spot
from .synthetic import compute_dynamic_dte


# ==============================================================================
# 1. INSTITUTIONAL FALLBACK BENCHMARK DATASET (GCZ26)
# ==============================================================================
BENCHMARK_GCZ26_DATA = [
    {'strike': 4135.0, 'callBid': 133.2, 'callAsk': 133.6, 'callMid': 133.4, 'callLatest': 133.4, 'callVolume': 0.0, 'callOpenInterest': 75.0, 'callGamma': 0.00336, 'callIV': 0.21764, 'putBid': 87.2, 'putAsk': 87.6, 'putMid': 87.4, 'putLatest': 87.4, 'putVolume': 1.0, 'putOpenInterest': 37.0, 'putGamma': 0.00336, 'putIV': 0.21764},
    {'strike': 4140.0, 'callBid': 130.4, 'callAsk': 130.8, 'callMid': 130.6, 'callLatest': 130.6, 'callVolume': 3.0, 'callOpenInterest': 56.0, 'callGamma': 0.00344, 'callIV': 0.21716, 'putBid': 89.4, 'putAsk': 89.8, 'putMid': 89.6, 'putLatest': 89.6, 'putVolume': 0.0, 'putOpenInterest': 118.0, 'putGamma': 0.00344, 'putIV': 0.21716},
    {'strike': 4145.0, 'callBid': 127.7, 'callAsk': 128.1, 'callMid': 127.9, 'callLatest': 127.9, 'callVolume': 6.0, 'callOpenInterest': 52.0, 'callGamma': 0.00352, 'callIV': 0.21668, 'putBid': 91.7, 'putAsk': 92.1, 'putMid': 91.9, 'putLatest': 91.9, 'putVolume': 1.0, 'putOpenInterest': 98.0, 'putGamma': 0.00352, 'putIV': 0.21668},
    {'strike': 4150.0, 'callBid': 125.1, 'callAsk': 125.5, 'callMid': 125.3, 'callLatest': 125.3, 'callVolume': 17.0, 'callOpenInterest': 461.0, 'callGamma': 0.00360, 'callIV': 0.21620, 'putBid': 94.1, 'putAsk': 94.5, 'putMid': 94.3, 'putLatest': 94.3, 'putVolume': 15.0, 'putOpenInterest': 1162.0, 'putGamma': 0.00360, 'putIV': 0.21620},
    {'strike': 4155.0, 'callBid': 122.4, 'callAsk': 122.8, 'callMid': 122.6, 'callLatest': 122.6, 'callVolume': 13.0, 'callOpenInterest': 37.0, 'callGamma': 0.00364, 'callIV': 0.21602, 'putBid': 96.4, 'putAsk': 96.8, 'putMid': 96.6, 'putLatest': 96.6, 'putVolume': 1.0, 'putOpenInterest': 50.0, 'putGamma': 0.00364, 'putIV': 0.21602},
    {'strike': 4160.0, 'callBid': 119.8, 'callAsk': 120.2, 'callMid': 120.0, 'callLatest': 120.0, 'callVolume': 0.0, 'callOpenInterest': 161.0, 'callGamma': 0.00368, 'callIV': 0.21584, 'putBid': 98.8, 'putAsk': 99.2, 'putMid': 99.0, 'putLatest': 99.0, 'putVolume': 4.0, 'putOpenInterest': 318.0, 'putGamma': 0.00368, 'putIV': 0.21584},
    {'strike': 4165.0, 'callBid': 117.1, 'callAsk': 117.5, 'callMid': 117.3, 'callLatest': 117.3, 'callVolume': 0.0, 'callOpenInterest': 54.0, 'callGamma': 0.00372, 'callIV': 0.21566, 'putBid': 101.1, 'putAsk': 101.5, 'putMid': 101.3, 'putLatest': 101.3, 'putVolume': 16.0, 'putOpenInterest': 81.0, 'putGamma': 0.00372, 'putIV': 0.21566},
    {'strike': 4170.0, 'callBid': 114.5, 'callAsk': 114.9, 'callMid': 114.7, 'callLatest': 114.7, 'callVolume': 5.0, 'callOpenInterest': 155.0, 'callGamma': 0.00376, 'callIV': 0.21548, 'putBid': 103.5, 'putAsk': 103.9, 'putMid': 103.7, 'putLatest': 103.7, 'putVolume': 4.0, 'putOpenInterest': 326.0, 'putGamma': 0.00376, 'putIV': 0.21548},
    {'strike': 4175.0, 'callBid': 111.9, 'callAsk': 112.3, 'callMid': 112.1, 'callLatest': 112.1, 'callVolume': 26.0, 'callOpenInterest': 1039.0, 'callGamma': 0.00380, 'callIV': 0.21530, 'putBid': 105.9, 'putAsk': 106.3, 'putMid': 106.1, 'putLatest': 106.1, 'putVolume': 20.0, 'putOpenInterest': 437.0, 'putGamma': 0.00380, 'putIV': 0.21530},
    {'strike': 4180.0, 'callBid': 109.3, 'callAsk': 109.7, 'callMid': 109.5, 'callLatest': 109.5, 'callVolume': 2.0, 'callOpenInterest': 30.0, 'callGamma': 0.00378, 'callIV': 0.21516, 'putBid': 108.3, 'putAsk': 108.7, 'putMid': 108.5, 'putLatest': 108.5, 'putVolume': 63.0, 'putOpenInterest': 236.0, 'putGamma': 0.00378, 'putIV': 0.21516},
    {'strike': 4185.0, 'callBid': 106.7, 'callAsk': 107.1, 'callMid': 106.9, 'callLatest': 106.9, 'callVolume': 7.0, 'callOpenInterest': 42.0, 'callGamma': 0.00376, 'callIV': 0.21502, 'putBid': 110.7, 'putAsk': 111.1, 'putMid': 110.9, 'putLatest': 110.9, 'putVolume': 19.0, 'putOpenInterest': 95.0, 'putGamma': 0.00376, 'putIV': 0.21502},
    {'strike': 4190.0, 'callBid': 104.1, 'callAsk': 104.5, 'callMid': 104.3, 'callLatest': 104.3, 'callVolume': 20.0, 'callOpenInterest': 425.0, 'callGamma': 0.00374, 'callIV': 0.21488, 'putBid': 113.1, 'putAsk': 113.5, 'putMid': 113.3, 'putLatest': 113.3, 'putVolume': 13.0, 'putOpenInterest': 537.0, 'putGamma': 0.00374, 'putIV': 0.21488},
    {'strike': 4195.0, 'callBid': 101.5, 'callAsk': 101.9, 'callMid': 101.7, 'callLatest': 101.7, 'callVolume': 12.0, 'callOpenInterest': 38.0, 'callGamma': 0.00372, 'callIV': 0.21474, 'putBid': 115.5, 'putAsk': 115.9, 'putMid': 115.7, 'putLatest': 115.7, 'putVolume': 13.0, 'putOpenInterest': 57.0, 'putGamma': 0.00372, 'putIV': 0.21474},
    {'strike': 4200.0, 'callBid': 99.0, 'callAsk': 99.4, 'callMid': 99.2, 'callLatest': 99.2, 'callVolume': 646.0, 'callOpenInterest': 2444.0, 'callGamma': 0.00370, 'callIV': 0.21460, 'putBid': 118.0, 'putAsk': 118.4, 'putMid': 118.2, 'putLatest': 118.2, 'putVolume': 148.0, 'putOpenInterest': 2527.0, 'putGamma': 0.00370, 'putIV': 0.21460},
    {'strike': 4205.0, 'callBid': 96.4, 'callAsk': 96.8, 'callMid': 96.6, 'callLatest': 96.6, 'callVolume': 4.0, 'callOpenInterest': 418.0, 'callGamma': 0.00366, 'callIV': 0.21448, 'putBid': 120.4, 'putAsk': 120.8, 'putMid': 120.6, 'putLatest': 120.6, 'putVolume': 5.0, 'putOpenInterest': 61.0, 'putGamma': 0.00366, 'putIV': 0.21448},
    {'strike': 4210.0, 'callBid': 93.9, 'callAsk': 94.3, 'callMid': 94.1, 'callLatest': 94.1, 'callVolume': 18.0, 'callOpenInterest': 48.0, 'callGamma': 0.00362, 'callIV': 0.21436, 'putBid': 122.9, 'putAsk': 123.3, 'putMid': 123.1, 'putLatest': 123.1, 'putVolume': 7.0, 'putOpenInterest': 108.0, 'putGamma': 0.00362, 'putIV': 0.21436},
    {'strike': 4215.0, 'callBid': 91.4, 'callAsk': 91.8, 'callMid': 91.6, 'callLatest': 91.6, 'callVolume': 5.0, 'callOpenInterest': 91.0, 'callGamma': 0.00358, 'callIV': 0.21424, 'putBid': 125.4, 'putAsk': 125.8, 'putMid': 125.6, 'putLatest': 125.6, 'putVolume': 4.0, 'putOpenInterest': 227.0, 'putGamma': 0.00358, 'putIV': 0.21424},
    {'strike': 4220.0, 'callBid': 88.9, 'callAsk': 89.3, 'callMid': 89.1, 'callLatest': 89.1, 'callVolume': 36.0, 'callOpenInterest': 304.0, 'callGamma': 0.00354, 'callIV': 0.21412, 'putBid': 127.9, 'putAsk': 128.3, 'putMid': 128.1, 'putLatest': 128.1, 'putVolume': 7.0, 'putOpenInterest': 59.0, 'putGamma': 0.00354, 'putIV': 0.21412},
    {'strike': 4225.0, 'callBid': 86.4, 'callAsk': 86.8, 'callMid': 86.6, 'callLatest': 86.6, 'callVolume': 4.0, 'callOpenInterest': 338.0, 'callGamma': 0.00350, 'callIV': 0.21400, 'putBid': 130.4, 'putAsk': 130.8, 'putMid': 130.6, 'putLatest': 130.6, 'putVolume': 7.0, 'putOpenInterest': 264.0, 'putGamma': 0.00350, 'putIV': 0.21400},
    {'strike': 4230.0, 'callBid': 83.9, 'callAsk': 84.3, 'callMid': 84.1, 'callLatest': 84.1, 'callVolume': 10.0, 'callOpenInterest': 101.0, 'callGamma': 0.00342, 'callIV': 0.21380, 'putBid': 132.9, 'putAsk': 133.3, 'putMid': 133.1, 'putLatest': 133.1, 'putVolume': 6.0, 'putOpenInterest': 445.0, 'putGamma': 0.00342, 'putIV': 0.21380}
]

CANONICAL_COLUMNS = [
    'strike',
    'callBid', 'callAsk', 'callMid', 'callLatest', 'callVolume', 'callOpenInterest', 'callGamma', 'callIV',
    'putBid', 'putAsk', 'putMid', 'putLatest', 'putVolume', 'putOpenInterest', 'putGamma', 'putIV'
]


# ==============================================================================
# 2. AUTO CLEANING & NORMALIZATION FUNCTIONS
# ==============================================================================

def clean_val(v: Any, default: float = 0.0) -> float:
    """
    Cleans dirty values smoothly:
    - Sheets formula errors: #ERROR!, #N/A, #VALUE!, #REF!, #DIV/0!, #NUM!, #NAME?
    - Special text indicators: 'unch', 'N/A', 'nan', 'null', 'none', '-', '--', ''
    - Settlement price marker 's' suffix: e.g. '133.40s', '1.80s'
    - Percentage marker '%' suffix: e.g. '26.90%', '15%'
    - Formula leading characters: '+', '='
    - Currency and formatting: '$', commas ',', quotes '"'
    """
    if v is None:
        return default
    if isinstance(v, (int, float)):
        if math.isnan(v) or math.isinf(v):
            return default
        return float(v)

    s = str(v).strip()
    if not s:
        return default

    s_upper = s.upper()
    # Check for spreadsheets errors & keywords
    if any(err in s_upper for err in ('#ERROR', '#REF', '#VALUE', '#N/A', '#DIV/0', '#NUM', '#NAME', 'UNCH', 'NAN', 'NULL', 'NONE')):
        return default
    if s in ('-', '--', '.', 'N/A', 'n/a'):
        return default

    # Remove quotes, currency symbols, and leading formula markers
    s = s.replace('"', '').replace("'", "").replace('$', '')
    while s.startswith(('=', '+')):
        s = s[1:].strip()

    # Remove settlement marker 's' or 'S' at end of number (e.g. 133.40s)
    if s.endswith(('s', 'S')) and len(s) > 1 and (s[-2].isdigit() or s[-2] == '.'):
        s = s[:-1].strip()

    # Remove percentage marker '%'
    if s.endswith('%'):
        s = s[:-1].strip()

    # Remove commas and spaces in numbers (e.g. "4,135.00")
    s = s.replace(',', '').replace(' ', '')

    try:
        val = float(s)
        if math.isnan(val) or math.isinf(val):
            return default
        return val
    except (ValueError, TypeError):
        # Fallback regex search for embedded float
        m = re.search(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', s)
        if m:
            try:
                return float(m.group(0))
            except Exception:
                return default
        return default


def clean_strike(v: Any) -> float:
    """
    Extracts numerical strike price:
    Handles '4,135.00C', '4,135.00P', '+4150', '=4150.00', '4,200', etc.
    """
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)

    s = str(v).strip().replace('"', '').replace("'", "")
    while s.startswith(('=', '+')):
        s = s[1:].strip()

    # Strip trailing C or P
    if s.endswith(('c', 'C', 'p', 'P')):
        s = s[:-1].strip()

    s = s.replace(',', '').replace(' ', '')
    try:
        return float(s)
    except Exception:
        m = re.search(r'\d[\d,]*\.?\d*', str(v))
        if m:
            clean_s = m.group(0).replace(',', '')
            return float(clean_s)
        return 0.0


# ==============================================================================
# 3. MULTI-FORMAT DATA INGESTION PIPELINE
# ==============================================================================

def normalize_options_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardizes any options DataFrame into the canonical 17-column format.
    Ensures strikes are unique, sorted, Bid/Ask mid computed, Gamma/IV clean.
    Supports any clipboard headers with spaces, underscores, or abbreviations.
    """
    if df is None or len(df) == 0:
        return pd.DataFrame(BENCHMARK_GCZ26_DATA)

    norm_col = {re.sub(r'[\s_\-]+', '', str(c).lower()): c for c in df.columns}

    # Detect if dataframe has direct call/put columns
    has_canonical = ('strike' in norm_col or 'k' in norm_col) and (
        'callbid' in norm_col or 'callvolume' in norm_col or 'callvol' in norm_col or 'callopeninterest' in norm_col or 'calloi' in norm_col
    )

    if not has_canonical:
        # Check if table is stacked with 'Type' or strike ends with C/P
        return _parse_stacked_df(df)

    exp_col = norm_col.get('expirationdate') or norm_col.get('expiry') or norm_col.get('expiredate')
    found_exp = ""
    if exp_col and exp_col in df.columns:
        s_series = df[exp_col].dropna()
        if not s_series.empty:
            found_exp = str(s_series.iloc[0]).strip()
    if not found_exp and hasattr(df, 'attrs') and df.attrs.get('expiration_date'):
        found_exp = str(df.attrs['expiration_date']).strip()

    def get_num(r, *keys, default=0.0):
        for k in keys:
            norm_k = re.sub(r'[\s_\-]+', '', k.lower())
            if norm_k in norm_col:
                orig_c = norm_col[norm_k]
                v = r.get(orig_c)
                if pd.notna(v) and str(v).strip() != '':
                    return clean_val(v, default=default)
        return default

    stk_col = norm_col.get('strike', norm_col.get('k', df.columns[0]))

    rows = []
    for _, r in df.iterrows():
        stk = clean_strike(r.get(stk_col))
        if stk <= 0:
            continue

        c_bid = get_num(r, 'callbid', 'call_bid', 'cbid', default=0.0)
        c_ask = get_num(r, 'callask', 'call_ask', 'cask', default=0.0)
        c_last = get_num(r, 'calllatest', 'call_latest', 'calllast', 'clast', default=0.0)
        c_mid_raw = get_num(r, 'callmid', 'call_mid', 'cmid', default=0.0)

        if c_bid > 0 and c_ask > 0:
            c_mid = (c_bid + c_ask) / 2.0
        elif c_mid_raw > 0:
            c_mid = c_mid_raw
        else:
            c_mid = c_last

        c_vol = get_num(r, 'callvolume', 'callvol', 'call_vol', 'call_volume', 'cvol', default=0.0)
        c_oi = get_num(r, 'callopeninterest', 'calloi', 'call_oi', 'call_open_interest', 'coi', default=0.0)
        c_gamma = get_num(r, 'callgamma', 'call_gamma', 'cgamma', 'gamma', default=0.0037)
        if c_gamma <= 0:
            c_gamma = 0.0037

        c_iv = get_num(r, 'calliv', 'call_iv', 'civ', 'iv', default=0.215)
        if c_iv > 1.0:
            c_iv = c_iv / 100.0

        p_bid = get_num(r, 'putbid', 'put_bid', 'pbid', default=0.0)
        p_ask = get_num(r, 'putask', 'put_ask', 'pask', default=0.0)
        p_last = get_num(r, 'putlatest', 'put_latest', 'putlast', 'plast', default=0.0)
        p_mid_raw = get_num(r, 'putmid', 'put_mid', 'pmid', default=0.0)

        if p_bid > 0 and p_ask > 0:
            p_mid = (p_bid + p_ask) / 2.0
        elif p_mid_raw > 0:
            p_mid = p_mid_raw
        else:
            p_mid = p_last

        p_vol = get_num(r, 'putvolume', 'putvol', 'put_vol', 'put_volume', 'pvol', default=0.0)
        p_oi = get_num(r, 'putopeninterest', 'putoi', 'put_oi', 'put_open_interest', 'poi', default=0.0)
        p_gamma = get_num(r, 'putgamma', 'put_gamma', 'pgamma', 'gamma', default=0.0037)
        if p_gamma <= 0:
            p_gamma = 0.0037

        p_iv = get_num(r, 'putiv', 'put_iv', 'piv', 'iv', default=0.215)
        if p_iv > 1.0:
            p_iv = p_iv / 100.0

        r_dict = {
            'strike': stk,
            'callBid': c_bid if c_bid > 0 else (c_mid - 0.20 if c_mid > 0 else 0.0),
            'callAsk': c_ask if c_ask > 0 else (c_mid + 0.20 if c_mid > 0 else 0.0),
            'callMid': c_mid,
            'callLatest': c_last if c_last > 0 else c_mid,
            'callVolume': c_vol,
            'callOpenInterest': c_oi,
            'callGamma': c_gamma,
            'callIV': c_iv,
            'putBid': p_bid if p_bid > 0 else (p_mid - 0.20 if p_mid > 0 else 0.0),
            'putAsk': p_ask if p_ask > 0 else (p_mid + 0.20 if p_mid > 0 else 0.0),
            'putMid': p_mid,
            'putLatest': p_last if p_last > 0 else p_mid,
            'putVolume': p_vol,
            'putOpenInterest': p_oi,
            'putGamma': p_gamma,
            'putIV': p_iv
        }
        if found_exp:
            r_dict['expirationDate'] = found_exp
        rows.append(r_dict)


    out_df = pd.DataFrame(rows)
    if len(out_df) == 0:
        return pd.DataFrame(BENCHMARK_GCZ26_DATA)

    out_df = out_df.drop_duplicates(subset=['strike'], keep='last').sort_values('strike').reset_index(drop=True)
    cols = [c for c in CANONICAL_COLUMNS if c in out_df.columns]
    if 'expirationDate' in out_df.columns:
        cols.append('expirationDate')
        out_df.attrs['expiration_date'] = found_exp
    elif found_exp:
        out_df.attrs['expiration_date'] = found_exp
    return out_df[cols]


def _parse_stacked_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Parses table where Calls and Puts are on separate rows (stacked).
    Matches strikes between Calls and Puts.
    """
    col_map = {c.lower().strip(): c for c in df.columns}
    stk_col = col_map.get('strike', df.columns[0])
    type_col = col_map.get('type', col_map.get('optiontype', None))

    calls_dict: Dict[float, Dict[str, float]] = {}
    puts_dict: Dict[float, Dict[str, float]] = {}

    for _, r in df.iterrows():
        raw_stk = str(r.get(stk_col, ''))
        stk = clean_strike(raw_stk)
        if stk <= 0:
            continue

        is_call = False
        is_put = False

        if type_col and pd.notna(r.get(type_col)):
            t_val = str(r.get(type_col)).upper()
            if 'CALL' in t_val or t_val == 'C':
                is_call = True
            elif 'PUT' in t_val or t_val == 'P':
                is_put = True
        else:
            if 'C' in raw_stk.upper():
                is_call = True
            elif 'P' in raw_stk.upper():
                is_put = True

        bid = clean_val(r.get(col_map.get('bid', col_map.get('bidprice', 0))))
        ask = clean_val(r.get(col_map.get('ask', col_map.get('askprice', 0))))
        latest = clean_val(r.get(col_map.get('latest', col_map.get('lastprice', 0))))
        vol = clean_val(r.get(col_map.get('volume', col_map.get('vol', 0))))
        oi = clean_val(r.get(col_map.get('open int', col_map.get('openinterest', col_map.get('oi', 0)))))
        gamma = clean_val(r.get(col_map.get('gamma', 0.0037)))
        if gamma <= 0:
            gamma = 0.0037
        iv = clean_val(r.get(col_map.get('iv', col_map.get('volatility', 0.215))))
        if iv > 1.0:
            iv = iv / 100.0

        entry = {'bid': bid, 'ask': ask, 'latest': latest, 'vol': vol, 'oi': oi, 'gamma': gamma, 'iv': iv}
        if is_call:
            calls_dict[stk] = entry
        elif is_put:
            puts_dict[stk] = entry

    all_strikes = sorted(set(calls_dict.keys()).union(set(puts_dict.keys())))
    if not all_strikes:
        return pd.DataFrame(BENCHMARK_GCZ26_DATA)

    rows = []
    for k in all_strikes:
        c = calls_dict.get(k, {'bid': 0.0, 'ask': 0.0, 'latest': 0.0, 'vol': 0.0, 'oi': 0.0, 'gamma': 0.0037, 'iv': 0.215})
        p = puts_dict.get(k, {'bid': 0.0, 'ask': 0.0, 'latest': 0.0, 'vol': 0.0, 'oi': 0.0, 'gamma': 0.0037, 'iv': 0.215})

        c_mid = (c['bid'] + c['ask']) / 2.0 if (c['bid'] > 0 and c['ask'] > 0) else c['latest']
        p_mid = (p['bid'] + p['ask']) / 2.0 if (p['bid'] > 0 and p['ask'] > 0) else p['latest']

        rows.append({
            'strike': k,
            'callBid': c['bid'] if c['bid'] > 0 else (c_mid - 0.20 if c_mid > 0 else 0.0),
            'callAsk': c['ask'] if c['ask'] > 0 else (c_mid + 0.20 if c_mid > 0 else 0.0),
            'callMid': c_mid,
            'callLatest': c['latest'] if c['latest'] > 0 else c_mid,
            'callVolume': c['vol'],
            'callOpenInterest': c['oi'],
            'callGamma': c['gamma'],
            'callIV': c['iv'],
            'putBid': p['bid'] if p['bid'] > 0 else (p_mid - 0.20 if p_mid > 0 else 0.0),
            'putAsk': p['ask'] if p['ask'] > 0 else (p_mid + 0.20 if p_mid > 0 else 0.0),
            'putMid': p_mid,
            'putLatest': p['latest'] if p['latest'] > 0 else p_mid,
            'putVolume': p['vol'],
            'putOpenInterest': p['oi'],
            'putGamma': p['gamma'],
            'putIV': p['iv']
        })

    return pd.DataFrame(rows)


def parse_bookmarklet_csv(content_or_path: Union[str, io.StringIO]) -> pd.DataFrame:
    """Parses Bookmarklet 1-Click CSV output."""
    if isinstance(content_or_path, str) and os.path.exists(content_or_path):
        df = pd.read_csv(content_or_path, encoding='utf-8-sig', encoding_errors='ignore', on_bad_lines='skip')
    elif isinstance(content_or_path, io.StringIO):
        df = pd.read_csv(content_or_path, on_bad_lines='skip')
    else:
        df = pd.read_csv(io.StringIO(str(content_or_path)), on_bad_lines='skip')
    return normalize_options_df(df)


def parse_clipboard_tsv(tsv_text: str) -> pd.DataFrame:
    """
    Parses Bookmarklet TSV clipboard:
    Columns: Strike, Call Bid, Call Ask, Call Vol, Call OI, Call Gamma, Put Bid, Put Ask, Put Vol, Put OI, Put Gamma
    """
    df = pd.read_csv(io.StringIO(tsv_text.strip()), sep='\t', on_bad_lines='skip')
    rename_rules = {
        'Strike': 'strike',
        'Call Bid': 'callBid',
        'Call Ask': 'callAsk',
        'Call Vol': 'callVolume',
        'Call OI': 'callOpenInterest',
        'Call Gamma': 'callGamma',
        'Put Bid': 'putBid',
        'Put Ask': 'putAsk',
        'Put Vol': 'putVolume',
        'Put OI': 'putOpenInterest',
        'Put Gamma': 'putGamma'
    }
    df = df.rename(columns=rename_rules)
    return normalize_options_df(df)


def parse_dual_files(prices_path: str, greeks_path: Optional[str] = None) -> pd.DataFrame:
    """
    Parses legacy dual-files (raw 1-cell-per-line dump) robustly using regex scanning.
    """
    greeks_map: Dict[float, Dict[str, float]] = {}
    if greeks_path and os.path.exists(greeks_path):
        with open(greeks_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
            g_lines = [l.strip() for l in f if l.strip()]

        # Scan for Put/Call Greeks rows
        for i in range(len(g_lines)):
            line = g_lines[i]
            # Match strike e.g. "3,950.00"
            m = re.match(r'^"?(\d{1,2},\d{3}\.\d{2})"?$', line)
            if m and i + 5 < len(g_lines):
                # Next line might be Put/Call
                k = float(m.group(1).replace(',', ''))
                # Look ahead for IV & Gamma in next 5 lines
                for j in range(i + 1, min(i + 7, len(g_lines))):
                    chunk_val = g_lines[j]
                    if '%' in chunk_val and k not in greeks_map:
                        iv_val = clean_val(chunk_val) / 100.0
                        gamma_val = clean_val(g_lines[j + 2]) if j + 2 < len(g_lines) else 0.0037
                        greeks_map[k] = {'iv': iv_val, 'gamma': gamma_val if gamma_val > 0 else 0.0037}
                        break

    with open(prices_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
        p_lines = [l.strip() for l in f if l.strip()]

    calls: Dict[float, Dict[str, float]] = {}
    puts: Dict[float, Dict[str, float]] = {}

    for i, line in enumerate(p_lines):
        m_c = re.match(r'^"?(\d{1,2},\d{3}\.\d{2})C"?$', line)
        if m_c and i + 10 < len(p_lines):
            stk = float(m_c.group(1).replace(',', ''))
            calls[stk] = {
                'latest': clean_val(p_lines[i + 4]),
                'bid': clean_val(p_lines[i + 6]),
                'ask': clean_val(p_lines[i + 7]),
                'vol': clean_val(p_lines[i + 8]),
                'oi': clean_val(p_lines[i + 9]),
            }
            continue

        m_p = re.match(r'^"?(\d{1,2},\d{3}\.\d{2})P"?$', line)
        if m_p and i + 10 < len(p_lines):
            stk = float(m_p.group(1).replace(',', ''))
            puts[stk] = {
                'latest': clean_val(p_lines[i + 4]),
                'bid': clean_val(p_lines[i + 6]),
                'ask': clean_val(p_lines[i + 7]),
                'vol': clean_val(p_lines[i + 8]),
                'oi': clean_val(p_lines[i + 9]),
            }

    matched_strikes = sorted(set(calls.keys()).intersection(set(puts.keys())))
    if not matched_strikes:
        # Fallback to union if intersection is empty
        matched_strikes = sorted(set(calls.keys()).union(set(puts.keys())))

    if not matched_strikes:
        return pd.DataFrame(BENCHMARK_GCZ26_DATA)

    ref_strikes = np.array(sorted(greeks_map.keys())) if greeks_map else np.array([])
    ref_gammas = np.array([greeks_map[k]['gamma'] for k in ref_strikes]) if greeks_map else np.array([])
    ref_ivs = np.array([greeks_map[k]['iv'] for k in ref_strikes]) if greeks_map else np.array([])

    rows = []
    for k in matched_strikes:
        c = calls.get(k, {'bid': 0.0, 'ask': 0.0, 'latest': 0.0, 'vol': 0.0, 'oi': 0.0})
        p = puts.get(k, {'bid': 0.0, 'ask': 0.0, 'latest': 0.0, 'vol': 0.0, 'oi': 0.0})

        c_mid = (c['bid'] + c['ask']) / 2.0 if (c['bid'] > 0 and c['ask'] > 0) else c['latest']
        p_mid = (p['bid'] + p['ask']) / 2.0 if (p['bid'] > 0 and p['ask'] > 0) else p['latest']

        if len(ref_strikes) > 0:
            interp_gamma = float(np.interp(k, ref_strikes, ref_gammas))
            interp_iv = float(np.interp(k, ref_strikes, ref_ivs))
        else:
            interp_gamma = 0.0037
            interp_iv = 0.215

        rows.append({
            'strike': k,
            'callBid': c['bid'] if c['bid'] > 0 else (c_mid - 0.20 if c_mid > 0 else 0.0),
            'callAsk': c['ask'] if c['ask'] > 0 else (c_mid + 0.20 if c_mid > 0 else 0.0),
            'callMid': c_mid,
            'callLatest': c['latest'] if c['latest'] > 0 else c_mid,
            'callOpenInterest': c['oi'],
            'callVolume': c['vol'],
            'callGamma': interp_gamma,
            'callIV': interp_iv,
            'putBid': p['bid'] if p['bid'] > 0 else (p_mid - 0.20 if p_mid > 0 else 0.0),
            'putAsk': p['ask'] if p['ask'] > 0 else (p_mid + 0.20 if p_mid > 0 else 0.0),
            'putMid': p_mid,
            'putLatest': p['latest'] if p['latest'] > 0 else p_mid,
            'putOpenInterest': p['oi'],
            'putVolume': p['vol'],
            'putGamma': interp_gamma,
            'putIV': interp_iv,
        })

    return pd.DataFrame(rows)


def load_options_data(
    source: Optional[Union[str, pd.DataFrame]] = None,
    data_dir: Optional[str] = None
) -> pd.DataFrame:
    """
    Universal Automated Data Loader:
    - If `source` is a DataFrame: normalizes and returns.
    - If `source` is "clipboard": reads clipboard directly.
    - If `source` is a raw TSV or CSV string: parses automatically.
    - If `source` is a file path: detects format and loads.
    - If `source` is None: searches candidate directories for Bookmarklet or options CSVs.
    - If nothing found: falls back safely to institutional GCZ26 benchmark data.
    """
    if isinstance(source, pd.DataFrame):
        return normalize_options_df(source)
    if isinstance(source, list):
        return normalize_options_df(pd.DataFrame(source))

    # 1. Clipboard direct string or directive
    if isinstance(source, str):
        s_strip = source.strip()
        if s_strip.lower() == 'clipboard':
            try:
                clip_df = pd.read_clipboard()
                return normalize_options_df(clip_df)
            except Exception:
                pass
        # Raw TSV text with tabs
        elif '\t' in s_strip and ('Strike' in s_strip or 'strike' in s_strip):
            return parse_clipboard_tsv(s_strip)
        # Raw CSV text
        elif '\n' in s_strip and (',' in s_strip) and ('strike' in s_strip.lower()):
            return parse_bookmarklet_csv(s_strip)
        # File path
        elif os.path.exists(source):
            return _load_from_path(source)
        else:
            return pd.DataFrame(BENCHMARK_GCZ26_DATA)

    # 2. Search candidate directories (only when source is None)
    search_dirs = []
    if data_dir:
        search_dirs.append(data_dir)
    search_dirs.extend([
        '/content',
        '/content/drive/MyDrive/Neiro-Quant/data',
        'data',
        '../data',
        '.',
        r'H:\My Drive\Neiro-Quant\data',
        r'H:\My Drive\Neiro-Quant',
        'docs/tailieudacta'
    ])

    file_patterns = [
        'options_prices_GCZ*.csv',
        'options_prices*.csv',
        '*options*prices*.csv',
        '*Options*Prices*.csv',
        '*Options*.csv',
        '*options*.csv',
        '*stacked-intraday*.csv',
        '*volatility-greeks*.csv',
        '*greeks*.csv'
    ]

    for d in search_dirs:
        if not os.path.exists(d):
            continue
        for pat in file_patterns:
            matches = glob.glob(os.path.join(d, pat))
            if matches:
                target = matches[0]
                try:
                    df = _load_from_path(target, data_dir=d)
                    if not df.empty and len(df) > 0 and 'strike' in df.columns:
                        print(f"[NGUON DU LIEU] Da nap thanh cong tu file: '{target}' ({len(df)} strikes)")
                        return df
                except Exception:
                    continue

    # 3. Fallback Benchmark Data
    print("[NGUON DU LIEU] Khong tim thay file CSV phu hop -> Dang dung Benchmark CME GCZ26 du phong.")
    return pd.DataFrame(BENCHMARK_GCZ26_DATA)


def _load_from_path(file_path: str, data_dir: Optional[str] = None) -> pd.DataFrame:
    """Helper to detect file structure and load."""
    if not os.path.exists(file_path):
        return pd.DataFrame(BENCHMARK_GCZ26_DATA)

    # Peek first line
    with open(file_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
        first_line = f.readline().strip()
        second_line = f.readline().strip()

    # Case A: Bookmarklet 1-Click CSV
    if 'strike' in first_line.lower() and ('callbid' in first_line.lower() or 'callvolume' in first_line.lower() or 'callopeninterest' in first_line.lower()):
        df = parse_bookmarklet_csv(file_path)
        # Check if there is a sister greeks file in the same directory to auto-merge real greeks
        parent_dir = data_dir or os.path.dirname(file_path) or 'data'
        if os.path.exists(parent_dir):
            try:
                for gf_name in os.listdir(parent_dir):
                    if 'greek' in gf_name.lower() and gf_name.lower().endswith('.csv') and os.path.abspath(os.path.join(parent_dir, gf_name)) != os.path.abspath(file_path):
                        gdf = pd.read_csv(os.path.join(parent_dir, gf_name))
                        col_gamma = next((c for c in gdf.columns if 'gamma' in c.lower() and 'call' in c.lower()), None) or next((c for c in gdf.columns if 'gamma' in c.lower()), None)
                        col_put_gamma = next((c for c in gdf.columns if 'gamma' in c.lower() and 'put' in c.lower()), None) or col_gamma
                        if col_gamma and 'strike' in [c.lower() for c in gdf.columns]:
                            stk_col = next(c for c in gdf.columns if 'strike' in c.lower())
                            g_map = dict(zip(gdf[stk_col], gdf[col_gamma]))
                            pg_map = dict(zip(gdf[stk_col], gdf[col_put_gamma]))
                            df['callGamma'] = df['strike'].map(g_map).fillna(df['callGamma'])
                            df['putGamma'] = df['strike'].map(pg_map).fillna(df['putGamma'])
                            break
            except Exception:
                pass
        return df

    # Case B: Bookmarklet TSV
    if '\t' in first_line and 'strike' in first_line.lower():
        with open(file_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
            return parse_clipboard_tsv(f.read())

    # Case C: Standard Table with header
    if any(h in first_line.lower() for h in ['strike', 'type', 'bid', 'ask']):
        df = pd.read_csv(file_path, encoding='utf-8-sig', encoding_errors='ignore', on_bad_lines='skip')
        return normalize_options_df(df)

    # Case D: Legacy line dump (Calls on top, Puts below)
    parent_dir = data_dir or os.path.dirname(file_path) or 'data'
    greeks_file = os.path.join(parent_dir, 'volatility-greeks.csv')
    return parse_dual_files(file_path, greeks_file if os.path.exists(greeks_file) else None)


def aggregate_options_dataframes(
    dfs: list[pd.DataFrame],
    spot_price: Optional[float] = None,
    r: float = 0.045,
    default_iv: float = 0.16,
) -> pd.DataFrame:
    """Aggregates multiple options chains (e.g. Weekly + Monthly) across strikes.

    Superimposes Dealer GEX and Gamma Power:
        - Power_Call(K) = sum_i [ OI_Call,i(K) * Gamma_Call,i(K) ]
        - Power_Put(K)  = sum_i [ OI_Put,i(K)  * Gamma_Put,i(K)  ]
        - GEX_Call(K)   = sum_i [ GEX_Call,i(K) ]
        - GEX_Put(K)    = sum_i [ GEX_Put,i(K) ]
        - NetGEX(K)     = GEX_Call(K) + GEX_Put(K)

    Preserves nearest-expiry market prices (callBid, callAsk, putBid, putAsk).
    """
    if not dfs:
        return pd.DataFrame()

    valid_dfs = []
    for d in dfs:
        if d is not None and not d.empty:
            norm_d = normalize_options_df(d).copy()
            if not norm_d.empty and "strike" in norm_d.columns:
                valid_dfs.append(norm_d)

    if not valid_dfs:
        return pd.DataFrame()

    if len(valid_dfs) == 1:
        single_df = valid_dfs[0].copy()
        if "callGammaPower" not in single_df.columns:
            single_df["callGammaPower"] = single_df["callOpenInterest"] * single_df["callGamma"]
        if "putGammaPower" not in single_df.columns:
            single_df["putGammaPower"] = single_df["putOpenInterest"] * single_df["putGamma"]
        return single_df

    # Sort chains by DTE ascending so that index 0 is nearest to expiration
    def get_dte(df_item: pd.DataFrame) -> float:
        if "dte_days" in df_item.attrs:
            return float(df_item.attrs["dte_days"])
        exp_val = df_item.attrs.get("expiration_date")
        if not exp_val and "expirationDate" in df_item.columns and not df_item["expirationDate"].dropna().empty:
            exp_val = df_item["expirationDate"].dropna().iloc[0]
        return compute_dynamic_dte(exp_val, default_dte=30.0)

    valid_dfs.sort(key=get_dte)

    spot = spot_price
    if spot is None or spot <= 0:
        atm_idx = (valid_dfs[0]["callMid"] - valid_dfs[0]["putMid"]).abs().idxmin()
        spot = float(valid_dfs[0].loc[atm_idx, "strike"])

    MULT = 100.0
    scale = (spot ** 2) * 0.01 / 1e6

    processed_dfs = []
    for df_item in valid_dfs:
        d_copy = df_item.copy()
        dte = get_dte(d_copy)
        t_years = max(float(dte) / 365.0, 1.0 / 365.0)
        sigma = max(0.01, float(default_iv))
        denom = sigma * math.sqrt(t_years)
        half_sig2_t = 0.5 * (sigma ** 2) * t_years
        df_disc = math.exp(-r * t_years)

        strikes_arr = d_copy["strike"].values.astype(float)
        d1 = (np.log(np.maximum(1e-4, spot / strikes_arr)) + half_sig2_t) / denom
        pdf_d1 = (1.0 / math.sqrt(2.0 * math.pi)) * np.exp(-0.5 * (d1 ** 2))
        b76_gamma = (df_disc * pdf_d1) / np.maximum(1e-4, spot * denom)

        # Fill gamma if missing / zero
        d_copy["callGamma"] = np.where(d_copy["callGamma"] > 0, d_copy["callGamma"], b76_gamma)
        d_copy["putGamma"] = np.where(d_copy["putGamma"] > 0, d_copy["putGamma"], b76_gamma)

        d_copy["callGammaPower"] = d_copy["callOpenInterest"] * d_copy["callGamma"]
        d_copy["putGammaPower"] = d_copy["putOpenInterest"] * d_copy["putGamma"]

        d_copy["callGEX"] = d_copy["callGamma"] * d_copy["callOpenInterest"] * MULT * scale
        d_copy["putGEX"] = - (d_copy["putGamma"] * d_copy["putOpenInterest"] * MULT * scale)
        d_copy["netGEX"] = d_copy["callGEX"] + d_copy["putGEX"]

        processed_dfs.append(d_copy)

    # Base pricing from nearest expiration
    nearest_df = processed_dfs[0].set_index("strike")
    price_cols = [
        "callBid", "callAsk", "callMid", "callLatest", "callIV",
        "putBid", "putAsk", "putMid", "putLatest", "putIV"
    ]

    concat_all = pd.concat(processed_dfs, ignore_index=True)
    agg_df = concat_all.groupby("strike", as_index=False).agg({
        "callOpenInterest": "sum",
        "putOpenInterest": "sum",
        "callVolume": "sum",
        "putVolume": "sum",
        "callGammaPower": "sum",
        "putGammaPower": "sum",
        "callGEX": "sum",
        "putGEX": "sum",
        "netGEX": "sum",
    })

    # Superimposed effective Gamma
    agg_df["callGamma"] = np.where(
        agg_df["callOpenInterest"] > 0,
        agg_df["callGammaPower"] / np.maximum(1, agg_df["callOpenInterest"]),
        0.0,
    )
    agg_df["putGamma"] = np.where(
        agg_df["putOpenInterest"] > 0,
        agg_df["putGammaPower"] / np.maximum(1, agg_df["putOpenInterest"]),
        0.0,
    )

    # Merge pricing columns from nearest chain
    for col in price_cols:
        if col in nearest_df.columns:
            agg_df[col] = agg_df["strike"].map(nearest_df[col]).fillna(0.0)
        else:
            agg_df[col] = 0.0

    agg_df = agg_df.sort_values("strike").reset_index(drop=True)
    agg_df.attrs["is_aggregated"] = True
    agg_df.attrs["aggregated_count"] = len(processed_dfs)
    agg_df.attrs["expiration_date"] = valid_dfs[0].attrs.get("expiration_date", "MULTI-EXPIRY")
    agg_df.attrs["dte_days"] = get_dte(valid_dfs[0])

    return agg_df


def load_multi_expiry_options(data_dir: Optional[str] = None) -> pd.DataFrame:
    """Discovers all available options chain files in data_dir and aggregates them."""
    search_dir = data_dir or "data"
    if not os.path.exists(search_dir):
        return load_options_data()

    pattern = os.path.join(search_dir, "options_prices*.csv")
    matched_files = glob.glob(pattern)
    # Exclude near_the_money slice if full file exists
    matched_files = [f for f in matched_files if "near_the_money" not in os.path.basename(f).lower()]

    if not matched_files:
        return load_options_data(data_dir=data_dir)

    # If individual sub-expiry files exist (e.g. options_prices_*_OG*.csv), aggregate ONLY the sub-expiry files
    # to prevent double-counting against the master options_prices_GCZ26.csv
    sub_expiry_files = [
        f for f in matched_files
        if os.path.basename(f).lower() not in ["options_prices_gcz26.csv", "options_prices.csv"]
        and "_og" in os.path.basename(f).lower()
    ]
    files_to_load = sub_expiry_files if len(sub_expiry_files) >= 2 else matched_files

    if len(files_to_load) == 1:
        return _load_from_path(files_to_load[0], data_dir=search_dir)

    dfs = []
    for f in files_to_load:
        try:
            d = _load_from_path(f, data_dir=search_dir)
            if not d.empty and len(d) > 0 and "strike" in d.columns:
                dfs.append(d)
        except Exception:
            continue

    if not dfs:
        return load_options_data(data_dir=data_dir)

    return aggregate_options_dataframes(dfs)


# ==============================================================================
# 4. QUANT MATRIX & REAL-TIME TACTICAL BOARD GENERATOR
# ==============================================================================

def compute_tactical_matrix(
    df: pd.DataFrame,
    spot: Optional[float] = None,
    r: float = 0.045,
    dte_days: Optional[float] = None
) -> Dict[str, Any]:
    """
    Computes Net GEX matrix, Delta Flow, institutional key levels,
    and returns a structured Real-time Tactical Board (Bang tac chien dinh luong).
    """
    df = normalize_options_df(df).copy()
    if df.empty:
        df = normalize_options_df(pd.DataFrame(BENCHMARK_GCZ26_DATA)).copy()

    if dte_days is None:
        exp_val = df.attrs.get('expiration_date') or (df['expirationDate'].dropna().iloc[0] if 'expirationDate' in df.columns and not df['expirationDate'].dropna().empty else None)
        effective_dte = compute_dynamic_dte(exp_val, default_dte=30.0)
    else:
        effective_dte = float(dte_days)

    # 1. Determine Spot Price via Implied Spot if not provided
    atm_idx = (df['callMid'] - df['putMid']).abs().idxmin()
    atm_strike = float(df.loc[atm_idx, 'strike'])
    c_mid_atm = float(df.loc[atm_idx, 'callMid'])
    p_mid_atm = float(df.loc[atm_idx, 'putMid'])

    if spot is None or spot <= 0:
        spot_price = compute_implied_spot(atm_strike, c_mid_atm, p_mid_atm, r=r, T=effective_dte / 365.0)
    else:
        spot_price = float(spot)

    # 2. Net GEX & Delta Flow Calculation
    # MULT = 100 troy oz per CME Gold contract
    MULT = 100.0
    scale = (spot_price ** 2) * 0.01 / 1e6

    df['callGEX'] = df['callGamma'] * df['callOpenInterest'] * MULT * scale
    df['putGEX'] = - (df['putGamma'] * df['putOpenInterest'] * MULT * scale)
    df['netGEX'] = df['callGEX'] + df['putGEX']

    df['callDeltaFlow'] = df['callVolume'] * MULT * scale
    df['putDeltaFlow'] = - (df['putVolume'] * MULT * scale)
    df['netDeltaFlow'] = df['callDeltaFlow'] + df['putDeltaFlow']

    # 2.2 Second-Order Greeks: Vanna (VEX) & Charm (CHEX) Calculation (Black-76)
    T_years = max(float(effective_dte) / 365.0, 1.0 / 365.0)
    atm_straddle = c_mid_atm + p_mid_atm
    if spot_price > 0 and T_years > 0:
        sigma_atm = atm_straddle / (0.7979 * spot_price * np.sqrt(T_years))
        sigma_atm = float(np.clip(sigma_atm, 0.01, 2.0))
    else:
        sigma_atm = 0.15

    strikes_arr = df['strike'].values.astype(float)
    denom = sigma_atm * np.sqrt(T_years)
    d1 = (np.log(np.maximum(1e-4, spot_price / strikes_arr)) + 0.5 * (sigma_atm ** 2) * T_years) / denom
    d2 = d1 - denom

    pdf_d1 = (1.0 / np.sqrt(2.0 * np.pi)) * np.exp(-0.5 * (d1 ** 2))
    cdf_d1 = 0.5 * (1.0 + np.vectorize(math.erf)(d1 / np.sqrt(2.0)))
    df_discount = np.exp(-r * T_years)

    # Vanna = -df * n(d1) * (d2 / sigma)
    vanna = - df_discount * pdf_d1 * (d2 / sigma_atm)

    # Charm_call = -df * [ n(d1) * (r / denom - d2 / (2T)) - r * N(d1) ]
    charm_call = - df_discount * (pdf_d1 * (r / denom - d2 / (2.0 * T_years)) - r * cdf_d1)
    charm_put = charm_call - r * df_discount

    charm_call_day = charm_call / 365.0
    charm_put_day = charm_put / 365.0

    # VEX ($M per 1% IV shift) & CHEX ($M per day of decay)
    df['callVEX'] = vanna * df['callOpenInterest'] * MULT * spot_price * 0.01 / 1e6
    df['putVEX'] = - (vanna * df['putOpenInterest'] * MULT * spot_price * 0.01 / 1e6)
    df['netVEX'] = df['callVEX'] + df['putVEX']

    df['callCHEX'] = charm_call_day * df['callOpenInterest'] * MULT * spot_price / 1e6
    df['putCHEX'] = - (charm_put_day * df['putOpenInterest'] * MULT * spot_price / 1e6)
    df['netCHEX'] = df['callCHEX'] + df['putCHEX']

    # 3. Institutional Walls & Levels: Gamma-Weighted vs Raw OI
    snap = to_options_snapshot(df)
    call_walls_gamma, put_walls_gamma = find_gamma_weighted_walls(
        df, top_n=2, spot_price=spot_price, r=r, dte_days=effective_dte, default_iv=sigma_atm
    )
    call_walls_oi, put_walls_oi = find_walls(snap, top_n=2, spot_price=spot_price)

    total_net_gex = float(df['netGEX'].sum())
    total_net_vex = float(df['netVEX'].sum())
    total_net_chex = float(df['netCHEX'].sum())
    regime = "LONG_GAMMA" if total_net_gex > 10.0 else ("SHORT_GAMMA" if total_net_gex < -10.0 else "NEUTRAL")

    if call_walls_gamma:
        call_wall = float(call_walls_gamma[0].strike)
        call_wall_oi = int(call_walls_gamma[0].oi)
        call_wall_siege = float(call_walls_gamma[0].siege_ratio)
        call_wall_power = float(call_walls_gamma[0].gamma_power)
        call_wall_regime = call_walls_gamma[0].regime
    else:
        call_wall_row = df.loc[df['callOpenInterest'].idxmax()]
        call_wall = float(call_wall_row['strike'])
        call_wall_oi = int(call_wall_row['callOpenInterest'])
        call_wall_siege = compute_wall_siege_ratio(int(call_wall_row['callVolume']), call_wall_oi)
        call_wall_power = 0.0
        call_wall_regime = "NEUTRAL"

    if put_walls_gamma:
        put_wall = float(put_walls_gamma[0].strike)
        put_wall_oi = int(put_walls_gamma[0].oi)
        put_wall_siege = float(put_walls_gamma[0].siege_ratio)
        put_wall_power = float(put_walls_gamma[0].gamma_power)
        put_wall_regime = put_walls_gamma[0].regime
    else:
        put_wall_row = df.loc[df['putOpenInterest'].idxmax()]
        put_wall = float(put_wall_row['strike'])
        put_wall_oi = int(put_wall_row['putOpenInterest'])
        put_wall_siege = compute_wall_siege_ratio(int(put_wall_row['putVolume']), put_wall_oi)
        put_wall_power = 0.0
        put_wall_regime = "NEUTRAL"

    # Gamma Flip: Solve exact continuous S* where aggregate net dealer GEX = 0
    exact_gamma_flip = compute_exact_gamma_flip(
        snap, spot_price=spot_price, r=r, dte_days=effective_dte, default_iv=sigma_atm
    )
    gamma_flip_floor = exact_gamma_flip if exact_gamma_flip is not None else float(call_wall if total_net_gex < 0 else put_wall)

    squeeze_trigger = call_wall + 2.50
    waterfall_trigger = put_wall - 2.50

    # 4. Straddle & 1-Sigma Expected Move (Brenner-Subrahmanyam)
    expected_move_1s = atm_straddle / 0.7979

    # 5. Build Structured Tactical Table (Bảng tác chiến định lượng theo thời gian thực)
    put_wall_note = (
        f"Put Wall {put_wall:.0f} là BẪY NAM CHÂM GIA TỐC (Negative GEX / Siege {put_wall_siege:.2f}) -> CẤM ĐẶT LIMIT ĐÓN ĐẦU, chờ đâm thủng quét gamma mới buy reversal"
        if put_wall_regime == "MAGNET_WALL"
        else f"Major Put Wall {put_wall_oi:,} OI (Vùng đệm tiền đáy - Pinning Bounce)"
    )
    call_wall_note = (
        f"Call Wall {call_wall:.0f} là BẪY NAM CHÂM GIA TỐC (Short Gamma squeeze)"
        if call_wall_regime == "MAGNET_WALL"
        else f"Call Wall {call_wall_oi:,} OI (MM ép cản giá bán khống chế)"
    )

    tactical_rows = [
        {
            'Chien Luoc': '1. BAN DINH (Fade Sell)',
            'Vung Gia CME': f"{call_wall - 1.50:.2f} - {call_wall:.2f}",
            'Entry': f"{call_wall - 1.00:.2f}",
            'Hard SL': f"{call_wall + 4.00:.2f} ($4.0)",
            'TP1 / TP2': f"{spot_price:.2f} / {atm_strike:.2f}",
            'Ghi Chu': call_wall_note
        },
        {
            'Chien Luoc': '2. MUA DAY (Rebound Buy)',
            'Vung Gia CME': f"{put_wall:.2f} - {put_wall + 1.50:.2f}",
            'Entry': f"{put_wall + 0.50:.2f}",
            'Hard SL': f"{put_wall - 4.00:.2f} ($4.0)",
            'TP1 / TP2': f"{spot_price:.2f} / {call_wall:.2f}",
            'Ghi Chu': put_wall_note
        },
        {
            'Chien Luoc': '3. MUA DUOI (Squeeze Break)',
            'Vung Gia CME': f"Vuot > {squeeze_trigger:.2f}",
            'Entry': f"{squeeze_trigger + 0.50:.2f}",
            'Hard SL': f"{squeeze_trigger - 3.50:.2f} ($4.0)",
            'TP1 / TP2': f"{call_wall + 15.0:.2f} / {call_wall + 20.0:.2f}",
            'Ghi Chu': f"Vo tuong Call {call_wall:.0f} -> MM cover short mua duoi manh"
        },
        {
            'Chien Luoc': '4. BAN THAO (Waterfall Break)',
            'Vung Gia CME': f"Thung < {waterfall_trigger:.2f}",
            'Entry': f"{waterfall_trigger - 1.00:.2f}",
            'Hard SL': f"{waterfall_trigger + 3.50:.2f} ($4.5)",
            'TP1 / TP2': f"{put_wall - 15.0:.2f} / {put_wall - 20.0:.2f}",
            'Ghi Chu': f"Thung Put Wall {put_wall:.0f} -> Hoang loan roi tu do vao Air Pocket"
        }
    ]

    tactical_table = pd.DataFrame(tactical_rows)

    return {
        'df': df,
        'spot_price': spot_price,
        'atm_strike': atm_strike,
        'call_wall': call_wall,
        'call_wall_oi': call_wall_oi,
        'call_wall_siege': call_wall_siege,
        'call_wall_power': call_wall_power,
        'call_wall_regime': call_wall_regime,
        'put_wall': put_wall,
        'put_wall_oi': put_wall_oi,
        'put_wall_siege': put_wall_siege,
        'put_wall_power': put_wall_power,
        'put_wall_regime': put_wall_regime,
        'total_net_gex': total_net_gex,
        'total_net_vex': total_net_vex,
        'total_net_chex': total_net_chex,
        'sigma_atm': sigma_atm,
        'regime': regime,
        'gamma_flip_floor': gamma_flip_floor,
        'exact_gamma_flip': exact_gamma_flip,
        'zero_gamma_flip': exact_gamma_flip,
        'squeeze_trigger': squeeze_trigger,
        'waterfall_trigger': waterfall_trigger,
        'atm_straddle': atm_straddle,
        'expected_move_1s': expected_move_1s,
        'tactical_table': tactical_table
    }


def generate_tactical_summary(
    source: Optional[Union[str, pd.DataFrame]] = None,
    spot: Optional[float] = None
) -> pd.DataFrame:
    """One-click entry point to load data and return the Tactical Board."""
    df = load_options_data(source)
    matrix = compute_tactical_matrix(df, spot=spot)
    return matrix['tactical_table']


# ==============================================================================
# 5. INTEROPERABILITY WITH MODELS & STRATEGY
# ==============================================================================

def to_options_snapshot(
    df: pd.DataFrame,
    symbol: str = "GCZ26",
    expiry: Optional[str] = None,
    timestamp: str = ""
) -> OptionsSnapshot:
    """Converts normalized DataFrame into OptionsSnapshot model."""
    df = normalize_options_df(df)
    if not expiry:
        exp_found = df.attrs.get('expiration_date') or (df['expirationDate'].dropna().iloc[0] if 'expirationDate' in df.columns and not df['expirationDate'].dropna().empty else None)
        expiry_val = str(exp_found) if exp_found else "DEC26"
    else:
        expiry_val = expiry

    strikes = tuple(
        OptionsStrike(
            strike=float(r['strike']),
            call_bid=float(r['callBid']),
            call_ask=float(r['callAsk']),
            call_oi=int(r['callOpenInterest']),
            call_volume=int(r['callVolume']),
            put_bid=float(r['putBid']),
            put_ask=float(r['putAsk']),
            put_oi=int(r['putOpenInterest']),
            put_volume=int(r['putVolume'])
        )
        for _, r in df.iterrows()
    )
    return OptionsSnapshot(symbol=symbol, expiry=expiry_val, timestamp=timestamp, strikes=strikes)


def to_market_snapshot(
    df: pd.DataFrame,
    spot: Optional[float] = None,
    dte_days: Optional[float] = None,
    risk_free_rate: float = 0.045
) -> MarketSnapshot:
    """Converts normalized DataFrame into MarketSnapshot model for Strategy V2."""
    df = normalize_options_df(df)
    if dte_days is None:
        exp_val = df.attrs.get('expiration_date') or (df['expirationDate'].dropna().iloc[0] if 'expirationDate' in df.columns and not df['expirationDate'].dropna().empty else None)
        effective_dte = compute_dynamic_dte(exp_val, default_dte=30.0)
    else:
        effective_dte = float(dte_days)

    quotes = tuple(
        OptionQuote(
            strike=float(r['strike']),
            call_mid=float(r['callMid']),
            put_mid=float(r['putMid']),
            call_oi=float(r['callOpenInterest']),
            put_oi=float(r['putOpenInterest']),
            call_gamma=float(r['callGamma']),
            put_gamma=float(r['putGamma']),
            call_iv=float(r['callIV']),
            put_iv=float(r['putIV'])
        )
        for _, r in df.iterrows()
    )

    if spot is None or spot <= 0:
        atm_idx = (df['callMid'] - df['putMid']).abs().idxmin()
        atm_strike = float(df.loc[atm_idx, 'strike'])
        c_mid_atm = float(df.loc[atm_idx, 'callMid'])
        p_mid_atm = float(df.loc[atm_idx, 'putMid'])
        spot_price = compute_implied_spot(atm_strike, c_mid_atm, p_mid_atm, r=risk_free_rate, T=effective_dte / 365.0)
    else:
        spot_price = float(spot)

    return MarketSnapshot(
        spot=spot_price,
        dte_days=effective_dte,
        quotes=quotes,
        risk_free_rate=risk_free_rate
    )
