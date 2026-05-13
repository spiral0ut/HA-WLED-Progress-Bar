"""Coordinator for WLED Progress Bar.

Responsibilities:
1. Subscribe to state changes of the configured HA source entity.
2. Recalculate the LED colour layout whenever the value changes.
3. Push the layout to WLED via the JSON API (POST /json/state).
4. Expose the current percentage for the sensor entity.

WLED JSON API assumptions
─────────────────────────
• Target endpoint: POST http://<host>/json/state
• The body is a JSON object.  Relevant keys used here:
    {
      "bri": 0-255,        # global brightness
      "seg": [             # array of segment objects
        {
          "id": 0,         # segment index (we always use segment 0)
          "i": [           # individual LED colour list (firmware ≥ 0.12.0)
                           # Interleaved format: [led_idx, r, g, b, ...]
                           # OR flat list: [r, g, b, r, g, b, ...] starting
                           # at led_start.  We use the interleaved form so
                           # we can target a sub-range of the strip.
          ]
        }
      ]
    }
• The "i" key (individual LED) is available from WLED firmware 0.12.0+.
  Earlier firmware (< 0.12) does not support it; users should upgrade.
• We always address segment 0.  If the user has multiple segments configured
  in WLED, this may overwrite the first segment's colours.  A future version
  could let the user pick the segment index.
• We do NOT modify the WLED effect or palette – the progress bar is purely
  colour-based (fx=0 / Solid) but we don't force that here to avoid wiping
  other user settings.  If the current effect overrides individual LED colours
  the bar will not be visible; the user should set the WLED segment effect to
  "Solid" manually or via an automation.
• HTTP POST returns 200 on success.  Any other status is treated as an error
  but does NOT crash HA – it is logged and retried on the next cycle.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_BACKGROUND_COLOR,
    CONF_BACKGROUND_OFF,
    CONF_BRIGHTNESS,
    CONF_ENTITY_ID,
    CONF_GRADIENT_END_COLOR,
    CONF_GRADIENT_MODE,
    CONF_GRADIENT_START_COLOR,
    CONF_HOST,
    CONF_LED_COUNT,
    CONF_LED_END,
    CONF_LED_START,
    CONF_MAX_VALUE,
    CONF_MIN_VALUE,
    CONF_NEAR_COMPLETE_COLOR,
    CONF_NEAR_COMPLETE_THRESHOLD,
    CONF_PROGRESS_COLOR,
    CONF_REVERSE,
    CONF_UPDATE_INTERVAL,
    DEFAULT_BACKGROUND_COLOR,
    DEFAULT_BACKGROUND_OFF,
    DEFAULT_BRIGHTNESS,
    DEFAULT_GRADIENT_END_COLOR,
    DEFAULT_GRADIENT_MODE,
    DEFAULT_GRADIENT_START_COLOR,
    DEFAULT_LED_COUNT,
    DEFAULT_MAX_VALUE,
    DEFAULT_MIN_VALUE,
    DEFAULT_NEAR_COMPLETE_COLOR,
    DEFAULT_NEAR_COMPLETE_THRESHOLD,
    DEFAULT_PROGRESS_COLOR,
    DEFAULT_REVERSE,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    WLED_JSON_STATE_PATH,
)

_LOGGER = logging.getLogger(__name__)

_AIOHTTP_TIMEOUT = aiohttp.ClientTimeout(total=10)


def _parse_rgb(rgb_str: str) -> tuple[int, int, int]:
    """Parse 'r,g,b' string to (r, g, b) tuple.  Returns (0,0,0) on failure."""
    try:
        r, g, b = (int(x.strip()) for x in rgb_str.split(","))
        return (
            max(0, min(255, r)),
            max(0, min(255, g)),
            max(0, min(255, b)),
        )
    except Exception:  # noqa: BLE001
        _LOGGER.warning("Invalid RGB string '%s', falling back to (0,0,0)", rgb_str)
        return (0, 0, 0)


def _lerp_color(
    color_a: tuple[int, int, int],
    color_b: tuple[int, int, int],
    t: float,
) -> tuple[int, int, int]:
    """Linearly interpolate between two RGB colours; t ∈ [0.0, 1.0]."""
    t = max(0.0, min(1.0, t))
    return (
        int(color_a[0] + (color_b[0] - color_a[0]) * t),
        int(color_a[1] + (color_b[1] - color_a[1]) * t),
        int(color_a[2] + (color_b[2] - color_a[2]) * t),
    )


def _build_individual_payload(
    led_start: int,
    led_end: int,
    filled_count: int,
    progress_color: tuple[int, int, int],
    background_color: tuple[int, int, int] | None,
    gradient_mode: bool,
    gradient_start: tuple[int, int, int],
    gradient_end: tuple[int, int, int],
    reverse: bool,
) -> list[int | list[int]]:
    """Build the WLED "i" (individual LED) payload list.

    WLED's "i" key accepts an interleaved list of the form:
        [led_index, r, g, b, led_index, r, g, b, ...]
    We emit one entry per LED in [led_start, led_end].

    Parameters
    ----------
    led_start      : first physical LED index on the strip (0-based).
    led_end        : last physical LED index on the strip (inclusive).
    filled_count   : number of LEDs that should show the progress colour.
    progress_color : RGB for the "filled" region.
    background_color: RGB for the "empty" region, or None for off (0,0,0).
    gradient_mode  : if True, use gradient_start→gradient_end instead of
                     a flat progress_color.
    gradient_start : gradient starting colour (for the first filled LED).
    gradient_end   : gradient ending colour (for the last filled LED).
    reverse        : if True, fill from led_end towards led_start.
    """
    total_leds = led_end - led_start + 1
    bg_rgb = background_color if background_color is not None else (0, 0, 0)

    # Build a list of (led_index, r, g, b) for every LED in the range.
    payload: list[int | list[int]] = []
    for offset in range(total_leds):
        physical_idx = led_start + offset

        # Determine whether this LED is in the "filled" zone.
        if reverse:
            # Counting from the far end; fill_start is led_end working backwards.
            in_filled = offset >= (total_leds - filled_count)
        else:
            in_filled = offset < filled_count

        if in_filled:
            if gradient_mode and filled_count > 1:
                # t is 0.0 at the first filled LED, 1.0 at the last.
                if reverse:
                    filled_offset = offset - (total_leds - filled_count)
                else:
                    filled_offset = offset
                t = filled_offset / (filled_count - 1)
                color = _lerp_color(gradient_start, gradient_end, t)
            else:
                color = progress_color
        else:
            color = bg_rgb

        # Interleaved format: [index, r, g, b]
        payload.append(physical_idx)
        payload.extend(color)

    return payload


class WLEDProgressBarCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinates polling + WLED push for one config entry."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._entry = entry
        self._host: str = entry.data[CONF_HOST]
        self._entity_id: str = entry.data.get(CONF_ENTITY_ID, "") or entry.options.get(
            CONF_ENTITY_ID, ""
        )
        self._enabled: bool = False
        self._saved_wled_state: dict[str, Any] | None = None

        # Will be overridden from options each refresh cycle.
        interval = int(entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self._host}",
            update_interval=timedelta(seconds=interval),
        )

    # ── Enable / disable ───────────────────────────────────────────────────────

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    async def async_save_wled_state(self) -> None:
        """GET current WLED state and cache it so we can restore it later."""
        url = f"http://{self._host.rstrip('/')}{WLED_JSON_STATE_PATH}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=_AIOHTTP_TIMEOUT) as resp:
                    if resp.status == 200:
                        self._saved_wled_state = await resp.json(content_type=None)
                    else:
                        _LOGGER.warning(
                            "Could not snapshot WLED state at %s (HTTP %s)", self._host, resp.status
                        )
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("Could not snapshot WLED state at %s: %s", self._host, exc)

    async def async_restore_wled_state(self) -> None:
        """POST the saved WLED state back. Falls back to clear_bar if no snapshot."""
        if self._saved_wled_state is None:
            _LOGGER.debug("No saved WLED state; clearing bar instead")
            await self.async_clear_bar()
            return

        state = dict(self._saved_wled_state)
        # Strip read-only fields WLED won't accept on POST.
        for ro_key in ("nightlight", "udpn", "lor", "time", "mainseg"):
            state.pop(ro_key, None)
        # Remove "i" from segments (write-only in WLED, never returned by GET).
        if "seg" in state:
            state["seg"] = [{k: v for k, v in seg.items() if k != "i"} for seg in state["seg"]]

        await self._async_post_state(state)
        self._saved_wled_state = None

    # ── Public helpers ─────────────────────────────────────────────────────────

    @property
    def current_percent(self) -> float | None:
        """Return the last calculated percentage (0–100), or None if unknown."""
        if self.data:
            return self.data.get("percent")
        return None

    @property
    def current_value(self) -> float | None:
        """Return the raw source entity value."""
        if self.data:
            return self.data.get("value")
        return None

    # ── DataUpdateCoordinator hook ─────────────────────────────────────────────

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch state and push to WLED.  Called by the coordinator timer."""
        # Refresh entity_id in case options were updated.
        entity_id = (
            self._entry.data.get(CONF_ENTITY_ID) or self._entry.options.get(CONF_ENTITY_ID) or ""
        )
        if not entity_id:
            raise UpdateFailed("No source entity configured")

        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unavailable", "unknown"):
            _LOGGER.debug("Source entity %s is unavailable; skipping WLED push", entity_id)
            return self.data or {"value": None, "percent": None, "filled": 0}

        try:
            raw_value = float(state.state)
        except ValueError:
            _LOGGER.warning(
                "Entity %s has non-numeric state '%s'; skipping push",
                entity_id,
                state.state,
            )
            return self.data or {"value": None, "percent": None, "filled": 0}

        if not self._enabled:
            # Return current data so sensor stays live without touching WLED.
            return self.data or {"value": None, "percent": None, "filled": 0}

        return await self._push_to_wled(raw_value)

    # ── Core logic ─────────────────────────────────────────────────────────────

    async def _push_to_wled(
        self,
        raw_value: float,
        overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Calculate LED layout from raw_value and push to WLED."""
        opts = self._entry.options
        ov = overrides or {}

        min_val = float(opts.get(CONF_MIN_VALUE, DEFAULT_MIN_VALUE))
        max_val = float(opts.get(CONF_MAX_VALUE, DEFAULT_MAX_VALUE))
        led_start = int(opts.get(CONF_LED_START, 0))
        led_count = int(opts.get(CONF_LED_COUNT, DEFAULT_LED_COUNT))
        led_end = int(opts.get(CONF_LED_END, led_start + led_count - 1))
        total_leds = led_end - led_start + 1

        brightness = int(ov.get(CONF_BRIGHTNESS, opts.get(CONF_BRIGHTNESS, DEFAULT_BRIGHTNESS)))
        reverse = bool(opts.get(CONF_REVERSE, DEFAULT_REVERSE))
        gradient_mode = bool(opts.get(CONF_GRADIENT_MODE, DEFAULT_GRADIENT_MODE))
        bg_off = bool(opts.get(CONF_BACKGROUND_OFF, DEFAULT_BACKGROUND_OFF))

        progress_color = _parse_rgb(
            ov.get(CONF_PROGRESS_COLOR, opts.get(CONF_PROGRESS_COLOR, DEFAULT_PROGRESS_COLOR))
        )
        bg_color_str = ov.get(
            CONF_BACKGROUND_COLOR, opts.get(CONF_BACKGROUND_COLOR, DEFAULT_BACKGROUND_COLOR)
        )
        background_color = None if bg_off else _parse_rgb(bg_color_str)

        near_threshold = float(
            opts.get(CONF_NEAR_COMPLETE_THRESHOLD, DEFAULT_NEAR_COMPLETE_THRESHOLD)
        )
        near_color = _parse_rgb(
            ov.get(
                CONF_NEAR_COMPLETE_COLOR,
                opts.get(CONF_NEAR_COMPLETE_COLOR, DEFAULT_NEAR_COMPLETE_COLOR),
            )
        )

        grad_start = _parse_rgb(opts.get(CONF_GRADIENT_START_COLOR, DEFAULT_GRADIENT_START_COLOR))
        grad_end = _parse_rgb(opts.get(CONF_GRADIENT_END_COLOR, DEFAULT_GRADIENT_END_COLOR))

        # ── Clamp and calculate percent ────────────────────────────────────────
        value_range = max_val - min_val
        if value_range == 0:
            percent = 0.0
        else:
            percent = max(0.0, min(100.0, (raw_value - min_val) / value_range * 100.0))

        # Near-complete colour override.
        if percent >= near_threshold and not gradient_mode:
            progress_color = near_color

        filled_count = round(percent / 100.0 * total_leds)

        # ── Build WLED payload ────────────────────────────────────────────────
        individual_payload = _build_individual_payload(
            led_start=led_start,
            led_end=led_end,
            filled_count=filled_count,
            progress_color=progress_color,
            background_color=background_color,
            gradient_mode=gradient_mode,
            gradient_start=grad_start,
            gradient_end=grad_end,
            reverse=reverse,
        )

        # WLED JSON state payload.
        # Key explanation:
        #   bri  – brightness (0-255)
        #   seg  – segment array; we always write segment 0.
        #   on   – ensure strip is on
        #   seg[].id – segment index
        #   seg[].i  – individual LED colours (interleaved index + RGB)
        #   seg[].fx – 0 = Solid (no effect); WLED ignores "i" for non-solid
        #              effects, so we force solid here.
        wled_payload = {
            "on": True,
            "bri": brightness,
            "seg": [
                {
                    "id": 0,
                    "fx": 0,  # Force Solid effect so "i" colours are respected.
                    "i": individual_payload,
                }
            ],
        }

        await self._async_post_state(wled_payload)

        return {
            "value": raw_value,
            "percent": percent,
            "filled": filled_count,
            "total": total_leds,
        }

    async def _async_post_state(self, payload: dict[str, Any]) -> None:
        """POST payload to WLED JSON state endpoint.

        Errors are logged but do not raise UpdateFailed so HA stays stable.
        """
        url = f"http://{self._host.rstrip('/')}{WLED_JSON_STATE_PATH}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    timeout=_AIOHTTP_TIMEOUT,
                ) as resp:
                    if resp.status != 200:
                        _LOGGER.warning(
                            "WLED at %s returned HTTP %s for state update",
                            self._host,
                            resp.status,
                        )
        except aiohttp.ClientConnectorError:
            _LOGGER.warning("Cannot connect to WLED at %s – device may be offline", self._host)
        except aiohttp.ServerTimeoutError:
            _LOGGER.warning("WLED at %s timed out during state push", self._host)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error("Unexpected error pushing to WLED at %s: %s", self._host, exc)

    # ── Service helpers ────────────────────────────────────────────────────────

    async def async_render_now(self, overrides: dict[str, Any] | None = None) -> None:
        """Force an immediate render cycle (called by the render_now service)."""
        entity_id = (
            self._entry.data.get(CONF_ENTITY_ID) or self._entry.options.get(CONF_ENTITY_ID) or ""
        )
        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unavailable", "unknown"):
            _LOGGER.info("render_now: entity %s unavailable, skipping", entity_id)
            return
        try:
            raw_value = float(state.state)
        except ValueError:
            return
        result = await self._push_to_wled(raw_value, overrides=overrides)
        self.async_set_updated_data(result)

    async def async_clear_bar(self) -> None:
        """Turn all LEDs in the configured segment to off."""
        opts = self._entry.options
        led_start = int(opts.get(CONF_LED_START, 0))
        led_count = int(opts.get(CONF_LED_COUNT, DEFAULT_LED_COUNT))
        led_end = int(opts.get(CONF_LED_END, led_start + led_count - 1))
        brightness = int(opts.get(CONF_BRIGHTNESS, DEFAULT_BRIGHTNESS))

        # Build an all-black individual payload.
        individual_payload: list[int] = []
        for idx in range(led_start, led_end + 1):
            individual_payload.extend([idx, 0, 0, 0])

        wled_payload = {
            "on": True,
            "bri": brightness,
            "seg": [{"id": 0, "fx": 0, "i": individual_payload}],
        }
        await self._async_post_state(wled_payload)
