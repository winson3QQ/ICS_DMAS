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
let _polygonLayer = null;
let _infraLayer = null;
let _flowLayer = null;
let _routeLayer = null;
let _pinEditMode = false;
let _coordDisplayMode = 'mgrs';
let _mgrsGridVisible = false;
const _layerVis = { zones: true, polygons: true, infra: true, flows: true, routes: true, mgrs: false };

const _HSINCHU_CENTER = [24.8283, 121.0149];
const _HSINCHU_ZOOM = 15;

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

const _NAPSG_GROUP_ABBR = { security: '安', rescue: '救', medical: '醫', care: '護', infra: '設', ops: '行' };
const _NODE_ABBR = { shelter: '收', medical: '醫', forward: '前', security: '安', command: '指' };
const _NODE_COLORS = { shelter: '#f0883e', medical: '#e05555', forward: '#58a6ff', security: '#e3b341', command: '#8b949e' };
const _SEV_COLORS = { critical: '#e05555', warning: '#e3b341', info: '#3a4149' };
const _RAG_COLORS = { ok: '#1a9e52', warn: '#d49000', crit: '#cc2a2a' };

const POLY_TYPES = {
  control:    { label: '管制區', color: '#e05555', dash: true },
  evacuation: { label: '疏散範圍', color: '#e3b341', dash: true },
  assembly:   { label: '集結點', color: '#3fb950', dash: false },
  danger:     { label: '危險區域', color: '#c0392b', dash: false },
  ops:        { label: '作業區', color: '#58a6ff', dash: false },
};

const INFRA_TYPES = {
  hospital: { label: '醫院', color: '#e05555', abbr: 'H' },
  shelter:  { label: '收容所', color: '#e3b341', abbr: 'S' },
  police:   { label: '警察局', color: '#58a6ff', abbr: 'P' },
  fire:     { label: '消防站', color: '#ff7f50', abbr: 'F' },
  utility:  { label: '公用設施', color: '#8b949e', abbr: 'U' },
};

const ROUTE_TYPES = {
  primary:   { label: '主要疏散路線', color: '#56d364', dash: false },
  secondary: { label: '次要路線', color: '#e3b341', dash: true },
  emergency: { label: '緊急通道', color: '#e05555', dash: false },
};

