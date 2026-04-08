#!/usr/bin/env node
/* ════════════════════════════════════════════════════════════════════
   ICS DMAS — ics_ws_server.js v1.0.0
   統一 Pi WebSocket 伺服器（shelter / medical）

   用法：
     node ics_ws_server.js --unit shelter
     node ics_ws_server.js --unit medical

   依賴：
     npm install ws better-sqlite3 express cors

   systemd 啟動範例：
     ExecStart=/usr/bin/node /home/pi/ics_ws_server.js --unit shelter
   ════════════════════════════════════════════════════════════════════ */
'use strict';

/* ─── --unit 參數解析 + 組別配置 ─────────────────────────────────── */
const UNIT_CONFIGS = {
  shelter: {
    wsPort: 8765, adminPort: 8766,
    dbPath: './shelter-pwa/shelter_accounts.db',
    publicDir: './shelter-pwa/public',
    unitId: 'shelter', deviceId: 'shelter_pi',
    logPrefix: 'Shelter',
    pwaHtml: 'shelter_pwa.html',
    roles: ['組長', '一般'],
    defaultRole: '一般',
    roleMigration: "UPDATE accounts SET role='一般' WHERE role IN ('人管','物管','環管')",
    syncTables: ['persons', 'beds', 'resources', 'incidents', 'shifts'],
  },
  medical: {
    wsPort: 8775, adminPort: 8776,
    dbPath: './medical-pwa/medical_accounts.db',
    publicDir: './medical-pwa/public',
    unitId: 'medical', deviceId: 'medical_pi',
    logPrefix: 'Medical',
    pwaHtml: 'medical_pwa.html',
    roles: ['組長', '檢傷官', '治療官', '後送官', '後勤官'],
    defaultRole: '檢傷官',
    roleMigration: null,
    syncTables: ['patients', 'triages', 'incidents', 'shifts'],
  },
};

const unitArg = process.argv.find((a, i) => i > 0 && process.argv[i - 1] === '--unit');
if (!unitArg || !UNIT_CONFIGS[unitArg]) {
  console.error(`用法: node ics_ws_server.js --unit <${Object.keys(UNIT_CONFIGS).join('|')}>`);
  process.exit(1);
}
const cfg = UNIT_CONFIGS[unitArg];

const WebSocket  = require('ws');
const http       = require('http');
const https      = require('https');
const express    = require('express');
const cors       = require('cors');
const crypto     = require('crypto');
const fs         = require('fs');
const path       = require('path');
const Database   = require('better-sqlite3');

/* ─── Log 系統（LOG_LEVEL=error|warn|info|debug，預設 info）────── */
const _LOG_LEVELS = { error:0, warn:1, info:2, debug:3 };
const _logLevel = _LOG_LEVELS[process.env.LOG_LEVEL] ?? _LOG_LEVELS.debug;
const _ts = () => new Date().toISOString().slice(11,23); // HH:MM:SS.mmm
const log = {
  error: (...a) => _logLevel >= 0 && console.error(`[E][${_ts()}]`, ...a),
  warn:  (...a) => _logLevel >= 1 && console.warn (`[W][${_ts()}]`, ...a),
  info:  (...a) => _logLevel >= 2 && console.log  (`[I][${_ts()}]`, ...a),
  debug: (...a) => _logLevel >= 3 && console.log  (`[D][${_ts()}]`, ...a),
};
const SERVER_VERSION = 'v1.1.0';
log.info(`${cfg.logPrefix} WS Server ${SERVER_VERSION} | unit=${unitArg} | Log level: ${process.env.LOG_LEVEL || 'debug'}`);

/* ─── 設定 ────────────────────────────────────────────────────── */
const WS_PORT      = process.env.WS_PORT       || cfg.wsPort;
const ADMIN_PORT   = process.env.ADMIN_PORT    || cfg.adminPort;
const DB_PATH      = process.env.DB_PATH       || path.resolve(cfg.dbPath);
const COMMAND_URL  = process.env.COMMAND_URL   || '';   // 例：https://127.0.0.1:8000
let   _commandUrl  = COMMAND_URL;
const DELTA_LOG_MAX = 1000;

// TLS 憑證（由 CERT_PATH / KEY_PATH 環境變數指定；未設定則退回 HTTP）
const CERT_PATH = process.env.CERT_PATH || '';
const KEY_PATH  = process.env.KEY_PATH  || '';

// 指揮部 HTTPS 呼叫用的 CA 憑證（支援私有 CA，如 mkcert）
// 優先讀 CA_CERT_PATH，其次自動推算 CERT_PATH 同目錄下的 rootCA.pem
const _caCertPath = process.env.CA_CERT_PATH ||
  (CERT_PATH ? path.join(path.dirname(CERT_PATH), 'rootCA.pem') : '');
const CA_CERT = (_caCertPath && fs.existsSync(_caCertPath))
  ? (() => { try { return fs.readFileSync(_caCertPath); } catch { return null; } })()
  : null;
if (CA_CERT) log.info(`[TLS] 指揮部推送 CA=${_caCertPath}`);

function loadTlsOptions() {
  if (!CERT_PATH || !KEY_PATH) return null;
  try {
    return { cert: fs.readFileSync(CERT_PATH), key: fs.readFileSync(KEY_PATH) };
  } catch (e) {
    log.warn(`[TLS] 憑證載入失敗：${e.message}，退回 HTTP`);
    return null;
  }
}
const tlsOpts = loadTlsOptions();
const PROTOCOL = tlsOpts ? 'https' : 'http';
const WS_PROTOCOL = tlsOpts ? 'wss' : 'ws';

/* ─── 指揮部 HTTPS POST 輔助函式 ─────────────────────────────────
   使用 Node.js 內建 https.request（支援自訂 CA 憑證）。
   HTTP 端點則退回 http.request。
── */
function postJSON(urlStr, body, timeoutMs = 8000) {
  return new Promise((resolve, reject) => {
    const url   = new URL(urlStr);
    const data  = JSON.stringify(body);
    const isHttps = url.protocol === 'https:';
    const mod   = isHttps ? require('https') : require('http');
    const opts  = {
      hostname: url.hostname,
      port:     url.port || (isHttps ? 443 : 80),
      path:     url.pathname + url.search,
      method:   'POST',
      headers:  { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(data) },
    };
    if (isHttps && CA_CERT) opts.ca = CA_CERT;
    const req = mod.request(opts, (res) => {
      let buf = '';
      res.on('data', c => buf += c);
      res.on('end', () => resolve({ status: res.statusCode, body: buf }));
    });
    req.setTimeout(timeoutMs, () => { req.destroy(); reject(new Error('timeout')); });
    req.on('error', reject);
    req.write(data);
    req.end();
  });
}

