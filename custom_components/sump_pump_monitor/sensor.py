from __future__ import annotations

from datetime import datetime, timezone

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import UnitOfPower, UnitOfTime
from homeassistant.core import callback

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    coordinators = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for coordinator in coordinators.values():
        entities.extend([
            PumpSensor(coordinator, "pump_power", "Pump Power", UnitOfPower.WATT,
                       "power", SensorDeviceClass.POWER),
            PumpSensor(coordinator, "current_run_duration", "Current Run Duration",
                       UnitOfTime.SECONDS, "current_run_duration"),
            PumpSensor(coordinator, "last_cycle_duration", "Last Cycle Duration",
                       UnitOfTime.SECONDS, "last_cycle_duration"),
            PumpSensor(coordinator, "average_cycle_duration", "Average Cycle Duration",
                       UnitOfTime.SECONDS, "average_cycle_duration"),
            PumpSensor(coordinator, "last_cycle_average_power", "Last Cycle Average Power",
                       UnitOfPower.WATT, "last_cycle_average_power", SensorDeviceClass.POWER),
            PumpSensor(coordinator, "last_cycle_peak_power", "Last Cycle Peak Power",
                       UnitOfPower.WATT, "last_cycle_peak_power", SensorDeviceClass.POWER),
            PumpSensor(coordinator, "historical_average_power", "Historical Average Power",
                       UnitOfPower.WATT, "historical_average_power", SensorDeviceClass.POWER),
            PumpSensor(coordinator, "cycles_24_hours", "Cycles — 24 Hours", None,
                       "cycles_24_hours"),
            PumpSensor(coordinator, "runtime_24_hours", "Runtime — 24 Hours",
                       UnitOfTime.SECONDS, "runtime_24_hours"),
            PumpSensor(coordinator, "last_cycle_start", "Last Cycle Start", None,
                       "last_cycle_start", SensorDeviceClass.TIMESTAMP),
            PumpSensor(coordinator, "last_cycle_end", "Last Cycle End", None,
                       "last_cycle_end", SensorDeviceClass.TIMESTAMP),
            PumpCycleHistorySensor(coordinator),
        ])
    async_add_entities(entities)


class PumpSensor(SensorEntity):
    """Simple read-only sensor backed by the pump coordinator."""

    _attr_should_poll = False

    def __init__(self, coordinator, key, name, unit, state_key, device_class=None):
        self.coordinator = coordinator
        self.state_key = state_key
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
        self._remove_listener = self.coordinator.add_update_listener(
            self._handle_coordinator_update
        )
        self.async_on_remove(self._remove_listener)
        # Publish the current coordinator state immediately.
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self):
        self.async_write_ha_state()

    @property
    def available(self):
        # Only the direct pump-power sensor follows source availability.
        if self.state_key == "power":
            return bool(getattr(self.coordinator, "sensor_available", False))
        return True

    @property
    def native_value(self):
        try:
            value = self.coordinator.get_entity_value(self.state_key)
        except Exception:
            # Do not let an entity property exception prevent entity creation.
            return None
        if value is None:
            return None
        if isinstance(value, (int, float)):
            if self._attr_native_unit_of_measurement == UnitOfTime.SECONDS:
                return round(value)
            return value
        if isinstance(value, datetime):
            return value
        return None


class PumpCycleHistorySensor(SensorEntity):
    """Expose retained cycle history as a Lovelace-friendly sensor."""

    _attr_should_poll = False
    _attr_icon = "mdi:history"

    def __init__(self, coordinator):
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.pump_id}_cycle_history"
        self._attr_name = "Cycle History"
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
    def native_value(self):
        return len(self.coordinator.history)

    @property
    def extra_state_attributes(self):
        cycles = []
        for record in reversed(self.coordinator.history):
            start = record.get("start")
            end = record.get("end")
            cycles.append(
                {
                    "start": (
                        datetime.fromtimestamp(float(start), timezone.utc).astimezone().isoformat()
                        if start is not None
                        else None
                    ),
                    "end": (
                        datetime.fromtimestamp(float(end), timezone.utc).astimezone().isoformat()
                        if end is not None
                        else None
                    ),
                    "duration": round(float(record["duration"]))
                    if record.get("duration") is not None
                    else None,
                    "average_power": round(float(record["average_power"]), 1)
                    if record.get("average_power") is not None
                    else None,
                    "peak_power": round(float(record["peak_power"]), 1)
                    if record.get("peak_power") is not None
                    else None,
                }
            )

        return {
            "cycles": cycles,
            "retained_cycles": len(cycles),
            "history_days": self.coordinator.history_days,
            "max_history_cycles": self.coordinator.max_history_cycles,
        }
