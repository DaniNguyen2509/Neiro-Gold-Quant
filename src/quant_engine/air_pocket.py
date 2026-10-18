"""Tier 3: OI Air Pocket detection."""
from __future__ import annotations

from .models import AirPocket, OptionsSnapshot


def detect_air_pockets(
    snapshot: OptionsSnapshot,
    atm_strike: float,
    wall_strike: float,
    threshold_pct: float = 0.35,
) -> list[AirPocket]:
    """Find zones between ATM and a Wall with thin OI.

    Air Pocket = contiguous strikes where OI < threshold_pct * avg_oi.

    Args:
        snapshot: Options chain data.
        atm_strike: Current ATM strike.
        wall_strike: Target wall strike.
        threshold_pct: OI threshold as fraction of average (default 0.35 = 35%).

    Returns:
        List of AirPocket zones.
    """
    lo, hi = min(atm_strike, wall_strike), max(atm_strike, wall_strike)
    zone_strikes = [s for s in snapshot.strikes if lo <= s.strike <= hi]

    if not zone_strikes:
        return []

    # Use total OI (call + put) for each strike
    oi_values = [s.call_oi + s.put_oi for s in zone_strikes]
    avg_oi = sum(oi_values) / len(oi_values) if oi_values else 0.0
    threshold = avg_oi * threshold_pct

    pockets: list[AirPocket] = []
    pocket_start: float | None = None
    pocket_ois: list[float] = []

    for strike_data, oi in zip(zone_strikes, oi_values, strict=True):
        if oi < threshold:
            if pocket_start is None:
                pocket_start = strike_data.strike
            pocket_ois.append(oi)
        else:
            if pocket_start is not None and pocket_ois:
                pockets.append(
                    AirPocket(
                        low_strike=pocket_start,
                        high_strike=zone_strikes[
                            zone_strikes.index(strike_data) - 1
                        ].strike,
                        avg_oi=sum(pocket_ois) / len(pocket_ois),
                        threshold_pct=threshold_pct,
                    )
                )
                pocket_start = None
                pocket_ois = []

    # Close trailing pocket
    if pocket_start is not None and pocket_ois:
        pockets.append(
            AirPocket(
                low_strike=pocket_start,
                high_strike=zone_strikes[-1].strike,
                avg_oi=sum(pocket_ois) / len(pocket_ois),
                threshold_pct=threshold_pct,
            )
        )

    return pockets
