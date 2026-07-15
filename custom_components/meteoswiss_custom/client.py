"""Async client for official MeteoSwiss Open Data endpoints."""

from __future__ import annotations

import asyncio
import csv
import logging
import math
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from io import StringIO
from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession

from .const import (
    DAILY_FORECAST_PARAMETERS,
    HOURLY_FORECAST_PARAMETERS,
    LOCAL_FORECAST_COLLECTION,
    LOCAL_POINT_META_URL,
    OBSERVATION_BACKFILL_MAX_AGE,
    SMN_ASSET_BASE,
    SMN_STATION_META_URL,
    STAC_API_BASE,
)
from .models import ForecastPeriod, ForecastPoint, MeteoSwissData, Observation, Station

_LOGGER = logging.getLogger(__name__)


class MeteoSwissClientError(Exception):
    """Base exception for MeteoSwiss client failures."""


@dataclass(slots=True)
class _CachedResponse:
    payload: Any
    etag: str | None
    last_modified: str | None


class MeteoSwissClient:
    """Small async client for the official MeteoSwiss STAC and CSV files."""

    def __init__(self, session: ClientSession) -> None:
        """Initialize the client."""
        self._session = session
        self._cache: dict[str, _CachedResponse] = {}
        self._points: list[ForecastPoint] | None = None
        self._stations: list[Station] | None = None

    async def async_resolve_location(
        self,
        latitude: float,
        longitude: float,
        point_id: int | None = None,
        point_type_id: int | None = None,
        station_abbr: str | None = None,
    ) -> tuple[ForecastPoint, Station]:
        """Resolve configured or nearest MeteoSwiss point and station."""
        points, stations = await asyncio.gather(
            self.async_get_forecast_points(),
            self.async_get_stations(),
        )

        if point_id is not None and point_type_id is not None:
            point = next(
                (
                    item
                    for item in points
                    if item.point_id == point_id and item.point_type_id == point_type_id
                ),
                None,
            )
            if point is None:
                raise MeteoSwissClientError(
                    f"Unknown forecast point {point_type_id}:{point_id}"
                )
        else:
            # Prefer postal-code forecast points for home coordinates; fall back
            # to any official point if the closest known location is a station/POI.
            postal_points = [item for item in points if item.point_type_id == 2]
            point = self._nearest(postal_points or points, latitude, longitude)

        if station_abbr:
            station = next(
                (
                    item
                    for item in stations
                    if item.abbr.casefold() == station_abbr.casefold()
                ),
                None,
            )
            if station is None:
                raise MeteoSwissClientError(f"Unknown station {station_abbr}")
        else:
            station = self._nearest(stations, latitude, longitude)

        return point, station

    async def async_get_forecast_points(self) -> list[ForecastPoint]:
        """Return all official local forecast points."""
        if self._points is not None:
            return self._points

        text = await self._async_get_text(LOCAL_POINT_META_URL, encoding="latin-1")
        points: list[ForecastPoint] = []
        for row in self._read_csv(text):
            lat = _float(row.get("point_coordinates_wgs84_lat"))
            lon = _float(row.get("point_coordinates_wgs84_lon"))
            point_id = _int(row.get("point_id"))
            point_type_id = _int(row.get("point_type_id"))
            if lat is None or lon is None or point_id is None or point_type_id is None:
                continue
            points.append(
                ForecastPoint(
                    point_id=point_id,
                    point_type_id=point_type_id,
                    name=row.get("point_name") or f"{point_type_id}:{point_id}",
                    latitude=lat,
                    longitude=lon,
                    altitude=_float(row.get("point_height_masl")),
                    station_abbr=_clean(row.get("station_abbr")),
                    postal_code=_clean(row.get("postal_code")),
                )
            )
        self._points = points
        return points

    async def async_get_stations(self) -> list[Station]:
        """Return all official SwissMetNet stations."""
        if self._stations is not None:
            return self._stations

        text = await self._async_get_text(SMN_STATION_META_URL, encoding="latin-1")
        stations: list[Station] = []
        for row in self._read_csv(text):
            lat = _float(row.get("station_coordinates_wgs84_lat"))
            lon = _float(row.get("station_coordinates_wgs84_lon"))
            abbr = _clean(row.get("station_abbr"))
            if lat is None or lon is None or abbr is None:
                continue
            stations.append(
                Station(
                    abbr=abbr.upper(),
                    name=row.get("station_name") or abbr.upper(),
                    latitude=lat,
                    longitude=lon,
                    altitude=_float(row.get("station_height_masl")),
                    canton=_clean(row.get("station_canton")),
                )
            )
        self._stations = stations
        return stations

    async def async_get_data(
        self, point: ForecastPoint, station: Station
    ) -> MeteoSwissData:
        """Fetch current observations and forecasts."""
        forecast_task = self.async_get_forecast_data(point, station)
        observation_task = self.async_get_observation(station)
        forecast, observation = await asyncio.gather(forecast_task, observation_task)
        forecast.observation = observation
        return forecast

    async def async_get_forecast_data(
        self, point: ForecastPoint, station: Station
    ) -> MeteoSwissData:
        """Fetch forecasts without coupling them to current observations."""
        item = await self._async_latest_item(LOCAL_FORECAST_COLLECTION)
        hourly_task = self._async_forecast_periods(
            item, HOURLY_FORECAST_PARAMETERS, point
        )
        daily_task = self._async_forecast_periods(
            item, DAILY_FORECAST_PARAMETERS, point
        )
        hourly, daily = await asyncio.gather(hourly_task, daily_task)
        updated_raw = item.get("properties", {}).get("updated") or item.get(
            "properties", {}
        ).get("datetime")
        return MeteoSwissData(
            point=point,
            station=station,
            hourly=hourly,
            daily=daily,
            updated_at=_parse_iso_datetime(updated_raw),
        )

    async def async_get_observation(self, station: Station) -> Observation | None:
        """Fetch latest 10-minute values for a SwissMetNet station."""
        abbr = station.abbr.lower()
        url = f"{SMN_ASSET_BASE}/{abbr}/ogd-smn_{abbr}_t_now.csv"
        try:
            text = await self._async_get_text(url, encoding="latin-1")
        except MeteoSwissClientError as err:
            _LOGGER.debug("Unable to fetch observation for %s: %s", station.abbr, err)
            return None

        rows = list(self._read_csv(text))
        if not rows:
            return None

        latest_row = rows[-1]
        latest_timestamp = _parse_station_timestamp(
            latest_row.get("reference_timestamp")
        )
        values: dict[str, float | int | str | None] = {
            key: None
            for key in latest_row
            if key not in {"station_abbr", "reference_timestamp"}
        }
        value_timestamps: dict[str, datetime | None] = {}

        # Newly published rows can be temporarily incomplete. Backfill only from
        # recent rows and retain each value's true timestamp so Home Assistant can
        # expose stale data instead of silently pretending it is current.
        for row in reversed(rows):
            row_timestamp = _parse_station_timestamp(row.get("reference_timestamp"))
            if (
                latest_timestamp is not None
                and row_timestamp is not None
                and latest_timestamp - row_timestamp > OBSERVATION_BACKFILL_MAX_AGE
            ):
                break
            for key, raw_value in row.items():
                if key in {"station_abbr", "reference_timestamp"}:
                    continue
                if values.get(key) is not None:
                    continue
                value = _number_or_text(raw_value)
                if value is not None:
                    values[key] = value
                    value_timestamps[key] = row_timestamp

        return Observation(
            station=station,
            timestamp=latest_timestamp,
            values=values,
            value_timestamps=value_timestamps,
        )

    async def _async_forecast_periods(
        self,
        item: dict[str, Any],
        parameters: Iterable[str],
        point: ForecastPoint,
    ) -> list[ForecastPeriod]:
        """Fetch and merge parameter CSVs into forecast periods."""
        assets = item.get("assets", {})
        merged: dict[datetime, dict[str, float | int | str | None]] = {}

        for parameter in parameters:
            href = _asset_href_for_parameter(assets, parameter)
            if href is None:
                _LOGGER.debug("Forecast parameter %s is not available", parameter)
                continue
            text = await self._async_get_text(href, encoding="latin-1")
            for row in self._read_csv(text):
                if _int(row.get("point_id")) != point.point_id:
                    continue
                if _int(row.get("point_type_id")) != point.point_type_id:
                    continue
                timestamp = _parse_forecast_datetime(row.get("Date"))
                if timestamp is None:
                    continue
                merged.setdefault(timestamp, {})[parameter] = _number_or_text(
                    row.get(parameter)
                )

        return [
            ForecastPeriod(timestamp, values)
            for timestamp, values in sorted(merged.items(), key=lambda item: item[0])
        ]

    async def _async_latest_item(self, collection: str) -> dict[str, Any]:
        """Return the latest available STAC item for a collection."""
        payload = await self._async_get_json(
            f"{STAC_API_BASE}/collections/{collection}/items?limit=25"
        )
        features = payload.get("features") or []
        if not features:
            raise MeteoSwissClientError(f"No STAC items found for {collection}")

        def sort_key(item: dict[str, Any]) -> str:
            properties = item.get("properties", {})
            return (
                properties.get("updated")
                or properties.get("datetime")
                or properties.get("created")
                or item.get("id")
                or ""
            )

        return max(features, key=sort_key)

    async def _async_get_json(self, url: str) -> Any:
        """GET JSON with conditional request support."""
        return await self._async_get(url, "json")

    async def _async_get_text(self, url: str, encoding: str = "utf-8") -> str:
        """GET text with conditional request support."""
        return await self._async_get(url, "text", encoding=encoding)

    async def _async_get(
        self, url: str, response_type: str, encoding: str = "utf-8"
    ) -> Any:
        """GET a URL and reuse cached payload on 304 responses."""
        headers: dict[str, str] = {}
        cached = self._cache.get(url)
        if cached is not None and cached.etag:
            headers["If-None-Match"] = cached.etag
        if cached is not None and cached.last_modified:
            headers["If-Modified-Since"] = cached.last_modified

        try:
            async with self._session.get(url, headers=headers) as response:
                if response.status == 304 and cached is not None:
                    return cached.payload
                response.raise_for_status()
                if response_type == "json":
                    payload = await response.json()
                else:
                    raw = await response.read()
                    payload = raw.decode(encoding, errors="replace")
                self._cache[url] = _CachedResponse(
                    payload=payload,
                    etag=response.headers.get("ETag"),
                    last_modified=response.headers.get("Last-Modified"),
                )
                return payload
        except (ClientError, ClientResponseError, TimeoutError) as err:
            if cached is not None:
                _LOGGER.debug(
                    "Using cached MeteoSwiss payload for %s after %s", url, err
                )
                return cached.payload
            raise MeteoSwissClientError(f"Unable to fetch {url}: {err}") from err

    @staticmethod
    def _read_csv(text: str) -> list[dict[str, str]]:
        """Read MeteoSwiss semicolon-delimited CSV."""
        return list(csv.DictReader(StringIO(text), delimiter=";"))

    @staticmethod
    def _nearest(items: Iterable[Any], latitude: float, longitude: float) -> Any:
        """Return the nearest item with latitude/longitude attributes."""
        items_list = list(items)
        if not items_list:
            raise MeteoSwissClientError("No MeteoSwiss locations available")
        return min(
            items_list,
            key=lambda item: _distance_km(
                latitude, longitude, item.latitude, item.longitude
            ),
        )


