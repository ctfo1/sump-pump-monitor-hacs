from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.helpers.storage import Store

from .const import *

_LOGGER = logging.getLogger(__name__)

class PumpCoordinator:
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, pump_id: str, pump: dict):
        self.hass = hass
        self.entry = entry
        self.pump_id = pump_id
        self.data = dict(pump)
        self.state: dict[str, Any] = {
            "last_run": None, "run_start": None, "last_interval": 0.0,
            "cycles": 0, "intervals": [], "watchdog_until": None,
            "sensor_offline_since": None, "sensor_offline_alerted": False,
            "running": False, "last_run_duration": None, "last_alert": None,
        }
        self._store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}_{entry.entry_id}_{pump_id}")
        self._unsub = None
        self._watchdog_cancel = None
        self._outage_cancel = None
        self._listeners = []

    async def async_setup(self):
        stored = await self._store.async_load()
        if stored:
            self.state.update(stored)
        self._unsub = async_track_state_change_event(self.hass, [self.power_sensor], self._state_changed)
        self._listeners.append(self._unsub)
        self._reschedule_watchdog()
        # Establish the running state from the current sensor value without
        # inventing a run when the sensor starts at or below the threshold.
        current_power = self._power()
        if current_power is not None:
            self.state["running"] = current_power > float(self.data[CONF_RUNNING_WATTS])
            if not self.state["running"]:
                self.state["run_start"] = None
            self.hass.async_create_task(self._save())

    async def async_unload(self):
        for unsub in self._listeners:
            unsub()
        if self._watchdog_cancel:
            self._watchdog_cancel()
        if self._outage_cancel:
            self._outage_cancel()

    @property
    def power_sensor(self): return self.data[CONF_POWER_SENSOR]
    @property
    def name(self): return self.data[CONF_NAME]
    @property
    def device_id(self): return self.pump_id

    def _save(self):
        return self._store.async_save(self.state)

    def _power(self):
        value = self.hass.states.get(self.power_sensor)
        if not value or value.state in (STATE_UNKNOWN, STATE_UNAVAILABLE): return None
        try: return float(value.state)
        except ValueError: return None

    @callback
    def _state_changed(self, event: Event):
        old = event.data.get("old_state")
        new = event.data.get("new_state")
        old_value = self._parse(old)
        new_value = self._parse(new)
        if new and new.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            self._sensor_offline()
            return
        if new_value is None: return
        threshold = float(self.data[CONF_RUNNING_WATTS])
        if old_value is None:
            # Unknown/unavailable -> a numeric value is a recovery event, not
            # proof that the pump started. Evaluate the actual numeric value.
            if new_value > threshold and not self.state["running"]:
                self._start_run()
        elif old_value <= threshold < new_value:
            if not self.state["running"]:
                self._start_run()
        elif old_value > self.data[CONF_RUNNING_WATTS] >= new_value:
            if self.state["running"]:
                self._stop_run()
        if self.state["sensor_offline_since"] is not None:
            self._sensor_recovered()

    def _parse(self, state):
        if not state or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE): return None
        try: return float(state.state)
        except (TypeError, ValueError): return None

    def _start_run(self):
        now = datetime.now().astimezone().timestamp()
        self.state["running"] = True
        self.state["run_start"] = now
        self.state["cycles"] = int(self.state.get("cycles", 0)) + 1
        last = self.state.get("last_run")
        if last:
            interval = max(0.0, now - float(last))
            self.state["last_interval"] = min(interval, 604800.0)
            intervals = list(self.state.get("intervals", []))
            if interval > 0:
                intervals.append(interval)
                self.state["intervals"] = intervals[-5:]
            self._interval_notification(interval)
        self.state["last_run"] = now
        self._arm_watchdog()
        self.hass.async_create_task(self._save())

    def _stop_run(self):
        now = datetime.now().astimezone().timestamp()
        start = self.state.get("run_start")
        self.state["running"] = False
        if start:
            duration = max(0.0, now - float(start))
            self.state["last_run_duration"] = duration
            if duration > float(self.data[CONF_MAX_RUN_SECONDS]):
                self._notify("⚠️ Sump Pump Excessive Runtime", f"{self.name} ran for {duration:.1f} seconds (threshold: {float(self.data[CONF_MAX_RUN_SECONDS]):.0f}s). Possible pump or float switch issue.")
        self.state["run_start"] = None
        self.hass.async_create_task(self._save())

    def _interval_notification(self, interval):
        previous = float(self.state.get("last_interval", 0) or 0)
        # last_interval has already been updated, so recover prior value from previous interval history when possible.
        history = self.state.get("intervals", [])
        prior = history[-2] if len(history) >= 2 else 0
        if prior <= 0: return
        change = abs(interval-prior)/prior*100
        if interval >= float(self.data[CONF_RESUME_AFTER_HOURS])*3600:
            self._notify("Sump Pump Resumed", f"{self.name} ran for the first time in {interval/3600:.1f} hours. Monitoring is now active.")
        elif change > float(self.data[CONF_INTERVAL_CHANGE_PERCENT]):
            self._notify("Sump Pump Interval Changed", f"{self.name} interval changed by {change:.1f}%. Previous: {prior/60:.1f} min, Current: {interval/60:.1f} min.")

    def _watchdog_minutes(self):
        intervals = self.state.get("intervals", [])
        avg = sum(intervals)/len(intervals)/60 if intervals else float(self.data[CONF_ALERT_MAX_MINUTES])
        return min(max(avg*float(self.data[CONF_ALERT_MULTIPLIER]), float(self.data[CONF_ALERT_MIN_MINUTES])), float(self.data[CONF_ALERT_MAX_MINUTES]))

    def _arm_watchdog(self):
        if self.state.get("sensor_offline_since"): return
        minutes = self._watchdog_minutes()
        until = datetime.now().astimezone().timestamp() + minutes*60
        self.state["watchdog_until"] = until
        if self._watchdog_cancel: self._watchdog_cancel()
        self._watchdog_cancel = async_call_later(self.hass, minutes*60, self._watchdog_expired)

    def _reschedule_watchdog(self):
        until = self.state.get("watchdog_until")
        if not until or self.state.get("sensor_offline_since") or self.state.get("running"): return
        delay = float(until) - datetime.now().astimezone().timestamp()
        if delay <= 0: self._watchdog_expired(None)
        else: self._watchdog_cancel = async_call_later(self.hass, delay, self._watchdog_expired)

    @callback
    def _watchdog_expired(self, _):
        self._watchdog_cancel = None
        self.state["watchdog_until"] = None
        if not self.state.get("running") and self._power() is not None:
            since = self.time_since_last_run_minutes
            self._notify("⚠️ Sump Pump May Not Be Running", f"{self.name}: no sump activity detected for {since:.1f} min. Last known interval was {float(self.state.get('last_interval', 0))/60:.1f} min.")
            self.hass.async_create_task(self._save())

    def _sensor_offline(self):
        if self.state.get("sensor_offline_since") is None:
            self.state["sensor_offline_since"] = datetime.now().astimezone().timestamp()
            if self._outage_cancel: self._outage_cancel()
            self._outage_cancel = async_call_later(self.hass, float(self.data[CONF_SENSOR_OUTAGE_MINUTES])*60, self._outage_alert)
            if self._watchdog_cancel: self._watchdog_cancel(); self._watchdog_cancel = None
            self.state["watchdog_until"] = None
            self.hass.async_create_task(self._save())

    @callback
    def _outage_alert(self, _):
        self._outage_cancel = None
        if self.state.get("sensor_offline_since") and not self.state.get("sensor_offline_alerted"):
            self.state["sensor_offline_alerted"] = True
            self._notify("⚠️ Sump Power Sensor Offline", f"{self.name}: power sensor is unavailable. Monitoring is inactive until it recovers.")
            self.hass.async_create_task(self._save())

    def _sensor_recovered(self):
        was_alerted = self.state.get("sensor_offline_alerted")
        self.state["sensor_offline_since"] = None
        self.state["sensor_offline_alerted"] = False
        if was_alerted:
            self._notify("✅ Sump Power Sensor Back Online", f"{self.name}: monitoring has resumed. Watchdog will arm on the next sump run.")
        self.hass.async_create_task(self._save())

    def _notify(self, title, message):
        service = str(
            self.entry.options.get(
                CONF_NOTIFICATION_SERVICE,
                self.entry.data.get(
                    CONF_NOTIFICATION_SERVICE,
                    self.data.get(CONF_NOTIFICATION_SERVICE, ""),
                ),
            )
        ).strip()
        if not service: return
        if "." in service:
            domain, name = service.split(".", 1)
        else:
            domain, name = "notify", service
        self.hass.async_create_task(self.hass.services.async_call(domain, name, {"title": title, "message": message}, blocking=False))

    @property
    def average_interval_seconds(self):
        vals=self.state.get("intervals", [])
        return sum(vals)/len(vals) if vals else 0.0
    @property
    def time_since_last_run_minutes(self):
        last=self.state.get("last_run")
        return max(0.0,(datetime.now().astimezone().timestamp()-float(last))/60) if last else 0.0
    @property
    def current_run_seconds(self):
        start=self.state.get("run_start")
        return max(0.0,(datetime.now().astimezone().timestamp()-float(start))) if start else 0.0
    @property
    def sensor_available(self): return self._power() is not None
