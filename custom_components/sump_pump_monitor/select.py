from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory

from .const import CONF_POWER_SENSOR, CONF_POWER_SWITCH, DOMAIN


def _friendly_entity(hass, entity_id: str) -> str:
    state = hass.states.get(entity_id)
    name = state.name if state else entity_id
    return f"{name} — {entity_id}"


async def async_setup_entry(hass, entry, async_add_entities):
    coordinators = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            PumpEntitySelect(coordinator, CONF_POWER_SENSOR)
            for coordinator in coordinators.values()
        ]
        + [
            PumpEntitySelect(coordinator, CONF_POWER_SWITCH)
            for coordinator in coordinators.values()
        ]
    )


class PumpEntitySelect(SelectEntity):
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, key):
        self.coordinator = coordinator
        self.key = key
        self._attr_unique_id = f"{coordinator.pump_id}_config_{key}"
        self._attr_name = (
            "Pump Power Sensor" if key == CONF_POWER_SENSOR else "Power Monitor Switch"
        )
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.pump_id)},
            "name": coordinator.name,
            "manufacturer": "Sump Pump Monitor",
            "model": "Sump Pump",
        }

    @property
    def options(self):
        if self.key == CONF_POWER_SENSOR:
            entities = [
                s.entity_id
                for s in self.coordinator.hass.states.async_all("sensor")
                if s.attributes.get("device_class") == "power"
                or s.attributes.get("unit_of_measurement") in ("W", "kW")
            ]
        else:
            entities = [s.entity_id for s in self.coordinator.hass.states.async_all("switch")]

        current = self.coordinator.data.get(self.key)
        if current and current not in entities:
            entities.insert(0, current)

        labels = [_friendly_entity(self.coordinator.hass, entity_id) for entity_id in entities]
        self._label_to_entity = dict(zip(labels, entities))
        if self.key == CONF_POWER_SWITCH:
            labels.insert(0, "None — no power monitor switch")
            self._label_to_entity["None — no power monitor switch"] = ""
        return labels

    @property
    def current_option(self):
        current = self.coordinator.data.get(self.key)
        if not current and self.key == CONF_POWER_SWITCH:
            return "None — no power monitor switch"
        for label, entity_id in self._label_to_entity.items():
            if entity_id == current:
                return label
        return current

    async def async_select_option(self, option: str) -> None:
        entity_id = self._label_to_entity.get(option, option)
        await self.coordinator.async_update_config(self.key, entity_id)
        self.async_write_ha_state()
