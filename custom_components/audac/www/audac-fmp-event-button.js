class AudacFmpEventButton extends HTMLElement {
  static getConfigElement() {
    return document.createElement("audac-fmp-event-button-editor");
  }

  static getStubConfig() {
    return {
      xmp_entry_id: "",
      slot: 1,
      event: 1,
      label: "FMP Event",
      style_mode: "default",
    };
  }

  set hass(hass) {
    this._hass = hass;
    if (!this.content) this._render();
    this._update();
  }

  setConfig(config) {
    if (!config.xmp_entry_id) {
      throw new Error("xmp_entry_id is required");
    }
    const slot = Number(config.slot !== undefined ? config.slot : 1);
    const event = Number(config.event !== undefined ? config.event : 1);
    if (!Number.isInteger(slot) || slot < 1 || slot > 4) {
      throw new Error("slot must be an integer between 1 and 4");
    }
    if (!Number.isInteger(event) || event < 1 || event > 50) {
      throw new Error("event must be an integer between 1 and 50");
    }

    this.config = {
      ...config,
      slot,
      event,
      label: String(config.label !== undefined ? config.label : `Slot ${slot} Event ${event}`),
      style_mode: config.style_mode === "bubble" ? "bubble" : "default",
    };
  }

  getCardSize() {
    return 2;
  }

  _render() {
    const card = document.createElement("ha-card");
    card.className =
      this.config && this.config.style_mode === "bubble" ? "audac-fmp bubble" : "audac-fmp default";
    card.innerHTML = `
      <style>
        @import url('/hacsfiles/Bubble-Card/src/cards/button/styles.css');
        @import url('/hacsfiles/bubble-card/src/cards/button/styles.css');

        ha-card.audac-fmp.default {
          padding: 14px;
        }

        .audac-fmp-wrap {
          display: grid;
          gap: 10px;
        }

        .audac-fmp-head {
          display: flex;
          justify-content: space-between;
          align-items: baseline;
          gap: 8px;
        }

        .audac-fmp-title {
          font-size: 16px;
          font-weight: 700;
          line-height: 1.3;
        }

        .audac-fmp-meta {
          font-size: 12px;
          opacity: 0.75;
          white-space: nowrap;
        }

        .audac-fmp-buttons {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 10px;
        }

        .audac-btn {
          border: 1px solid var(--divider-color);
          border-radius: 14px;
          padding: 10px 12px;
          background: var(--card-background-color);
          color: var(--primary-text-color);
          font-weight: 600;
          cursor: pointer;
        }

        .audac-btn:active {
          transform: scale(0.98);
        }

        .audac-btn.play {
          border-color: color-mix(in srgb, var(--success-color, #2e7d32) 60%, var(--divider-color));
        }

        .audac-btn.stop {
          border-color: color-mix(in srgb, var(--error-color, #c62828) 60%, var(--divider-color));
        }

        .audac-fmp-status {
          font-size: 12px;
          opacity: 0.75;
        }

        ha-card.audac-fmp.bubble {
          padding: 14px;
          border-radius: var(--bubble-border-radius, 22px);
          background: var(
            --bubble-main-background-color,
            color-mix(in srgb, var(--card-background-color) 88%, var(--primary-color))
          );
          border: none;
          box-shadow: var(--ha-card-box-shadow, none);
        }

        ha-card.audac-fmp.bubble .audac-btn {
          border-radius: 999px;
          border: none;
          background: var(--bubble-secondary-background-color, rgba(127, 127, 127, 0.18));
        }
      </style>
      <div class="audac-fmp-wrap">
        <div class="audac-fmp-head">
          <div class="audac-fmp-title" id="title"></div>
          <div class="audac-fmp-meta" id="meta"></div>
        </div>
        <div class="audac-fmp-buttons">
          <button class="audac-btn play" id="play">Play</button>
          <button class="audac-btn stop" id="stop">Stop</button>
        </div>
        <div class="audac-fmp-status" id="status"></div>
      </div>
    `;

    this.content = card;
    this.appendChild(card);

    card.querySelector("#play").addEventListener("click", () => this._sendTrigger(true));
    card.querySelector("#stop").addEventListener("click", () => this._sendTrigger(false));
  }

  _update() {
    if (!this.content || !this.config) return;
    this.content.className = this.config.style_mode === "bubble" ? "audac-fmp bubble" : "audac-fmp default";

    this.content.querySelector("#title").textContent = this.config.label;
    this.content.querySelector("#meta").textContent = `Slot ${this.config.slot} | Event ${this.config.event}`;

    const status = this.content.querySelector("#status");
    status.textContent = this._lastStatus || "Ready";
  }

  async _sendTrigger(start) {
    if (!this._hass || !this.config) return;
    const cmd = `SSTR${this.config.slot}`;
    const arg = `${this.config.event}^${start ? 1 : 0}`;

    try {
      await this._hass.callService("audac", "send_raw_command", {
        entry_id: this.config.xmp_entry_id,
        command: cmd,
        argument: arg,
      });
      this._lastStatus = `${start ? "Play" : "Stop"} sent (${arg})`;
    } catch (err) {
      this._lastStatus = `Error: ${(err && err.message) || err}`;
    }

    this._update();
  }
}

