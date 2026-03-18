const XMP44_CARD_VERSION = "3.15.2";

// ─── i18n ───────────────────────────────────────────────────────────
const _xmpLang = () => {
  try { return document.querySelector('home-assistant')?.hass?.language || 'en'; } catch(e) { return 'en'; }
};
const _xmpI18n = {
  de: {
    slots: 'Slots', slot: 'Slot', no_slots: 'Keine Module gefunden',
    no_slots_hint: 'Audac XMP44 Integration einrichten und Module konfigurieren',
    playing: 'Wiedergabe', paused: 'Pausiert', stopped: 'Gestoppt', idle: 'Bereit',
    station: 'Sender', frequency: 'Frequenz', signal: 'Signal',
    title_default: 'Audac XMP44', design: 'Design',
    auto: 'Automatisch', dark: 'Dunkel', light: 'Hell',
    title: 'Titel', accent_color: 'Akzentfarbe', reset: 'Standard',
    accent_hint: 'Standard: #7c6bf0 (Violett)',
    stereo: 'Stereo', mono: 'Mono', band: 'Band',
    connected: 'Verbunden', not_connected: 'Nicht verbunden',
    pairing: 'Pairing', recorder: 'Aufnahme',
    desc_main: 'XMP44 Module mit Status und Steuerung',
    name_main: 'Audac XMP44',
    entity_not_found: 'Entity nicht gefunden',
    desc_slot: 'Einzelnes XMP44 Modul mit Steuerung',
    name_slot: 'Audac XMP44 Modul',
    select_entity: 'Entity auswählen',
    auto_first: '-- Automatisch (erstes Modul) --',
  },
  en: {
    slots: 'Slots', slot: 'Slot', no_slots: 'No modules found',
    no_slots_hint: 'Set up Audac XMP44 integration and configure modules',
    playing: 'Playing', paused: 'Paused', stopped: 'Stopped', idle: 'Idle',
    station: 'Station', frequency: 'Frequency', signal: 'Signal',
    title_default: 'Audac XMP44', design: 'Design',
    auto: 'Automatic', dark: 'Dark', light: 'Light',
    title: 'Title', accent_color: 'Accent color', reset: 'Default',
    accent_hint: 'Default: #7c6bf0 (Violet)',
    stereo: 'Stereo', mono: 'Mono', band: 'Band',
    connected: 'Connected', not_connected: 'Not connected',
    pairing: 'Pairing', recorder: 'Recording',
    desc_main: 'XMP44 modules with status and controls',
    name_main: 'Audac XMP44',
    entity_not_found: 'Entity not found',
    desc_slot: 'Single XMP44 module with controls',
    name_slot: 'Audac XMP44 Module',
    select_entity: 'Select entity',
    auto_first: '-- Automatic (first module) --',
  },
};
function xmpT(key) { const l = _xmpLang(); return (_xmpI18n[l] || _xmpI18n['en'])[key] || _xmpI18n['en'][key] || key; }

// ─── Registration ──────────────────────────────────────────────────
window.customCards = window.customCards || [];
if (!window.customCards.find(c => c.type === "audac-xmp44-card")) {
  window.customCards.push({
    type: "audac-xmp44-card", name: "Audac XMP44",
    description: "Audac XMP44 modular audio system card", preview: true,
  });
}
if (!window.customCards.find(c => c.type === "audac-xmp44-slot-card")) {
  window.customCards.push({
    type: "audac-xmp44-slot-card", name: xmpT("name_slot"),
    description: xmpT("desc_slot"), preview: true,
  });
}

// ─── Helpers ───────────────────────────────────────────────────────
function xmpEscape(str) {
  return String(str).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}
function xmpHexToRgb(hex) {
  const c = hex.replace("#","");
  return `${parseInt(c.substring(0,2),16)}, ${parseInt(c.substring(2,4),16)}, ${parseInt(c.substring(4,6),16)}`;
}
function xmpTheme(isDark, accentHex) {
  const accent = accentHex || "#7c6bf0";
  const rgb = xmpHexToRgb(accent);
  return {
    
    
    
    text: isDark ? "#e4e6eb" : "#1a1c20",
    textSec: isDark ? "rgba(228,230,235,0.6)" : "rgba(26,28,32,0.5)",
    accent, accentLight: isDark ? `rgba(${rgb},0.15)` : `rgba(${rgb},0.1)`,
    accentMid: isDark ? `rgba(${rgb},0.25)` : `rgba(${rgb},0.18)`,
    accentShadow: `rgba(${rgb},0.4)`, border: isDark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)",
    isDark,
  };
}
function xmpIsDark(theme) {
  return theme === "dark" || (theme === "auto" && window.matchMedia("(prefers-color-scheme: dark)").matches);
}

const XMP_ICONS = {
  bluetooth: '<path d="M17.71 7.71L12 2h-1v7.59L6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 11 14.41V22h1l5.71-5.71-4.3-4.29 4.3-4.29zM13 5.83l1.88 1.88L13 9.59V5.83zm1.88 10.46L13 18.17v-3.76l1.88 1.88z"/>',
  radio: '<path d="M20 6H8.3l8.26-3.918L15.54 0 3.27 5.818C2.52 6.136 2 6.835 2 7.667V18c0 1.105.895 2 2 2h16c1.105 0 2-.895 2-2V8c0-1.105-.895-2-2-2zm-8 11c-1.657 0-3-1.343-3-3s1.343-3 3-3 3 1.343 3 3-1.343 3-3 3z"/>',
  music: '<path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/>',
  microphone: '<path d="M12 14c1.66 0 2.99-1.34 2.99-3L15 5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.3-3c0 3-2.54 5.1-5.3 5.1S6.7 14 6.7 11H5c0 3.41 2.72 6.23 6 6.72V21h2v-3.28c3.28-.48 6-3.3 6-6.72h-1.7z"/>',
  speaker: '<path d="M17 2H7c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h10c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-5 2c1.1 0 2 .9 2 2s-.9 2-2 2-2-.9-2-2 .9-2 2-2zm0 16c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/>',
  voicefile: '<path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm-1 7V3.5L18.5 9H13zm-3 4c1.1 0 2 .9 2 2s-.9 2-2 2-2-.9-2-2 .9-2 2-2zm3.5 6h-7v-.7c0-1.1 1.3-2.1 3.5-2.1s3.5 1 3.5 2.1V19z"/>',
  internet: '<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>',
  play: '<path d="M8 5v14l11-7z"/>',
  pause: '<path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>',
  stop: '<path d="M6 6h12v12H6z"/>',
  next: '<path d="M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z"/>',
  prev: '<path d="M6 6h2v12H6zm3.5 6l8.5 6V6z"/>',
  chevron: '<path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z"/>',
};
function xmpSvg(icon, size = 22) {
  return `<svg viewBox="0 0 24 24" width="${size}" height="${size}" fill="currentColor">${XMP_ICONS[icon] || ''}</svg>`;
}

