/**
 * map.js — 指揮情境圖模組（C1-F CSP 模組化）
 *
 * 職責：
 *   - 載入 /static/map_config.json
 *   - 管理站內靜態圖與站外 Leaflet 地圖切換
 *   - 渲染基本節點 / 事件 marker
 *   - 提供 main.js 事件委派所需的地圖操作函式
 *
 * 可 import：ws.js。不得 import events.js / decisions.js / cop.js / charts.js。
 */

import { authFetch } from './ws.js';

const API_BASE = location.origin;
const el = id => document.getElementById(id);

let _deps = {};
let _mapConfig = null;
let _currentMap = 'indoor';
let _leafletMap = null;
let _leafletMarkers = [];
let _pinEditMode = false;
let _coordDisplayMode = 'mgrs';

const _PERM_NODES = [
  { id: 'node_shelter', label: '收容組', node_type: 'shelter', icon: 'pin' },
  { id: 'node_medical', label: '醫療組', node_type: 'medical', icon: 'pin' },
  { id: 'node_command', label: '指揮部', node_type: 'command', icon: 'pin' },
  { id: 'node_forward', label: '前進組', node_type: 'forward', icon: 'pin' },
  { id: 'node_security', label: '安全組', node_type: 'security', icon: 'pin' },
];

const _EVENT_TYPES = {
  explosive: { label: '疑似爆裂物', group: 'security', severity: 'critical' },
  drone: { label: '無人機威脅', group: 'security', severity: 'critical' },
  violent: { label: '暴力事件', group: 'security', severity: 'critical' },
  unknown_person: { label: '不明人士', group: 'security', severity: 'warning' },
  perimeter: { label: '管制區異常', group: 'security', severity: 'warning' },
  crowd: { label: '秩序問題', group: 'security', severity: 'warning' },
  rescue: { label: '受困救援', group: 'rescue', severity: 'warning' },
  qrf: { label: 'QRF 出動', group: 'rescue', severity: 'warning' },
  mci: { label: '大量傷亡', group: 'medical', severity: 'critical' },
  emergency: { label: '緊急病症', group: 'medical', severity: 'critical' },
  infectious: { label: '傳染疑慮', group: 'medical', severity: 'warning' },
  capacity: { label: '量能超載', group: 'care', severity: 'warning' },
  isolation: { label: '隔離事件', group: 'care', severity: 'warning' },
  person_need: { label: '人員狀況', group: 'care', severity: 'info' },
  comm_fail: { label: '通訊異常', group: 'infra', severity: 'warning' },
  facility: { label: '設施異常', group: 'infra', severity: 'info' },
  equipment: { label: '設備故障', group: 'infra', severity: 'info' },
  evacuation: { label: '撤離', group: 'ops', severity: 'warning' },
  resource: { label: '資源調度', group: 'ops', severity: 'info' },
  situation: { label: '現場變化', group: 'ops', severity: 'info' },
  hazard: { label: '危害回報', group: 'ops', severity: 'info' },
  other: { label: '其他', group: 'ops', severity: 'info' },
};

const _EVENT_GROUPS = {
  security: '安全威脅',
  rescue: '搜救行動',
  medical: '醫療緊急',
  care: '收容照護',
  infra: '基礎設施',
  ops: '行動管理',
};

export function initMap(deps = {}) {
  _deps = deps;
  return _loadMapConfig();
}

async function _loadMapConfig() {
  try {
    const resp = await fetch(API_BASE + '/static/map_config.json');
    _mapConfig = await resp.json();
  } catch (e) {
    console.warn('[map.js] map_config 載入失敗', e);
    _mapConfig = { maps: { indoor: { zones: [] }, outdoor: { zones: [] } } };
  }
  switchMap(sessionStorage.getItem('_currentMap') || 'indoor');
}

export function getMapConfig() {
  return _mapConfig;
}

