"""Unit tests for WLED Progress Bar coordinator utilities.

These tests cover pure-Python helper functions and do NOT require a running
Home Assistant instance or a live WLED device.  Run with:

    pytest tests/

To run against a real HA environment use pytest-homeassistant-custom-component
(see pyproject.toml dev dependencies).
"""

import pytest
from custom_components.wled_progress_bar.coordinator import (
    _parse_rgb,
    _lerp_color,
    _build_individual_payload,
)


class TestParseRGB:
    def test_valid(self):
        assert _parse_rgb("255,0,128") == (255, 0, 128)

    def test_clamps(self):
        assert _parse_rgb("300,-5,128") == (255, 0, 128)

    def test_with_spaces(self):
        assert _parse_rgb(" 10 , 20 , 30 ") == (10, 20, 30)

    def test_invalid_returns_fallback(self):
        assert _parse_rgb("not_a_color") == (0, 0, 0)

    def test_wrong_component_count(self):
        assert _parse_rgb("1,2") == (0, 0, 0)


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

    def test_clamps_t(self):
        assert _lerp_color((0, 0, 0), (255, 255, 255), 1.5) == (255, 255, 255)
        assert _lerp_color((0, 0, 0), (255, 255, 255), -0.5) == (0, 0, 0)


class TestBuildIndividualPayload:
    def _led_colors(self, payload, start, end):
        """Extract (r,g,b) for each LED index from interleaved payload."""
        colors = {}
        i = 0
        while i < len(payload):
            idx = payload[i]
            r, g, b = payload[i + 1], payload[i + 2], payload[i + 3]
            colors[idx] = (r, g, b)
            i += 4
        return [colors[led] for led in range(start, end + 1)]

    def test_all_leds_present(self):
        payload = _build_individual_payload(
            led_start=0, led_end=9, filled_count=5,
            progress_color=(0, 255, 0), background_color=(0, 0, 0),
            gradient_mode=False, gradient_start=(0, 0, 255), gradient_end=(0, 255, 0),
            reverse=False,
        )
        # Interleaved: 4 ints per LED (index + r + g + b)
        assert len(payload) == 10 * 4

    def test_filled_forward(self):
        payload = _build_individual_payload(
            led_start=0, led_end=9, filled_count=4,
            progress_color=(0, 255, 0), background_color=(50, 50, 50),
            gradient_mode=False, gradient_start=(0, 0, 255), gradient_end=(0, 255, 0),
            reverse=False,
        )
        colors = self._led_colors(payload, 0, 9)
        # First 4 should be progress colour
        for i in range(4):
            assert colors[i] == (0, 255, 0), f"LED {i} should be progress colour"
        # Remaining 6 should be background
        for i in range(4, 10):
            assert colors[i] == (50, 50, 50), f"LED {i} should be background colour"

    def test_filled_reverse(self):
        payload = _build_individual_payload(
            led_start=0, led_end=9, filled_count=3,
            progress_color=(255, 0, 0), background_color=(0, 0, 0),
            gradient_mode=False, gradient_start=(0, 0, 255), gradient_end=(255, 0, 0),
            reverse=True,
        )
        colors = self._led_colors(payload, 0, 9)
        # Last 3 should be progress colour
        for i in range(7, 10):
            assert colors[i] == (255, 0, 0), f"LED {i} should be progress colour"
        for i in range(7):
            assert colors[i] == (0, 0, 0), f"LED {i} should be background"

    def test_background_off(self):
        """background_color=None should produce (0,0,0) for background LEDs."""
        payload = _build_individual_payload(
            led_start=0, led_end=4, filled_count=2,
            progress_color=(0, 200, 0), background_color=None,
            gradient_mode=False, gradient_start=(0, 0, 0), gradient_end=(0, 0, 0),
            reverse=False,
        )
        colors = self._led_colors(payload, 0, 4)
        for i in range(2, 5):
            assert colors[i] == (0, 0, 0)

    def test_gradient(self):
        payload = _build_individual_payload(
            led_start=0, led_end=4, filled_count=5,
            progress_color=(0, 0, 0), background_color=(0, 0, 0),
            gradient_mode=True, gradient_start=(0, 0, 255), gradient_end=(0, 255, 0),
            reverse=False,
        )
        colors = self._led_colors(payload, 0, 4)
        # LED 0 should be gradient_start, LED 4 should be gradient_end
        assert colors[0] == (0, 0, 255)
        assert colors[4] == (0, 255, 0)

    def test_sub_range(self):
        """Verify led_start offset is applied correctly to physical indices."""
        payload = _build_individual_payload(
            led_start=10, led_end=14, filled_count=3,
            progress_color=(0, 255, 0), background_color=(0, 0, 0),
            gradient_mode=False, gradient_start=(0, 0, 0), gradient_end=(0, 0, 0),
            reverse=False,
        )
        # Physical indices should be 10-14
        indices = payload[::4]
        assert indices == [10, 11, 12, 13, 14]
