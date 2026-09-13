# Sump Pump Monitor

A Home Assistant custom integration inspired by [oester/sump_pump_monitor](https://github.com/oester/sump_monitor).

It monitors sump pumps using an existing Home Assistant power sensor and creates a dedicated Home Assistant device for each configured pump.

## Installation with HACS

1. Open **HACS → Integrations**.
2. Select the three-dot menu → **Custom repositories**.
3. Add this GitHub repository URL.
4. Select **Integration** as the category.
5. Install **Sump Pump Monitor**.
6. Restart Home Assistant.
7. Go to **Settings → Devices & services → Add integration** and search for **Sump Pump Monitor**.

## Repository layout

The integration lives under `custom_components/sump_pump_monitor/`, as required for a Home Assistant custom integration. The repository root contains `hacs.json` and documentation so the repository can be added directly to HACS.

## Status

This is an early development release. Test it before relying on its alerts for critical sump-pump protection.


## Notification service

The configuration flow presents a dropdown populated from the notify services currently registered in Home Assistant. Select **None (notifications disabled)** to disable alerts.
