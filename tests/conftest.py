"""Minimal Home Assistant stubs for unit tests that target pure client logic."""

from __future__ import annotations

import sys
from enum import StrEnum
from types import ModuleType


class _Platform(StrEnum):
    WEATHER = "weather"
    SENSOR = "sensor"


class _ConfigEntry:
    pass


class _HomeAssistant:
    pass


class _DataUpdateCoordinator:
    def __class_getitem__(cls, item):  # noqa: ANN001
        return cls


class _UpdateFailed(Exception):
    pass


def _module(name: str) -> ModuleType:
    module = ModuleType(name)
    sys.modules[name] = module
    return module


homeassistant = _module("homeassistant")
config_entries = _module("homeassistant.config_entries")
core = _module("homeassistant.core")
const = _module("homeassistant.const")
helpers = _module("homeassistant.helpers")
aiohttp_client = _module("homeassistant.helpers.aiohttp_client")
update_coordinator = _module("homeassistant.helpers.update_coordinator")

config_entries.ConfigEntry = _ConfigEntry
core.HomeAssistant = _HomeAssistant
const.Platform = _Platform
aiohttp_client.async_get_clientsession = lambda hass: None
update_coordinator.DataUpdateCoordinator = _DataUpdateCoordinator
update_coordinator.UpdateFailed = _UpdateFailed

homeassistant.config_entries = config_entries
homeassistant.core = core
homeassistant.const = const
homeassistant.helpers = helpers
helpers.aiohttp_client = aiohttp_client
helpers.update_coordinator = update_coordinator

