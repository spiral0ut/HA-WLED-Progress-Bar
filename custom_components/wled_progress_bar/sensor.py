"""Sensor entity for WLED Progress Bar.

Exposes the current progress percentage (0–100) as a HA sensor so it can
be used in dashboards, automations, and the custom Lovelace card.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import COORDINATOR, DOMAIN
from .coordinator import WLEDProgressBarCoordinator

_LOGGER = logging.getLogger(__name__)

SENSOR_DESCRIPTION = SensorEntityDescription(
    key="progress_percent",
    translation_key="progress_percent",
    native_unit_of_measurement=PERCENTAGE,
    state_class=SensorStateClass.MEASUREMENT,
    icon="mdi:led-strip-variant",
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the WLED Progress Bar sensor."""
    coordinator: WLEDProgressBarCoordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
    async_add_entities([WLEDProgressBarSensor(coordinator, entry)])


class WLEDProgressBarSensor(CoordinatorEntity[WLEDProgressBarCoordinator], SensorEntity):
    """Sensor exposing the current progress percentage."""

    entity_description = SENSOR_DESCRIPTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WLEDProgressBarCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_progress_percent"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="WLED",
            model="Progress Bar",
            configuration_url=f"http://{entry.data.get('host', '')}",
        )

    @property
    def native_value(self) -> float | None:
        """Return the current progress as a percentage."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("percent")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose additional diagnostic attributes."""
        data = self.coordinator.data or {}
        return {
            "source_value": data.get("value"),
            "filled_leds": data.get("filled"),
            "total_leds": data.get("total"),
        }
