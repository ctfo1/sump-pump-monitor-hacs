from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.helpers import selector

from .const import (
    CONF_ALERT_MAX_MINUTES, CONF_ALERT_MIN_MINUTES, CONF_ALERT_MULTIPLIER,
    CONF_INTERVAL_CHANGE_PERCENT, CONF_MAX_RUN_SECONDS, CONF_NOTIFICATION_SERVICE,
    CONF_POWER_SENSOR, CONF_RESUME_AFTER_HOURS, CONF_RUNNING_WATTS,
    CONF_SENSOR_OUTAGE_MINUTES, DEFAULT_ALERT_MAX_MINUTES, DEFAULT_ALERT_MIN_MINUTES,
    DEFAULT_ALERT_MULTIPLIER, DEFAULT_INTERVAL_CHANGE_PERCENT, DEFAULT_MAX_RUN_SECONDS,
    DEFAULT_NOTIFICATION_SERVICE, DEFAULT_RESUME_AFTER_HOURS, DEFAULT_RUNNING_WATTS,
    DEFAULT_SENSOR_OUTAGE_MINUTES, DOMAIN,
)

class SumpMonitorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def _notification_options(self):
        """Return currently available notify services for the config flow."""
        services = self.hass.services.async_services().get("notify", {})
        options = [{"value": "", "label": "None (notifications disabled)"}]
        options.extend(
            {"value": service, "label": f"notify.{service}"}
            for service in sorted(services)
        )
        return options

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            await self.async_set_unique_id(f"{user_input[CONF_POWER_SENSOR]}:{user_input[CONF_NAME].lower()}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        schema = vol.Schema({
            vol.Required(CONF_NAME): str,
            vol.Required(CONF_POWER_SENSOR): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="power", multiple=False)
            ),
            vol.Required(CONF_RUNNING_WATTS, default=DEFAULT_RUNNING_WATTS): vol.Coerce(float),
            vol.Optional(
                CONF_NOTIFICATION_SERVICE,
                default=DEFAULT_NOTIFICATION_SERVICE,
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=self._notification_options(),
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(CONF_ALERT_MULTIPLIER, default=DEFAULT_ALERT_MULTIPLIER): vol.Coerce(float),
            vol.Required(CONF_ALERT_MIN_MINUTES, default=DEFAULT_ALERT_MIN_MINUTES): vol.Coerce(float),
            vol.Required(CONF_ALERT_MAX_MINUTES, default=DEFAULT_ALERT_MAX_MINUTES): vol.Coerce(float),
            vol.Required(CONF_MAX_RUN_SECONDS, default=DEFAULT_MAX_RUN_SECONDS): vol.Coerce(float),
            vol.Required(CONF_INTERVAL_CHANGE_PERCENT, default=DEFAULT_INTERVAL_CHANGE_PERCENT): vol.Coerce(float),
            vol.Required(CONF_RESUME_AFTER_HOURS, default=DEFAULT_RESUME_AFTER_HOURS): vol.Coerce(float),
            vol.Required(CONF_SENSOR_OUTAGE_MINUTES, default=DEFAULT_SENSOR_OUTAGE_MINUTES): vol.Coerce(float),
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