/* ─── 推送快照至指揮部 ───────────────────────────────────────────
   規格 §10.4：將快照 POST 至指揮部 /api/snapshots。
   若 COMMAND_URL 未設定則略過（純本地模式）。
── */
async function pushToCommand(snapshotPayload) {
  const target = _commandUrl || COMMAND_URL;
  if (!target) return;
  try {
    const res = await postJSON(`${target}/api/snapshots`, snapshotPayload);
    if (res.status >= 200 && res.status < 300) {
      log.info(`[Command] Snapshot pushed OK: ${snapshotPayload.snapshot_id}`);
    } else {
      log.warn(`[Command] Push failed ${res.status}: ${res.body}`);
    }
  } catch (err) {
    log.warn(`[Command] Push error: ${err.message}`);
  }
}

/* ─── [DEPRECATED] 舊 snapshot 定時推送（Wave 4 已由 piPush 取代）── */
// autoPushLatestSnapshot / startAutoPush / pushThreePassToCommand
// 已不再使用，保留供參考。

/* ═══════════════════════════════════════════════════════════════
   Wave 4：Pi current_state push（取代舊 snapshot 定時推送）
   每 PI_PUSH_INTERVAL_MS 毫秒讀 current_state → push_queue → POST 指揮部。
   斷線期間 buffer，復線後依序補送。
═══════════════════════════════════════════════════════════════ */
const PI_PUSH_INTERVAL_MS = parseInt(process.env.PI_PUSH_INTERVAL_MS || '') || 60_000;
const MAX_QUEUE_AGE_MS = 24 * 60 * 60 * 1000; // 24hr

function postJSONWithBearer(urlStr, body, bearerToken, timeoutMs = 8000) {
  return new Promise((resolve, reject) => {
    const url   = new URL(urlStr);
    const data  = JSON.stringify(body);
    const isHttps = url.protocol === 'https:';
    const mod   = isHttps ? require('https') : require('http');
    const opts  = {
      hostname: url.hostname,
      port:     url.port || (isHttps ? 443 : 80),
      path:     url.pathname + url.search,
      method:   'POST',
      headers:  {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(data),
        'Authorization': `Bearer ${bearerToken}`,
      },
    };
    if (isHttps && CA_CERT) opts.ca = CA_CERT;
    const req = mod.request(opts, (res) => {
      let buf = '';
      res.on('data', c => buf += c);
      res.on('end', () => resolve({ status: res.statusCode, body: buf }));
    });
    req.setTimeout(timeoutMs, () => { req.destroy(); reject(new Error('timeout')); });
    req.on('error', reject);
    req.write(data);
    req.end();
  });
}

function getPiApiKey() {
  const row = db.prepare("SELECT value FROM config WHERE key='pi_api_key'").get();
  return row ? row.value : null;
}

let _lastPushHash = '';

async function piPushOnce() {
  const target = _commandUrl || COMMAND_URL;
  const apiKey = getPiApiKey();
  if (!target || !apiKey) return;

  // 1. 讀 current_state 全表
  const rows = db.prepare('SELECT table_name, record_id, record_json, updated_at FROM current_state').all();
  if (rows.length === 0) { log.debug('[PiPush] current_state 為空，略過'); return; }

  // 1.5 比對 hash，資料沒變就跳過
  const rawJson = JSON.stringify(rows);
  const hash = crypto.createHash('md5').update(rawJson).digest('hex');
  if (hash === _lastPushHash) {
    log.debug('[PiPush] 資料未變更，略過');
    return;
  }

  const records = rows.map(r => ({
    table_name: r.table_name,
    record_id: r.record_id,
    record: JSON.parse(r.record_json),
    updated_at: r.updated_at,
  }));

  // 2. 寫入 push_queue
  const now = nowISO();
  const info = db.prepare('INSERT INTO push_queue(records_json, pushed_at) VALUES(?,?)').run(JSON.stringify(records), now);
  const queueId = info.lastInsertRowid;

  // 3. POST 至指揮部
  try {
    const res = await postJSONWithBearer(
      `${target}/api/pi-push/${cfg.unitId}`, { records, pushed_at: now }, apiKey
    );
    if (res.status >= 200 && res.status < 300) {
      db.prepare('UPDATE push_queue SET sent=1, sent_at=? WHERE id=?').run(nowISO(), queueId);
      _lastPushHash = hash;
      log.info(`[PiPush] OK: ${records.length} records, queue#${queueId}`);
      // 補送舊的未送出項目
      await replayUnsentQueue(target, apiKey);
    } else {
      log.warn(`[PiPush] Failed ${res.status}: ${res.body}`);
    }
  } catch (err) {
    log.warn(`[PiPush] Error: ${err.message} (queued #${queueId}, will retry)`);
  }

  // 4. 清理過期 queue
  const cutoff = new Date(Date.now() - MAX_QUEUE_AGE_MS).toISOString();
  db.prepare('DELETE FROM push_queue WHERE sent=1 AND pushed_at < ?').run(cutoff);
  db.prepare('DELETE FROM push_queue WHERE pushed_at < ?').run(cutoff);
}

async function replayUnsentQueue(target, apiKey) {
  const unsent = db.prepare('SELECT id, records_json, pushed_at FROM push_queue WHERE sent=0 ORDER BY id ASC LIMIT 50').all();
  if (unsent.length <= 1) return; // 只有剛才那筆（已處理過），略過
  // 跳過第一筆（最新的，剛剛已送）
  for (const row of unsent.slice(0, -1)) {
    try {
      const records = JSON.parse(row.records_json);
      const res = await postJSONWithBearer(
        `${target}/api/pi-push/${cfg.unitId}`, { records, pushed_at: row.pushed_at }, apiKey
      );
      if (res.status >= 200 && res.status < 300) {
        db.prepare('UPDATE push_queue SET sent=1, sent_at=? WHERE id=?').run(nowISO(), row.id);
        log.info(`[PiPush] Replayed queue#${row.id} OK`);
      } else {
        log.warn(`[PiPush] Replay queue#${row.id} failed: ${res.status}`);
        break;
      }
    } catch (err) {
      log.warn(`[PiPush] Replay error: ${err.message}`);
      break;
    }
  }
}

