/**
 * auth.js — 認證模組（root module）
 *
 * 職責：login / logout / session / token 持有 + PinLock + Settings + Admin + Pi 節點管理
 * 不可 import 其他業務模組。
 *
 * 對外 export：
 *   getToken()           — 取目前 session token
 *   clearSession()       — 登出並清除狀態（ws.js 的 _pollActive 透過 onClearSession callback 協調）
 *   onAuthChange(cb)     — 登入 / 登出事件監聽
 *   authFetch(url, opts) — 帶 token 的 fetch，401 自動登出
 *   PinLock              — 閒置鎖定物件
 *   getCurrentOperator() — 取目前登入帳號
 */

'use strict';

const el = id => document.getElementById(id);
const API_BASE = location.origin;

// ── session callbacks ──────────────────────────────────────────
const _authListeners = [];
let _onEnterDashboard = null;
let _openModal = null;
let _closeModal = null;

/** 登入 / 登出時通知訂閱者 */
function _notifyAuth(type) {
  _authListeners.forEach(cb => cb(type));
}

export function onAuthChange(cb) {
  _authListeners.push(cb);
}

// ── token 存取 ─────────────────────────────────────────────────
export function getToken() {
  return sessionStorage.getItem('cmd_session_id');
}

export function getCurrentOperator() {
  return sessionStorage.getItem('cmd_username') || '指揮部';
}

// ── authFetch ──────────────────────────────────────────────────
/** 所有 API 呼叫統一加 session token；401 自動觸發登出 */
export async function authFetch(url, opts = {}) {
  const token = getToken();
  if (token) {
    opts.headers = Object.assign({}, opts.headers || {}, {'X-Session-Token': token});
  }
  const resp = await fetch(url, opts);
  if (resp.status === 401) {
    clearSession();
    el('login-screen').style.display = '';
    return resp;
  }
  return resp;
}

// ── session 清除 ───────────────────────────────────────────────
export function clearSession() {
  sessionStorage.removeItem('cmd_session_id');
  sessionStorage.removeItem('cmd_username');
  sessionStorage.removeItem('cmd_role');
  sessionStorage.removeItem('cmd_display_name');
  sessionStorage.removeItem('cmd_login_time');
  PinLock.clear();
  _notifyAuth('logout');
}

// ── 登入 ───────────────────────────────────────────────────────
export async function handleCmdLogin() {
  const btn = el('cmd-login-btn');
  const warn = el('cmd-login-warn');
  const username = el('cmd-username').value.trim();
  const pin = el('cmd-pin').value.trim();
  warn.textContent = '';

  if (!username) { warn.textContent = '請輸入帳號'; return; }
  if (!/^\d{4,6}$/.test(pin)) { warn.textContent = 'PIN 須為 4-6 位數字'; return; }

  btn.disabled = true;
  try {
    const resp = await fetch(API_BASE + '/api/auth/login', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({username, pin}),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      warn.textContent = err.detail || '登入失敗';
      return;
    }
    const data = await resp.json();
    sessionStorage.setItem('cmd_session_id', data.session_id);
    sessionStorage.setItem('cmd_username', data.username);
    sessionStorage.setItem('cmd_role', data.role);
    sessionStorage.setItem('cmd_display_name', data.display_name);
    sessionStorage.setItem('cmd_login_time', new Date().toISOString());
    // 儲存 PIN hash 供 PinLock 客戶端解鎖用
    const enc = new TextEncoder();
    const salt = crypto.getRandomValues(new Uint8Array(16));
    const key = await crypto.subtle.importKey('raw', enc.encode(pin), 'PBKDF2', false, ['deriveBits']);
    const bits = await crypto.subtle.deriveBits({name:'PBKDF2',salt,iterations:100000,hash:'SHA-256'}, key, 256);
    sessionStorage.setItem('cmd_pin_hash', Array.from(new Uint8Array(bits)).map(b=>b.toString(16).padStart(2,'0')).join(''));
    sessionStorage.setItem('cmd_pin_salt', Array.from(salt).map(b=>b.toString(16).padStart(2,'0')).join(''));

    _enterDashboard();
  } catch(e) {
    warn.textContent = '連線失敗';
  } finally {
    btn.disabled = false;
  }
}

function _enterDashboard() {
  el('login-screen').style.display = 'none';
  el('cmd-user-badge').textContent = sessionStorage.getItem('cmd_display_name') || sessionStorage.getItem('cmd_username');
  // 角色限制
  const isCommander = sessionStorage.getItem('cmd_role') === '指揮官';
  el('stg-admin-section').style.display = isCommander ? '' : 'none';
  // 更新 settings footer
  el('stg-user-info').textContent = (sessionStorage.getItem('cmd_display_name') || '') + ' (' + sessionStorage.getItem('cmd_role') + ')　' + (_fmtLocalDT(sessionStorage.getItem('cmd_login_time') || '') || '').slice(11,19);
  PinLock.start();
  _notifyAuth('login');
  if (typeof _onEnterDashboard === 'function') _onEnterDashboard();
}

