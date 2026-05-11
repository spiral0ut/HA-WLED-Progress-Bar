"""Standalone unit tests for LED layout helper functions.

These tests copy the pure-Python functions from coordinator.py directly so
they can run without any Home Assistant dependencies.

Run with:  pytest tests/test_led_helpers.py -v
"""

# ── Copy of pure helpers (no HA dependencies) ────────────────────────────────


def _parse_rgb(rgb_str: str) -> tuple:
    try:
        r, g, b = (int(x.strip()) for x in rgb_str.split(","))
        return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))
    except Exception:
        return (0, 0, 0)


def _lerp_color(color_a: tuple, color_b: tuple, t: float) -> tuple:
    t = max(0.0, min(1.0, t))
    return (
        int(color_a[0] + (color_b[0] - color_a[0]) * t),
        int(color_a[1] + (color_b[1] - color_a[1]) * t),
        int(color_a[2] + (color_b[2] - color_a[2]) * t),
    )


def _build_individual_payload(
    led_start,
    led_end,
    filled_count,
    progress_color,
    background_color,
    gradient_mode,
    gradient_start,
    gradient_end,
    reverse,
):
    total_leds = led_end - led_start + 1
    bg_rgb = background_color if background_color is not None else (0, 0, 0)
    payload = []
    for offset in range(total_leds):
        physical_idx = led_start + offset
        if reverse:
            in_filled = offset >= (total_leds - filled_count)
        else:
            in_filled = offset < filled_count
        if in_filled:
            if gradient_mode and filled_count > 1:
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
        payload.append(physical_idx)
        payload.extend(color)
    return payload


# ── Helper ────────────────────────────────────────────────────────────────────


def _led_colors(payload, start, end):
    colors = {}
    i = 0
    while i < len(payload):
        idx = payload[i]
        r, g, b = payload[i + 1], payload[i + 2], payload[i + 3]
        colors[idx] = (r, g, b)
        i += 4
    return [colors[led] for led in range(start, end + 1)]


# ── Tests ──────────────────────────────────────────────────────────────────────


class TestParseRGB:
    def test_valid(self):
        assert _parse_rgb("255,0,128") == (255, 0, 128)

    def test_clamps_high(self):
        assert _parse_rgb("300,0,128") == (255, 0, 128)

    def test_clamps_low(self):
        assert _parse_rgb("0,-5,128") == (0, 0, 128)

    def test_with_spaces(self):
        assert _parse_rgb(" 10 , 20 , 30 ") == (10, 20, 30)

    def test_invalid_returns_black(self):
        assert _parse_rgb("not_a_color") == (0, 0, 0)

    def test_wrong_component_count(self):
        assert _parse_rgb("1,2") == (0, 0, 0)

    def test_zeros(self):
        assert _parse_rgb("0,0,0") == (0, 0, 0)

    def test_max(self):
        assert _parse_rgb("255,255,255") == (255, 255, 255)


class TestLerpColor:
    def test_t_zero(self):
        assert _lerp_color((0, 0, 0), (255, 255, 255), 0.0) == (0, 0, 0)

    def test_t_one(self):
        assert _lerp_color((0, 0, 0), (255, 255, 255), 1.0) == (255, 255, 255)

    def test_t_half(self):
        r, g, b = _lerp_color((0, 0, 0), (100, 200, 50), 0.5)
        assert r == 50
        assert g == 100
        assert b == 25

    def test_clamps_above_one(self):
        assert _lerp_color((0, 0, 0), (255, 255, 255), 2.0) == (255, 255, 255)

    def test_clamps_below_zero(self):
        assert _lerp_color((0, 0, 0), (255, 255, 255), -1.0) == (0, 0, 0)

    def test_same_color(self):
        assert _lerp_color((100, 100, 100), (100, 100, 100), 0.7) == (100, 100, 100)