const MODULE_ICON_MAP = {
  DMP40: 'radio', TMP40: 'radio', MMP40: 'music', IMP40: 'internet',
  FMP40: 'voicefile', BMP40: 'bluetooth', NMP40: 'speaker',
};

function xmpAutoDiscover(hass) {
  if (!hass) return [];
  return Object.keys(hass.states)
    .filter(id => id.startsWith("media_player.") && hass.states[id]?.attributes?.slot_number != null)
    .sort();
}

/** Find all entities (buttons, switches, sensors) belonging to a given slot. */
function xmpSlotEntities(hass, slotNumber) {
  if (!hass || slotNumber == null) return { buttons: [], switches: [], sensors: [] };
  const result = { buttons: [], switches: [], sensors: [] };
  for (const [id, state] of Object.entries(hass.states)) {
    if (state?.attributes?.slot_number !== slotNumber) continue;
    if (id.startsWith('button.')) result.buttons.push({ id, state });
    else if (id.startsWith('switch.')) result.switches.push({ id, state });
    else if (id.startsWith('sensor.')) result.sensors.push({ id, state });
  }
  return result;
}

// ─── Main Card ─────────────────────────────────────────────────────
class AudacXMP44Card extends HTMLElement {
  constructor() { super(); this.attachShadow({mode:'open'}); this._config = {}; this._hass = null; this._expanded = {}; this._prevSnapshot = ''; this._rendered = false; }

  static getConfigElement() { return document.createElement("audac-xmp44-card-editor"); }
  static getStubConfig() { return { title: "", theme: "auto", accent_color: "" }; }

  setConfig(config) { this._config = config; this._rendered = false; if (this._hass) this._render(); }
  set hass(h) {
    this._hass = h;
    if (!this._rendered) { this._render(); return; }
    // Only re-render if relevant state changed
    const snapshot = this._stateSnapshot();
    if (snapshot === this._prevSnapshot) return;
    this._prevSnapshot = snapshot;
    this._render();
  }

  _stateSnapshot() {
    const hass = this._hass;
    if (!hass) return '';
    let entities = this._config.entities;
    if (!entities || entities.length === 0) entities = xmpAutoDiscover(hass);
    const parts = [];
    for (const id of entities) {
      const e = hass.states[id];
      if (!e) continue;
      const a = e.attributes;
      parts.push(`${id}:${e.state}:${a.media_title||''}:${a.media_artist||''}:${a.source||''}:${a.station_name||''}:${a.program_name||''}:${a.frequency||''}:${a.signal_strength||''}:${a.output_gain||''}:${a.connected_device||''}`);
    }
    // Also include related switch/sensor states for expanded slots
    for (const id of Object.keys(this._expanded)) {
      if (!this._expanded[id]) continue;
      const e = hass.states[id];
      const slotNum = e?.attributes?.slot_number;
      if (slotNum == null) continue;
      for (const [sid, s] of Object.entries(hass.states)) {
        if (s.attributes?.slot_number === slotNum && (sid.startsWith('switch.') || sid.startsWith('sensor.'))) {
          parts.push(`${sid}:${s.state}`);
        }
      }
    }
    return parts.join('|');
  }