let _piPushStarted = false;
function startPiPush() {
  if (_piPushStarted) return;
  const target = _commandUrl || COMMAND_URL;
  const apiKey = getPiApiKey();
  if (!target || !apiKey) {
    log.info('[PiPush] 未設定 command_url 或 pi_api_key，跳過定時推送');
    return;
  }
  _piPushStarted = true;
  setTimeout(() => piPushOnce(), 5_000);
  setInterval(() => piPushOnce(), PI_PUSH_INTERVAL_MS);
  log.info(`[PiPush] 定時推送 current_state 至指揮部，間隔 ${PI_PUSH_INTERVAL_MS / 1000}s`);
}

/* ─── SQLite 初始化 ──────────────────────────────────────────── */
const db = new Database(DB_PATH);

db.exec(`
  PRAGMA journal_mode=WAL;

  CREATE TABLE IF NOT EXISTS config (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
  );

  CREATE TABLE IF NOT EXISTS accounts (
    id          TEXT PRIMARY KEY,
    username    TEXT UNIQUE NOT NULL,
    role        TEXT NOT NULL,
    pin_hash    TEXT NOT NULL,
    pin_salt    TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'active',
    created_at  TEXT NOT NULL,
    created_by  TEXT NOT NULL DEFAULT 'system',
    last_login  TEXT,
    device_id   TEXT
  );

  -- 角色遷移（僅 shelter 需要）

  CREATE TABLE IF NOT EXISTS audit_log (
    id            TEXT PRIMARY KEY,
    action        TEXT NOT NULL,
    operator_name TEXT NOT NULL,
    device_id     TEXT,
    session_id    TEXT,
    timestamp     TEXT NOT NULL,
    detail        TEXT
  );

  CREATE TABLE IF NOT EXISTS delta_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    src        TEXT,
    table_name TEXT,
    record_id  TEXT,
    record_json TEXT,
    ts         TEXT,
    recv_at    TEXT NOT NULL
  );

  CREATE TABLE IF NOT EXISTS login_failures (
    username   TEXT NOT NULL,
    failed_at  TEXT NOT NULL
  );
  CREATE INDEX IF NOT EXISTS idx_login_failures_username ON login_failures(username);

  -- v2.1: SNAPSHOT 表（供三 Pass 對齊用）
  CREATE TABLE IF NOT EXISTS snapshots (
    snapshot_uuid  TEXT PRIMARY KEY,
    unit_id        TEXT NOT NULL DEFAULT '${cfg.unitId}',
    source         TEXT NOT NULL DEFAULT 'pi_push',
    payload_json   TEXT NOT NULL,
    recv_at        TEXT NOT NULL,
    merged         INTEGER NOT NULL DEFAULT 0
  );

  -- Wave 4：current_state 即時狀態鏡像
  CREATE TABLE IF NOT EXISTS current_state (
    table_name  TEXT NOT NULL,
    record_id   TEXT NOT NULL,
    record_json TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    PRIMARY KEY (table_name, record_id)
  );

  -- Wave 4：推送佇列
  CREATE TABLE IF NOT EXISTS push_queue (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    records_json TEXT NOT NULL,
    pushed_at    TEXT NOT NULL,
    sent         INTEGER NOT NULL DEFAULT 0,
    sent_at      TEXT
  );
`);

// 角色遷移（依組別條件執行）
if (cfg.roleMigration) db.exec(cfg.roleMigration);

/* ─── v2.1：確保 config.last_sync_to_command 存在 ──────────────
   指揮部規格 §14.2：各組 Pi 記錄最後成功推送至指揮部的時間戳，
   供三 Pass 同步計算起始時間點。
   若無記錄則初始化為 epoch（代表需全量同步）。
─────────────────────────────────────────────────────────────── */
(function initConfig() {
  const row = db.prepare("SELECT value FROM config WHERE key='last_sync_to_command'").get();
  if (!row) {
    db.prepare("INSERT INTO config(key,value) VALUES('last_sync_to_command','1970-01-01T00:00:00.000Z')").run();
    log.debug('[Config] Initialized last_sync_to_command = epoch (full sync on first connect)');
  }
  // site_salt：本站加密金鑰衍生用鹽值，Pi 啟動時一次性產生，永久保存
  // 規格 §5.4：所有裝置以 PBKDF2(site_pin, site_salt) 衍生相同金鑰，確保跨裝置加密互通
  const saltRow = db.prepare("SELECT value FROM config WHERE key='site_salt'").get();
  if (!saltRow) {
    const newSalt = crypto.randomBytes(16).toString('hex');
    db.prepare("INSERT INTO config(key,value) VALUES('site_salt',?)").run(newSalt);
    log.info(`[Config] Generated new site_salt (first startup)`);
  } else {
    log.debug('[Config] site_salt loaded from DB');
  }
  // 從 DB 讀取持久化的 command_url（若環境變數未設定）
  if (!COMMAND_URL) {
    const urlRow = db.prepare("SELECT value FROM config WHERE key='command_url'").get();
    if (urlRow) {
      _commandUrl = urlRow.value;
      log.debug(`[Config] Loaded command_url from DB: ${_commandUrl}`);
    }
  }
})();

/* ─── PBKDF2 雜湊 ─────────────────────────────────────────────── */
function hashPin(pin, saltHex) {
  return new Promise((resolve, reject) => {
    const salt = Buffer.from(saltHex, 'hex');
    crypto.pbkdf2(pin, salt, 200000, 32, 'sha256', (err, key) => {
      if (err) reject(err);
      else resolve(key.toString('hex'));
    });
  });
}

