/**
 * WLED Progress Bar Card
 * ──────────────────────
 * A Lovelace custom card that:
 *  - Displays the current value and percentage of the linked wled_progress_bar
 *    sensor entity.
 *  - Renders a live colour-matched progress bar preview.
 *  - Provides buttons to call the integration services (render_now, clear_bar,
 *    turn_off_background) directly from the dashboard.
 *  - Supports a GUI card editor (the `getConfigElement` / `getStubConfig`
 *    interface) for easy configuration in the Lovelace UI editor.
 *
 * Installation
 * ────────────
 * Add to resources (Lovelace → Manage resources):
 *   /local/wled_progress_bar/wled-progress-bar-card.js
 *   (or via HACS frontend resource; see README)
 *
 * Minimal YAML config:
 *   type: custom:wled-progress-bar-card
 *   entity: sensor.wled_progress_bar_progress   # the % sensor
 *
 * Full YAML config:
 *   type: custom:wled-progress-bar-card
 *   entity: sensor.wled_progress_bar_progress
 *   title: My LED Bar
 *   progress_color: "0,255,0"
 *   near_complete_color: "255,165,0"
 *   near_complete_threshold: 90
 *   background_color: "20,20,20"
 *   gradient: false
 *   show_value: true
 *   show_controls: true
 *   unit: "%"
 */

// ── Utility helpers ────────────────────────────────────────────────────────────

function parseRGB(str, fallback = [0, 128, 0]) {
  if (!str) return fallback;
  const parts = String(str).split(",").map(Number);
  if (parts.length === 3 && parts.every(n => !isNaN(n))) {
    return parts.map(n => Math.min(255, Math.max(0, Math.round(n))));
  }
  return fallback;
}

function rgbToCss(rgb) {
  return `rgb(${rgb[0]},${rgb[1]},${rgb[2]})`;
}

function lerpColor(a, b, t) {
  t = Math.min(1, Math.max(0, t));
  return [
    Math.round(a[0] + (b[0] - a[0]) * t),
    Math.round(a[1] + (b[1] - a[1]) * t),
    Math.round(a[2] + (b[2] - a[2]) * t),
  ];
}

// ── Card Editor ───────────────────────────────────────────────────────────────

class WLEDProgressBarCardEditor extends HTMLElement {
  constructor() {
    super();
    this._config = {};
    this.attachShadow({ mode: "open" });
  }

