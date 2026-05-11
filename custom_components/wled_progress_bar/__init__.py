"""WLED Progress Bar – Home Assistant custom integration.

This integration watches a numeric Home Assistant entity and renders its
current value as a visual progress bar on a WLED LED strip using the
WLED JSON API (https://kno.wled.ge/interfaces/json-api/).

Architecture:
  - WLEDProgressBarCoordinator  (coordinator.py)  polls the HA state machine
    at a configurable interval, recalculates the LED layout, and pushes the
    result to WLED via aiohttp.
  - WLEDProgressBarSensor       (sensor.py)        exposes the current percent
    value so it can be used in automations / dashboards.
  - Config/Options flow          (config_flow.py)   handles initial setup and
    live reconfiguration from the UI.
  - Services                    (this file)         provide render_now,
    set_colors, clear_bar, and turn_off_background.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import (
    COORDINATOR,
    DOMAIN,
    SERVICE_CLEAR_BAR,
    SERVICE_RENDER_NOW,
    SERVICE_SET_COLORS,
    SERVICE_TURN_OFF_BACKGROUND,
    CONF_PROGRESS_COLOR,
    CONF_BACKGROUND_COLOR,
    CONF_NEAR_COMPLETE_COLOR,
    CONF_BRIGHTNESS,
)
from .coordinator import WLEDProgressBarCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up WLED Progress Bar from a config entry."""
    coordinator = WLEDProgressBarCoordinator(hass, entry)

    # Perform an initial refresh so entities have data immediately.
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        COORDINATOR: coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register integration-level services (only once, using entry check).
    _register_services(hass)

    # Re-register options listener so a live options change propagates.
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        # If no entries remain, remove service registrations.
        if not hass.data[DOMAIN]:
            for service in (
                SERVICE_RENDER_NOW,
                SERVICE_SET_COLORS,
                SERVICE_CLEAR_BAR,
                SERVICE_TURN_OFF_BACKGROUND,
            ):
                hass.services.async_remove(DOMAIN, service)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update – reload the entry so new values take effect."""
    await hass.config_entries.async_reload(entry.entry_id)


# ── Service schemas ────────────────────────────────────────────────────────────

def _rgb_str(value: str) -> str:
    """Validate 'r,g,b' string where each component is 0-255."""
    try:
        parts = [int(p.strip()) for p in value.split(",")]
    except ValueError as exc:
        raise vol.Invalid("Expected 'r,g,b' format") from exc
    if len(parts) != 3 or not all(0 <= p <= 255 for p in parts):
        raise vol.Invalid("Each RGB component must be an integer 0–255")
    return value


_RENDER_NOW_SCHEMA = vol.Schema({})

_SET_COLORS_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_PROGRESS_COLOR): _rgb_str,
        vol.Optional(CONF_BACKGROUND_COLOR): _rgb_str,
        vol.Optional(CONF_NEAR_COMPLETE_COLOR): _rgb_str,
        vol.Optional(CONF_BRIGHTNESS): vol.All(int, vol.Range(min=0, max=255)),
    }
)

_CLEAR_BAR_SCHEMA = vol.Schema({})
_TURN_OFF_BG_SCHEMA = vol.Schema({})


def _register_services(hass: HomeAssistant) -> None:
    """Register integration-level services (idempotent)."""
    if hass.services.has_service(DOMAIN, SERVICE_RENDER_NOW):
        return  # already registered

    async def _handle_render_now(call: ServiceCall) -> None:
        """Trigger an immediate push to WLED for all configured entries."""
        entries = hass.data.get(DOMAIN, {})
        if not entries:
            raise HomeAssistantError("No WLED Progress Bar entries configured")
        for entry_data in entries.values():
            coord: WLEDProgressBarCoordinator = entry_data[COORDINATOR]
            await coord.async_render_now()

    async def _handle_set_colors(call: ServiceCall) -> None:
        """Override colours and push to WLED for all entries."""
        entries = hass.data.get(DOMAIN, {})
        if not entries:
            raise HomeAssistantError("No WLED Progress Bar entries configured")
        overrides: dict[str, Any] = {
            k: v
            for k, v in call.data.items()
            if k in (CONF_PROGRESS_COLOR, CONF_BACKGROUND_COLOR, CONF_NEAR_COMPLETE_COLOR, CONF_BRIGHTNESS)
        }
        for entry_data in entries.values():
            coord: WLEDProgressBarCoordinator = entry_data[COORDINATOR]
            await coord.async_render_now(overrides=overrides)

    async def _handle_clear_bar(call: ServiceCall) -> None:
        """Turn all LEDs in the configured segment off."""
        entries = hass.data.get(DOMAIN, {})
        if not entries:
            raise HomeAssistantError("No WLED Progress Bar entries configured")
        for entry_data in entries.values():
            coord: WLEDProgressBarCoordinator = entry_data[COORDINATOR]
            await coord.async_clear_bar()

    async def _handle_turn_off_background(call: ServiceCall) -> None:
        """Set background LEDs to off without affecting progress LEDs."""
        entries = hass.data.get(DOMAIN, {})
        if not entries:
            raise HomeAssistantError("No WLED Progress Bar entries configured")
        for entry_data in entries.values():
            coord: WLEDProgressBarCoordinator = entry_data[COORDINATOR]
            await coord.async_render_now(overrides={CONF_BACKGROUND_COLOR: "0,0,0"})

    hass.services.async_register(DOMAIN, SERVICE_RENDER_NOW, _handle_render_now, schema=_RENDER_NOW_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SET_COLORS, _handle_set_colors, schema=_SET_COLORS_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_CLEAR_BAR, _handle_clear_bar, schema=_CLEAR_BAR_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_TURN_OFF_BACKGROUND, _handle_turn_off_background, schema=_TURN_OFF_BG_SCHEMA)