function randomHex(bytes = 16) { return crypto.randomBytes(bytes).toString('hex'); }
function nowISO() { return new Date().toISOString(); }
function newUUID() { return crypto.randomUUID ? crypto.randomUUID() : randomHex(16); }

/* ─── 管理員 PIN ─────────────────────────────────────────────── */
function getAdminPinHash() {
  const row = db.prepare('SELECT value FROM config WHERE key=?').get('admin_pin_hash');
  return row ? row.value : null;
}
function getAdminPinSalt() {
  const row = db.prepare('SELECT value FROM config WHERE key=?').get('admin_pin_salt');
  return row ? row.value : null;
}

/* ─── last_sync_to_command 讀寫 ──────────────────────────────────
   供 sync_push 處理器與 catchup 使用。
─────────────────────────────────────────────────────────────── */
function getLastSyncToCommand() {
  const row = db.prepare("SELECT value FROM config WHERE key='last_sync_to_command'").get();
  return row ? row.value : '1970-01-01T00:00:00.000Z';
}

function updateLastSyncToCommand(isoTs) {
  db.prepare("INSERT OR REPLACE INTO config(key,value) VALUES('last_sync_to_command',?)").run(isoTs);
}

/* ─── site_salt 讀取 ──────────────────────────────────────────────
   回傳本站加密鹽值（auth_result 附帶給裝置做金鑰衍生）。
   正常情況下 initConfig() 已確保存在，此處加 fallback 防止意外。
─────────────────────────────────────────────────────────────── */
function getSiteSalt() {
  const row = db.prepare("SELECT value FROM config WHERE key='site_salt'").get();
  if (row) return row.value;
  // fallback：不應執行到此，但保險起見重新產生
  log.warn('[Config] site_salt missing from DB, regenerating (check initConfig)');
  const newSalt = crypto.randomBytes(16).toString('hex');
  db.prepare("INSERT OR REPLACE INTO config(key,value) VALUES('site_salt',?)").run(newSalt);
  return newSalt;
}

/* ─── Delta 日誌 ─────────────────────────────────────────────── */
const deltaLog = [];

function appendDelta(msg) {
  deltaLog.unshift({ ...msg, recv_at: nowISO() });
  if (deltaLog.length > DELTA_LOG_MAX) deltaLog.length = DELTA_LOG_MAX;
  try {
    db.prepare(`INSERT INTO delta_log(src,table_name,record_id,record_json,ts,recv_at)
                VALUES(?,?,?,?,?,?)`)
      .run(
        msg.src || '',
        msg.table || '',
        msg.record?._id ? String(msg.record._id) : '',
        JSON.stringify(msg.record || {}),
        msg.ts || '',
        nowISO()
      );
    db.prepare(`DELETE FROM delta_log WHERE id NOT IN (
      SELECT id FROM delta_log ORDER BY id DESC LIMIT ?
    )`).run(DELTA_LOG_MAX);
  } catch(e) { /* non-critical */ }

  // Wave 4：UPSERT current_state（維持各 record 最新版本）
  const _tbl = msg.table || '';
  const _rid = msg.record?._id ? String(msg.record._id) : '';
  if (_tbl && _rid) {
    try {
      db.prepare(`INSERT INTO current_state(table_name, record_id, record_json, updated_at)
                  VALUES(?,?,?,?)
                  ON CONFLICT(table_name, record_id) DO UPDATE SET
                    record_json=excluded.record_json, updated_at=excluded.updated_at`)
        .run(_tbl, _rid, JSON.stringify(msg.record || {}), nowISO());
    } catch(e) { log.warn('[current_state] UPSERT error:', e.message); }
  }
}

function getRecentDeltas(sinceISO) {
  try {
    const rows = db.prepare(
      `SELECT src, table_name as "table", record_json, ts FROM delta_log
       WHERE ts >= ? ORDER BY id ASC LIMIT ?`
    ).all(sinceISO || '1970-01-01T00:00:00.000Z', DELTA_LOG_MAX);
    return rows.map(r => ({
      src: r.src, table: r.table,
      record: JSON.parse(r.record_json || '{}'),
      ts: r.ts, action: 'upsert',
    }));
  } catch(e) { return []; }
}

/* ════════════════════════════════════════════════════════════════
   WebSocket 伺服器（支援 WSS/WS）
════════════════════════════════════════════════════════════════ */
const wsRawServer = tlsOpts
  ? https.createServer(tlsOpts)
  : http.createServer();
const wss = new WebSocket.Server({ server: wsRawServer, perMessageDeflate: false });

wsRawServer.on('upgrade', (req, socket, _head) => {
  const ip = socket.remoteAddress;
  const urlSrc = new URL(req.url, 'wss://localhost').searchParams.get('src') || '?';
  log.debug(`[WS] HTTP Upgrade received from ${ip} src=${urlSrc}`);
});

wsRawServer.listen(WS_PORT, () => {
  log.info(`[WS] ${WS_PROTOCOL.toUpperCase()} Server listening on port ${WS_PORT}`);
});
const clients = new Map();

