"""Constants for Open-Meteo Advanced integration."""
from dataclasses import dataclass
from typing import Optional

DOMAIN = "open_meteo_advanced"

CONF_NAME = "name"
CONF_LATITUDE = "latitude"
CONF_LONGITUDE = "longitude"
CONF_MODEL = "model"
CONF_FORECAST_DAYS = "forecast_days"
CONF_PAST_DAYS = "past_days"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_HOURLY_VARS = "hourly_variables"
CONF_DAILY_VARS = "daily_variables"
CONF_CURRENT_VARS = "current_variables"

DEFAULT_NAME = "Open-Meteo"
DEFAULT_UPDATE_INTERVAL = 60  # minutes
DEFAULT_FORECAST_DAYS = 7
DEFAULT_PAST_DAYS = 0

CONF_WEATHER_ENTITY = "weather_entity"

API_BASE_URL = "https://api.open-meteo.com/v1/forecast"

# Variables always fetched when the weather entity is enabled
WEATHER_CURRENT_VARS = [
    "temperature_2m", "relative_humidity_2m", "apparent_temperature",
    "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m",
    "pressure_msl", "weather_code", "cloud_cover", "visibility",
    "precipitation", "is_day",
]
WEATHER_HOURLY_VARS = [
    "temperature_2m", "weather_code", "wind_speed_10m", "wind_direction_10m",
    "precipitation_probability", "precipitation", "pressure_msl",
    "cloud_cover", "relative_humidity_2m", "is_day",
]
WEATHER_DAILY_VARS = [
    "temperature_2m_max", "temperature_2m_min", "weather_code",
    "wind_speed_10m_max", "wind_direction_10m_dominant",
    "precipitation_sum", "precipitation_probability_max",
]

# WMO code → HA weather condition
_WMO_TO_CONDITION: dict[int, str] = {
    0: "sunny", 1: "sunny", 2: "partlycloudy", 3: "cloudy",
    45: "fog", 48: "fog",
    51: "rainy", 53: "rainy", 55: "rainy",
    56: "snowy-rainy", 57: "snowy-rainy",
    61: "rainy", 63: "rainy", 65: "pouring",
    66: "snowy-rainy", 67: "snowy-rainy",
    71: "snowy", 73: "snowy", 75: "snowy", 77: "snowy",
    80: "rainy", 81: "rainy", 82: "pouring",
    85: "snowy", 86: "snowy",
    95: "lightning", 96: "hail", 99: "hail",
}


def wmo_to_ha_condition(code: int | None, is_day: int | None = 1) -> str:
    """Convert a WMO weather code to a Home Assistant condition string."""
    if code is None:
        return "exceptional"
    condition = _WMO_TO_CONDITION.get(int(code), "exceptional")
    if condition == "sunny" and is_day == 0:
        return "clear-night"
    return condition


@dataclass
class VariableMeta:
    name: str
    unit: Optional[str]
    device_class: Optional[str]
    icon: Optional[str] = None


