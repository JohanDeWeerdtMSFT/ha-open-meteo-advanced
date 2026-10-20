"""Config flow for Open-Meteo Advanced."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    CONF_CURRENT_VARS,
    CONF_DAILY_VARS,
    CONF_FORECAST_DAYS,
    CONF_HOURLY_VARS,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_MODEL,
    CONF_NAME,
    CONF_PAST_DAYS,
    CONF_UPDATE_INTERVAL,
    CONF_WEATHER_ENTITY,
    CURRENT_VARIABLES,
    DAILY_VARIABLES,
    DEFAULT_FORECAST_DAYS,
    DEFAULT_NAME,
    DEFAULT_PAST_DAYS,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    HOURLY_VARIABLES,
    WEATHER_MODELS,
)

_LOGGER = logging.getLogger(__name__)

_HOURLY_KEYS = list(HOURLY_VARIABLES.keys())
_DAILY_KEYS = list(DAILY_VARIABLES.keys())
_CURRENT_KEYS = list(CURRENT_VARIABLES.keys())
_MODEL_KEYS = list(WEATHER_MODELS.keys())


class OpenMeteoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Multi-step config flow for Open-Meteo Advanced."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_timing()

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_LATITUDE, default=0.0): vol.All(
                    vol.Coerce(float), vol.Range(min=-90, max=90)
                ),
                vol.Required(CONF_LONGITUDE, default=0.0): vol.All(
                    vol.Coerce(float), vol.Range(min=-180, max=180)
                ),
                vol.Required(CONF_MODEL, default="best_match"): vol.In(_MODEL_KEYS),
                vol.Required(CONF_WEATHER_ENTITY, default=True): bool,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_timing(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        if user_input is not None:
            self._data[CONF_UPDATE_INTERVAL] = int(user_input[CONF_UPDATE_INTERVAL])
            self._data[CONF_FORECAST_DAYS] = int(user_input[CONF_FORECAST_DAYS])
            self._data[CONF_PAST_DAYS] = int(user_input[CONF_PAST_DAYS])
            return await self.async_step_current_vars()

        schema = vol.Schema(
            {
                vol.Required(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): vol.All(
                    vol.Coerce(int), vol.Range(min=15, max=1440)
                ),
                vol.Required(CONF_FORECAST_DAYS, default=DEFAULT_FORECAST_DAYS): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=16)
                ),
                vol.Required(CONF_PAST_DAYS, default=DEFAULT_PAST_DAYS): vol.All(
                    vol.Coerce(int), vol.Range(min=0, max=92)
                ),
            }
        )
        return self.async_show_form(step_id="timing", data_schema=schema)

    async def async_step_current_vars(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        if user_input is not None:
            try:
                self._data[CONF_CURRENT_VARS] = _parse_multiselect(
                    user_input.get(CONF_CURRENT_VARS, ""), _CURRENT_KEYS
                )
            except vol.Invalid:
                return _invalid_variables(self, "current_vars", CONF_CURRENT_VARS, user_input)
            return await self.async_step_hourly_vars()

        schema = vol.Schema(
            {
                vol.Optional(CONF_CURRENT_VARS, default=""): str,
            }
        )
        return self.async_show_form(
            step_id="current_vars",
            data_schema=schema,
            description_placeholders={"available": ", ".join(_CURRENT_KEYS)},
        )

    async def async_step_hourly_vars(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        if user_input is not None:
            try:
                self._data[CONF_HOURLY_VARS] = _parse_multiselect(
                    user_input.get(CONF_HOURLY_VARS, ""), _HOURLY_KEYS
                )
            except vol.Invalid:
                return _invalid_variables(self, "hourly_vars", CONF_HOURLY_VARS, user_input)
            return await self.async_step_daily_vars()

        schema = vol.Schema(
            {
                vol.Optional(CONF_HOURLY_VARS, default=""): str,
            }
        )
        return self.async_show_form(step_id="hourly_vars", data_schema=schema)

    async def async_step_daily_vars(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        if user_input is not None:
            try:
                self._data[CONF_DAILY_VARS] = _parse_multiselect(
                    user_input.get(CONF_DAILY_VARS, ""), _DAILY_KEYS
                )
            except vol.Invalid:
                return _invalid_variables(self, "daily_vars", CONF_DAILY_VARS, user_input)
            return self.async_create_entry(
                title=self._data.get(CONF_NAME, DEFAULT_NAME),
                data=self._data,
            )

        schema = vol.Schema(
            {
                vol.Optional(CONF_DAILY_VARS, default=""): str,
            }
        )
        return self.async_show_form(step_id="daily_vars", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "OpenMeteoOptionsFlow":
        return OpenMeteoOptionsFlow(config_entry)


def _parse_multiselect(value: str | list, valid_keys: list[str]) -> list[str]:
    """Accept known variables, preserving order while removing duplicates."""
    if isinstance(value, list):
        items = value
    else:
        items = [v.strip() for v in value.split(",") if v.strip()]
    if any(v not in valid_keys for v in items):
        raise vol.Invalid("Unknown variable name")
    return list(dict.fromkeys(items))


def _invalid_variables(
    flow: config_entries.ConfigFlow | config_entries.OptionsFlow,
    step_id: str,
    key: str,
    user_input: dict[str, Any],
) -> dict:
    """Keep invalid input editable and display a field-specific error."""
    value = user_input.get(key, "")
    if isinstance(value, list):
        value = ", ".join(value)
    return flow.async_show_form(
        step_id=step_id,
        data_schema=vol.Schema({vol.Optional(key, default=value): str}),
        errors={key: "invalid_variables"},
    )


class OpenMeteoOptionsFlow(config_entries.OptionsFlow):
    """Reconfigure all settings after initial setup."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry
        self._data: dict[str, Any] = {**config_entry.data, **config_entry.options}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_timing()

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=self._data.get(CONF_NAME, DEFAULT_NAME)): str,
                vol.Required(CONF_LATITUDE, default=self._data.get(CONF_LATITUDE, 0.0)): vol.All(
                    vol.Coerce(float), vol.Range(min=-90, max=90)
                ),
                vol.Required(CONF_LONGITUDE, default=self._data.get(CONF_LONGITUDE, 0.0)): vol.All(
                    vol.Coerce(float), vol.Range(min=-180, max=180)
                ),
                vol.Required(CONF_MODEL, default=self._data.get(CONF_MODEL, "best_match")): vol.In(_MODEL_KEYS),
                vol.Required(CONF_WEATHER_ENTITY, default=self._data.get(CONF_WEATHER_ENTITY, True)): bool,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_timing(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        if user_input is not None:
            self._data[CONF_UPDATE_INTERVAL] = int(user_input[CONF_UPDATE_INTERVAL])
            self._data[CONF_FORECAST_DAYS] = int(user_input[CONF_FORECAST_DAYS])
            self._data[CONF_PAST_DAYS] = int(user_input[CONF_PAST_DAYS])
            return await self.async_step_current_vars()

        schema = vol.Schema(
            {
                vol.Required(CONF_UPDATE_INTERVAL, default=self._data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)): vol.All(vol.Coerce(int), vol.Range(min=15, max=1440)),
                vol.Required(CONF_FORECAST_DAYS, default=self._data.get(CONF_FORECAST_DAYS, DEFAULT_FORECAST_DAYS)): vol.All(vol.Coerce(int), vol.Range(min=1, max=16)),
                vol.Required(CONF_PAST_DAYS, default=self._data.get(CONF_PAST_DAYS, DEFAULT_PAST_DAYS)): vol.All(vol.Coerce(int), vol.Range(min=0, max=92)),
            }
        )
        return self.async_show_form(step_id="timing", data_schema=schema)

    async def async_step_current_vars(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        if user_input is not None:
            try:
                self._data[CONF_CURRENT_VARS] = _parse_multiselect(
                    user_input.get(CONF_CURRENT_VARS, ""), _CURRENT_KEYS
                )
            except vol.Invalid:
                return _invalid_variables(self, "current_vars", CONF_CURRENT_VARS, user_input)
            return await self.async_step_hourly_vars()

        current = ", ".join(self._data.get(CONF_CURRENT_VARS, []))
        schema = vol.Schema({vol.Optional(CONF_CURRENT_VARS, default=current): str})
        return self.async_show_form(step_id="current_vars", data_schema=schema)

    async def async_step_hourly_vars(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        if user_input is not None:
            try:
                self._data[CONF_HOURLY_VARS] = _parse_multiselect(
                    user_input.get(CONF_HOURLY_VARS, ""), _HOURLY_KEYS
                )
            except vol.Invalid:
                return _invalid_variables(self, "hourly_vars", CONF_HOURLY_VARS, user_input)
            return await self.async_step_daily_vars()

        current = ", ".join(self._data.get(CONF_HOURLY_VARS, []))
        schema = vol.Schema({vol.Optional(CONF_HOURLY_VARS, default=current): str})
        return self.async_show_form(step_id="hourly_vars", data_schema=schema)

    async def async_step_daily_vars(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        if user_input is not None:
            try:
                self._data[CONF_DAILY_VARS] = _parse_multiselect(
                    user_input.get(CONF_DAILY_VARS, ""), _DAILY_KEYS
                )
            except vol.Invalid:
                return _invalid_variables(self, "daily_vars", CONF_DAILY_VARS, user_input)
            return self.async_create_entry(title="", data=self._data)

        current = ", ".join(self._data.get(CONF_DAILY_VARS, []))
        schema = vol.Schema({vol.Optional(CONF_DAILY_VARS, default=current): str})
        return self.async_show_form(step_id="daily_vars", data_schema=schema)
