"""Config flow for MeteoSwiss Custom."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import MeteoSwissClient, MeteoSwissClientError
from .const import (
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_POINT_ID,
    CONF_POINT_NAME,
    CONF_POINT_TYPE_ID,
    CONF_STATION_ABBR,
    CONF_STATION_NAME,
    CONF_USE_HOME_LOCATION,
    DOMAIN,
)


class MeteoSwissConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MeteoSwiss Custom."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            result = await self._async_validate_and_build_data(user_input)
            if isinstance(result, dict):
                unique_id = (
                    f"{result[CONF_POINT_TYPE_ID]}:{result[CONF_POINT_ID]}:"
                    f"{result[CONF_STATION_ABBR]}"
                )
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=result[CONF_POINT_NAME],
                    data=result,
                )
            errors["base"] = result

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(self.hass.config.latitude, self.hass.config.longitude),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle reconfiguration."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            result = await self._async_validate_and_build_data(user_input)
            if isinstance(result, dict):
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates=result,
                )
            errors["base"] = result

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_schema(
                entry.data.get(CONF_LATITUDE, self.hass.config.latitude),
                entry.data.get(CONF_LONGITUDE, self.hass.config.longitude),
                entry.data,
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> MeteoSwissOptionsFlow:
        """Return the options flow."""
        return MeteoSwissOptionsFlow(config_entry)

    async def _async_validate_and_build_data(
        self, user_input: Mapping[str, Any]
    ) -> dict[str, Any] | str:
        """Validate user input and return normalized entry data or an error key."""
        latitude = float(user_input.get(CONF_LATITUDE) or self.hass.config.latitude)
        longitude = float(user_input.get(CONF_LONGITUDE) or self.hass.config.longitude)
        point_id = _optional_int(user_input.get(CONF_POINT_ID))
        point_type_id = _optional_int(user_input.get(CONF_POINT_TYPE_ID))
        station_abbr = _optional_str(user_input.get(CONF_STATION_ABBR))

        if point_id is not None and point_type_id is None:
            return "point_type_required"
        if point_type_id is not None and point_id is None:
            return "point_required"

        client = MeteoSwissClient(async_get_clientsession(self.hass))
        try:
            point, station = await client.async_resolve_location(
                latitude=latitude,
                longitude=longitude,
                point_id=point_id,
                point_type_id=point_type_id,
                station_abbr=station_abbr,
            )
        except MeteoSwissClientError:
            return "cannot_connect"

        return {
            CONF_USE_HOME_LOCATION: bool(user_input.get(CONF_USE_HOME_LOCATION, True)),
            CONF_LATITUDE: latitude,
            CONF_LONGITUDE: longitude,
            CONF_POINT_ID: point.point_id,
            CONF_POINT_TYPE_ID: point.point_type_id,
            CONF_POINT_NAME: point.name,
            CONF_STATION_ABBR: station.abbr,
            CONF_STATION_NAME: station.name,
        }


class MeteoSwissOptionsFlow(config_entries.OptionsFlow):
    """Options flow for MeteoSwiss Custom."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({}),
        )


def _schema(
    default_latitude: float,
    default_longitude: float,
    defaults: Mapping[str, Any] | None = None,
) -> vol.Schema:
    """Return config flow schema."""
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_USE_HOME_LOCATION,
                default=defaults.get(CONF_USE_HOME_LOCATION, True),
            ): bool,
            vol.Required(
                CONF_LATITUDE,
                default=defaults.get(CONF_LATITUDE, default_latitude),
            ): float,
            vol.Required(
                CONF_LONGITUDE,
                default=defaults.get(CONF_LONGITUDE, default_longitude),
            ): float,
            vol.Optional(
                CONF_POINT_ID,
                default=str(defaults.get(CONF_POINT_ID, "") or ""),
            ): str,
            vol.Optional(
                CONF_POINT_TYPE_ID,
                default=str(defaults.get(CONF_POINT_TYPE_ID, "") or ""),
            ): str,
            vol.Optional(
                CONF_STATION_ABBR,
                default=defaults.get(CONF_STATION_ABBR, ""),
            ): str,
        }
    )


def _optional_int(value: Any) -> int | None:
    """Return an optional integer from form input."""
    if value in (None, ""):
        return None
    return int(value)


def _optional_str(value: Any) -> str | None:
    """Return an optional string from form input."""
    if value in (None, ""):
        return None
    return str(value).strip().upper()
