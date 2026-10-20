"""Verify weather and timestamp data through Home Assistant state/service APIs."""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from homeassistant.helpers import entity_registry as er

from custom_components.open_meteo_advanced.const import API_BASE_URL, DOMAIN


def entity_id(hass, entry, platform, suffix):
    """Resolve the existing entity identity instead of relying on display names."""
    result = er.async_get(hass).async_get_entity_id(
        platform, DOMAIN, f"{entry.entry_id}_{suffix}"
    )
    assert result is not None
    return result


async def test_location_time_drives_sensor_states_and_forecasts(
    hass, config_entry, mock_api, freezer
):
    """Location date/hour, aware timestamps and native forecast units agree."""
    freezer.move_to("2026-10-20T22:30:00+00:00")
    await hass.config.async_set_time_zone("America/Los_Angeles")
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get(
        entity_id(hass, config_entry, "sensor", "hourly_temperature_2m")
    ).state == "12"
    assert hass.states.get(
        entity_id(hass, config_entry, "sensor", "daily_temperature_2m_max")
    ).state == "14"
    assert hass.states.get(
        entity_id(hass, config_entry, "sensor", "daily_sunrise")
    ).state == "2026-10-21T06:02:00+00:00"
    assert hass.states.get(
        entity_id(hass, config_entry, "sensor", "daily_sunset")
    ).state == "2026-10-21T16:38:00+00:00"

    weather = entity_id(hass, config_entry, "weather", "weather")
    hourly = await hass.services.async_call(
        "weather", "get_forecasts", {"entity_id": weather, "type": "hourly"},
        blocking=True, return_response=True,
    )
    assert [item["datetime"] for item in hourly[weather]["forecast"]] == [
        "2026-10-20T22:00:00+00:00", "2026-10-20T23:00:00+00:00",
    ]
    assert hourly[weather]["forecast"][0]["temperature"] == 12
    assert hourly[weather]["forecast"][0]["condition"] == "clear-night"
    daily = await hass.services.async_call(
        "weather", "get_forecasts", {"entity_id": weather, "type": "daily"},
        blocking=True, return_response=True,
    )
    assert daily[weather]["forecast"][0]["datetime"] == "2026-10-20T22:00:00+00:00"
    assert daily[weather]["forecast"][0]["temperature"] == 14
    assert daily[weather]["forecast"][0]["templow"] == 6
    assert mock_api.call_count == 1
    query = mock_api.mock_calls[0][1].query
    assert query["timezone"] == "auto"
    assert query["past_days"] == "1"
    assert query["hourly"].split(",").count("temperature_2m") == 1


def epoch(value):
    """Encode a literal instant for the mocked API, not the expected output."""
    return int(datetime.fromisoformat(value).timestamp())


