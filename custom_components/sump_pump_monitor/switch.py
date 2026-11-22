from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.exceptions import HomeAssistantError

from .const import CONF_POWER_SWITCH, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the per-pump power-monitor controls."""
    coordinators = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            PowerMonitorControlSwitch(coordinator)
            for coordinator in coordinators.values()
            if coordinator.data.get(CONF_POWER_SWITCH)
        ]
    )


class PowerMonitorControlSwitch(SwitchEntity):
    """Expose the configured smart-plug switch as a control on the pump device."""

    _attr_should_poll = False
    _attr_icon = "mdi:power"

    def __init__(self, coordinator):
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.pump_id}_power_monitor_control"
        self._attr_name = "Power Monitor Control"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.pump_id)},
            "name": coordinator.name,
            "manufacturer": "Sump Pump Monitor",
            "model": "Sump Pump",
        }
        self._remove_update_listener = None

    @property
    def available(self) -> bool:
        """Remain visible, but unavailable, if the configured switch is offline."""
        entity_id = self.coordinator.power_switch
        if not entity_id:
            return False
        state = self.hass.states.get(entity_id)
        return bool(
            state
            and state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE)
        )

    @property
    def is_on(self) -> bool | None:
        """Return the live state of the configured switch."""
        entity_id = self.coordinator.power_switch
        state = self.hass.states.get(entity_id) if entity_id else None
        if not state or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return None
        return state.state == STATE_ON

    async def async_added_to_hass(self) -> None:
        """Subscribe to coordinator updates so the toggle mirrors the real switch."""
        await super().async_added_to_hass()
        self._remove_update_listener = self.coordinator.add_update_listener(
            self.async_write_ha_state
        )

    async def async_will_remove_from_hass(self) -> None:
        """Remove the coordinator update listener."""
        if self._remove_update_listener:
            self._remove_update_listener()
            self._remove_update_listener = None
        await super().async_will_remove_from_hass()

    async def async_turn_on(self, **kwargs) -> None:
        await self._async_set_switch("turn_on")

    async def async_turn_off(self, **kwargs) -> None:
        await self._async_set_switch("turn_off")

    async def _async_set_switch(self, service: str) -> None:
        """Forward a user command to the switch entity selected in pump config."""
        entity_id = self.coordinator.power_switch
        if not entity_id:
            return
        try:
            await self.hass.services.async_call(
                "switch",
                service,
                {"entity_id": entity_id},
                blocking=True,
            )
        except HomeAssistantError:
            _LOGGER.exception(
                "Unable to %s configured power monitor switch %s for %s",
                service,
                entity_id,
                self.coordinator.name,
            )
