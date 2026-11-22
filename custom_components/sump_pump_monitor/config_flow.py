from __future__ import annotations

import uuid

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_HISTORY_DAYS,
    CONF_MAX_HISTORY_CYCLES,
    CONF_NAME,
    CONF_NOTIFICATION_SERVICE,
    CONF_NOTIFICATION_TARGET,
    CONF_POWER_SENSOR,
    CONF_POWER_SWITCH,
    CONF_PUMPS,
    CONF_PUMP_ID,
    DEFAULT_HISTORY_DAYS,
    DEFAULT_MAX_HISTORY_CYCLES,
    DEFAULT_NOTIFICATION_TARGET,
    DOMAIN,
)


class SumpPumpMonitorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 4

    @staticmethod
    def _pump_schema() -> vol.Schema:
        """Return the minimal per-pump setup configuration."""
        return vol.Schema(
            {
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_POWER_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor", device_class="power", multiple=False
                    )
                ),
                vol.Optional(CONF_POWER_SWITCH, default=None): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="switch", multiple=False)
                ),
            }
        )

    @staticmethod
    def _notification_schema(current: str = "") -> vol.Schema:
        return vol.Schema(
            {
                vol.Optional(
                    CONF_NOTIFICATION_TARGET, default=current or None
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="notify", multiple=False)
                )
            }
        )

    @staticmethod
    def _general_schema() -> vol.Schema:
        return vol.Schema(
            {
                vol.Required(
                    CONF_HISTORY_DAYS, default=DEFAULT_HISTORY_DAYS
                ): vol.Coerce(int),
                vol.Required(
                    CONF_MAX_HISTORY_CYCLES,
                    default=DEFAULT_MAX_HISTORY_CYCLES,
                ): vol.Coerce(int),
            }
        )

    @staticmethod
    def _clean_pump(pump: dict) -> dict:
        """Normalize optional values before storing a pump configuration."""
        cleaned = dict(pump)
        if not cleaned.get(CONF_POWER_SWITCH):
            cleaned.pop(CONF_POWER_SWITCH, None)
        return cleaned

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            pump_id = uuid.uuid4().hex
            pump = self._clean_pump(user_input)
            notification_target = pump.pop(
                CONF_NOTIFICATION_TARGET, DEFAULT_NOTIFICATION_TARGET
            )
            return self.async_create_entry(
                title="Sump Pump Monitor",
                data={
                    CONF_PUMPS: {pump_id: pump},
                    CONF_NOTIFICATION_TARGET: notification_target or "",
                    CONF_HISTORY_DAYS: DEFAULT_HISTORY_DAYS,
                    CONF_MAX_HISTORY_CYCLES: DEFAULT_MAX_HISTORY_CYCLES,
                },
            )

        schema = dict(self._pump_schema().schema)
        schema[vol.Optional(
            CONF_NOTIFICATION_TARGET, default=DEFAULT_NOTIFICATION_TARGET or None
        )] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="notify", multiple=False)
        )
        return self.async_show_form(step_id="user", data_schema=vol.Schema(schema))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return SumpPumpMonitorOptionsFlow()


