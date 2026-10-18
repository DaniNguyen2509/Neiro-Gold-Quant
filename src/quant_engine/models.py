"""Core data models for Options Chain and computed levels."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class OptionsStrike:
    """Single strike row from the options chain.

    CRITICAL: Never use the Latest column from Barchart.
    Always compute mid from Bid/Ask.
    """

    strike: float
    call_bid: float
    call_ask: float
    call_oi: int
    call_volume: int
    put_bid: float
    put_ask: float
    put_oi: int
    put_volume: int

    @property
    def call_mid(self) -> float:
        return (self.call_bid + self.call_ask) / 2.0

    @property
    def put_mid(self) -> float:
        return (self.put_bid + self.put_ask) / 2.0


@dataclass(frozen=True, slots=True)
class OptionsSnapshot:
    """Complete options chain snapshot at a point in time."""

    symbol: str
    expiry: str
    timestamp: str
    strikes: tuple[OptionsStrike, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class Wall:
    """A structural wall (support/resistance from OI concentration)."""

    strike: float
    oi: int
    volume: int
    side: str  # "call" or "put"
    rank: int  # 1 = primary wall


@dataclass(frozen=True, slots=True)
class AirPocket:
    """Zone with thin OI between ATM and a Wall."""

    low_strike: float
    high_strike: float
    avg_oi: float
    threshold_pct: float


@dataclass(frozen=True, slots=True)
class QuantLevels:
    """All computed levels from the Quant Engine."""

    synthetic_atm_pivot: float
    implied_straddle: float
    sigma_1_upper: float
    sigma_1_lower: float
    sigma_085_upper: float
    sigma_085_lower: float
    call_wall_1: Wall | None = None
    put_wall_1: Wall | None = None
    call_wall_2: Wall | None = None
    put_wall_2: Wall | None = None
    gamma_squeeze_up: float | None = None
    gamma_waterfall_down: float | None = None
    pin_risk_strike: float | None = None
    air_pockets: tuple[AirPocket, ...] = field(default_factory=tuple)
    basis: float = 0.0
