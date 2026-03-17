const CARD_VERSION = "3.14.1";

// ─── i18n ───────────────────────────────────────────────────────────
const _mtxLang = () => {
  try { return document.querySelector('home-assistant')?.hass?.language || 'en'; } catch(e) { return 'en'; }
};
const _mtxI18n = {
  de: {
    zones: 'Zonen', zone: 'Zone', zone_1: 'Zone', zone_n: 'Zonen',
    no_zones: 'Keine Zonen gefunden',
    no_zones_hint: 'Audac MTX Integration einrichten oder Zonen manuell konfigurieren',
    muted: 'Stumm', linked_zones: 'Gekoppelte Zonen',
    volume: 'Lautst\u00e4rke', source: 'Quelle', bass: 'Bass', treble: 'H\u00f6hen',
    title: 'Titel', accent_color: 'Akzentfarbe', reset: 'Standard',
    accent_hint: 'Standard: #7c6bf0 (Violett)', design: 'Design',
    auto: 'Automatisch', dark: 'Dunkel', light: 'Hell',
    show_source: 'Quellenauswahl anzeigen', show_bass_treble: 'Bass / H\u00f6hen anzeigen',
    auto_first_zone: '-- Automatisch (erste Zone) --',
    title_optional: 'Titel (optional)', auto_from_entity: 'Automatisch vom Entity',
    desc_main: 'Alle Zonen mit Lautst\u00e4rke, Quelle, Bass & H\u00f6hen',
    desc_zones: 'Zonen\u00fcbersicht (kompakt)',
    desc_volume: 'Lautst\u00e4rke-Regler f\u00fcr eine einzelne Zone',
    desc_source: 'Quellenauswahl f\u00fcr eine einzelne Zone',
    desc_bass: 'Bass-Regler f\u00fcr eine einzelne Zone',
    desc_treble: 'H\u00f6hen-Regler f\u00fcr eine einzelne Zone',
    name_volume: 'Audac MTX Lautst\u00e4rke', name_source: 'Audac MTX Quelle',
    name_bass: 'Audac MTX Bass', name_treble: 'Audac MTX H\u00f6hen',
    name_zones: 'Audac MTX Zonen',
    entity_not_found: 'Entity nicht gefunden',
    none_configured: '(keine konfiguriert)',
  },
  en: {
    zones: 'Zones', zone: 'Zone', zone_1: 'Zone', zone_n: 'Zones',
    no_zones: 'No zones found',
    no_zones_hint: 'Set up Audac MTX integration or configure zones manually',
    muted: 'Muted', linked_zones: 'Linked zones',
    volume: 'Volume', source: 'Source', bass: 'Bass', treble: 'Treble',
    title: 'Title', accent_color: 'Accent color', reset: 'Default',
    accent_hint: 'Default: #7c6bf0 (Violet)', design: 'Design',
    auto: 'Automatic', dark: 'Dark', light: 'Light',
    show_source: 'Show source selection', show_bass_treble: 'Show bass / treble',
    auto_first_zone: '-- Automatic (first zone) --',
    title_optional: 'Title (optional)', auto_from_entity: 'Automatic from entity',
    desc_main: 'All zones with volume, source, bass & treble',
    desc_zones: 'Zone overview (compact)',
    desc_volume: 'Volume control for a single zone',
    desc_source: 'Source selection for a single zone',
    desc_bass: 'Bass control for a single zone',
    desc_treble: 'Treble control for a single zone',
    name_volume: 'Audac MTX Volume', name_source: 'Audac MTX Source',
    name_bass: 'Audac MTX Bass', name_treble: 'Audac MTX Treble',
    name_zones: 'Audac MTX Zones',
    entity_not_found: 'Entity not found',
    none_configured: '(none configured)',
  },
};
function mtxT(key) { const l = _mtxLang(); return (_mtxI18n[l] || _mtxI18n['en'])[key] || _mtxI18n['en'][key] || key; }
function mtxPlural(count, one, many) { return count === 1 ? one : many; }
function mtxLinkedNames(hass, zoneNumbers) {
  if (!hass || !zoneNumbers || zoneNumbers.length === 0) return '';
  const names = [];
  for (const zNum of zoneNumbers) {
    const match = Object.keys(hass.states).find(id =>
      id.startsWith('media_player.') && id.includes('audac_mtx') &&
      hass.states[id]?.attributes?.zone_number === zNum
    );
    if (match) {
      const fn = hass.states[match].attributes.friendly_name || '';
      names.push(mtxShortName(fn, 'Audac MTX'));
    } else {
      names.push('Zone ' + zNum);
    }
  }
  return names.join(', ');
}

// MUST be at top: HA reads this synchronously to know which custom elements to wait for
window.customCards = window.customCards || [];
[
  { type: "audac-mtx-card",        name: "Audac MTX",         description: "Multi-zone Audac MTX audio matrix card", preview: true, documentationURL: "https://github.com/FX6W9WZK/ha-audac" },
  { type: "audac-mtx-volume-card", name: "Audac MTX Volume",  description: "Volume control for a zone", preview: true },
  { type: "audac-mtx-source-card", name: "Audac MTX Source",  description: "Source selection for a zone", preview: true },
  { type: "audac-mtx-bass-card",   name: "Audac MTX Bass",    description: "Bass control for a zone", preview: true },
  { type: "audac-mtx-treble-card", name: "Audac MTX Treble",  description: "Treble control for a zone", preview: true },
].forEach(card => {
  if (!window.customCards.find(c => c.type === card.type)) {
    window.customCards.push(card);
  }
});

/** Escapes HTML special characters to prevent XSS when injecting user-defined strings. */
function mtxEscape(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}


/** Strip integration name prefix from zone friendly name.
 *  e.g. "Audac MTX Bar" -> "Bar", "Audac MTX Zone 3" -> "Zone 3" */
function mtxShortName(fullName, cardTitle) {
  if (!fullName) return fullName;
  // Strip card title prefix (e.g. "Audac MTX ")
  if (cardTitle && fullName.startsWith(cardTitle + " ")) {
    return fullName.slice(cardTitle.length + 1);
  }
  // Fallback: strip common prefixes like "Audac MTX "
  return fullName.replace(/^Audac MTX\s+/i, "") || fullName;
}

/** Converts a hex color (#rrggbb) to an "r, g, b" string for use in rgba(). */
function mtxHexToRgb(hex) {
  const c = hex.replace("#", "");
  const r = parseInt(c.substring(0, 2), 16);
  const g = parseInt(c.substring(2, 4), 16);
  const b = parseInt(c.substring(4, 6), 16);
  return `${r}, ${g}, ${b}`;
}

/** Returns a debounced version of fn that only fires after `wait` ms of silence. */
function mtxDebounce(fn, wait = 300) {
  let timer;
  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), wait);
  };
}

const MTX_ICONS = {
  music: '<path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/>',
  speaker: '<path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>',
  speakerMuted: '<path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z"/>',
  speakerSmall: '<path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/>',
  source: '<path d="M21 3H3c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h18c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H3V5h18v14zM9 8h2v8H9zm4 2h2v6h-2z"/>',
  bass: '<path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/>',
  treble: '<path d="M12 3l.01 10.55c-.59-.34-1.27-.55-2-.55C7.79 13 6 14.79 6 17s1.79 4 4.01 4S14 19.21 14 17V7h4V3h-6z"/>',
  chevron: '<path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z"/>',
  equalizer: '<path d="M10 20h4V4h-4v16zm-6 0h4v-8H4v8zM16 9v11h4V9h-4z"/>',
};

function mtxThemeVars(isDark, accentHex) {
  const accent = accentHex || "#7c6bf0";
  const rgb = mtxHexToRgb(accent);
  return {
    volBgStart: isDark ? `rgba(${rgb}, 0.38)` : `rgba(${rgb}, 0.26)`,
    volBgMid:   isDark ? `rgba(${rgb}, 0.14)` : `rgba(${rgb}, 0.09)`,
    
    
    
    text: isDark ? "#e4e6eb" : "#1a1c20",
    textSec: isDark ? "rgba(228, 230, 235, 0.6)" : "rgba(26, 28, 32, 0.5)",
    accent,
    accentLight: isDark ? `rgba(${rgb}, 0.15)` : `rgba(${rgb}, 0.1)`,
    accentMid: isDark ? `rgba(${rgb}, 0.25)` : `rgba(${rgb}, 0.18)`,
    accentShadow: `rgba(${rgb}, 0.4)`,
    accentSecond: accentHex ? accent : "#a78bfa",
    border: isDark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)",
    mutedColor: "#ef5350",
    isDark,
  };
}

function mtxIsDark(theme) {
  return theme === "dark" || (theme === "auto" && window.matchMedia("(prefers-color-scheme: dark)").matches);
}

function mtxSvg(icon, size = 22) {
  return `<svg viewBox="0 0 24 24" width="${size}" height="${size}" fill="currentColor">${MTX_ICONS[icon]}</svg>`;
}

function mtxAutoDiscover(hass) {
  if (!hass) return [];
  return Object.keys(hass.states)
    .filter((id) => {
      if (!id.startsWith("media_player.") || !id.includes("audac_mtx")) return false;
      // Respect zone_visible attribute (set by integration when zone is hidden)
      const visible = hass.states[id]?.attributes?.zone_visible;
      if (visible === false) return false;
      // Hide slave zones (linked_to is non-empty array or non-zero int)
      const linked = hass.states[id]?.attributes?.linked_to;
      if (Array.isArray(linked) && linked.length > 0) return false;
      if (typeof linked === 'number' && linked !== 0) return false;
      return true;
    })
    .sort();
}

