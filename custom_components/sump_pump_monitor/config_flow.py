from __future__ import annotations

import uuid

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_ALERT_MAX_MINUTES, CONF_ALERT_MIN_MINUTES, CONF_ALERT_MULTIPLIER,
    CONF_INTERVAL_CHANGE_PERCENT, CONF_MAX_RUN_SECONDS, CONF_NAME,
    CONF_NOTIFICATION_SERVICE, CONF_POWER_SENSOR, CONF_PUMPS,
    CONF_PUMP_ID, CONF_RESUME_AFTER_HOURS, CONF_RUNNING_WATTS,
    CONF_SENSOR_OUTAGE_MINUTES, DEFAULT_ALERT_MAX_MINUTES,
    DEFAULT_ALERT_MIN_MINUTES, DEFAULT_ALERT_MULTIPLIER,
    DEFAULT_INTERVAL_CHANGE_PERCENT, DEFAULT_MAX_RUN_SECONDS,
    DEFAULT_NOTIFICATION_SERVICE, DEFAULT_RESUME_AFTER_HOURS,
    DEFAULT_RUNNING_WATTS, DEFAULT_SENSOR_OUTAGE_MINUTES, DOMAIN,
)


class SumpPumpMonitorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    def _notification_options(self):
        services = self.hass.services.async_services().get("notify", {})
        options = [{"value": "", "label": "None (notifications disabled)"}]
        options.extend(
            {"value": service, "label": f"notify.{service}"}
            for service in sorted(services)
        )
        return options

    @staticmethod
    def _pump_schema(notification_options):
        return vol.Schema({
            vol.Required(CONF_NAME): str,
            vol.Required(CONF_POWER_SENSOR): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="power", multiple=False)
            ),
            vol.Required(CONF_RUNNING_WATTS, default=DEFAULT_RUNNING_WATTS): vol.Coerce(float),
            vol.Optional(CONF_NOTIFICATION_SERVICE, default=DEFAULT_NOTIFICATION_SERVICE): selector.SelectSelector(
                selector.SelectSelectorConfig(options=notification_options, mode=selector.SelectSelectorMode.DROPDOWN)
            ),
            vol.Required(CONF_ALERT_MULTIPLIER, default=DEFAULT_ALERT_MULTIPLIER): vol.Coerce(float),
            vol.Required(CONF_ALERT_MIN_MINUTES, default=DEFAULT_ALERT_MIN_MINUTES): vol.Coerce(float),
            vol.Required(CONF_ALERT_MAX_MINUTES, default=DEFAULT_ALERT_MAX_MINUTES): vol.Coerce(float),
            vol.Required(CONF_MAX_RUN_SECONDS, default=DEFAULT_MAX_RUN_SECONDS): vol.Coerce(float),
            vol.Required(CONF_INTERVAL_CHANGE_PERCENT, default=DEFAULT_INTERVAL_CHANGE_PERCENT): vol.Coerce(float),
            vol.Required(CONF_RESUME_AFTER_HOURS, default=DEFAULT_RESUME_AFTER_HOURS): vol.Coerce(float),
            vol.Required(CONF_SENSOR_OUTAGE_MINUTES, default=DEFAULT_SENSOR_OUTAGE_MINUTES): vol.Coerce(float),
        })

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            pump_id = uuid.uuid4().hex
            pump = dict(user_input)
            pump[CONF_PUMP_ID] = pump_id
            return self.async_create_entry(
                title="Sump Pump Monitor",
                data={CONF_PUMPS: {pump_id: pump}},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=self._pump_schema(self._notification_options()),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return SumpPumpMonitorOptionsFlow()


class SumpPumpMonitorOptionsFlow(config_entries.OptionsFlowWithReload):
    async def async_step_init(self, user_input=None):
        return self.async_show_menu(
            step_id="init",
            menu_options=["add_pump", "edit_pump", "remove_pump"],
        )

    def _pumps(self):
        return dict(self.config_entry.options.get(CONF_PUMPS, self.config_entry.data.get(CONF_PUMPS, {})))

    async def async_step_add_pump(self, user_input=None):
        if user_input is not None:
            pump_id = uuid.uuid4().hex
            pump = dict(user_input)
            pump[CONF_PUMP_ID] = pump_id
            pumps = self._pumps()
            pumps[pump_id] = pump
            return self.async_create_entry(title="", data={CONF_PUMPS: pumps})
        return self.async_show_form(
            step_id="add_pump",
            data_schema=SumpPumpMonitorConfigFlow._pump_schema(self._notification_options()),
        )

    async def async_step_edit_pump(self, user_input=None):
        pumps = self._pumps()
        if not pumps:
            return self.async_abort(reason="no_pumps")
        if user_input is None:
            options = [{"value": pump_id, "label": pump[CONF_NAME]} for pump_id, pump in pumps.items()]
            return self.async_show_form(
                step_id="edit_pump",
                data_schema=vol.Schema({vol.Required(CONF_PUMP_ID): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=options, mode=selector.SelectSelectorMode.DROPDOWN)
                )}),
            )
        self._edit_pump_id = user_input[CONF_PUMP_ID]
        pump = pumps[self._edit_pump_id]
        return self.async_show_form(
            step_id="edit_pump_details",
            data_schema=self.add_suggested_values_to_schema(
                SumpPumpMonitorConfigFlow._pump_schema(self._notification_options()), pump
            ),
        )

    async def async_step_edit_pump_details(self, user_input=None):
        if user_input is not None:
            pumps = self._pumps()
            pump_id = self._edit_pump_id
            updated = dict(user_input)
            updated[CONF_PUMP_ID] = pump_id
            pumps[pump_id] = updated
            return self.async_create_entry(title="", data={CONF_PUMPS: pumps})
        return await self.async_step_edit_pump(None)

    async def async_step_remove_pump(self, user_input=None):
        pumps = self._pumps()
        if not pumps:
            return self.async_abort(reason="no_pumps")
        if user_input is not None:
            pumps.pop(user_input[CONF_PUMP_ID], None)
            if not pumps:
                return self.async_abort(reason="last_pump")
            return self.async_create_entry(title="", data={CONF_PUMPS: pumps})
        options = [{"value": pump_id, "label": pump[CONF_NAME]} for pump_id, pump in pumps.items()]
        return self.async_show_form(
            step_id="remove_pump",
            data_schema=vol.Schema({vol.Required(CONF_PUMP_ID): selector.SelectSelector(
                selector.SelectSelectorConfig(options=options, mode=selector.SelectSelectorMode.DROPDOWN)
            )}),
        )
