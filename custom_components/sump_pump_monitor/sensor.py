from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import UnitOfTime

from . import get_pumps
from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    coordinators = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for coordinator in coordinators.values():
        entities.extend([
            PumpSensor(coordinator, "last_interval", "Last Interval", UnitOfTime.MINUTES, lambda c=coordinator: c.state.get("last_interval", 0) / 60),
            PumpSensor(coordinator, "average_interval", "Average Interval", UnitOfTime.MINUTES, lambda c=coordinator: c.average_interval_seconds / 60),
            PumpSensor(coordinator, "time_since_last_run", "Time Since Last Run", UnitOfTime.MINUTES, lambda c=coordinator: c.time_since_last_run_minutes),
            PumpSensor(coordinator, "current_run_duration", "Current Run Duration", UnitOfTime.SECONDS, lambda c=coordinator: c.current_run_seconds),
            PumpSensor(coordinator, "last_run_duration", "Last Run Duration", UnitOfTime.SECONDS, lambda c=coordinator: c.state.get("last_run_duration")),
            PumpSensor(coordinator, "watchdog_duration", "Watchdog Duration", UnitOfTime.MINUTES, lambda c=coordinator: c._watchdog_minutes()),
            PumpSensor(coordinator, "cycles", "Lifetime Cycles", None, lambda c=coordinator: c.state.get("cycles", 0)),
            PumpSensor(coordinator, "power", "Pump Power", "W", lambda c=coordinator: c._power()),
        ])
    async_add_entities(entities)


class PumpSensor(SensorEntity):
    _attr_should_poll = True

    def __init__(self, coordinator, key, name, unit, fn):
        self.c = coordinator
        self._fn = fn
        self._attr_unique_id = f"{coordinator.pump_id}_{key}"
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.pump_id)},
            "name": coordinator.name,
            "manufacturer": "Sump Pump Monitor",
            "model": "Sump Pump",
        }

    @property
    def native_value(self):
        return self._fn()
