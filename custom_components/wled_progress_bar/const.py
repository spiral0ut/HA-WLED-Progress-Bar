"""Constants for WLED Progress Bar integration."""

DOMAIN = "wled_progress_bar"

# ── Config / Options keys ────────────────────────────────────────────────────
CONF_HOST = "host"
CONF_ENTITY_ID = "entity_id"
CONF_MIN_VALUE = "min_value"
CONF_MAX_VALUE = "max_value"
CONF_LED_COUNT = "led_count"
CONF_LED_START = "led_start"
CONF_LED_END = "led_end"

# Background: "off" or an RGB colour stored as "r,g,b"
CONF_BACKGROUND_COLOR = "background_color"
CONF_BACKGROUND_OFF = "background_off"

# Progress bar colour (RGB)
CONF_PROGRESS_COLOR = "progress_color"

# Near-complete threshold (0–100 percent) and override colour
CONF_NEAR_COMPLETE_THRESHOLD = "near_complete_threshold"
CONF_NEAR_COMPLETE_COLOR = "near_complete_color"

# Gradient / colour-mode
CONF_GRADIENT_MODE = "gradient_mode"
CONF_GRADIENT_START_COLOR = "gradient_start_color"
CONF_GRADIENT_END_COLOR = "gradient_end_color"

# Reverse LED direction
CONF_REVERSE = "reverse"

# WLED brightness (0–255)
CONF_BRIGHTNESS = "brightness"

# How often (seconds) the coordinator polls the source entity and pushes to WLED
CONF_UPDATE_INTERVAL = "update_interval"

# ── Defaults ─────────────────────────────────────────────────────────────────
DEFAULT_MIN_VALUE = 0.0
DEFAULT_MAX_VALUE = 100.0
DEFAULT_LED_COUNT = 30
DEFAULT_LED_START = 0  # First LED index (0-based)
DEFAULT_LED_END = None  # None → use LED_COUNT-1
DEFAULT_BACKGROUND_OFF = True
DEFAULT_BACKGROUND_COLOR = "0,0,0"
DEFAULT_PROGRESS_COLOR = "0,255,0"
DEFAULT_NEAR_COMPLETE_THRESHOLD = 90
DEFAULT_NEAR_COMPLETE_COLOR = "255,165,0"
DEFAULT_GRADIENT_MODE = False
DEFAULT_GRADIENT_START_COLOR = "0,0,255"
DEFAULT_GRADIENT_END_COLOR = "0,255,0"
DEFAULT_REVERSE = False
DEFAULT_BRIGHTNESS = 128
DEFAULT_UPDATE_INTERVAL = 5  # seconds

# ── WLED API ──────────────────────────────────────────────────────────────────
# All calls target the WLED JSON API endpoint: http://<host>/json/state
# Segment-level colour data is sent inside the "seg" array.
# WLED supports per-LED colouring via the "i" (individual) key within a segment;
# this integration uses that approach for maximum flexibility.
# See: https://kno.wled.ge/interfaces/json-api/
WLED_JSON_STATE_PATH = "/json/state"
WLED_JSON_INFO_PATH = "/json/info"

# ── Services ──────────────────────────────────────────────────────────────────
SERVICE_RENDER_NOW = "render_now"
SERVICE_SET_COLORS = "set_colors"
SERVICE_CLEAR_BAR = "clear_bar"
SERVICE_TURN_OFF_BACKGROUND = "turn_off_background"

# ── Coordinator / DataStore ───────────────────────────────────────────────────
COORDINATOR = "coordinator"