export function switchMap(key) {
  if (key === 'osm') key = 'outdoor';
  _currentMap = key || 'indoor';
  sessionStorage.setItem('_currentMap', _currentMap);
  document.querySelectorAll('.map-tab').forEach(t => {
    t.classList.toggle('active', t.dataset.map === _currentMap);
  });

  const isOutdoor = _currentMap === 'outdoor';
  const mapImg = el('map-img');
  const overlay = el('map-overlay');
  const leafletEl = el('leaflet-map');
  if (mapImg) mapImg.style.display = isOutdoor ? 'none' : '';
  if (overlay) overlay.style.display = isOutdoor ? 'none' : '';
  if (leafletEl) leafletEl.classList.toggle('active', isOutdoor);
  const mgrsIsland = el('mgrs-island');
  if (mgrsIsland) mgrsIsland.style.display = isOutdoor ? 'flex' : 'none';

  if (isOutdoor) {
    _initLeaflet();
    refreshLeafletMarkers();
    return;
  }

  const map = _mapConfig?.maps?.[_currentMap];
  if (mapImg && map?.image) {
    mapImg.src = '/static/' + map.image;
    mapImg.style.display = '';
  }
  renderMapOverlay();
}

function _initLeaflet() {
  if (!window.L || !el('leaflet-map')) return;
  if (!_leafletMap) {
    _leafletMap = L.map('leaflet-map', { zoomControl: false }).setView([24.8283, 121.0149], 15);
    _leafletMap.on('click', e => {
      if (el('map-coord-panel')) {
        el('map-coord-panel').style.display = 'block';
        el('map-coord-panel').textContent = _coordValue(e.latlng.lat, e.latlng.lng);
      }
    });
  }
  setTimeout(() => _leafletMap.invalidateSize(), 0);
}

export function renderMapOverlay() {
  const overlay = el('map-overlay');
  if (!overlay || !_mapConfig) return;
  const map = _mapConfig.maps?.[_currentMap];
  overlay.innerHTML = '';
  if (!map?.zones) return;
  overlay.style.pointerEvents = 'none';

  const data = _deps.getData?.() || {};
  for (const zone of map.zones) {
    if (zone.event_id) {
      const ev = (data.events || []).find(item => item.id === zone.event_id);
      if (ev && ['resolved', 'closed'].includes(ev.status)) continue;
    }
    const marker = document.createElement('button');
    marker.type = 'button';
    marker.className = 'zone-marker';
    marker.style.left = (zone.x_pct || 50) + '%';
    marker.style.top = (zone.y_pct || 50) + '%';
    marker.style.pointerEvents = 'auto';
    marker.dataset.zoneId = zone.id;
    marker.innerHTML = `<div class="zone-dot">${_icon(zone)}</div>
      <div class="zone-info"><div class="zone-label">${zone.event_code || zone.label || zone.id}</div></div>`;
    marker.addEventListener('click', () => {
      if (zone.event_id) _deps.showEventProcessModal?.(zone);
      else showZoneDetail(zone);
    });
    overlay.appendChild(marker);
  }
}

export function refreshLeafletMarkers() {
  if (!_leafletMap || !_mapConfig) return;
  _leafletMarkers.forEach(m => m.remove());
  _leafletMarkers = [];
  const map = _mapConfig.maps?.outdoor;
  if (!map?.zones || !window.L) return;
  for (const zone of map.zones) {
    if (zone.lat == null || zone.lng == null) continue;
    const marker = L.marker([zone.lat, zone.lng], { title: zone.label || zone.id });
    marker.on('click', () => zone.event_id ? _deps.showEventProcessModal?.(zone) : showZoneDetail(zone));
    marker.addTo(_leafletMap);
    _leafletMarkers.push(marker);
  }
}

function _icon(zone) {
  if (zone.icon === 'pin') return '●';
  if (zone.event_id || zone.event_code) return '!';
  return '◆';
}

export function findZoneByEventId(eventId) {
  if (!_mapConfig) return null;
  for (const map of Object.values(_mapConfig.maps || {})) {
    const found = (map.zones || []).find(z => z.event_id === eventId || z.id === eventId);
    if (found) return found;
  }
  return null;
}

export function showZoneDetail(zone) {
  if (!zone) return;
  const body = `<div style="font-size:12px;line-height:1.7;">
    <div>類型：${zone.node_type || '—'}</div>
    <div>座標：${zone.lat != null ? _coordValue(zone.lat, zone.lng) : '站內相對位置'}</div>
  </div>`;
  _deps.openModal?.(zone.label || zone.id || '節點', body);
}