class AudacFmpEventButtonEditor extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  setConfig(config) {
    this._config = {
      xmp_entry_id: "",
      slot: 1,
      event: 1,
      label: "FMP Event",
      style_mode: "default",
      ...config,
    };
    this._render();
  }

  _valueChanged(ev) {
    if (!this._config || !this._hass) return;
    const target = ev.target;
    const key = target.dataset.key;
    if (!key) return;

    let value = target.value;
    if (key === "slot" || key === "event") value = Number(value);

    const newConfig = { ...this._config, [key]: value };
    this._config = newConfig;
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: newConfig },
        bubbles: true,
        composed: true,
      })
    );
  }

  _render() {
    if (!this._hass || !this._config) return;
    if (!this.content) {
      this.content = document.createElement("div");
      this.appendChild(this.content);
    }

    const slotOptions = [1, 2, 3, 4]
      .map((n) => `<option value="${n}" ${Number(this._config.slot) === n ? "selected" : ""}>${n}</option>`)
      .join("");
    const eventOptions = Array.from({ length: 50 }, (_, i) => i + 1)
      .map(
        (n) =>
          `<option value="${n}" ${Number(this._config.event) === n ? "selected" : ""}>${n}</option>`
      )
      .join("");

    this.content.innerHTML = `
      <style>
        .audac-editor {
          display: grid;
          gap: 12px;
          padding: 8px 0;
        }
        .audac-editor label {
          display: grid;
          gap: 4px;
          font-size: 12px;
          opacity: 0.85;
        }
        .audac-editor input,
        .audac-editor select {
          padding: 8px;
          border-radius: 8px;
          border: 1px solid var(--divider-color);
          background: var(--card-background-color);
          color: var(--primary-text-color);
        }
      </style>
      <div class="audac-editor">
        <label>XMP Entry ID
          <input data-key="xmp_entry_id" type="text" value="${this._config.xmp_entry_id || ""}" />
        </label>
        <label>Slot
          <select data-key="slot">${slotOptions}</select>
        </label>
        <label>Event
          <select data-key="event">${eventOptions}</select>
        </label>
        <label>Bezeichnung
          <input data-key="label" type="text" value="${this._config.label || ""}" />
        </label>
        <label>Style
          <select data-key="style_mode">
            <option value="default" ${this._config.style_mode === "default" ? "selected" : ""}>default</option>
            <option value="bubble" ${this._config.style_mode === "bubble" ? "selected" : ""}>bubble</option>
          </select>
        </label>
      </div>
    `;

    this.content.querySelectorAll("input,select").forEach((el) => {
      el.addEventListener("change", this._valueChanged.bind(this));
    });
  }
}

if (!customElements.get("audac-fmp-event-button")) {
  customElements.define("audac-fmp-event-button", AudacFmpEventButton);
}
if (!customElements.get("audac-fmp-event-button-editor")) {
  customElements.define("audac-fmp-event-button-editor", AudacFmpEventButtonEditor);
}

window.customCards = window.customCards || [];
window.customCards.push({
  type: "audac-fmp-event-button",
  name: "Audac FMP Event Button",
  description: "Dashboard button for XMP/FMP trigger events (Play/Stop, optional bubble style)",
  preview: true,
});
