# WLED Progress Bar for Home Assistant
# UNTESTED - Use at your own risk!

[![HACS Custom][hacs-badge]][hacs-url]
[![GitHub release][release-badge]][release-url]
[![CI][ci-badge]][ci-url]
[![License: MIT][license-badge]](LICENSE)

[hacs-badge]: https://img.shields.io/badge/HACS-Custom-orange.svg
[hacs-url]: https://hacs.xyz
[release-badge]: https://img.shields.io/github/v/release/spiral0ut/HA-WLED-Progress-Bar
[release-url]: https://github.com/spiral0ut/HA-WLED-Progress-Bar/releases
[ci-badge]: https://img.shields.io/github/actions/workflow/status/spiral0ut/HA-WLED-Progress-Bar/ci.yml?branch=main&label=CI
[ci-url]: https://github.com/spiral0ut/HA-WLED-Progress-Bar/actions/workflows/ci.yml
[license-badge]: https://img.shields.io/badge/License-MIT-blue.svg

Turn any [WLED](https://kno.wled.ge/)-connected LED strip into a fully
customisable physical progress bar, thermometer, fluid-level indicator, or
timer display — all driven by any numeric entity in Home Assistant.

---

## Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation — HACS](#installation--hacs-recommended)
- [Installation — Manual](#installation--manual)
- [Lovelace card resource](#lovelace-card-resource)
- [Initial setup](#initial-setup)
- [Options reference](#options-reference)
- [Example configurations](#example-configurations)
- [Lovelace card YAML](#lovelace-card-yaml)
- [Automation examples](#automation-examples)
- [First live-test checklist](#first-live-test-checklist)
- [WLED setup assumptions](#wled-setup-assumptions)
- [Troubleshooting](#troubleshooting)
- [Limitations](#limitations)
- [Roadmap](#roadmap)
- [Contributing](#contributing)

---

## Features

- **Watch any numeric entity** — `sensor`, `input_number`, `number` domains.
- **Min/max scaling** — map any value range (−20–50 °C, 0–1000 L, …) to your strip.
- **Sub-range targeting** — use only a slice of a longer strip via `led_start`/`led_end`.
- **Near-complete colour** — auto-switch to a warning colour near 100 %.
- **Gradient mode** — linearly interpolate colour across all filled LEDs.
- **Configurable background** — dim glow, solid colour, or fully off.
- **Reverse direction** — fill from either end of the strip.
- **HA services** — `render_now`, `set_colors`, `clear_bar`, `turn_off_background`.
- **Custom Lovelace card** — live LED preview, value display, service buttons, GUI editor.
- **HACS compatible**.

---

## Requirements

| Software | Minimum version | Notes |
|---|---|---|
| Home Assistant | 2023.6.0 | Config entry options selectors required |
| WLED firmware | **0.12.0** | Individual LED `"i"` key required |

> **Important — WLED firmware:** This integration uses the `"i"` (individual
> LED) key inside the WLED segment object, introduced in firmware **0.12.0**.
> Older firmware silently ignores that key and the bar will not render. Check
> your WLED version at `http://<your-wled-ip>` → Info, and update if needed.

---

## Installation — HACS (recommended)

HACS lets you install and update custom integrations directly from the HA UI.

### Step 1 — Add the custom repository

1. Open **HACS** in the HA sidebar.
2. Go to **Integrations**.
3. Click the **⋮** (three-dot) menu in the top-right corner.
4. Choose **Custom repositories**.
5. In the dialog:
   - **Repository URL:** `https://github.com/spiral0ut/HA-WLED-Progress-Bar`
   - **Category:** `Integration`
6. Click **Add**. The repository now appears in your HACS integration list.

### Step 2 — Download the integration

1. Search for **WLED Progress Bar** in the HACS Integrations tab.
2. Click the result and then **Download**.
3. Accept the version prompt and click **Download** again.

### Step 3 — Restart Home Assistant

Go to **Settings → System → Restart** and wait for HA to come back online.

### Step 4 — Register the Lovelace card resource

See [Lovelace card resource](#lovelace-card-resource) below.

### Step 5 — Add the integration

Go to **Settings → Devices & Services → Add Integration** and search for
*WLED Progress Bar*.

---

## Installation — Manual

Use this method if you don't have HACS or prefer direct file management.

1. Download `wled_progress_bar.zip` from the
   [latest release](https://github.com/spiral0ut/HA-WLED-Progress-Bar/releases/latest).
2. Extract the zip. You will find a `custom_components/wled_progress_bar/`
   directory inside.
3. Copy the entire `wled_progress_bar/` folder into your HA configuration
   directory:
   ```
   config/
   └── custom_components/
       └── wled_progress_bar/   ← copy here
           ├── __init__.py
           ├── manifest.json
           ├── www/
           │   └── wled-progress-bar-card.js
           └── ...
   ```
4. Restart Home Assistant (**Settings → System → Restart**).
5. Register the Lovelace card resource (see below).
6. Add the integration (**Settings → Devices & Services → Add Integration →
   WLED Progress Bar**).

---

## Lovelace card resource

The Lovelace card JavaScript file is bundled inside the integration. Home
Assistant serves the `www/` sub-directory of every custom component under the
URL path `/local/<domain>/`, so the card is available at:

```
/local/wled_progress_bar/wled-progress-bar-card.js
```

**To register it:**

1. Go to **Settings → Dashboards**.
2. Click the **⋮** menu → **Resources** (or, in older HA, open your dashboard
   in edit mode → **Manage resources**).
3. Click **Add resource**.
4. Enter the URL:
   ```
   /local/wled_progress_bar/wled-progress-bar-card.js
   ```
5. Set the resource type to **JavaScript module**.
6. Click **Create** and reload the page (hard refresh: Ctrl+Shift+R /
   Cmd+Shift+R).

> **After a HACS update** the browser may cache the old version. Do a hard
> refresh or append a `?v=X` cache-buster to the URL in Resources.

---

## Initial setup

1. **Settings → Devices & Services → Add Integration → WLED Progress Bar**.
2. Enter the **IP address or hostname** of your WLED device (e.g. `192.168.1.42`
   or `wled-strip.local`).
3. Select the **source entity** — any `sensor`, `input_number`, or `number`
   entity with a numeric state.
4. Click **Submit**. The integration tests connectivity and auto-detects the
   LED count from WLED's `/json/info` endpoint.
5. A new device and a **Progress** sensor entity are created.
6. Open the integration tile → **Configure** to fine-tune scaling, LED range,
   colours, and update interval.

---

## Options reference

Options are split across two pages in the **Configure** dialog.

### Page 1 — Scaling & LED range

| Option | Default | Description |
|---|---|---|
| `entity_id` | — | Source numeric HA entity |
| `min_value` | `0` | Value mapped to 0 LEDs lit |
| `max_value` | `100` | Value mapped to all LEDs lit |
| `led_count` | auto-detected | Total LEDs on the strip |
| `led_start` | `0` | First LED index to use (0-based) |
| `led_end` | `led_count − 1` | Last LED index to use (inclusive) |
| `reverse` | `false` | Fill from the far end inward |
| `update_interval` | `5` s | Push-to-WLED cadence |
| `brightness` | `128` | WLED global brightness (0–255) |

### Page 2 — Colours

All colours are entered as comma-separated **`r,g,b`** integers (0–255 each),
e.g. `0,255,0` for pure green.

| Option | Default | Description |
|---|---|---|
| `progress_color` | `0,255,0` | Colour of filled LEDs |
| `background_off` | `true` | Set unfilled LEDs to off (black) |
| `background_color` | `0,0,0` | Colour of unfilled LEDs (when not off) |
| `near_complete_threshold` | `90` | % at which the override colour activates |
| `near_complete_color` | `255,165,0` | Colour when above threshold |
| `gradient_mode` | `false` | Interpolate colour across filled LEDs |
| `gradient_start_color` | `0,0,255` | Gradient start (first filled LED) |
| `gradient_end_color` | `0,255,0` | Gradient end (last filled LED) |

> When `gradient_mode` is enabled, `near_complete_color` is not applied —
> gradient takes precedence.

---

## Example configurations

### Temperature thermometer (−20 to 50 °C)

```yaml
# Configure options
entity_id: sensor.outdoor_temperature
min_value: -20
max_value: 50
progress_color: "0,100,255"      # cool blue at low temps
near_complete_threshold: 80      # > 28 °C triggers warning
near_complete_color: "255,50,0"  # hot red
```

### Water tank / fluid level (0–1000 L)

```yaml
entity_id: sensor.water_tank_level
min_value: 0
max_value: 1000
progress_color: "0,150,255"
near_complete_threshold: 90
near_complete_color: "255,120,0"
background_off: false
background_color: "5,5,40"       # dim navy glow when empty
```

### Timer / countdown (100 → 0 %, depleting bar)

```yaml
entity_id: sensor.timer_remaining_percent
min_value: 0
max_value: 100
progress_color: "0,200,0"
near_complete_threshold: 20      # last 20% → red alert
near_complete_color: "220,0,0"
reverse: true                    # bar shrinks from the right
```

### Gradient CPU load bar

```yaml
entity_id: sensor.processor_use
min_value: 0
max_value: 100
gradient_mode: true
gradient_start_color: "0,0,255"  # blue at low load
gradient_end_color: "255,0,0"    # red at high load
brightness: 180
```

---

## Lovelace card YAML

### Minimal

```yaml
type: custom:wled-progress-bar-card
entity: sensor.wled_progress_bar_progress
```

### Full

```yaml
type: custom:wled-progress-bar-card
entity: sensor.wled_progress_bar_progress
title: Water Tank
progress_color: "0,150,255"
background_color: "5,5,40"
near_complete_color: "255,120,0"
near_complete_threshold: 90
gradient: false
show_value: true
show_controls: true
unit: " L"
```

The card also has a **GUI editor** — in the Lovelace UI editor, click
**Add card → Custom: WLED Progress Bar Card** and fill in the form.

---

## Automation examples

### Instant update on significant change

```yaml
alias: "WLED – instant render on large change"
trigger:
  - platform: state
    entity_id: sensor.water_tank_level
condition:
  - condition: template
    value_template: >
      {{ (trigger.to_state.state | float(0)
          - trigger.from_state.state | float(0)) | abs > 20 }}
action:
  - action: wled_progress_bar.render_now
```

### Turn off bar at night

```yaml
alias: "WLED – off at night"
trigger:
  - platform: time
    at: "22:30:00"
action:
  - action: wled_progress_bar.clear_bar
```

### Restore bar in the morning

```yaml
alias: "WLED – on in the morning"
trigger:
  - platform: time
    at: "07:00:00"
action:
  - action: wled_progress_bar.render_now
```

### Temporary colour override

```yaml
alias: "WLED – party mode colours"
trigger:
  - platform: state
    entity_id: input_boolean.party_mode
    to: "on"
action:
  - action: wled_progress_bar.set_colors
    data:
      progress_color: "255,0,200"
      brightness: 255
```

---

## First live-test checklist

Work through this list after installing to confirm everything is working
end-to-end.

- [ ] **WLED reachable** — open `http://<your-wled-ip>` in a browser and
      confirm the WLED web UI loads.
- [ ] **WLED firmware ≥ 0.12.0** — check the version in WLED → Info tab.
- [ ] **WLED effect is Solid** — in WLED UI, set the segment 0 effect to
      *Solid* so individual LED colours are respected. The integration forces
      this on each push, but confirming it manually rules out firmware quirks.
- [ ] **Integration added without error** — Settings → Devices & Services →
      WLED Progress Bar shows no error badge.
- [ ] **Progress sensor has a numeric state** — check the
      `sensor.wled_progress_bar_progress` entity in Developer Tools → States.
- [ ] **Source entity has a numeric state** — confirm your chosen entity is not
      `unavailable` or `unknown`.
- [ ] **LEDs respond within `update_interval` seconds** — change the source
      entity value (or call `render_now`) and watch the strip.
- [ ] **Near-complete colour fires** — set the source entity value above your
      threshold and confirm the colour changes.
- [ ] **`clear_bar` turns everything off** — call the service from Developer
      Tools → Services.
- [ ] **Lovelace card loads** — add the card to a dashboard. If you see
      `"Custom element doesn't exist: wled-progress-bar-card"`, recheck the
      resource URL and do a hard browser refresh.
- [ ] **Card controls work** — click *Render Now* in the card and confirm WLED
      updates.
- [ ] **Debug logs are clean** — enable debug logging (see Troubleshooting) and
      watch for repeated errors.

---

## WLED setup assumptions

1. **Segment 0** — The integration always writes to WLED segment index 0. If
   you have multiple segments in WLED, segment 0 will be overwritten on every
   cycle. Use `led_start`/`led_end` to address a sub-range within segment 0
   instead of creating multiple segments.
2. **Solid effect** — `fx: 0` (Solid) is forced in the API call so the `"i"`
   individual LED colours are applied. All other WLED effects ignore the `"i"`
   key.
3. **No authentication** — Default WLED builds have no HTTP auth. If you
   enabled basic auth in WLED, the integration will receive `401` responses and
   log warnings. Auth support is on the roadmap.
4. **Firmware ≥ 0.12.0** — The `"i"` per-LED key was added in this version.
5. **HTTP only** — Communicates over `http://` on port 80. HTTPS is not
   required and not supported.
6. **Single instance per device** — One config entry per WLED device IP
   (enforced by unique ID).

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| LEDs don't respond at all | WLED not reachable from HA host | Ping WLED IP from HA; check network/firewall |
| LEDs respond but colours wrong | WLED firmware < 0.12.0 | Upgrade firmware |
| Only first LED lights up | `"i"` key ignored by active effect | Set WLED segment 0 effect to *Solid* |
| `Progress` sensor shows `unavailable` | Source entity unavailable | Check source entity state |
| Bar never updates | Coordinator error | Enable debug logs; check HA log for `wled_progress_bar` errors |
| Bar flickers / rapid changes | Update interval too short | Increase `update_interval` to 10–30 s |
| Only part of strip updates | `led_start`/`led_end` misconfigured | Match the physical LED count in WLED Info |
| WLED returns HTTP 401 | Basic auth enabled in WLED | Disable WLED auth or wait for auth support |
| Card not found in Lovelace | Resource not registered or wrong URL | Re-check resource URL; hard-refresh browser |
| Card shows entity unavailable | Sensor entity not yet created | Restart HA; check integration is loaded |

### Enable debug logging

```yaml
# configuration.yaml
logger:
  logs:
    custom_components.wled_progress_bar: debug
```

Then restart HA and watch **Settings → System → Logs**.

---

## Limitations

- **Single segment** — Only WLED segment 0 is targeted. Multi-segment support
  is planned.
- **No WLED auth** — HTTP basic authentication is not implemented yet.
- **Effect forced to Solid** — `fx: 0` is set on every API call. This will
  override any effect you set in WLED for that segment.
- **Gradient disables near-complete override** — By design; gradient colour
  provides its own visual gradient effect.
- **No live HA test environment** — This integration was developed and tested
  against the WLED JSON API specification without a live HA + WLED setup. The
  logic is correct per-spec, but edge cases may surface. Please open a GitHub
  issue with your firmware version and HA logs if something doesn't work.

---

## Roadmap

**v0.2.0 — planned**

- [ ] Configurable segment index (not just segment 0)
- [ ] WLED HTTP basic auth support
- [ ] State-change listener to supplement/replace polling (lower WLED traffic)
- [ ] Optional WLED preset restore on `clear_bar`

**v0.3.0 — ideas**

- [ ] Colour pickers in the Lovelace card editor (replace `r,g,b` text fields)
- [ ] Multi-zone support (map different value ranges to different LED segments)
- [ ] MQTT push mode (bypass HTTP polling entirely)

---

## Contributing

Pull requests and issues are welcome.

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/test_led_helpers.py -v

# Lint + format check
ruff check custom_components/ tests/
ruff format --check custom_components/ tests/
```

Please run both checks before opening a PR. The CI workflow enforces them on
all PRs to `main`.

---

## License

MIT — see [LICENSE](LICENSE).