HOURLY_VARIABLES: dict[str, VariableMeta] = {
    # Temperature
    "temperature_2m": VariableMeta("Temperature 2m", "°C", "temperature"),
    "dew_point_2m": VariableMeta("Dew Point 2m", "°C", "temperature"),
    "apparent_temperature": VariableMeta("Apparent Temperature", "°C", "temperature"),
    "soil_temperature_0cm": VariableMeta("Soil Temperature 0cm", "°C", "temperature"),
    "soil_temperature_6cm": VariableMeta("Soil Temperature 6cm", "°C", "temperature"),
    "soil_temperature_18cm": VariableMeta("Soil Temperature 18cm", "°C", "temperature"),
    "soil_temperature_54cm": VariableMeta("Soil Temperature 54cm", "°C", "temperature"),
    # Humidity
    "relative_humidity_2m": VariableMeta("Relative Humidity 2m", "%", "humidity"),
    # Pressure
    "pressure_msl": VariableMeta("Pressure MSL", "hPa", "atmospheric_pressure"),
    "surface_pressure": VariableMeta("Surface Pressure", "hPa", "atmospheric_pressure"),
    "vapour_pressure_deficit": VariableMeta("Vapour Pressure Deficit", "kPa", "atmospheric_pressure"),
    # Precipitation
    "precipitation": VariableMeta("Precipitation", "mm", "precipitation"),
    "rain": VariableMeta("Rain", "mm", "precipitation"),
    "showers": VariableMeta("Showers", "mm", "precipitation"),
    "snowfall": VariableMeta("Snowfall", "cm", None, "mdi:snowflake"),
    "snow_depth": VariableMeta("Snow Depth", "m", None, "mdi:snowflake-variant"),
    "precipitation_probability": VariableMeta("Precipitation Probability", "%", None, "mdi:weather-rainy"),
    "evapotranspiration": VariableMeta("Evapotranspiration", "mm", "precipitation"),
    "et0_fao_evapotranspiration": VariableMeta("ET₀ FAO Evapotranspiration", "mm", "precipitation"),
    # Wind
    "wind_speed_10m": VariableMeta("Wind Speed 10m", "km/h", "wind_speed"),
    "wind_speed_80m": VariableMeta("Wind Speed 80m", "km/h", "wind_speed"),
    "wind_speed_120m": VariableMeta("Wind Speed 120m", "km/h", "wind_speed"),
    "wind_speed_180m": VariableMeta("Wind Speed 180m", "km/h", "wind_speed"),
    "wind_direction_10m": VariableMeta("Wind Direction 10m", "°", None, "mdi:compass"),
    "wind_direction_80m": VariableMeta("Wind Direction 80m", "°", None, "mdi:compass"),
    "wind_direction_120m": VariableMeta("Wind Direction 120m", "°", None, "mdi:compass"),
    "wind_direction_180m": VariableMeta("Wind Direction 180m", "°", None, "mdi:compass"),
    "wind_gusts_10m": VariableMeta("Wind Gusts 10m", "km/h", "wind_speed"),
    # Radiation
    "shortwave_radiation": VariableMeta("Shortwave Radiation", "W/m²", "irradiance"),
    "direct_radiation": VariableMeta("Direct Radiation", "W/m²", "irradiance"),
    "direct_normal_irradiance": VariableMeta("Direct Normal Irradiance", "W/m²", "irradiance"),
    "diffuse_radiation": VariableMeta("Diffuse Radiation", "W/m²", "irradiance"),
    "global_tilted_irradiance": VariableMeta("Global Tilted Irradiance", "W/m²", "irradiance"),
    # Cloud
    "cloud_cover": VariableMeta("Cloud Cover", "%", None, "mdi:cloud"),
    "cloud_cover_low": VariableMeta("Cloud Cover Low", "%", None, "mdi:cloud"),
    "cloud_cover_mid": VariableMeta("Cloud Cover Mid", "%", None, "mdi:cloud"),
    "cloud_cover_high": VariableMeta("Cloud Cover High", "%", None, "mdi:cloud-outline"),
    # Other
    "visibility": VariableMeta("Visibility", "m", "distance"),
    "cape": VariableMeta("CAPE", "J/kg", None, "mdi:weather-lightning"),
    "freezing_level_height": VariableMeta("Freezing Level Height", "m", None, "mdi:thermometer-minus"),
    "weather_code": VariableMeta("Weather Code (WMO)", None, None, "mdi:weather-partly-cloudy"),
    "is_day": VariableMeta("Is Day", None, None, "mdi:weather-sunny"),
    # Soil moisture
    "soil_moisture_0_to_1cm": VariableMeta("Soil Moisture 0-1cm", "m³/m³", "moisture"),
    "soil_moisture_1_to_3cm": VariableMeta("Soil Moisture 1-3cm", "m³/m³", "moisture"),
    "soil_moisture_3_to_9cm": VariableMeta("Soil Moisture 3-9cm", "m³/m³", "moisture"),
    "soil_moisture_9_to_27cm": VariableMeta("Soil Moisture 9-27cm", "m³/m³", "moisture"),
    "soil_moisture_27_to_81cm": VariableMeta("Soil Moisture 27-81cm", "m³/m³", "moisture"),
}