wss.on('connection', (ws, req) => {
  const ip = req.socket.remoteAddress;
  const urlSrc = new URL(req.url, 'wss://localhost').searchParams.get('src') || '?';
  log.info(`[WS] Client connected from ${ip} src=${urlSrc}`);

  ws.isAlive = true;
  ws.on('pong', () => { ws.isAlive = true; });

  let _zombieTimer = setTimeout(() => {
    log.warn(`[WS] No message in 5s from ${ip} src=${urlSrc} → zombie suspected`);
  }, 5000);

  ws.on('message', async (raw) => {
    if (_zombieTimer) { clearTimeout(_zombieTimer); _zombieTimer = null; }
    let msg;
    try { msg = JSON.parse(raw); } catch { return; }

    switch (msg.type) {

      /* ── 驗證登入 ── */
      case 'auth': {
        const { username, pin, device_id } = msg;
        if (!username || !pin) {
          ws.send(JSON.stringify({ type: 'auth_result', ok: false, reason: '帳號或 PIN 為空' }));
          return;
        }
        if (isLoginLocked(username)) {
          ws.send(JSON.stringify({ type: 'auth_result', ok: false, reason: '連續錯誤超過 5 次，鎖定 30 分鐘，請稍後再試' }));
          return;
        }
        const account = db.prepare('SELECT * FROM accounts WHERE username=? AND status=?')
          .get(username, 'active');
        if (!account) {
          writeAuditLog('login_failed', username, device_id || '', null, { reason: '帳號不存在或已停用' });
          ws.send(JSON.stringify({ type: 'auth_result', ok: false, reason: '帳號不存在或已停用' }));
          return;
        }
        const hash = await hashPin(pin, account.pin_salt);
        if (hash !== account.pin_hash) {
          const locked = checkLoginLock(username);
          writeAuditLog('login_failed', username, device_id || '', null, { reason: 'PIN 錯誤', now_locked: locked });
          if (locked) {
            ws.send(JSON.stringify({ type: 'auth_result', ok: false, reason: '連續錯誤超過 5 次，鎖定 30 分鐘，請稍後再試' }));
          } else {
            ws.send(JSON.stringify({ type: 'auth_result', ok: false, reason: 'PIN 錯誤' }));
          }
          return;
        }
        db.prepare('DELETE FROM login_failures WHERE username=?').run(username);
        db.prepare('UPDATE accounts SET last_login=?, device_id=? WHERE username=?')
          .run(nowISO(), device_id || null, username);
        clients.set(ws, { deviceId: device_id || ip, username, role: account.role, connectedAt: nowISO() });
        writeAuditLog('login_success', username, device_id || '', null, { role: account.role });
        ws.send(JSON.stringify({
          type: 'auth_result',
          ok: true, username, role: account.role,
          pi_time: nowISO(),
          last_sync_to_command: getLastSyncToCommand(),  // v2.1: 回傳讓前端知道上次同步時間
          site_salt: getSiteSalt(),                      // v2.2: 本站加密鹽值，裝置用於衍生 AES-GCM 金鑰
        }));
        log.info(`[WS] Auth OK: ${username} (${account.role}) from ${ip}`);
        break;
      }

      /* ── Delta 廣播（L2 同步） ── */
      case 'delta': {
        appendDelta(msg);
        const src = msg.src || clients.get(ws)?.deviceId;
        wss.clients.forEach(client => {
          if (client !== ws && client.readyState === WebSocket.OPEN) {
            client.send(JSON.stringify({ ...msg, _relayed_by_pi: true }));
          }
        });
        break;
      }

      /* ── debug_ping（診斷用，記錄 connect() 呼叫來源） ── */
      case 'debug_ping': {
        log.info(`[WS] debug_ping from ${ip} source=${msg.source||'?'} device=${msg.device_id||'?'}`);
        break;
      }

      /* ── session_restore（刷新頁面後透明還原身份，不重新驗 PIN） ── */
      case 'session_restore': {
        const { username, role: rawRole, device_id } = msg;
        const role = cfg.roles.includes(rawRole) ? rawRole : cfg.defaultRole;
        if (username && role) {
          const existing = clients.get(ws);
          clients.set(ws, { deviceId: device_id || ip, username, role, connectedAt: existing?.connectedAt || nowISO() });
          log.info(`[WS] Session restored: ${username} (${role}) device=${device_id||'?'}`);
        }
        break;
      }

      /* ── Catchup 請求（新裝置連線補傳） ── */
      case 'catchup_req': {
        const since = msg.since || '1970-01-01T00:00:00.000Z';
        const deltas = getRecentDeltas(since);
        ws.send(JSON.stringify({ type: 'catchup_resp', deltas, pi_time: nowISO() }));
        log.info(`[WS] Catchup: sent ${deltas.length} deltas since ${since}`);
        break;
      }

      /* ── v2.1: sync_push（網路恢復後，各組推送完整記錄至 Pi）
         §10.4：Pi 收到推送後：
         1. 將記錄寫入 delta_log（供其他裝置 catchup）
         2. 廣播至所有已連線裝置
         3. 更新 last_sync_to_command
         4. 回傳 sync_ack（含 Pass 1 SNAPSHOT 合併結果摘要）
      ── */
      case 'sync_push': {
        const { sync_start_ts, tables, snapshots: pushSnapshots, device_id: pushDeviceId } = msg;
        let recordsApplied = 0;
        let snapshotsMerged = 0;

        // 將各 table 的記錄寫入 delta_log 並廣播
        const SYNC_TABLES = cfg.syncTables;
        for (const table of SYNC_TABLES) {
          const records = tables?.[table] || [];
          for (const record of records) {
            if (!record || !record._id) continue;
            const delta = {
              src: pushDeviceId || `${cfg.unitId}_push`,
              table,
              action: 'upsert',
              record,
              ts: record.updated_at || record.timestamp || nowISO(),
            };
            appendDelta(delta);
            // 廣播給其他已連線裝置
            wss.clients.forEach(client => {
              if (client !== ws && client.readyState === WebSocket.OPEN) {
                client.send(JSON.stringify({ ...delta, _relayed_by_pi: true, type: 'delta' }));
              }
            });
            recordsApplied++;
          }
        }

        // Pass 1：SNAPSHOT 去重與合併
        // 若推送包含 snapshots（含 snapshot_uuid），嘗試合併至本機 snapshots 表
        const passOneResults = [];
        if (Array.isArray(pushSnapshots)) {
          for (const snap of pushSnapshots) {
            if (!snap.snapshot_uuid) continue;
            const existing = db.prepare("SELECT snapshot_uuid FROM snapshots WHERE snapshot_uuid=?")
              .get(snap.snapshot_uuid);
            if (existing) {
              // 已有 QR 掃描版本 → 以完整記錄覆蓋，標記 source=merged_from_qr
              db.prepare(`UPDATE snapshots SET source='merged_from_qr', payload_json=?, merged=1
                          WHERE snapshot_uuid=?`)
                .run(JSON.stringify(snap), snap.snapshot_uuid);
              passOneResults.push({ uuid: snap.snapshot_uuid, action: 'merged_over_qr' });
            } else {
              // 新快照：直接寫入
              db.prepare(`INSERT OR IGNORE INTO snapshots(snapshot_uuid,unit_id,source,payload_json,recv_at,merged)
                          VALUES(?,?,?,?,?,0)`)
                .run(snap.snapshot_uuid, snap.unit_id || cfg.unitId, 'pi_push',
                    JSON.stringify(snap), nowISO());
              passOneResults.push({ uuid: snap.snapshot_uuid, action: 'inserted' });
            }
            snapshotsMerged++;
          }
        }

        // 更新 last_sync_to_command（§10.3）
        const newSyncTs = nowISO();
        updateLastSyncToCommand(newSyncTs);
        writeAuditLog('network_recovery_push', clients.get(ws)?.username || 'unknown',
          pushDeviceId || '', null,
          { sync_start_ts, records_sent: recordsApplied, snapshots_merged: snapshotsMerged, triggered_by: 'ws_reconnect' }
        );

        // 回傳 sync_ack
        ws.send(JSON.stringify({
          type: 'sync_ack',
          ok: true,
          pi_time: newSyncTs,
          last_sync_to_command: newSyncTs,
          records_applied: recordsApplied,
          snapshots_merged: snapshotsMerged,
          pass1_results: passOneResults,
        }));
        log.info(`[WS] sync_push: applied ${recordsApplied} records, merged ${snapshotsMerged} snapshots`);

        // Wave 4：sync_push 後立即觸發一次 piPush（加速資料同步至指揮部）
        piPushOnce().catch(err =>
          log.warn('[PiPush] sync_push trigger error:', err.message)
        );
        break;
      }

      /* ── 時間同步 ── */
      case 'time_sync_req': {
        ws.send(JSON.stringify({ type: 'time_sync_resp', pi_time: nowISO(), device_id: msg.device_id }));
        break;
      }

      /* ── 稽核日誌（從前端上傳高風險操作記錄） ── */
      case 'audit_event': {
        try {
          writeAuditLog(
            msg.action || 'unknown',
            msg.operator_name || '未知',
            msg.device_id || '',
            msg.session_id || null,
            msg.detail || {}
          );
        } catch(e) { /* non-critical */ }
        break;
      }

      /* ── Ping ── */
      case 'ping': {
        ws.send(JSON.stringify({ type: 'pong', pi_time: nowISO() }));
        break;
      }
    }
  });

  ws.on('close', (code, reason) => {
    if (_zombieTimer) { clearTimeout(_zombieTimer); _zombieTimer = null; }
    const info = clients.get(ws);
    const who = info ? info.username : '(未驗證)';
    log.info(`[WS] Disconnected: ${who} code=${code} reason=${reason||''}`);
    clients.delete(ws);
  });

  ws.on("error", err => log.warn('[WS] Error:', err.message));

  ws.send(JSON.stringify({
    type: 'welcome',
    pi_time: nowISO(),
    server_version: '2.1',
    last_sync_to_command: getLastSyncToCommand(),
  }));
});

