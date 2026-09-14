from __future__ import annotations

from datetime import datetime, timezone

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import UnitOfPower, UnitOfTime

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    coordinators = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for coordinator in coordinators.values():
        entities.extend(
            [
                PumpSensor(coordinator, "power", "Pump Power", UnitOfPower.WATT, lambda c: c._power()),
                PumpSensor(coordinator, "current_run_duration", "Current Run Duration", UnitOfTime.SECONDS, lambda c: c.current_run_seconds),
                PumpSensor(coordinator, "last_cycle_duration", "Last Cycle Duration", UnitOfTime.SECONDS, lambda c: c.last_cycle_duration),
                PumpSensor(coordinator, "average_cycle_duration", "Average Cycle Duration", UnitOfTime.SECONDS, lambda c: c.average_cycle_duration),
                PumpSensor(coordinator, "average_running_power", "Average Running Power", UnitOfPower.WATT, lambda c: c.state.get("last_run_avg_power")),
                PumpSensor(coordinator, "peak_running_power", "Peak Running Power", UnitOfPower.WATT, lambda c: c.state.get("last_run_peak_power")),
                PumpSensor(coordinator, "historical_average_power", "Historical Average Power", UnitOfPower.WATT, lambda c: c.historical_average_power),
                PumpSensor(coordinator, "cycles_1h", "Cycles — 1 Hour", None, lambda c: c.cycles_1h),
                PumpSensor(coordinator, "cycles_6h", "Cycles — 6 Hours", None, lambda c: c.cycles_6h),
                PumpSensor(coordinator, "cycles_24h", "Cycles — 24 Hours", None, lambda c: c.cycles_24h),
                PumpSensor(coordinator, "runtime_1h", "Runtime — 1 Hour", UnitOfTime.SECONDS, lambda c: c.runtime_1h),
                PumpSensor(coordinator, "runtime_6h", "Runtime — 6 Hours", UnitOfTime.SECONDS, lambda c: c.runtime_6h),
                PumpSensor(coordinator, "runtime_24h", "Runtime — 24 Hours", UnitOfTime.SECONDS, lambda c: c.runtime_24h),
                PumpSensor(
                    coordinator, "last_cycle_start", "Last Cycle Start", None,
                    lambda c: c.last_cycle_start_datetime, SensorDeviceClass.TIMESTAMP
                ),
                PumpSensor(
                    coordinator, "last_cycle_end", "Last Cycle End", None,
                    lambda c: c.last_cycle_end_datetime, SensorDeviceClass.TIMESTAMP
                ),
            ]
        )
    async_add_entities(entities)


class PumpSensor(SensorEntity):
    _attr_should_poll = True

    def __init__(self, coordinator, key, name, unit, fn, device_class=None):
        self.c = coordinator
        self._fn = fn
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

    @property
    def native_value(self):
        return self._fn()
