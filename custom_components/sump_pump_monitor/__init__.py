from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_PUMPS, DOMAIN, PLATFORMS
from .coordinator import PumpCoordinator

# Preload platform modules while the integration is imported.
# Home Assistant may otherwise import platform modules from the event loop during
# config-entry forwarding, which can trigger blocking import warnings on newer HA/Python versions.
from . import binary_sensor as _binary_sensor  # noqa: F401
from . import button as _button  # noqa: F401
from . import number as _number  # noqa: F401
from . import select as _select  # noqa: F401
from . import sensor as _sensor  # noqa: F401


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
