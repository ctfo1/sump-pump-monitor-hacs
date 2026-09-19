from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import UnitOfPower, UnitOfTime
from homeassistant.core import callback

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    coordinators = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for coordinator in coordinators.values():
        entities.extend([
            PumpSensor(coordinator, "power", "Pump Power", UnitOfPower.WATT,
                       lambda c: c._power(), SensorDeviceClass.POWER, True),
            PumpSensor(coordinator, "current_run_duration", "Current Run Duration",
                       UnitOfTime.SECONDS, lambda c: c.current_run_seconds),
            PumpSensor(coordinator, "last_cycle_duration", "Last Cycle Duration",
                       UnitOfTime.SECONDS, lambda c: c.last_cycle_duration),
            PumpSensor(coordinator, "average_cycle_duration", "Average Cycle Duration",
                       UnitOfTime.SECONDS, lambda c: c.average_cycle_duration),
            PumpSensor(coordinator, "last_cycle_average_power", "Last Cycle Average Power",
                       UnitOfPower.WATT, lambda c: c.state.get("last_run_avg_power"),
                       SensorDeviceClass.POWER),
            PumpSensor(coordinator, "last_cycle_peak_power", "Last Cycle Peak Power",
                       UnitOfPower.WATT, lambda c: c.state.get("last_run_peak_power"),
                       SensorDeviceClass.POWER),
            PumpSensor(coordinator, "historical_average_power", "Historical Average Power",
                       UnitOfPower.WATT, lambda c: c.historical_average_power,
                       SensorDeviceClass.POWER),
            PumpSensor(coordinator, "cycles_24h", "Cycles — 24 Hours",
                       None, lambda c: c.cycles_24h),
            PumpSensor(coordinator, "runtime_24h", "Runtime — 24 Hours",
                       UnitOfTime.SECONDS, lambda c: c.runtime_24h),
            PumpSensor(coordinator, "last_cycle_start", "Last Cycle Start",
                       None, lambda c: c.last_cycle_start_datetime,
                       SensorDeviceClass.TIMESTAMP),
            PumpSensor(coordinator, "last_cycle_end", "Last Cycle End",
                       None, lambda c: c.last_cycle_end_datetime,
                       SensorDeviceClass.TIMESTAMP),
        ])
    async_add_entities(entities)


class PumpSensor(SensorEntity):
    """A sensor backed directly by a PumpCoordinator."""

    _attr_should_poll = False

    def __init__(self, coordinator, key, name, unit, fn,
                 device_class=None, requires_power=False):
        self.c = coordinator
        self._fn = fn
        self._requires_power = requires_power
        self._attr_unique_id = f"{coordinator.pump_id}_{key}"
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.pump_id)},
            "name": coordinator.name,
            "manufacturer": "Sump Pump Monitor",
            "model": "Sump Pump",
        }
        self._remove_listener = None

    async def async_added_to_hass(self):
        self._remove_listener = self.c.add_update_listener(self._handle_coordinator_update)
        self.async_on_remove(self._remove_listener)

    @callback
    def _handle_coordinator_update(self):
        self.async_write_ha_state()

    @property
    def available(self):
        if self._requires_power:
            return self.c.sensor_available
        return True

    @property
    def native_value(self):
        return self._fn()
