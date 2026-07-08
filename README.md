# MeteoSwiss Custom for Home Assistant

Custom Home Assistant integration for official MeteoSwiss Open Data.

This integration uses only documented MeteoSwiss/FSDI Open Data endpoints:

- Local forecasts: `ch.meteoschweiz.ogd-local-forecasting`
- SwissMetNet observations: `ch.meteoschweiz.ogd-smn`

Attribution: **Source: MeteoSwiss**.

## Features

- UI configuration flow.
- Automatic nearest forecast point and SwissMetNet station from the Home Assistant location.
- Optional manual override using official MeteoSwiss point IDs and station abbreviations.
- One `weather` entity with hourly and daily forecasts.
- Observation sensors for temperature, humidity, dew point, precipitation, wind, gusts, wind bearing, pressure, radiation and sunshine.
- Diagnostics for the resolved official point/station and last update status.
- French and English translations.

## Installation with HACS

1. Add this repository as a custom HACS repository of type **Integration**.
2. Install **MeteoSwiss Custom**.
3. Restart Home Assistant.
4. Go to **Settings > Devices & services > Add integration** and search for **MeteoSwiss Custom**.

## Manual Installation

Copy `custom_components/meteoswiss_custom` into your Home Assistant `custom_components` directory, then restart Home Assistant.

## Manual Location Override

The integration can auto-select official sources. For manual setup, use:

- `point_id` and `point_type_id` from `ogd-local-forecasting_meta_point.csv`.
- `station_abbr` from `ogd-smn_meta_stations.csv`.

Point type IDs:

- `1`: weather station
- `2`: postal code
- `3`: mountain point of interest

## Data Update Behavior

Home Assistant polls every 20 minutes. MeteoSwiss local forecasts are updated hourly; SwissMetNet 10-minute files are updated approximately every 10 minutes.

The client uses conditional requests (`ETag` / `Last-Modified`) where the FSDI service provides them.

## Known Limitations

- This v1 uses official documented Open Data only. It does not call private or undocumented MeteoSwiss app endpoints.
- Natural hazard warnings, radar products and pollen products are not exposed as Home Assistant entities until they are mapped from official Open Data collections with stable semantics.
- Forecast CSV files are split by parameter, so the first refresh downloads several official CSV assets.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
pytest
ruff check .
```

For full Home Assistant validation, run `hassfest` in a Home Assistant development environment.

