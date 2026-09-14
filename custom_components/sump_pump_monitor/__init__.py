from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_PUMPS, DOMAIN, PLATFORMS
from .coordinator import PumpCoordinator


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


def get_pumps(entry: ConfigEntry) -> dict:
    """Return configured pumps, preferring updated options."""
    return entry.options.get(CONF_PUMPS, entry.data.get(CONF_PUMPS, {}))


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    pumps = get_pumps(entry)
    coordinators = {}
    for pump_id, pump in pumps.items():
        coordinator = PumpCoordinator(hass, entry, pump_id, pump)
        await coordinator.async_setup()
        coordinators[pump_id] = coordinator

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinators
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    coordinators = hass.data.get(DOMAIN, {}).pop(entry.entry_id, {})
    for coordinator in coordinators.values():
        await coordinator.async_unload()
    return unloaded