class SumpPumpMonitorOptionsFlow(config_entries.OptionsFlowWithReload):
    def _pumps(self) -> dict:
        pumps = self.config_entry.options.get(CONF_PUMPS)
        if pumps is None:
            pumps = self.config_entry.data.get(CONF_PUMPS, {})
        return {key: dict(value) for key, value in pumps.items()}

    def _notification_target(self) -> str:
        return str(
            self.config_entry.options.get(
                CONF_NOTIFICATION_TARGET,
                self.config_entry.data.get(
                    CONF_NOTIFICATION_TARGET,
                    self.config_entry.options.get(
                        CONF_NOTIFICATION_SERVICE,
                        self.config_entry.data.get(CONF_NOTIFICATION_SERVICE, ""),
                    ),
                ),
            )
            or ""
        )

    def _general(self) -> dict:
        return {
            CONF_HISTORY_DAYS: int(
                self.config_entry.options.get(
                    CONF_HISTORY_DAYS,
                    self.config_entry.data.get(
                        CONF_HISTORY_DAYS, DEFAULT_HISTORY_DAYS
                    ),
                )
            ),
            CONF_MAX_HISTORY_CYCLES: int(
                self.config_entry.options.get(
                    CONF_MAX_HISTORY_CYCLES,
                    self.config_entry.data.get(
                        CONF_MAX_HISTORY_CYCLES, DEFAULT_MAX_HISTORY_CYCLES
                    ),
                )
            ),
        }

    def _save_options(self, pumps: dict | None = None) -> dict:
        options = dict(self.config_entry.options)
        options[CONF_PUMPS] = pumps if pumps is not None else self._pumps()
        options[CONF_NOTIFICATION_TARGET] = self._notification_target()
        options.update(self._general())
        options.pop(CONF_NOTIFICATION_SERVICE, None)
        return options

    async def async_step_init(self, user_input=None):
        return self.async_show_menu(
            step_id="init",
            menu_options={
                "add_pump": "Add pump",
                "remove_pump": "Remove pump",
                "notification": "Notification settings",
                "history": "Cycle history settings",
            },
        )

    async def async_step_notification(self, user_input=None):
        if user_input is not None:
            options = self._save_options()
            options[CONF_NOTIFICATION_TARGET] = user_input.get(
                CONF_NOTIFICATION_TARGET
            ) or ""
            return self.async_create_entry(title="", data=options)
        return self.async_show_form(
            step_id="notification",
            data_schema=SumpPumpMonitorConfigFlow._notification_schema(
                self._notification_target()
            ),
        )

    async def async_step_history(self, user_input=None):
        if user_input is not None:
            options = self._save_options()
            options[CONF_HISTORY_DAYS] = int(user_input[CONF_HISTORY_DAYS])
            options[CONF_MAX_HISTORY_CYCLES] = int(
                user_input[CONF_MAX_HISTORY_CYCLES]
            )
            return self.async_create_entry(title="", data=options)
        general = self._general()
        return self.async_show_form(
            step_id="history",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HISTORY_DAYS, default=general[CONF_HISTORY_DAYS]
                    ): vol.Coerce(int),
                    vol.Required(
                        CONF_MAX_HISTORY_CYCLES,
                        default=general[CONF_MAX_HISTORY_CYCLES],
                    ): vol.Coerce(int),
                }
            ),
        )

    async def async_step_add_pump(self, user_input=None):
        if user_input is not None:
            pump_id = uuid.uuid4().hex
            pumps = self._pumps()
            pumps[pump_id] = SumpPumpMonitorConfigFlow._clean_pump(user_input)
            return self.async_create_entry(title="", data=self._save_options(pumps))
        return self.async_show_form(
            step_id="add_pump",
            data_schema=SumpPumpMonitorConfigFlow._pump_schema(),
        )

    async def async_step_edit_pump(self, user_input=None):
        pumps = self._pumps()
        if not pumps:
            return self.async_abort(reason="no_pumps")
        if user_input is None:
            return self.async_show_form(
                step_id="edit_pump",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_PUMP_ID): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                options=[
                                    {
                                        "value": pid,
                                        "label": p.get(CONF_NAME, pid),
                                    }
                                    for pid, p in pumps.items()
                                ],
                                mode=selector.SelectSelectorMode.DROPDOWN,
                            )
                        )
                    }
                ),
            )
        pump_id = user_input[CONF_PUMP_ID]
        if pump_id not in pumps:
            return self.async_abort(reason="pump_not_found")
        # Keep the selected ID on the flow instance for the following step.
        self._edit_pump_id = pump_id
        current = dict(pumps[pump_id])
        current.setdefault(CONF_POWER_SWITCH, None)
        return self.async_show_form(
            step_id="edit_pump_details",
            data_schema=self.add_suggested_values_to_schema(
                SumpPumpMonitorConfigFlow._pump_schema(), current
            ),
        )

    async def async_step_edit_pump_details(self, user_input=None):
        pump_id = getattr(self, "_edit_pump_id", None)
        pumps = self._pumps()
        if pump_id not in pumps:
            return self.async_abort(reason="edit_failed")
        pumps[pump_id] = SumpPumpMonitorConfigFlow._clean_pump(user_input or {})
        return self.async_create_entry(title="", data=self._save_options(pumps))

    async def async_step_remove_pump(self, user_input=None):
        pumps = self._pumps()
        if not pumps:
            return self.async_abort(reason="no_pumps")
        if user_input is not None:
            pumps.pop(user_input[CONF_PUMP_ID], None)
            if not pumps:
                return self.async_abort(reason="last_pump")
            return self.async_create_entry(title="", data=self._save_options(pumps))
        return self.async_show_form(
            step_id="remove_pump",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PUMP_ID): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {
                                    "value": pid,
                                    "label": p.get(CONF_NAME, pid),
                                }
                                for pid, p in pumps.items()
                            ],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
        )