function mtxBaseStyles(t) {
  return `
    :host { display: block; --accent: ${t.accent}; --accent-light: ${t.accentLight}; }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    .mtx-card {
      background: var(--ha-card-background, var(--card-background-color, ${t.isDark ? "rgba(30,33,40,0.95)" : "rgba(255,255,255,0.95)"}));
      border-radius: var(--ha-card-border-radius, 25px); padding: 16px;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      color: ${t.text}; border: 1px solid var(--ha-card-border-color, ${t.border});
      box-shadow: var(--ha-card-box-shadow, none);
    }
    .mtx-header {
      display: flex; align-items: center; gap: 14px; margin-bottom: 16px; padding: 0 4px;
    }
    .mtx-header-icon {
      width: 38px; height: 38px; border-radius: 50%;
      background: linear-gradient(135deg, ${t.accent}, #a78bfa);
      display: flex; align-items: center; justify-content: center; color: white; flex-shrink: 0;
    }
    .mtx-header-content { flex: 1; min-width: 0; }
    .mtx-header-title { font-size: 14px; font-weight: 700; letter-spacing: -0.3px; line-height: 1.3; }
    .mtx-header-sub { font-size: 11px; color: ${t.textSec}; font-weight: 500; }
    .mtx-header-badge {
      background: ${t.accentLight}; color: ${t.accent};
      font-size: 13px; font-weight: 700; padding: 5px 11px; border-radius: 12px; white-space: nowrap;
    }
    .mtx-label {
      display: flex; align-items: center; gap: 6px;
      font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; color: ${t.textSec};
    }
    .mtx-slider-wrap {
      flex: 1; position: relative; height: 36px; display: flex; align-items: center;
      background: ${t.isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)'}; border-radius: 10px; overflow: hidden;
    }
    .mtx-slider-fill {
      position: absolute; top: 0; left: 0; height: 100%;
      background: linear-gradient(90deg, ${t.accentLight}, ${t.accentMid});
      border-radius: 10px; transition: width 0.1s ease; pointer-events: none;
    }
    .mtx-slider {
      -webkit-appearance: none; appearance: none;
      width: 100%; height: 100%; background: transparent;
      cursor: pointer; position: relative; z-index: 2; margin: 0; padding: 0 12px;
    }
    .mtx-slider::-webkit-slider-thumb {
      -webkit-appearance: none; width: 16px; height: 16px; border-radius: 50%;
      background: ${t.accent}; box-shadow: 0 2px 6px ${t.accentShadow};
      cursor: pointer; transition: transform 0.15s ease;
    }
    .mtx-slider::-webkit-slider-thumb:hover { transform: scale(1.2); }
    .mtx-slider::-moz-range-thumb {
      width: 16px; height: 16px; border-radius: 50%;
      background: ${t.accent}; box-shadow: 0 2px 6px ${t.accentShadow}; cursor: pointer; border: none;
    }
    .mtx-val {
      font-size: 13px; font-weight: 700; color: ${t.accent};
      min-width: 42px; text-align: right; flex-shrink: 0; line-height: 1.2;
    }
    .mtx-val small { font-size: 10px; font-weight: 500; color: ${t.textSec}; }
    .mtx-btn {
      width: 36px; height: 36px; border-radius: 10px; border: none;
      background: ${t.isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)'};
      color: ${t.textSec}; cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      transition: all 0.2s ease; flex-shrink: 0;
    }
    .mtx-btn:hover { background: ${t.isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)'}; }
    .mtx-btn.active-mute {
      background: ${t.isDark ? 'rgba(239,83,80,0.2)' : 'rgba(239,83,80,0.12)'}; color: ${t.mutedColor};
    }
    .mtx-source-grid {
      display: grid; grid-template-columns: repeat(auto-fill, minmax(90px, 1fr)); gap: 6px;
    }
    .mtx-source-btn {
      padding: 8px 10px; border-radius: 10px; border: 1px solid ${t.border};
      background: ${t.isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.02)'};
      color: ${t.textSec}; font-size: 11px; font-weight: 600;
      cursor: pointer; transition: all 0.2s ease;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    .mtx-source-btn:hover {
      background: ${t.isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)'}; color: ${t.text};
    }
    .mtx-source-btn.active {
      background: ${t.accentLight}; color: ${t.accent};
      border-color: ${t.isDark ? 'rgba(124,107,240,0.3)' : 'rgba(124,107,240,0.2)'};
    }
    .mtx-empty {
      display: flex; flex-direction: column; align-items: center;
      justify-content: center; padding: 30px 20px; gap: 8px; color: ${t.textSec};
    }
    .mtx-empty p { font-size: 14px; font-weight: 600; }
    .mtx-empty span { font-size: 12px; opacity: 0.6; text-align: center; }
  `;
}

function singleCardEditorStyles() {
  return `
    :host { display: block; }
    .editor { padding: 16px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    .field { margin-bottom: 12px; }
    label { display: block; font-size: 12px; font-weight: 600; margin-bottom: 4px; color: var(--primary-text-color, #333); }
    input, select { width: 100%; padding: 8px 12px; border: 1px solid var(--divider-color, #ddd); border-radius: 8px; font-size: 14px; background: var(--card-background-color, #fff); color: var(--primary-text-color, #333); }
    .hint { font-size: 11px; color: var(--secondary-text-color, #888); margin-top: 2px; }
  `;
}


class AudacMTXCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
    this._expanded = {};
    this._prevStates = {};
    this._rendered = false;
  }

  connectedCallback() {
    // Re-render if hass is already available (handles late connection)
    if (this._hass && !this._rendered) {
      this._render();
    }
  }

  static getConfigElement() {
    return document.createElement("audac-mtx-card-editor");
  }

  static getStubConfig() {
    return { title: "Audac MTX", zones: [], show_bass_treble: true, show_source: true, theme: "auto", accent_color: "" };
  }

  setConfig(config) {
    if (!config) throw new Error("Invalid configuration");
    this._config = { title: "Audac MTX", zones: [], show_bass_treble: true, show_source: true, theme: "auto", accent_color: "", ...config };
    this._rendered = false;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._rendered) {
      this._render();
      return;
    }
    const zones = this._getZones();
    const existingCards = this.shadowRoot?.querySelectorAll(".zone-card");
    // Full rebuild if zone count changed or cards are missing
    if (!existingCards || existingCards.length !== zones.length) {
      this._rendered = false;
      this._render();
      return;
    }
    try {
      this._updateExisting();
    } catch (e) {
      // Recover from any update error with a clean rebuild
      this._rendered = false;
      this._render();
    }
  }

  _getZones() {
    if (!this._hass) return [];
    const zones = this._config.zones || [];
    if (zones.length > 0) {
      return zones.map((z) => {
        const entityId = typeof z === "string" ? z : z.entity;
        const entity = this._hass.states[entityId];
        if (!entity) return null;
        // Respect zone_visible attribute
        if (entity.attributes?.zone_visible === false) return null;
        // Hide slave zones
        const linked = entity.attributes?.linked_to;
        if (Array.isArray(linked) && linked.length > 0) return null;
        if (typeof linked === 'number' && linked !== 0) return null;
        const rawName = (typeof z === "object" && z.name) || entity.attributes.friendly_name || entityId;
        return { entityId, entity, name: rawName, _shortName: mtxShortName(rawName, this._config.title) };
      }).filter(Boolean);
    }
    return mtxAutoDiscover(this._hass).map((entityId) => ({
      entityId, entity: this._hass.states[entityId],
      name: this._hass.states[entityId].attributes.friendly_name || entityId, _shortName: mtxShortName(this._hass.states[entityId].attributes.friendly_name || entityId, this._config.title),
    }));
  }

  _toggleExpand(entityId) {
    const wasExpanded = this._expanded[entityId];
    // Close all zones first (accordion behaviour)
    this._expanded = {};
    // Toggle the clicked zone
    if (!wasExpanded) this._expanded[entityId] = true;
    this._rendered = false;
    this._render();
    if (!wasExpanded && this._hass) {
      setTimeout(() => {
        this._hass.callService("homeassistant", "update_entity", { entity_id: entityId }).catch(() => {});
      }, 320);
    }
  }

  async _callService(domain, service, data) {
    if (this._hass) await this._hass.callService(domain, service, data);
  }

  _vol(z) { const v = z.entity.attributes.volume_level; return v == null ? 0 : Math.round(v * 100); }
  _muted(z) { return z.entity.attributes.is_volume_muted === true; }
  _src(z) { return z.entity.attributes.source || "---"; }
  _srcList(z) { return z.entity.attributes.source_list || []; }

  // Smart update: only patch changed values without rebuilding the DOM
  _updateExisting() {
    const r = this.shadowRoot;
    if (!r) return;
    const zones = this._getZones();
    const t = mtxThemeVars(mtxIsDark(this._config.theme), this._config.accent_color || "");

    // Update header badge (active count)
    const activeCount = zones.filter(z => !this._muted(z) && this._vol(z) > 0).length;
    const badge = r.querySelector(".mtx-header-badge");
    if (badge) badge.textContent = `${activeCount}/${zones.length}`;

    zones.forEach(z => {
      const prev = this._prevStates[z.entityId];
      const vol = this._vol(z);
      const muted = this._muted(z);
      const src = this._src(z);
      const isOff = z.entity.state === "off";
      const active = !isOff && !muted && vol > 0;
      const bass = z.entity.attributes.bass;
      const treble = z.entity.attributes.treble;
      const bassRaw = z.entity.attributes.bass_raw;
      const trebleRaw = z.entity.attributes.treble_raw;
      const volDb = z.entity.attributes.volume_db;

      const card = r.querySelector(`.zone-card[data-entity="${z.entityId}"]`);
      if (!card) return;

      // Volume background fill
      const volBg = card.querySelector(".zone-vol-bg");
      if (volBg) volBg.style.width = (muted ? 0 : vol) + "%";

      // Zone card classes
      card.classList.toggle("muted", muted);
      card.classList.toggle("off", isOff);

      // Zone icon active state
      const icon = card.querySelector(".zone-icon");
      if (icon) {
        icon.classList.toggle("active", active);
        icon.innerHTML = mtxSvg(muted ? "speakerMuted" : "speaker");
      }

      // Detail line (volume % · source)
      const detail = card.querySelector(".zone-detail");
      if (detail) detail.textContent = muted ? mtxT("muted") : (this._config.show_source && src !== "---" ? src : "");

      // Badge
      // Mute badge: add/remove dynamically
      let zoneBadge = card.querySelector(".zone-badge");
      if (muted && !zoneBadge) {
        zoneBadge = document.createElement("div");
        zoneBadge.className = "zone-badge muted";
        zoneBadge.textContent = "MUTE";
        card.querySelector(".zone-content")?.insertBefore(zoneBadge, card.querySelector(".zone-chevron"));
      } else if (!muted && zoneBadge) {
        zoneBadge.remove();
      }

      // Volume slider (only update if not currently being dragged)
      const slider = card.querySelector("[data-volume]");
      if (slider && document.activeElement !== slider) {
        slider.value = vol;
        const fill = slider.closest(".mtx-slider-wrap")?.querySelector(".mtx-slider-fill");
        if (fill) fill.style.width = vol + "%";
        const valSpan = slider.closest(".vol-row")?.querySelector(".mtx-val");
        if (valSpan) valSpan.innerHTML = `${vol}%${volDb != null ? "<br><small>" + volDb + " dB</small>" : ""}`;
      }

      // Mute button
      const muteBtn = card.querySelector("[data-mute]");
      if (muteBtn) {
        muteBtn.className = "mtx-btn" + (muted ? " active-mute" : "");
        muteBtn.dataset.muted = muted;
        muteBtn.innerHTML = mtxSvg(muted ? "speakerMuted" : "speaker", 18);
      }

      // Source buttons
      card.querySelectorAll("[data-source]").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.value === src);
      });

      // Bass slider (only if not being dragged)
      const bassSlider = card.querySelector("[data-bass]");
      if (bassSlider && document.activeElement !== bassSlider && bassRaw != null) {
        bassSlider.value = bassRaw;
        const fill = bassSlider.closest(".mtx-slider-wrap")?.querySelector(".mtx-slider-fill");
        if (fill) fill.style.width = (bassRaw / 14 * 100) + "%";
        const label = bassSlider.closest(".tone-ctrl")?.querySelector(".tone-val");
        if (label) label.textContent = (bass > 0 ? "+" : "") + bass + " dB";
      }

      // Treble slider (only if not being dragged)
      const trebleSlider = card.querySelector("[data-treble]");
      if (trebleSlider && document.activeElement !== trebleSlider && trebleRaw != null) {
        trebleSlider.value = trebleRaw;
        const fill = trebleSlider.closest(".mtx-slider-wrap")?.querySelector(".mtx-slider-fill");
        if (fill) fill.style.width = (trebleRaw / 14 * 100) + "%";
        const label = trebleSlider.closest(".tone-ctrl")?.querySelector(".tone-val");
        if (label) label.textContent = (treble > 0 ? "+" : "") + treble + " dB";
      }

      this._prevStates[z.entityId] = { vol, muted, src, bass, treble, bassRaw, trebleRaw };
    });
  }

  _render() {
    if (!this.shadowRoot) return;
    const zones = this._getZones();
    const t = mtxThemeVars(mtxIsDark(this._config.theme), this._config.accent_color || "");
    const activeCount = zones.filter(z => !this._muted(z) && this._vol(z) > 0).length;

    this.shadowRoot.innerHTML = `
      <style>
        ${mtxBaseStyles(t)}
        .zones-container { display: flex; flex-direction: column; gap: 8px; }
        .zone-card {
          background: ${t.isDark ? "rgba(255,255,255,0.04)" : "rgba(0,0,0,0.03)"}; border-radius: 25px; overflow: hidden;
          transition: all 0.3s cubic-bezier(0.25,0.1,0.25,1); border: 1px solid transparent;
        }
        .zone-card:hover { background: ${t.isDark ? "rgba(255,255,255,0.07)" : "rgba(0,0,0,0.05)"}; }
        .zone-card.expanded {
          border-color: ${t.isDark ? 'rgba(124,107,240,0.2)' : 'rgba(124,107,240,0.15)'};
          background: ${t.isDark ? 'rgba(45,48,58,0.9)' : 'rgba(240,242,248,0.95)'};
        }
        .zone-card.muted .zone-vol-bg { opacity: 0 !important; }
        .zone-card.off { opacity: 0.5; }
        .zone-main { position: relative; cursor: pointer; padding: 10px 12px; overflow: hidden; }
        .zone-vol-bg {
          position: absolute; top: 0; left: 0; height: 100%;
          background: linear-gradient(90deg,
            ${t.volBgStart} 0%,
            ${t.volBgMid} 70%,
            transparent 100%);
          transition: width 0.5s cubic-bezier(0.25,0.1,0.25,1); pointer-events: none;
        }
        .zone-content { position: relative; display: flex; align-items: center; gap: 12px; z-index: 1; }
        .zone-icon {
          width: 36px; height: 36px; border-radius: 50%;
          background: ${t.isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)'};
          display: flex; align-items: center; justify-content: center;
          color: ${t.textSec}; transition: all 0.3s ease; flex-shrink: 0;
        }
        .zone-icon.active { background: linear-gradient(135deg, ${t.accent}, ${t.accentSecond}); color: white; }
        .zone-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
        .zone-name { font-size: 13px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .zone-detail { font-size: 11px; color: ${t.textSec}; font-weight: 500; line-height: 1.2; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .zone-badge {
          font-size: 13px; font-weight: 700; color: ${t.accent};
          background: ${t.accentLight}; padding: 4px 10px; border-radius: 10px;
          white-space: nowrap; min-width: 48px; text-align: center; flex-shrink: 0;
        }
        .zone-badge.muted { color: ${t.mutedColor}; background: ${t.isDark ? 'rgba(239,83,80,0.15)' : 'rgba(239,83,80,0.1)'}; font-size: 11px; }
        .zone-chevron { color: ${t.textSec}; transition: transform 0.3s ease; flex-shrink: 0; }
        .zone-chevron.rotated { transform: rotate(180deg); }
        .zone-controls {
          padding: 4px 16px 16px; display: flex; flex-direction: column; gap: 14px;
          animation: slideDown 0.3s cubic-bezier(0.25,0.1,0.25,1);
        }
        @keyframes slideDown { from { opacity: 0; transform: translateY(-8px); } to { opacity: 1; transform: translateY(0); } }
        .ctrl-section { display: flex; flex-direction: column; gap: 8px; }
        .vol-row { display: flex; align-items: center; gap: 10px; }
        .tone-section { flex-direction: row; gap: 12px; }
        .tone-ctrl {
          flex: 1; display: flex; flex-direction: column; gap: 6px;
          background: ${t.isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.02)'};
          padding: 8px 12px; border-radius: 20px;
        }
        .tone-val { font-size: 16px; font-weight: 700; color: ${t.text}; }
      </style>
      <div class="mtx-card">
        <div class="mtx-header">
          <div class="mtx-header-icon">${mtxSvg('music', 24)}</div>
          <div class="mtx-header-content">
            <h2 class="mtx-header-title">${mtxEscape(this._config.title)}</h2>
            <span class="mtx-header-sub">${zones.length} ${mtxPlural(zones.length, mtxT('zone_1'), mtxT('zone_n'))}</span>
          </div>
          <div class="mtx-header-badge">${activeCount}/${zones.length}</div>
        </div>
        <div class="zones-container">
          ${zones.length > 0 ? zones.map(z => this._renderZone(z, t)).join("") : `<div class="mtx-empty">${mtxSvg('music', 48)}<p>${mtxT("no_zones")}</p><span>${mtxT("no_zones_hint")}</span></div>`}
        </div>
      </div>
    `;
    this._rendered = true;
    zones.forEach(z => {
      const vol = this._vol(z), muted = this._muted(z), src = this._src(z);
      this._prevStates[z.entityId] = {
        vol, muted, src,
        bass: z.entity.attributes.bass,
        treble: z.entity.attributes.treble,
        bassRaw: z.entity.attributes.bass_raw,
        trebleRaw: z.entity.attributes.treble_raw,
      };
    });
    this._attachEvents();
  }

  _renderZone(z, t) {
    const exp = this._expanded[z.entityId] || false;
    const vol = this._vol(z);
    const muted = this._muted(z);
    const src = this._src(z);
    const isOff = z.entity.state === "off";
    const active = !isOff && !muted && vol > 0;
    return `
      <div class="zone-card ${exp ? 'expanded' : ''} ${muted ? 'muted' : ''} ${isOff ? 'off' : ''}" data-entity="${z.entityId}">
        <div class="zone-main" data-toggle="${z.entityId}">
          <div class="zone-vol-bg" style="width: ${muted ? 0 : vol}%"></div>
          <div class="zone-content">
            <div class="zone-icon ${active ? 'active' : ''}">${mtxSvg(muted ? 'speakerMuted' : 'speaker')}</div>
            <div class="zone-info">
              <span class="zone-name">${mtxEscape(z._shortName || z.name)}${(z.entity.attributes.linked_zones || []).length > 0 ? ' <span style="font-size:10px;opacity:0.6;" title="${mtxT("linked_zones")}">🔗 <span style="font-size:9px;">' + mtxEscape(mtxLinkedNames(this._hass, z.entity.attributes.linked_zones)) + '</span></span>' : ''}</span>
              <span class="zone-detail">${muted ? mtxT('muted') : (this._config.show_source && src !== '---' ? mtxEscape(src) : '')}</span>
            </div>
            ${muted ? `<div class="zone-badge muted">MUTE</div>` : ''}
            <div class="zone-chevron ${exp ? 'rotated' : ''}">${mtxSvg('chevron', 20)}</div>
          </div>
        </div>
        ${exp ? this._renderControls(z, t) : ''}
      </div>
    `;
  }

  _renderControls(z, t) {
    const vol = this._vol(z);
    const muted = this._muted(z);
    const src = this._src(z);
    const srcList = this._srcList(z);
    const bass = z.entity.attributes.bass;
    const treble = z.entity.attributes.treble;
    const bassRaw = z.entity.attributes.bass_raw != null ? z.entity.attributes.bass_raw : 7;
    const trebleRaw = z.entity.attributes.treble_raw != null ? z.entity.attributes.treble_raw : 7;
    const volDb = z.entity.attributes.volume_db;
    return `
      <div class="zone-controls">
        <div class="ctrl-section">
          <div class="mtx-label">${mtxSvg("speakerSmall", 16)} ${mtxT("volume")}</div>
          <div class="vol-row">
            <button class="mtx-btn ${muted ? 'active-mute' : ''}" data-mute="${z.entityId}" data-muted="${muted}">
              ${mtxSvg(muted ? 'speakerMuted' : 'speaker', 18)}
            </button>
            <div class="mtx-slider-wrap">
              <input type="range" class="mtx-slider" min="0" max="100" step="1" value="${vol}" data-volume="${z.entityId}" />
              <div class="mtx-slider-fill" style="width: ${vol}%"></div>
            </div>
            <span class="mtx-val">${vol}%${volDb != null ? '<br><small>' + volDb + ' dB</small>' : ''}</span>
          </div>
        </div>
        ${this._config.show_source && srcList.length > 0 ? `
        <div class="ctrl-section">
          <div class="mtx-label">${mtxSvg("source", 16)} ${mtxT("source")}</div>
          <div class="mtx-source-grid">
            ${srcList.map(s => `<button class="mtx-source-btn ${s === src ? 'active' : ''}" data-source="${z.entityId}" data-value="${mtxEscape(s)}">${mtxEscape(s)}</button>`).join("")}
          </div>
        </div>` : ''}
        ${this._config.show_bass_treble ? `
        <div class="ctrl-section tone-section">
          ${bass != null ? `
          <div class="tone-ctrl">
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <div class="mtx-label">${mtxT("bass")}</div>
              <span class="tone-val">${bass > 0 ? '+' : ''}${bass} dB</span>
            </div>
            <div class="mtx-slider-wrap" style="height:28px;">
              <input type="range" class="mtx-slider" min="0" max="14" step="1" value="${bassRaw}" data-bass="${z.entityId}" />
              <div class="mtx-slider-fill" style="width:${(bassRaw / 14) * 100}%;"></div>
            </div>
          </div>` : ''}
          ${treble != null ? `
          <div class="tone-ctrl">
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <div class="mtx-label">${mtxT("treble")}</div>
              <span class="tone-val">${treble > 0 ? '+' : ''}${treble} dB</span>
            </div>
            <div class="mtx-slider-wrap" style="height:28px;">
              <input type="range" class="mtx-slider" min="0" max="14" step="1" value="${trebleRaw}" data-treble="${z.entityId}" />
              <div class="mtx-slider-fill" style="width:${(trebleRaw / 14) * 100}%;"></div>
            </div>
          </div>` : ''}
        </div>` : ''}
      </div>
    `;
  }

  _attachEvents() {
    const r = this.shadowRoot; if (!r) return;
    r.querySelectorAll("[data-toggle]").forEach(el => {
      el.addEventListener("click", e => {
        if (e.target.closest("[data-mute]") || e.target.closest("[data-volume]") || e.target.closest("[data-source]") || e.target.closest("[data-bass]") || e.target.closest("[data-treble]")) return;
        this._toggleExpand(el.dataset.toggle);
      });
    });
    r.querySelectorAll("[data-mute]").forEach(el => {
      el.addEventListener("click", e => { e.stopPropagation(); this._callService("media_player", "volume_mute", { entity_id: el.dataset.mute, is_volume_muted: el.dataset.muted !== "true" }); });
    });
    r.querySelectorAll("[data-volume]").forEach(el => {
      el.addEventListener("input", e => {
        const v = parseInt(e.target.value);
        const fill = e.target.closest(".mtx-slider-wrap").querySelector(".mtx-slider-fill");
        if (fill) fill.style.width = v + "%";
        const valSpan = e.target.closest(".vol-row").querySelector(".mtx-val");
        if (valSpan) valSpan.innerHTML = v + "%";
      });
      el._debouncedVolumeSet = el._debouncedVolumeSet || mtxDebounce((v) => {
        this._callService("media_player", "volume_set", { entity_id: el.dataset.volume, volume_level: v / 100 });
      }, 250);
      el.addEventListener("change", e => { el._debouncedVolumeSet(parseInt(e.target.value)); });
      el.addEventListener("click", e => e.stopPropagation());
    });
    r.querySelectorAll("[data-source]").forEach(el => {
      el.addEventListener("click", e => { e.stopPropagation(); this._callService("media_player", "select_source", { entity_id: el.dataset.source, source: el.dataset.value }); });
    });
    r.querySelectorAll("[data-bass]").forEach(el => {
      el.addEventListener("input", e => {
        const v = parseInt(e.target.value);
        const fill = e.target.closest(".mtx-slider-wrap")?.querySelector(".mtx-slider-fill");
        if (fill) fill.style.width = (v / 14 * 100) + "%";
        const label = e.target.closest(".tone-ctrl")?.querySelector(".tone-val");
        if (label) label.textContent = ((v - 7) * 2 > 0 ? "+" : "") + (v - 7) * 2 + " dB";
      });
      el._debouncedBassSet = el._debouncedBassSet || mtxDebounce((v) => {
        this._callService("media_player", "set_bass", { entity_id: el.dataset.bass, bass: v });
      }, 250);
      el.addEventListener("change", e => { el._debouncedBassSet(parseInt(e.target.value)); });
      el.addEventListener("click", e => e.stopPropagation());
    });
    r.querySelectorAll("[data-treble]").forEach(el => {
      el.addEventListener("input", e => {
        const v = parseInt(e.target.value);
        const fill = e.target.closest(".mtx-slider-wrap")?.querySelector(".mtx-slider-fill");
        if (fill) fill.style.width = (v / 14 * 100) + "%";
        const label = e.target.closest(".tone-ctrl")?.querySelector(".tone-val");
        if (label) label.textContent = ((v - 7) * 2 > 0 ? "+" : "") + (v - 7) * 2 + " dB";
      });
      el._debouncedTrebleSet = el._debouncedTrebleSet || mtxDebounce((v) => {
        this._callService("media_player", "set_treble", { entity_id: el.dataset.treble, treble: v });
      }, 250);
      el.addEventListener("change", e => { el._debouncedTrebleSet(parseInt(e.target.value)); });
      el.addEventListener("click", e => e.stopPropagation());
    });
  }

  getCardSize() { return 1 + this._getZones().length; }
}


