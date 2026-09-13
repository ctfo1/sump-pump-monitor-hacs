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
    VERSION = 3

    @staticmethod
    def _notification_options(hass):
        services = hass.services.async_services().get("notify", {})
        options = [{"value": "", "label": "None (notifications disabled)"}]
        options.extend(
            {"value": f"notify.{service}", "label": f"notify.{service}"}
            for service in sorted(services)
        )
        return options

    @staticmethod
    def _pump_schema(hass, include_name=True):
        schema = {}
        if include_name:
            schema[vol.Required(CONF_NAME)] = str
        schema.update({
            vol.Required(CONF_POWER_SENSOR): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="power", multiple=False)
            ),
            vol.Required(CONF_RUNNING_WATTS, default=DEFAULT_RUNNING_WATTS): vol.Coerce(float),
            vol.Required(CONF_ALERT_MULTIPLIER, default=DEFAULT_ALERT_MULTIPLIER): vol.Coerce(float),
            vol.Required(CONF_ALERT_MIN_MINUTES, default=DEFAULT_ALERT_MIN_MINUTES): vol.Coerce(float),
            vol.Required(CONF_ALERT_MAX_MINUTES, default=DEFAULT_ALERT_MAX_MINUTES): vol.Coerce(float),
            vol.Required(CONF_MAX_RUN_SECONDS, default=DEFAULT_MAX_RUN_SECONDS): vol.Coerce(float),
            vol.Required(CONF_INTERVAL_CHANGE_PERCENT, default=DEFAULT_INTERVAL_CHANGE_PERCENT): vol.Coerce(float),
            vol.Required(CONF_RESUME_AFTER_HOURS, default=DEFAULT_RESUME_AFTER_HOURS): vol.Coerce(float),
            vol.Required(CONF_SENSOR_OUTAGE_MINUTES, default=DEFAULT_SENSOR_OUTAGE_MINUTES): vol.Coerce(float),
        })
        return vol.Schema(schema)

    @staticmethod
    def _notification_schema(hass, current=""):
        return vol.Schema({
            vol.Required(CONF_NOTIFICATION_SERVICE, default=current): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=SumpPumpMonitorConfigFlow._notification_options(hass),
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )
        })

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            pump_id = uuid.uuid4().hex
            pump = dict(user_input)
            pump[CONF_PUMP_ID] = pump_id
            # Notification service is an integration-wide setting, not pump-specific.
            notification_service = pump.pop(CONF_NOTIFICATION_SERVICE, DEFAULT_NOTIFICATION_SERVICE)
            return self.async_create_entry(
                title="Sump Pump Monitor",
                data={
                    CONF_PUMPS: {pump_id: pump},
                    CONF_NOTIFICATION_SERVICE: notification_service,
                },
            )

        schema = self._pump_schema(self.hass)
        # Keep notification selection visible during initial setup.
        schema = vol.Schema({**schema.schema, vol.Required(
            CONF_NOTIFICATION_SERVICE, default=DEFAULT_NOTIFICATION_SERVICE
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=self._notification_options(self.hass),
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        )})
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return SumpPumpMonitorOptionsFlow()


class SumpPumpMonitorOptionsFlow(config_entries.OptionsFlowWithReload):
    def _pumps(self):
        pumps = self.config_entry.options.get(CONF_PUMPS)
        if pumps is None:
            pumps = self.config_entry.data.get(CONF_PUMPS, {})
        return {key: dict(value) for key, value in pumps.items()}

    def _notification_service(self):
        return self.config_entry.options.get(
            CONF_NOTIFICATION_SERVICE,
            self.config_entry.data.get(CONF_NOTIFICATION_SERVICE, DEFAULT_NOTIFICATION_SERVICE),
        )

    async def async_step_init(self, user_input=None):
        return self.async_show_menu(
            step_id="init",
            menu_options=["add_pump", "edit_pump", "remove_pump", "notification"],
        )

    async def async_step_notification(self, user_input=None):
        if user_input is not None:
            options = dict(self.config_entry.options)
            options[CONF_NOTIFICATION_SERVICE] = user_input[CONF_NOTIFICATION_SERVICE]
            options.setdefault(CONF_PUMPS, self._pumps())
            return self.async_create_entry(title="", data=options)
        return self.async_show_form(
            step_id="notification",
            data_schema=SumpPumpMonitorConfigFlow._notification_schema(
                self.hass, self._notification_service()
            ),
        )

    async def async_step_add_pump(self, user_input=None):
        if user_input is not None:
            pump_id = uuid.uuid4().hex
            pump = dict(user_input)
            pump[CONF_PUMP_ID] = pump_id
            pumps = self._pumps()
            pumps[pump_id] = pump
            options = dict(self.config_entry.options)
            options[CONF_PUMPS] = pumps
            options.setdefault(CONF_NOTIFICATION_SERVICE, self._notification_service())
            return self.async_create_entry(title="", data=options)
        return self.async_show_form(
            step_id="add_pump",
            data_schema=SumpPumpMonitorConfigFlow._pump_schema(self.hass),
        )

    async def async_step_edit_pump(self, user_input=None):
        pumps = self._pumps()
        if not pumps:
            return self.async_abort(reason="no_pumps")
        if user_input is None:
            options = [
                {"value": pump_id, "label": pump[CONF_NAME]}
                for pump_id, pump in pumps.items()
            ]
            return self.async_show_form(
                step_id="edit_pump",
                data_schema=vol.Schema({
                    vol.Required(CONF_PUMP_ID): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                }),
            )
        pump_id = user_input[CONF_PUMP_ID]
        if pump_id not in pumps:
            return self.async_abort(reason="pump_not_found")
        self._edit_pump_id = pump_id
        return self.async_show_form(
            step_id="edit_pump_details",
            data_schema=self.add_suggested_values_to_schema(
                SumpPumpMonitorConfigFlow._pump_schema(self.hass),
                pumps[pump_id],
            ),
        )

    async def async_step_edit_pump_details(self, user_input=None):
        if user_input is None:
            return self.async_abort(reason="edit_failed")
        pumps = self._pumps()
        pump_id = getattr(self, "_edit_pump_id", None)
        if pump_id not in pumps:
            return self.async_abort(reason="edit_failed")
        updated = dict(user_input)
        updated[CONF_PUMP_ID] = pump_id
        pumps[pump_id] = updated
        options = dict(self.config_entry.options)
        options[CONF_PUMPS] = pumps
        options.setdefault(CONF_NOTIFICATION_SERVICE, self._notification_service())
        return self.async_create_entry(title="", data=options)

    async def async_step_remove_pump(self, user_input=None):
        pumps = self._pumps()
        if not pumps:
            return self.async_abort(reason="no_pumps")
        if user_input is not None:
            pumps.pop(user_input[CONF_PUMP_ID], None)
            if not pumps:
                return self.async_abort(reason="last_pump")
            options = dict(self.config_entry.options)
            options[CONF_PUMPS] = pumps
            options.setdefault(CONF_NOTIFICATION_SERVICE, self._notification_service())
            return self.async_create_entry(title="", data=options)
        options = [
            {"value": pump_id, "label": pump[CONF_NAME]}
            for pump_id, pump in pumps.items()
        ]
        return self.async_show_form(
            step_id="remove_pump",
            data_schema=vol.Schema({
                vol.Required(CONF_PUMP_ID): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
            }),
        )
