"""Config flow for WLED Progress Bar integration.

Two flows are provided:
1. ConfigFlow  – initial setup (host + source entity + LED range).
2. OptionsFlow – live reconfiguration of all visual and operational settings.

The split keeps first-time setup minimal while allowing deep customisation
after the entry is created.
"""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_BACKGROUND_COLOR,
    CONF_BACKGROUND_OFF,
    CONF_BRIGHTNESS,
    CONF_ENTITY_ID,
    CONF_GRADIENT_END_COLOR,
    CONF_GRADIENT_MODE,
    CONF_GRADIENT_START_COLOR,
    CONF_LED_COUNT,
    CONF_LED_END,
    CONF_LED_START,
    CONF_MAX_VALUE,
    CONF_MIN_VALUE,
    CONF_NEAR_COMPLETE_COLOR,
    CONF_NEAR_COMPLETE_THRESHOLD,
    CONF_PROGRESS_COLOR,
    CONF_REVERSE,
    CONF_UPDATE_INTERVAL,
    DEFAULT_BACKGROUND_COLOR,
    DEFAULT_BACKGROUND_OFF,
    DEFAULT_BRIGHTNESS,
    DEFAULT_GRADIENT_END_COLOR,
    DEFAULT_GRADIENT_MODE,
    DEFAULT_GRADIENT_START_COLOR,
    DEFAULT_LED_COUNT,
    DEFAULT_MAX_VALUE,
    DEFAULT_MIN_VALUE,
    DEFAULT_NEAR_COMPLETE_COLOR,
    DEFAULT_NEAR_COMPLETE_THRESHOLD,
    DEFAULT_PROGRESS_COLOR,
    DEFAULT_REVERSE,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    WLED_JSON_INFO_PATH,
)

_LOGGER = logging.getLogger(__name__)


def _rgb_str_validator(value: str) -> str:
    """Validate that a string is in 'r,g,b' form with each part 0-255."""
    try:
        parts = [int(p.strip()) for p in str(value).split(",")]
    except ValueError as exc:
        raise vol.Invalid("Use 'r,g,b' format, e.g. '255,128,0'") from exc
    if len(parts) != 3 or not all(0 <= p <= 255 for p in parts):
        raise vol.Invalid("Each component must be 0–255")
    return value


async def _async_test_wled_connection(host: str) -> dict[str, Any] | None:
    """Try to reach WLED /json/info and return the info dict, or None on failure.

    NOTE: WLED's /json/info returns a JSON object with keys such as 'ver'
    (firmware version) and 'leds' (LED configuration). We only use this to
    validate connectivity – we do not depend on any specific key being present.
    """
    url = f"http://{host.rstrip('/')}{WLED_JSON_INFO_PATH}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    return await resp.json()
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("WLED connection test failed for %s: %s", host, exc)
    return None


# ── Initial config flow ────────────────────────────────────────────────────────


class WLEDProgressBarConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial setup config flow."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> WLEDProgressBarOptionsFlow:
        return WLEDProgressBarOptionsFlow(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            entity_id = user_input[CONF_ENTITY_ID]

            # Validate WLED host reachability.
            info = await _async_test_wled_connection(host)
            if info is None:
                errors["base"] = "cannot_connect"
            else:
                # Attempt to auto-detect LED count from WLED info.
                # WLED /json/info returns {"leds": {"count": N, ...}} in most
                # firmware versions ≥0.10. Fall back to user default if absent.
                try:
                    detected_count = int(info["leds"]["count"])
                except (KeyError, TypeError, ValueError):
                    detected_count = DEFAULT_LED_COUNT

                # Unique ID = host (one entry per WLED device).
                await self.async_set_unique_id(host)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"WLED Progress Bar ({host})",
                    data={
                        CONF_HOST: host,
                        CONF_ENTITY_ID: entity_id,
                    },
                    options={
                        CONF_MIN_VALUE: DEFAULT_MIN_VALUE,
                        CONF_MAX_VALUE: DEFAULT_MAX_VALUE,
                        CONF_LED_COUNT: detected_count,
                        CONF_LED_START: 0,
                        CONF_LED_END: detected_count - 1,
                        CONF_BACKGROUND_OFF: DEFAULT_BACKGROUND_OFF,
                        CONF_BACKGROUND_COLOR: DEFAULT_BACKGROUND_COLOR,
                        CONF_PROGRESS_COLOR: DEFAULT_PROGRESS_COLOR,
                        CONF_NEAR_COMPLETE_THRESHOLD: DEFAULT_NEAR_COMPLETE_THRESHOLD,
                        CONF_NEAR_COMPLETE_COLOR: DEFAULT_NEAR_COMPLETE_COLOR,
                        CONF_GRADIENT_MODE: DEFAULT_GRADIENT_MODE,
                        CONF_GRADIENT_START_COLOR: DEFAULT_GRADIENT_START_COLOR,
                        CONF_GRADIENT_END_COLOR: DEFAULT_GRADIENT_END_COLOR,
                        CONF_REVERSE: DEFAULT_REVERSE,
                        CONF_BRIGHTNESS: DEFAULT_BRIGHTNESS,
                        CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_ENTITY_ID): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor", "input_number", "number"])
                ),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)


# ── Options flow ───────────────────────────────────────────────────────────────


