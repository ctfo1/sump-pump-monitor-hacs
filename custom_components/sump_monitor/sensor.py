from __future__ import annotations
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import UnitOfTime
from homeassistant.helpers.entity import EntityCategory
from .const import DOMAIN
from . import PumpCoordinator

async def async_setup_entry(hass, entry, async_add_entities):
    c=hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        PumpSensor(c,"last_interval","Last Interval",UnitOfTime.MINUTES,lambda:c.state.get("last_interval",0)/60),
        PumpSensor(c,"average_interval","Average Interval",UnitOfTime.MINUTES,lambda:c.average_interval_seconds/60),
        PumpSensor(c,"time_since_last_run","Time Since Last Run",UnitOfTime.MINUTES,lambda:c.time_since_last_run_minutes),
        PumpSensor(c,"current_run_duration","Current Run Duration",UnitOfTime.SECONDS,lambda:c.current_run_seconds),
        PumpSensor(c,"last_run_duration","Last Run Duration",UnitOfTime.SECONDS,lambda:c.state.get("last_run_duration")),
        PumpSensor(c,"watchdog_duration","Watchdog Duration",UnitOfTime.MINUTES,lambda:c._watchdog_minutes()),
        PumpSensor(c,"cycles","Lifetime Cycles",None,lambda:c.state.get("cycles",0)),
        PumpSensor(c,"power","Pump Power", "W", lambda:c._power()),
    ])

class PumpSensor(SensorEntity):
    _attr_should_poll=True
    def __init__(self,c,key,name,unit,fn):
        self.c=c; self._attr_unique_id=f"{c.entry.entry_id}_{key}"; self._attr_name=name; self._unit=unit; self._fn=fn
        self._attr_device_info={"identifiers":{(DOMAIN,c.entry.entry_id)},"name":c.name,"manufacturer":"Sump Monitor","model":"Sump Pump"}
    @property
    def native_value(self): return self._fn()
    @property
    def native_unit_of_measurement(self): return self._unit
