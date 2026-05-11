# Changelog

All notable changes to **WLED Progress Bar** are documented here.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).  
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

_Nothing yet._

---

## [0.1.0] – 2026-05-11

### Added

- **Core integration** (`custom_components/wled_progress_bar`):
  - Config flow: connect to a WLED device by IP/hostname; auto-detect LED
    count from WLED `/json/info`.
  - Two-step options flow: scaling & LED range, then colour settings.
  - `DataUpdateCoordinator` polling at a configurable interval (default 5 s).
  - WLED JSON API rendering via `POST /json/state` using the `"i"` individual
    LED key (requires WLED firmware ≥ 0.12.0).
  - Per-LED colour calculation: flat progress colour, near-complete colour
    override, and linear gradient mode.
  - Configurable sub-range (`led_start` / `led_end`) to target a portion of a
    longer strip.
  - Reverse direction support.
  - Adjustable brightness (0–255).
  - Background LEDs: fully off or configurable RGB colour.
- **Sensor entity** exposing the current progress percentage (0–100 %) plus
  `source_value`, `filled_leds`, and `total_leds` attributes.
- **Services**: `render_now`, `set_colors`, `clear_bar`,
  `turn_off_background`.
- **Custom Lovelace card** (`www/wled-progress-bar-card.js`):
  - Displays current value, percentage, 60-dot LED mini-preview, and LED
    count.
  - Service action buttons: Render Now, Clear Bar, BG Off.
  - GUI card editor (`getConfigElement`) with live config-changed events.
  - Registers itself in `window.customCards` for the Lovelace card picker.
- **HACS metadata** (`hacs.json`).
- **Unit tests** for all pure-Python LED helper functions (23 tests).
- **CI workflow** (`.github/workflows/ci.yml`): pytest on Python 3.11/3.12
  and Node.js syntax check on the Lovelace card.
- `CHANGELOG.md`, `.gitignore`, `RELEASE_NOTES_v0.1.0.md`.

### Known limitations

- Only WLED segment 0 is targeted.
- WLED HTTP basic auth is not supported.
- `fx: 0` (Solid) is forced on every push; this can conflict with WLED
  presets that set a different effect.
- Gradient mode disables the near-complete colour override.

[Unreleased]: https://github.com/spiral0ut/HA-WLED-Progress-Bar/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/spiral0ut/HA-WLED-Progress-Bar/releases/tag/v0.1.0
