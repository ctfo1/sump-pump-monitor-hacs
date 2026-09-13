from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    coordinators = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for coordinator in coordinators.values():
        entities.extend([
            PumpBinary(coordinator, "running", "Pump Running", BinarySensorDeviceClass.RUNNING, lambda c=coordinator: c.state.get("running", False)),
            PumpBinary(coordinator, "sensor_available", "Power Sensor Available", BinarySensorDeviceClass.CONNECTIVITY, lambda c=coordinator: c.sensor_available),
        ])
    async_add_entities(entities)


class PumpBinary(BinarySensorEntity):
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
        return self._fn()
