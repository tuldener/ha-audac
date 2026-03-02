const CARD_VERSION = "1.0.0";

class AudacMTXCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
    this._expanded = {};
  }

  static getConfigElement() {
    return document.createElement("audac-mtx-card-editor");
  }

  static getStubConfig() {
    return {
      title: "Audac MTX",
      zones: [],
      show_bass_treble: true,
      show_source: true,
      theme: "auto",
    };
  }

  setConfig(config) {
    if (!config) throw new Error("Invalid configuration");
    this._config = {
      title: "Audac MTX",
      zones: [],
      show_bass_treble: true,
      show_source: true,
      theme: "auto",
      ...config,
    };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _getZoneEntities() {
    if (!this._hass) return [];
    const zones = this._config.zones || [];

    if (zones.length > 0) {
      return zones
        .map((z) => {
          const entityId =
            typeof z === "string" ? z : z.entity;
          const entity = this._hass.states[entityId];
          if (!entity) return null;
          return {
            entityId,
            entity,
            name: (typeof z === "object" && z.name) || entity.attributes.friendly_name || entityId,
            icon: (typeof z === "object" && z.icon) || "mdi:speaker",
          };
        })
        .filter(Boolean);
    }

    return Object.keys(this._hass.states)
      .filter((id) => id.startsWith("media_player.") && id.includes("audac"))
      .map((entityId) => ({
        entityId,
        entity: this._hass.states[entityId],
        name: this._hass.states[entityId].attributes.friendly_name || entityId,
        icon: "mdi:speaker",
      }));
  }

  _toggleExpand(entityId) {
    this._expanded[entityId] = !this._expanded[entityId];
    this._render();
  }

  async _callService(domain, service, data) {
    if (this._hass) {
      await this._hass.callService(domain, service, data);
    }
  }

  _handleVolumeChange(entityId, value) {
    this._callService("media_player", "volume_set", {
      entity_id: entityId,
      volume_level: value / 100,
    });
  }

  _handleMuteToggle(entityId, currentMute) {
    this._callService("media_player", "volume_mute", {
      entity_id: entityId,
      is_volume_muted: !currentMute,
    });
  }

  _handleSourceSelect(entityId, source) {
    this._callService("media_player", "select_source", {
      entity_id: entityId,
      source: source,
    });
  }

  _render() {
    if (!this.shadowRoot) return;

    const zones = this._getZoneEntities();
    const isDark = this._config.theme === "dark" || 
      (this._config.theme === "auto" && window.matchMedia("(prefers-color-scheme: dark)").matches);

    this.shadowRoot.innerHTML = `
      <style>${this._getStyles(isDark)}</style>
      <div class="audac-mtx-card ${isDark ? 'dark' : 'light'}">
        <div class="card-header">
          <div class="header-icon">
            <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor">
              <path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/>
            </svg>
          </div>
          <div class="header-content">
            <h2 class="header-title">${this._config.title}</h2>
            <span class="header-subtitle">${zones.length} Zone${zones.length !== 1 ? 'n' : ''} aktiv</span>
          </div>
          <div class="header-badge">${zones.filter(z => z.entity.state === "on").length}/${zones.length}</div>
        </div>
        <div class="zones-container">
          ${zones.length > 0 ? zones.map((z) => this._renderZone(z)).join("") : this._renderEmptyState()}
        </div>
      </div>
    `;

    this._attachEventListeners();
  }

  _renderEmptyState() {
    return `
      <div class="empty-state">
        <svg viewBox="0 0 24 24" width="48" height="48" fill="currentColor" opacity="0.3">
          <path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/>
        </svg>
        <p>Keine Zonen konfiguriert</p>
        <span>Füge Audac MTX Entities zur Konfiguration hinzu</span>
      </div>
    `;
  }

  _renderZone(zone) {
    const { entityId, entity, name, icon } = zone;
    const isExpanded = this._expanded[entityId] || false;
    const volumeLevel = entity.attributes.volume_level || 0;
    const volumePercent = Math.round(volumeLevel * 100);
    const isMuted = entity.attributes.is_volume_muted || false;
    const source = entity.attributes.source || "---";
    const sourceList = entity.attributes.source_list || [];
    const bass = entity.attributes.bass || 0;
    const treble = entity.attributes.treble || 0;
    const isOn = entity.state === "on";
    const isOff = entity.state === "off";

    return `
      <div class="zone-card ${isExpanded ? 'expanded' : ''} ${isMuted ? 'muted' : ''} ${isOff ? 'off' : ''}" data-entity="${entityId}">
        <div class="zone-main" data-toggle="${entityId}">
          <div class="zone-volume-bg" style="width: ${isMuted ? 0 : volumePercent}%"></div>
          <div class="zone-content">
            <div class="zone-icon ${isOn ? 'active' : ''}">
              <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor">
                ${isMuted 
                  ? '<path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z"/>'
                  : '<path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>'
                }
              </svg>
            </div>
            <div class="zone-info">
              <span class="zone-name">${name}</span>
              <span class="zone-detail">
                ${isMuted ? 'Stumm' : volumePercent + '% Lautstärke'}
                ${this._config.show_source ? ' · ' + source : ''}
              </span>
            </div>
            <div class="zone-volume-badge ${isMuted ? 'muted-badge' : ''}">
              ${isMuted ? 'MUTE' : volumePercent + '%'}
            </div>
            <div class="zone-expand-icon ${isExpanded ? 'rotated' : ''}">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                <path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z"/>
              </svg>
            </div>
          </div>
        </div>
        
        ${isExpanded ? this._renderExpandedControls(entityId, volumePercent, isMuted, source, sourceList, bass, treble) : ''}
      </div>
    `;
  }

  _renderExpandedControls(entityId, volumePercent, isMuted, source, sourceList, bass, treble) {
    return `
      <div class="zone-controls">
        <div class="control-section">
          <div class="control-label">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
              <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/>
            </svg>
            Lautstärke
          </div>
          <div class="volume-control">
            <button class="btn-icon btn-mute ${isMuted ? 'active' : ''}" data-mute="${entityId}" data-muted="${isMuted}">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                ${isMuted 
                  ? '<path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z"/>'
                  : '<path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>'
                }
              </svg>
            </button>
            <div class="slider-container">
              <input type="range" class="volume-slider" min="0" max="100" value="${volumePercent}" data-volume="${entityId}" />
              <div class="slider-fill" style="width: ${volumePercent}%"></div>
            </div>
            <span class="volume-value">${volumePercent}%</span>
          </div>
        </div>

        ${this._config.show_source ? `
        <div class="control-section">
          <div class="control-label">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
              <path d="M21 3H3c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h18c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H3V5h18v14zM9 8h2v8H9zm4 2h2v6h-2z"/>
            </svg>
            Quelle
          </div>
          <div class="source-grid">
            ${sourceList.map((s) => `
              <button class="source-btn ${s === source ? 'active' : ''}" data-source="${entityId}" data-value="${s}">
                ${s}
              </button>
            `).join("")}
          </div>
        </div>
        ` : ''}

        ${this._config.show_bass_treble ? `
        <div class="control-section tone-section">
          <div class="tone-control">
            <div class="control-label">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM9 17H7V7h2v10zm4 0h-2V10h2v7zm4 0h-2V13h2v4z"/>
              </svg>
              Bass
            </div>
            <div class="tone-value ${bass > 0 ? 'positive' : bass < 0 ? 'negative' : ''}">${bass > 0 ? '+' : ''}${bass} dB</div>
          </div>
          <div class="tone-control">
            <div class="control-label">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM9 17H7V10h2v7zm4 0h-2V7h2v10zm4 0h-2V13h2v4z"/>
              </svg>
              Höhen
            </div>
            <div class="tone-value ${treble > 0 ? 'positive' : treble < 0 ? 'negative' : ''}">${treble > 0 ? '+' : ''}${treble} dB</div>
          </div>
        </div>
        ` : ''}
      </div>
    `;
  }

  _attachEventListeners() {
    const root = this.shadowRoot;
    if (!root) return;

    root.querySelectorAll("[data-toggle]").forEach((el) => {
      el.addEventListener("click", (e) => {
        if (e.target.closest("[data-mute]") || e.target.closest("[data-volume]") || e.target.closest("[data-source]")) return;
        this._toggleExpand(el.dataset.toggle);
      });
    });

    root.querySelectorAll("[data-mute]").forEach((el) => {
      el.addEventListener("click", (e) => {
        e.stopPropagation();
        this._handleMuteToggle(el.dataset.mute, el.dataset.muted === "true");
      });
    });

    root.querySelectorAll("[data-volume]").forEach((el) => {
      el.addEventListener("input", (e) => {
        const val = parseInt(e.target.value);
        const fill = e.target.closest('.slider-container').querySelector('.slider-fill');
        if (fill) fill.style.width = val + '%';
        const valSpan = e.target.closest('.volume-control').querySelector('.volume-value');
        if (valSpan) valSpan.textContent = val + '%';
      });
      el.addEventListener("change", (e) => {
        this._handleVolumeChange(el.dataset.volume, parseInt(e.target.value));
      });
      el.addEventListener("click", (e) => e.stopPropagation());
    });

    root.querySelectorAll("[data-source]").forEach((el) => {
      el.addEventListener("click", (e) => {
        e.stopPropagation();
        this._handleSourceSelect(el.dataset.source, el.dataset.value);
      });
    });
  }

  _getStyles(isDark) {
    const bg = isDark ? "rgba(30, 33, 40, 0.95)" : "rgba(255, 255, 255, 0.95)";
    const cardBg = isDark ? "rgba(40, 44, 52, 0.8)" : "rgba(245, 247, 250, 0.8)";
    const cardBgHover = isDark ? "rgba(50, 55, 65, 0.9)" : "rgba(235, 238, 245, 0.9)";
    const text = isDark ? "#e4e6eb" : "#1a1c20";
    const textSec = isDark ? "rgba(228, 230, 235, 0.6)" : "rgba(26, 28, 32, 0.5)";
    const accent = "#7c6bf0";
    const accentLight = isDark ? "rgba(124, 107, 240, 0.15)" : "rgba(124, 107, 240, 0.1)";
    const border = isDark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)";
    const mutedColor = "#ef5350";

    return `
      :host {
        display: block;
        --accent: ${accent};
        --accent-light: ${accentLight};
      }

      * { box-sizing: border-box; margin: 0; padding: 0; }

      .audac-mtx-card {
        background: ${bg};
        border-radius: 24px;
        padding: 20px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        color: ${text};
        backdrop-filter: blur(20px);
        border: 1px solid ${border};
      }

      .card-header {
        display: flex;
        align-items: center;
        gap: 14px;
        margin-bottom: 18px;
        padding: 0 4px;
      }

      .header-icon {
        width: 48px;
        height: 48px;
        border-radius: 16px;
        background: linear-gradient(135deg, ${accent}, #a78bfa);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        flex-shrink: 0;
      }

      .header-content { flex: 1; min-width: 0; }

      .header-title {
        font-size: 18px;
        font-weight: 700;
        letter-spacing: -0.3px;
        line-height: 1.3;
      }

      .header-subtitle {
        font-size: 12px;
        color: ${textSec};
        font-weight: 500;
      }

      .header-badge {
        background: ${accentLight};
        color: ${accent};
        font-size: 13px;
        font-weight: 700;
        padding: 6px 12px;
        border-radius: 12px;
        white-space: nowrap;
      }

      .zones-container {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }

      .zone-card {
        background: ${cardBg};
        border-radius: 18px;
        overflow: hidden;
        transition: all 0.3s cubic-bezier(0.25, 0.1, 0.25, 1);
        border: 1px solid transparent;
      }

      .zone-card:hover {
        background: ${cardBgHover};
      }

      .zone-card.expanded {
        border-color: ${isDark ? 'rgba(124, 107, 240, 0.2)' : 'rgba(124, 107, 240, 0.15)'};
        background: ${isDark ? 'rgba(45, 48, 58, 0.9)' : 'rgba(240, 242, 248, 0.95)'};
      }

      .zone-card.muted .zone-volume-bg {
        opacity: 0 !important;
      }

      .zone-card.off {
        opacity: 0.5;
      }

      .zone-main {
        position: relative;
        cursor: pointer;
        padding: 14px 16px;
        overflow: hidden;
      }

      .zone-volume-bg {
        position: absolute;
        top: 0;
        left: 0;
        height: 100%;
        background: linear-gradient(90deg, ${accentLight}, transparent);
        transition: width 0.5s cubic-bezier(0.25, 0.1, 0.25, 1);
        pointer-events: none;
      }

      .zone-content {
        position: relative;
        display: flex;
        align-items: center;
        gap: 12px;
        z-index: 1;
      }

      .zone-icon {
        width: 40px;
        height: 40px;
        border-radius: 12px;
        background: ${isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)'};
        display: flex;
        align-items: center;
        justify-content: center;
        color: ${textSec};
        transition: all 0.3s ease;
        flex-shrink: 0;
      }

      .zone-icon.active {
        background: linear-gradient(135deg, ${accent}, #a78bfa);
        color: white;
      }

      .zone-info {
        flex: 1;
        min-width: 0;
        display: flex;
        flex-direction: column;
        gap: 2px;
      }

      .zone-name {
        font-size: 14px;
        font-weight: 600;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .zone-detail {
        font-size: 11px;
        color: ${textSec};
        font-weight: 500;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .zone-volume-badge {
        font-size: 13px;
        font-weight: 700;
        color: ${accent};
        background: ${accentLight};
        padding: 4px 10px;
        border-radius: 10px;
        white-space: nowrap;
        min-width: 48px;
        text-align: center;
        flex-shrink: 0;
      }

      .zone-volume-badge.muted-badge {
        color: ${mutedColor};
        background: ${isDark ? 'rgba(239, 83, 80, 0.15)' : 'rgba(239, 83, 80, 0.1)'};
        font-size: 11px;
      }

      .zone-expand-icon {
        color: ${textSec};
        transition: transform 0.3s ease;
        flex-shrink: 0;
      }

      .zone-expand-icon.rotated {
        transform: rotate(180deg);
      }

      .zone-controls {
        padding: 4px 16px 16px;
        display: flex;
        flex-direction: column;
        gap: 14px;
        animation: slideDown 0.3s cubic-bezier(0.25, 0.1, 0.25, 1);
      }

      @keyframes slideDown {
        from { opacity: 0; transform: translateY(-8px); }
        to { opacity: 1; transform: translateY(0); }
      }

      .control-section {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }

      .control-label {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        color: ${textSec};
      }

      .volume-control {
        display: flex;
        align-items: center;
        gap: 10px;
      }

      .btn-icon {
        width: 36px;
        height: 36px;
        border-radius: 10px;
        border: none;
        background: ${isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)'};
        color: ${textSec};
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.2s ease;
        flex-shrink: 0;
      }

      .btn-icon:hover {
        background: ${isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)'};
      }

      .btn-mute.active {
        background: ${isDark ? 'rgba(239, 83, 80, 0.2)' : 'rgba(239, 83, 80, 0.12)'};
        color: ${mutedColor};
      }

      .slider-container {
        flex: 1;
        position: relative;
        height: 36px;
        display: flex;
        align-items: center;
        background: ${isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)'};
        border-radius: 10px;
        overflow: hidden;
      }

      .slider-fill {
        position: absolute;
        top: 0;
        left: 0;
        height: 100%;
        background: linear-gradient(90deg, ${accentLight}, ${isDark ? 'rgba(124, 107, 240, 0.25)' : 'rgba(124, 107, 240, 0.18)'});
        border-radius: 10px;
        transition: width 0.1s ease;
        pointer-events: none;
      }

      .volume-slider {
        -webkit-appearance: none;
        appearance: none;
        width: 100%;
        height: 100%;
        background: transparent;
        cursor: pointer;
        position: relative;
        z-index: 2;
        margin: 0;
        padding: 0 12px;
      }

      .volume-slider::-webkit-slider-thumb {
        -webkit-appearance: none;
        width: 16px;
        height: 16px;
        border-radius: 50%;
        background: ${accent};
        box-shadow: 0 2px 6px rgba(124, 107, 240, 0.4);
        cursor: pointer;
        transition: transform 0.15s ease;
      }

      .volume-slider::-webkit-slider-thumb:hover {
        transform: scale(1.2);
      }

      .volume-slider::-moz-range-thumb {
        width: 16px;
        height: 16px;
        border-radius: 50%;
        background: ${accent};
        box-shadow: 0 2px 6px rgba(124, 107, 240, 0.4);
        cursor: pointer;
        border: none;
      }

      .volume-value {
        font-size: 13px;
        font-weight: 700;
        color: ${accent};
        min-width: 36px;
        text-align: right;
        flex-shrink: 0;
      }

      .source-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(90px, 1fr));
        gap: 6px;
      }

      .source-btn {
        padding: 8px 10px;
        border-radius: 10px;
        border: 1px solid ${border};
        background: ${isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.02)'};
        color: ${textSec};
        font-size: 11px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s ease;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .source-btn:hover {
        background: ${isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)'};
        color: ${text};
      }

      .source-btn.active {
        background: ${accentLight};
        color: ${accent};
        border-color: ${isDark ? 'rgba(124, 107, 240, 0.3)' : 'rgba(124, 107, 240, 0.2)'};
      }

      .tone-section {
        flex-direction: row;
        gap: 12px;
      }

      .tone-control {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 6px;
        background: ${isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.02)'};
        padding: 10px 12px;
        border-radius: 12px;
      }

      .tone-value {
        font-size: 18px;
        font-weight: 700;
        color: ${text};
      }

      .tone-value.positive { color: #66bb6a; }
      .tone-value.negative { color: ${mutedColor}; }

      .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 40px 20px;
        gap: 8px;
        color: ${textSec};
      }

      .empty-state p {
        font-size: 14px;
        font-weight: 600;
      }

      .empty-state span {
        font-size: 12px;
        opacity: 0.6;
      }
    `;
  }

  getCardSize() {
    const zones = this._getZoneEntities();
    return 1 + zones.length;
  }
}

class AudacMTXCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
  }

  setConfig(config) {
    this._config = { ...config };
    this._render();
  }

  _render() {
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        .editor {
          padding: 16px;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        .field {
          margin-bottom: 12px;
        }
        label {
          display: block;
          font-size: 12px;
          font-weight: 600;
          margin-bottom: 4px;
          color: var(--primary-text-color, #333);
        }
        input, select {
          width: 100%;
          padding: 8px 12px;
          border: 1px solid var(--divider-color, #ddd);
          border-radius: 8px;
          font-size: 14px;
          background: var(--card-background-color, #fff);
          color: var(--primary-text-color, #333);
        }
        textarea {
          width: 100%;
          padding: 8px 12px;
          border: 1px solid var(--divider-color, #ddd);
          border-radius: 8px;
          font-size: 13px;
          font-family: monospace;
          min-height: 80px;
          background: var(--card-background-color, #fff);
          color: var(--primary-text-color, #333);
        }
        .checkbox-field {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 8px;
        }
        .checkbox-field input { width: auto; }
      </style>
      <div class="editor">
        <div class="field">
          <label>Title</label>
          <input type="text" id="title" value="${this._config.title || 'Audac MTX'}" />
        </div>
        <div class="field">
          <label>Zones (entity IDs, one per line)</label>
          <textarea id="zones">${(this._config.zones || []).join('\n')}</textarea>
        </div>
        <div class="field">
          <label>Theme</label>
          <select id="theme">
            <option value="auto" ${this._config.theme === 'auto' ? 'selected' : ''}>Auto</option>
            <option value="dark" ${this._config.theme === 'dark' ? 'selected' : ''}>Dark</option>
            <option value="light" ${this._config.theme === 'light' ? 'selected' : ''}>Light</option>
          </select>
        </div>
        <div class="checkbox-field">
          <input type="checkbox" id="show_source" ${this._config.show_source !== false ? 'checked' : ''} />
          <label for="show_source">Show Source Selection</label>
        </div>
        <div class="checkbox-field">
          <input type="checkbox" id="show_bass_treble" ${this._config.show_bass_treble !== false ? 'checked' : ''} />
          <label for="show_bass_treble">Show Bass / Treble</label>
        </div>
      </div>
    `;

    this.shadowRoot.getElementById("title").addEventListener("change", (e) => {
      this._config.title = e.target.value;
      this._fireChanged();
    });
    this.shadowRoot.getElementById("zones").addEventListener("change", (e) => {
      this._config.zones = e.target.value.split("\n").map(s => s.trim()).filter(Boolean);
      this._fireChanged();
    });
    this.shadowRoot.getElementById("theme").addEventListener("change", (e) => {
      this._config.theme = e.target.value;
      this._fireChanged();
    });
    this.shadowRoot.getElementById("show_source").addEventListener("change", (e) => {
      this._config.show_source = e.target.checked;
      this._fireChanged();
    });
    this.shadowRoot.getElementById("show_bass_treble").addEventListener("change", (e) => {
      this._config.show_bass_treble = e.target.checked;
      this._fireChanged();
    });
  }

  _fireChanged() {
    const event = new CustomEvent("config-changed", {
      detail: { config: this._config },
      bubbles: true,
      composed: true,
    });
    this.dispatchEvent(event);
  }
}

customElements.define("audac-mtx-card", AudacMTXCard);
customElements.define("audac-mtx-card-editor", AudacMTXCardEditor);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "audac-mtx-card",
  name: "Audac MTX Card",
  description: "A Bubble Card-inspired controller for Audac MTX audio matrices",
  preview: true,
  documentationURL: "https://github.com/ha-audac-mtx",
});

console.info(
  `%c AUDAC-MTX-CARD %c v${CARD_VERSION} `,
  "color: white; background: #7c6bf0; font-weight: 700; padding: 2px 6px; border-radius: 4px 0 0 4px;",
  "color: #7c6bf0; background: #e8e5fc; font-weight: 700; padding: 2px 6px; border-radius: 0 4px 4px 0;"
);
