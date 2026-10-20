"""Weather platform for Open-Meteo Advanced."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_MODEL, CONF_NAME, CONF_WEATHER_ENTITY, DOMAIN
from .coordinator import OpenMeteoCoordinator

_LOGGER = logging.getLogger(__name__)

# Import weather-specific HA classes; handle version differences gracefully
try:
    from homeassistant.components.weather import (
        WeatherEntity,
        WeatherEntityFeature,
    )
    _FEATURES = WeatherEntityFeature.FORECAST_DAILY | WeatherEntityFeature.FORECAST_HOURLY
except (ImportError, AttributeError):
    from homeassistant.components.weather import WeatherEntity
    WeatherEntityFeature = None
    _FEATURES = 0

try:
    from homeassistant.const import (
        UnitOfLength,
        UnitOfPressure,
        UnitOfSpeed,
        UnitOfTemperature,
    )
    _TEMP_UNIT = UnitOfTemperature.CELSIUS
    _WIND_UNIT = UnitOfSpeed.KILOMETERS_PER_HOUR
    _PRESSURE_UNIT = UnitOfPressure.HPA
    _VISIBILITY_UNIT = UnitOfLength.KILOMETERS
    _PRECIP_UNIT = UnitOfLength.MILLIMETERS
except (ImportError, AttributeError):
    _TEMP_UNIT = "°C"
    _WIND_UNIT = "km/h"
    _PRESSURE_UNIT = "hPa"
    _VISIBILITY_UNIT = "km"
    _PRECIP_UNIT = "mm"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    opts = {**entry.data, **entry.options}
    if not opts.get(CONF_WEATHER_ENTITY, False):
        return
    coordinator: OpenMeteoCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([OpenMeteoWeatherEntity(coordinator, entry)])


class OpenMeteoWeatherEntity(CoordinatorEntity[OpenMeteoCoordinator], WeatherEntity):
    """Weather entity backed by Open-Meteo data."""

    _attr_has_entity_name = True
    _attr_name = "Weather"
    _attr_native_temperature_unit = _TEMP_UNIT
    _attr_native_wind_speed_unit = _WIND_UNIT
    _attr_native_pressure_unit = _PRESSURE_UNIT
    _attr_native_visibility_unit = _VISIBILITY_UNIT
    _attr_native_precipitation_unit = _PRECIP_UNIT
    _attr_supported_features = _FEATURES

    def __init__(
        self,
        coordinator: OpenMeteoCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_weather"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.data.get(CONF_NAME, "Open-Meteo"),
            manufacturer="Open-Meteo",
            model=entry.options.get(CONF_MODEL, entry.data.get(CONF_MODEL, "best_match")),
            configuration_url="https://open-meteo.com/en/docs",
        )

    @property
    def _weather(self) -> dict[str, Any]:
        if self.coordinator.data:
            return self.coordinator.data.get("_weather", {})
        return {}

    @property
    def condition(self) -> str | None:
        return self._weather.get("condition")

    @property
    def native_temperature(self) -> float | None:
        return self._weather.get("temperature")

    @property
    def humidity(self) -> float | None:
        return self._weather.get("humidity")

    @property
    def native_wind_speed(self) -> float | None:
        return self._weather.get("wind_speed")

    @property
    def wind_bearing(self) -> float | None:
        return self._weather.get("wind_bearing")

    @property
    def native_wind_gust_speed(self) -> float | None:
        return self._weather.get("wind_gust_speed")

    @property
    def native_pressure(self) -> float | None:
        return self._weather.get("pressure")

    @property
    def cloud_coverage(self) -> float | None:
        return self._weather.get("cloud_coverage")

    @property
    def native_visibility(self) -> float | None:
        return self._weather.get("visibility")

    # ------------------------------------------------------------------
    # Forecasts (HA 2023.9+ API)
    # ------------------------------------------------------------------

    async def async_forecast_hourly(self) -> list[dict[str, Any]]:
        return self._weather.get("hourly_forecast", [])

    async def async_forecast_daily(self) -> list[dict[str, Any]]:
        return self._weather.get("daily_forecast", [])

    @property
    def forecast(self) -> list[dict[str, Any]]:
        """Deprecated forecast property kept for HA < 2023.9 compatibility."""
        return self._weather.get("daily_forecast", [])