class AudacMTXCardEditor extends HTMLElement {
  constructor() { super(); this.attachShadow({ mode: "open" }); this._config = {}; }
  setConfig(config) { this._config = { ...config }; this._render(); }
  _render() {
    this.shadowRoot.innerHTML = `
      <style>
        ${singleCardEditorStyles()}
        .checkbox-field { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
        .checkbox-field input { width: auto; }
        .section-title { font-size: 13px; font-weight: 700; margin: 16px 0 8px; padding-top: 12px; border-top: 1px solid var(--divider-color, #ddd); color: var(--primary-text-color, #333); }
        .zone-row { display: flex; gap: 8px; margin-bottom: 8px; align-items: center; }
        .zone-row input { flex: 1; }
        .btn-remove { border: none; background: none; cursor: pointer; color: #ef5350; font-size: 16px; padding: 2px 6px; flex-shrink: 0; }
        .btn-add { margin-top: 4px; padding: 8px 14px; border-radius: 8px; border: 1px dashed var(--divider-color, #ccc); background: transparent; color: var(--primary-text-color, #333); cursor: pointer; font-size: 13px; width: 100%; }
      </style>
      <div class="editor">
        <div class="field"><label>${mtxT("title")}</label><input type="text" id="title" value="${this._config.title || 'Audac MTX'}" /></div>
        <div class="field">
          <label>${mtxT("accent_color")}</label>
          <div style="display:flex;gap:8px;align-items:center;">
            <input type="color" id="accent_color" value="${this._config.accent_color || '#7c6bf0'}" style="width:48px;height:36px;padding:2px;border-radius:8px;border:1px solid var(--divider-color,#ddd);cursor:pointer;" />
            <input type="text" id="accent_color_hex" value="${this._config.accent_color || '#7c6bf0'}" placeholder="#7c6bf0" style="flex:1;" />
            <button id="accent_reset" style="padding:6px 10px;border-radius:8px;border:1px solid var(--divider-color,#ddd);background:transparent;cursor:pointer;font-size:12px;white-space:nowrap;">↺ ${mtxT("reset")}</button>
          </div>
          <div class="hint">${mtxT("accent_hint")}</div>
        </div>
        <div class="field"><label>${mtxT("design")}</label>
          <select id="theme">
            <option value="auto" ${this._config.theme === 'auto' ? 'selected' : ''}>${mtxT("auto")}</option>
            <option value="dark" ${this._config.theme === 'dark' ? 'selected' : ''}>${mtxT("dark")}</option>
            <option value="light" ${this._config.theme === 'light' ? 'selected' : ''}>${mtxT("light")}</option>
          </select>
        </div>
        <div class="checkbox-field"><input type="checkbox" id="show_source" ${this._config.show_source !== false ? 'checked' : ''} /><label for="show_source">${mtxT("show_source")}</label></div>
        <div class="checkbox-field"><input type="checkbox" id="show_bass_treble" ${this._config.show_bass_treble !== false ? 'checked' : ''} /><label for="show_bass_treble">${mtxT("show_bass_treble")}</label></div>
      </div>
    `;
    this.shadowRoot.getElementById("title").addEventListener("change", e => { this._config.title = e.target.value; this._fire(); });
    const colorPicker = this.shadowRoot.getElementById("accent_color");
    const colorHex = this.shadowRoot.getElementById("accent_color_hex");
    const colorReset = this.shadowRoot.getElementById("accent_reset");
    colorPicker.addEventListener("input", e => {
      colorHex.value = e.target.value;
      this._config.accent_color = e.target.value;
      this._fire();
    });
    colorHex.addEventListener("change", e => {
      const v = e.target.value.trim();
      if (/^#[0-9a-fA-F]{6}$/.test(v)) {
        colorPicker.value = v;
        this._config.accent_color = v;
        this._fire();
      }
    });
    colorReset.addEventListener("click", () => {
      const def = "#7c6bf0";
      colorPicker.value = def;
      colorHex.value = def;
      this._config.accent_color = "";
      this._fire();
    });
    this.shadowRoot.getElementById("theme").addEventListener("change", e => { this._config.theme = e.target.value; this._fire(); });
    this.shadowRoot.getElementById("show_source").addEventListener("change", e => { this._config.show_source = e.target.checked; this._fire(); });
    this.shadowRoot.getElementById("show_bass_treble").addEventListener("change", e => { this._config.show_bass_treble = e.target.checked; this._fire(); });
  }
  _fire() { this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._config }, bubbles: true, composed: true })); }
}


