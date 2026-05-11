"""Standalone unit tests for WLED Progress Bar pure-Python helpers.

These tests import the helper functions directly (without loading the HA
package) to validate the core LED layout logic.

Run with:  pytest tests/test_coordinator_standalone.py -v
"""

import sys
import types

# ── Minimal HA stubs so coordinator.py can be imported without homeassistant ──
# We inject just enough dummy modules to satisfy the import chain.


def _stub_module(name):
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    return mod


for _name in [
    "homeassistant",
    "homeassistant.config_entries",
    "homeassistant.core",
    "homeassistant.helpers",
    "homeassistant.helpers.update_coordinator",
]:
    if _name not in sys.modules:
        _stub_module(_name)


# DataUpdateCoordinator stub
class _FakeCoordinator:
    def __init__(self, *a, **kw):
        pass


sys.modules["homeassistant.helpers.update_coordinator"].DataUpdateCoordinator = _FakeCoordinator
sys.modules["homeassistant.helpers.update_coordinator"].UpdateFailed = Exception
sys.modules["homeassistant.config_entries"].ConfigEntry = object

_ha_core = sys.modules["homeassistant.core"]
_ha_core.HomeAssistant = object
_ha_core.callback = lambda f: f  # no-op decorator stub

# ── Now import the helpers from coordinator ───────────────────────────────────
import importlib  # noqa: E402
import importlib.util  # noqa: E402
import pathlib  # noqa: E402

_COORD_PATH = (
    pathlib.Path(__file__).parent.parent
    / "custom_components"
    / "wled_progress_bar"
    / "coordinator.py"
)

# We load coordinator.py as a standalone module to avoid the HA import chain.
_spec = importlib.util.spec_from_file_location("_coord_helpers", _COORD_PATH)
_mod = importlib.util.module_from_spec(_spec)

# Pre-stub const imports used by coordinator.py
_const_path = (
    pathlib.Path(__file__).parent.parent / "custom_components" / "wled_progress_bar" / "const.py"
)
_const_spec = importlib.util.spec_from_file_location(
    "custom_components.wled_progress_bar.const", _const_path
)
_const_mod = importlib.util.module_from_spec(_const_spec)
_const_spec.loader.exec_module(_const_mod)
sys.modules["custom_components.wled_progress_bar.const"] = _const_mod

_spec.loader.exec_module(_mod)

_parse_rgb = _mod._parse_rgb
_lerp_color = _mod._lerp_color
_build_individual_payload = _mod._build_individual_payload


# ── Tests ──────────────────────────────────────────────────────────────────────


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
        colors = self._led_colors(payload, 0, 9)
        for i in range(4):
            assert colors[i] == (0, 255, 0)
        for i in range(4, 10):
            assert colors[i] == (50, 50, 50)

    def test_filled_reverse(self):
        payload = _build_individual_payload(
            led_start=0,
            led_end=9,
            filled_count=3,
            progress_color=(255, 0, 0),
            background_color=(0, 0, 0),
            gradient_mode=False,
            gradient_start=(0, 0, 255),
            gradient_end=(255, 0, 0),
            reverse=True,
        )
        colors = self._led_colors(payload, 0, 9)
        for i in range(7, 10):
            assert colors[i] == (255, 0, 0)
        for i in range(7):
            assert colors[i] == (0, 0, 0)

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
        colors = self._led_colors(payload, 0, 4)
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
        colors = self._led_colors(payload, 0, 4)
        assert colors[0] == (0, 0, 255)
        assert colors[4] == (0, 255, 0)

    def test_sub_range_physical_indices(self):
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

    def test_zero_filled(self):
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
        colors = self._led_colors(payload, 0, 4)
        for c in colors:
            assert c == (10, 10, 10)

    def test_fully_filled(self):
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
        colors = self._led_colors(payload, 0, 4)
        for c in colors:
            assert c == (0, 200, 100)