wss.on("error", err => log.error('[WS Server Error]', err));

/* ─── 伺服器端 Ping（維持 iOS Safari WebSocket 連線）──────────
   iOS Safari 在背景或節能模式下會關閉閒置 WebSocket。
   每 25 秒由伺服器主動 ping，瀏覽器自動回 pong，
   讓系統認為連線有活動，避免被關閉。
─────────────────────────────────────────────────────────── */
setInterval(() => {
  wss.clients.forEach(ws => {
    if (ws.readyState !== ws.OPEN) return;
    if (ws.isAlive === false) {
      log.warn(`[WS] No pong received, terminating ${clients.get(ws)?.username || '(未驗證)'}`);
      ws.terminate();
      return;
    }
    ws.isAlive = false;
    ws.ping();
  });
}, 25_000);

/* ─── 稽核日誌寫入 ─────────────────────────────────────────── */
function writeAuditLog(action, operator, deviceId, sessionId, detail) {
  db.prepare(`INSERT INTO audit_log(id,action,operator_name,device_id,session_id,timestamp,detail)
              VALUES(?,?,?,?,?,?,?)`)
    .run(newUUID(), action, operator, deviceId || null, sessionId || null, nowISO(), JSON.stringify(detail || {}));
}

/* ─── 登入失敗鎖定 ─────────────────────────────────────────── */
function checkLoginLock(username) {
  const WINDOW_MS = 30 * 60 * 1000;
  const MAX_FAIL  = 5;
  const now       = Date.now();
  const windowISO = new Date(now - WINDOW_MS).toISOString();
  db.prepare(`DELETE FROM login_failures WHERE username=? AND failed_at < ?`).run(username, windowISO);
  db.prepare(`INSERT INTO login_failures(username, failed_at) VALUES(?,?)`).run(username, new Date(now).toISOString());
  const count = db.prepare(
    `SELECT COUNT(*) as cnt FROM login_failures WHERE username=? AND failed_at >= ?`
  ).get(username, windowISO).cnt;
  return count >= MAX_FAIL;
}

function isLoginLocked(username) {
  const WINDOW_MS = 30 * 60 * 1000;
  const MAX_FAIL  = 5;
  const windowISO = new Date(Date.now() - WINDOW_MS).toISOString();
  const count = db.prepare(
    `SELECT COUNT(*) as cnt FROM login_failures WHERE username=? AND failed_at >= ?`
  ).get(username, windowISO).cnt;
  return count >= MAX_FAIL;
}

/* ════════════════════════════════════════════════════════════════
   HTTP Admin API
════════════════════════════════════════════════════════════════ */
const app = express();
app.use(cors({ origin: '*' }));
app.use(express.json());

// 提供 public/ 下的靜態檔案（PWA HTML、sw.js、manifest.json、lib/）
const PUBLIC_DIR = process.env.PUBLIC_DIR || path.resolve(cfg.publicDir);
if (fs.existsSync(PUBLIC_DIR)) {
  app.use(express.static(PUBLIC_DIR));
  log.info(`[Static] 提供 PWA 靜態檔案：${PUBLIC_DIR}`);
}

app.get('/', (req, res) => {
  const pwaPath = path.join(PUBLIC_DIR, cfg.pwaHtml);
  if (fs.existsSync(pwaPath)) {
    res.sendFile(pwaPath);
    return;
  }
  const adminPath = path.join(__dirname, 'admin_v2.0.html');
  if (fs.existsSync(adminPath)) {
    res.sendFile(adminPath);
  } else {
    res.send('<h1>admin_v2.0.html 未找到</h1>');
  }
});

