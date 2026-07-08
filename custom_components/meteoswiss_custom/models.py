"""Typed models used by the MeteoSwiss custom integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ForecastPoint:
    """A MeteoSwiss local forecast point."""

    point_id: int
    point_type_id: int
    name: str
    latitude: float
    longitude: float
    altitude: float | None = None
    station_abbr: str | None = None
    postal_code: str | None = None

    @property
    def key(self) -> tuple[int, int]:
        """Return the unique point key."""
        return (self.point_id, self.point_type_id)


@dataclass(frozen=True, slots=True)
class Station:
    """A MeteoSwiss SwissMetNet station."""

    abbr: str
    name: str
    latitude: float
    longitude: float
    altitude: float | None = None
    canton: str | None = None


@dataclass(frozen=True, slots=True)
class Observation:
    """Current observation values from a SwissMetNet station."""

    station: Station
    timestamp: datetime | None
    values: dict[str, float | int | str | None]


@dataclass(frozen=True, slots=True)
class ForecastPeriod:
    """Forecast values for one timestamp."""

    datetime: datetime
    values: dict[str, float | int | str | None]


@dataclass(slots=True)
class MeteoSwissData:
    """Complete data payload exposed to Home Assistant."""

    point: ForecastPoint
    station: Station
    observation: Observation | None = None
    hourly: list[ForecastPeriod] = field(default_factory=list)
    daily: list[ForecastPeriod] = field(default_factory=list)
    updated_at: datetime | None = None

