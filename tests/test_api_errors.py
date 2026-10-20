"""Report request failures as retryable setup failures, never successful data."""

import aiohttp
import pytest

from homeassistant.config_entries import ConfigEntryState

from custom_components.open_meteo_advanced.const import API_BASE_URL, DOMAIN


@pytest.mark.parametrize(
    ("response", "message"),
    [
        ({"status": 400, "text": "Unsupported variable"}, "API error 400"),
        ({"status": 429, "text": "Too many requests"}, "API error 429"),
        ({"status": 503, "text": "Unavailable"}, "API error 503"),
        ({"exc": aiohttp.ClientConnectionError("Offline")}, "Connection error: Offline"),
        ({"exc": TimeoutError()}, "Timed out fetching Open-Meteo data"),
        ({"text": "not JSON"}, "Invalid API JSON"),
        ({"json": []}, "Expected an API response object"),
        ({"json": {"error": True, "reason": "Bad model"}}, "API error: Bad model"),
        (
            {"json": {"timezone": "Not/A_Zone", "utc_offset_seconds": 0}},
            "Unknown API timezone",
        ),
        (
            {"json": {"timezone": "UTC", "utc_offset_seconds": 0, "hourly": []}},
            "Invalid hourly data",
        ),
        (
            {"json": {"timezone": "UTC", "utc_offset_seconds": 0,
                      "hourly": {"time": ["not a timestamp"]}}},
            "Expected a Unix timestamp",
        ),
    ],
)
async def test_request_failure_is_visible_and_retryable(
    hass, config_entry, aioclient_mock, caplog, response, message
):
    """First-refresh failures must not create a falsely loaded config entry."""
    aioclient_mock.get(API_BASE_URL, **response)
    assert not await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.SETUP_RETRY
    assert message in caplog.text
    assert config_entry.entry_id not in hass.data.get(DOMAIN, {})
