"""Data update coordinator for MeteoSwiss Custom."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import MeteoSwissClient, MeteoSwissClientError
from .const import DEFAULT_UPDATE_INTERVAL, DOMAIN, OBSERVATION_UPDATE_INTERVAL
from .models import ForecastPoint, MeteoSwissData, Observation, Station

_LOGGER = logging.getLogger(__name__)


class MeteoSwissDataUpdateCoordinator(DataUpdateCoordinator[MeteoSwissData]):
    """Coordinate MeteoSwiss API polling."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: MeteoSwissClient,
        point: ForecastPoint,
        station: Station,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_UPDATE_INTERVAL,
        )
        self.client = client
        self.point = point
        self.station = station

    async def _async_update_data(self) -> MeteoSwissData:
        """Fetch latest forecast data."""
        try:
            return await self.client.async_get_forecast_data(self.point, self.station)
        except MeteoSwissClientError as err:
            raise UpdateFailed(str(err)) from err


class MeteoSwissObservationDataUpdateCoordinator(DataUpdateCoordinator[Observation]):
    """Update SwissMetNet observations independently from forecasts."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: MeteoSwissClient,
        point: ForecastPoint,
        station: Station,
    ) -> None:
        """Initialize the observation coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_observations",
            update_interval=OBSERVATION_UPDATE_INTERVAL,
        )
        self.client = client
        self.point = point
        self.station = station

    async def _async_update_data(self) -> Observation:
        """Fetch the latest observation without affecting forecasts."""
        observation = await self.client.async_get_observation(self.station)
        if observation is None:
            raise UpdateFailed(
                f"No observation data available for station {self.station.abbr}"
            )
        return observation
