"""Neiro-Quant Level State Engine & Air Pocket Detector (Tầng 4).

Implements the finite state machine for options levels and market microstructure
as specified in docs/architecture.md (Mục V - Level State Engine):
- State Machine: DORMANT -> TESTING -> ABSORPTION_DEFENDED / SLICED_VACUUM_RUN
- Air Pocket Detection: Identifies low-liquidity zones between strikes
- Major Wall Finder: Finds the true structural defense cluster (not just arbitrary $5 step)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal
import numpy as np
import pandas as pd


class LevelState(str, Enum):
    DORMANT = "DORMANT"
    TESTING = "TESTING"
    ABSORPTION_DEFENDED = "ABSORPTION_DEFENDED"
    SLICED_VACUUM_RUN = "SLICED_VACUUM_RUN"
    WALL_DEFENDED = "WALL_DEFENDED"


@dataclass(frozen=True, slots=True)
class AirPocketZone:
    """Represents a low-liquidity air pocket between two structural walls."""
    start_strike: float
    end_strike: float
    gap_size: float
    avg_oi: float
    avg_volume: float
    direction: Literal["DOWN", "UP"]


@dataclass(frozen=True, slots=True)
class LevelEvaluation:
    """Evaluated state and tactical directive for a specific level."""
    level_name: str
    strike: float
    state: LevelState
    distance_pts: float
    net_gex_at_strike: float
    is_air_pocket_adjacent: bool
    vacuum_target: float | None = None
    recommended_action: str = ""
    entry_trigger: str = ""
    hard_sl: float = 0.0
    take_profit: float = 0.0
    notes: str = ""


def find_next_major_wall(
    df: pd.DataFrame,
    current_strike: float,
    direction: Literal["DOWN", "UP"] = "DOWN",
    oi_percentile: float = 65.0,
    min_distance: float = 10.0,
) -> tuple[float, int]:
    """Finds the next substantial defense strike with high Open Interest / Volume.

    Args:
        df: DataFrame with 'strike', 'callOpenInterest', 'putOpenInterest', 'callVolume', 'putVolume'.
        current_strike: Starting strike to search away from.
        direction: 'DOWN' to search below current_strike, 'UP' to search above.
        oi_percentile: Minimum percentile of local active zone OI to qualify as a major wall.
        min_distance: Minimum price distance required (prevents picking adjacent 1-step strike).

    Returns:
        tuple (target_strike, total_oi_at_strike)
    """
    if df.empty or "strike" not in df.columns:
        fallback = current_strike - 15.0 if direction == "DOWN" else current_strike + 15.0
        return fallback, 0

    work_df = df.copy()
    if "total_oi" not in work_df.columns:
        work_df["total_oi"] = work_df["callOpenInterest"].fillna(0) + work_df["putOpenInterest"].fillna(0)

    # Local active trading zone (+/- 60 pts around current strike)
    local_active = work_df[abs(work_df["strike"] - current_strike) <= 60.0]
    if len(local_active) < 3:
        local_active = work_df

    # Relevant side OI
    side_oi_col = "putOpenInterest" if direction == "DOWN" else "callOpenInterest"
    if side_oi_col not in work_df.columns:
        side_oi_col = "total_oi"

    if direction == "DOWN":
        candidates = local_active[local_active["strike"] < current_strike].sort_values("strike", ascending=False)
    else:
        candidates = local_active[local_active["strike"] > current_strike].sort_values("strike", ascending=True)

    if candidates.empty:
        # Search outside local zone if empty
        if direction == "DOWN":
            candidates = work_df[work_df["strike"] < current_strike].sort_values("strike", ascending=False)
        else:
            candidates = work_df[work_df["strike"] > current_strike].sort_values("strike", ascending=True)

    if candidates.empty:
        fallback = current_strike - 15.0 if direction == "DOWN" else current_strike + 15.0
        return fallback, 0

    local_threshold = float(local_active[side_oi_col].quantile(oi_percentile / 100.0))

    # Pick candidate that exceeds threshold and respects min_distance or is a clear local peak
    for i in range(len(candidates)):
        row = candidates.iloc[i]
        s = float(row["strike"])
        oi = float(row[side_oi_col])
        dist = abs(s - current_strike)

        # Qualifying condition: meets local threshold and has sufficient distance or higher than immediate neighbor
        first_neighbor_oi = float(candidates.iloc[0][side_oi_col])
        if oi >= local_threshold and (dist >= min_distance or oi > first_neighbor_oi * 1.25):
            return s, int(row["total_oi"])

    # Fallback to candidate with maximum side OI
    best = candidates.sort_values(side_oi_col, ascending=False).iloc[0]
    return float(best["strike"]), int(best["total_oi"])


def detect_strike_air_pockets(
    df: pd.DataFrame,
    start_strike: float,
    end_strike: float,
    threshold_ratio: float = 0.40,
) -> list[AirPocketZone]:
    """Detects air pocket zones between start_strike and end_strike where total OI < threshold_ratio * mean_oi."""
    if df.empty or "strike" not in df.columns:
        return []

    lo, hi = min(start_strike, end_strike), max(start_strike, end_strike)
    direction: Literal["DOWN", "UP"] = "DOWN" if start_strike > end_strike else "UP"

    sub = df[(df["strike"] >= lo) & (df["strike"] <= hi)].sort_values("strike")
    if len(sub) < 2:
        return []

    total_oi = (sub["callOpenInterest"].fillna(0) + sub["putOpenInterest"].fillna(0)).values
    total_vol = (sub["callVolume"].fillna(0) + sub["putVolume"].fillna(0)).values
    strikes = sub["strike"].values

    mean_oi = float(np.mean(total_oi)) if len(total_oi) > 0 else 0.0
    if mean_oi <= 0:
        return []

    threshold = mean_oi * threshold_ratio
    pockets: list[AirPocketZone] = []

    in_pocket = False
    p_start = 0.0
    pocket_ois = []
    pocket_vols = []

    for s, oi, vol in zip(strikes, total_oi, total_vol):
        if oi < threshold:
            if not in_pocket:
                in_pocket = True
                p_start = s
            pocket_ois.append(oi)
            pocket_vols.append(vol)
        else:
            if in_pocket:
                in_pocket = False
                pockets.append(AirPocketZone(
                    start_strike=p_start,
                    end_strike=s,
                    gap_size=abs(s - p_start),
                    avg_oi=float(np.mean(pocket_ois)),
                    avg_volume=float(np.mean(pocket_vols)),
                    direction=direction,
                ))
                pocket_ois = []
                pocket_vols = []

    if in_pocket and len(pocket_ois) > 0:
        pockets.append(AirPocketZone(
            start_strike=p_start,
            end_strike=strikes[-1],
            gap_size=abs(strikes[-1] - p_start),
            avg_oi=float(np.mean(pocket_ois)),
            avg_volume=float(np.mean(pocket_vols)),
            direction=direction,
        ))

    return pockets


def evaluate_tactical_level_states(
    spot_price: float,
    df: pd.DataFrame,
    meta: dict[str, Any],
    slice_buffer: float = 1.5,
    testing_range: float = 2.0,
    dormant_distance: float = 5.0,
) -> list[LevelEvaluation]:
    """Applies the Level State Machine to all primary tactical levels.

    Levels evaluated:
    1. Call Wall (Đỉnh kiên cố)
    2. Strike Above ATM (Tiền tuyến kháng cự)
    3. ATM Pivot (Trục cân bằng ngầm định)
    4. Strike Below ATM (Tiền tuyến hỗ trợ)
    5. Put Wall (Đáy bê tông cốt thép)
    """
    evaluations: list[LevelEvaluation] = []

    atm_pivot = float(meta.get("atm_strike", spot_price))
    call_wall = float(meta.get("call_wall", atm_pivot + 20.0))
    put_wall = float(meta.get("put_wall", atm_pivot - 20.0))
    total_gex = float(meta.get("total_net_gex", 0.0))
    is_short_gamma = total_gex < 0

    strikes = df["strike"].values if "strike" in df.columns else np.array([atm_pivot])
    step = float(np.diff(strikes).min()) if len(strikes) > 1 else 5.0

    strikes_above = strikes[strikes > spot_price]
    strike_above = float(strikes_above[0]) if len(strikes_above) > 0 else call_wall

    strikes_below = strikes[strikes <= spot_price]
    strike_below = float(strikes_below[-1]) if len(strikes_below) > 0 else put_wall

    atm_support = atm_pivot - step
    atm_resistance = atm_pivot + step

    key_levels = [
        ("Call Wall", call_wall, "RESISTANCE"),
        ("ATM Kháng Cự (+1 Nấc)", atm_resistance, "RESISTANCE"),
        ("ATM Pivot", atm_pivot, "PIVOT"),
        ("ATM Hỗ Trợ (-1 Nấc)", atm_support, "SUPPORT"),
        ("Cản Gần Nhất (Immediate Resistance)", strike_above, "RESISTANCE"),
        ("Đệm Gần Nhất (Immediate Support)", strike_below, "SUPPORT"),
        ("Major Put Wall", put_wall, "SUPPORT"),
    ]

    # Remove duplicates preserving order
    seen_strikes = set()
    unique_levels = []
    for name, lvl, role in key_levels:
        if lvl not in seen_strikes:
            seen_strikes.add(lvl)
            unique_levels.append((name, lvl, role))

    for name, lvl, role in unique_levels:
        dist = spot_price - lvl
        abs_dist = abs(dist)

        # Retrieve net GEX at this strike if available
        strike_row = df[df["strike"] == lvl] if "strike" in df.columns else pd.DataFrame()
        gex_at_strike = float(strike_row["netGEX"].iloc[0]) if not strike_row.empty and "netGEX" in strike_row.columns else 0.0

        if role == "SUPPORT":
            if dist < -slice_buffer:
                # Sliced through downwards
                target, _ = find_next_major_wall(df, lvl, direction="DOWN", oi_percentile=60.0)
                evaluations.append(LevelEvaluation(
                    level_name=name,
                    strike=lvl,
                    state=LevelState.SLICED_VACUUM_RUN,
                    distance_pts=dist,
                    net_gex_at_strike=gex_at_strike,
                    is_air_pocket_adjacent=True,
                    vacuum_target=target,
                    recommended_action="SELL_BREAKOUT_RUNNER",
                    entry_trigger=f"Đã thủng dứt khoát < {lvl - slice_buffer:.2f}",
                    hard_sl=lvl + 1.50,
                    take_profit=target + 1.00,
                    notes=f"🚨 SLICED_VACUUM_RUN: Thủng {lvl:.0f} trong -GEX -> CẤM BẮT ĐÁY! Trượt tự do về Major Wall {target:.0f}.",
                ))
            elif abs_dist <= testing_range:
                # Testing support
                evaluations.append(LevelEvaluation(
                    level_name=name,
                    strike=lvl,
                    state=LevelState.TESTING,
                    distance_pts=dist,
                    net_gex_at_strike=gex_at_strike,
                    is_air_pocket_adjacent=False,
                    vacuum_target=None,
                    recommended_action="WATCH_ABSORPTION_OR_SLICING",
                    entry_trigger=f"Biên {lvl:.2f} - {lvl + 1.50:.2f}",
                    hard_sl=lvl - 2.50,
                    take_profit=atm_pivot,
                    notes=f"Áp sát hỗ trợ {lvl:.0f}. Ưu tiên MUA REBOUND vùng {lvl:.1f}-{lvl+1.5:.1f} (SL: {lvl-2.5:.1f}). Nếu thủng > {lvl-slice_buffer:.1f} -> CẮT LỖ, đánh SELL BREAKOUT.",
                ))
            elif dist > dormant_distance:
                evaluations.append(LevelEvaluation(
                    level_name=name,
                    strike=lvl,
                    state=LevelState.DORMANT,
                    distance_pts=dist,
                    net_gex_at_strike=gex_at_strike,
                    is_air_pocket_adjacent=False,
                    recommended_action="NONE",
                    notes="Chốt chặn ở xa, duy trì theo dõi trên bản đồ thanh khoản.",
                ))
            else:
                evaluations.append(LevelEvaluation(
                    level_name=name,
                    strike=lvl,
                    state=LevelState.WALL_DEFENDED,
                    distance_pts=dist,
                    net_gex_at_strike=gex_at_strike,
                    is_air_pocket_adjacent=False,
                    recommended_action="HOLD_DEFENSE",
                    notes="Chốt chặn đang giữ nhịp phía dưới giá hiện tại.",
                ))

        elif role == "RESISTANCE":
            if dist > slice_buffer:
                # Sliced through upwards (Squeeze)
                target, _ = find_next_major_wall(df, lvl, direction="UP", oi_percentile=60.0)
                evaluations.append(LevelEvaluation(
                    level_name=name,
                    strike=lvl,
                    state=LevelState.SLICED_VACUUM_RUN,
                    distance_pts=dist,
                    net_gex_at_strike=gex_at_strike,
                    is_air_pocket_adjacent=True,
                    vacuum_target=target,
                    recommended_action="BUY_BREAKOUT_RUNNER",
                    entry_trigger=f"Đã phá trần > {lvl + slice_buffer:.2f}",
                    hard_sl=lvl - 1.50,
                    take_profit=target - 1.00,
                    notes=f"⚡ GAMMA SQUEEZE RUNNER: Phá trần {lvl:.0f} -> CẤM CHẶN ĐẦU! Hút giá lên Major Wall {target:.0f}.",
                ))
            elif abs_dist <= testing_range:
                # Testing resistance
                evaluations.append(LevelEvaluation(
                    level_name=name,
                    strike=lvl,
                    state=LevelState.TESTING,
                    distance_pts=dist,
                    net_gex_at_strike=gex_at_strike,
                    is_air_pocket_adjacent=False,
                    recommended_action="WATCH_ABSORPTION_OR_BREAKOUT",
                    entry_trigger=f"Biên {lvl - 1.50:.2f} - {lvl:.2f}",
                    hard_sl=lvl + 2.50,
                    take_profit=atm_pivot,
                    notes=f"Áp sát cản trần {lvl:.0f}. Ưu tiên SHORT FADE vùng {lvl-1.5:.1f}-{lvl:.1f} (SL: {lvl+2.5:.1f}). Nếu phá trần > {lvl+slice_buffer:.1f} -> HỦY SHORT, đánh BUY SQUEEZE.",
                ))
            elif abs_dist > dormant_distance:
                evaluations.append(LevelEvaluation(
                    level_name=name,
                    strike=lvl,
                    state=LevelState.DORMANT,
                    distance_pts=dist,
                    net_gex_at_strike=gex_at_strike,
                    is_air_pocket_adjacent=False,
                    recommended_action="NONE",
                    notes="Cản ở xa, định hướng biên trên.",
                ))
            else:
                evaluations.append(LevelEvaluation(
                    level_name=name,
                    strike=lvl,
                    state=LevelState.WALL_DEFENDED,
                    distance_pts=dist,
                    net_gex_at_strike=gex_at_strike,
                    is_air_pocket_adjacent=False,
                    recommended_action="HOLD_CEILING",
                    notes="Cản trần đang ghìm giá phía trên.",
                ))

        else:  # PIVOT
            if abs_dist <= testing_range:
                evaluations.append(LevelEvaluation(
                    level_name=name,
                    strike=lvl,
                    state=LevelState.TESTING,
                    distance_pts=dist,
                    net_gex_at_strike=gex_at_strike,
                    is_air_pocket_adjacent=False,
                    recommended_action="PIVOT_EQUILIBRIUM",
                    notes="Giá đang dao động quanh trục ATM Pivot cân bằng ngầm định.",
                ))
            elif dist < -slice_buffer:
                evaluations.append(LevelEvaluation(
                    level_name=name,
                    strike=lvl,
                    state=LevelState.SLICED_VACUUM_RUN if is_short_gamma else LevelState.WALL_DEFENDED,
                    distance_pts=dist,
                    net_gex_at_strike=gex_at_strike,
                    is_air_pocket_adjacent=is_short_gamma,
                    recommended_action="SELL_PRESSURE",
                    notes=f"Giá rơi sâu dưới ATM Pivot {lvl:.0f} ({dist:+.1f} pts) -> Trục này trở thành Kháng cự đè nặng.",
                ))
            else:
                evaluations.append(LevelEvaluation(
                    level_name=name,
                    strike=lvl,
                    state=LevelState.WALL_DEFENDED,
                    distance_pts=dist,
                    net_gex_at_strike=gex_at_strike,
                    is_air_pocket_adjacent=False,
                    recommended_action="BUY_PRESSURE",
                    notes=f"Giá duy trì trên ATM Pivot {lvl:.0f} ({dist:+.1f} pts) -> Trục này đóng vai trò Bệ đỡ.",
                ))

    return evaluations