def _asset_href_for_parameter(assets: dict[str, Any], parameter: str) -> str | None:
    """Find a forecast asset by MeteoSwiss parameter short name."""
    suffix = f".{parameter}.csv"
    for name, asset in assets.items():
        if name.endswith(suffix):
            return asset.get("href")
    return None


def _parse_forecast_datetime(value: str | None) -> datetime | None:
    """Parse UTC forecast timestamp YYYYMMDDHHMM."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y%m%d%H%M").replace(tzinfo=UTC)
    except ValueError:
        return None


def _parse_station_timestamp(value: str | None) -> datetime | None:
    """Parse UTC SwissMetNet timestamp DD.MM.YYYY HH:MM."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%d.%m.%Y %H:%M").replace(tzinfo=UTC)
    except ValueError:
        return None


def _parse_iso_datetime(value: str | None) -> datetime | None:
    """Parse an ISO timestamp from STAC metadata."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _number_or_text(value: str | None) -> float | int | str | None:
    """Convert CSV values to numeric types where possible."""
    cleaned = _clean(value)
    if cleaned is None:
        return None
    integer = _int(cleaned)
    if integer is not None and "." not in cleaned:
        return integer
    floating = _float(cleaned)
    if floating is not None:
        return floating
    return cleaned


def _clean(value: str | None) -> str | None:
    """Normalize empty CSV strings to None."""
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _float(value: str | None) -> float | None:
    """Parse a float."""
    cleaned = _clean(value)
    if cleaned is None:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _int(value: str | None) -> int | None:
    """Parse an int."""
    cleaned = _clean(value)
    if cleaned is None:
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in kilometers."""
    radius = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    hav = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return 2 * radius * math.atan2(math.sqrt(hav), math.sqrt(1 - hav))
