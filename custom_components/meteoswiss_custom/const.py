"""Constants for the MeteoSwiss custom integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "meteoswiss_custom"
NAME: Final = "MeteoSwiss Custom"
ATTRIBUTION: Final = "Source: MeteoSwiss"

PLATFORMS: Final = [Platform.WEATHER, Platform.SENSOR]

CONF_USE_HOME_LOCATION: Final = "use_home_location"
CONF_POINT_ID: Final = "point_id"
CONF_POINT_TYPE_ID: Final = "point_type_id"
CONF_POINT_NAME: Final = "point_name"
CONF_STATION_ABBR: Final = "station_abbr"
CONF_STATION_NAME: Final = "station_name"
CONF_LATITUDE: Final = "latitude"
CONF_LONGITUDE: Final = "longitude"

DEFAULT_UPDATE_INTERVAL: Final = timedelta(minutes=20)
METADATA_UPDATE_INTERVAL: Final = timedelta(hours=24)

STAC_API_BASE: Final = "https://data.geo.admin.ch/api/stac/v1"
LOCAL_FORECAST_COLLECTION: Final = "ch.meteoschweiz.ogd-local-forecasting"
SMN_COLLECTION: Final = "ch.meteoschweiz.ogd-smn"

LOCAL_FORECAST_ASSET_BASE: Final = (
    "https://data.geo.admin.ch/ch.meteoschweiz.ogd-local-forecasting"
)
SMN_ASSET_BASE: Final = "https://data.geo.admin.ch/ch.meteoschweiz.ogd-smn"

LOCAL_POINT_META_URL: Final = (
    f"{LOCAL_FORECAST_ASSET_BASE}/ogd-local-forecasting_meta_point.csv"
)
SMN_STATION_META_URL: Final = f"{SMN_ASSET_BASE}/ogd-smn_meta_stations.csv"

HOURLY_FORECAST_PARAMETERS: Final = (
    "tre200h0",  # temperature
    "rre150h0",  # hourly precipitation
    "rp0003i0",  # 3h precipitation probability
    "fu3010h0",  # wind speed
    "fu3010h1",  # gust
    "dkl010h0",  # wind bearing
    "jww003i0",  # weather type
)

DAILY_FORECAST_PARAMETERS: Final = (
    "tre200pn",  # daily min, local time
    "tre200px",  # daily max, local time
    "rka150p0",  # daily precipitation, local time
    "jp2000d0",  # daily pictogram
)

ESSENTIAL_OBSERVATION_PARAMETERS: Final = (
    "tre200s0",
    "ure200s0",
    "tde200s0",
    "rre150z0",
    "fu3010z0",
    "fu3010z1",
    "dkl010z0",
    "prestas0",
    "pp0qnhs0",
    "gre000z0",
    "sre000z0",
)