@pytest.mark.parametrize(
    ("now", "zone", "offset", "hours", "days", "temperature", "first_hour", "next_day"),
    [
        (
            "2026-10-25T00:30:00+00:00", "Europe/Brussels", 7200,
            ["2026-10-25T00:00:00+00:00", "2026-10-25T01:00:00+00:00",
             "2026-10-25T02:00:00+00:00"],
            ["2026-10-24", "2026-10-25", "2026-10-26"],
            "10", "2026-10-25T00:00:00+00:00", "2026-10-25T23:00:00+00:00",
        ),
        (
            "2026-10-25T01:30:00+00:00", "Europe/Brussels", 7200,
            ["2026-10-25T00:00:00+00:00", "2026-10-25T01:00:00+00:00",
             "2026-10-25T02:00:00+00:00"],
            ["2026-10-24", "2026-10-25", "2026-10-26"],
            "11", "2026-10-25T01:00:00+00:00", "2026-10-25T23:00:00+00:00",
        ),
        (
            "2026-03-29T01:30:00+00:00", "Europe/Brussels", 3600,
            ["2026-03-29T00:00:00+00:00", "2026-03-29T01:00:00+00:00",
             "2026-03-29T02:00:00+00:00"],
            ["2026-03-28", "2026-03-29", "2026-03-30"],
            "11", "2026-03-29T01:00:00+00:00", "2026-03-29T22:00:00+00:00",
        ),
        (
            "2026-10-20T19:00:00+00:00", "Asia/Kolkata", 19800,
            ["2026-10-20T18:30:00+00:00", "2026-10-20T19:30:00+00:00",
             "2026-10-20T20:30:00+00:00"],
            ["2026-10-20", "2026-10-21", "2026-10-22"],
            "10", "2026-10-20T18:30:00+00:00", "2026-10-21T18:30:00+00:00",
        ),
        (
            "2026-10-20T02:30:00+00:00", "America/Los_Angeles", -25200,
            ["2026-10-20T01:00:00+00:00", "2026-10-20T02:00:00+00:00",
             "2026-10-20T03:00:00+00:00"],
            ["2026-10-18", "2026-10-19", "2026-10-20"],
            "11", "2026-10-20T02:00:00+00:00", "2026-10-20T07:00:00+00:00",
        ),
    ],
)
async def test_dst_and_remote_timezones_keep_correct_instants_and_dates(
    hass, config_entry, aioclient_mock, freezer, now, zone, offset,
    hours, days, temperature, first_hour, next_day
):
    """Repeated/skipped hours and fixed-offset API dates must not shift values."""
    freezer.move_to(now)
    fixed_offset = timezone(timedelta(seconds=offset))
    raw = {
        "timezone": zone, "utc_offset_seconds": offset,
        "hourly": {
            "time": [epoch(value) for value in hours],
            "temperature_2m": [10, 11, 12],
        },
        "daily": {
            "time": [
                int(datetime.fromisoformat(day).replace(tzinfo=fixed_offset).timestamp())
                for day in days
            ],
            "temperature_2m_max": [90, 20, 30],
        },
    }
    aioclient_mock.get(API_BASE_URL, params={"timeformat": "unixtime"}, json=raw)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(
        entity_id(hass, config_entry, "sensor", "hourly_temperature_2m")
    ).state == temperature
    assert hass.states.get(
        entity_id(hass, config_entry, "sensor", "daily_temperature_2m_max")
    ).state == "20"
    weather = entity_id(hass, config_entry, "weather", "weather")
    for forecast_type, expected in [("hourly", first_hour), ("daily", next_day)]:
        response = await hass.services.async_call(
            "weather", "get_forecasts", {"entity_id": weather, "type": forecast_type},
            blocking=True, return_response=True,
        )
        forecasts = response[weather]["forecast"]
        assert forecasts[0 if forecast_type == "hourly" else 1]["datetime"] == expected


@pytest.mark.parametrize("shape", ["missing", "null_block", "null_array", "short", "null_value"])
async def test_missing_or_null_measurements_are_unknown_not_setup_errors(
    hass, config_entry, aioclient_mock, freezer, shape
):
    """An unavailable variable must not break other entities or the config entry."""
    freezer.move_to("2026-10-20T22:30:00+00:00")
    raw = {"timezone": "UTC", "utc_offset_seconds": 0}
    if shape == "null_block":
        raw.update(current=None, hourly=None, daily=None)
    elif shape != "missing":
        values = {"null_array": None, "short": [], "null_value": [None]}[shape]
        raw.update(
            current={"temperature_2m": None},
            hourly={"time": [epoch("2026-10-20T22:00:00+00:00")],
                    "temperature_2m": values},
            daily={"time": [epoch("2026-10-20T00:00:00+00:00")],
                   "temperature_2m_max": values, "sunrise": values, "sunset": values},
        )
    aioclient_mock.get(API_BASE_URL, json=raw)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    for suffix in [
        "current_temperature_2m", "hourly_temperature_2m",
        "daily_temperature_2m_max", "daily_sunrise", "daily_sunset",
    ]:
        assert hass.states.get(entity_id(hass, config_entry, "sensor", suffix)).state == "unknown"


