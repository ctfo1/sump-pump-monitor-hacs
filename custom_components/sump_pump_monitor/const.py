DOMAIN = "sump_pump_monitor"
NAME = "Sump Pump Monitor"
STORAGE_VERSION = 1
STORAGE_KEY = "sump_pump_monitor"

CONF_PUMPS = "pumps"
CONF_PUMP_ID = "pump_id"
CONF_NAME = "name"
CONF_POWER_SENSOR = "power_sensor"
CONF_RUNNING_WATTS = "running_watts"
CONF_NOTIFICATION_TARGET = "notification_target"
# Legacy key retained for migration from v0.2.x.
CONF_NOTIFICATION_SERVICE = "notification_service"
CONF_ALERT_MULTIPLIER = "alert_multiplier"
CONF_ALERT_MIN_MINUTES = "alert_min_minutes"
CONF_ALERT_MAX_MINUTES = "alert_max_minutes"
CONF_MAX_RUN_SECONDS = "max_run_seconds"
CONF_INTERVAL_CHANGE_PERCENT = "interval_change_percent"
CONF_RESUME_AFTER_HOURS = "resume_after_hours"
CONF_SENSOR_OUTAGE_MINUTES = "sensor_outage_minutes"

DEFAULT_RUNNING_WATTS = 50.0
DEFAULT_NOTIFICATION_SERVICE = ""
DEFAULT_ALERT_MULTIPLIER = 2.5
DEFAULT_ALERT_MIN_MINUTES = 30.0
DEFAULT_ALERT_MAX_MINUTES = 240.0
DEFAULT_MAX_RUN_SECONDS = 30.0
DEFAULT_INTERVAL_CHANGE_PERCENT = 25.0
DEFAULT_RESUME_AFTER_HOURS = 72.0
DEFAULT_SENSOR_OUTAGE_MINUTES = 2.0

PLATFORMS = ["sensor", "binary_sensor", "number", "button"]
