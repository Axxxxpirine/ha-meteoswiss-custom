"""Shared entity helpers for MeteoSwiss Custom."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN
from .coordinator import MeteoSwissDataUpdateCoordinator


class MeteoSwissEntity(CoordinatorEntity[MeteoSwissDataUpdateCoordinator]):
    """Base class for MeteoSwiss entities."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(self, coordinator: MeteoSwissDataUpdateCoordinator) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        point = self.coordinator.point
        return DeviceInfo(
            identifiers={(DOMAIN, f"{point.point_type_id}:{point.point_id}")},
            name=point.name,
            manufacturer="MeteoSwiss",
            model="Open Data local forecast",
            configuration_url="https://opendatadocs.meteoswiss.ch/",
            suggested_area=point.name,
        )
