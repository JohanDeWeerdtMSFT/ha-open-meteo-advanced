"""Fixtures for public Home Assistant integration boundaries."""

from copy import deepcopy
from datetime import datetime

import pytest

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.open_meteo_advanced.const import API_BASE_URL, DOMAIN


@pytest.fixture(autouse=True)
def custom_integrations(enable_custom_integrations):
    """Allow Home Assistant to discover the custom integration."""


@pytest.fixture
def config_entry(hass):
    """Use a location whose date differs from the HA host's date."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Brussels",
        data={
            "name": "Brussels", "latitude": 50.85, "longitude": 4.35,
            "model": "best_match", "weather_entity": True,
            "update_interval": 60, "forecast_days": 7, "past_days": 1,
            "current_variables": ["temperature_2m"],
            "hourly_variables": ["temperature_2m"],
            "daily_variables": ["temperature_2m_max", "sunrise", "sunset"],
        },
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def api_data():
    """Model a response with past_days and location-local midnight."""
    return {
        "timezone": "Europe/Brussels",
        "utc_offset_seconds": 7200,
        "current": {
            "temperature_2m": 11, "weather_code": 0, "is_day": 0, "visibility": 1000,
        },
        "hourly": {
            "time": ["2026-10-20T00:00", "2026-10-21T00:00", "2026-10-21T01:00"],
            "temperature_2m": [1, 12, 13],
            "weather_code": [0, 0, 0],
            "is_day": [0, 0, 0],
        },
        "daily": {
            "time": ["2026-10-20", "2026-10-21", "2026-10-22"],
            "temperature_2m_max": [9, 14, 15],
            "temperature_2m_min": [2, 6, 7],
            "weather_code": [0, 0, 0],
            "sunrise": ["2026-10-20T08:00", "2026-10-21T08:02", None],
            "sunset": ["2026-10-20T18:40", "2026-10-21T18:38", None],
        },
    }


@pytest.fixture
def mock_api(aioclient_mock, api_data):
    """Return the format requested at the HTTP boundary, as the real API does."""
    epoch = deepcopy(api_data)
    for section, key in [
        ("hourly", "time"), ("daily", "time"),
        ("daily", "sunrise"), ("daily", "sunset"),
    ]:
        epoch[section][key] = [
            int(datetime.fromisoformat(
                f"{value}T00:00+02:00" if len(value) == 10 else f"{value}+02:00"
            ).timestamp()) if value is not None else None
            for value in api_data[section][key]
        ]
    aioclient_mock.get(API_BASE_URL, params={"timeformat": "unixtime"}, json=epoch)
    aioclient_mock.get(API_BASE_URL, json=api_data)
    return aioclient_mock