// ── 登出 ───────────────────────────────────────────────────────
export async function cmdLogout() {
  closeSettings();
  try {
    await authFetch(API_BASE + '/api/auth/logout', {method:'POST'});
  } catch(e) {}
  clearSession();
  el('login-screen').style.display = '';
  el('cmd-username').value = '';
  el('cmd-pin').value = '';
  el('cmd-login-warn').textContent = '';
  el('cmd-user-badge').textContent = '';
}

// ── PinLock ────────────────────────────────────────────────────
export const PinLock = (() => {
  const IDLE_MS = 270000;
  const WARN_S = 30;
  let _timer = null, _warnTimer = null, _countdown = 0;

  function _reset() {
    clearTimeout(_timer);
    clearTimeout(_warnTimer);
    _countdown = 0;
    el('idle-countdown').style.display = 'none';
    el('idle-countdown').textContent = '';
    _timer = setTimeout(_warn, IDLE_MS);
  }

  function _warn() {
    _countdown = WARN_S;
    el('idle-countdown').style.display = '';
    _tick();
  }

  function _tick() {
    if (_countdown <= 0) { _lock(); return; }
    el('idle-countdown').textContent = _countdown + 's';
    _countdown--;
    _warnTimer = setTimeout(_tick, 1000);
  }

  function _lock() {
    el('pin-lock-overlay').classList.add('show');
    el('pinlock-user').textContent = sessionStorage.getItem('cmd_display_name') || sessionStorage.getItem('cmd_username') || '';
    el('pinlock-pin').value = '';
    el('pinlock-warn').textContent = '';
    _notifyAuth('lock');
  }

  async function unlock() {
    const pin = el('pinlock-pin').value.trim();
    if (!pin) { el('pinlock-warn').textContent = '請輸入 PIN'; return; }
    const stored = sessionStorage.getItem('cmd_pin_hash');
    const saltHex = sessionStorage.getItem('cmd_pin_salt');
    if (!stored || !saltHex) { cmdLogout(); return; }
    const enc = new TextEncoder();
    const salt = new Uint8Array(saltHex.match(/.{2}/g).map(h => parseInt(h, 16)));
    const key = await crypto.subtle.importKey('raw', enc.encode(pin), 'PBKDF2', false, ['deriveBits']);
    const bits = await crypto.subtle.deriveBits({name:'PBKDF2',salt,iterations:100000,hash:'SHA-256'}, key, 256);
    const hash = Array.from(new Uint8Array(bits)).map(b=>b.toString(16).padStart(2,'0')).join('');
    if (hash !== stored) { el('pinlock-warn').textContent = 'PIN 錯誤'; return; }
    el('pin-lock-overlay').classList.remove('show');
    try { await authFetch(API_BASE + '/api/auth/heartbeat'); } catch(e) {}
    _notifyAuth('unlock');
    _reset();
  }

  function start() {
    ['click','keydown','touchstart','scroll'].forEach(evt =>
      document.addEventListener(evt, _reset, {passive:true})
    );
    _reset();
  }

  function clear() {
    clearTimeout(_timer);
    clearTimeout(_warnTimer);
    el('idle-countdown').style.display = 'none';
  }

  return { start, clear, unlock, resetIdle: _reset };
})();

export function unlockPinLock() {
  return PinLock.unlock();
}

export function setModalHandlers({ openModal, closeModal } = {}) {
  _openModal = typeof openModal === 'function' ? openModal : null;
  _closeModal = typeof closeModal === 'function' ? closeModal : null;
}

// ── Settings ───────────────────────────────────────────────────
export function openSettings() {
  el('settings-overlay').classList.add('show');
  el('settings-panel').classList.add('show');
}

export function closeSettings() {
  el('settings-overlay').classList.remove('show');
  el('settings-panel').classList.remove('show');
}

export function openConfigModal() {
  Promise.all([
    authFetch(API_BASE + '/api/config/command_post_name').then(r => r.ok ? r.json() : {value:null}),
    authFetch(API_BASE + '/api/config/command_post_location').then(r => r.ok ? r.json() : {value:null}),
  ]).then(([nameRes, locRes]) => {
    openModal('指揮部設定',
      '<div style="display:flex;flex-direction:column;gap:12px;">' +
        '<label style="font-size:11px;color:var(--text2);">指揮部名稱</label>' +
        '<input id="cfg-name" class="login-input" value="' + (nameRes.value || '') + '" placeholder="例：校園災害應變指揮部">' +
        '<label style="font-size:11px;color:var(--text2);">位置</label>' +
        '<input id="cfg-location" class="login-input" value="' + (locRes.value || '') + '" placeholder="例：行政大樓 1F">' +
      '</div>',
      '<button class="adm-btn" data-action="close-modal">取消</button>' +
      '<button class="login-btn" style="width:auto;padding:6px 16px;" data-action="save-config">儲存</button>'
    );
  });
}

export async function saveConfig() {
  const name = el('cfg-name')?.value.trim();
  const loc = el('cfg-location')?.value.trim();
  if (name) await authFetch(API_BASE + '/api/config/command_post_name', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({value:name})});
  if (loc) await authFetch(API_BASE + '/api/config/command_post_location', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({value:loc})});
  closeModal();
}