class AudacMTXVolumeCard extends HTMLElement {
  constructor() { super(); this.attachShadow({ mode: "open" }); this._config = {}; this._hass = null; }
  static getConfigElement() { return document.createElement("audac-mtx-volume-card-editor"); }
  static getStubConfig() { return { entity: "", title: "", theme: "auto" }; }
  setConfig(config) {
    if (!config) throw new Error("Invalid configuration");
    this._config = { entity: "", title: "", theme: "auto", ...config };
    this._render();
  }
  set hass(hass) { this._hass = hass; this._render(); }
  _render() {
    if (!this.shadowRoot) return;
    const entityId = this._config.entity;
    const entity = this._hass ? (entityId ? this._hass.states[entityId] : this._findEntity()) : null;
    const t = mtxThemeVars(mtxIsDark(this._config.theme));
    if (!entity) {
      const name = this._config.title || "Audac MTX";
      this.shadowRoot.innerHTML = `
        <style>${mtxBaseStyles(t)}
          .vol-row { display: flex; align-items: center; gap: 10px; margin-top: 8px; }
        </style>
        <div class="mtx-card">
          <div class="mtx-header">
            <div class="mtx-header-icon">${mtxSvg('speaker', 22)}</div>
            <div class="mtx-header-content">
              <div class="mtx-header-title">${mtxEscape(name)}</div>
              <div class="mtx-header-sub">${mtxT("volume")}</div>
            </div>
            <div class="mtx-header-badge">75%</div>
          </div>
          <div class="vol-row">
            <button class="mtx-btn">${mtxSvg('speaker', 18)}</button>
            <div class="mtx-slider-wrap">
              <input type="range" class="mtx-slider" min="0" max="100" step="1" value="75" disabled />
              <div class="mtx-slider-fill" style="width: 75%"></div>
            </div>
            <span class="mtx-val">75%<br><small>-18 dB</small></span>
          </div>
        </div>
      `;
      return;
    }
    const vol = Math.round((entity.attributes.volume_level || 0) * 100);
    const muted = entity.attributes.is_volume_muted === true;
    const volDb = entity.attributes.volume_db;
    const name = this._config.title || entity.attributes.friendly_name || entityId;
    const eid = entityId || this._findEntityId();
    this.shadowRoot.innerHTML = `
      <style>${mtxBaseStyles(t)}
        .vol-row { display: flex; align-items: center; gap: 10px; margin-top: 8px; }
      </style>
      <div class="mtx-card">
        <div class="mtx-header">
          <div class="mtx-header-icon">${mtxSvg('speaker', 22)}</div>
          <div class="mtx-header-content">
            <div class="mtx-header-title">${mtxEscape(name)}</div>
            <div class="mtx-header-sub">${mtxT("volume")}</div>
          </div>
          <div class="mtx-header-badge">${muted ? 'MUTE' : vol + '%'}</div>
        </div>
        <div class="vol-row">
          <button class="mtx-btn ${muted ? 'active-mute' : ''}" data-mute="${eid}" data-muted="${muted}">
            ${mtxSvg(muted ? 'speakerMuted' : 'speaker', 18)}
          </button>
          <div class="mtx-slider-wrap">
            <input type="range" class="mtx-slider" min="0" max="100" step="1" value="${vol}" data-volume="${eid}" />
            <div class="mtx-slider-fill" style="width: ${vol}%"></div>
          </div>
          <span class="mtx-val">${vol}%${volDb != null ? '<br><small>' + volDb + ' dB</small>' : ''}</span>
        </div>
      </div>
    `;
    this._attach(eid);
  }
  _findEntity() { const id = this._findEntityId(); return id ? this._hass.states[id] : null; }
  _findEntityId() { return this._config.entity || mtxAutoDiscover(this._hass)[0] || ""; }
  _attach(eid) {
    const r = this.shadowRoot;
    r.querySelectorAll("[data-mute]").forEach(el => {
      el.addEventListener("click", () => { this._hass.callService("media_player", "volume_mute", { entity_id: eid, is_volume_muted: el.dataset.muted !== "true" }); });
    });
    r.querySelectorAll("[data-volume]").forEach(el => {
      el.addEventListener("input", e => {
        const v = parseInt(e.target.value);
        const fill = r.querySelector('.mtx-slider-fill'); if (fill) fill.style.width = v + '%';
        const val = r.querySelector('.mtx-val'); if (val) val.innerHTML = v + '%';
      });
      el._debouncedVolumeSet = el._debouncedVolumeSet || mtxDebounce((v) => {
        this._hass.callService("media_player", "volume_set", { entity_id: eid, volume_level: v / 100 });
      }, 250);
      el.addEventListener("change", e => { el._debouncedVolumeSet(parseInt(e.target.value)); });
    });
  }
  getCardSize() { return 2; }
}


class AudacMTXSourceCard extends HTMLElement {
  constructor() { super(); this.attachShadow({ mode: "open" }); this._config = {}; this._hass = null; }
  static getConfigElement() { return document.createElement("audac-mtx-source-card-editor"); }
  static getStubConfig() { return { entity: "", title: "", theme: "auto" }; }
  setConfig(config) {
    if (!config) throw new Error("Invalid configuration");
    this._config = { entity: "", title: "", theme: "auto", ...config };
    this._render();
  }
  set hass(hass) { this._hass = hass; this._render(); }
  _render() {
    if (!this.shadowRoot) return;
    const entityId = this._config.entity;
    const entity = this._hass ? (entityId ? this._hass.states[entityId] : this._findEntity()) : null;
    const t = mtxThemeVars(mtxIsDark(this._config.theme));
    if (!entity) {
      const name = this._config.title || "Audac MTX";
      const demoSources = ["Mic 1", "Line 3", "Bluetooth"];
      this.shadowRoot.innerHTML = `
        <style>${mtxBaseStyles(t)}
          .src-wrap { margin-top: 8px; }
        </style>
        <div class="mtx-card">
          <div class="mtx-header">
            <div class="mtx-header-icon">${mtxSvg('source', 22)}</div>
            <div class="mtx-header-content">
              <div class="mtx-header-title">${mtxEscape(name)}</div>
              <div class="mtx-header-sub">${mtxT("source")}</div>
            </div>
            <div class="mtx-header-badge">Bluetooth</div>
          </div>
          <div class="src-wrap">
            <div class="mtx-source-grid">
              ${demoSources.map(s => `<button class="mtx-source-btn ${s === "Bluetooth" ? 'active' : ''}" disabled>${mtxEscape(s)}</button>`).join("")}
            </div>
          </div>
        </div>
      `;
      return;
    }
    const src = entity.attributes.source || "---";
    const srcList = entity.attributes.source_list || [];
    const name = this._config.title || entity.attributes.friendly_name || entityId;
    const eid = entityId || this._findEntityId();
    this.shadowRoot.innerHTML = `
      <style>${mtxBaseStyles(t)}
        .src-wrap { margin-top: 8px; }
      </style>
      <div class="mtx-card">
        <div class="mtx-header">
          <div class="mtx-header-icon">${mtxSvg('source', 22)}</div>
          <div class="mtx-header-content">
            <div class="mtx-header-title">${mtxEscape(name)}</div>
            <div class="mtx-header-sub">${mtxT("source")}</div>
          </div>
          <div class="mtx-header-badge">${mtxEscape(src)}</div>
        </div>
        <div class="src-wrap">
          <div class="mtx-source-grid">
            ${srcList.map(s => `<button class="mtx-source-btn ${s === src ? 'active' : ''}" data-source="${eid}" data-value="${mtxEscape(s)}">${mtxEscape(s)}</button>`).join("")}
          </div>
        </div>
      </div>
    `;
    this.shadowRoot.querySelectorAll("[data-source]").forEach(el => {
      el.addEventListener("click", () => { this._hass.callService("media_player", "select_source", { entity_id: eid, source: el.dataset.value }); });
    });
  }
  _findEntity() { const id = this._findEntityId(); return id ? this._hass.states[id] : null; }
  _findEntityId() { return this._config.entity || mtxAutoDiscover(this._hass)[0] || ""; }
  getCardSize() { return 2; }
}