async def test_forecast_windows_are_bounded_and_past_values_are_not_reused(
    hass, config_entry, aioclient_mock, freezer
):
    """past_days does not consume the 48-hour/14-day forecast budget."""
    freezer.move_to("2026-10-20T22:30:00+00:00")
    start_hour = datetime(2026, 10, 19, 22, tzinfo=UTC)
    start_day = datetime(2026, 10, 19, tzinfo=timezone(timedelta(hours=2)))
    raw = {
        "timezone": "Europe/Brussels", "utc_offset_seconds": 7200,
        "hourly": {
            "time": [int((start_hour + timedelta(hours=i)).timestamp()) for i in range(100)],
            "temperature_2m": [20] * 100,
        },
        "daily": {
            "time": [int((start_day + timedelta(days=i)).timestamp()) for i in range(20)],
            "temperature_2m_max": [25] * 20,
        },
    }
    aioclient_mock.get(API_BASE_URL, json=raw)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    weather = entity_id(hass, config_entry, "weather", "weather")
    for forecast_type, suffix, limit in [
        ("hourly", "hourly_temperature_2m", 48),
        ("daily", "daily_temperature_2m_max", 14),
    ]:
        response = await hass.services.async_call(
            "weather", "get_forecasts", {"entity_id": weather, "type": forecast_type},
            blocking=True, return_response=True,
        )
        assert len(response[weather]["forecast"]) == limit
        assert response[weather]["forecast"][0]["datetime"] == "2026-10-20T22:00:00+00:00"
        state = hass.states.get(entity_id(hass, config_entry, "sensor", suffix))
        assert len(state.attributes["forecast"]) == limit

    aioclient_mock.clear_requests()
    aioclient_mock.get(API_BASE_URL, json={
        "timezone": "Europe/Brussels", "utc_offset_seconds": 7200,
        "hourly": {"time": [epoch("2026-10-19T00:00:00+00:00")], "temperature_2m": [99]},
        "daily": {"time": [epoch("2026-10-18T22:00:00+00:00")], "temperature_2m_max": [99]},
    })
    # A normal config-entry reload must not resurrect an expired forecast.
    assert await hass.config_entries.async_reload(config_entry.entry_id)
    await hass.async_block_till_done()
    for suffix in ["hourly_temperature_2m", "daily_temperature_2m_max"]:
        state = hass.states.get(entity_id(hass, config_entry, "sensor", suffix))
        assert state.state == "unknown"
        assert "forecast" not in state.attributes
    for forecast_type in ["hourly", "daily"]:
        response = await hass.services.async_call(
            "weather", "get_forecasts", {"entity_id": weather, "type": forecast_type},
            blocking=True, return_response=True,
        )
        assert response[weather]["forecast"] == []


@pytest.mark.parametrize("model", ["best_match", "dwd_icon_global"])
async def test_request_honors_option_overrides_without_duplicate_weather_variables(
    hass, config_entry, mock_api, freezer, model
):
    """Options override stored location/model/range without changing entity IDs."""
    freezer.move_to("2026-10-20T22:30:00+00:00")
    hass.config_entries.async_update_entry(
        config_entry,
        options={
            "latitude": 51.0, "longitude": 5.0, "model": model,
            "forecast_days": 3, "past_days": 2, "update_interval": 30,
        },
    )
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    query = mock_api.mock_calls[0][1].query
    assert query["latitude"] == "51.0"
    assert query["longitude"] == "5.0"
    assert query["forecast_days"] == "3"
    assert query["past_days"] == "2"
    assert query["timeformat"] == "unixtime"
    assert query["wind_speed_unit"] == "kmh"
    if model == "best_match":
        assert "models" not in query
    else:
        assert query["models"] == "dwd_icon_global"
    for group in ["hourly", "daily", "current"]:
        variables = query[group].split(",")
        assert len(variables) == len(set(variables))
    assert hass.states.get(
        entity_id(hass, config_entry, "sensor", "hourly_temperature_2m")
    ).state == "12"