  setConfig(config) {
    this._config = { ...config };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._rendered) this._render();
  }

  _render() {
    this._rendered = true;
    const cfg = this._config;
    this.shadowRoot.innerHTML = `
      <style>
        .form { display: grid; gap: 8px; padding: 8px; font-family: var(--paper-font-body1_-_font-family, sans-serif); font-size: 14px; }
        label { display: flex; flex-direction: column; gap: 4px; color: var(--primary-text-color); }
        input, select { background: var(--card-background-color, #fff); border: 1px solid var(--divider-color, #ccc); border-radius: 4px; padding: 6px 8px; color: var(--primary-text-color); font-size: 14px; }
        .row { display: flex; gap: 8px; }
        .row label { flex: 1; }
        h4 { margin: 8px 0 4px; font-size: 13px; font-weight: 600; color: var(--secondary-text-color); text-transform: uppercase; letter-spacing: 0.05em; }
      </style>
      <div class="form">
        <h4>Entity</h4>
        <label>Sensor entity
          <input id="entity" type="text" placeholder="sensor.wled_progress_bar_progress" value="${cfg.entity || ''}">
        </label>
        <label>Title (optional)
          <input id="title" type="text" placeholder="WLED Bar" value="${cfg.title || ''}">
        </label>

        <h4>Display</h4>
        <div class="row">
          <label>Show value
            <select id="show_value">
              <option value="true" ${cfg.show_value !== false ? 'selected' : ''}>Yes</option>
              <option value="false" ${cfg.show_value === false ? 'selected' : ''}>No</option>
            </select>
          </label>
          <label>Show controls
            <select id="show_controls">
              <option value="true" ${cfg.show_controls !== false ? 'selected' : ''}>Yes</option>
              <option value="false" ${cfg.show_controls === false ? 'selected' : ''}>No</option>
            </select>
          </label>
          <label>Unit
            <input id="unit" type="text" placeholder="%" value="${cfg.unit !== undefined ? cfg.unit : '%'}">
          </label>
        </div>

        <h4>Colors (r,g,b)</h4>
        <div class="row">
          <label>Progress color
            <input id="progress_color" type="text" placeholder="0,255,0" value="${cfg.progress_color || '0,255,0'}">
          </label>
          <label>Background color
            <input id="background_color" type="text" placeholder="20,20,20" value="${cfg.background_color || '20,20,20'}">
          </label>
        </div>
        <div class="row">
          <label>Near-complete color
            <input id="near_complete_color" type="text" placeholder="255,165,0" value="${cfg.near_complete_color || '255,165,0'}">
          </label>
          <label>Near-complete threshold (%)
            <input id="near_complete_threshold" type="number" min="0" max="100" step="1" value="${cfg.near_complete_threshold !== undefined ? cfg.near_complete_threshold : 90}">
          </label>
        </div>
        <label>Gradient
          <select id="gradient">
            <option value="false" ${!cfg.gradient ? 'selected' : ''}>Off</option>
            <option value="true" ${cfg.gradient ? 'selected' : ''}>On</option>
          </select>
        </label>
      </div>
    `;

    const fields = ["entity","title","progress_color","background_color","near_complete_color","near_complete_threshold","unit"];
    const boolFields = ["show_value","show_controls","gradient"];

    fields.forEach(id => {
      const el = this.shadowRoot.getElementById(id);
      if (el) el.addEventListener("change", () => this._valueChanged());
    });
    boolFields.forEach(id => {
      const el = this.shadowRoot.getElementById(id);
      if (el) el.addEventListener("change", () => this._valueChanged());
    });
  }

  _valueChanged() {
    const cfg = { ...this._config };
    const get = id => this.shadowRoot.getElementById(id);

    cfg.entity = get("entity").value;
    cfg.title = get("title").value || undefined;
    cfg.progress_color = get("progress_color").value || undefined;
    cfg.background_color = get("background_color").value || undefined;
    cfg.near_complete_color = get("near_complete_color").value || undefined;
    cfg.near_complete_threshold = parseInt(get("near_complete_threshold").value, 10);
    cfg.show_value = get("show_value").value === "true";
    cfg.show_controls = get("show_controls").value === "true";
    cfg.gradient = get("gradient").value === "true";
    cfg.unit = get("unit").value;

    this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: cfg } }));
  }
}

customElements.define("wled-progress-bar-card-editor", WLEDProgressBarCardEditor);

// ── Main Card ─────────────────────────────────────────────────────────────────

class WLEDProgressBarCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
  }

  // Called by HA to provide the card config.
  setConfig(config) {
    if (!config.entity) throw new Error("wled-progress-bar-card: 'entity' is required");
    this._config = {
      title: "WLED Progress Bar",
      show_value: true,
      show_controls: true,
      unit: "%",
      progress_color: "0,255,0",
      background_color: "20,20,20",
      near_complete_color: "255,165,0",
      near_complete_threshold: 90,
      gradient: false,
      ...config,
    };
    this._render();
  }

  // Called by HA whenever relevant state changes.
  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  // ── Rendering ───────────────────────────────────────────────────────────────

  _render() {
    if (!this._config || !this._hass) return;

    const cfg = this._config;
    const stateObj = this._hass.states[cfg.entity];

    let percent = null;
    let displayValue = "—";
    let sourceValue = null;
    let filledLEDs = null;
    let totalLEDs = null;

    if (stateObj) {
      const raw = parseFloat(stateObj.state);
      if (!isNaN(raw)) {
        percent = Math.min(100, Math.max(0, raw));
        displayValue = `${percent.toFixed(1)}${cfg.unit || "%"}`;
      }
      if (stateObj.attributes) {
        sourceValue = stateObj.attributes.source_value;
        filledLEDs  = stateObj.attributes.filled_leds;
        totalLEDs   = stateObj.attributes.total_leds;
      }
    }

    // Determine bar colour at current percent.
    const progressRGB = parseRGB(cfg.progress_color, [0, 200, 0]);
    const nearRGB     = parseRGB(cfg.near_complete_color, [255, 165, 0]);
    const bgRGB       = parseRGB(cfg.background_color, [20, 20, 20]);
    const threshold   = cfg.near_complete_threshold ?? 90;
    const gradientOn  = cfg.gradient === true;

    let barColorCss;
    if (gradientOn) {
      barColorCss = `linear-gradient(to right, ${rgbToCss(progressRGB)}, ${rgbToCss(nearRGB)})`;
    } else {
      const effectiveRGB = (percent !== null && percent >= threshold) ? nearRGB : progressRGB;
      barColorCss = rgbToCss(effectiveRGB);
    }

    const barWidth  = percent !== null ? `${percent}%` : "0%";
    const bgCss     = rgbToCss(bgRGB);

    // Build LED mini-preview (max 60 dots to avoid overflow).
    const previewDots = this._buildLEDPreview(percent, progressRGB, bgRGB, nearRGB, threshold, gradientOn);

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          --card-radius: 12px;
        }
        .card {
          background: var(--ha-card-background, var(--card-background-color, #fff));
          border-radius: var(--ha-card-border-radius, var(--card-radius));
          box-shadow: var(--ha-card-box-shadow, 0 2px 4px rgba(0,0,0,0.1));
          padding: 16px;
          font-family: var(--paper-font-body1_-_font-family, sans-serif);
          color: var(--primary-text-color);
        }
        .header {
          display: flex;
          justify-content: space-between;
          align-items: baseline;
          margin-bottom: 12px;
        }
        .title {
          font-size: 14px;
          font-weight: 600;
          color: var(--secondary-text-color);
          text-transform: uppercase;
          letter-spacing: 0.04em;
        }
        .value {
          font-size: 28px;
          font-weight: 700;
          color: var(--primary-text-color);
          line-height: 1;
        }
        .meta {
          font-size: 12px;
          color: var(--secondary-text-color);
          margin-top: 2px;
        }
        .bar-track {
          height: 20px;
          border-radius: 10px;
          background: ${bgCss};
          overflow: hidden;
          margin: 12px 0 8px;
          position: relative;
        }
        .bar-fill {
          height: 100%;
          width: ${barWidth};
          background: ${gradientOn ? barColorCss : 'none'};
          ${gradientOn ? '' : `background-color: ${barColorCss};`}
          border-radius: 10px;
          transition: width 0.4s ease, background-color 0.3s ease;
        }
        .led-preview {
          display: flex;
          flex-wrap: wrap;
          gap: 2px;
          margin: 6px 0 12px;
        }
        .led-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          flex-shrink: 0;
        }
        .controls {
          display: flex;
          gap: 8px;
          flex-wrap: wrap;
          margin-top: 4px;
        }
        button {
          flex: 1;
          min-width: 80px;
          padding: 7px 10px;
          border: none;
          border-radius: 6px;
          background: var(--primary-color, #03a9f4);
          color: var(--text-primary-color, #fff);
          font-size: 12px;
          font-weight: 600;
          cursor: pointer;
          transition: opacity 0.2s;
        }
        button:hover { opacity: 0.85; }
        button.secondary {
          background: var(--secondary-background-color, #f0f0f0);
          color: var(--primary-text-color);
        }
        .unavailable { color: var(--warning-color, #f57c00); font-size: 13px; }
      </style>
      <ha-card>
        <div class="card">
          <div class="header">
            <span class="title">${this._escape(cfg.title || "WLED Progress Bar")}</span>
            ${cfg.show_value ? `<div><div class="value">${this._escape(displayValue)}</div>${sourceValue !== null && sourceValue !== undefined ? `<div class="meta">source: ${this._escape(String(sourceValue))}</div>` : ''}</div>` : ''}
          </div>

          ${!stateObj || stateObj.state === "unavailable" ? '<div class="unavailable">Entity unavailable</div>' : ''}

          <div class="bar-track">
            <div class="bar-fill"></div>
          </div>

          ${previewDots}

          ${filledLEDs !== null && totalLEDs !== null ? `<div class="meta">${filledLEDs} / ${totalLEDs} LEDs lit</div>` : ''}

          ${cfg.show_controls !== false ? `
          <div class="controls">
            <button id="btn-render">⚡ Render Now</button>
            <button id="btn-clear" class="secondary">⬛ Clear Bar</button>
            <button id="btn-bg-off" class="secondary">🌑 BG Off</button>
          </div>` : ''}
        </div>
      </ha-card>
    `;

    // Attach service call handlers.
    if (cfg.show_controls !== false && this._hass) {
      this._attachButton("btn-render",  "wled_progress_bar", "render_now", {});
      this._attachButton("btn-clear",   "wled_progress_bar", "clear_bar", {});
      this._attachButton("btn-bg-off",  "wled_progress_bar", "turn_off_background", {});
    }
  }

  _buildLEDPreview(percent, progressRGB, bgRGB, nearRGB, threshold, gradientOn) {
    const MAX_DOTS = 60;
    const filled = percent !== null ? Math.round(percent / 100 * MAX_DOTS) : 0;
    const dots = [];

    for (let i = 0; i < MAX_DOTS; i++) {
      let color;
      if (i < filled) {
        if (gradientOn && filled > 1) {
          const t = i / (filled - 1);
          color = lerpColor(progressRGB, nearRGB, t);
        } else {
          color = (percent !== null && percent >= threshold) ? nearRGB : progressRGB;
        }
      } else {
        color = bgRGB;
      }
      dots.push(`<div class="led-dot" style="background:${rgbToCss(color)}"></div>`);
    }
    return `<div class="led-preview">${dots.join("")}</div>`;
  }

  _attachButton(id, domain, service, data) {
    const btn = this.shadowRoot.getElementById(id);
    if (!btn) return;
    btn.addEventListener("click", async () => {
      try {
        await this._hass.callService(domain, service, data);
      } catch (e) {
        console.error(`wled-progress-bar-card: service call ${domain}.${service} failed:`, e);
      }
    });
  }

  _escape(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // ── Card editor interface ─────────────────────────────────────────────────

  static getConfigElement() {
    return document.createElement("wled-progress-bar-card-editor");
  }

  static getStubConfig() {
    return {
      entity: "sensor.wled_progress_bar_progress",
      title: "WLED Progress Bar",
      progress_color: "0,255,0",
      near_complete_color: "255,165,0",
      near_complete_threshold: 90,
      background_color: "20,20,20",
      gradient: false,
      show_value: true,
      show_controls: true,
      unit: "%",
    };
  }

  // ── Card size hint ────────────────────────────────────────────────────────

  getCardSize() {
    return 4;
  }
}

customElements.define("wled-progress-bar-card", WLEDProgressBarCard);

// ── Register with HA card registry ────────────────────────────────────────────

window.customCards = window.customCards || [];
window.customCards.push({
  type: "wled-progress-bar-card",
  name: "WLED Progress Bar Card",
  description: "Display and control a WLED LED strip used as a progress bar.",
  preview: true,
  documentationURL: "https://github.com/your-username/wled_progress_bar",
});

console.info(
  "%c WLED-PROGRESS-BAR-CARD %c v1.0.0 ",
  "color:#fff;background:#01696F;padding:2px 6px;border-radius:3px 0 0 3px;font-weight:700",
  "color:#01696F;background:#e8f5e9;padding:2px 6px;border-radius:0 3px 3px 0"
);
