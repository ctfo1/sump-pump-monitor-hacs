from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import callback

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    coordinators = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for coordinator in coordinators.values():
        entities.extend([
            PumpBinary(coordinator, "pump_running", "Pump Running",
                       BinarySensorDeviceClass.RUNNING, "running"),
            PumpBinary(coordinator, "power_monitor_unavailable",
                       "Power Monitor Unavailable", BinarySensorDeviceClass.PROBLEM,
                       "power_monitor_unavailable"),
            PumpBinary(coordinator, "power_monitor_switched_off",
                       "Power Monitor Switched Off", BinarySensorDeviceClass.PROBLEM,
                       "power_monitor_switched_off"),
            PumpBinary(coordinator, "running_too_long", "Running Too Long",
                       BinarySensorDeviceClass.PROBLEM, "running_too_long"),
            PumpBinary(coordinator, "high_power_draw", "High Power Draw",
                       BinarySensorDeviceClass.PROBLEM, "high_power_draw"),
            PumpBinary(coordinator, "heavy_cycling", "Heavy Cycling",
                       BinarySensorDeviceClass.PROBLEM, "heavy_cycling"),
        ])
    async_add_entities(entities)


class PumpBinary(BinarySensorEntity):
    """Simple binary sensor backed by the pump coordinator."""

    _attr_should_poll = False

    def __init__(self, coordinator, key, name, device_class, state_key):
        self.coordinator = coordinator
        self.state_key = state_key
        self._attr_unique_id = f"{coordinator.pump_id}_{key}"
        self._attr_name = name
        self._attr_device_class = device_class
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.pump_id)},
            "name": coordinator.name,
            "manufacturer": "Sump Pump Monitor",
            "model": "Sump Pump",
        }
        self._remove_listener = None

    async def async_added_to_hass(self):
        self._remove_listener = self.coordinator.add_update_listener(
            self._handle_coordinator_update
        )
        self.async_on_remove(self._remove_listener)
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self):
        self.async_write_ha_state()

    @property
    def available(self):
        return True

    @property
    def is_on(self):
        try:
            value = self.coordinator.get_entity_value(self.state_key)
        except Exception:
            return False
        return bool(value)