export function exportDashboardJSON(data) {
  if (!data) return;
  const blob = new Blob([JSON.stringify(data, null, 2)], {type:'application/json'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'dashboard_' + new Date().toISOString().slice(0,19).replace(/:/g,'-') + '.json';
  a.click();
  URL.revokeObjectURL(a.href);
}

export async function showAuditLog(existingLogs = null, activeFilter = 'all') {
  if (Array.isArray(existingLogs)) {
    _auditRenderModal(existingLogs, activeFilter);
    return;
  }
  const resp = await authFetch(API_BASE + '/api/audit_log?limit=200');
  if (!resp.ok) return;
  const logs = await resp.json();
  _auditRenderModal(logs, activeFilter);
}

// ── 日期格式化 ─────────────────────────────────────────────────
export function fmtLocalDT(isoStr) {
  if (!isoStr) return '';
  const d = new Date(isoStr.endsWith('Z') ? isoStr : isoStr + 'Z');
  const p = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

// 內部別名（向下相容）
const _fmtLocalDT = fmtLocalDT;

// ── Audit log ──────────────────────────────────────────────────
const _AUDIT_BADGE = {
  'login':                  { c:'#388bfd', zh:'登入' },
  'logout':                 { c:'#8b949e', zh:'登出' },
  'event_created':          { c:'#3fb950', zh:'新增事件' },
  'event_status_updated':   { c:'#e3b341', zh:'更新狀態' },
  'event_note_added':       { c:'#79c0ff', zh:'補充備註' },
  'decision_created':       { c:'#d2a8ff', zh:'新增裁示' },
  'decision_made':          { c:'#ff7b72', zh:'裁示決定' },
  'snapshot_received':      { c:'#56d364', zh:'收快照' },
  'db_reset':               { c:'#f85149', zh:'重設DB' },
  'exercise_reset':         { c:'#f85149', zh:'重設演練' },
  'account_created':        { c:'#388bfd', zh:'建立帳號' },
  'account_status_updated': { c:'#e3b341', zh:'帳號狀態' },
  'account_pin_reset':      { c:'#e3b341', zh:'重設PIN' },
  'account_role_updated':   { c:'#d2a8ff', zh:'更新角色' },
  'account_deleted':        { c:'#f85149', zh:'刪除帳號' },
  'config_updated':         { c:'#8b949e', zh:'更新設定' },
  'three_pass_sync':        { c:'#79c0ff', zh:'三通同步' },
  'conflict_resolved':      { c:'#56d364', zh:'衝突解決' },
  'manual_input':           { c:'#56d364', zh:'手動輸入' },
  'pi_node_created':        { c:'#388bfd', zh:'新增Pi節點' },
  'pi_node_deleted':        { c:'#f85149', zh:'刪除Pi節點' },
};

function _auditEventLabel(log) {
  if (log._event_desc) return log._event_desc.length > 28 ? log._event_desc.slice(0,26)+'…' : log._event_desc;
  try {
    const d = JSON.parse(log.detail || '{}');
    if (d.event_code) return d.event_code;
  } catch(e) {}
  return (log.target_id || '').slice(0,8) || '—';
}

const _AUDIT_FILTERS = [
  { key:'all',     zh:'全部' },
  { key:'account', zh:'帳號', match: a => a.startsWith('login') || a.startsWith('logout') || a.startsWith('account') },
  { key:'event',   zh:'事件', match: a => a.startsWith('event') || a.startsWith('decision') },
  { key:'system',  zh:'系統', match: a => ['snapshot_received','db_reset','exercise_reset','config_updated','three_pass_sync','conflict_resolved','pi_node_created','pi_node_deleted','manual_input'].includes(a) },
];

function _auditRenderModal(logs, activeFilter) {
  const filtered = activeFilter === 'all' ? logs
    : logs.filter(l => {
        const def = _AUDIT_FILTERS.find(f => f.key === activeFilter);
        return def?.match?.(l.action_type || '');
      });

  const chips = _AUDIT_FILTERS.map(f =>
    `<span data-action="audit-filter" data-filter="${f.key}" data-logs-key="latest"
      style="cursor:pointer;padding:3px 10px;border-radius:12px;font-size:10px;white-space:nowrap;
             background:${f.key===activeFilter?'var(--yellow)':'var(--surface2)'};
             color:${f.key===activeFilter?'#000':'var(--text2)'};border:1px solid var(--border);">${f.zh}</span>`
  ).join('');

  let lastDate = '';
  let rows = '';
  for (const log of filtered) {
    const dt = _fmtLocalDT(log.created_at);
    const dateStr = dt.slice(0,10);
    if (dateStr !== lastDate) {
      lastDate = dateStr;
      rows += `<div style="font-size:10px;color:var(--text3);padding:8px 0 4px;border-top:1px solid var(--border);margin-top:4px;">${dateStr}</div>`;
    }

    const badge = _AUDIT_BADGE[log.action_type] || { c:'#8b949e', zh: log.action_type };
    const badgeHtml = `<span style="display:inline-block;padding:1px 7px;border-radius:10px;font-size:10px;font-weight:600;background:${badge.c}22;color:${badge.c};border:1px solid ${badge.c}55;white-space:nowrap;">${badge.zh}</span>`;

    let targetHtml = '';
    if (log.target_table === 'events') {
      targetHtml = `<span style="color:var(--text2);font-size:11px;">${_auditEventLabel(log)}</span>`;
    } else if (log.target_table === 'accounts') {
      targetHtml = `<span style="color:var(--text2);font-size:11px;">${log.target_id || ''}</span>`;
    } else if (log.target_table) {
      targetHtml = `<span style="color:var(--text3);font-size:10px;">${log.target_table}</span>`;
    }

    rows += `<div style="display:grid;grid-template-columns:90px 88px 80px 1fr;gap:6px;align-items:center;padding:5px 2px;border-bottom:1px solid rgba(255,255,255,.04);">
      <span style="font-family:var(--mono);font-size:10px;color:var(--text3);">${dt.slice(11)}</span>
      ${badgeHtml}
      <span style="font-size:11px;color:var(--text3);">${log.operator || '—'}</span>
      ${targetHtml}
    </div>`;
  }

  if (!rows) rows = `<div style="color:var(--text3);font-size:11px;padding:20px 0;text-align:center;">（無紀錄）</div>`;

  // 暫存 logs 供篩選 chip 使用
  window._auditLogsCache = logs;

  const bodyHtml = `
    <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px;">${chips}</div>
    <div style="max-height:55vh;overflow-y:auto;">${rows}</div>`;

  openModal('稽核日誌', bodyHtml, `<button class="adm-btn" data-action="close-modal">關閉</button>`);
}

// ── Admin 面板 ─────────────────────────────────────────────────
let _admPin = '';

/** 提供給 cop.js 等模組讀取已快取的 Admin PIN（admin 面板登入後設定） */
export function getAdminPin() { return _admPin; }

export function openAdminPanel() {
  closeSettings();
  el('admin-overlay').classList.add('show');
  el('admin-panel').classList.add('show');
  el('adm-pin-screen').style.display = '';
  el('adm-main').style.display = 'none';
  el('adm-pin-input').value = '';
  el('adm-pin-warn').textContent = '';
  setTimeout(() => el('adm-pin-input').focus(), 100);
}

export function closeAdminPanel() {
  el('admin-overlay').classList.remove('show');
  el('admin-panel').classList.remove('show');
  _admPin = '';
}

export async function adminLogin() {
  const pin = el('adm-pin-input').value.trim();
  if (!pin) { el('adm-pin-warn').textContent = '請輸入 PIN'; return; }
  const resp = await authFetch(API_BASE + '/api/admin/accounts', {
    headers: {'X-Admin-PIN': pin},
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    const detail = body.detail || '';
    if (resp.status === 503) {
      el('adm-pin-warn').textContent = '⚠️ Admin PIN 尚未設定，請查看伺服器啟動 log';
    } else if (resp.status === 423) {
      const localDetail = detail.replace(
        /\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z/,
        s => new Date(s).toLocaleTimeString('zh-TW', {hour:'2-digit', minute:'2-digit'})
      );
      el('adm-pin-warn').textContent = '🔒 ' + (localDetail || '管理員 PIN 已鎖定，請稍後再試');
    } else {
      el('adm-pin-warn').textContent = detail.includes('剩餘') ? '❌ ' + detail : '❌ 管理員 PIN 錯誤';
    }
    el('adm-pin-input').value = '';
    el('adm-pin-input').focus();
    return;
  }
  _admPin = pin;
  el('adm-pin-screen').style.display = 'none';
  el('adm-main').style.display = 'flex';
  admShowTab('list');
  _admLoadSysInfo();
}

async function _admLoadSysInfo() {
  try {
    const r = await fetch(API_BASE + '/api/admin/status');
    if (!r.ok) return;
    const d = await r.json();
    const si = el('adm-sysinfo');
    if (si) {
      si.innerHTML =
        `<span>cmd <b>${document.body.dataset.cmdVersion || '—'}</b></span>` +
        `<span>DB schema <b>v${d.schema_version ?? '—'}</b></span>` +
        `<span>帳號 <b>${d.active_accounts}</b></span>`;
    }
  } catch { /* 靜默失敗 */ }
}

export function admShowTab(tab) {
  const tabs = ['list','add','pi','log','sys'];
  document.querySelectorAll('.adm-tab').forEach((t, i) => {
    t.classList.toggle('active', tabs[i] === tab);
  });
  tabs.forEach(k => { el('adm-panel-' + k).style.display = k === tab ? '' : 'none'; });
  if (tab === 'list') admLoadAccounts();
  if (tab === 'add') admShowAddForm();
  if (tab === 'pi') admLoadPiNodes();
  if (tab === 'log') admLoadLog();
  if (tab === 'sys') admShowSys();
}

export function admShowSys() {
  el('adm-panel-sys').innerHTML = `
    <div style="margin-bottom:24px;">
      <div style="font-size:13px;font-weight:600;margin-bottom:12px;color:var(--text);">🔑 更改 Admin PIN</div>
      <div style="display:flex;flex-direction:column;gap:8px;max-width:320px;">
        <input id="adm-sys-old-pin" class="login-input" type="password" inputmode="numeric"
               maxlength="6" placeholder="目前 Admin PIN">
        <input id="adm-sys-new-pin" class="login-input" type="password" inputmode="numeric"
               maxlength="6" placeholder="新 PIN（4-6 位數字）">
        <input id="adm-sys-new-pin2" class="login-input" type="password" inputmode="numeric"
               maxlength="6" placeholder="確認新 PIN">
        <button class="login-btn" data-action="adm-change-pin" style="margin-top:4px;">更改 Admin PIN</button>
        <div id="adm-sys-warn" style="font-size:12px;color:var(--red);min-height:16px;"></div>
      </div>
    </div>
    <div style="border-top:1px solid var(--border);padding-top:16px;">
      <div style="font-size:13px;font-weight:600;margin-bottom:8px;color:var(--red);">⚠ 重設指揮部資料庫</div>
      <div style="font-size:11px;color:var(--text2);margin-bottom:12px;line-height:1.6;">
        清除所有快照、事件、裁示、Pi 批次資料。<br>
        <b>帳號和 Pi 節點註冊不受影響</b>，Pi 端資料也不受影響。<br>
        <span style="color:var(--red);">此操作無法復原。</span>
      </div>
      <button class="login-btn" data-action="confirmResetDB"
              style="background:var(--red);color:#fff;border:none;max-width:320px;">重設指揮部資料庫</button>
    </div>`;
}

export async function admChangeAdminPin() {
  const oldPin  = el('adm-sys-old-pin').value.trim();
  const newPin  = el('adm-sys-new-pin').value.trim();
  const newPin2 = el('adm-sys-new-pin2').value.trim();
  const warn    = el('adm-sys-warn');
  warn.textContent = '';

  if (!oldPin || !newPin || !newPin2) { warn.textContent = '⚠️ 請填寫所有欄位'; return; }
  if (!/^\d{4,6}$/.test(newPin))     { warn.textContent = '⚠️ 新 PIN 須為 4-6 位數字'; return; }
  if (newPin !== newPin2)             { warn.textContent = '⚠️ 新 PIN 兩次輸入不一致'; return; }

  const resp = await authFetch(API_BASE + '/api/admin/pin', {
    method: 'PUT',
    headers: {'X-Admin-PIN': oldPin, 'Content-Type': 'application/json'},
    body: JSON.stringify({new_pin: newPin}),
  });
  const body = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    const detail = body.detail || '';
    if (resp.status === 423) {
      warn.textContent = '🔒 ' + detail.replace(
        /\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z/,
        s => new Date(s).toLocaleTimeString('zh-TW', {hour:'2-digit', minute:'2-digit'})
      );
    } else {
      warn.textContent = '❌ ' + (detail || '更改失敗，請確認目前 PIN 是否正確');
    }
    return;
  }
  _admPin = newPin;
  el('adm-sys-old-pin').value = '';
  el('adm-sys-new-pin').value = '';
  el('adm-sys-new-pin2').value = '';
  warn.style.color = 'var(--green, #4caf50)';
  warn.textContent = '✅ Admin PIN 已更新';
  setTimeout(() => { warn.textContent = ''; warn.style.color = 'var(--red)'; }, 3000);
}

export async function admLoadAccounts() {
  const resp = await authFetch(API_BASE + '/api/admin/accounts', {headers:{'X-Admin-PIN':_admPin}});
  if (!resp.ok) return;
  const accounts = await resp.json();
  let html = '';
  for (const a of accounts) {
    const statusCls = a.status === 'active' ? 'active' : 'suspended';
    const statusLabel = a.status === 'active' ? '啟用' : '停用';
    html += '<div class="adm-account-card" id="adm-card-' + a.username + '">' +
      '<div class="adm-account-row">' +
        '<div><span class="adm-account-name">' + a.username + '</span>' +
          (a.display_name ? ' <span style="color:var(--text3);font-size:11px;">' + a.display_name + '</span>' : '') +
        '</div>' +
        '<div style="display:flex;gap:4px;">' +
          '<span class="adm-badge role">' + a.role + '</span>' +
          '<span class="adm-badge ' + statusCls + '">' + statusLabel + '</span>' +
        '</div>' +
      '</div>' +
      '<div class="adm-btns">' +
        '<button class="adm-btn" data-action="adm-toggle-edit" data-username="' + a.username + '">編輯</button>' +
        '<button class="adm-btn" data-action="adm-toggle-status" data-username="' + a.username + '" data-status="' + a.status + '">' + (a.status === 'active' ? '停用' : '啟用') + '</button>' +
        '<button class="adm-btn danger" data-action="adm-delete" data-username="' + a.username + '">刪除</button>' +
      '</div>' +
      '<div class="adm-edit-form" id="adm-edit-' + a.username + '" style="display:none;">' +
        '<label>新 PIN（4-6 位數字，留空不改）</label>' +
        '<input id="adm-newpin-' + a.username + '" type="password" inputmode="numeric" maxlength="6" placeholder="新 PIN">' +
        '<label>角色</label>' +
        '<select id="adm-role-' + a.username + '">' +
          '<option value="操作員"' + (a.role==='操作員'?' selected':'') + '>操作員</option>' +
          '<option value="指揮官"' + (a.role==='指揮官'?' selected':'') + '>指揮官</option>' +
        '</select>' +
        '<label>顯示名稱</label>' +
        '<input id="adm-dname-' + a.username + '" value="' + (a.display_name || '') + '">' +
        '<div style="display:flex;gap:6px;">' +
          '<button class="adm-btn" data-action="adm-save-edit" data-username="' + a.username + '">儲存</button>' +
          '<button class="adm-btn" data-action="adm-toggle-edit" data-username="' + a.username + '">取消</button>' +
        '</div>' +
      '</div>' +
    '</div>';
  }
  if (!accounts.length) html = '<div style="color:var(--text3);text-align:center;padding:20px;">無帳號</div>';
  el('adm-panel-list').innerHTML = html;
}

export function admToggleEdit(username) {
  const form = el('adm-edit-' + username);
  if (form) form.style.display = form.style.display === 'none' ? '' : 'none';
}

export async function admSaveEdit(username) {
  const newPin = el('adm-newpin-' + username)?.value.trim();
  const newRole = el('adm-role-' + username)?.value;
  const newDname = el('adm-dname-' + username)?.value.trim();
  const headers = {'X-Admin-PIN': _admPin, 'Content-Type': 'application/json'};
  if (newPin) {
    if (!/^\d{4,6}$/.test(newPin)) { alert('PIN 須為 4-6 位數字'); return; }
    await authFetch(API_BASE + '/api/admin/accounts/' + username + '/pin', {method:'PUT', headers, body:JSON.stringify({new_pin:newPin})});
  }
  if (newRole) await authFetch(API_BASE + '/api/admin/accounts/' + username + '/role?role=' + encodeURIComponent(newRole), {method:'PUT', headers});
  admLoadAccounts();
}

export async function admToggleStatus(username, current) {
  const newStatus = current === 'active' ? 'suspended' : 'active';
  await authFetch(API_BASE + '/api/admin/accounts/' + username + '/status', {
    method:'PUT',
    headers:{'X-Admin-PIN':_admPin,'Content-Type':'application/json'},
    body: JSON.stringify({status: newStatus}),
  });
  admLoadAccounts();
}

export async function admDelete(username) {
  if (!confirm('確定刪除帳號 ' + username + '？')) return;
  await authFetch(API_BASE + '/api/admin/accounts/' + username, {
    method:'DELETE', headers:{'X-Admin-PIN':_admPin},
  });
  admLoadAccounts();
}

export function admShowAddForm() {
  el('adm-panel-add').innerHTML =
    '<div class="adm-add-form">' +
      '<label>帳號</label><input id="adm-add-user" placeholder="帳號">' +
      '<label>PIN（4-6 位數字）</label><input id="adm-add-pin" type="password" inputmode="numeric" maxlength="6" placeholder="PIN">' +
      '<label>角色</label><select id="adm-add-role"><option value="操作員">操作員</option><option value="指揮官">指揮官</option></select>' +
      '<label>顯示名稱（選填）</label><input id="adm-add-dname" placeholder="顯示名稱">' +
      '<button class="adm-add-btn" data-action="adm-add-account">新增帳號</button>' +
      '<div id="adm-add-warn" style="font-size:11px;color:var(--red);min-height:16px;"></div>' +
    '</div>';
}

export async function admAddAccount() {
  const username = el('adm-add-user')?.value.trim();
  const pin = el('adm-add-pin')?.value.trim();
  const role = el('adm-add-role')?.value;
  const displayName = el('adm-add-dname')?.value.trim();
  const warn = el('adm-add-warn');
  warn.textContent = '';
  if (!username) { warn.textContent = '請輸入帳號'; return; }
  if (!/^\d{4,6}$/.test(pin)) { warn.textContent = 'PIN 須為 4-6 位數字'; return; }
  const resp = await authFetch(API_BASE + '/api/admin/accounts', {
    method:'POST',
    headers:{'X-Admin-PIN':_admPin,'Content-Type':'application/json'},
    body: JSON.stringify({username, pin, role, display_name: displayName || null}),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    warn.textContent = err.detail || '新增失敗';
    return;
  }
  admShowTab('list');
}

export async function admLoadLog() {
  const resp = await authFetch(API_BASE + '/api/admin/audit-log?limit=50', {headers:{'X-Admin-PIN':_admPin}});
  if (!resp.ok) return;
  const logs = await resp.json();
  let html = '';
  for (const log of logs) {
    html += '<div class="adm-log-entry">' +
      '<span class="adm-log-time">' + (_fmtLocalDT(log.created_at) || '') + '</span> ' +
      '<span class="adm-log-action">' + (log.action_type || '') + '</span> ' +
      '<span style="color:var(--text2);">' + (log.operator || '') + '</span> ' +
      '<span style="color:var(--text3);font-size:10px;">' + (log.target_table || '') + '/' + (log.target_id || '').slice(0,8) + '</span>' +
    '</div>';
  }
  el('adm-panel-log').innerHTML = html || '<div style="color:var(--text3);text-align:center;padding:20px;">無日誌</div>';
}

// ── Pi 節點管理 ────────────────────────────────────────────────
let _lastCreatedApiKey = null;

export async function admLoadPiNodes() {
  const resp = await authFetch(API_BASE + '/api/admin/pi-nodes', {headers:{'X-Admin-PIN':_admPin}});
  if (!resp.ok) return;
  const nodes = await resp.json();
  let html = '';

  html += `<div style="padding:8px 0;border-bottom:1px solid var(--border);margin-bottom:8px;">
    <div style="font-size:11px;font-weight:700;margin-bottom:6px;">註冊新節點</div>
    <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;">
      <select id="pi-new-unit" style="padding:4px 8px;font-size:11px;background:var(--surface);color:var(--text);border:1px solid var(--border);border-radius:3px;">
        <option value="shelter">shelter（收容組）</option>
        <option value="medical">medical（醫療組）</option>
        <option value="forward">forward（前進組）</option>
        <option value="security">security（安全組）</option>
      </select>
      <input id="pi-new-label" placeholder="顯示名稱" style="padding:4px 8px;font-size:11px;background:var(--surface);color:var(--text);border:1px solid var(--border);border-radius:3px;width:120px;">
      <button data-action="adm-create-pi-node" style="padding:4px 12px;font-size:11px;background:var(--blue);color:#fff;border:none;border-radius:3px;cursor:pointer;">建立</button>
    </div>
  </div>`;

  html += `<div id="pi-key-display" style="display:none;padding:8px;margin-bottom:8px;background:#1a2332;border:1px solid var(--yellow);border-radius:4px;">
    <div style="font-size:10px;color:var(--yellow);font-weight:700;margin-bottom:4px;">⚠ API Key（僅顯示一次，請複製）</div>
    <div id="pi-key-value" style="font-size:10px;font-family:var(--mono);word-break:break-all;color:var(--text);user-select:all;margin-bottom:6px;"></div>
    <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;">
      <button data-action="pi-copy-key" style="padding:3px 10px;font-size:10px;background:var(--surface2);color:var(--text);border:1px solid var(--border);border-radius:3px;cursor:pointer;">複製 Key</button>
      <input id="pi-admin-url" placeholder="Pi Admin URL（如 http://127.0.0.1:8766）" style="padding:3px 6px;font-size:10px;background:var(--surface);color:var(--text);border:1px solid var(--border);border-radius:3px;flex:1;min-width:180px;">
      <button data-action="adm-push-key-to-pi" style="padding:3px 10px;font-size:10px;background:var(--green);color:#000;border:none;border-radius:3px;cursor:pointer;font-weight:600;">推送至 Pi</button>
    </div>
    <div id="pi-push-result" style="font-size:10px;margin-top:4px;min-height:14px;"></div>
  </div>`;

  if (nodes.length === 0) {
    html += '<div style="color:var(--text3);text-align:center;padding:20px;font-size:11px;">尚未註冊任何 Pi 節點</div>';
  }
  for (const n of nodes) {
    let dotColor = 'var(--text3)', dotAnim = '', dotLabel = 'never';
    if (n.last_seen_at) {
      const age = Date.now() - new Date(n.last_seen_at).getTime();
      if (age < 30000)      { dotColor = 'var(--green)';  dotLabel = 'online'; }
      else if (age < 90000) { dotColor = 'var(--yellow)'; dotAnim = 'animation:blink 1s infinite;'; dotLabel = 'degrading'; }
      else                  { dotColor = 'var(--red)';    dotAnim = 'animation:blink .6s infinite;'; dotLabel = 'offline'; }
    }
    const dot = `<span style="color:${dotColor};${dotAnim}" title="${dotLabel}">●</span>`;
    const seen = n.last_seen_at ? _fmtLocalDT(n.last_seen_at) : '從未連線';
    html += `<div style="display:flex;align-items:center;padding:8px 0;border-bottom:1px solid var(--border);gap:8px;">
      <div style="flex:1;">
        <div style="font-size:12px;font-weight:600;">${dot} ${n.label || n.unit_id}</div>
        <div style="font-size:10px;color:var(--text3);">${n.unit_id} · key ...${n.api_key_suffix} · ${seen}</div>
      </div>
      <button data-action="adm-rekey-pi-node" data-unit-id="${n.unit_id}" style="padding:3px 8px;font-size:10px;background:var(--surface2);color:var(--text);border:1px solid var(--border);border-radius:3px;cursor:pointer;">換 Key</button>
      <button data-action="adm-delete-pi-node" data-unit-id="${n.unit_id}" style="padding:3px 8px;font-size:10px;background:var(--surface2);color:var(--red);border:1px solid var(--border);border-radius:3px;cursor:pointer;">刪除</button>
    </div>`;
  }
  el('adm-panel-pi').innerHTML = html;
}

export async function admCreatePiNode() {
  const unit_id = el('pi-new-unit')?.value;
  const label = el('pi-new-label')?.value.trim() || unit_id;
  const resp = await authFetch(API_BASE + '/api/admin/pi-nodes', {
    method:'POST', headers:{'X-Admin-PIN':_admPin,'Content-Type':'application/json'},
    body: JSON.stringify({unit_id, label}),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(()=>({}));
    alert(err.detail || '建立失敗');
    return;
  }
  const result = await resp.json();
  _lastCreatedApiKey = result.api_key;
  admLoadPiNodes().then(() => {
    el('pi-key-display').style.display = '';
    el('pi-key-value').textContent = result.api_key;
    el('pi-push-result').textContent = '';
  });
}

export async function admRekeyPiNode(unitId) {
  if (!confirm(`確定要重新產生 ${unitId} 的 API Key？舊 Key 將立即失效。`)) return;
  const resp = await authFetch(API_BASE + `/api/admin/pi-nodes/${unitId}/rekey`, {
    method:'POST', headers:{'X-Admin-PIN':_admPin},
  });
  if (!resp.ok) { alert('操作失敗'); return; }
  const result = await resp.json();
  _lastCreatedApiKey = result.api_key;
  admLoadPiNodes().then(() => {
    el('pi-key-display').style.display = '';
    el('pi-key-value').textContent = result.api_key;
    el('pi-push-result').textContent = '';
  });
}

export async function admDeletePiNode(unitId) {
  if (!confirm(`確定刪除 ${unitId} 節點？`)) return;
  await authFetch(API_BASE + `/api/admin/pi-nodes/${unitId}`, {
    method:'DELETE', headers:{'X-Admin-PIN':_admPin},
  });
  admLoadPiNodes();
}

export async function admPushKeyToPi() {
  const piUrl = el('pi-admin-url')?.value.trim().replace(/\/$/,'');
  const key = el('pi-key-value')?.textContent;
  const resultEl = el('pi-push-result');
  if (!piUrl) { resultEl.textContent = '請輸入 Pi Admin URL'; resultEl.style.color = 'var(--red)'; return; }
  if (!key) { resultEl.textContent = '無 API Key'; resultEl.style.color = 'var(--red)'; return; }
  resultEl.textContent = '推送中...'; resultEl.style.color = 'var(--text3)';
  try {
    const r1 = await fetch(piUrl + '/admin/command-url', {
      method:'POST', headers:{'X-Admin-PIN':'1234','Content-Type':'application/json'},
      body: JSON.stringify({url: API_BASE}),
    });
    if (!r1.ok) { resultEl.textContent = '設定 command_url 失敗（檢查 Pi Admin PIN）'; resultEl.style.color='var(--red)'; return; }
    const r2 = await fetch(piUrl + '/admin/pi-api-key', {
      method:'POST', headers:{'X-Admin-PIN':'1234','Content-Type':'application/json'},
      body: JSON.stringify({api_key: key}),
    });
    if (!r2.ok) { resultEl.textContent = '設定 api_key 失敗'; resultEl.style.color='var(--red)'; return; }
    resultEl.textContent = '✓ 已推送 command_url + api_key 至 Pi'; resultEl.style.color = 'var(--green)';
  } catch(e) {
    resultEl.textContent = '連線失敗：' + e.message; resultEl.style.color = 'var(--red)';
  }
}

// ── 通用 Modal（由 main.js 注入 handler，auth.js 不 import 業務模組）───────
function openModal(title, body, footer) {
  if (_openModal) _openModal(title, body, footer);
}
function closeModal() {
  if (_closeModal) _closeModal();
}

// ── 鍵盤快捷鍵（Enter 觸發登入 / 解鎖）──────────────────────────
document.addEventListener('keydown', e => {
  if (e.key !== 'Enter') return;
  const ls = el('login-screen');
  if (ls && ls.style.display !== 'none' && document.activeElement &&
      (document.activeElement.id === 'cmd-username' || document.activeElement.id === 'cmd-pin')) {
    handleCmdLogin();
    return;
  }
  const pl = el('pin-lock-overlay');
  if (pl && pl.classList.contains('show') && document.activeElement?.id === 'pinlock-pin') {
    PinLock.unlock();
    return;
  }
  if (document.activeElement?.id === 'adm-pin-input') {
    adminLogin();
  }
});

// ── 認證初始化（供 main.js 呼叫）───────────────────────────────
export async function authInit(options = {}) {
  _onEnterDashboard = options.onEnterDashboard || null;
  const token = sessionStorage.getItem('cmd_session_id');
  if (token) {
    try {
      const resp = await fetch(API_BASE + '/api/auth/heartbeat', {
        headers: {'X-Session-Token': token}
      });
      if (resp.ok) {
        _enterDashboard();
        return 'ok';
      }
    } catch(e) {}
    clearSession();
  }
  el('login-screen').style.display = '';
  return 'need-login';
}
