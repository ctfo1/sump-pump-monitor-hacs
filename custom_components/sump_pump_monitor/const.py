DOMAIN = "sump_pump_monitor"
NAME = "Sump Pump Monitor"
STORAGE_VERSION = 1
STORAGE_KEY = "sump_pump_monitor"

CONF_PUMPS = "pumps"
CONF_PUMP_ID = "pump_id"
CONF_NAME = "name"
CONF_POWER_SENSOR = "power_sensor"
CONF_POWER_SWITCH = "power_switch"
CONF_RUNNING_WATTS = "running_watts"
CONF_NOTIFICATION_TARGET = "notification_target"
# Legacy key retained for migration from v0.2.x.
CONF_NOTIFICATION_SERVICE = "notification_service"
CONF_MAX_RUN_SECONDS = "max_run_seconds"
CONF_HIGH_POWER_PERCENT = "high_power_percent"
CONF_USAGE_WINDOW_HOURS = "usage_window_hours"
CONF_HEAVY_CYCLING_PERCENT = "heavy_cycling_percent"
CONF_HISTORY_DAYS = "history_days"
CONF_MAX_HISTORY_CYCLES = "max_history_cycles"

DEFAULT_RUNNING_WATTS = 50.0
DEFAULT_HIGH_POWER_PERCENT = 20.0
DEFAULT_USAGE_WINDOW_HOURS = 6.0
DEFAULT_HEAVY_CYCLING_PERCENT = 50.0
DEFAULT_HISTORY_DAYS = 90
DEFAULT_MAX_HISTORY_CYCLES = 2000
DEFAULT_NOTIFICATION_TARGET = ""
DEFAULT_MAX_RUN_SECONDS = 30.0

EVENT_CYCLE_COMPLETED = "sump_pump_monitor_cycle_completed"

PLATFORMS = ["sensor", "binary_sensor", "number", "select", "button"]
