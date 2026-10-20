"""Test entry setup and options reload through Home Assistant."""

from homeassistant.config_entries import ConfigEntryState
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.open_meteo_advanced.const import DOMAIN


async def set_weather_option(hass, entry, enabled):
    """Complete the real options wizard without mocking the reload listener."""
    manager = hass.config_entries.options
    result = await manager.async_init(entry.entry_id)
    result = await manager.async_configure(
        result["flow_id"],
        {"name": "Brussels", "latitude": 50.85, "longitude": 4.35,
         "model": "best_match", "weather_entity": enabled},
    )
    result = await manager.async_configure(
        result["flow_id"], {"update_interval": 30, "forecast_days": 7, "past_days": 1}
    )
    for key, value in [
        ("current_variables", "temperature_2m, temperature_2m"),
        ("hourly_variables", "temperature_2m"),
        ("daily_variables", "temperature_2m_max, sunrise, sunset"),
    ]:
        result = await manager.async_configure(result["flow_id"], {key: value})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()


async def test_options_toggle_unloads_weather_and_preserves_entity_identity(
    hass, config_entry, mock_api, freezer
):
    """Off/on options reloads must remove weather without affecting built-in data."""
    freezer.move_to("2026-10-20T22:30:00+00:00")
    builtin = MockConfigEntry(
        domain="open_meteo", title="Existing", data={"zone": "zone.home"}
    )
    builtin.add_to_hass(hass)
    hass.states.async_set("weather.existing_open_meteo", "cloudy", {"temperature": 10})
    existing = hass.states.get("weather.existing_open_meteo")

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    weather = registry.async_get_entity_id(
        "weather", DOMAIN, f"{config_entry.entry_id}_weather"
    )
    sensor = registry.async_get_entity_id(
        "sensor", DOMAIN, f"{config_entry.entry_id}_current_temperature_2m"
    )
    assert weather is not None
    assert hass.states.get(weather) is not None

    await set_weather_option(hass, config_entry, False)
    assert config_entry.state is ConfigEntryState.LOADED
    assert hass.states.get(weather) is None
    assert hass.states.get(sensor).state == "11"
    assert config_entry.options["current_variables"] == ["temperature_2m"]

    await set_weather_option(hass, config_entry, True)
    assert config_entry.state is ConfigEntryState.LOADED
    assert registry.async_get_entity_id(
        "weather", DOMAIN, f"{config_entry.entry_id}_weather"
    ) == weather
    assert hass.states.get(weather) is not None

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(weather) is None
    assert hass.states.get(sensor) is None
    assert config_entry.entry_id not in hass.data[DOMAIN]
    assert hass.config_entries.async_get_entry(builtin.entry_id) is builtin
    assert hass.states.get("weather.existing_open_meteo") == existing
