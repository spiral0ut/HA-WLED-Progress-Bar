"""Switch platform for WLED Progress Bar.

Provides a single on/off switch per config entry:
  - ON:  snapshots current WLED state, then starts progress bar rendering.
  - OFF: stops rendering and restores WLED to the state captured at turn-on
         (falls back to clearing the bar if no snapshot is available, e.g.
         after an HA restart with the switch already on).
"""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import COORDINATOR, DOMAIN
from .coordinator import WLEDProgressBarCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: WLEDProgressBarCoordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
    async_add_entities([WLEDProgressBarSwitch(coordinator, entry)])


class WLEDProgressBarSwitch(RestoreEntity, SwitchEntity):
    """Switch that enables / disables WLED progress bar rendering."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_translation_key = "active"
    _attr_icon = "mdi:led-strip-variant"

    def __init__(
        self,
        coordinator: WLEDProgressBarCoordinator,
        entry: ConfigEntry,
    ) -> None:
        self._coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_active"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="WLED",
            model="Progress Bar",
            configuration_url=f"http://{entry.data.get('host', '')}",
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        # Default ON for brand-new installs (no saved state yet).
        should_be_on = last is None or last.state == "on"

        if should_be_on:
            await self._coordinator.async_save_wled_state()
            self._coordinator.set_enabled(True)
            await self._coordinator.async_refresh()
        # If restoring to OFF, the coordinator stays disabled (already False).

    @property
    def is_on(self) -> bool:
        return self._coordinator.is_enabled

    async def async_turn_on(self, **kwargs) -> None:
        await self._coordinator.async_save_wled_state()
        self._coordinator.set_enabled(True)
        await self._coordinator.async_refresh()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        self._coordinator.set_enabled(False)
        await self._coordinator.async_restore_wled_state()
        self.async_write_ha_state()
