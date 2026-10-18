"""Tier 3: Dealer Positioning - Walls, Pin Risk, Gamma Triggers."""
from __future__ import annotations

from .models import OptionsSnapshot, Wall


def find_walls(
    snapshot: OptionsSnapshot,
    top_n: int = 2,
) -> tuple[list[Wall], list[Wall]]:
    """Find top-N Call Walls and Put Walls by OI.

    Returns:
        (call_walls, put_walls) sorted by OI descending.
    """
    if not snapshot.strikes:
        return [], []

    call_sorted = sorted(snapshot.strikes, key=lambda s: s.call_oi, reverse=True)
    put_sorted = sorted(snapshot.strikes, key=lambda s: s.put_oi, reverse=True)

    call_walls = [
        Wall(
            strike=s.strike,
            oi=s.call_oi,
            volume=s.call_volume,
            side="call",
            rank=i + 1,
        )
        for i, s in enumerate(call_sorted[:top_n])
    ]

    put_walls = [
        Wall(
            strike=s.strike,
            oi=s.put_oi,
            volume=s.put_volume,
            side="put",
            rank=i + 1,
        )
        for i, s in enumerate(put_sorted[:top_n])
    ]

    return call_walls, put_walls


def gamma_squeeze_trigger(call_wall: Wall, call_mid_at_wall: float) -> float:
    """Short Gamma breakeven for upside squeeze.

    Trigger_Up = Strike_CallWall + Call_mid(CallWall)
    """
    return call_wall.strike + call_mid_at_wall


def gamma_waterfall_trigger(put_wall: Wall, put_mid_at_wall: float) -> float:
    """Short Gamma breakeven for downside waterfall.

    Trigger_Down = Strike_PutWall - Put_mid(PutWall)
    """
    return put_wall.strike - put_mid_at_wall


def detect_pin_risk(snapshot: OptionsSnapshot) -> float | None:
    """Detect pin risk: strike where both Call_OI and Put_OI are in top 2.

    Returns the pinning strike, or None if no pin risk detected.
    """
    if len(snapshot.strikes) < 2:
        return None

    call_top2 = {
        s.strike
        for s in sorted(snapshot.strikes, key=lambda s: s.call_oi, reverse=True)[:2]
    }
    put_top2 = {
        s.strike
        for s in sorted(snapshot.strikes, key=lambda s: s.put_oi, reverse=True)[:2]
    }

    overlap = call_top2 & put_top2
    if not overlap:
        return None

    # Return the strike with highest combined OI
    return max(
        overlap,
        key=lambda k: next(
            s.call_oi + s.put_oi for s in snapshot.strikes if s.strike == k
        ),
    )
