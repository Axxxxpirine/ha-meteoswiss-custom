"""Tests for the MeteoSwiss Open Data client."""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import AsyncMock

import pytest

from custom_components.meteoswiss_custom.client import (
    MeteoSwissClient,
    _asset_href_for_parameter,
    _number_or_text,
    _parse_forecast_datetime,
    _parse_station_timestamp,
)


def test_parse_forecast_datetime() -> None:
    """Forecast timestamps are UTC."""
    parsed = _parse_forecast_datetime("202607052100")

    assert parsed is not None
    assert parsed.isoformat() == "2026-07-05T21:00:00+00:00"


def test_parse_station_timestamp() -> None:
    """Station timestamps are UTC."""
    parsed = _parse_station_timestamp("08.07.2026 00:00")

    assert parsed is not None
    assert parsed.isoformat() == "2026-07-08T00:00:00+00:00"


def test_number_or_text() -> None:
    """CSV values are converted without losing text values."""
    assert _number_or_text("42") == 42
    assert _number_or_text("15.9") == 15.9
    assert _number_or_text("") is None
    assert _number_or_text("ABO") == "ABO"


def test_asset_href_for_parameter() -> None:
    """Forecast asset lookup uses parameter suffixes."""
    assets = {
        "vnut12.lssw.202607060000.tre200h0.csv": {"href": "https://example/tre.csv"},
        "vnut12.lssw.202607060000.rre150h0.csv": {"href": "https://example/rre.csv"},
    }

    assert _asset_href_for_parameter(assets, "tre200h0") == "https://example/tre.csv"
    assert _asset_href_for_parameter(assets, "missing") is None


@pytest.mark.asyncio
async def test_forecast_point_metadata_parsing() -> None:
    """Forecast point metadata is parsed from official CSV shape."""
    client = MeteoSwissClient(cast(Any, object()))
    client._async_get_text = AsyncMock(  # type: ignore[method-assign]
        return_value=(
            "point_id;point_type_id;station_abbr;postal_code;point_name;"
            "point_type_de;point_type_fr;point_type_it;point_type_en;"
            "point_height_masl;point_coordinates_lv95_east;"
            "point_coordinates_lv95_north;point_coordinates_wgs84_lat;"
            "point_coordinates_wgs84_lon\n"
            "1;1;ARO;;Arosa;Station;Station;Stazione;Station;1878.0;"
            "2771031.0;1184830.0;46.792661;9.679014\n"
        )
    )

    points = await client.async_get_forecast_points()

    assert len(points) == 1
    assert points[0].point_id == 1
    assert points[0].point_type_id == 1
    assert points[0].name == "Arosa"
    assert points[0].station_abbr == "ARO"


@pytest.mark.asyncio
async def test_station_metadata_parsing() -> None:
    """Station metadata is parsed from official CSV shape."""
    client = MeteoSwissClient(cast(Any, object()))
    client._async_get_text = AsyncMock(  # type: ignore[method-assign]
        return_value=(
            "station_abbr;station_name;station_canton;station_wigos_id;"
            "station_type_de;station_type_fr;station_type_it;station_type_en;"
            "station_dataowner;station_data_since;station_height_masl;"
            "station_height_barometer_masl;station_coordinates_lv95_east;"
            "station_coordinates_lv95_north;station_coordinates_wgs84_lat;"
            "station_coordinates_wgs84_lon;station_exposition_de;"
            "station_exposition_fr;station_exposition_it;station_exposition_en;"
            "station_url_de;station_url_fr;station_url_it;station_url_en\n"
            "ABO;Adelboden;BE;0-20000-0-06735;Automatische Wetterstationen;"
            "Stations meteorologiques;Stazioni;Automatic weather stations;"
            "MeteoSchweiz;01.01.1901;1321.0;1326.0;2609372.0;1148939.0;"
            "46.491703;7.560703;Hang;Versant;Versante;slope;de;fr;it;en\n"
        )
    )

    stations = await client.async_get_stations()

    assert len(stations) == 1
    assert stations[0].abbr == "ABO"
    assert stations[0].name == "Adelboden"
    assert stations[0].canton == "BE"

