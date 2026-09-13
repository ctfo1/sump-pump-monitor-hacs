from homeassistant.components.number import NumberEntity

from .const import *


async def async_setup_entry(hass, entry, async_add_entities):
    coordinators = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for coordinator in coordinators.values():
        entities.extend([
            ConfigNumber(coordinator, CONF_RUNNING_WATTS, "Running Wattage", 1, 500, 1),
            ConfigNumber(coordinator, CONF_ALERT_MULTIPLIER, "Alert Multiplier", 1, 10, .1),
            ConfigNumber(coordinator, CONF_ALERT_MIN_MINUTES, "Alert Minimum", 1, 1440, 1),
            ConfigNumber(coordinator, CONF_ALERT_MAX_MINUTES, "Alert Maximum", 1, 2880, 1),
            ConfigNumber(coordinator, CONF_MAX_RUN_SECONDS, "Maximum Run Duration", 1, 3600, 1),
            ConfigNumber(coordinator, CONF_INTERVAL_CHANGE_PERCENT, "Interval Change Percent", 1, 100, 1),
            ConfigNumber(coordinator, CONF_RESUME_AFTER_HOURS, "Resume After", 1, 720, 1),
            ConfigNumber(coordinator, CONF_SENSOR_OUTAGE_MINUTES, "Sensor Outage Delay", 1, 60, 1),
        ])
    async_add_entities(entities)


class ConfigNumber(NumberEntity):
    def __init__(self, coordinator, key, name, lo, hi, step):
        self.c = coordinator
        self.key = key
        self._attr_unique_id = f"{coordinator.pump_id}_{key}"
        self._attr_name = name
        self._attr_native_min_value = lo
        self._attr_native_max_value = hi
        self._attr_native_step = step
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.pump_id)},
            "name": coordinator.name,
            "manufacturer": "Sump Pump Monitor",
            "model": "Sump Pump",
        }

    @property
    def native_value(self):
        return float(self.c.data[self.key])

    async def async_set_native_value(self, value):
        self.c.data[self.key] = float(value)
        pumps = dict(self.c.entry.options.get(CONF_PUMPS, self.c.entry.data.get(CONF_PUMPS, {})))
        pump = dict(pumps[self.c.pump_id])
        pump[self.key] = float(value)
        pumps[self.c.pump_id] = pump
        self.c.hass.config_entries.async_update_entry(self.c.entry, options={CONF_PUMPS: pumps})
        await self.c._store.async_save(self.c.state)
