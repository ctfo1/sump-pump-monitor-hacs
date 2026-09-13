from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from .const import DOMAIN

async def async_setup_entry(hass,entry,async_add_entities):
 c=hass.data[DOMAIN][entry.entry_id]
 async_add_entities([PumpBinary(c,"running","Pump Running",BinarySensorDeviceClass.RUNNING,lambda:c.state.get("running",False)),PumpBinary(c,"sensor_available","Power Sensor Available",BinarySensorDeviceClass.CONNECTIVITY,lambda:c.sensor_available)])
class PumpBinary(BinarySensorEntity):
 def __init__(self,c,key,name,dc,fn):
  self.c=c; self._fn=fn; self._attr_unique_id=f"{c.entry.entry_id}_{key}"; self._attr_name=name; self._attr_device_class=dc; self._attr_device_info={"identifiers":{(DOMAIN,c.entry.entry_id)},"name":c.name,"manufacturer":"Sump Pump Monitor","model":"Sump Pump"}
 @property
 def is_on(self): return self._fn()
