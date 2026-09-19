from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store

from .const import *

_LOGGER = logging.getLogger(__name__)

# Dispatcher signal used by entities to refresh immediately when pump state changes.
UPDATE_SIGNAL = "sump_pump_monitor_update"


class PumpCoordinator:
    """Monitor one physical sump pump and persist completed-cycle history."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, pump_id: str, pump: dict):
        self.hass = hass
        self.entry = entry
        self.pump_id = pump_id
        self.data = dict(pump)
        self.state: dict[str, Any] = {
            "running": False,
            "run_start": None,
            "last_run_start": None,
            "last_run_end": None,
            "last_run_duration": None,
            "last_run_avg_power": None,
            "last_run_peak_power": None,
            "cycles": 0,
            "current_power_samples": [],
            "high_power_alerted": False,
            "heavy_cycling_alerted": False,
            "running_too_long_alerted": False,
            "sensor_offline_since": None,
            "sensor_offline_alerted": False,
            "history": [],
        }
        self._store = Store(
            hass, STORAGE_VERSION, f"{STORAGE_KEY}_{entry.entry_id}_{pump_id}"
        )
        self._listeners = []
        self._runtime_cancel = None
        self._outage_cancel = None
        self._last_status_update = 0.0
        self._entity_listeners = set()

    def add_update_listener(self, listener):
        """Register a callback for entity state updates."""
        self._entity_listeners.add(listener)
        return lambda: self._entity_listeners.discard(listener)

    @callback
    def async_update_entities(self):
        """Notify all entities that coordinator state has changed."""
        for listener in tuple(self._entity_listeners):
            listener()

    async def async_setup(self):
        stored = await self._store.async_load()
        if stored:
            # New storage is preferred. Retain useful lifetime count from older versions.
            self.state.update(stored)
            self.state.setdefault("history", [])
            self.state.setdefault("current_power_samples", [])
            self._prune_history()

        entities = [self.power_sensor]
        if self.power_switch:
            entities.append(self.power_switch)
        self._listeners.append(
            async_track_state_change_event(self.hass, entities, self._state_changed)
        )

        power = self._power()
        if power is None:
            self._sensor_offline()
        else:
            self._clear_sensor_offline()
            self.state["running"] = power > self.running_watts
            if not self.state["running"]:
                self.state["run_start"] = None
            elif self.state["run_start"] is None:
                # Do not invent a historical start time after restart.
                self.state["run_start"] = datetime.now(timezone.utc).timestamp()
                self.state["current_power_samples"] = [power]
                self._schedule_runtime_alert()
        self._prune_history()
        await self._save()
        self.async_update_entities()

    async def async_unload(self):
        for unsub in self._listeners:
            unsub()
        if self._runtime_cancel:
            self._runtime_cancel()
        if self._outage_cancel:
            self._outage_cancel()

    async def async_update_config(self, key: str, value):
        """Update one pump-specific setting from a device configuration entity."""
        if key == CONF_POWER_SWITCH and not value:
            self.data.pop(key, None)
        else:
            self.data[key] = value

        pumps = {
            pid: dict(pump)
            for pid, pump in (
                self.entry.options.get(
                    CONF_PUMPS, self.entry.data.get(CONF_PUMPS, {})
                )
            ).items()
        }
        pumps[self.pump_id] = dict(self.data)

        options = dict(self.entry.options)
        options[CONF_PUMPS] = pumps
        self.hass.config_entries.async_update_entry(self.entry, options=options)

        # Rebind state listeners if either monitored entity changed.
        if key in (CONF_POWER_SENSOR, CONF_POWER_SWITCH):
            for unsub in self._listeners:
                unsub()
            self._listeners = []
            entities = [self.power_sensor]
            if self.power_switch:
                entities.append(self.power_switch)
            self._listeners.append(
                async_track_state_change_event(
                    self.hass, entities, self._state_changed
                )
            )

            # Re-evaluate the new monitor immediately.
            power = self._power()
            if power is None:
                self._sensor_offline()
            else:
                self._clear_sensor_offline()
                self._process_power_change()
                self._process_switch_change()

        self._dispatch_update()
        self._save_task()

    @property
    def power_sensor(self):
        return self.data[CONF_POWER_SENSOR]

    @property
    def power_switch(self):
        return self.data.get(CONF_POWER_SWITCH)

    @property
    def name(self):
        return self.data[CONF_NAME]

    @property
    def device_id(self):
        return self.pump_id

    @property
    def running_watts(self):
        return float(self.data.get(CONF_RUNNING_WATTS, DEFAULT_RUNNING_WATTS))

    def _dispatch_update(self):
        """Notify entities that coordinator state has changed."""
        async_dispatcher_send(
            self.hass,
            f"{UPDATE_SIGNAL}_{self.entry.entry_id}_{self.pump_id}",
        )

    def _save(self):
        return self._store.async_save(self.state)

    def _power(self):
        state = self.hass.states.get(self.power_sensor)
        if not state or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return None
        try:
            return float(state.state)
        except (TypeError, ValueError):
            return None

    def _switch_on(self) -> bool | None:
        if not self.power_switch:
            return None
        state = self.hass.states.get(self.power_switch)
        if not state or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return None
        return state.state != STATE_OFF

    @callback
    def _state_changed(self, event: Event):
        entity_id = event.data.get("entity_id")
        new = event.data.get("new_state")
        if entity_id == self.power_sensor:
            if new and new.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                self._sensor_offline()
                return
            if self._power() is None:
                self._sensor_offline()
                return
            self._clear_sensor_offline()
            self._process_power_change()
        elif entity_id == self.power_switch:
            # Switch state is deliberately tracked independently from power-sensor availability.
            self._process_switch_change()
        self._save_task()

    def _process_power_change(self):
        power = self._power()
        if power is None:
            return
        running = power > self.running_watts
        if running and not self.state["running"]:
            self._start_run(power)
        elif not running and self.state["running"]:
            self._stop_run()
        elif running:
            samples = list(self.state.get("current_power_samples", []))
            samples.append(power)
            # Avoid unbounded sample storage; only the current run needs this.
            self.state["current_power_samples"] = samples[-300:]
            self._evaluate_high_power()
            self._evaluate_heavy_cycling()
        self._dispatch_update()

    def _process_switch_change(self):
        if self._switch_on() is False:
            self._notify(
                "Sump Pump Monitor: Power Monitor Switched Off",
                f"{self.name}: the configured power monitor switch is off.",
            )
        self._dispatch_update()

    def _start_run(self, power: float):
        now = datetime.now(timezone.utc)
        ts = now.timestamp()
        self.state["running"] = True
        self.state["run_start"] = ts
        self.state["last_run_start"] = ts
        self.state["current_power_samples"] = [power]
        self.state["high_power_alerted"] = False
        self.state["heavy_cycling_alerted"] = False
        self.state["running_too_long_alerted"] = False
        self.state["cycles"] = int(self.state.get("cycles", 0)) + 1
        self._schedule_runtime_alert()
        self._evaluate_high_power()
        self._evaluate_heavy_cycling()
        self._dispatch_update()
        self._save_task()

    def _stop_run(self):
        now = datetime.now(timezone.utc)
        ts = now.timestamp()
        start = self.state.get("run_start")
        self.state["running"] = False
        self.state["last_run_end"] = ts
        duration = max(0.0, ts - float(start)) if start else None
        self.state["last_run_duration"] = duration
        samples = [float(v) for v in self.state.get("current_power_samples", [])]
        avg_power = sum(samples) / len(samples) if samples else None
        peak_power = max(samples) if samples else None
        self.state["last_run_avg_power"] = avg_power
        self.state["last_run_peak_power"] = peak_power
        if start:
            self.state.setdefault("history", []).append(
                {
                    "start": float(start),
                    "end": ts,
                    "duration": duration,
                    "average_power": avg_power,
                    "peak_power": peak_power,
                }
            )
        self.state["run_start"] = None
        self.state["current_power_samples"] = []
        if self._runtime_cancel:
            self._runtime_cancel()
            self._runtime_cancel = None
        self._prune_history()
        self._dispatch_update()
        self._save_task()

    def _schedule_runtime_alert(self):
        if self._runtime_cancel:
            self._runtime_cancel()
        delay = max(1.0, float(self.data.get(CONF_MAX_RUN_SECONDS, DEFAULT_MAX_RUN_SECONDS)))
        self._runtime_cancel = async_call_later(
            self.hass, delay, self._runtime_alert
        )

    @callback
    def _runtime_alert(self, _):
        self._runtime_cancel = None
        if self.state.get("running") and not self.state.get("running_too_long_alerted"):
            self.state["running_too_long_alerted"] = True
            elapsed = self.current_run_seconds
            self._notify(
                "Sump Pump Monitor: Pump Running Too Long",
                f"{self.name}: pump has been running for {elapsed:.1f} seconds "
                f"(limit: {float(self.data.get(CONF_MAX_RUN_SECONDS, DEFAULT_MAX_RUN_SECONDS)):.0f}s).",
            )
            self._dispatch_update()
            self._save_task()

    def _evaluate_high_power(self):
        if self.state.get("high_power_alerted"):
            return
        baseline = self.historical_average_power
        if baseline is None:
            return
        samples = self.state.get("current_power_samples", [])
        if not samples:
            return
        current = sum(float(v) for v in samples) / len(samples)
        limit = baseline * (1.0 + float(self.data.get(CONF_HIGH_POWER_PERCENT, DEFAULT_HIGH_POWER_PERCENT)) / 100.0)
        if current > limit:
            self.state["high_power_alerted"] = True
            self._notify(
                "Sump Pump Monitor: High Power Draw",
                f"{self.name}: current average draw is {current:.1f} W; "
                f"historical average is {baseline:.1f} W "
                f"({float(self.data.get(CONF_HIGH_POWER_PERCENT, DEFAULT_HIGH_POWER_PERCENT)):.0f}% threshold).",
            )
            self._save_task()

    def _evaluate_heavy_cycling(self):
        if self.state.get("heavy_cycling_alerted"):
            return
        if len(self.history) < 10:
            return
        expected = self.expected_cycles_in_window
        if expected is None or expected <= 0:
            return
        current = self.cycles_in_window
        limit = expected * (1.0 + float(self.data.get(CONF_HEAVY_CYCLING_PERCENT, DEFAULT_HEAVY_CYCLING_PERCENT)) / 100.0)
        if current > limit:
            self.state["heavy_cycling_alerted"] = True
            hours = float(self.data.get(CONF_USAGE_WINDOW_HOURS, DEFAULT_USAGE_WINDOW_HOURS))
            self._notify(
                "Sump Pump Monitor: Heavy Cycling",
                f"{self.name}: {current} cycles in the last {hours:g} hours; "
                f"historical expectation is about {expected:.1f}.",
            )
            self._save_task()

    @property
    def history(self) -> list[dict]:
        return list(self.state.get("history", []))

    def _prune_history(self):
        history = sorted(self.state.get("history", []), key=lambda r: float(r.get("start", 0)))
        # History retention is integration-wide and stored in config entry options.
        history_days = int(
            self.entry.options.get(
                CONF_HISTORY_DAYS,
                self.entry.data.get(CONF_HISTORY_DAYS, DEFAULT_HISTORY_DAYS),
            )
        )
        max_cycles = int(
            self.entry.options.get(
                CONF_MAX_HISTORY_CYCLES,
                self.entry.data.get(CONF_MAX_HISTORY_CYCLES, DEFAULT_MAX_HISTORY_CYCLES),
            )
        )
        cutoff = datetime.now(timezone.utc).timestamp() - history_days * 86400
        history = [r for r in history if float(r.get("start", 0)) >= cutoff]
        history = history[-max_cycles:]
        self.state["history"] = history

    @property
    def historical_average_power(self):
        limit = 20
        values = [
            float(r["average_power"])
            for r in self.history[-limit:]
            if r.get("average_power") is not None and float(r["average_power"]) > 0
        ]
        return sum(values) / len(values) if values else None

    @property
    def cycles_in_window(self) -> int:
        cutoff = datetime.now(timezone.utc).timestamp() - float(
            self.data.get(CONF_USAGE_WINDOW_HOURS, DEFAULT_USAGE_WINDOW_HOURS)
        ) * 3600
        return sum(1 for r in self.history if float(r.get("start", 0)) >= cutoff)

    @property
    def expected_cycles_in_window(self) -> float | None:
        usable = self._baseline_cycles()
        if len(usable) < 10:
            return None
        intervals = []
        for previous, current in zip(usable, usable[1:]):
            delta = float(current["start"]) - float(previous["start"])
            if delta > 0:
                intervals.append(delta)
        if not intervals:
            return None
        avg_interval = sum(intervals) / len(intervals)
        return float(self.data.get(CONF_USAGE_WINDOW_HOURS, DEFAULT_USAGE_WINDOW_HOURS)) * 3600 / avg_interval

    def _baseline_cycles(self):
        # Use recent completed cycles, excluding a cycle currently being built.
        limit = 20
        return self.history[-limit:]

    @property
    def sensor_available(self):
        return self._power() is not None

    @property
    def power_monitor_switched_off(self):
        return self._switch_on() is False

    @property
    def power_monitor_unavailable(self):
        return self.state.get("sensor_offline_alerted", False)

    @property
    def running_too_long(self):
        if not self.state.get("running"):
            return False
        return self.current_run_seconds >= float(
            self.data.get(CONF_MAX_RUN_SECONDS, DEFAULT_MAX_RUN_SECONDS)
        )

    @property
    def high_power(self):
        baseline = self.historical_average_power
        samples = self.state.get("current_power_samples", [])
        if baseline is None or not samples:
            return False
        current = sum(float(v) for v in samples) / len(samples)
        return current > baseline * (
            1 + float(self.data.get(CONF_HIGH_POWER_PERCENT, DEFAULT_HIGH_POWER_PERCENT)) / 100
        )

    @property
    def heavy_cycling(self):
        expected = self.expected_cycles_in_window
        if expected is None:
            return False
        return self.cycles_in_window > expected * (
            1 + float(self.data.get(CONF_HEAVY_CYCLING_PERCENT, DEFAULT_HEAVY_CYCLING_PERCENT)) / 100
        )

    @property
    def current_run_seconds(self):
        start = self.state.get("run_start")
        if not start:
            return 0.0
        return max(0.0, datetime.now(timezone.utc).timestamp() - float(start))

    @property
    def last_cycle_duration(self):
        return self.state.get("last_run_duration")

    @property
    def last_cycle_start(self):
        return self.state.get("last_run_start")

    @property
    def last_cycle_end(self):
        return self.state.get("last_run_end")

    @property
    def last_cycle_start_datetime(self):
        value = self.last_cycle_start
        return datetime.fromtimestamp(value, timezone.utc) if value else None

    @property
    def last_cycle_end_datetime(self):
        value = self.last_cycle_end
        return datetime.fromtimestamp(value, timezone.utc) if value else None

    @property
    def average_cycle_duration(self):
        values = [float(r["duration"]) for r in self.history if r.get("duration") is not None]
        return sum(values) / len(values) if values else None

    @property
    def cycles_1h(self):
        return self._cycles_for_hours(1)

    @property
    def cycles_6h(self):
        return self._cycles_for_hours(6)

    @property
    def cycles_24h(self):
        return self._cycles_for_hours(24)

    @property
    def runtime_1h(self):
        return self._runtime_for_hours(1)

    @property
    def runtime_6h(self):
        return self._runtime_for_hours(6)

    @property
    def runtime_24h(self):
        return self._runtime_for_hours(24)

    def _cycles_for_hours(self, hours):
        cutoff = datetime.now(timezone.utc).timestamp() - hours * 3600
        return sum(1 for r in self.history if float(r.get("start", 0)) >= cutoff)

    def _runtime_for_hours(self, hours):
        cutoff = datetime.now(timezone.utc).timestamp() - hours * 3600
        total = 0.0
        for r in self.history:
            start = float(r.get("start", 0))
            if start >= cutoff and r.get("duration") is not None:
                total += float(r["duration"])
        return total

    def _save_task(self):
        self.hass.async_create_task(self._save())

    def _sensor_offline(self):
        if self.state.get("sensor_offline_since") is not None:
            return
        self.state["sensor_offline_since"] = datetime.now(timezone.utc).timestamp()
        self.state["sensor_offline_alerted"] = False
        if self._outage_cancel:
            self._outage_cancel()
        self._outage_cancel = async_call_later(
            self.hass,
            float(self.data.get(CONF_SENSOR_OUTAGE_MINUTES, DEFAULT_SENSOR_OUTAGE_MINUTES)) * 60,
            self._outage_alert,
        )
        self._dispatch_update()
        self._save_task()

    def _clear_sensor_offline(self):
        if self.state.get("sensor_offline_since") is None:
            return
        was_alerted = self.state.get("sensor_offline_alerted")
        self.state["sensor_offline_since"] = None
        self.state["sensor_offline_alerted"] = False
        if self._outage_cancel:
            self._outage_cancel()
            self._outage_cancel = None
        if was_alerted:
            self._notify(
                "Sump Pump Monitor: Power Monitor Back Online",
                f"{self.name}: the power monitor is available again.",
            )
        self._dispatch_update()
        self._save_task()

    @callback
    def _outage_alert(self, _):
        self._outage_cancel = None
        if self.state.get("sensor_offline_since") and not self.state.get("sensor_offline_alerted"):
            self.state["sensor_offline_alerted"] = True
            self._notify(
                "Sump Pump Monitor: Power Monitor Unavailable",
                f"{self.name}: the configured power sensor is unavailable. Pump monitoring is suspended.",
            )
            self._dispatch_update()
            self._save_task()

    def _notify(self, title, message):
        target = self.entry.options.get(
            CONF_NOTIFICATION_TARGET,
            self.entry.data.get(
                CONF_NOTIFICATION_TARGET,
                self.entry.options.get(
                    CONF_NOTIFICATION_SERVICE,
                    self.entry.data.get(CONF_NOTIFICATION_SERVICE, ""),
                ),
            ),
        )
        target = str(target or "").strip()
        if not target:
            return
        if not target.startswith("notify."):
            target = f"notify.{target}"
        self.hass.async_create_task(
            self.hass.services.async_call(
                "notify",
                "send_message",
                {"message": message, "title": title},
                target={"entity_id": target},
                blocking=False,
            )
        )

    async def async_send_test_notification(self):
        target = self.entry.options.get(
            CONF_NOTIFICATION_TARGET,
            self.entry.data.get(
                CONF_NOTIFICATION_TARGET,
                self.entry.options.get(
                    CONF_NOTIFICATION_SERVICE,
                    self.entry.data.get(CONF_NOTIFICATION_SERVICE, ""),
                ),
            ),
        )
        target = str(target or "").strip()
        if not target:
            _LOGGER.warning("No notification target configured for %s", self.name)
            return False
        if not target.startswith("notify."):
            target = f"notify.{target}"
        try:
            await self.hass.services.async_call(
                "notify",
                "send_message",
                {
                    "message": f"Sump Pump Monitor test notification for {self.name}.",
                    "title": "Sump Pump Monitor Test",
                },
                target={"entity_id": target},
                blocking=True,
            )
        except Exception:
            _LOGGER.exception("Failed to send test notification to %s", target)
            return False
        return True
