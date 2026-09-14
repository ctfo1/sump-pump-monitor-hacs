# Sump Pump Monitor

A Home Assistant custom integration inspired by [oester/sump_monitor](https://github.com/oester/sump_monitor).

Sump Pump Monitor monitors one or more sump pumps using existing Home Assistant power-monitor entities. Each configured pump is a Home Assistant device.

## Monitoring

The integration focuses on five conditions:

1. **Power monitor unavailable** — the configured power sensor is unavailable/unknown for the configured delay.
2. **Power monitor switched off** — the optional smart-plug switch is explicitly off.
3. **Pump running too long** — continuous runtime exceeds the configured maximum.
4. **High power draw** — the current cycle's average draw exceeds the recent historical average by the configured percentage.
5. **Heavy cycling** — the number of cycles in a rolling usage window exceeds the recent historical expected rate by the configured percentage.

A pump reporting 0 W while its power monitor is available and switched on is a normal **pump off** condition and does not generate an alert.

## Historical cycle data

Every completed cycle is persisted independently for each pump with:

- cycle start date/time
- cycle end date/time
- duration
- average running power
- peak running power

History is retained for **90 days** by default, with a maximum of **2,000 cycles per pump**. The oldest records are discarded first when either limit is reached. Retention can be changed from the integration's **Cycle history settings**.

The historical data is integration-owned persistent storage; it is not stored in Home Assistant helper entities and is not dependent on Recorder retention.

Recent completed cycles are used as the anomaly-detection baselines. A cycle that is currently in progress is never included in the historical baseline.

## Installation with HACS

1. Open **HACS → Integrations**.
2. Select the three-dot menu → **Custom repositories**.
3. Add this GitHub repository URL.
4. Select **Integration** as the category.
5. Install **Sump Pump Monitor**.
6. Restart Home Assistant.
7. Go to **Settings → Devices & services → Add integration** and search for **Sump Pump Monitor**.

## Configuration

The integration uses one Home Assistant config entry and creates one Home Assistant device per configured pump.

For each pump configure:

- Pump name
- Pump power sensor
- Optional power-monitor switch
- Running power threshold
- Maximum continuous runtime
- High-power threshold
- Number of recent cycles used for the power baseline
- Heavy-usage rolling window
- Heavy-cycling threshold
- Minimum historical cycles before heavy-cycling detection
- Power-monitor unavailable delay

The integration-wide notification target is a Home Assistant `notify` entity. A Notification Group helper can be selected directly.

## Entities

Each pump provides power, runtime, cycle-count, usage, historical-power and cycle-time entities, plus binary sensors for the five monitored conditions.

A **Test Notification** button is also provided on each pump device.

## Important

This is an early development release. Do not rely on it as the sole protection for critical sump-pump equipment.
