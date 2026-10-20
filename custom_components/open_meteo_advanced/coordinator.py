"""DataUpdateCoordinator for Open-Meteo Advanced."""
from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta, tzinfo
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    API_BASE_URL,
    CONF_CURRENT_VARS,
    CONF_DAILY_VARS,
    CONF_FORECAST_DAYS,
    CONF_HOURLY_VARS,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_MODEL,
    CONF_PAST_DAYS,
    CONF_WEATHER_ENTITY,
    DOMAIN,
    WEATHER_CURRENT_VARS,
    WEATHER_DAILY_VARS,
    WEATHER_HOURLY_VARS,
    wmo_to_ha_condition,
)

_LOGGER = logging.getLogger(__name__)

MAX_HOURLY_FORECAST = 48
MAX_DAILY_FORECAST = 14


class OpenMeteoCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetches data from Open-Meteo API and exposes it per-variable."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        update_interval: timedelta,
    ) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=update_interval)
        self.entry = entry
        self._session = async_get_clientsession(hass)

    async def _async_update_data(self) -> dict[str, Any]:
        opts: dict[str, Any] = {**self.entry.data, **self.entry.options}

        user_hourly: list[str] = opts.get(CONF_HOURLY_VARS, [])
        user_daily: list[str] = opts.get(CONF_DAILY_VARS, [])
        user_current: list[str] = opts.get(CONF_CURRENT_VARS, [])
        weather_entity: bool = opts.get(CONF_WEATHER_ENTITY, False)

        # Merge user-selected vars with weather-entity vars (deduplicated)
        if weather_entity:
            hourly_vars = list(dict.fromkeys(user_hourly + WEATHER_HOURLY_VARS))
            daily_vars = list(dict.fromkeys(user_daily + WEATHER_DAILY_VARS))
            current_vars = list(dict.fromkeys(user_current + WEATHER_CURRENT_VARS))
        else:
            hourly_vars = user_hourly
            daily_vars = user_daily
            current_vars = user_current

        if not hourly_vars and not daily_vars and not current_vars:
            return {}

        params: dict[str, Any] = {
            "latitude": opts[CONF_LATITUDE],
            "longitude": opts[CONF_LONGITUDE],
            "timezone": "auto",
            "timeformat": "unixtime",
            "wind_speed_unit": "kmh",
            "forecast_days": opts.get(CONF_FORECAST_DAYS, 7),
            "past_days": opts.get(CONF_PAST_DAYS, 0),
        }

        model = opts.get(CONF_MODEL, "best_match")
        if model != "best_match":
            params["models"] = model

        if hourly_vars:
            params["hourly"] = ",".join(hourly_vars)
        if daily_vars:
            params["daily"] = ",".join(daily_vars)
        if current_vars:
            params["current"] = ",".join(current_vars)

        try:
            async with self._session.get(
                API_BASE_URL,
                params=params,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise UpdateFailed(f"API error {resp.status}: {body[:200]}")
                raw = await resp.json()
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Connection error: {err}") from err
        except TimeoutError as err:
            raise UpdateFailed("Timed out fetching Open-Meteo data") from err
        except ValueError as err:
            raise UpdateFailed(f"Invalid API JSON: {err}") from err

        try:
            if not isinstance(raw, dict):
                raise ValueError("Expected an API response object")
            if raw.get("error"):
                raise UpdateFailed(f"API error: {raw.get('reason', 'Unknown error')}")
            for section in ("current", "hourly", "daily"):
                if raw.get(section) is not None and not isinstance(raw[section], dict):
                    raise ValueError(f"Invalid {section} data")

            result = self._parse_sensors(raw, user_hourly, user_daily, user_current)
            if weather_entity:
                result["_weather"] = self._parse_weather(raw)
        except (KeyError, TypeError, ValueError, OverflowError) as err:
            raise UpdateFailed(f"Invalid API response: {err}") from err

        return result

    # ------------------------------------------------------------------
    # Sensor data parsing
    # ------------------------------------------------------------------

    def _parse_sensors(
        self,
        raw: dict[str, Any],
        hourly_vars: list[str],
        daily_vars: list[str],
        current_vars: list[str],
    ) -> dict[str, Any]:
        result: dict[str, Any] = {}
        now = dt_util.utcnow()
        zone = _response_timezone(raw)

        current = raw.get("current") or {}
        for var in current_vars:
            result[f"current_{var}"] = current.get(var)

        if hourly_vars:
            hourly = raw.get("hourly") or {}
            times = [_utc_timestamp(t) for t in _series(hourly, "time")]
            idx = next(
                (i for i, t in enumerate(times) if t <= now < t + timedelta(hours=1)),
                None,
            )
            upcoming = [
                i for i, t in enumerate(times) if t + timedelta(hours=1) > now
            ][:MAX_HOURLY_FORECAST]

            for var in hourly_vars:
                result[f"hourly_{var}"] = _value(hourly, var, idx)
                result[f"hourly_{var}_forecast"] = [
                    {"time": times[i].isoformat(), "value": _value(hourly, var, i)}
                    for i in upcoming
                ]

        if daily_vars:
            daily = raw.get("daily") or {}
            dates = _daily_dates(raw, daily)
            today = now.astimezone(zone).date()
            idx = next((i for i, date in enumerate(dates) if date == today), None)
            upcoming = [
                i for i, date in enumerate(dates) if date >= today
            ][:MAX_DAILY_FORECAST]

            for var in daily_vars:
                value = _value(daily, var, idx)
                result[f"daily_{var}"] = (
                    _utc_timestamp(value)
                    if var in ("sunrise", "sunset") and value is not None
                    else value
                )
                forecast = []
                for i in upcoming:
                    value = _value(daily, var, i)
                    if var in ("sunrise", "sunset") and value is not None:
                        value = _utc_timestamp(value).isoformat()
                    forecast.append({"time": dates[i].isoformat(), "value": value})
                result[f"daily_{var}_forecast"] = forecast

        return result

    # ------------------------------------------------------------------
    # Weather entity data parsing
    # ------------------------------------------------------------------

    def _parse_weather(self, raw: dict[str, Any]) -> dict[str, Any]:
        now = dt_util.utcnow()
        zone = _response_timezone(raw)
        current_raw = raw.get("current") or {}

        weather: dict[str, Any] = {
            "temperature": current_raw.get("temperature_2m"),
            "humidity": current_raw.get("relative_humidity_2m"),
            "apparent_temperature": current_raw.get("apparent_temperature"),
            "wind_speed": current_raw.get("wind_speed_10m"),
            "wind_bearing": current_raw.get("wind_direction_10m"),
            "wind_gust_speed": current_raw.get("wind_gusts_10m"),
            "pressure": current_raw.get("pressure_msl"),
            "cloud_coverage": current_raw.get("cloud_cover"),
            "visibility": _m_to_km(current_raw.get("visibility")),
            "condition": wmo_to_ha_condition(
                current_raw.get("weather_code"),
                current_raw.get("is_day", 1),
            ),
            "hourly_forecast": [],
            "daily_forecast": [],
        }

        # Hourly forecast
        hourly_raw = raw.get("hourly") or {}
        h_times = [_utc_timestamp(t) for t in _series(hourly_raw, "time")]
        if h_times:
            upcoming = [
                i for i, t in enumerate(h_times) if t + timedelta(hours=1) > now
            ][:MAX_HOURLY_FORECAST]

            h_temp = _series(hourly_raw, "temperature_2m")
            h_code = _series(hourly_raw, "weather_code")
            h_wind = _series(hourly_raw, "wind_speed_10m")
            h_bearing = _series(hourly_raw, "wind_direction_10m")
            h_precip_prob = _series(hourly_raw, "precipitation_probability")
            h_precip = _series(hourly_raw, "precipitation")
            h_pressure = _series(hourly_raw, "pressure_msl")
            h_cloud = _series(hourly_raw, "cloud_cover")
            h_humidity = _series(hourly_raw, "relative_humidity_2m")
            h_is_day = _series(hourly_raw, "is_day")

            for i in upcoming:
                code = h_code[i] if i < len(h_code) else None
                weather["hourly_forecast"].append({
                    "datetime": h_times[i].isoformat(),
                    "condition": wmo_to_ha_condition(
                        code, h_is_day[i] if i < len(h_is_day) else None
                    ),
                    "native_temperature": h_temp[i] if i < len(h_temp) else None,
                    "native_wind_speed": h_wind[i] if i < len(h_wind) else None,
                    "wind_bearing": h_bearing[i] if i < len(h_bearing) else None,
                    "precipitation_probability": h_precip_prob[i] if i < len(h_precip_prob) else None,
                    "native_precipitation": h_precip[i] if i < len(h_precip) else None,
                    "native_pressure": h_pressure[i] if i < len(h_pressure) else None,
                    "cloud_coverage": h_cloud[i] if i < len(h_cloud) else None,
                    "humidity": h_humidity[i] if i < len(h_humidity) else None,
                })

        # Daily forecast
        daily_raw = raw.get("daily") or {}
        dates = _daily_dates(raw, daily_raw)
        if dates:
            today = now.astimezone(zone).date()
            upcoming = [
                i for i, date in enumerate(dates) if date >= today
            ][:MAX_DAILY_FORECAST]

            d_max = _series(daily_raw, "temperature_2m_max")
            d_min = _series(daily_raw, "temperature_2m_min")
            d_code = _series(daily_raw, "weather_code")
            d_wind = _series(daily_raw, "wind_speed_10m_max")
            d_bearing = _series(daily_raw, "wind_direction_10m_dominant")
            d_precip = _series(daily_raw, "precipitation_sum")
            d_precip_prob = _series(daily_raw, "precipitation_probability_max")

            for i in upcoming:
                code = d_code[i] if i < len(d_code) else None
                weather["daily_forecast"].append({
                    "datetime": datetime.combine(
                        dates[i], time(), tzinfo=zone
                    ).astimezone(dt_util.UTC).isoformat(),
                    "condition": wmo_to_ha_condition(code),
                    "native_temperature": d_max[i] if i < len(d_max) else None,
                    "native_templow": d_min[i] if i < len(d_min) else None,
                    "native_wind_speed": d_wind[i] if i < len(d_wind) else None,
                    "wind_bearing": d_bearing[i] if i < len(d_bearing) else None,
                    "native_precipitation": d_precip[i] if i < len(d_precip) else None,
                    "precipitation_probability": d_precip_prob[i] if i < len(d_precip_prob) else None,
                })

        return weather


def _response_timezone(raw: dict[str, Any]) -> tzinfo:
    """Use the API location, never the Home Assistant host's timezone."""
    zone = dt_util.get_time_zone(raw["timezone"])
    if zone is None:
        raise ValueError(f"Unknown API timezone: {raw['timezone']}")
    return zone


def _utc_timestamp(value: int | float) -> datetime:
    """Decode the explicitly requested Unix time without guessing a timezone."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"Expected a Unix timestamp, got {value!r}")
    return dt_util.utc_from_timestamp(value)


def _series(block: dict[str, Any], key: str) -> list[Any]:
    """Missing/null variable arrays represent unavailable measurements."""
    values = block.get(key)
    if values is None:
        return []
    if not isinstance(values, list):
        raise ValueError(f"Expected an array for {key}")
    return values


def _value(block: dict[str, Any], key: str, index: int | None) -> Any:
    values = _series(block, key)
    return values[index] if index is not None and index < len(values) else None


def _daily_dates(raw: dict[str, Any], daily: dict[str, Any]) -> list[date]:
    """Open-Meteo daily Unix dates use the response's fixed UTC offset."""
    offset = timedelta(seconds=raw["utc_offset_seconds"])
    return [
        (_utc_timestamp(value) + offset).date()
        for value in _series(daily, "time")
    ]


def _m_to_km(value: float | None) -> float | None:
    """Convert visibility from metres to kilometres."""
    return round(value / 1000, 1) if value is not None else None