  _render() {
    const hass = this._hass;
    if (!hass) return;
    const t = xmpTheme(xmpIsDark(this._config.theme || "auto"), this._config.accent_color);

    let entities = this._config.entities;
    if (!entities || entities.length === 0) {
      entities = xmpAutoDiscover(hass);
    }
    const slots = entities.map(id => {
      const entity = hass.states[id];
      if (!entity) return null;
      const slotNum = entity.attributes?.slot_number;
      const related = xmpSlotEntities(hass, slotNum);
      return { entityId: id, entity, related };
    }).filter(Boolean);

    const title = this._config.title || xmpT('title_default');
    const activeCount = slots.filter(s => ['playing','paused'].includes(s.entity.state)).length;

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; --accent: ${t.accent}; }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        .xmp-card {
          background: var(--ha-card-background, var(--card-background-color, ${t.isDark ? "rgba(30,33,40,0.95)" : "rgba(255,255,255,0.95)"}));
          border-radius: var(--ha-card-border-radius, 25px); padding: 16px;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
          color: ${t.text}; border: 1px solid var(--ha-card-border-color, ${t.border});
          box-shadow: var(--ha-card-box-shadow, none);
        }
        .xmp-header { display: flex; align-items: center; gap: 14px; margin-bottom: 16px; padding: 0 4px; }
        .xmp-header-icon {
          width: 38px; height: 38px; border-radius: 50%;
          background: linear-gradient(135deg, ${t.accent}, #a78bfa);
          display: flex; align-items: center; justify-content: center; color: white; flex-shrink: 0;
        }
        .xmp-header-content { flex: 1; min-width: 0; }
        .xmp-header-title { font-size: 14px; font-weight: 700; letter-spacing: -0.3px; line-height: 1.3; }
        .xmp-header-sub { font-size: 11px; color: ${t.textSec}; font-weight: 500; }
        .xmp-header-badge {
          background: ${t.accentLight}; color: ${t.accent};
          font-size: 12px; font-weight: 700; padding: 4px 10px; border-radius: 12px; white-space: nowrap;
        }
        .slots-container { display: flex; flex-direction: column; gap: 6px; }
        .slot-card {
          background: ${t.isDark ? "rgba(255,255,255,0.04)" : "rgba(0,0,0,0.03)"}; border-radius: 25px; overflow: hidden;
          transition: all 0.3s cubic-bezier(0.25,0.1,0.25,1); border: 1px solid transparent;
        }
        .slot-card:hover { background: ${t.isDark ? "rgba(255,255,255,0.07)" : "rgba(0,0,0,0.05)"}; }
        .slot-card.expanded {
          border-color: ${t.isDark ? 'rgba(124,107,240,0.2)' : 'rgba(124,107,240,0.15)'};
          background: ${t.isDark ? 'rgba(45,48,58,0.9)' : 'rgba(240,242,248,0.95)'};
        }
        .slot-main { position: relative; cursor: pointer; padding: 8px 12px; overflow: hidden; }
        .slot-content { position: relative; display: flex; align-items: center; gap: 10px; z-index: 1; }
        .slot-icon {
          width: 36px; height: 36px; border-radius: 50%;
          background: ${t.isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)'};
          display: flex; align-items: center; justify-content: center;
          color: ${t.textSec}; transition: all 0.3s ease; flex-shrink: 0;
        }
        .slot-icon.active { background: linear-gradient(135deg, ${t.accent}, #a78bfa); color: white; }
        .slot-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
        .slot-name { font-size: 13px; font-weight: 600; line-height: 1.3; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .slot-detail { font-size: 11px; color: ${t.textSec}; font-weight: 500; line-height: 1.2; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .slot-badge {
          font-size: 11px; font-weight: 600; color: ${t.accent};
          background: ${t.accentLight}; padding: 4px 10px; border-radius: 10px;
          white-space: nowrap; flex-shrink: 0;
        }
        .slot-badge.playing { color: #4caf50; background: ${t.isDark ? 'rgba(76,175,80,0.15)' : 'rgba(76,175,80,0.1)'}; }
        .slot-chevron { color: ${t.textSec}; transition: transform 0.3s ease; flex-shrink: 0; }
        .slot-chevron.rotated { transform: rotate(180deg); }
        .slot-controls {
          padding: 4px 12px 12px; display: flex; flex-direction: column; gap: 12px;
          animation: xmpSlideDown 0.3s cubic-bezier(0.25,0.1,0.25,1);
        }
        @keyframes xmpSlideDown { from { opacity: 0; transform: translateY(-8px); } to { opacity: 1; transform: translateY(0); } }
        .xmp-playback { display: flex; align-items: center; justify-content: center; gap: 8px; }
        .xmp-play-btn {
          width: 36px; height: 36px; border-radius: 50%; border: none;
          background: ${t.isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)'};
          color: ${t.textSec}; cursor: pointer; display: flex; align-items: center; justify-content: center;
          transition: all 0.2s ease; flex-shrink: 0;
        }
        .xmp-play-btn:hover { background: ${t.isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)'}; color: ${t.text}; }
        .xmp-play-btn.primary {
          width: 44px; height: 44px; border-radius: 50%;
          background: linear-gradient(135deg, ${t.accent}, #a78bfa); color: white;
        }
        .xmp-play-btn.primary:hover { opacity: 0.9; }
        .xmp-song-info {
          text-align: center; padding: 4px 0 8px;
        }
        .xmp-song-title { font-size: 13px; font-weight: 600; line-height: 1.3; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .xmp-song-artist { font-size: 11px; color: ${t.textSec}; font-weight: 500; line-height: 1.2; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .xmp-info-row {
          display: flex; align-items: center; justify-content: space-between;
          font-size: 12px; color: ${t.textSec}; padding: 4px 0;
        }
        .xmp-info-label { font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; font-size: 10px; }
        .xmp-info-value { font-weight: 600; color: ${t.text}; }
        .xmp-source-grid {
          display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 6px;
        }
        .xmp-source-btn {
          padding: 7px 10px; border-radius: 20px; border: 1px solid ${t.border};
          background: ${t.isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.02)'};
          color: ${t.textSec}; font-size: 11px; font-weight: 600;
          cursor: pointer; transition: all 0.2s ease;
          white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }
        .xmp-source-btn:hover { background: ${t.isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)'}; color: ${t.text}; }
        .xmp-source-btn.active {
          background: ${t.accentLight}; color: ${t.accent};
          border-color: ${t.isDark ? 'rgba(124,107,240,0.3)' : 'rgba(124,107,240,0.2)'};
        }
        .xmp-empty {
          display: flex; flex-direction: column; align-items: center;
          justify-content: center; padding: 30px 20px; gap: 8px; color: ${t.textSec};
        }
        .xmp-empty p { font-size: 14px; font-weight: 600; }
        .xmp-empty span { font-size: 12px; opacity: 0.6; text-align: center; }
        .xmp-trigger-grid {
          display: flex; flex-direction: column; gap: 6px;
        }
        .xmp-trigger-row {
          display: grid; grid-template-columns: 1fr 1fr; gap: 6px;
        }
        .xmp-trigger-btn {
          padding: 8px 12px; border-radius: 20px; border: 1px solid ${t.border};
          background: ${t.isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.02)'};
          color: ${t.text}; font-size: 12px; font-weight: 600;
          cursor: pointer; transition: all 0.2s ease; display: flex; align-items: center; gap: 8px;
        }
        .xmp-trigger-btn:hover { background: ${t.isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)'}; }
        .xmp-trigger-btn:active { transform: scale(0.97); }
        .xmp-trigger-icon { color: ${t.accent}; flex-shrink: 0; }
        .xmp-bt-row {
          display: flex; align-items: center; justify-content: space-between;
          padding: 8px 12px; border-radius: 12px;
          background: ${t.isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.02)'};
        }
        .xmp-bt-label { font-size: 12px; font-weight: 600; }
        .xmp-bt-value { font-size: 12px; color: ${t.accent}; font-weight: 600; }
        .xmp-bt-btn {
          padding: 6px 14px; border-radius: 8px; border: none; font-size: 11px; font-weight: 600;
          cursor: pointer; transition: all 0.2s ease;
        }
        .xmp-bt-btn.on { background: ${t.accentLight}; color: ${t.accent}; }
        .xmp-bt-btn.off { background: ${t.isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)'}; color: ${t.textSec}; }
        .xmp-bt-btn.danger { background: ${t.isDark ? 'rgba(239,83,80,0.15)' : 'rgba(239,83,80,0.1)'}; color: #ef5350; }
        .xmp-bt-btn:hover { opacity: 0.85; }
      </style>
      <div class="xmp-card">
        <div class="xmp-header">
          <div class="xmp-header-icon">${xmpSvg('speaker', 24)}</div>
          <div class="xmp-header-content">
            <h2 class="xmp-header-title">${xmpEscape(title)}</h2>
            <span class="xmp-header-sub">${slots.length} ${xmpT('slots')}</span>
          </div>
          ${activeCount > 0 ? `<div class="xmp-header-badge">${activeCount} ${xmpT('playing')}</div>` : ''}
        </div>
        <div class="slots-container">
          ${slots.length > 0 ? slots.map(s => this._renderSlot(s, t)).join("") :
            `<div class="xmp-empty">${xmpSvg('speaker',48)}<p>${xmpT("no_slots")}</p><span>${xmpT("no_slots_hint")}</span></div>`}
        </div>
      </div>
    `;
    this._attachEvents();
    this._rendered = true;
    this._prevSnapshot = this._stateSnapshot();
  }

  _renderSlot(s, t) {
    const a = s.entity.attributes;
    const moduleName = a.module_name || 'Unknown';
    const moduleIcon = MODULE_ICON_MAP[moduleName] || 'music';
    const friendlyName = a.friendly_name || moduleName;
    const state = s.entity.state;
    const isActive = ['playing','paused'].includes(state);
    const exp = this._expanded[s.entityId] || false;

    // Detail line
    let detail = '';
    if (a.station_name) detail = a.station_name;
    else if (a.program_name) detail = a.program_name;
    else if (a.media_title) detail = a.media_title;
    else if (a.connected_device && a.connected_device !== 'Nicht verbunden') detail = `🔗 ${a.connected_device}`;
    else if (a.module_description) detail = a.module_description;

    // Badge
    let badge = '';
    if (state === 'playing') badge = `<span class="slot-badge playing">${xmpT('playing')}</span>`;
    else if (state === 'paused') badge = `<span class="slot-badge">${xmpT('paused')}</span>`;
    else if (a.frequency) badge = `<span class="slot-badge">${(a.frequency / 100).toFixed(1)} MHz</span>`;
    else badge = `<span class="slot-badge">${moduleName}</span>`;

    return `
      <div class="slot-card ${exp ? 'expanded' : ''}" data-entity="${s.entityId}">
        <div class="slot-main" data-toggle="${s.entityId}">
          <div class="slot-content">
            <div class="slot-icon ${isActive ? 'active' : ''}">${xmpSvg(moduleIcon, 22)}</div>
            <div class="slot-info">
              <div class="slot-name">${xmpEscape(friendlyName)}</div>
              ${detail ? `<div class="slot-detail">${xmpEscape(detail)}</div>` : ''}
            </div>
            ${badge}
            <div class="slot-chevron ${exp ? 'rotated' : ''}">${xmpSvg('chevron', 20)}</div>
          </div>
        </div>
        ${exp ? this._renderControls(s, t) : ''}
      </div>
    `;
  }

  _renderControls(s, t) {
    const a = s.entity.attributes;
    const moduleName = a.module_name || '';
    const state = s.entity.state;
    const rel = s.related || { buttons: [], switches: [], sensors: [] };
    let html = '<div class="slot-controls">';

    // ── BMP40: Connected device + Pairing + Disconnect ──
    if (moduleName === 'BMP40') {
      // Connected device sensor
      const connSensor = rel.sensors.find(e => e.id.includes('connected_device'));
      if (connSensor) {
        const connName = connSensor.state.state || 'Nicht verbunden';
        html += `<div class="xmp-bt-row"><span class="xmp-bt-label">🔗 ${xmpEscape(connName)}</span></div>`;
      }
      // Pairing switch
      const pairingSwitch = rel.switches.find(e => e.id.includes('pairing'));
      if (pairingSwitch) {
        const isOn = pairingSwitch.state.state === 'on';
        html += `<div class="xmp-bt-row">
          <span class="xmp-bt-label">${xmpT('pairing')}</span>
          <button class="xmp-bt-btn ${isOn ? 'on' : 'off'}" data-toggle-switch="${pairingSwitch.id}">
            ${isOn ? 'ON' : 'OFF'}
          </button>
        </div>`;
      }
      // Disconnect button
      const discBtn = rel.buttons.find(e => e.id.includes('disconnect'));
      if (discBtn) {
        html += `<div class="xmp-bt-row">
          <span class="xmp-bt-label">Bluetooth</span>
          <button class="xmp-bt-btn danger" data-press-button="${discBtn.id}">Disconnect</button>
        </div>`;
      }
    }

    // Song info (BMP40, MMP40, NMP40, IMP40)
    const title = a.media_title;
    const artist = a.media_artist;
    if (title) {
      html += `<div class="xmp-song-info">
        <div class="xmp-song-title">${xmpEscape(title)}</div>
        ${artist ? `<div class="xmp-song-artist">${xmpEscape(artist)}</div>` : ''}
      </div>`;
    }

    // Playback controls (BMP40, MMP40, NMP40)
    const features = a.supported_features || 0;
    const hasPlay = features & 4;
    if (hasPlay) {
      const isPlaying = state === 'playing';
      html += `<div class="xmp-playback">
        <button class="xmp-play-btn" data-action="prev" data-entity="${s.entityId}">${xmpSvg('prev', 20)}</button>
        <button class="xmp-play-btn primary" data-action="${isPlaying ? 'pause' : 'play'}" data-entity="${s.entityId}">
          ${xmpSvg(isPlaying ? 'pause' : 'play', 24)}
        </button>
        <button class="xmp-play-btn" data-action="next" data-entity="${s.entityId}">${xmpSvg('next', 20)}</button>
      </div>`;
    }

    // Source selection (IMP40)
    const sources = a.source_list;
    const currentSource = a.source;
    if (sources && sources.length > 0) {
      html += `<div class="xmp-source-grid">
        ${sources.map(src =>
          `<button class="xmp-source-btn ${src === currentSource ? 'active' : ''}"
                  data-source="${xmpEscape(src)}" data-entity="${s.entityId}">${xmpEscape(src)}</button>`
        ).join('')}
      </div>`;
    }

    // ── FMP40: Trigger buttons ──
    if (moduleName === 'FMP40') {
      const devicePrefix = a.friendly_name || '';
      const triggerBtns = rel.buttons.filter(e => !e.state.attributes?.friendly_name?.toLowerCase().endsWith(' stop'));
      const stopBtns = rel.buttons.filter(e => e.state.attributes?.friendly_name?.toLowerCase().endsWith(' stop'));
      if (triggerBtns.length > 0) {
        html += '<div class="xmp-trigger-grid">';
        for (const btn of triggerBtns) {
          let name = btn.state.attributes?.friendly_name || 'Trigger';
          if (devicePrefix && name.startsWith(devicePrefix + ' ')) name = name.slice(devicePrefix.length + 1);
          const trigNum = btn.state.attributes?.trigger_number;
          const stopBtn = stopBtns.find(s => s.state.attributes?.trigger_number === trigNum);
          html += '<div class="xmp-trigger-row">';
          html += `<button class="xmp-trigger-btn" data-press-button="${btn.id}">
            <span class="xmp-trigger-icon">${xmpSvg('play', 16)}</span>
            ${xmpEscape(name)}
          </button>`;
          if (stopBtn) {
            html += `<button class="xmp-trigger-btn" data-press-button="${stopBtn.id}">
              <span class="xmp-trigger-icon">${xmpSvg('stop', 16)}</span>
              Stop
            </button>`;
          }
          html += '</div>';
        }
        html += '</div>';
      }
    }

    // ── MMP40: Transport + Recording + Repeat/Random ──
    if (moduleName === 'MMP40') {
      const devicePrefix = a.friendly_name || '';
      const findBtn = (substr) => rel.buttons.find(e => e.id.includes(substr));
      // Transport row
      const goStart = findBtn('go_to_start');
      const ffw = findBtn('fast_forward');
      const frw = findBtn('fast_rewind');
      if (goStart || ffw || frw) {
        html += '<div class="xmp-playback">';
        if (frw) html += `<button class="xmp-play-btn" data-press-button="${frw.id}">${xmpSvg('prev', 18)}</button>`;
        if (goStart) html += `<button class="xmp-play-btn" data-press-button="${goStart.id}">${xmpSvg('stop', 18)}</button>`;
        if (ffw) html += `<button class="xmp-play-btn" data-press-button="${ffw.id}">${xmpSvg('next', 18)}</button>`;
        html += '</div>';
      }
      // Repeat + Random
      const repeatBtns = rel.buttons.filter(e => e.id.includes('repeat_'));
      const randomBtns = rel.buttons.filter(e => e.id.includes('random_'));
      if (repeatBtns.length > 0 || randomBtns.length > 0) {
        html += '<div class="xmp-source-grid">';
        for (const btn of [...repeatBtns, ...randomBtns]) {
          let name = btn.state.attributes?.friendly_name || '';
          if (devicePrefix && name.startsWith(devicePrefix + ' ')) name = name.slice(devicePrefix.length + 1);
          html += `<button class="xmp-source-btn" data-press-button="${btn.id}">${xmpEscape(name)}</button>`;
        }
        html += '</div>';
      }
      // Recording
      const recBtns = rel.buttons.filter(e => e.id.includes('rec_'));
      if (recBtns.length > 0) {
        html += '<div class="xmp-source-grid">';
        for (const btn of recBtns) {
          let name = btn.state.attributes?.friendly_name || '';
          if (devicePrefix && name.startsWith(devicePrefix + ' ')) name = name.slice(devicePrefix.length + 1);
          html += `<button class="xmp-source-btn" data-press-button="${btn.id}">${xmpEscape(name)}</button>`;
        }
        html += '</div>';
      }
      // Recorder mode switch
      const recSwitch = rel.switches.find(e => e.id.includes('recorder'));
      if (recSwitch) {
        const isRec = recSwitch.state.state === 'on';
        html += `<div class="xmp-bt-row">
          <span class="xmp-bt-label">${xmpT('recorder')}</span>
          <button class="xmp-bt-btn ${isRec ? 'on' : 'off'}" data-toggle-switch="${recSwitch.id}">${isRec ? 'ON' : 'OFF'}</button>
        </div>`;
      }
    }

    // ── DMP40/TMP40: Presets, Search, Stereo, Band ──
    if (moduleName === 'DMP40' || moduleName === 'TMP40') {
      const devicePrefix = a.friendly_name || '';
      // Search buttons
      const searchUp = rel.buttons.find(e => e.id.includes('search_up'));
      const searchDown = rel.buttons.find(e => e.id.includes('search_down'));
      if (searchUp || searchDown) {
        html += '<div class="xmp-playback">';
        if (searchDown) html += `<button class="xmp-play-btn" data-press-button="${searchDown.id}">${xmpSvg('prev', 18)}</button>`;
        if (searchUp) html += `<button class="xmp-play-btn" data-press-button="${searchUp.id}">${xmpSvg('next', 18)}</button>`;
        html += '</div>';
      }
      // Preset grid
      const presetBtns = rel.buttons.filter(e => e.id.includes('preset_'));
      if (presetBtns.length > 0) {
        html += '<div class="xmp-source-grid">';
        for (const btn of presetBtns) {
          let name = btn.state.attributes?.friendly_name || '';
          if (devicePrefix && name.startsWith(devicePrefix + ' ')) name = name.slice(devicePrefix.length + 1);
          html += `<button class="xmp-source-btn" data-press-button="${btn.id}">${xmpEscape(name)}</button>`;
        }
        html += '</div>';
      }
      // Band switch (DMP40 only)
      const bandBtn = rel.buttons.find(e => e.id.includes('band_switch'));
      if (bandBtn) {
        html += `<div class="xmp-bt-row">
          <span class="xmp-bt-label">${xmpT('band')}</span>
          <button class="xmp-bt-btn on" data-press-button="${bandBtn.id}">DAB/FM</button>
        </div>`;
      }
      // Stereo switch
      const stereoSwitch = rel.switches.find(e => e.id.includes('stereo'));
      if (stereoSwitch) {
        const isStereo = stereoSwitch.state.state === 'on';
        html += `<div class="xmp-bt-row">
          <span class="xmp-bt-label">${xmpT('stereo')}</span>
          <button class="xmp-bt-btn ${isStereo ? 'on' : 'off'}" data-toggle-switch="${stereoSwitch.id}">${isStereo ? 'Stereo' : 'Mono'}</button>
        </div>`;
      }
    }

    // Tuner info (DMP40, TMP40)
    if (a.frequency) {
      html += `<div class="xmp-info-row"><span class="xmp-info-label">${xmpT('frequency')}</span><span class="xmp-info-value">${(a.frequency / 100).toFixed(1)} MHz</span></div>`;
    }
    if (a.program_name && !title) {
      html += `<div class="xmp-info-row"><span class="xmp-info-label">${xmpT('station')}</span><span class="xmp-info-value">${xmpEscape(a.program_name)}</span></div>`;
    }
    if (a.signal_strength != null) {
      html += `<div class="xmp-info-row"><span class="xmp-info-label">${xmpT('signal')}</span><span class="xmp-info-value">${a.signal_strength}%</span></div>`;
    }
    if (a.band) {
      html += `<div class="xmp-info-row"><span class="xmp-info-label">${xmpT('band')}</span><span class="xmp-info-value">${a.band}</span></div>`;
    }

    // Output gain (all modules)
    if (a.output_gain != null) {
      html += `<div class="xmp-info-row"><span class="xmp-info-label">Output Gain</span><span class="xmp-info-value">${a.output_gain} dB</span></div>`;
    }

    html += '</div>';
    return html;
  }

  _attachEvents() {
    // Toggle expand
    this.shadowRoot.querySelectorAll('[data-toggle]').forEach(el => {
      el.addEventListener('click', () => {
        const id = el.dataset.toggle;
        const wasExpanded = this._expanded[id];
        this._expanded = {};
        if (!wasExpanded) this._expanded[id] = true;
        this._rendered = false;
        this._render();
      });
    });
    // Playback buttons
    this.shadowRoot.querySelectorAll('[data-action]').forEach(el => {
      el.addEventListener('click', (e) => {
        e.stopPropagation();
        const action = el.dataset.action;
        const entityId = el.dataset.entity;
        const serviceMap = { play: 'media_play', pause: 'media_pause', stop: 'media_stop', next: 'media_next_track', prev: 'media_previous_track' };
        if (serviceMap[action]) {
          this._hass.callService('media_player', serviceMap[action], { entity_id: entityId });
        }
      });
    });
    // Source buttons
    this.shadowRoot.querySelectorAll('[data-source]').forEach(el => {
      el.addEventListener('click', (e) => {
        e.stopPropagation();
        this._hass.callService('media_player', 'select_source', {
          entity_id: el.dataset.entity, source: el.dataset.source,
        });
      });
    });
    // Generic button press (triggers, disconnect, station buttons)
    this.shadowRoot.querySelectorAll('[data-press-button]').forEach(el => {
      el.addEventListener('click', (e) => {
        e.stopPropagation();
        this._hass.callService('button', 'press', { entity_id: el.dataset.pressButton });
      });
    });
    // Switch toggle (pairing, stereo, recorder)
    this.shadowRoot.querySelectorAll('[data-toggle-switch]').forEach(el => {
      el.addEventListener('click', (e) => {
        e.stopPropagation();
        const entityId = el.dataset.toggleSwitch;
        const current = this._hass.states[entityId]?.state;
        this._hass.callService('switch', current === 'on' ? 'turn_off' : 'turn_on', { entity_id: entityId });
      });
    });
  }

  getCardSize() { return 3; }
}

// ─── Editor ────────────────────────────────────────────────────────
class AudacXMP44CardEditor extends HTMLElement {
  constructor() { super(); this.attachShadow({mode:'open'}); this._config = {}; this._rendered = false; }
  setConfig(config) { this._config = {...config}; if (!this._rendered) this._render(); this._rendered = true; }
  set hass(h) { this._hass = h; }

  _render() {
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        .editor { padding: 16px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        .field { margin-bottom: 12px; }
        label { display: block; font-size: 12px; font-weight: 600; margin-bottom: 4px; color: var(--primary-text-color, #333); }
        input, select { width: 100%; padding: 8px 12px; border: 1px solid var(--divider-color, #ddd); border-radius: 8px; font-size: 14px; background: var(--card-background-color, #fff); color: var(--primary-text-color, #333); }
        .hint { font-size: 11px; color: var(--secondary-text-color, #888); margin-top: 2px; }
        .row { display: flex; gap: 12px; }
        .row .field { flex: 1; }
      </style>
      <div class="editor">
        <div class="field">
          <label>${xmpT('title')}</label>
          <input type="text" id="title" value="${xmpEscape(this._config.title || '')}" placeholder="${xmpT('title_default')}">
        </div>
        <div class="row">
          <div class="field">
            <label>${xmpT('design')}</label>
            <select id="theme">
              <option value="auto" ${(this._config.theme||'auto')==='auto'?'selected':''}>${xmpT('auto')}</option>
              <option value="dark" ${this._config.theme==='dark'?'selected':''}>${xmpT('dark')}</option>
              <option value="light" ${this._config.theme==='light'?'selected':''}>${xmpT('light')}</option>
            </select>
          </div>
          <div class="field">
            <label>${xmpT('accent_color')}</label>
            <input type="text" id="accent_color" value="${this._config.accent_color || ''}" placeholder="#7c6bf0">
            <div class="hint">${xmpT('accent_hint')}</div>
          </div>
        </div>
      </div>
    `;
    ['title','theme','accent_color'].forEach(field => {
      const el = this.shadowRoot.getElementById(field);
      if (el) el.addEventListener('change', () => {
        this._config[field] = el.value;
        this.dispatchEvent(new CustomEvent('config-changed', { detail: { config: this._config } }));
      });
    });
  }
}

// ─── Register ──────────────────────────────────────────────────────
const _xmpDefine = (name, cls) => { if (!customElements.get(name)) customElements.define(name, cls); };
_xmpDefine("audac-xmp44-card", AudacXMP44Card);
_xmpDefine("audac-xmp44-card-editor", AudacXMP44CardEditor);

// ─── Slot Card (single module) ──────────────────────────────────────
class AudacXMP44SlotCard extends HTMLElement {
  constructor() { super(); this.attachShadow({mode:'open'}); this._config = {}; this._hass = null; this._prevSnapshot = ''; this._prevConfigSnap = ''; }

  static getConfigElement() { return document.createElement("audac-xmp44-slot-card-editor"); }
  static getStubConfig() { return { entity: "", title: "", theme: "auto", accent_color: "" }; }

  setConfig(config) {
    if (!config) throw new Error("Invalid configuration");
    this._config = { entity: "", title: "", theme: "auto", accent_color: "", ...config };
    const configSnap = JSON.stringify(this._config);
    if (configSnap !== this._prevConfigSnap) {
      this._prevConfigSnap = configSnap;
      this._prevSnapshot = '';  // force state re-check
      this._render();
    }
  }
  set hass(h) {
    this._hass = h;
    const snap = this._stateSnapshot();
    if (snap === this._prevSnapshot) return;
    this._prevSnapshot = snap;
    this._render();
  }

  _findEntityId() { return this._config.entity || xmpAutoDiscover(this._hass)[0] || ""; }

  _stateSnapshot() {
    if (!this._hass) return '';
    const entityId = this._findEntityId();
    const e = this._hass.states[entityId];
    if (!e) return entityId;
    const a = e.attributes;
    const parts = [`${entityId}:${e.state}:${a.media_title||''}:${a.media_artist||''}:${a.source||''}:${a.station_name||''}:${a.program_name||''}:${a.frequency||''}:${a.signal_strength||''}:${a.output_gain||''}:${a.connected_device||''}`];
    const slotNum = a.slot_number;
    if (slotNum != null) {
      for (const [sid, s] of Object.entries(this._hass.states)) {
        if (s.attributes?.slot_number === slotNum && (sid.startsWith('switch.') || sid.startsWith('sensor.') || sid.startsWith('button.'))) {
          parts.push(`${sid}:${s.state}`);
        }
      }
    }
    return parts.join('|');
  }

  _render() {
    if (!this.shadowRoot) return;
    const hass = this._hass;
    const t = xmpTheme(xmpIsDark(this._config.theme || "auto"), this._config.accent_color);
    const entityId = hass ? this._findEntityId() : "";
    const entity = hass ? hass.states[entityId] : null;

    // Static preview when no entity/hass
    if (!entity) {
      const name = this._config.title || xmpT("name_slot");
      this.shadowRoot.innerHTML = `
        <style>${this._styles(t)}</style>
        <div class="xmp-card">
          <div class="xmp-header">
            <div class="xmp-header-icon">${xmpSvg('music', 24)}</div>
            <div class="xmp-header-content">
              <h2 class="xmp-header-title">${xmpEscape(name)}</h2>
              <span class="xmp-header-sub">${xmpT('slot')}</span>
            </div>
            <div class="xmp-header-badge">BMP40</div>
          </div>
          <div class="slot-controls">
            <div class="xmp-bt-row">
              <span class="xmp-bt-label">🔗 Kygo - Firestone</span>
            </div>
            <div class="xmp-playback">
              <button class="xmp-play-btn" disabled>${xmpSvg('prev', 20)}</button>
              <button class="xmp-play-btn primary" disabled>${xmpSvg('play', 24)}</button>
              <button class="xmp-play-btn" disabled>${xmpSvg('next', 20)}</button>
            </div>
          </div>
        </div>`;
      return;
    }

    const a = entity.attributes;
    const moduleName = a.module_name || 'Unknown';
    const moduleIcon = MODULE_ICON_MAP[moduleName] || 'music';
    const friendlyName = this._config.title || a.friendly_name || moduleName;
    const state = entity.state;
    const isActive = ['playing','paused'].includes(state);
    const slotNum = a.slot_number;
    const related = xmpSlotEntities(hass, slotNum);

    // Detail line
    let detail = '';
    if (a.station_name) detail = a.station_name;
    else if (a.program_name) detail = a.program_name;
    else if (a.media_title) detail = a.media_title;
    else if (a.connected_device && a.connected_device !== 'Nicht verbunden') detail = `🔗 ${a.connected_device}`;
    else if (a.module_description) detail = a.module_description;

    // Badge
    let badge = '';
    if (state === 'playing') badge = `<div class="xmp-header-badge playing">${xmpT('playing')}</div>`;
    else if (state === 'paused') badge = `<div class="xmp-header-badge">${xmpT('paused')}</div>`;
    else if (a.frequency) badge = `<div class="xmp-header-badge">${(a.frequency / 100).toFixed(1)} MHz</div>`;
    else badge = `<div class="xmp-header-badge">${moduleName}</div>`;

    // Reuse the main card's _renderControls via a temporary instance
    const tmpCard = new AudacXMP44Card();
    tmpCard._hass = hass;
    const s = { entityId, entity, related };
    const controlsHtml = tmpCard._renderControls(s, t);

    this.shadowRoot.innerHTML = `
      <style>${this._styles(t)}</style>
      <div class="xmp-card">
        <div class="xmp-header">
          <div class="xmp-header-icon ${isActive ? 'active' : ''}">${xmpSvg(moduleIcon, 24)}</div>
          <div class="xmp-header-content">
            <h2 class="xmp-header-title">${xmpEscape(friendlyName)}</h2>
            <span class="xmp-header-sub">${detail ? xmpEscape(detail) : moduleName}</span>
          </div>
          ${badge}
        </div>
        ${controlsHtml}
      </div>
    `;
    this._attachEvents();
  }

  _styles(t) {
    return `
      :host { display: block; --accent: ${t.accent}; }
      * { box-sizing: border-box; margin: 0; padding: 0; }
      .xmp-card {
        background: var(--ha-card-background, var(--card-background-color, ${t.isDark ? "rgba(30,33,40,0.95)" : "rgba(255,255,255,0.95)"}));
        border-radius: var(--ha-card-border-radius, 25px); padding: 16px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        color: ${t.text}; border: 1px solid var(--ha-card-border-color, ${t.border});
        box-shadow: var(--ha-card-box-shadow, none);
      }
      .xmp-header { display: flex; align-items: center; gap: 14px; margin-bottom: 12px; padding: 0 4px; }
      .xmp-header-icon {
        width: 38px; height: 38px; border-radius: 50%;
        background: ${t.isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)'};
        display: flex; align-items: center; justify-content: center;
        color: ${t.textSec}; flex-shrink: 0; transition: all 0.3s ease;
      }
      .xmp-header-icon.active { background: linear-gradient(135deg, ${t.accent}, #a78bfa); color: white; }
      .xmp-header-content { flex: 1; min-width: 0; }
      .xmp-header-title { font-size: 14px; font-weight: 700; letter-spacing: -0.3px; line-height: 1.3; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      .xmp-header-sub { font-size: 11px; color: ${t.textSec}; font-weight: 500; }
      .xmp-header-badge {
        background: ${t.accentLight}; color: ${t.accent};
        font-size: 12px; font-weight: 700; padding: 4px 10px; border-radius: 12px; white-space: nowrap;
      }
      .xmp-header-badge.playing { color: #4caf50; background: ${t.isDark ? 'rgba(76,175,80,0.15)' : 'rgba(76,175,80,0.1)'}; }
      .slot-controls {
        display: flex; flex-direction: column; gap: 12px;
      }
      .xmp-playback { display: flex; align-items: center; justify-content: center; gap: 8px; }
      .xmp-play-btn {
        width: 36px; height: 36px; border-radius: 50%; border: none;
        background: ${t.isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)'};
        color: ${t.textSec}; cursor: pointer; display: flex; align-items: center; justify-content: center;
        transition: all 0.2s ease; flex-shrink: 0;
      }
      .xmp-play-btn:hover { background: ${t.isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)'}; color: ${t.text}; }
      .xmp-play-btn.primary {
        width: 44px; height: 44px; border-radius: 50%;
        background: linear-gradient(135deg, ${t.accent}, #a78bfa); color: white;
      }
      .xmp-play-btn.primary:hover { opacity: 0.9; }
      .xmp-song-info { text-align: center; padding: 4px 0 8px; }
      .xmp-song-title { font-size: 13px; font-weight: 600; line-height: 1.3; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      .xmp-song-artist { font-size: 11px; color: ${t.textSec}; font-weight: 500; }
      .xmp-info-row {
        display: flex; align-items: center; justify-content: space-between;
        font-size: 12px; color: ${t.textSec}; padding: 4px 0;
      }
      .xmp-info-label { font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; font-size: 10px; }
      .xmp-info-value { font-weight: 600; color: ${t.text}; }
      .xmp-source-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 6px; }
      .xmp-source-btn {
        padding: 7px 10px; border-radius: 20px; border: 1px solid ${t.border};
        background: ${t.isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.02)'};
        color: ${t.textSec}; font-size: 11px; font-weight: 600;
        cursor: pointer; transition: all 0.2s ease;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
      }
      .xmp-source-btn:hover { background: ${t.isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)'}; color: ${t.text}; }
      .xmp-source-btn.active {
        background: ${t.accentLight}; color: ${t.accent};
        border-color: ${t.isDark ? 'rgba(124,107,240,0.3)' : 'rgba(124,107,240,0.2)'};
      }
      .xmp-trigger-grid { display: flex; flex-direction: column; gap: 6px; }
      .xmp-trigger-row { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
      .xmp-trigger-btn {
        padding: 8px 12px; border-radius: 20px; border: 1px solid ${t.border};
        background: ${t.isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.02)'};
        color: ${t.text}; font-size: 12px; font-weight: 600;
        cursor: pointer; transition: all 0.2s ease; display: flex; align-items: center; gap: 8px;
      }
      .xmp-trigger-btn:hover { background: ${t.isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)'}; }
      .xmp-trigger-btn:active { transform: scale(0.97); }
      .xmp-trigger-icon { color: ${t.accent}; flex-shrink: 0; }
      .xmp-bt-row {
        display: flex; align-items: center; justify-content: space-between;
        padding: 8px 12px; border-radius: 12px;
        background: ${t.isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.02)'};
      }
      .xmp-bt-label { font-size: 12px; font-weight: 600; }
      .xmp-bt-btn {
        padding: 6px 14px; border-radius: 8px; border: none; font-size: 11px; font-weight: 600;
        cursor: pointer; transition: all 0.2s ease;
      }
      .xmp-bt-btn.on { background: ${t.accentLight}; color: ${t.accent}; }
      .xmp-bt-btn.off { background: ${t.isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)'}; color: ${t.textSec}; }
      .xmp-bt-btn.danger { background: ${t.isDark ? 'rgba(239,83,80,0.15)' : 'rgba(239,83,80,0.1)'}; color: #ef5350; }
      .xmp-bt-btn:hover { opacity: 0.85; }
    `;
  }

  _attachEvents() {
    // Playback buttons
    this.shadowRoot.querySelectorAll('[data-action]').forEach(el => {
      el.addEventListener('click', (e) => {
        e.stopPropagation();
        const serviceMap = { play: 'media_play', pause: 'media_pause', stop: 'media_stop', next: 'media_next_track', prev: 'media_previous_track' };
        if (serviceMap[el.dataset.action]) {
          this._hass.callService('media_player', serviceMap[el.dataset.action], { entity_id: el.dataset.entity });
        }
      });
    });
    // Source buttons
    this.shadowRoot.querySelectorAll('[data-source]').forEach(el => {
      el.addEventListener('click', (e) => {
        e.stopPropagation();
        this._hass.callService('media_player', 'select_source', { entity_id: el.dataset.entity, source: el.dataset.source });
      });
    });
    // Generic button press
    this.shadowRoot.querySelectorAll('[data-press-button]').forEach(el => {
      el.addEventListener('click', (e) => {
        e.stopPropagation();
        this._hass.callService('button', 'press', { entity_id: el.dataset.pressButton });
      });
    });
    // Switch toggle
    this.shadowRoot.querySelectorAll('[data-toggle-switch]').forEach(el => {
      el.addEventListener('click', (e) => {
        e.stopPropagation();
        const entityId = el.dataset.toggleSwitch;
        const current = this._hass.states[entityId]?.state;
        this._hass.callService('switch', current === 'on' ? 'turn_off' : 'turn_on', { entity_id: entityId });
      });
    });
  }

  getCardSize() { return 3; }
}

// ─── Slot Card Editor ────────────────────────────────────────────────
class AudacXMP44SlotCardEditor extends HTMLElement {
  constructor() { super(); this.attachShadow({mode:'open'}); this._config = {}; this._rendered = false; }
  setConfig(config) {
    this._config = {...config};
    if (!this._rendered && this._hass) { this._render(); this._rendered = true; }
  }
  set hass(h) {
    this._hass = h;
    if (!this._rendered) { this._render(); this._rendered = true; }
  }

  _render() {
    if (!this._hass) return;
    const entities = xmpAutoDiscover(this._hass);
    const options = entities.map(id => {
      const e = this._hass.states[id];
      const name = e?.attributes?.friendly_name || id;
      const mod = e?.attributes?.module_name || '';
      return `<option value="${id}" ${this._config.entity === id ? 'selected' : ''}>${xmpEscape(name)}${mod ? ' (' + mod + ')' : ''}</option>`;
    }).join('');

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        .editor { padding: 16px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        .field { margin-bottom: 12px; }
        label { display: block; font-size: 12px; font-weight: 600; margin-bottom: 4px; color: var(--primary-text-color, #333); }
        input, select { width: 100%; padding: 8px 12px; border: 1px solid var(--divider-color, #ddd); border-radius: 8px; font-size: 14px; background: var(--card-background-color, #fff); color: var(--primary-text-color, #333); }
        .hint { font-size: 11px; color: var(--secondary-text-color, #888); margin-top: 2px; }
        .row { display: flex; gap: 12px; }
        .row .field { flex: 1; }
      </style>
      <div class="editor">
        <div class="field">
          <label>${xmpT('select_entity')}</label>
          <select id="entity">
            <option value="" ${!this._config.entity ? 'selected' : ''}>${xmpT('auto_first')}</option>
            ${options}
          </select>
        </div>
        <div class="field">
          <label>${xmpT('title')}</label>
          <input type="text" id="title" value="${xmpEscape(this._config.title || '')}" placeholder="${xmpT('auto')}">
        </div>
        <div class="row">
          <div class="field">
            <label>${xmpT('design')}</label>
            <select id="theme">
              <option value="auto" ${(this._config.theme||'auto')==='auto'?'selected':''}>${xmpT('auto')}</option>
              <option value="dark" ${this._config.theme==='dark'?'selected':''}>${xmpT('dark')}</option>
              <option value="light" ${this._config.theme==='light'?'selected':''}>${xmpT('light')}</option>
            </select>
          </div>
          <div class="field">
            <label>${xmpT('accent_color')}</label>
            <input type="text" id="accent_color" value="${this._config.accent_color || ''}" placeholder="#7c6bf0">
            <div class="hint">${xmpT('accent_hint')}</div>
          </div>
        </div>
      </div>
    `;
    ['entity','title','theme','accent_color'].forEach(field => {
      const el = this.shadowRoot.getElementById(field);
      if (el) el.addEventListener('change', () => {
        this._config[field] = el.value;
        this.dispatchEvent(new CustomEvent('config-changed', { detail: { config: this._config } }));
      });
    });
  }
}

_xmpDefine("audac-xmp44-slot-card", AudacXMP44SlotCard);
_xmpDefine("audac-xmp44-slot-card-editor", AudacXMP44SlotCardEditor);

Promise.all([
  customElements.whenDefined("audac-xmp44-card"),
  customElements.whenDefined("audac-xmp44-slot-card"),
]).then(() => { window.dispatchEvent(new Event("ll-rebuild")); });

console.info(
  `%c AUDAC-XMP44-CARD %c v${XMP44_CARD_VERSION} `,
  "color: white; background: #7c6bf0; font-weight: 700; padding: 2px 6px; border-radius: 4px 0 0 4px;",
  "color: #7c6bf0; background: #e8e5fc; font-weight: 700; padding: 2px 6px; border-radius: 0 4px 4px 0;"
);