class AudacMTXBassCard extends HTMLElement {
  constructor() { super(); this.attachShadow({ mode: "open" }); this._config = {}; this._hass = null; }
  static getConfigElement() { return document.createElement("audac-mtx-bass-card-editor"); }
  static getStubConfig() { return { entity: "", title: "", theme: "auto" }; }
  setConfig(config) {
    if (!config) throw new Error("Invalid configuration");
    this._config = { entity: "", title: "", theme: "auto", ...config };
    this._render();
  }
  set hass(hass) { this._hass = hass; this._render(); }
  _render() {
    if (!this.shadowRoot) return;
    const entityId = this._config.entity;
    const entity = this._hass ? (entityId ? this._hass.states[entityId] : this._findEntity()) : null;
    const t = mtxThemeVars(mtxIsDark(this._config.theme));
    if (!entity) {
      const name = this._config.title || "Audac MTX";
      this.shadowRoot.innerHTML = `
        <style>${mtxBaseStyles(t)}
          .bass-row { display: flex; align-items: center; gap: 10px; margin-top: 8px; }
        </style>
        <div class="mtx-card">
          <div class="mtx-header">
            <div class="mtx-header-icon">${mtxSvg('equalizer', 22)}</div>
            <div class="mtx-header-content">
              <div class="mtx-header-title">${mtxEscape(name)}</div>
              <div class="mtx-header-sub">${mtxT("bass")}</div>
            </div>
            <div class="mtx-header-badge">0 dB</div>
          </div>
          <div class="bass-row">
            <span class="mtx-val" style="min-width:36px;text-align:left;">-14</span>
            <div class="mtx-slider-wrap">
              <input type="range" class="mtx-slider" min="0" max="14" step="1" value="7" disabled />
              <div class="mtx-slider-fill" style="width: 50%"></div>
            </div>
            <span class="mtx-val">+14</span>
          </div>
        </div>
      `;
      return;
    }
    const bass = entity.attributes.bass;
    const bassRaw = entity.attributes.bass_raw;
    const name = this._config.title || entity.attributes.friendly_name || entityId;
    const eid = entityId || this._findEntityId();
    const sliderVal = bassRaw != null ? bassRaw : 7;
    this.shadowRoot.innerHTML = `
      <style>${mtxBaseStyles(t)}
        .bass-row { display: flex; align-items: center; gap: 10px; margin-top: 8px; }
      </style>
      <div class="mtx-card">
        <div class="mtx-header">
          <div class="mtx-header-icon">${mtxSvg('equalizer', 22)}</div>
          <div class="mtx-header-content">
            <div class="mtx-header-title">${mtxEscape(name)}</div>
            <div class="mtx-header-sub">${mtxT("bass")}</div>
          </div>
          <div class="mtx-header-badge">${bass != null ? (bass > 0 ? '+' : '') + bass + ' dB' : '---'}</div>
        </div>
        <div class="bass-row">
          <span class="mtx-val" style="min-width:36px;text-align:left;">-14</span>
          <div class="mtx-slider-wrap">
            <input type="range" class="mtx-slider" min="0" max="14" step="1" value="${sliderVal}" data-bass="${eid}" />
            <div class="mtx-slider-fill" style="width: ${(sliderVal / 14) * 100}%"></div>
          </div>
          <span class="mtx-val">+14</span>
        </div>
      </div>
    `;
    this.shadowRoot.querySelectorAll("[data-bass]").forEach(el => {
      el.addEventListener("input", e => {
        const fill = el.closest('.mtx-slider-wrap')?.querySelector('.mtx-slider-fill');
        if (fill) fill.style.width = (parseInt(e.target.value) / 14 * 100) + '%';
      });
      el.addEventListener("change", e => {
        this._hass.callService("media_player", "set_bass", { entity_id: eid, bass: parseInt(e.target.value) });
      });
    });
  }
  _findEntity() { const id = this._findEntityId(); return id ? this._hass.states[id] : null; }
  _findEntityId() { return this._config.entity || mtxAutoDiscover(this._hass)[0] || ""; }
  getCardSize() { return 2; }
}


class AudacMTXTrebleCard extends HTMLElement {
  constructor() { super(); this.attachShadow({ mode: "open" }); this._config = {}; this._hass = null; }
  static getConfigElement() { return document.createElement("audac-mtx-treble-card-editor"); }
  static getStubConfig() { return { entity: "", title: "", theme: "auto" }; }
  setConfig(config) {
    if (!config) throw new Error("Invalid configuration");
    this._config = { entity: "", title: "", theme: "auto", ...config };
    this._render();
  }
  set hass(hass) { this._hass = hass; this._render(); }
  _render() {
    if (!this.shadowRoot) return;
    const entityId = this._config.entity;
    const entity = this._hass ? (entityId ? this._hass.states[entityId] : this._findEntity()) : null;
    const t = mtxThemeVars(mtxIsDark(this._config.theme));
    if (!entity) {
      const name = this._config.title || "Audac MTX";
      this.shadowRoot.innerHTML = `
        <style>${mtxBaseStyles(t)}
          .treble-row { display: flex; align-items: center; gap: 10px; margin-top: 8px; }
        </style>
        <div class="mtx-card">
          <div class="mtx-header">
            <div class="mtx-header-icon">${mtxSvg('equalizer', 22)}</div>
            <div class="mtx-header-content">
              <div class="mtx-header-title">${mtxEscape(name)}</div>
              <div class="mtx-header-sub">${mtxT("treble")}</div>
            </div>
            <div class="mtx-header-badge">0 dB</div>
          </div>
          <div class="treble-row">
            <span class="mtx-val" style="min-width:36px;text-align:left;">-14</span>
            <div class="mtx-slider-wrap">
              <input type="range" class="mtx-slider" min="0" max="14" step="1" value="7" disabled />
              <div class="mtx-slider-fill" style="width: 50%"></div>
            </div>
            <span class="mtx-val">+14</span>
          </div>
        </div>
      `;
      return;
    }
    const treble = entity.attributes.treble;
    const trebleRaw = entity.attributes.treble_raw;
    const name = this._config.title || entity.attributes.friendly_name || entityId;
    const eid = entityId || this._findEntityId();
    const sliderVal = trebleRaw != null ? trebleRaw : 7;
    this.shadowRoot.innerHTML = `
      <style>${mtxBaseStyles(t)}
        .treble-row { display: flex; align-items: center; gap: 10px; margin-top: 8px; }
      </style>
      <div class="mtx-card">
        <div class="mtx-header">
          <div class="mtx-header-icon">${mtxSvg('equalizer', 22)}</div>
          <div class="mtx-header-content">
            <div class="mtx-header-title">${mtxEscape(name)}</div>
            <div class="mtx-header-sub">${mtxT("treble")}</div>
          </div>
          <div class="mtx-header-badge">${treble != null ? (treble > 0 ? '+' : '') + treble + ' dB' : '---'}</div>
        </div>
        <div class="treble-row">
          <span class="mtx-val" style="min-width:36px;text-align:left;">-14</span>
          <div class="mtx-slider-wrap">
            <input type="range" class="mtx-slider" min="0" max="14" step="1" value="${sliderVal}" data-treble="${eid}" />
            <div class="mtx-slider-fill" style="width: ${(sliderVal / 14) * 100}%"></div>
          </div>
          <span class="mtx-val">+14</span>
        </div>
      </div>
    `;
    this.shadowRoot.querySelectorAll("[data-treble]").forEach(el => {
      el.addEventListener("input", e => {
        const fill = el.closest('.mtx-slider-wrap')?.querySelector('.mtx-slider-fill');
        if (fill) fill.style.width = (parseInt(e.target.value) / 14 * 100) + '%';
      });
      el.addEventListener("change", e => {
        this._hass.callService("media_player", "set_treble", { entity_id: eid, treble: parseInt(e.target.value) });
      });
    });
  }
  _findEntity() { const id = this._findEntityId(); return id ? this._hass.states[id] : null; }
  _findEntityId() { return this._config.entity || mtxAutoDiscover(this._hass)[0] || ""; }
  getCardSize() { return 2; }
}


class AudacMTXSingleEditor extends HTMLElement {
  constructor() { super(); this.attachShadow({ mode: "open" }); this._config = {}; this._hass = null; }
  setConfig(config) { this._config = { ...config }; this._render(); }

  set hass(hass) { this._hass = hass; this._render(); }

  _getZoneOptions() {
    if (!this._hass) return [];
    return mtxAutoDiscover(this._hass).map(entityId => {
      const entity = this._hass.states[entityId];
      const fullName = entity?.attributes?.friendly_name || entityId;
      const short = mtxShortName(fullName, "Audac MTX");
      return { entityId, label: short };
    });
  }

