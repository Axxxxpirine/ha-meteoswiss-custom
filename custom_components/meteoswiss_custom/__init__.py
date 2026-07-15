"""The MeteoSwiss Custom integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import MeteoSwissClient
from .const import (
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_POINT_ID,
    CONF_POINT_NAME,
    CONF_POINT_TYPE_ID,
    CONF_STATION_ABBR,
    CONF_STATION_NAME,
    PLATFORMS,
)
from .coordinator import (
    MeteoSwissDataUpdateCoordinator,
    MeteoSwissObservationDataUpdateCoordinator,
)
from .models import ForecastPoint, Station


@dataclass(slots=True)
class MeteoSwissRuntimeData:
    """Runtime data for a config entry."""

    client: MeteoSwissClient
    forecast_coordinator: MeteoSwissDataUpdateCoordinator
    observation_coordinator: MeteoSwissObservationDataUpdateCoordinator
    point: ForecastPoint
    station: Station


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MeteoSwiss Custom from a config entry."""
    session = async_get_clientsession(hass)
    client = MeteoSwissClient(session)

    point_id = entry.data.get(CONF_POINT_ID)
    point_type_id = entry.data.get(CONF_POINT_TYPE_ID)
    station_abbr = entry.data.get(CONF_STATION_ABBR)
    latitude = entry.data.get(CONF_LATITUDE, hass.config.latitude)
    longitude = entry.data.get(CONF_LONGITUDE, hass.config.longitude)

    point, station = await client.async_resolve_location(
        latitude=latitude,
        longitude=longitude,
        point_id=point_id,
        point_type_id=point_type_id,
        station_abbr=station_abbr,
    )
    forecast_coordinator = MeteoSwissDataUpdateCoordinator(hass, client, point, station)
    observation_coordinator = MeteoSwissObservationDataUpdateCoordinator(
        hass, client, point, station
    )
    await forecast_coordinator.async_config_entry_first_refresh()
    # Observation failures must not prevent the integration from loading. The
    # independent coordinator will retry every ten minutes.
    await observation_coordinator.async_refresh()

    entry.runtime_data = MeteoSwissRuntimeData(
        client=client,
        forecast_coordinator=forecast_coordinator,
        observation_coordinator=observation_coordinator,
        point=point,
        station=station,
    )

    updates: dict[str, object] = {}
    if entry.data.get(CONF_POINT_NAME) != point.name:
        updates[CONF_POINT_NAME] = point.name
    if entry.data.get(CONF_STATION_NAME) != station.name:
        updates[CONF_STATION_NAME] = station.name
    if updates:
        hass.config_entries.async_update_entry(entry, data={**entry.data, **updates})

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a MeteoSwiss config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old config entries."""
    if entry.version == 1:
        return True
    return False
