# Configuration

## Initial setup

1. Install Sump Pump Monitor and restart Home Assistant.
2. Add **Sump Pump Monitor**.
3. Configure the pump name and the existing Home Assistant power sensor that reports the pump's electrical consumption.
4. Optionally select the smart-plug switch used to power the monitor.
5. Select a notification target if alerts are desired.

Additional pumps can be added from the integration's **Configure** menu. Pump thresholds and entity selections can also be adjusted from the pump device's configuration entities.

## Monitored conditions

### Power monitor unavailable

If the configured power sensor becomes `unknown` or `unavailable`, pump-cycle monitoring is suspended. A fixed one-minute grace period applies before an unavailable alert is sent. This delay is not configurable. When the sensor becomes available again, monitoring resumes and a recovery notification is sent if an outage alert had been issued.

### Power monitor switched off

If an optional power-monitor switch is configured and its state changes from on to off, the integration sends one switched-off alert. The alert latch is persisted across Home Assistant restarts, so a switch that remains off does not generate a new alert on every startup. Returning the switch to on clears the latch and rearms the next on-to-off alert.

If no previous switch state has been recorded, the first known state is treated as a baseline. This avoids a spurious alert merely because the switch is already off during initial setup. If Home Assistant was offline, or the switch entity was unavailable, during an on-to-off transition and the last persisted state was on, the transition is detected when the switch becomes available again and one alert is sent. This detection is independent of power-sensor availability.

A pump drawing 0 W while the monitor is available and switched on is normal and is not an alert.

### Pump running too long

A run begins when power rises above the configured running threshold. If continuous runtime reaches **Maximum Run Duration**, a notification is sent once for that run.

If Home Assistant starts while the pump is already running, the actual start time is unknowable. Runtime measurement begins when the integration observes the running pump after startup. The runtime timer is restored from this new observed start after each restart. If the power sensor becomes unavailable during a run, the unobserved interval is excluded and the incomplete run is omitted from completed-cycle history.

### High power draw

The integration records average and peak power for each completed cycle. The historical average power baseline uses up to the 20 most recent completed cycles with usable average-power values.

During a run, the integration calculates the average power observed so far. If that average exceeds the historical average by **High Power Threshold (%)**, the high-power condition is raised.

The current run's power buffer retains up to 300 samples. At a typical 10-second reporting interval, this represents approximately 50 minutes of readings.

### Heavy cycling

The integration uses recent completed cycle start times to calculate a historical average cycle interval. The configured **Heavy Usage Window** is converted to an expected number of cycles.

The baseline uses up to the 20 most recent completed cycles and requires at least 10 completed cycles before heavy-cycling evaluation becomes active. If the current number of completed cycles in the rolling window exceeds the historical expectation by **Heavy Cycling Threshold (%)**, the heavy-cycling condition is raised.

## Historical cycle storage

Each completed cycle stores:

- Start date/time
- End date/time
- Duration
- Average running power
- Peak running power

Default retention is **90 days** and **2,000 cycles per pump**. Both limits are enforced, with the oldest records removed first.

History is stored in Home Assistant's integration storage and survives Home Assistant restarts. It is separate from Recorder retention.

The **Cycle History** sensor reports the retained cycle count and a compact summary of the latest cycle; it does not expose the full retained history as entity attributes.

When a cycle completes, the integration fires the `sump_pump_monitor_cycle_completed` Home Assistant event. Event data includes `pump_id`, `pump_name`, `start`, `end`, `duration`, `average_power`, and `peak_power`. The timestamps are local-time ISO 8601 strings; duration is in seconds and power values are in watts. Automations can listen for this event to process each completed cycle.

## Default settings

- Running power threshold: **50 W**
- Maximum continuous runtime: **30 seconds**
- High power threshold: **20%**
- High-power baseline: **up to 20 recent completed cycles**
- Heavy usage window: **6 hours**
- Heavy cycling threshold: **50%**
- Heavy-cycling baseline: **at least 10 and up to 20 completed cycles**
- Power-monitor unavailable grace period: **1 minute**, with its original deadline restored after restart
- Current-run power buffer: **300 samples**
- History age: **90 days**
- Maximum cycles per pump: **2,000**
- Notification target: disabled until selected

## Notification target

Notifications use a Home Assistant `notify` entity. Notification Group helpers are supported because they are exposed as notify entities.

Use the integration's **Notification settings** option to change the target. Each pump's **Test Notification** button can be used to verify it.
