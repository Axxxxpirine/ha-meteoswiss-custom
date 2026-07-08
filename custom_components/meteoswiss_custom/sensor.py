"""Sensor platform for MeteoSwiss Custom."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    DEGREE,
    PERCENTAGE,
    UnitOfIrradiance,
    UnitOfLength,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MeteoSwissRuntimeData
from .const import DOMAIN
from .coordinator import MeteoSwissDataUpdateCoordinator
from .entity import MeteoSwissEntity


@dataclass(frozen=True, kw_only=True)
class MeteoSwissSensorEntityDescription(SensorEntityDescription):
    """Describe a MeteoSwiss sensor."""

    parameter: str


SENSORS: tuple[MeteoSwissSensorEntityDescription, ...] = (
    MeteoSwissSensorEntityDescription(
        key="temperature",
        translation_key="temperature",
        parameter="tre200s0",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    MeteoSwissSensorEntityDescription(
        key="humidity",
        translation_key="humidity",
        parameter="ure200s0",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    MeteoSwissSensorEntityDescription(
        key="dew_point",
        translation_key="dew_point",
        parameter="tde200s0",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    MeteoSwissSensorEntityDescription(
        key="precipitation_10_min",
        translation_key="precipitation_10_min",
        parameter="rre150z0",
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    MeteoSwissSensorEntityDescription(
        key="wind_speed",
        translation_key="wind_speed",
        parameter="fu3010z0",
        device_class=SensorDeviceClass.WIND_SPEED,
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    MeteoSwissSensorEntityDescription(
        key="wind_gust",
        translation_key="wind_gust",
        parameter="fu3010z1",
        device_class=SensorDeviceClass.WIND_SPEED,
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    MeteoSwissSensorEntityDescription(
        key="wind_bearing",
        translation_key="wind_bearing",
        parameter="dkl010z0",
        native_unit_of_measurement=DEGREE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    MeteoSwissSensorEntityDescription(
        key="pressure_qfe",
        translation_key="pressure_qfe",
        parameter="prestas0",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.HPA,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    MeteoSwissSensorEntityDescription(
        key="pressure_qnh",
        translation_key="pressure_qnh",
        parameter="pp0qnhs0",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.HPA,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    MeteoSwissSensorEntityDescription(
        key="global_radiation",
        translation_key="global_radiation",
        parameter="gre000z0",
        device_class=SensorDeviceClass.IRRADIANCE,
        native_unit_of_measurement=UnitOfIrradiance.WATTS_PER_SQUARE_METER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    MeteoSwissSensorEntityDescription(
        key="sunshine_duration",
        translation_key="sunshine_duration",
        parameter="sre000z0",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MeteoSwiss sensors."""
    runtime_data: MeteoSwissRuntimeData = entry.runtime_data
    async_add_entities(
        MeteoSwissSensor(runtime_data.coordinator, description) for description in SENSORS
    )


class MeteoSwissSensor(MeteoSwissEntity, SensorEntity):
    """A MeteoSwiss observation sensor."""

    entity_description: MeteoSwissSensorEntityDescription

    def __init__(
        self,
        coordinator: MeteoSwissDataUpdateCoordinator,
        description: MeteoSwissSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = (
            f"{DOMAIN}_{coordinator.station.abbr.lower()}_{description.key}"
        )

    @property
    def native_value(self) -> Any:
        """Return the native value."""
        observation = self.coordinator.data.observation
        if observation is None:
            return None
        return observation.values.get(self.entity_description.parameter)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        observation = self.coordinator.data.observation
        return (
            super().available
            and observation is not None
            and observation.values.get(self.entity_description.parameter) is not None
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        observation = self.coordinator.data.observation
        return {
            "station": self.coordinator.station.abbr,
            "station_name": self.coordinator.station.name,
            "reference_timestamp": observation.timestamp.isoformat()
            if observation and observation.timestamp
            else None,
        }

