class AudacDeviceTile extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
    if (!this.content) this._render();
    this._update();
  }

  setConfig(config) {
    if (!config.volume_entity) {
      throw new Error("volume_entity is required");
    }
    this.config = config;
  }

  getCardSize() {
    return 2;
  }

  _render() {
    const card = document.createElement("ha-card");
    card.style.padding = "16px";
    card.innerHTML = `
      <style>
        .audac-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
        .audac-title { font-weight: 700; font-size: 16px; }
        .audac-row { display: grid; grid-template-columns: 1fr; gap: 8px; }
        .audac-btn { border: 1px solid var(--divider-color); border-radius: 10px; padding: 10px; text-align: center; cursor: pointer; }
        .audac-btn.active { background: var(--primary-color); color: var(--text-primary-color); }
        .audac-slider { width: 100%; margin-top: 12px; }
        .audac-source { margin-top: 12px; width: 100%; }
      </style>
      <div class="audac-head">
        <div class="audac-title"></div>
        <div class="audac-state"></div>
      </div>
      <div class="audac-row">
        <div class="audac-btn" id="muteBtn">Mute</div>
      </div>
      <input class="audac-slider" id="vol" type="range" min="0" max="70" step="1" />
      <select class="audac-source" id="source"></select>
    `;

    this.content = card;
    this.appendChild(card);

    card.querySelector("#muteBtn").addEventListener("click", () => {
      if (!this.config.mute_entity) return;
      this._hass.callService("switch", "toggle", { entity_id: this.config.mute_entity });
    });

    card.querySelector("#vol").addEventListener("change", (ev) => {
      this._hass.callService("number", "set_value", {
        entity_id: this.config.volume_entity,
        value: Number(ev.target.value),
      });
    });

    card.querySelector("#source").addEventListener("change", (ev) => {
      if (!this.config.source_entity) return;
      this._hass.callService("select", "select_option", {
        entity_id: this.config.source_entity,
        option: ev.target.value,
      });
    });
  }

  _update() {
    const name = this.config.name || "Audac";
    const mute = this.config.mute_entity ? this._hass.states[this.config.mute_entity] : null;
    const volume = this._hass.states[this.config.volume_entity];
    const source = this.config.source_entity ? this._hass.states[this.config.source_entity] : null;

    if (!volume) return;

    this.content.querySelector(".audac-title").textContent = name;
    this.content.querySelector(".audac-state").textContent = `Atten: ${volume.state} dB`;

    const muteBtn = this.content.querySelector("#muteBtn");
    if (mute) {
      muteBtn.classList.toggle("active", mute.state === "on");
      muteBtn.style.display = "block";
    } else {
      muteBtn.style.display = "none";
    }

    const vol = this.content.querySelector("#vol");
    vol.value = Number(volume.state || 0);

    const sourceSelect = this.content.querySelector("#source");
    if (!source) {
      sourceSelect.style.display = "none";
      return;
    }

    sourceSelect.style.display = "block";
    const options = source.attributes.options || [];
    const current = source.state;

    sourceSelect.innerHTML = options
      .map((opt) => `<option value="${opt}" ${String(opt) === current ? "selected" : ""}>${opt}</option>`)
      .join("");
  }
}

customElements.define("audac-device-tile", AudacDeviceTile);
window.customCards = window.customCards || [];
window.customCards.push({
  type: "audac-device-tile",
  name: "Audac Device Tile",
  description: "Compact tile for Audac MTX zone controls",
});
