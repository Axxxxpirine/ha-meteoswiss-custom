"""Diagnostics support for MeteoSwiss Custom."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import MeteoSwissRuntimeData
from .const import ATTRIBUTION, OBSERVATION_STALE_AFTER


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    runtime_data: MeteoSwissRuntimeData | None = getattr(entry, "runtime_data", None)
    data: dict[str, Any] = {
        "attribution": ATTRIBUTION,
        "entry": {
            "title": entry.title,
            "data": dict(entry.data),
            "options": dict(entry.options),
        },
    }
    if runtime_data is not None:
        forecast_data = runtime_data.forecast_coordinator.data
        observation = runtime_data.observation_coordinator.data
        data["resolved"] = {
            "forecast_point": {
                "point_id": runtime_data.point.point_id,
                "point_type_id": runtime_data.point.point_type_id,
                "name": runtime_data.point.name,
                "latitude": runtime_data.point.latitude,
                "longitude": runtime_data.point.longitude,
            },
            "station": {
                "abbr": runtime_data.station.abbr,
                "name": runtime_data.station.name,
                "latitude": runtime_data.station.latitude,
                "longitude": runtime_data.station.longitude,
            },
        }
        data["last_update"] = {
            "forecast_success": runtime_data.forecast_coordinator.last_update_success,
            "forecast_updated_at": forecast_data.updated_at.isoformat()
            if forecast_data and forecast_data.updated_at
            else None,
            "hourly_forecasts": len(forecast_data.hourly) if forecast_data else 0,
            "daily_forecasts": len(forecast_data.daily) if forecast_data else 0,
            "observation_success": (
                runtime_data.observation_coordinator.last_update_success
            ),
            "observation_timestamp": observation.timestamp.isoformat()
            if observation and observation.timestamp
            else None,
            "observation_age_minutes": _age_minutes(
                observation.timestamp if observation else None
            ),
            "observation_stale": _is_stale(
                observation.timestamp if observation else None
            ),
        }
    return data


def _age_minutes(timestamp: datetime | None) -> float | None:
    """Return a non-negative timestamp age in minutes."""
    if timestamp is None:
        return None
    return round(max(0.0, (datetime.now(UTC) - timestamp).total_seconds()) / 60, 1)


def _is_stale(timestamp: datetime | None) -> bool | None:
    """Return whether an observation is older than the grace threshold."""
    if timestamp is None:
        return None
    return datetime.now(UTC) - timestamp > OBSERVATION_STALE_AFTER