async function adminAuth(req, res, next) {
  const pin = req.headers['x-admin-pin'] || req.body?.admin_pin;
  const adminHash = getAdminPinHash();
  const adminSalt = getAdminPinSalt();
  if (!adminHash) {
    if (req.path === '/admin/setup') return next();
    return res.status(403).json({ ok: false, reason: '管理員 PIN 尚未設定' });
  }
  if (!pin) return res.status(401).json({ ok: false, reason: '缺少管理員 PIN' });
  try {
    const hash = await hashPin(pin, adminSalt);
    if (hash !== adminHash) return res.status(403).json({ ok: false, reason: '管理員 PIN 錯誤' });
    next();
  } catch(e) { res.status(500).json({ ok: false, reason: '驗證錯誤' }); }
}

app.post('/admin/setup', async (req, res) => {
  if (getAdminPinHash()) return res.status(400).json({ ok: false, reason: '管理員 PIN 已設定' });
  const { admin_pin } = req.body;
  if (!admin_pin || admin_pin.length < 4 || !/^\d+$/.test(admin_pin))
    return res.status(400).json({ ok: false, reason: 'PIN 格式不符（4-8 位數字）' });
  const salt = randomHex(16);
  const hash = await hashPin(admin_pin, salt);
  db.prepare("INSERT OR REPLACE INTO config(key,value) VALUES('admin_pin_hash',?)").run(hash);
  db.prepare("INSERT OR REPLACE INTO config(key,value) VALUES('admin_pin_salt',?)").run(salt);
  writeAuditLog('admin_pin_setup', 'system', '', null, {});
  res.json({ ok: true, message: '管理員 PIN 設定成功' });
});

app.get('/admin/accounts', adminAuth, (req, res) => {
  const accounts = db.prepare(
    'SELECT id,username,role,status,created_at,created_by,last_login,device_id FROM accounts ORDER BY created_at'
  ).all();
  res.json({ ok: true, accounts });
});

app.post('/admin/accounts', adminAuth, async (req, res) => {
  const { username, role, pin, created_by } = req.body;
  if (!username || !role || !pin) return res.status(400).json({ ok: false, reason: '缺少必填欄位' });
  if (!cfg.roles.includes(role)) return res.status(400).json({ ok: false, reason: '角色不在允許清單' });
  if (!/^\d{4,6}$/.test(pin)) return res.status(400).json({ ok: false, reason: 'PIN 格式不符' });
  const existing = db.prepare('SELECT id FROM accounts WHERE username=?').get(username);
  if (existing) return res.status(400).json({ ok: false, reason: '帳號名稱已存在' });
  const salt = randomHex(16); const hash = await hashPin(pin, salt); const id = newUUID();
  db.prepare(`INSERT INTO accounts(id,username,role,pin_hash,pin_salt,status,created_at,created_by) VALUES(?,?,?,?,?,?,?,?)`)
    .run(id, username, role, hash, salt, 'active', nowISO(), created_by || 'admin');
  writeAuditLog('account_created', created_by || 'admin', '', null, { target: username, role });
  res.json({ ok: true, id, username, role });
});

app.put('/admin/accounts/:username/status', adminAuth, (req, res) => {
  const { username } = req.params;
  const { status, updated_by } = req.body;
  if (!['active','suspended'].includes(status)) return res.status(400).json({ ok: false, reason: 'status 格式不符' });
  const account = db.prepare('SELECT id FROM accounts WHERE username=?').get(username);
  if (!account) return res.status(404).json({ ok: false, reason: '帳號不存在' });
  db.prepare('UPDATE accounts SET status=? WHERE username=?').run(status, username);
  writeAuditLog('account_status_changed', updated_by || 'admin', '', null, { target: username, new_status: status });
  res.json({ ok: true, username, status });
});

app.put('/admin/accounts/:username/pin', adminAuth, async (req, res) => {
  const { username } = req.params;
  const { new_pin, updated_by } = req.body;
  if (!new_pin || !/^\d{4,6}$/.test(new_pin)) return res.status(400).json({ ok: false, reason: 'PIN 格式不符' });
  const account = db.prepare('SELECT id FROM accounts WHERE username=?').get(username);
  if (!account) return res.status(404).json({ ok: false, reason: '帳號不存在' });
  const salt = randomHex(16); const hash = await hashPin(new_pin, salt);
  db.prepare('UPDATE accounts SET pin_hash=?, pin_salt=? WHERE username=?').run(hash, salt, username);
  writeAuditLog('pin_reset', updated_by || 'admin', '', null, { target: username });
  res.json({ ok: true, username, message: 'PIN 已重設' });
});

app.delete('/admin/accounts/:username', adminAuth, (req, res) => {
  const { username } = req.params;
  const { deleted_by } = req.body || {};
  const account = db.prepare('SELECT id FROM accounts WHERE username=?').get(username);
  if (!account) return res.status(404).json({ ok: false, reason: '帳號不存在' });
  db.prepare('DELETE FROM accounts WHERE username=?').run(username);
  writeAuditLog('account_deleted', deleted_by || 'admin', '', null, { target: username });
  res.json({ ok: true, username });
});

app.put('/admin/accounts/:username/role', adminAuth, (req, res) => {
  const { username } = req.params;
  const { role, updated_by } = req.body || {};
  if (!cfg.roles.includes(role)) return res.status(400).json({ ok: false, reason: '角色不在允許清單' });
  const account = db.prepare('SELECT id FROM accounts WHERE username=?').get(username);
  if (!account) return res.status(404).json({ ok: false, reason: '帳號不存在' });
  db.prepare('UPDATE accounts SET role=? WHERE username=?').run(role, username);
  writeAuditLog('account_role_changed', updated_by || 'admin', '', null, { target: username, new_role: role });
  res.json({ ok: true, username, role });
});

app.post('/admin/accounts/suspend-all', adminAuth, (req, res) => {
  const { suspended_by } = req.body;
  const result = db.prepare("UPDATE accounts SET status='suspended'").run();
  writeAuditLog('all_accounts_suspended', suspended_by || 'admin', '', null, { count: result.changes });
  res.json({ ok: true, suspended_count: result.changes });
});