DAILY_VARIABLES: dict[str, VariableMeta] = {
    "temperature_2m_max": VariableMeta("Temperature Max", "°C", "temperature"),
    "temperature_2m_mean": VariableMeta("Temperature Mean", "°C", "temperature"),
    "temperature_2m_min": VariableMeta("Temperature Min", "°C", "temperature"),
    "apparent_temperature_max": VariableMeta("Apparent Temp Max", "°C", "temperature"),
    "apparent_temperature_mean": VariableMeta("Apparent Temp Mean", "°C", "temperature"),
    "apparent_temperature_min": VariableMeta("Apparent Temp Min", "°C", "temperature"),
    "precipitation_sum": VariableMeta("Precipitation Sum", "mm", "precipitation"),
    "rain_sum": VariableMeta("Rain Sum", "mm", "precipitation"),
    "showers_sum": VariableMeta("Showers Sum", "mm", "precipitation"),
    "snowfall_sum": VariableMeta("Snowfall Sum", "cm", None, "mdi:snowflake"),
    "precipitation_hours": VariableMeta("Precipitation Hours", "h", "duration"),
    "precipitation_probability_max": VariableMeta("Precip. Probability Max", "%", None, "mdi:weather-rainy"),
    "precipitation_probability_mean": VariableMeta("Precip. Probability Mean", "%", None, "mdi:weather-rainy"),
    "precipitation_probability_min": VariableMeta("Precip. Probability Min", "%", None, "mdi:weather-rainy"),
    "et0_fao_evapotranspiration": VariableMeta("ET₀ FAO Evapotranspiration", "mm", "precipitation"),
    "weather_code": VariableMeta("Weather Code (WMO)", None, None, "mdi:weather-partly-cloudy"),
    "sunrise": VariableMeta("Sunrise", None, "timestamp", "mdi:weather-sunset-up"),
    "sunset": VariableMeta("Sunset", None, "timestamp", "mdi:weather-sunset-down"),
    "sunshine_duration": VariableMeta("Sunshine Duration", "s", "duration"),
    "daylight_duration": VariableMeta("Daylight Duration", "s", "duration"),
    "wind_speed_10m_max": VariableMeta("Wind Speed Max", "km/h", "wind_speed"),
    "wind_gusts_10m_max": VariableMeta("Wind Gusts Max", "km/h", "wind_speed"),
    "wind_direction_10m_dominant": VariableMeta("Wind Direction Dominant", "°", None, "mdi:compass"),
    "shortwave_radiation_sum": VariableMeta("Shortwave Radiation Sum", "MJ/m²", None, "mdi:solar-power"),
    "uv_index_max": VariableMeta("UV Index Max", None, None, "mdi:sun-wireless"),
    "uv_index_clear_sky_max": VariableMeta("UV Index Clear Sky Max", None, None, "mdi:sun-wireless-outline"),
}

CURRENT_VARIABLES: dict[str, VariableMeta] = {
    "temperature_2m": VariableMeta("Temperature", "°C", "temperature"),
    "relative_humidity_2m": VariableMeta("Relative Humidity", "%", "humidity"),
    "apparent_temperature": VariableMeta("Apparent Temperature", "°C", "temperature"),
    "precipitation": VariableMeta("Precipitation", "mm", "precipitation"),
    "rain": VariableMeta("Rain", "mm", "precipitation"),
    "showers": VariableMeta("Showers", "mm", "precipitation"),
    "snowfall": VariableMeta("Snowfall", "cm", None, "mdi:snowflake"),
    "weather_code": VariableMeta("Weather Code (WMO)", None, None, "mdi:weather-partly-cloudy"),
    "cloud_cover": VariableMeta("Cloud Cover", "%", None, "mdi:cloud"),
    "pressure_msl": VariableMeta("Pressure MSL", "hPa", "atmospheric_pressure"),
    "surface_pressure": VariableMeta("Surface Pressure", "hPa", "atmospheric_pressure"),
    "wind_speed_10m": VariableMeta("Wind Speed", "km/h", "wind_speed"),
    "wind_direction_10m": VariableMeta("Wind Direction", "°", None, "mdi:compass"),
    "wind_gusts_10m": VariableMeta("Wind Gusts", "km/h", "wind_speed"),
    "is_day": VariableMeta("Is Day", None, None, "mdi:weather-sunny"),
}