  _render() {
    const zones = this._getZoneOptions();
    const current = this._config.entity || "";
    const zoneOptions = zones.map(z =>
      `<option value="${z.entityId}" ${current === z.entityId ? "selected" : ""}>${mtxEscape(z.label)}</option>`
    ).join("");

    this.shadowRoot.innerHTML = `
      <style>${singleCardEditorStyles()}</style>
      <div class="editor">
        <div class="field">
          <label>${mtxT("zone")}</label>
          <select id="entity">
            <option value="" ${!current ? "selected" : ""}>${mtxT("auto_first_zone")}</option>
            ${zoneOptions}
          </select>
        </div>
        <div class="field">
          <label>${mtxT("title_optional")}</label>
          <input type="text" id="title" value="${this._config.title || ''}" placeholder="${mtxT("auto_from_entity")}" />
        </div>
        <div class="field">
          <label>${mtxT("design")}</label>
          <select id="theme">
            <option value="auto" ${this._config.theme === 'auto' ? 'selected' : ''}>${mtxT("auto")}</option>
            <option value="dark" ${this._config.theme === 'dark' ? 'selected' : ''}>${mtxT("dark")}</option>
            <option value="light" ${this._config.theme === 'light' ? 'selected' : ''}>${mtxT("light")}</option>
          </select>
        </div>
      </div>
    `;
    this.shadowRoot.getElementById("entity").addEventListener("change", e => { this._config.entity = e.target.value; this._fire(); });
    this.shadowRoot.getElementById("title").addEventListener("change", e => { this._config.title = e.target.value.trim(); this._fire(); });
    this.shadowRoot.getElementById("theme").addEventListener("change", e => { this._config.theme = e.target.value; this._fire(); });
  }
  _fire() { this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._config }, bubbles: true, composed: true })); }
}


class AudacMTXMoreInfo extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._entityId = null;
    this._expanded = {};
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  set entityId(eid) {
    this._entityId = eid;
    this._render();
  }

  _getZones() {
    if (!this._hass) return [];
    return mtxAutoDiscover(this._hass).map((entityId) => ({
      entityId,
      entity: this._hass.states[entityId],
      name: this._hass.states[entityId].attributes.friendly_name || entityId, _shortName: mtxShortName(this._hass.states[entityId].attributes.friendly_name || entityId, undefined),
    }));
  }

  _toggleExpand(entityId) { this._expanded[entityId] = !this._expanded[entityId]; this._render(); }

  _vol(z) { const v = z.entity.attributes.volume_level; return v == null ? 0 : Math.round(v * 100); }
  _muted(z) { return z.entity.attributes.is_volume_muted === true; }
  _src(z) { return z.entity.attributes.source || "---"; }
  _srcList(z) { return z.entity.attributes.source_list || []; }

  _render() {
    if (!this.shadowRoot || !this._hass) return;
    const zones = this._getZones();
    const t = mtxThemeVars(mtxIsDark("auto"));
    const activeCount = zones.filter(z => !this._muted(z) && this._vol(z) > 0).length;

    this.shadowRoot.innerHTML = `
      <style>
        ${mtxBaseStyles(t)}
        :host { display: block; padding: 0; }
        .mtx-card { border: none; border-radius: 0; backdrop-filter: none; }
        .zones-container { display: flex; flex-direction: column; gap: 8px; }
        .zone-card {
          background: ${t.isDark ? "rgba(255,255,255,0.04)" : "rgba(0,0,0,0.03)"}; border-radius: 25px; overflow: hidden;
          transition: all 0.3s cubic-bezier(0.25,0.1,0.25,1); border: 1px solid transparent;
        }
        .zone-card:hover { background: ${t.isDark ? "rgba(255,255,255,0.07)" : "rgba(0,0,0,0.05)"}; }
        .zone-card.expanded {
          border-color: ${t.isDark ? 'rgba(124,107,240,0.2)' : 'rgba(124,107,240,0.15)'};
          background: ${t.isDark ? 'rgba(45,48,58,0.9)' : 'rgba(240,242,248,0.95)'};
        }
        .zone-card.muted .zone-vol-bg { opacity: 0 !important; }
        .zone-card.off { opacity: 0.5; }
        .zone-card.current { border-color: ${t.accent}; }
        .zone-main { position: relative; cursor: pointer; padding: 10px 12px; overflow: hidden; }
        .zone-vol-bg {
          position: absolute; top: 0; left: 0; height: 100%;
          background: linear-gradient(90deg,
            ${t.volBgStart} 0%,
            ${t.volBgMid} 70%,
            transparent 100%);
          transition: width 0.5s cubic-bezier(0.25,0.1,0.25,1); pointer-events: none;
        }
        .zone-content { position: relative; display: flex; align-items: center; gap: 12px; z-index: 1; }
        .zone-icon {
          width: 36px; height: 36px; border-radius: 50%;
          background: ${t.isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)'};
          display: flex; align-items: center; justify-content: center;
          color: ${t.textSec}; transition: all 0.3s ease; flex-shrink: 0;
        }
        .zone-icon.active { background: linear-gradient(135deg, ${t.accent}, ${t.accentSecond}); color: white; }
        .zone-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
        .zone-name { font-size: 13px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .zone-detail { font-size: 11px; color: ${t.textSec}; font-weight: 500; line-height: 1.2; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .zone-badge {
          font-size: 13px; font-weight: 700; color: ${t.accent};
          background: ${t.accentLight}; padding: 4px 10px; border-radius: 10px;
          white-space: nowrap; min-width: 48px; text-align: center; flex-shrink: 0;
        }
        .zone-badge.muted { color: ${t.mutedColor}; background: ${t.isDark ? 'rgba(239,83,80,0.15)' : 'rgba(239,83,80,0.1)'}; font-size: 11px; }
        .zone-chevron { color: ${t.textSec}; transition: transform 0.3s ease; flex-shrink: 0; }
        .zone-chevron.rotated { transform: rotate(180deg); }
        .zone-controls {
          padding: 4px 16px 16px; display: flex; flex-direction: column; gap: 14px;
          animation: slideDown 0.3s cubic-bezier(0.25,0.1,0.25,1);
        }
        @keyframes slideDown { from { opacity: 0; transform: translateY(-8px); } to { opacity: 1; transform: translateY(0); } }
        .ctrl-section { display: flex; flex-direction: column; gap: 8px; }
        .vol-row { display: flex; align-items: center; gap: 10px; }
        .tone-section { flex-direction: row; gap: 12px; }
        .tone-ctrl {
          flex: 1; display: flex; flex-direction: column; gap: 6px;
          background: ${t.isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.02)'};
          padding: 8px 12px; border-radius: 20px;
        }
        .tone-val { font-size: 18px; font-weight: 700; color: ${t.text}; }
      </style>
      <div class="mtx-card">
        <div class="mtx-header">
          <div class="mtx-header-icon">${mtxSvg('music', 24)}</div>
          <div class="mtx-header-content">
            <h2 class="mtx-header-title">Audac MTX</h2>
            <span class="mtx-header-sub">${zones.length} ${mtxPlural(zones.length, mtxT('zone_1'), mtxT('zone_n'))}</span>
          </div>
          <div class="mtx-header-badge">${activeCount}/${zones.length}</div>
        </div>
        <div class="zones-container">
          ${zones.length > 0 ? zones.map(z => this._renderZone(z, t)).join("") : `<div class="mtx-empty">${mtxSvg('music', 48)}<p>${mtxT("no_zones")}</p></div>`}
        </div>
      </div>
    `;
    this._attachEvents();

    if (this._entityId) {
      const currentCard = this.shadowRoot.querySelector(`.zone-card[data-entity="${this._entityId}"]`);
      if (currentCard && !this._expanded[this._entityId]) {
        this._expanded[this._entityId] = true;
        this._render();
      }
    }
  }

  _renderZone(z, t) {
    const exp = this._expanded[z.entityId] || false;
    const vol = this._vol(z);
    const muted = this._muted(z);
    const src = this._src(z);
    const isOff = z.entity.state === "off";
    const active = !isOff && !muted && vol > 0;
    const isCurrent = z.entityId === this._entityId;
    return `
      <div class="zone-card ${exp ? 'expanded' : ''} ${muted ? 'muted' : ''} ${isOff ? 'off' : ''} ${isCurrent ? 'current' : ''}" data-entity="${z.entityId}">
        <div class="zone-main" data-toggle="${z.entityId}">
          <div class="zone-vol-bg" style="width: ${muted ? 0 : vol}%"></div>
          <div class="zone-content">
            <div class="zone-icon ${active ? 'active' : ''}">${mtxSvg(muted ? 'speakerMuted' : 'speaker')}</div>
            <div class="zone-info">
              <span class="zone-name">${mtxEscape(z.name)}</span>
              <span class="zone-detail">${muted ? mtxT('muted') : vol + '%'}${src !== '---' ? ' \u00b7 ' + mtxEscape(src) : ''}</span>
            </div>
            ${muted ? `<div class="zone-badge muted">MUTE</div>` : ''}
            <div class="zone-chevron ${exp ? 'rotated' : ''}">${mtxSvg('chevron', 20)}</div>
          </div>
        </div>
        ${exp ? this._renderControls(z, t) : ''}
      </div>
    `;
  }

  _renderControls(z, t) {
    const vol = this._vol(z);
    const muted = this._muted(z);
    const src = this._src(z);
    const srcList = this._srcList(z);
    const bass = z.entity.attributes.bass;
    const treble = z.entity.attributes.treble;
    const volDb = z.entity.attributes.volume_db;
    return `
      <div class="zone-controls">
        <div class="ctrl-section">
          <div class="mtx-label">${mtxSvg("speakerSmall", 16)} ${mtxT("volume")}</div>
          <div class="vol-row">
            <button class="mtx-btn ${muted ? 'active-mute' : ''}" data-mute="${z.entityId}" data-muted="${muted}">
              ${mtxSvg(muted ? 'speakerMuted' : 'speaker', 18)}
            </button>
            <div class="mtx-slider-wrap">
              <input type="range" class="mtx-slider" min="0" max="100" step="1" value="${vol}" data-volume="${z.entityId}" />
              <div class="mtx-slider-fill" style="width: ${vol}%"></div>
            </div>
            <span class="mtx-val">${vol}%${volDb != null ? '<br><small>' + volDb + ' dB</small>' : ''}</span>
          </div>
        </div>
        ${srcList.length > 0 ? `
        <div class="ctrl-section">
          <div class="mtx-label">${mtxSvg("source", 16)} ${mtxT("source")}</div>
          <div class="mtx-source-grid">
            ${srcList.map(s => `<button class="mtx-source-btn ${s === src ? 'active' : ''}" data-source="${z.entityId}" data-value="${mtxEscape(s)}">${mtxEscape(s)}</button>`).join("")}
          </div>
        </div>` : ''}
        ${bass != null || treble != null ? `
        <div class="ctrl-section tone-section">
          ${bass != null ? `
          <div class="tone-ctrl">
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <div class="mtx-label">${mtxT("bass")}</div>
              <span class="tone-val">${bass > 0 ? '+' : ''}${bass} dB</span>
            </div>
            <div class="mtx-slider-wrap" style="height:28px;">
              <input type="range" class="mtx-slider" min="0" max="14" step="1" value="${z.entity.attributes.bass_raw != null ? z.entity.attributes.bass_raw : 7}" data-bass="${z.entityId}" />
              <div class="mtx-slider-fill" style="width:${((z.entity.attributes.bass_raw != null ? z.entity.attributes.bass_raw : 7) / 14) * 100}%;"></div>
            </div>
          </div>` : ''}
          ${treble != null ? `
          <div class="tone-ctrl">
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <div class="mtx-label">${mtxT("treble")}</div>
              <span class="tone-val">${treble > 0 ? '+' : ''}${treble} dB</span>
            </div>
            <div class="mtx-slider-wrap" style="height:28px;">
              <input type="range" class="mtx-slider" min="0" max="14" step="1" value="${z.entity.attributes.treble_raw != null ? z.entity.attributes.treble_raw : 7}" data-treble="${z.entityId}" />
              <div class="mtx-slider-fill" style="width:${((z.entity.attributes.treble_raw != null ? z.entity.attributes.treble_raw : 7) / 14) * 100}%;"></div>
            </div>
          </div>` : ''}
        </div>` : ''}
      </div>
    `;
  }

  _attachEvents() {
    const r = this.shadowRoot; if (!r) return;
    r.querySelectorAll("[data-toggle]").forEach(el => {
      el.addEventListener("click", e => {
        if (e.target.closest("[data-mute]") || e.target.closest("[data-volume]") || e.target.closest("[data-source]") || e.target.closest("[data-bass]") || e.target.closest("[data-treble]")) return;
        this._toggleExpand(el.dataset.toggle);
      });
    });
    r.querySelectorAll("[data-mute]").forEach(el => {
      el.addEventListener("click", e => { e.stopPropagation(); this._hass.callService("media_player", "volume_mute", { entity_id: el.dataset.mute, is_volume_muted: el.dataset.muted !== "true" }); });
    });
    r.querySelectorAll("[data-volume]").forEach(el => {
      el.addEventListener("input", e => {
        const v = parseInt(e.target.value);
        const fill = e.target.closest('.mtx-slider-wrap')?.querySelector('.mtx-slider-fill');
        if (fill) fill.style.width = v + '%';
        const valSpan = e.target.closest('.vol-row')?.querySelector('.mtx-val');
        if (valSpan) valSpan.innerHTML = v + '%';
      });
      el._debouncedVolumeSet = el._debouncedVolumeSet || mtxDebounce((v) => {
        this._hass.callService("media_player", "volume_set", { entity_id: el.dataset.volume, volume_level: v / 100 });
      }, 250);
      el.addEventListener("change", e => { el._debouncedVolumeSet(parseInt(e.target.value)); });
      el.addEventListener("click", e => e.stopPropagation());
    });
    r.querySelectorAll("[data-source]").forEach(el => {
      el.addEventListener("click", e => { e.stopPropagation(); this._hass.callService("media_player", "select_source", { entity_id: el.dataset.source, source: el.dataset.value }); });
    });
    r.querySelectorAll("[data-bass]").forEach(el => {
      el.addEventListener("input", e => {
        const v = parseInt(e.target.value);
        const fill = e.target.closest(".mtx-slider-wrap")?.querySelector(".mtx-slider-fill");
        if (fill) fill.style.width = (v / 14 * 100) + "%";
        const label = e.target.closest(".tone-ctrl")?.querySelector(".tone-val");
        const db = (v - 7) * 2;
        if (label) label.textContent = (db > 0 ? "+" : "") + db + " dB";
      });
      el._debouncedBassSet = el._debouncedBassSet || mtxDebounce((v) => {
        this._hass.callService("media_player", "set_bass", { entity_id: el.dataset.bass, bass: v });
      }, 250);
      el.addEventListener("change", e => { el._debouncedBassSet(parseInt(e.target.value)); });
      el.addEventListener("click", e => e.stopPropagation());
    });
    r.querySelectorAll("[data-treble]").forEach(el => {
      el.addEventListener("input", e => {
        const v = parseInt(e.target.value);
        const fill = e.target.closest(".mtx-slider-wrap")?.querySelector(".mtx-slider-fill");
        if (fill) fill.style.width = (v / 14 * 100) + "%";
        const label = e.target.closest(".tone-ctrl")?.querySelector(".tone-val");
        const db = (v - 7) * 2;
        if (label) label.textContent = (db > 0 ? "+" : "") + db + " dB";
      });
      el._debouncedTrebleSet = el._debouncedTrebleSet || mtxDebounce((v) => {
        this._hass.callService("media_player", "set_treble", { entity_id: el.dataset.treble, treble: v });
      }, 250);
      el.addEventListener("change", e => { el._debouncedTrebleSet(parseInt(e.target.value)); });
      el.addEventListener("click", e => e.stopPropagation());
    });
  }
}


