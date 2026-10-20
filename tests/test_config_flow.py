"""Exercise configuration through Home Assistant's flow manager."""

import probatio

from homeassistant.data_entry_flow import FlowResultType


async def test_location_form_can_be_serialized_for_ui(hass):
    """The first setup form must render in Home Assistant."""
    result = await hass.config_entries.flow.async_init(
        "open_meteo_advanced", context={"source": "user"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    fields = probatio.to_field_list(result["data_schema"])
    assert {field["name"] for field in fields} == {
        "name", "latitude", "longitude", "model", "weather_entity"
    }
