# Open-Meteo Advanced — Home Assistant Integration

A custom integration for [Home Assistant](https://www.home-assistant.io/) that exposes the full power of the [Open-Meteo](https://open-meteo.com/) weather API: choose any forecasting model, select individual variables as sensors, and get a complete `weather` entity with hourly and daily forecasts.

> **Why not the official integration?**
> The built-in HA Open-Meteo integration covers a fixed set of variables and uses a single model. This integration lets you pick any combination of the 80+ available variables and any of the 48 supported models — including regional high-resolution models like ARPAE ICON-2I for Italy, Météo-France AROME, DWD ICON-D2, UKMO UK 2km, and many others.

---

## Features

- **48 weather models** — global (ECMWF, GFS, ICON, GEM, JMA, BOM, CMA…) and regional high-resolution (AROME France HD, ICON-D2, ICON-2I Italy, HARMONIE, UKMO UK 2km, MeteoSwiss, GeoSphere Austria…)
- **44 hourly sensor variables** — temperature, humidity, dew point, precipitation, radiation, evapotranspiration, soil temperature & moisture, CAPE, wind at multiple heights, visibility, and more
- **26 daily sensor variables** — max/min/mean temperature, precipitation sums, UV index, sunrise/sunset, sunshine duration, dominant wind…
- **15 current-condition sensor variables** — real-time values updated on every fetch
- **`weather` entity** with hourly (48 h) and daily (14 d) forecast — usable in the standard HA weather card and automations
- **Configurable update interval** (minimum 15 min), forecast window (1–16 days), and past-days lookback (0–92 days)
- Each sensor exposes a **`forecast` attribute** with the upcoming values (48 h for hourly, 14 d for daily)
- Fully reconfigurable after setup via the **Options flow**

---

## Requirements

- Home Assistant Core **2026.10.2** is the targeted support baseline.
  Older releases are not supported by this fork; later versions are not yet verified.
- HACS installed for the custom-repository path below (manual installation remains available).
- Internet access to `api.open-meteo.com` (free, no API key required for personal use)

### Validation and readiness

This personal fork is being prepared for **HACS custom-repository installation**,
not submission to the HACS default store. The target system is HAOS 18.3 with
Core 2026.10.2. Hosted tests exercise the real Core package with mocked API
responses; they do not certify HAOS/Supervisor behavior or a live installation.
Check the [Validate workflow](https://github.com/JohanDeWeerdtMSFT/ha-open-meteo-advanced/actions/workflows/validate.yaml)
on the exact commit before installing.

The workflow runs Home Assistant hassfest, HACS validation, and focused tests
against `homeassistant==2026.10.2` on Python 3.14 (Core requires at least 3.14.2).
It never substitutes another Core version if the target is unavailable.
HACS's `brands` and `license` publication checks are explicitly excluded:
there are no brand assets and the inherited license grant is unverified
([license blocker](https://github.com/JohanDeWeerdtMSFT/ha-open-meteo-advanced/issues/2)).
A green scoped workflow is **not** full publication/release approval.
No release is published by this work.

---

## Installation

### Manual

1. Download or clone this repository.
2. Copy the `custom_components/open_meteo_advanced/` folder into your HA configuration directory:
   ```
   <config>/custom_components/open_meteo_advanced/
   ```
3. Restart Home Assistant.
4. Go to **Settings → Devices & Services → + Add Integration** and search for **Open-Meteo Advanced**.

### HACS custom repository (this fork)

1. Wait for the linked installation-readiness PR to be reviewed and merged.
   HACS normally downloads the default branch; adding this URL before the PR
   lands will still download the old code. Do not treat a successful branch CI
   run as evidence that `master` already contains the changes.
2. Create a Home Assistant backup, download it off-device, and note the current
   integration version/commit. Agree on a maintenance window for the restart.
3. Open **HACS**, select the top-right menu, then **Custom repositories**.
4. Add `https://github.com/JohanDeWeerdtMSFT/ha-open-meteo-advanced`
   with type/category **Integration**. Do not add the upstream repository
   expecting this fork's changes.
5. Search for **Open-Meteo Advanced**, open it and choose **Download**.
   Without published releases HACS downloads the default branch commit; record
   that commit. The integration's `manifest.json` version alone does not identify it.
6. At the agreed time, restart Home Assistant. Then open
   **Settings → Devices & Services → Add Integration → Open-Meteo Advanced**.
   Start with `best_match`, your coordinates and a small set of variables.
7. Verify that the new sensors have values, that sunrise/sunset timestamps work,
   and that `weather.get_forecasts` returns daily/hourly forecasts for the new
   weather entity. Check the integration logs for setup/API errors.

This installs only `custom_components/open_meteo_advanced`. It must **not**
replace `open_meteo`, remove the built-in integration, or rename its existing
entities. Keep current dashboards/automations on the built-in entities until
the new ones have been checked. No live installation or restart is performed
by the preparation/CI workflow.

### Updates and rollback

Before updating, back up Home Assistant and retain the currently installed
`custom_components/open_meteo_advanced` folder plus its HACS commit/version.
Read the diff and require a passing workflow for the new commit. Use HACS's
**Update**/**Redownload** control, then restart in a coordinated window.
HACS handles updates to this fork only; it does not follow upstream changes
automatically. There are currently no published releases to select as a
known-good rollback version.

If an update fails, do not delete/recreate the config entry (its ID determines
entity unique IDs). If HACS offers the recorded known-good release, select it
via **Redownload**. For an untagged/default-branch installation, restore the
saved integration folder or the pre-update Home Assistant backup instead.
Restart after restoring and check the logs and existing entity IDs. Restore a
full backup when Core/configuration has also changed. Reverting this PR in Git
alone does not roll back files already installed on Home Assistant.

For a failed initial install, remove only this custom integration's entry and
files through the HA/HACS UI and restart at an agreed time; leave the built-in
Open-Meteo integration untouched.

### Development checks

Use the GitHub-hosted **Validate** workflow rather than installing Home Assistant
or running heavy tests on Windows ARM. Enable Actions for this fork if GitHub
shows them disabled. The equivalent test command on a compatible Linux/Python
3.14 runner is `python -m pip install -r requirements_test.txt`, followed by
`python -m pytest -q`. Tests disallow external network access.

Authoritative references:
[HACS custom repositories](https://www.hacs.xyz/docs/faq/custom_repositories/),
[integration requirements](https://www.hacs.xyz/docs/publish/integration/),
[HACS validation action](https://www.hacs.xyz/docs/publish/action/),
[Home Assistant manifest](https://developers.home-assistant.io/docs/creating_integration_manifest/),
and [weather forecast contract](https://developers.home-assistant.io/docs/core/entity/weather/).

---

## Configuration

The integration is configured through a five-step UI wizard.

### Step 1 — Location & Model

| Field | Description |
|-------|-------------|
| **Location name** | Display name for the device (e.g. `Florence`) |
| **Latitude / Longitude** | Coordinates of the location to monitor |
| **Weather model** | One of 48 available models (see list below) |
| **Create weather entity** | Toggle to also create a `weather.*` entity |

### Step 2 — Timing

| Field | Default | Range |
|-------|---------|-------|
| **Update interval** | 60 min | 15 – 1440 min |
| **Forecast days** | 7 | 1 – 16 |
| **Past days to include** | 0 | 0 – 92 |

### Steps 3–5 — Variables

Enter variable names separated by commas. Leaving a field blank creates no sensors for that category.
Unknown names are rejected rather than silently discarded. Latitude must be
between -90 and 90, and longitude between -180 and 180.

- **Step 3** — Current variables (real-time)
- **Step 4** — Hourly variables
- **Step 5** — Daily variables

All settings can be changed at any time via **Settings → Devices & Services → Open-Meteo Advanced → Configure**.

---

## Available Variables

### Current
`temperature_2m` · `relative_humidity_2m` · `apparent_temperature` · `precipitation` · `rain` · `showers` · `snowfall` · `weather_code` · `cloud_cover` · `pressure_msl` · `surface_pressure` · `wind_speed_10m` · `wind_direction_10m` · `wind_gusts_10m` · `is_day`

### Hourly (selection)
`temperature_2m` · `dew_point_2m` · `apparent_temperature` · `relative_humidity_2m` · `precipitation` · `rain` · `showers` · `snowfall` · `snow_depth` · `precipitation_probability` · `weather_code` · `pressure_msl` · `surface_pressure` · `cloud_cover` · `cloud_cover_low` · `cloud_cover_mid` · `cloud_cover_high` · `wind_speed_10m/80m/120m/180m` · `wind_direction_10m/80m/120m/180m` · `wind_gusts_10m` · `shortwave_radiation` · `direct_radiation` · `direct_normal_irradiance` · `diffuse_radiation` · `global_tilted_irradiance` · `vapour_pressure_deficit` · `cape` · `evapotranspiration` · `et0_fao_evapotranspiration` · `freezing_level_height` · `visibility` · `soil_temperature_0/6/18/54cm` · `soil_moisture_0-1/1-3/3-9/9-27/27-81cm` · `is_day`

### Daily (selection)
`temperature_2m_max/mean/min` · `apparent_temperature_max/mean/min` · `precipitation_sum` · `rain_sum` · `showers_sum` · `snowfall_sum` · `precipitation_hours` · `precipitation_probability_max/mean/min` · `et0_fao_evapotranspiration` · `weather_code` · `sunrise` · `sunset` · `sunshine_duration` · `daylight_duration` · `wind_speed_10m_max` · `wind_gusts_10m_max` · `wind_direction_10m_dominant` · `shortwave_radiation_sum` · `uv_index_max` · `uv_index_clear_sky_max`

---

## Supported Weather Models

| Model | Coverage |
|-------|----------|
| `best_match` | Auto-selected best model for the location |
| `ecmwf_ifs_9km` / `ecmwf_ifs_025` | ECMWF IFS global |
| `ecmwf_aifs_025` | ECMWF AI-based forecast |
| `ncep_gfs_seamless` / `ncep_gfs_011` | NOAA GFS global |
| `ncep_hrrr_conus` | NOAA HRRR (USA high-res) |
| `ncep_gfs_graphcast` / `ncep_aigfs_025` | NOAA AI-based |
| `dwd_icon_seamless` / `dwd_icon_global` | DWD ICON global |
| `dwd_icon_eu` / `dwd_icon_d2` | DWD ICON Europe / Germany |
| `meteofrance_seamless` | Météo-France auto |
| `meteofrance_arpege_world` / `_europe` | Météo-France ARPEGE |
| `meteofrance_arome_france` / `_hd` | Météo-France AROME (high-res France) |
| `italia_meteo_arpae_icon_2i` | ARPAE ICON-2I (Italy 2 km) |
| `knmi_harmonie_arome_europe` / `_netherlands` | KNMI HARMONIE-AROME |
| `dmi_harmonie_arome_europe` | DMI HARMONIE-AROME |
| `metno_nordic_seamless` / `metno_nordic` | MET Norway Nordic |
| `ukmo_seamless` / `ukmo_global_10km` / `ukmo_uk_2km` | UK Met Office |
| `meteoswiss_seamless` / `_icon_ch1` / `_icon_ch2` | MeteoSwiss |
| `geosphere_seamless` / `geosphere_arome_austria` | GeoSphere Austria |
| `gem_seamless` / `gem_global` / `gem_regional` / `gem_hrdps_continental` | Environment Canada |
| `jma_seamless` / `jma_msm` / `jma_gsm` | JMA (Japan) |
| `kma_seamless` / `kma_ldps` / `kma_gdps` | KMA (Korea) |
| `bom_access_global` | BOM (Australia) |
| `cma_grapes_global` | CMA GRAPES (China) |

---

## Sensor Attributes

Every sensor exposes its upcoming values as a `forecast` attribute — useful in templates and automations.

**Hourly sensors** — next 48 hours:
```yaml
forecast:
  - time: "2026-05-12T15:00"
    value: 22.4
  - time: "2026-05-12T16:00"
    value: 23.1
  ...
```

**Daily sensors** — next 14 days:
```yaml
forecast:
  - time: "2026-05-12"
    value: 18.3
  - time: "2026-05-13"
    value: 21.0
  ...
```

---

## Weather Entity

When enabled, a `weather.<location_name>` entity is created. It supports:

- Current condition, temperature, humidity, pressure, wind, visibility, cloud cover
- **Hourly forecast** (48 h) — condition, temperature, wind, precipitation probability, precipitation, pressure, cloud cover, humidity
- **Daily forecast** (14 d) — condition, max/min temperature, dominant wind, precipitation sum, precipitation probability

The weather card in HA Lovelace will automatically show forecasts.

The required API variables for the weather entity are fetched **automatically** — no manual variable selection needed. If you also select those same variables as sensors, they are deduplicated into a single API call.

### WMO Code → HA Condition Mapping

| WMO | HA condition |
|-----|-------------|
| 0, 1 | `sunny` / `clear-night` |
| 2 | `partlycloudy` |
| 3 | `cloudy` |
| 45, 48 | `fog` |
| 51–55, 61–63, 80–81 | `rainy` |
| 56–57, 66–67 | `snowy-rainy` |
| 65, 82 | `pouring` |
| 71–77, 85–86 | `snowy` |
| 95 | `lightning` |
| 96, 99 | `hail` |

---

## Data Source

All weather data is fetched from the [Open-Meteo API](https://open-meteo.com/en/docs). The service is **free for non-commercial personal use** and does not require an API key.

---

## License and provenance

The inherited upstream README labels this project **MIT**. This fork originated
from [stilli00/ha-open-meteo-advanced](https://github.com/stilli00/ha-open-meteo-advanced)
at commit `f0479315f242e830da9806734ebb64fdd2dcad93`; the starting tree contains
no LICENSE file, full license grant or copyright notice. Existing attribution
is preserved, but this fork does not invent a rights holder, permission grant,
or replacement license text. Confirm the applicable license and required notices
with the upstream author before publishing a release or redistributing it as a
fully licensed package. The unresolved provenance is tracked in
[issue #2](https://github.com/JohanDeWeerdtMSFT/ha-open-meteo-advanced/issues/2).