app.get('/admin/audit-log', adminAuth, (req, res) => {
  const limit  = parseInt(req.query.limit || '100');
  const offset = parseInt(req.query.offset || '0');
  const rows = db.prepare('SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ? OFFSET ?').all(limit, offset);
  const total = db.prepare('SELECT COUNT(*) as cnt FROM audit_log').get().cnt;
  res.json({ ok: true, logs: rows, total, limit, offset });
});

/* ── v2.1: last_sync_to_command 查詢端點（供指揮部 Pi 使用） ── */
app.get('/admin/sync-status', adminAuth, (req, res) => {
  res.json({
    ok: true,
    last_sync_to_command: getLastSyncToCommand(),
    pi_time: nowISO(),
    connected_clients: clients.size,
  });
});

app.get('/admin/status', (req, res) => {
  const accountCount = db.prepare("SELECT COUNT(*) as cnt FROM accounts WHERE status='active'").get().cnt;
  const deltaCount   = db.prepare("SELECT COUNT(*) as cnt FROM delta_log").get().cnt;
  res.json({
    ok: true,
    server_version: '2.1',
    pi_time: nowISO(),
    active_accounts: accountCount,
    delta_log_count: deltaCount,
    connected_clients: clients.size,
    admin_pin_setup: !!getAdminPinHash(),
    last_sync_to_command: getLastSyncToCommand(),
    command_url: COMMAND_URL || null,
  });
});

/* ─── CA 根憑證下載（供手機/平板安裝）─────────────────────────── */

app.get('/cert', (req, res) => {
  const caPath = path.resolve(__dirname, 'certs', 'rootCA.pem');
  if (!fs.existsSync(caPath)) {
    return res.status(404).send('rootCA.pem 未找到。請先將憑證部署到 certs/ 目錄。');
  }
  res.download(caPath, 'rootCA.pem');
});

app.get('/cert/install', (req, res) => {
  const host = req.headers.host || 'this-server';
  res.send(`<!DOCTYPE html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>安裝 CA 憑證</title>
<style>
  body{font-family:-apple-system,sans-serif;max-width:600px;margin:40px auto;padding:0 20px;line-height:1.6}
  h1{font-size:1.4em}
  .btn{display:inline-block;padding:14px 28px;background:#c0392b;color:#fff;text-decoration:none;border-radius:8px;font-size:1.1em;margin:20px 0}
  .step{background:#f5f5f5;padding:12px 16px;margin:8px 0;border-radius:6px}
  .num{font-weight:bold;color:#c0392b}
</style></head><body>
<h1>ICS_DMAS CA 憑證安裝</h1>
<p>安裝此憑證後，裝置才能信任本系統的 HTTPS/WSS 連線。</p>
<a class="btn" href="/cert">下載 CA 憑證</a>
<h2>iOS 安裝步驟</h2>
<div class="step"><span class="num">1.</span> 點擊上方按鈕下載</div>
<div class="step"><span class="num">2.</span> 設定 → 已下載描述檔 → 安裝</div>
<div class="step"><span class="num">3.</span> 設定 → 一般 → 關於本機 → 憑證信任設定 → 開啟信任</div>
<h2>Android 安裝步驟</h2>
<div class="step"><span class="num">1.</span> 點擊上方按鈕下載</div>
<div class="step"><span class="num">2.</span> 設定 → 安全性 → 加密與憑證 → 安裝憑證 → CA 憑證</div>
<div class="step"><span class="num">3.</span> 選擇下載的 rootCA.pem</div>
</body></html>`);
});

/* ─── 設定指揮部 URL（§10.4）───────────────────────────────────── */

app.get('/admin/command-url', adminAuth, (req, res) => {
  res.json({ ok: true, command_url: _commandUrl || null });
});

app.post('/admin/command-url', adminAuth, async (req, res) => {
  const { url } = req.body || {};
  if (!url || !url.startsWith('http')) {
    return res.status(400).json({ ok: false, error: '格式錯誤，範例：http://192.168.1.100:8000' });
  }
  _commandUrl = url.replace(/\/$/, '');
  // 寫入 config 表持久化
  db.prepare("INSERT OR REPLACE INTO config(key,value) VALUES('command_url',?)").run(_commandUrl);
  log.debug(`[Config] command_url set to: ${_commandUrl}`);
  startPiPush();  // 設定後立即嘗試啟動推送迴圈
  // 測試連線
  try {
    const r = await fetch(`${_commandUrl}/api/health`, { signal: AbortSignal.timeout(5000) });
    const body = await r.json();
    res.json({ ok: true, command_url: _commandUrl, health: body });
  } catch (err) {
    res.json({ ok: true, command_url: _commandUrl, health_error: err.message });
  }
});

/* ─── Wave 4：Pi API Key 管理端點 ─────────────────────────────── */
app.get('/admin/pi-api-key', adminAuth, (req, res) => {
  const key = getPiApiKey();
  res.json({ ok: true, has_key: !!key, key_suffix: key ? key.slice(-8) : null });
});

app.post('/admin/pi-api-key', adminAuth, (req, res) => {
  const { api_key } = req.body || {};
  if (!api_key || api_key.length < 16) {
    return res.status(400).json({ ok: false, error: 'api_key 至少 16 字元' });
  }
  db.prepare("INSERT OR REPLACE INTO config(key,value) VALUES('pi_api_key',?)").run(api_key);
  log.info('[Config] pi_api_key 已設定');
  startPiPush();  // 設定後立即嘗試啟動推送迴圈
  res.json({ ok: true });
});

const adminServer = tlsOpts
  ? https.createServer(tlsOpts, app)
  : http.createServer(app);

adminServer.listen(ADMIN_PORT, () => {
  log.info(`[Admin] v2.1 ${PROTOCOL.toUpperCase()} Listening on port ${ADMIN_PORT}`);
  if (!getAdminPinHash()) {
    log.warn('[Admin] ⚠️  管理員 PIN 尚未設定，請 POST /admin/setup {"admin_pin":"XXXX"}');
  }
  startPiPush();
});

process.on('SIGTERM', () => { wss.close(); db.close(); process.exit(0); });
process.on('SIGINT',  () => { wss.close(); db.close(); process.exit(0); });
