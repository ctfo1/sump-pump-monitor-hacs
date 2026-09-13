from __future__ import annotations

import uuid

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_ALERT_MAX_MINUTES, CONF_ALERT_MIN_MINUTES, CONF_ALERT_MULTIPLIER,
    CONF_INTERVAL_CHANGE_PERCENT, CONF_MAX_RUN_SECONDS, CONF_NAME,
    CONF_NOTIFICATION_SERVICE, CONF_NOTIFICATION_TARGET, CONF_POWER_SENSOR, CONF_PUMPS,
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
    def _notification_schema(hass, current=""):
        return vol.Schema({
            vol.Optional(CONF_NOTIFICATION_TARGET, default=current): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="notify", multiple=False)
            )
        })

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            pump_id = uuid.uuid4().hex
            pump = dict(user_input)
            pump[CONF_PUMP_ID] = pump_id
            # Notification service is an integration-wide setting, not pump-specific.
            notification_target = pump.pop(CONF_NOTIFICATION_TARGET, "")
            return self.async_create_entry(
                title="Sump Pump Monitor",
                data={
                    CONF_PUMPS: {pump_id: pump},
                    CONF_NOTIFICATION_TARGET: notification_target,
                },
            )

        schema = self._pump_schema(self.hass)
        schema = vol.Schema({
            **schema.schema,
            vol.Optional(CONF_NOTIFICATION_TARGET, default=""): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="notify", multiple=False)
            ),
        })
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

    def _notification_target(self):
        return self.config_entry.options.get(
            CONF_NOTIFICATION_TARGET,
            self.config_entry.data.get(
                CONF_NOTIFICATION_TARGET,
                self.config_entry.options.get(
                    CONF_NOTIFICATION_SERVICE,
                    self.config_entry.data.get(CONF_NOTIFICATION_SERVICE, ""),
                ),
            ),
        )

    async def async_step_init(self, user_input=None):
        return self.async_show_menu(
            step_id="init",
            menu_options={
                "add_pump": "Add pump",
                "edit_pump": "Edit pump",
                "remove_pump": "Remove pump",
                "notification": "Notification settings",
            },
        )

    async def async_step_notification(self, user_input=None):
        if user_input is not None:
            options = dict(self.config_entry.options)
            options[CONF_NOTIFICATION_TARGET] = user_input.get(CONF_NOTIFICATION_TARGET, "")
            options.pop(CONF_NOTIFICATION_SERVICE, None)
            options.setdefault(CONF_PUMPS, self._pumps())
            return self.async_create_entry(title="", data=options)
        return self.async_show_form(
            step_id="notification",
            data_schema=SumpPumpMonitorConfigFlow._notification_schema(
                self.hass, self._notification_target()
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
            options.setdefault(CONF_NOTIFICATION_TARGET, self._notification_target())
            options.pop(CONF_NOTIFICATION_SERVICE, None)
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
        options.setdefault(CONF_NOTIFICATION_TARGET, self._notification_target())
        options.pop(CONF_NOTIFICATION_SERVICE, None)
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
            options.setdefault(CONF_NOTIFICATION_TARGET, self._notification_target())
            options.pop(CONF_NOTIFICATION_SERVICE, None)
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
