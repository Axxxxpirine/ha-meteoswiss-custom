"""Weather platform for MeteoSwiss Custom."""

from __future__ import annotations

from typing import Any

from homeassistant.components.weather import (
    Forecast,
    WeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfLength,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MeteoSwissRuntimeData
from .const import DOMAIN
from .coordinator import MeteoSwissDataUpdateCoordinator
from .entity import MeteoSwissEntity
from .models import ForecastPeriod


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MeteoSwiss weather entity."""
    runtime_data: MeteoSwissRuntimeData = entry.runtime_data
    async_add_entities([MeteoSwissWeather(runtime_data.coordinator)])


class MeteoSwissWeather(MeteoSwissEntity, WeatherEntity):
    """Weather entity backed by official MeteoSwiss data."""

    _attr_translation_key = "weather"
    _attr_supported_features = (
        WeatherEntityFeature.FORECAST_HOURLY | WeatherEntityFeature.FORECAST_DAILY
    )
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_pressure_unit = UnitOfPressure.HPA
    _attr_native_wind_speed_unit = UnitOfSpeed.KILOMETERS_PER_HOUR
    _attr_native_precipitation_unit = UnitOfLength.MILLIMETERS

    def __init__(self, coordinator: MeteoSwissDataUpdateCoordinator) -> None:
        """Initialize the weather entity."""
        super().__init__(coordinator)
        self._attr_unique_id = (
            f"{DOMAIN}_{coordinator.point.point_type_id}_{coordinator.point.point_id}_weather"
        )

    @property
    def condition(self) -> str | None:
        """Return the current condition."""
        if self.coordinator.data.hourly:
            return _condition_from_symbol(self.coordinator.data.hourly[0].values.get("jww003i0"))
        if self.coordinator.data.daily:
            return _condition_from_symbol(self.coordinator.data.daily[0].values.get("jp2000d0"))
        return None

    @property
    def native_temperature(self) -> float | None:
        """Return native temperature."""
        return _current_or_forecast(self.coordinator, "tre200s0", "tre200h0")

    @property
    def humidity(self) -> float | None:
        """Return current humidity."""
        return _observation_value(self.coordinator, "ure200s0")

    @property
    def native_dew_point(self) -> float | None:
        """Return dew point."""
        return _observation_value(self.coordinator, "tde200s0")

    @property
    def native_pressure(self) -> float | None:
        """Return current pressure."""
        return _observation_value(self.coordinator, "pp0qnhs0") or _observation_value(
            self.coordinator, "prestas0"
        )

    @property
    def native_wind_speed(self) -> float | None:
        """Return wind speed."""
        return _current_or_forecast(self.coordinator, "fu3010z0", "fu3010h0")

    @property
    def native_wind_gust_speed(self) -> float | None:
        """Return wind gust speed."""
        return _current_or_forecast(self.coordinator, "fu3010z1", "fu3010h1")

    @property
    def wind_bearing(self) -> float | None:
        """Return wind bearing."""
        return _current_or_forecast(self.coordinator, "dkl010z0", "dkl010h0")

    async def async_forecast_hourly(self) -> list[Forecast] | None:
        """Return hourly forecast."""
        return [_hourly_forecast(period) for period in self.coordinator.data.hourly]

    async def async_forecast_daily(self) -> list[Forecast] | None:
        """Return daily forecast."""
        return [_daily_forecast(period) for period in self.coordinator.data.daily]


def _hourly_forecast(period: ForecastPeriod) -> Forecast:
    """Convert a MeteoSwiss forecast period to HA hourly forecast data."""
    values = period.values
    forecast: dict[str, Any] = {
        "datetime": period.datetime.isoformat(),
        "condition": _condition_from_symbol(values.get("jww003i0")),
    }
    _set_if_present(forecast, "native_temperature", values.get("tre200h0"))
    _set_if_present(forecast, "precipitation", values.get("rre150h0"))
    _set_if_present(forecast, "precipitation_probability", values.get("rp0003i0"))
    _set_if_present(forecast, "wind_speed", values.get("fu3010h0"))
    _set_if_present(forecast, "wind_gust_speed", values.get("fu3010h1"))
    _set_if_present(forecast, "wind_bearing", values.get("dkl010h0"))
    return forecast


def _daily_forecast(period: ForecastPeriod) -> Forecast:
    """Convert a MeteoSwiss forecast period to HA daily forecast data."""
    values = period.values
    forecast: dict[str, Any] = {
        "datetime": period.datetime.date().isoformat(),
        "condition": _condition_from_symbol(values.get("jp2000d0")),
    }
    _set_if_present(forecast, "native_temperature", values.get("tre200px"))
    _set_if_present(forecast, "native_templow", values.get("tre200pn"))
    _set_if_present(forecast, "precipitation", values.get("rka150p0"))
    return forecast


def _observation_value(
    coordinator: MeteoSwissDataUpdateCoordinator, parameter: str
) -> float | None:
    """Return an observation value as float if available."""
    observation = coordinator.data.observation
    if observation is None:
        return None
    return _as_float(observation.values.get(parameter))


def _current_or_forecast(
    coordinator: MeteoSwissDataUpdateCoordinator,
    observation_parameter: str,
    forecast_parameter: str,
) -> float | None:
    """Return current observation with forecast fallback."""
    observed = _observation_value(coordinator, observation_parameter)
    if observed is not None:
        return observed
    if not coordinator.data.hourly:
        return None
    return _as_float(coordinator.data.hourly[0].values.get(forecast_parameter))


def _set_if_present(target: dict[str, Any], key: str, value: Any) -> None:
    """Set a forecast field when value is present."""
    converted = _as_float(value)
    if converted is not None:
        target[key] = converted


def _as_float(value: Any) -> float | None:
    """Return a float or None."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _condition_from_symbol(value: Any) -> str | None:
    """Map MeteoSwiss weather symbol numbers to Home Assistant conditions."""
    try:
        symbol = int(float(value))
    except (TypeError, ValueError):
        return None

    if symbol in {1, 2}:
        return "sunny"
    if symbol in {3, 4, 5}:
        return "partlycloudy"
    if symbol in {6, 7, 8}:
        return "cloudy"
    if symbol in {9, 10, 11, 12, 13, 14, 15}:
        return "rainy"
    if symbol in {16, 17, 18, 19, 20, 21}:
        return "snowy"
    if symbol in {22, 23, 24, 25, 26, 27, 28, 29}:
        return "lightning-rainy"
    if symbol in {30, 31, 32}:
        return "fog"
    return "cloudy"

