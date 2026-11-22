# Sump Pump Monitor

A Home Assistant custom integration for monitoring one or more sump pumps using existing Home Assistant power-monitor entities. Each configured pump is represented as a Home Assistant device.

## Monitoring

The integration monitors:

- **Power monitor unavailable** — the selected power sensor is unknown or unavailable. A fixed one-minute grace period is used before an alert is sent; monitoring resumes when the sensor returns.
- **Power monitor switched off** — the optional smart-plug switch is explicitly off. An alert is sent once on an on-to-off transition, and is rearmed when the switch returns on. Its last known state is preserved while unavailable, so a missed on-to-off transition is detected when it returns. The alert latch is persisted across restarts.
- **Pump running too long** — continuous runtime exceeds the configured maximum.
- **High power draw** — the current run's average draw exceeds the historical average of up to the 20 most recent completed cycles by the configured percentage.
- **Heavy cycling** — cycle frequency in the configured rolling window exceeds the historical expected rate. The baseline uses up to 20 recent completed cycles and requires at least 10 completed cycles.

A pump reporting 0 W while its power monitor is available and switched on is a normal **pump off** condition.

## Cycle history

Completed cycles are persisted independently for each pump with their start time, end time, duration, average power, and peak power. History is stored by the integration, not in helper entities or Recorder, and survives Home Assistant restarts.

The **Cycle History** sensor reports the number of retained cycles and a compact summary of the latest cycle. It intentionally does not duplicate the full history in entity attributes.

When a cycle completes, the integration fires the `sump_pump_monitor_cycle_completed` Home Assistant event. The event data contains:

- `pump_id` and `pump_name`
- `start` and `end` timestamps
- `duration` in seconds
- `average_power` and `peak_power` in watts

Automations can listen for this event to process each completed cycle immediately.

Default history retention is **90 days** and **2,000 cycles per pump**. Both limits can be changed from **Cycle history settings**.

## Installation with HACS

1. Open **HACS → Integrations**.
2. Select the three-dot menu → **Custom repositories**.
3. Add this GitHub repository URL and select **Integration**.
4. Install **Sump Pump Monitor** and restart Home Assistant.
5. Go to **Settings → Devices & services → Add integration** and search for **Sump Pump Monitor**.

## Configuration

For each pump, configure its name, power sensor, and optional power-monitor switch. Additional thresholds and rolling-window settings are available as device configuration entities. The integration-wide notification target is a Home Assistant `notify` entity; Notification Group helpers can be selected.

Historical baselines use fixed sample counts: up to 20 recent completed cycles, with a minimum of 10 cycles for heavy-cycling evaluation. These counts are not configuration options.

The integration retains up to 300 power samples for the current run (approximately 50 minutes when the source reports every 10 seconds).

## Operational notes

If Home Assistant starts while a pump is already running, the actual start time is unknowable. Runtime measurement therefore begins when the integration observes the running pump after startup; it does not fabricate a historical start time. If the power sensor becomes unavailable during a run, the unobserved interval is excluded and the incomplete run is omitted from completed-cycle history.

The integration is event-driven and reacts to state changes from the configured power sensor and optional switch. It is intended as a monitoring aid, not as a replacement for independent sump-pump safety measures.
