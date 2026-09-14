from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import EntityCategory, UnitOfPower, UnitOfTime

from .const import (
    CONF_HEAVY_CYCLING_PERCENT,
    CONF_HIGH_POWER_PERCENT,
    CONF_MAX_RUN_SECONDS,
    CONF_MIN_HISTORICAL_CYCLES,
    CONF_POWER_BASELINE_CYCLES,
    CONF_RUNNING_WATTS,
    CONF_SENSOR_OUTAGE_MINUTES,
    CONF_USAGE_WINDOW_HOURS,
    DEFAULT_HEAVY_CYCLING_PERCENT,
    DEFAULT_HIGH_POWER_PERCENT,
    DEFAULT_MAX_RUN_SECONDS,
    DEFAULT_MIN_HISTORICAL_CYCLES,
    DEFAULT_POWER_BASELINE_CYCLES,
    DEFAULT_RUNNING_WATTS,
    DEFAULT_SENSOR_OUTAGE_MINUTES,
    DEFAULT_USAGE_WINDOW_HOURS,
    DOMAIN,
)

NUMBER_DEFINITIONS = (
    (CONF_RUNNING_WATTS, "Running Power Threshold", 1, 1000, 1, UnitOfPower.WATT, DEFAULT_RUNNING_WATTS),
    (CONF_MAX_RUN_SECONDS, "Maximum Run Duration", 5, 3600, 1, UnitOfTime.SECONDS, DEFAULT_MAX_RUN_SECONDS),
    (CONF_HIGH_POWER_PERCENT, "High Power Threshold", 0, 500, 5, "%", DEFAULT_HIGH_POWER_PERCENT),
    (CONF_POWER_BASELINE_CYCLES, "Power Baseline Cycles", 1, 200, 1, None, DEFAULT_POWER_BASELINE_CYCLES),
    (CONF_USAGE_WINDOW_HOURS, "Heavy Usage Window", 1, 168, 1, UnitOfTime.HOURS, DEFAULT_USAGE_WINDOW_HOURS),
    (CONF_HEAVY_CYCLING_PERCENT, "Heavy Cycling Threshold", 0, 500, 5, "%", DEFAULT_HEAVY_CYCLING_PERCENT),
    (CONF_MIN_HISTORICAL_CYCLES, "Minimum Historical Cycles", 1, 1000, 1, None, DEFAULT_MIN_HISTORICAL_CYCLES),
    (CONF_SENSOR_OUTAGE_MINUTES, "Monitor Unavailable Delay", 0.5, 60, 0.5, UnitOfTime.MINUTES, DEFAULT_SENSOR_OUTAGE_MINUTES),
)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinators = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            PumpConfigNumber(coordinator, key, name, minimum, maximum, step, unit, default)
            for coordinator in coordinators.values()
            for key, name, minimum, maximum, step, unit, default in NUMBER_DEFINITIONS
        ]
    )


class PumpConfigNumber(NumberEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator, key, name, minimum, maximum, step, unit, default):
        self.coordinator = coordinator
        self.key = key
        self.default = default
        self._attr_unique_id = f"{coordinator.pump_id}_config_{key}"
        self._attr_name = name
        self._attr_native_min_value = minimum
        self._attr_native_max_value = maximum
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.pump_id)},
            "name": coordinator.name,
            "manufacturer": "Sump Pump Monitor",
            "model": "Sump Pump",
        }

    @property
    def native_value(self):
        return float(self.coordinator.data.get(self.key, self.default))

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_update_config(self.key, value)
        self.async_write_ha_state()
