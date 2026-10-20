"""Exercise configuration through Home Assistant's flow manager."""

import probatio
import pytest

from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.open_meteo_advanced.const import DOMAIN


async def test_location_form_can_be_serialized_for_ui(hass):
    """The first setup form must render in Home Assistant."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    fields = probatio.to_field_list(result["data_schema"])
    assert {field["name"] for field in fields} == {
        "name", "latitude", "longitude", "model", "weather_entity"
    }


@pytest.mark.parametrize("options", [False, True])
@pytest.mark.parametrize(
    ("field", "value"),
    [("latitude", 91), ("latitude", -91), ("longitude", 181), ("longitude", -181)],
)
async def test_location_form_rejects_out_of_bounds_coordinates(hass, options, field, value):
    """Setup and options forms must reject invalid geographic coordinates."""
    if options:
        entry = MockConfigEntry(domain=DOMAIN, data={})
        entry.add_to_hass(hass)
        result = await hass.config_entries.options.async_init(entry.entry_id)
    else:
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
    data = {
        "name": "Brussels", "latitude": 50.85, "longitude": 4.35,
        "model": "best_match", "weather_entity": True,
    }
    data[field] = value
    with pytest.raises(probatio.Invalid):
        result["data_schema"](data)


@pytest.mark.parametrize("options", [False, True])
@pytest.mark.parametrize(
    ("step", "key"),
    [
        ("current_vars", "current_variables"),
        ("hourly_vars", "hourly_variables"),
        ("daily_vars", "daily_variables"),
    ],
)
async def test_variable_form_keeps_unknown_names_visible(hass, options, step, key):
    """A typo must not silently remove a requested sensor."""
    if options:
        entry = MockConfigEntry(domain=DOMAIN, data={})
        entry.add_to_hass(hass)
        manager = hass.config_entries.options
        result = await manager.async_init(entry.entry_id)
    else:
        manager = hass.config_entries.flow
        result = await manager.async_init(DOMAIN, context={"source": "user"})
    result = await manager.async_configure(
        result["flow_id"],
        {"name": "Brussels", "latitude": 50.85, "longitude": 4.35,
         "model": "best_match", "weather_entity": False},
    )
    result = await manager.async_configure(
        result["flow_id"], {"update_interval": 60, "forecast_days": 7, "past_days": 1}
    )
    for prior_step, prior_key in [
        ("current_vars", "current_variables"), ("hourly_vars", "hourly_variables")
    ]:
        if prior_step == step:
            break
        result = await manager.async_configure(result["flow_id"], {prior_key: ""})
    result = await manager.async_configure(
        result["flow_id"], {key: "temperature_2m, misspelled_variable"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == step
    assert result["errors"] == {key: "invalid_variables"}
    fields = probatio.to_field_list(result["data_schema"])
    assert fields[0]["default"] == "temperature_2m, misspelled_variable"


async def test_setup_wizard_accepts_corrected_variables_and_creates_entry(
    hass, mock_api, freezer
):
    """A user can correct a typo, deduplicate names and finish all setup steps."""
    freezer.move_to("2026-10-20T22:30:00+00:00")
    manager = hass.config_entries.flow
    result = await manager.async_init(DOMAIN, context={"source": "user"})
    location = {
        "name": "Brussels", "latitude": 50.85, "longitude": 4.35,
        "model": "best_match", "weather_entity": True,
    }
    result = await manager.async_configure(
        result["flow_id"], result["data_schema"](location)
    )
    result = await manager.async_configure(
        result["flow_id"],
        result["data_schema"]({"update_interval": 15, "forecast_days": 1, "past_days": 0}),
    )
    result = await manager.async_configure(
        result["flow_id"], {"current_variables": "temperature_2m, typo"}
    )
    assert result["errors"] == {"current_variables": "invalid_variables"}
    result = await manager.async_configure(
        result["flow_id"], {"current_variables": " temperature_2m, temperature_2m "}
    )
    result = await manager.async_configure(
        result["flow_id"], {"hourly_variables": ""}
    )
    result = await manager.async_configure(
        result["flow_id"], {"daily_variables": "sunrise"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["current_variables"] == ["temperature_2m"]
    assert result["data"]["hourly_variables"] == []
    assert result["data"]["daily_variables"] == ["sunrise"]
    await hass.async_block_till_done()
    assert mock_api.call_count == 1