class TestBuildIndividualPayload:
    def test_payload_length(self):
        payload = _build_individual_payload(
            led_start=0,
            led_end=9,
            filled_count=5,
            progress_color=(0, 255, 0),
            background_color=(0, 0, 0),
            gradient_mode=False,
            gradient_start=(0, 0, 255),
            gradient_end=(0, 255, 0),
            reverse=False,
        )
        assert len(payload) == 10 * 4

    def test_filled_forward(self):
        payload = _build_individual_payload(
            led_start=0,
            led_end=9,
            filled_count=4,
            progress_color=(0, 255, 0),
            background_color=(50, 50, 50),
            gradient_mode=False,
            gradient_start=(0, 0, 255),
            gradient_end=(0, 255, 0),
            reverse=False,
        )
        colors = _led_colors(payload, 0, 9)
        for i in range(4):
            assert colors[i] == (0, 255, 0), f"LED {i} should be progress"
        for i in range(4, 10):
            assert colors[i] == (50, 50, 50), f"LED {i} should be background"

    def test_filled_reverse(self):
        payload = _build_individual_payload(
            led_start=0,
            led_end=9,
            filled_count=3,
            progress_color=(255, 0, 0),
            background_color=(0, 0, 0),
            gradient_mode=False,
            gradient_start=(0, 0, 0),
            gradient_end=(0, 0, 0),
            reverse=True,
        )
        colors = _led_colors(payload, 0, 9)
        for i in range(7, 10):
            assert colors[i] == (255, 0, 0), f"LED {i} should be progress"
        for i in range(7):
            assert colors[i] == (0, 0, 0), f"LED {i} should be background"

    def test_background_none_is_black(self):
        payload = _build_individual_payload(
            led_start=0,
            led_end=4,
            filled_count=2,
            progress_color=(0, 200, 0),
            background_color=None,
            gradient_mode=False,
            gradient_start=(0, 0, 0),
            gradient_end=(0, 0, 0),
            reverse=False,
        )
        colors = _led_colors(payload, 0, 4)
        for i in range(2, 5):
            assert colors[i] == (0, 0, 0)

    def test_gradient_endpoints(self):
        payload = _build_individual_payload(
            led_start=0,
            led_end=4,
            filled_count=5,
            progress_color=(0, 0, 0),
            background_color=(0, 0, 0),
            gradient_mode=True,
            gradient_start=(0, 0, 255),
            gradient_end=(0, 255, 0),
            reverse=False,
        )
        colors = _led_colors(payload, 0, 4)
        assert colors[0] == (0, 0, 255)
        assert colors[4] == (0, 255, 0)

    def test_sub_range_indices(self):
        payload = _build_individual_payload(
            led_start=10,
            led_end=14,
            filled_count=3,
            progress_color=(0, 255, 0),
            background_color=(0, 0, 0),
            gradient_mode=False,
            gradient_start=(0, 0, 0),
            gradient_end=(0, 0, 0),
            reverse=False,
        )
        indices = payload[::4]
        assert indices == [10, 11, 12, 13, 14]

    def test_zero_filled_all_background(self):
        payload = _build_individual_payload(
            led_start=0,
            led_end=4,
            filled_count=0,
            progress_color=(0, 255, 0),
            background_color=(10, 10, 10),
            gradient_mode=False,
            gradient_start=(0, 0, 0),
            gradient_end=(0, 0, 0),
            reverse=False,
        )
        colors = _led_colors(payload, 0, 4)
        for c in colors:
            assert c == (10, 10, 10)

    def test_fully_filled_all_progress(self):
        payload = _build_individual_payload(
            led_start=0,
            led_end=4,
            filled_count=5,
            progress_color=(0, 200, 100),
            background_color=(10, 10, 10),
            gradient_mode=False,
            gradient_start=(0, 0, 0),
            gradient_end=(0, 0, 0),
            reverse=False,
        )
        colors = _led_colors(payload, 0, 4)
        for c in colors:
            assert c == (0, 200, 100)

    def test_gradient_reverse(self):
        """Gradient in reverse mode: LED at the far end gets gradient_start."""
        payload = _build_individual_payload(
            led_start=0,
            led_end=4,
            filled_count=5,
            progress_color=(0, 0, 0),
            background_color=(0, 0, 0),
            gradient_mode=True,
            gradient_start=(0, 0, 255),
            gradient_end=(0, 255, 0),
            reverse=True,
        )
        colors = _led_colors(payload, 0, 4)
        # All 5 LEDs filled in reverse; gradient_start at first filled offset
        # (which is led_start=0 when fully filled in reverse), gradient_end at last.
        assert colors[0] == (0, 0, 255)
        assert colors[4] == (0, 255, 0)
