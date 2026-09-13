from homeassistant.components.number import NumberEntity
from .const import *
async def async_setup_entry(hass,entry,async_add_entities):
 c=hass.data[DOMAIN][entry.entry_id]
 async_add_entities([ConfigNumber(c,CONF_RUNNING_WATTS,"Running Wattage",1,500,1),ConfigNumber(c,CONF_ALERT_MULTIPLIER,"Alert Multiplier",1,10,.1),ConfigNumber(c,CONF_ALERT_MIN_MINUTES,"Alert Minimum",1,1440,1),ConfigNumber(c,CONF_ALERT_MAX_MINUTES,"Alert Maximum",1,2880,1),ConfigNumber(c,CONF_MAX_RUN_SECONDS,"Maximum Run Duration",1,3600,1),ConfigNumber(c,CONF_INTERVAL_CHANGE_PERCENT,"Interval Change Percent",1,100,1),ConfigNumber(c,CONF_RESUME_AFTER_HOURS,"Resume After",1,720,1),ConfigNumber(c,CONF_SENSOR_OUTAGE_MINUTES,"Sensor Outage Delay",1,60,1)])
class ConfigNumber(NumberEntity):
 def __init__(self,c,key,name,lo,hi,step):
  self.c=c; self.key=key; self._attr_unique_id=f"{c.entry.entry_id}_{key}"; self._attr_name=name; self._attr_native_min_value=lo; self._attr_native_max_value=hi; self._attr_native_step=step; self._attr_device_info={"identifiers":{(DOMAIN,c.entry.entry_id)},"name":c.name,"manufacturer":"Sump Monitor","model":"Sump Pump"}
 @property
 def native_value(self): return float(self.c.data[self.key])
 async def async_set_native_value(self,value):
  self.c.data[self.key]=float(value)
  self.c.entry.async_on_unload(self.c.hass.config_entries.async_update_entry(self.c.entry,data=self.c.data))
  await self.c._store.async_save(self.c.state)
