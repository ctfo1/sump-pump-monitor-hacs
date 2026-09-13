# Configuration

1. Install the integration and restart Home Assistant.
2. Add **Sump Pump Monitor**.
3. Configure one pump at a time.
4. Enter the Home Assistant entity ID of a power sensor reporting watts.
5. Set the wattage above which the pump is considered running.
6. Optionally configure notification service and watchdog thresholds.

Each configured pump becomes its own Home Assistant device. No input_number, input_datetime, counter, timer, or statistics helpers are required.

## Default behavior

* Interval anomaly: alert when an interval changes by more than 25%.
* Spring/resume: an interval of 3 days or more is treated as a resume rather than an interval anomaly.
* Rolling interval baseline: last 5 completed intervals.
* Watchdog: `min(max(rolling_average * multiplier, minimum), maximum)`.
* Power sensor outage: after 2 minutes unavailable/unknown, monitoring is suspended and the watchdog is disarmed.
* Excessive runtime: 30 seconds by default.

The integration stores its runtime state in Home Assistant's storage and restores it after restart.