const FLOW_TYPES = {
  casualty:   { label: '傷患後送', color: '#e05555' },
  evacuation: { label: '疏散人員', color: '#e3b341' },
  resource:   { label: '資源調度', color: '#56d364' },
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
    _leafletMap = L.map('leaflet-map', {
      zoomControl: true,
      attributionControl: true,
      doubleClickZoom: false,
    }).setView(_HSINCHU_CENTER, _HSINCHU_ZOOM);

    if (window.protomapsL?.leafletLayer) {
      window.protomapsL.leafletLayer({
        url: '/tiles/pmtiles/taiwan.pmtiles',
        flavor: 'grayscale',
      }).addTo(_leafletMap);
    }

    _leafletMap.on('click', e => {
      if (el('map-coord-panel')) {
        el('map-coord-panel').style.display = 'block';
        el('map-coord-panel').textContent = _coordValue(e.latlng.lat, e.latlng.lng);
      }
    });

    const savedView = sessionStorage.getItem('_mapView');
    if (savedView) {
      try {
        const { lat, lng, zoom } = JSON.parse(savedView);
        _leafletMap.setView([lat, lng], zoom);
      } catch (e) {
        _leafletMap.setView(_HSINCHU_CENTER, _HSINCHU_ZOOM);
      }
    }

    _leafletMap.on('moveend zoomend', () => {
      const c = _leafletMap.getCenter();
      sessionStorage.setItem('_mapView', JSON.stringify({
        lat: Math.round(c.lat * 100000) / 100000,
        lng: Math.round(c.lng * 100000) / 100000,
        zoom: _leafletMap.getZoom(),
      }));
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
  _renderPolygons();
  _renderInfra();
  _renderFlows();
  _renderRoutes();
  if (!_layerVis.zones) return;
  const map = _mapConfig.maps?.outdoor;
  if (!map?.zones || !window.L) return;
  const data = _deps.getData?.() || {};
  for (const zone of map.zones) {
    if (zone.lat == null || zone.lng == null) continue;
    const isEvent = !!(zone.event_id || zone.event_code);
    let severity = 'warning';
    if (isEvent) {
      const ev = (data.events || []).find(item => item.id === zone.event_id);
      if (!ev) severity = 'info';
      else if (['resolved', 'closed'].includes(ev.status)) continue;
      else severity = ev.severity || 'warning';
    }

    const nodeOpts = {};
    if (!isEvent && zone.icon === 'pin' && (zone.node_type === 'shelter' || zone.node_type === 'medical')) {
      const calc = data.calc || {};
      const piNode = (data.pi_nodes || []).find(n => n.unit_id === zone.node_type);
      let linkLevel = 'lkp';
      if (piNode?.last_seen_at) {
        const age = Date.now() - new Date(piNode.last_seen_at).getTime();
        linkLevel = age < 30000 ? 'ok' : age < 90000 ? 'warn' : 'crit';
      }
      const snapshot = calc[zone.node_type]?.snapshot;
      if (snapshot) {
        const used = snapshot.bed_used || 0;
        const total = snapshot.bed_total || 1;
        const pct = used / total * 100;
        nodeOpts.rag = pct >= 90 ? 'crit' : pct >= 70 ? 'warn' : 'ok';
        nodeOpts.badge = used;
      } else {
        nodeOpts.rag = 'ok';
        nodeOpts.badge = '—';
      }
      if (linkLevel === 'crit' || linkLevel === 'lkp') nodeOpts.stale = true;
      if (linkLevel === 'warn') nodeOpts.linkWarn = true;
    }

    const marker = L.marker([zone.lat, zone.lng], {
      icon: _napsgIcon(zone.node_type, severity, isEvent, nodeOpts),
      draggable: true,
      title: zone.label || zone.id,
    });
    marker.bindTooltip(
      `<span>${zone.label || zone.id}</span>${zone.event_code ? ` <span style="color:var(--yellow)">${zone.event_code}</span>` : ''}`,
      { className: 'napsg-tooltip', direction: 'top', offset: [0, -16], permanent: false }
    );
    marker.on('click', e => {
      L.DomEvent.stopPropagation(e);
      if (isEvent) _deps.showEventProcessModal?.(zone);
      else showZoneDetail(zone);
    });
    marker.on('dragend', async () => {
      const ll = marker.getLatLng();
      zone.lat = Math.round(ll.lat * 1000000) / 1000000;
      zone.lng = Math.round(ll.lng * 1000000) / 1000000;
      await saveMapConfig();
    });
    marker.addTo(_leafletMap);
    _leafletMarkers.push(marker);
  }
}

function _napsgIcon(nodeType, severity, isEvent, opts = {}) {
  if (isEvent) {
    const color = _SEV_COLORS[severity] || '#8b949e';
    const abbr = _NAPSG_GROUP_ABBR[nodeType] || _NODE_ABBR[nodeType] || '?';
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="26" height="26" viewBox="0 0 26 26">
      <polygon points="13,1 25,13 13,25 1,13" fill="${color}" stroke="#fff" stroke-width="2"/>
      <text x="13" y="17" text-anchor="middle" font-size="9" font-weight="700" fill="#fff"
            font-family="sans-serif">${abbr}</text>
    </svg>`;
    return L.divIcon({ html: svg, className: '', iconSize: [26, 26], iconAnchor: [13, 13] });
  }

  const abbr = _NODE_ABBR[nodeType] || '?';
  let color = _NODE_COLORS[nodeType] || '#8b949e';
  if ((nodeType === 'shelter' || nodeType === 'medical') && opts.rag) {
    color = _RAG_COLORS[opts.rag] || color;
  }
  const ragCls = opts.rag ? ' ' + opts.rag : '';
  const staleCls = opts.stale ? ' napsg-stale' : '';
  const linkWarnCls = opts.linkWarn ? ' link-warn' : '';
  let badgeHtml = '';
  if (opts.stale && (nodeType === 'shelter' || nodeType === 'medical')) {
    badgeHtml = '<div class="napsg-badge off">OFF</div>';
  } else if (opts.badge != null && opts.badge !== '') {
    const badgeClass = opts.rag === 'crit' ? 'crit' : opts.rag === 'warn' ? 'warn' : '';
    badgeHtml = `<div class="napsg-badge ${badgeClass}">${opts.badge}</div>`;
  }

  if (nodeType === 'forward' || nodeType === 'security') {
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
      <rect x="1" y="1" width="22" height="22" rx="2" fill="${color}" stroke="#fff" stroke-width="2"/>
      <text x="12" y="16" text-anchor="middle" font-size="9" font-weight="700" fill="#fff"
            font-family="sans-serif">${abbr}</text>
    </svg>`;
    return L.divIcon({
      html: `<div class="napsg-wrap${ragCls}${staleCls}${linkWarnCls}">${svg}${badgeHtml}</div>`,
      className: '', iconSize: [24, 24], iconAnchor: [12, 12],
    });
  }

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 28 28">
    <circle cx="14" cy="14" r="12" fill="${color}" stroke="#fff" stroke-width="2"/>
    <text x="14" y="18" text-anchor="middle" font-size="10" font-weight="700" fill="#fff"
          font-family="sans-serif">${abbr}</text>
  </svg>`;
  return L.divIcon({
    html: `<div class="napsg-wrap${ragCls}${staleCls}${linkWarnCls}">${svg}${badgeHtml}</div>`,
    className: '', iconSize: [28, 28], iconAnchor: [14, 14],
  });
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

function _renderPolygons() {
  if (!_leafletMap) return;
  if (!_polygonLayer) _polygonLayer = L.layerGroup().addTo(_leafletMap);
  _polygonLayer.clearLayers();
  if (!_layerVis.polygons) return;
  const polygons = _mapConfig?.maps?.outdoor?.polygons || [];
  for (const poly of polygons) {
    const dash = poly.dash ? '8 5' : null;
    const layer = L.polygon(poly.latlngs, {
      color: poly.color,
      weight: 2,
      dashArray: dash,
      fillColor: poly.color,
      fillOpacity: 0.12,
      interactive: true,
    }).addTo(_polygonLayer);
    layer.on('click', () => _deps.openModal?.(`▱ ${poly.label}`, _simpleInfo(POLY_TYPES[poly.poly_type]?.label || poly.poly_type)));
    if (poly.label) {
      const labelPos = poly.label_anchor ? [poly.label_anchor[0], poly.label_anchor[1]] : _polyCentroid(poly.latlngs);
      L.marker(labelPos, {
        icon: L.divIcon({
          html: `<div style="font-size:10px;font-weight:700;color:${poly.color};text-shadow:0 0 4px rgba(14,22,29,.9),0 0 4px rgba(14,22,29,.9);white-space:nowrap;padding:2px 4px;">${poly.label}</div>`,
          className: '',
          iconSize: [120, 20],
          iconAnchor: [0, 10],
        }),
        interactive: false,
        zIndexOffset: 100,
      }).addTo(_polygonLayer);
    }
  }
}

function _polyCentroid(latlngs) {
  const lat = latlngs.reduce((sum, point) => sum + point[0], 0) / latlngs.length;
  const lng = latlngs.reduce((sum, point) => sum + point[1], 0) / latlngs.length;
  return [lat, lng];
}

function _infraIcon(infraType) {
  const def = INFRA_TYPES[infraType] || INFRA_TYPES.utility;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 28 28">
    <circle cx="14" cy="14" r="12" fill="${def.color}" stroke="#fff" stroke-width="2" opacity=".92"/>
    <text x="14" y="18.5" text-anchor="middle" font-size="11" font-weight="700"
          font-family="sans-serif" fill="#fff">${def.abbr}</text>
  </svg>`;
  return L.divIcon({ html: svg, className: '', iconSize: [28, 28], iconAnchor: [14, 14] });
}

function _renderInfra() {
  if (!_leafletMap) return;
  if (!_infraLayer) _infraLayer = L.layerGroup().addTo(_leafletMap);
  _infraLayer.clearLayers();
  if (!_layerVis.infra) return;
  const items = _mapConfig?.maps?.outdoor?.infrastructure || [];
  for (const item of items) {
    const def = INFRA_TYPES[item.infra_type] || INFRA_TYPES.utility;
    const marker = L.marker([item.lat, item.lng], {
      icon: _infraIcon(item.infra_type),
      title: item.label,
      zIndexOffset: -100,
    });
    marker.bindTooltip(`<span style="color:${def.color}">${def.label}</span> ${item.label}`, {
      className: 'napsg-tooltip',
      direction: 'top',
      offset: [0, -16],
    });
    marker.on('click', e => {
      L.DomEvent.stopPropagation(e);
      _deps.openModal?.(`${def.abbr} ${item.label}`, _simpleInfo(def.label));
    });
    marker.addTo(_infraLayer);
  }
}

function _bearing(lat1, lng1, lat2, lng2) {
  const rad = Math.PI / 180;
  const dLng = (lng2 - lng1) * rad;
  const y = Math.sin(dLng) * Math.cos(lat2 * rad);
  const x = Math.cos(lat1 * rad) * Math.sin(lat2 * rad) -
    Math.sin(lat1 * rad) * Math.cos(lat2 * rad) * Math.cos(dLng);
  return ((Math.atan2(y, x) * 180 / Math.PI) + 360) % 360;
}

function _arrowIcon(angle, color) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="-11 -11 22 22">
    <polygon points="0,-9 5,4 0,1 -5,4" fill="${color}" stroke="rgba(14,22,29,.6)" stroke-width="1"
      transform="rotate(${angle})"/>
  </svg>`;
  return L.divIcon({ html: svg, className: '', iconSize: [22, 22], iconAnchor: [11, 11] });
}

function _renderRoutes() {
  if (!_leafletMap) return;
  if (!_routeLayer) _routeLayer = L.layerGroup().addTo(_leafletMap);
  _routeLayer.clearLayers();
  if (!_layerVis.routes) return;
  const routes = _mapConfig?.maps?.outdoor?.routes || [];
  for (const route of routes) {
    const line = L.polyline(route.latlngs, {
      color: route.color,
      weight: 3,
      dashArray: route.dash ? '8 5' : null,
      opacity: 0.9,
    }).addTo(_routeLayer);
    line.on('click', () => _deps.openModal?.(`↗ ${route.label}`, _simpleInfo(ROUTE_TYPES[route.route_type]?.label || route.route_type)));
    for (let i = 0; i < route.latlngs.length - 1; i += 1) {
      const [lat1, lng1] = route.latlngs[i];
      const [lat2, lng2] = route.latlngs[i + 1];
      L.marker([(lat1 + lat2) / 2, (lng1 + lng2) / 2], {
        icon: _arrowIcon(_bearing(lat1, lng1, lat2, lng2), route.color),
        interactive: false,
        zIndexOffset: 50,
      }).addTo(_routeLayer);
    }
    if (route.label) {
      const labelPos = route.label_anchor || route.latlngs[Math.floor(route.latlngs.length / 2)];
      L.marker(labelPos, {
        icon: L.divIcon({
          html: `<div style="font-size:10px;font-weight:700;color:${route.color};text-shadow:0 0 4px rgba(14,22,29,.9),0 0 4px rgba(14,22,29,.9);white-space:nowrap;padding:2px 4px;">${route.label}</div>`,
          className: '',
          iconSize: [120, 20],
          iconAnchor: [0, 10],
        }),
        interactive: false,
        zIndexOffset: 100,
      }).addTo(_routeLayer);
    }
  }
}

function _resolveRef(ref, flow) {
  if (!ref) {
    const zoneId = flow?.from_zone_id || flow?.to_zone_id;
    if (!zoneId) return null;
    ref = `zone:${zoneId}`;
  }
  const sep = ref.indexOf(':');
  const type = sep > 0 ? ref.slice(0, sep) : 'zone';
  const id = sep > 0 ? ref.slice(sep + 1) : ref;
  if (type === 'infra') {
    const item = (_mapConfig?.maps?.outdoor?.infrastructure || []).find(i => i.id === id);
    return item ? { lat: item.lat, lng: item.lng, label: item.label } : null;
  }
  const zone = (_mapConfig?.maps?.outdoor?.zones || []).find(z => z.id === id);
  return zone ? { lat: zone.lat, lng: zone.lng, label: zone.label } : null;
}

function _renderFlows() {
  if (!_leafletMap) return;
  if (!_flowLayer) _flowLayer = L.layerGroup().addTo(_leafletMap);
  _flowLayer.clearLayers();
  if (!_layerVis.flows) return;
  const flows = _mapConfig?.maps?.outdoor?.flows || [];
  for (const flow of flows) {
    const from = _resolveRef(flow.from_ref || (flow.from_zone_id ? `zone:${flow.from_zone_id}` : null), flow);
    const to = _resolveRef(flow.to_ref || (flow.to_zone_id ? `zone:${flow.to_zone_id}` : null), flow);
    if (!from?.lat || !to?.lat) continue;
    const def = FLOW_TYPES[flow.flow_type] || FLOW_TYPES.casualty;
    const line = L.polyline([[from.lat, from.lng], [to.lat, to.lng]], {
      color: def.color,
      weight: 2.5,
      opacity: 0.85,
    }).addTo(_flowLayer);
    line.on('click', () => _deps.openModal?.(`→ ${flow.label || def.label}`, _simpleInfo(`${from.label || '?'} → ${to.label || '?'}`)));
    L.marker([(from.lat + to.lat) / 2, (from.lng + to.lng) / 2], {
      icon: _arrowIcon(_bearing(from.lat, from.lng, to.lat, to.lng), def.color),
      interactive: false,
      zIndexOffset: 50,
    }).addTo(_flowLayer);
  }
}

function _simpleInfo(text) {
  return `<div style="font-size:12px;line-height:1.7;color:var(--text2);">${text || ''}</div>`;
}

export function _toggleMgrsGrid() {
  _mgrsGridVisible = !_mgrsGridVisible;
  _layerVis.mgrs = _mgrsGridVisible;
  document.getElementById('btn-mgrs-grid')?.classList.toggle('active', _mgrsGridVisible);
}
export function _toggleLayerPanel() {
  const panel = el('layer-panel');
  if (panel) panel.style.display = panel.style.display === 'block' ? 'none' : 'block';
}
export function _closeLayerPanel() { if (el('layer-panel')) el('layer-panel').style.display = 'none'; }
export function _toggleLayer(key) {
  if (!key || !(key in _layerVis)) return;
  _layerVis[key] = !_layerVis[key];
  refreshLeafletMarkers();
}
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