const _define = (name, cls) => { if (!customElements.get(name)) customElements.define(name, cls); };

_define("audac-mtx-card", AudacMTXCard);
_define("audac-mtx-card-editor", AudacMTXCardEditor);
_define("audac-mtx-volume-card", AudacMTXVolumeCard);
_define("audac-mtx-source-card", AudacMTXSourceCard);
_define("audac-mtx-bass-card", AudacMTXBassCard);
_define("audac-mtx-treble-card", AudacMTXTrebleCard);
_define("audac-mtx-more-info", AudacMTXMoreInfo);

_define("audac-mtx-volume-card-editor", class extends AudacMTXSingleEditor {});
_define("audac-mtx-source-card-editor", class extends AudacMTXSingleEditor {});
_define("audac-mtx-bass-card-editor", class extends AudacMTXSingleEditor {});
_define("audac-mtx-treble-card-editor", class extends AudacMTXSingleEditor {});

// Tell Lovelace to re-render all cards now that our elements are defined.
// This is the standard pattern used by popular HACS cards (bubble-card, mushroom, etc.)
// to fix "Custom element doesn't exist" on first load.
Promise.all([
  customElements.whenDefined("audac-mtx-card"),
  customElements.whenDefined("audac-mtx-more-info"),
]).then(() => {
  window.dispatchEvent(new Event("ll-rebuild"));
});

(function() {
  const patchMoreInfo = () => {
    const moreInfoEl = document.querySelector("home-assistant")
      ?.shadowRoot?.querySelector("ha-more-info-dialog");
    if (!moreInfoEl) return;

    const origUpdate = moreInfoEl.updated || moreInfoEl.requestUpdate;
    if (moreInfoEl._audacPatched) return;
    moreInfoEl._audacPatched = true;

    const observer = new MutationObserver(() => {
      const entityId = moreInfoEl.entityId || moreInfoEl._entityId;
      if (!entityId || !entityId.includes("audac_mtx")) return;

      const content = moreInfoEl.shadowRoot?.querySelector(".content") ||
                      moreInfoEl.shadowRoot?.querySelector("ha-more-info-info") ||
                      moreInfoEl.shadowRoot?.querySelector("[slot='content']");
      if (!content) return;

      let mtxInfo = content.querySelector("audac-mtx-more-info");
      if (mtxInfo) {
        mtxInfo.hass = moreInfoEl.hass;
        mtxInfo.entityId = entityId;
        return;
      }

      mtxInfo = document.createElement("audac-mtx-more-info");
      mtxInfo.hass = moreInfoEl.hass;
      mtxInfo.entityId = entityId;
      content.innerHTML = "";
      content.appendChild(mtxInfo);
    });

    observer.observe(moreInfoEl.shadowRoot || moreInfoEl, { childList: true, subtree: true });
  };

  if (document.readyState === "complete") {
    setTimeout(patchMoreInfo, 2000);
  } else {
    window.addEventListener("load", () => setTimeout(patchMoreInfo, 2000));
  }
})();

console.info(
  `%c AUDAC-MTX-CARD %c v${CARD_VERSION} `,
  "color: white; background: #7c6bf0; font-weight: 700; padding: 2px 6px; border-radius: 4px 0 0 4px;",
  "color: #7c6bf0; background: #e8e5fc; font-weight: 700; padding: 2px 6px; border-radius: 0 4px 4px 0;"
);
