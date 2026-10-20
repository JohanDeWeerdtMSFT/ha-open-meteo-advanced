"""Verify weather and timestamp data through Home Assistant state/service APIs."""

from homeassistant.helpers import entity_registry as er

from custom_components.open_meteo_advanced.const import DOMAIN


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