WEATHER_MODELS: dict[str, str] = {
    "best_match": "Best Match (Auto)",
    "ecmwf_ifs_9km": "ECMWF IFS 9km",
    "ecmwf_ifs_025": "ECMWF IFS 0.25°",
    "ecmwf_aifs_025": "ECMWF AIFS 0.25°",
    "cma_grapes_global": "CMA GRAPES Global",
    "bom_access_global": "BOM ACCESS Global",
    "ncep_gfs_seamless": "NCEP GFS Seamless",
    "ncep_gfs_011": "NCEP GFS 0.11°",
    "ncep_hrrr_conus": "NCEP HRRR (CONUS)",
    "ncep_nbm_conus": "NCEP NBM (CONUS)",
    "ncep_nam_conus": "NCEP NAM (CONUS)",
    "ncep_gfs_graphcast": "NCEP GFS GraphCast",
    "ncep_aigfs_025": "NCEP AI-GFS 0.25°",
    "ncep_hgefs_025": "NCEP HGEFS 0.25°",
    "jma_seamless": "JMA Seamless",
    "jma_msm": "JMA MSM",
    "jma_gsm": "JMA GSM",
    "kma_seamless": "KMA Seamless",
    "kma_ldps": "KMA LDPS",
    "kma_gdps": "KMA GDPS",
    "dwd_icon_seamless": "DWD ICON Seamless",
    "dwd_icon_global": "DWD ICON Global",
    "dwd_icon_eu": "DWD ICON-EU",
    "dwd_icon_d2": "DWD ICON-D2",
    "gem_seamless": "GEM Seamless",
    "gem_global": "GEM Global",
    "gem_regional": "GEM Regional",
    "gem_hrdps_continental": "GEM HRDPS Continental",
    "gem_hrdps_west": "GEM HRDPS West",
    "meteofrance_seamless": "Météo-France Seamless",
    "meteofrance_arpege_world": "Météo-France ARPEGE World",
    "meteofrance_arpege_europe": "Météo-France ARPEGE Europe",
    "meteofrance_arome_france": "Météo-France AROME France",
    "meteofrance_arome_france_hd": "Météo-France AROME France HD",
    "italia_meteo_arpae_icon_2i": "ARPAE ICON-2I (Italy)",
    "metno_nordic_seamless": "MET Norway Nordic Seamless",
    "metno_nordic": "MET Norway Nordic",
    "knmi_seamless": "KNMI Seamless",
    "knmi_harmonie_arome_europe": "KNMI HARMONIE-AROME Europe",
    "knmi_harmonie_arome_netherlands": "KNMI HARMONIE-AROME Netherlands",
    "dmi_seamless": "DMI Seamless",
    "dmi_harmonie_arome_europe": "DMI HARMONIE-AROME Europe",
    "ukmo_seamless": "UKMO Seamless",
    "ukmo_global_10km": "UKMO Global 10km",
    "ukmo_uk_2km": "UKMO UK 2km",
    "meteoswiss_seamless": "MeteoSwiss Seamless",
    "meteoswiss_icon_ch1": "MeteoSwiss ICON-CH1",
    "meteoswiss_icon_ch2": "MeteoSwiss ICON-CH2",
    "geosphere_seamless": "GeoSphere Austria Seamless",
    "geosphere_arome_austria": "GeoSphere AROME Austria",
}