export function openMapConfigPanel() {
  const currentImage = _mapConfig?.maps?.indoor?.image || '—';
  const rows = _PERM_NODES.map(n => `<div style="display:flex;justify-content:space-between;gap:8px;padding:4px 0;border-bottom:1px solid var(--border);">
    <span>${n.label}</span><button data-action="closeModal" class="adm-btn">關閉</button></div>`).join('');
  _deps.openModal?.('地圖設定', `<div style="font-size:11px;color:var(--text2);margin-bottom:8px;">站內圖：${currentImage}</div>${rows}`);
}

export function closeMapConfigPanel() {
  el('map-config-overlay')?.style.setProperty('display', 'none');
}

export async function saveMapConfig() {
  if (!_mapConfig) return;
  await authFetch(API_BASE + '/api/map_config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(_mapConfig),
  });
}

export function togglePinEditMode() {
  _pinEditMode = !_pinEditMode;
  const btn = el('pin-edit-btn');
  if (btn) btn.textContent = _pinEditMode ? '調整中...' : '調整據點';
  renderMapOverlay();
}

export function cancelPlaceMode() {
  const panel = el('map-panel');
  panel?.classList.remove('placing');
}

export function _populateNapsgCsel() {
  const panel = el('place-type-panel');
  if (!panel) return;
  panel.innerHTML = '';
  let group = null;
  for (const [key, def] of Object.entries(_EVENT_TYPES)) {
    if (def.group !== group) {
      group = def.group;
      const h = document.createElement('div');
      h.className = 'csel-group-header';
      h.textContent = _EVENT_GROUPS[group] || group;
      panel.appendChild(h);
    }
    const item = document.createElement('button');
    item.type = 'button';
    item.className = 'csel-opt';
    item.dataset.value = key;
    item.textContent = def.label;
    item.addEventListener('click', () => {
      el('place-type-label').textContent = def.label;
      panel.classList.remove('open');
      onPlaceTypeChange();
    });
    panel.appendChild(item);
  }
}

export function toggleCsel() {
  el('place-type-panel')?.classList.toggle('open');
}

export function onPlaceTypeChange() {
  el('map-panel')?.classList.add('placing');
}

export function _mgrsSearch() {
  const input = el('mgrs-input');
  if (!input || !_leafletMap) return;
  input.blur();
}

export function _toggleCoordMode() {
  _coordDisplayMode = _coordDisplayMode === 'mgrs' ? 'wgs84' : 'mgrs';
}

export function _panToCoordTarget(event) {
  event?.stopPropagation?.();
}

function _coordValue(lat, lng) {
  if (_coordDisplayMode === 'wgs84') return `${lat.toFixed(6)}, ${lng.toFixed(6)}`;
  return `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
}

export function _toggleMgrsGrid() {}
export function _toggleLayerPanel() {
  const panel = el('layer-panel');
  if (panel) panel.style.display = panel.style.display === 'block' ? 'none' : 'block';
}
export function _closeLayerPanel() { if (el('layer-panel')) el('layer-panel').style.display = 'none'; }
export function _toggleLayer() {}
export function _startPolyDraw() {}
export function _cancelPolyDraw() {}
export function _finishPolyDraw() {}
export function _savePolygon() {}
export function _deletePolygon() {}
export function _resetPolyLabelAnchor() {}
export function _openPolyForm() {}
export function _openInfraForm() {}
export function _startInfraPlace() {}
export function _deleteInfra() {}
export function _saveInfraPosition() {}
export function _openFlowForm() {}
export function _saveFlow() {}
export function _deleteFlow() {}
export function _startRouteDraw() {}
export function _cancelRouteDraw() {}
export function _finishRouteDraw() {}
export function _openRouteForm() {}
export function _saveRoute() {}
export function _deleteRoute() {}
export function _resetRouteLabelAnchor() {}
export function _cancelNodePlace() {}
export function _cancelEventPin() {}
export function admUploadMapImage() {}
export function admRemoveMapImage() {}
export function l3SubTab() {}
export function openL4Detail() {}
export function backToL3() {}
export function loadL3Records() {}
export function _loadPwaIncidents() {}
export let _zoneModalTab = 'events';
export function setZoneModalTab(tab) { _zoneModalTab = tab; }
export function _renderZoneModal() {}