class WLEDProgressBarOptionsFlow(OptionsFlow):
    """Handle live reconfiguration of all options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry
        self._options = dict(config_entry.options)

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Step 1: scaling and LED range."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Basic cross-field validation.
            if user_input[CONF_MIN_VALUE] >= user_input[CONF_MAX_VALUE]:
                errors["base"] = "min_gte_max"
            elif user_input[CONF_LED_START] >= user_input[CONF_LED_END]:
                errors["base"] = "led_start_gte_end"
            else:
                self._options.update(user_input)
                return await self.async_step_colors()

        opts = self._options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_ENTITY_ID, default=self._config_entry.data.get(CONF_ENTITY_ID, "")
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor", "input_number", "number"])
                ),
                vol.Required(
                    CONF_MIN_VALUE, default=opts.get(CONF_MIN_VALUE, DEFAULT_MIN_VALUE)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(mode=selector.NumberSelectorMode.BOX, step=0.1)
                ),
                vol.Required(
                    CONF_MAX_VALUE, default=opts.get(CONF_MAX_VALUE, DEFAULT_MAX_VALUE)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(mode=selector.NumberSelectorMode.BOX, step=0.1)
                ),
                vol.Required(
                    CONF_LED_COUNT, default=opts.get(CONF_LED_COUNT, DEFAULT_LED_COUNT)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1, max=1000, mode=selector.NumberSelectorMode.BOX, step=1
                    )
                ),
                vol.Required(
                    CONF_LED_START, default=opts.get(CONF_LED_START, 0)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0, max=999, mode=selector.NumberSelectorMode.BOX, step=1
                    )
                ),
                vol.Required(
                    CONF_LED_END,
                    default=opts.get(CONF_LED_END, opts.get(CONF_LED_COUNT, DEFAULT_LED_COUNT) - 1),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1, max=1000, mode=selector.NumberSelectorMode.BOX, step=1
                    )
                ),
                vol.Required(
                    CONF_REVERSE, default=opts.get(CONF_REVERSE, DEFAULT_REVERSE)
                ): selector.BooleanSelector(),
                vol.Required(
                    CONF_UPDATE_INTERVAL,
                    default=opts.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=3600,
                        mode=selector.NumberSelectorMode.BOX,
                        step=1,
                        unit_of_measurement="s",
                    )
                ),
                vol.Required(
                    CONF_BRIGHTNESS, default=opts.get(CONF_BRIGHTNESS, DEFAULT_BRIGHTNESS)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0, max=255, mode=selector.NumberSelectorMode.SLIDER, step=1
                    )
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)

    async def async_step_colors(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Step 2: colour configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                for key in (
                    CONF_PROGRESS_COLOR,
                    CONF_BACKGROUND_COLOR,
                    CONF_NEAR_COMPLETE_COLOR,
                    CONF_GRADIENT_START_COLOR,
                    CONF_GRADIENT_END_COLOR,
                ):
                    if key in user_input:
                        _rgb_str_validator(user_input[key])
            except vol.Invalid as exc:
                errors["base"] = "invalid_rgb"
                _LOGGER.warning("Invalid RGB value in options: %s", exc)
            else:
                self._options.update(user_input)
                # Persist updated options and re-trigger a coordinator reload.
                return self.async_create_entry(title="", data=self._options)

        opts = self._options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_PROGRESS_COLOR,
                    default=opts.get(CONF_PROGRESS_COLOR, DEFAULT_PROGRESS_COLOR),
                ): str,
                vol.Required(
                    CONF_BACKGROUND_OFF,
                    default=opts.get(CONF_BACKGROUND_OFF, DEFAULT_BACKGROUND_OFF),
                ): selector.BooleanSelector(),
                vol.Required(
                    CONF_BACKGROUND_COLOR,
                    default=opts.get(CONF_BACKGROUND_COLOR, DEFAULT_BACKGROUND_COLOR),
                ): str,
                vol.Required(
                    CONF_NEAR_COMPLETE_THRESHOLD,
                    default=opts.get(CONF_NEAR_COMPLETE_THRESHOLD, DEFAULT_NEAR_COMPLETE_THRESHOLD),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=100,
                        mode=selector.NumberSelectorMode.SLIDER,
                        step=1,
                        unit_of_measurement="%",
                    )
                ),
                vol.Required(
                    CONF_NEAR_COMPLETE_COLOR,
                    default=opts.get(CONF_NEAR_COMPLETE_COLOR, DEFAULT_NEAR_COMPLETE_COLOR),
                ): str,
                vol.Required(
                    CONF_GRADIENT_MODE, default=opts.get(CONF_GRADIENT_MODE, DEFAULT_GRADIENT_MODE)
                ): selector.BooleanSelector(),
                vol.Required(
                    CONF_GRADIENT_START_COLOR,
                    default=opts.get(CONF_GRADIENT_START_COLOR, DEFAULT_GRADIENT_START_COLOR),
                ): str,
                vol.Required(
                    CONF_GRADIENT_END_COLOR,
                    default=opts.get(CONF_GRADIENT_END_COLOR, DEFAULT_GRADIENT_END_COLOR),
                ): str,
            }
        )

        return self.async_show_form(step_id="colors", data_schema=schema, errors=errors)
