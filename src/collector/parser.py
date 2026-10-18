"""Barchart Options Chain JSON parser.

Parses raw JSON responses from Barchart core-api/v1/options/get into
standardized Neiro-Quant tabular format for CME Gold (GCZ26).
"""
from __future__ import annotations

import logging
from typing import Any
import pandas as pd

logger = logging.getLogger(__name__)


def clean_num(val: Any, default: float = 0.0) -> float:
    """Clean string or number into float safely."""
    if val is None:
        return default
    if isinstance(val, (int, float)):
        import math
        return default if math.isnan(val) else float(val)
    s = str(val).strip().replace(",", "").replace("$", "").replace("%", "").replace("+", "").replace('"', "").replace("'", "")
    if s.endswith("s"):
        s = s[:-1]
    if s.lower() in ("", "none", "nan", "null", "n/a", "-", "--", "unch"):
        return default
    try:
        return float(s)
    except ValueError:
        return default


def parse_barchart_json(json_data: dict[str, Any] | list[Any]) -> pd.DataFrame:
    """Parse Barchart options response into standardized DataFrame.

    Matches structure:
    strike,callBid,callAsk,callMid,callLatest,callVolume,callOpenInterest,callGamma,callIV,
    putBid,putAsk,putMid,putLatest,putVolume,putOpenInterest,putGamma,putIV
    """
    if not json_data:
        raise ValueError("Empty JSON data provided to parser")

    # Extract records list
    records: list[dict[str, Any]] = []
    if isinstance(json_data, list):
        records = json_data
    elif isinstance(json_data, dict):
        d = json_data.get("data") or json_data.get("results") or json_data
        if isinstance(d, list):
            records = d
        elif isinstance(d, dict):
            # Check for Call / Put split
            for key in ("Call", "Put", "calls", "puts"):
                if key in d and isinstance(d[key], list):
                    records.extend(d[key])
            if not records:
                # Flatten any list values
                for v in d.values():
                    if isinstance(v, list):
                        records.extend(v)
                    elif isinstance(v, dict):
                        records.append(v)

    if not records:
        raise ValueError("Could not extract options records from JSON structure")

    call_map: dict[float, dict[str, Any]] = {}
    put_map: dict[float, dict[str, Any]] = {}
    all_strikes: set[float] = set()

    for item in records:
        if not isinstance(item, dict):
            continue
        raw = item.get("raw") if isinstance(item.get("raw"), dict) else item
        
        # Strike price
        k_val = raw.get("strikePrice") or raw.get("strike") or raw.get("strike_price")
        if k_val is None:
            continue
        k = clean_num(k_val)
        if k <= 0:
            continue

        all_strikes.add(k)

        # Option type (Call or Put)
        opt_type = str(raw.get("optionType") or raw.get("type") or "").strip().upper()
        if not opt_type and "symbol" in raw:
            sym = str(raw["symbol"]).strip().upper()
            if sym.endswith("P"):
                opt_type = "PUT"
            elif sym.endswith("C"):
                opt_type = "CALL"

        if opt_type.startswith("P"):
            put_map[k] = raw
        else:
            call_map[k] = raw

    if not all_strikes:
        raise ValueError("No valid strike prices found in records")

    sorted_strikes = sorted(all_strikes)
    rows: list[dict[str, Any]] = []

    for k in sorted_strikes:
        c = call_map.get(k, {})
        p = put_map.get(k, {})

        # Calls
        c_bid = clean_num(c.get("bidPrice") or c.get("bid"))
        c_ask = clean_num(c.get("askPrice") or c.get("ask"))
        c_last = clean_num(c.get("lastPrice") or c.get("last") or c.get("latest"))
        c_vol = int(clean_num(c.get("volume") or c.get("vol")))
        c_oi = int(clean_num(c.get("openInterest") or c.get("oi")))
        c_gamma = clean_num(c.get("gamma"), default=0.0005)
        c_iv = clean_num(c.get("volatility") or c.get("iv"))
        if c_iv > 1.0:
            c_iv = c_iv / 100.0
        c_mid = (c_bid + c_ask) / 2.0 if (c_bid > 0 and c_ask > 0) else c_last

        # Puts
        p_bid = clean_num(p.get("bidPrice") or p.get("bid"))
        p_ask = clean_num(p.get("askPrice") or p.get("ask"))
        p_last = clean_num(p.get("lastPrice") or p.get("last") or p.get("latest"))
        p_vol = int(clean_num(p.get("volume") or p.get("vol")))
        p_oi = int(clean_num(p.get("openInterest") or p.get("oi")))
        p_gamma = clean_num(p.get("gamma"), default=0.0005)
        p_iv = clean_num(p.get("volatility") or p.get("iv"))
        if p_iv > 1.0:
            p_iv = p_iv / 100.0
        p_mid = (p_bid + p_ask) / 2.0 if (p_bid > 0 and p_ask > 0) else p_last

        rows.append({
            "strike": k,
            "callBid": c_bid,
            "callAsk": c_ask,
            "callMid": round(c_mid, 2),
            "callLatest": c_last,
            "callVolume": c_vol,
            "callOpenInterest": c_oi,
            "callGamma": c_gamma,
            "callIV": round(c_iv, 4),
            "putBid": p_bid,
            "putAsk": p_ask,
            "putMid": round(p_mid, 2),
            "putLatest": p_last,
            "putVolume": p_vol,
            "putOpenInterest": p_oi,
            "putGamma": p_gamma,
            "putIV": round(p_iv, 4),
        })

    df = pd.DataFrame(rows)
    logger.info("Successfully parsed %d strikes from Barchart JSON", len(df))
    return df
