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
