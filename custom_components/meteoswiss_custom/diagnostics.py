"""Diagnostics support for MeteoSwiss Custom."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import MeteoSwissRuntimeData
from .const import ATTRIBUTION


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
        coordinator_data = runtime_data.coordinator.data
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
            "success": runtime_data.coordinator.last_update_success,
            "updated_at": coordinator_data.updated_at.isoformat()
            if coordinator_data and coordinator_data.updated_at
            else None,
            "hourly_forecasts": len(coordinator_data.hourly) if coordinator_data else 0,
            "daily_forecasts": len(coordinator_data.daily) if coordinator_data else 0,
            "has_observation": bool(coordinator_data and coordinator_data.observation),
        }
    return data

