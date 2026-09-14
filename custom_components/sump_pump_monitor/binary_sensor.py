from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    coordinators = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for coordinator in coordinators.values():
        entities.extend(
            [
                PumpBinary(coordinator, "running", "Pump Running", BinarySensorDeviceClass.RUNNING, lambda c: c.state.get("running", False)),
                PumpBinary(coordinator, "power_monitor_unavailable", "Power Monitor Unavailable", BinarySensorDeviceClass.PROBLEM, lambda c: c.power_monitor_unavailable),
                PumpBinary(coordinator, "power_monitor_switched_off", "Power Monitor Switched Off", BinarySensorDeviceClass.PROBLEM, lambda c: c.power_monitor_switched_off),
                PumpBinary(coordinator, "running_too_long", "Running Too Long", BinarySensorDeviceClass.PROBLEM, lambda c: c.running_too_long),
                PumpBinary(coordinator, "high_power", "High Power Draw", BinarySensorDeviceClass.PROBLEM, lambda c: c.high_power),
                PumpBinary(coordinator, "heavy_cycling", "Heavy Cycling", BinarySensorDeviceClass.PROBLEM, lambda c: c.heavy_cycling),
            ]
        )
    async_add_entities(entities)


class PumpBinary(BinarySensorEntity):
    _attr_should_poll = True

    def __init__(self, coordinator, key, name, device_class, fn):
        self.c = coordinator
        self._fn = fn
        self._attr_unique_id = f"{coordinator.pump_id}_{key}"
        self._attr_name = name
        self._attr_device_class = device_class
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.pump_id)},
            "name": coordinator.name,
            "manufacturer": "Sump Pump Monitor",
            "model": "Sump Pump",
        }

    @property
    def is_on(self):
        return bool(self._fn())
