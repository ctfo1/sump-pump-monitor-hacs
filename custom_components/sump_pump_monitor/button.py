from __future__ import annotations

from homeassistant.components.button import ButtonEntity

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    coordinators = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [TestNotificationButton(coordinator) for coordinator in coordinators.values()]
    )


class TestNotificationButton(ButtonEntity):
    """Send a test notification using the configured target."""

    _attr_icon = "mdi:bell-check-outline"
    _attr_should_poll = False

    def __init__(self, coordinator):
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.pump_id}_test_notification"
        self._attr_name = "Test Notification"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.pump_id)},
            "name": coordinator.name,
            "manufacturer": "Sump Pump Monitor",
            "model": "Sump Pump",
        }

    async def async_press(self) -> None:
        await self.coordinator.async_send_test_notification()
