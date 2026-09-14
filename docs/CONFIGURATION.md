# Configuration

## Initial setup

1. Install Sump Pump Monitor and restart Home Assistant.
2. Add **Sump Pump Monitor**.
3. Configure the first pump.
4. Select the existing Home Assistant power sensor that reports the pump's electrical consumption in watts.
5. Set the **Running power threshold** above the normal off-state draw.
6. If the power monitor is a controllable smart plug, select its **Power monitor switch**. This allows the integration to distinguish a switched-off plug from an unavailable power sensor.
7. Configure the alert thresholds as appropriate.
8. Select a notification target if alerts are desired.

Additional pumps are added from the integration's **Configure** menu.

## Monitored conditions

### Power monitor unavailable

If the configured power sensor becomes `unknown` or `unavailable` for longer than **Power monitor unavailable delay**, the integration reports the power monitor as unavailable and suspends pump-cycle monitoring until the sensor returns.

### Power monitor switched off

If an optional power-monitor switch is configured and its state is `off`, the integration reports that condition separately. A pump drawing 0 W while the switch is on is normal and is not an alert.

### Pump running too long

A run begins when power rises above the running threshold. If continuous runtime reaches **Maximum continuous runtime**, a notification is sent once for that run.

### High power draw

The integration records average and peak power for every completed cycle. The **historical average power** is calculated from the most recent configured number of completed cycles.

During a run, the integration calculates the average power observed so far. If that average exceeds the historical average by **High power threshold (%)**, the high-power condition is raised.

### Heavy cycling

The integration uses recent completed cycle start times to calculate a historical average cycle interval. The configured **Usage window** is converted to an expected number of cycles.

If the current number of completed cycles in that rolling window exceeds the historical expectation by **Heavy cycling threshold (%)**, the heavy-cycling condition is raised.

Heavy-cycling detection does not activate until **Minimum historical cycles** have been recorded.

## Historical cycle storage

Each completed cycle stores:

- Start date/time
- End date/time
- Duration
- Average running power
- Peak running power

Default retention is **90 days** and **2,000 cycles per pump**. Both limits are enforced, with the oldest records removed first.

History is stored in Home Assistant's integration storage and survives Home Assistant restarts. It is separate from Recorder retention.

## Default settings

- Running power threshold: **50 W**
- Maximum continuous runtime: **30 seconds**
- High power threshold: **20%**
- Power baseline cycles: **20**
- Heavy usage window: **6 hours**
- Heavy cycling threshold: **50%**
- Minimum historical cycles: **5**
- Power monitor unavailable delay: **2 minutes**
- History age: **90 days**
- Maximum cycles per pump: **2,000**
- Notification target: disabled until selected

## Notification target

Notifications use a Home Assistant `notify` entity. Notification Group helpers are supported because they are exposed as notify entities.

Use the integration's **Notification settings** option to change the target. Each pump's **Test Notification** button can be used to verify it.
