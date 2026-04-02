#!/usr/bin/env node
/* ════════════════════════════════════════════════════════════════════
   收容組 PWA v2.1 — shelter_ws_server_v2.1.js
   Pi WebSocket 伺服器（L2 跨裝置即時同步 + 任務帳號驗證）

   v2.1 新增：
   - config 表補 last_sync_to_command（三 Pass 同步起始時間）
   - sync_push 訊息處理器（網路恢復後接收收容組推送）
   - sync_ack 回應（含三 Pass Pass1 SNAPSHOT 合併結果）

   預設 Port：
     8765 — WebSocket（資料同步 + 驗證）
     8766 — HTTP（帳號管理 API + admin_v2.0.html 管理介面）

   依賴：
     npm install ws better-sqlite3 express cors crypto

   systemd 啟動範例：
     ExecStart=/usr/bin/node /home/pi/shelter_ws_server_v2.1.js
   ════════════════════════════════════════════════════════════════════ */
'use strict';

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
const SERVER_VERSION = 'v0.2.0';
log.info(`Shelter WS Server ${SERVER_VERSION} | Log level: ${process.env.LOG_LEVEL || 'debug'}`);

/* ─── 設定 ────────────────────────────────────────────────────── */
const WS_PORT      = process.env.WS_PORT       || 8765;
const ADMIN_PORT   = process.env.ADMIN_PORT    || 8766;
const DB_PATH      = process.env.DB_PATH       || path.join(__dirname, 'shelter_accounts.db');
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

/* ─── 定時推快照至指揮部（聯網情境自動同步）────────────────────────
   每 AUTO_PUSH_INTERVAL_MS 毫秒推最新快照至指揮部 /api/snapshots。
   環境變數 AUTO_PUSH_INTERVAL_MS 可覆寫，預設 5 分鐘。
── */
const AUTO_PUSH_INTERVAL_MS = parseInt(process.env.AUTO_PUSH_INTERVAL_MS || '') || 2 * 60 * 1000;

async function autoPushLatestSnapshot() {
  const target = _commandUrl || COMMAND_URL;
  if (!target) return;
  let row;
  try {
    row = db.prepare(
      "SELECT payload_json FROM snapshots ORDER BY recv_at DESC LIMIT 1"
    ).get();
  } catch { return; }
  if (!row) return;
  let payload;
  try { payload = JSON.parse(row.payload_json); } catch { return; }
  // 驗證必填欄位（SnapshotIn 格式）：格式不對就跳過，避免 FastAPI 422
  const required = ['v', 'type', 'snapshot_id', 't', 'src'];
  if (required.some(k => !(k in payload))) {
    log.debug('[AutoPush] 快照格式不符 SnapshotIn，略過（等待新格式快照）');
    return;
  }
  payload.source = 'auto';
  await pushToCommand(payload);
}

function startAutoPush() {
  if (!(_commandUrl || COMMAND_URL)) return;
  setTimeout(() => autoPushLatestSnapshot(), 10_000);      // 啟動 10 秒後先推一次
  setInterval(() => autoPushLatestSnapshot(), AUTO_PUSH_INTERVAL_MS);
  log.info(`[AutoPush] 定時推快照至指揮部，間隔 ${AUTO_PUSH_INTERVAL_MS / 1000}s`);
}

/* ─── 三 Pass 完整同步至指揮部（網路恢復後）──────────────────────
   呼叫指揮部 POST /api/sync/push，傳入：
     - snapshots：Pi 快照表中 recv_at >= last_sync_to_command 的所有快照
     - events：delta_log 中 incidents 記錄 ts >= last_sync_to_command
   指揮部執行三 Pass 後回傳結果，Pi 更新 last_sync_to_command。
   若 /api/sync/push 不可用，fallback 至 /api/snapshots 推最新快照。
── */
async function pushThreePassToCommand(lastSyncTs) {
  const target = _commandUrl || COMMAND_URL;
  if (!target) return;
  const since = lastSyncTs || '1970-01-01T00:00:00.000Z';

  let snapshots = [];
  try {
    const rows = db.prepare(
      "SELECT payload_json FROM snapshots WHERE recv_at >= ? ORDER BY recv_at ASC"
    ).all(since);
    snapshots = rows.map(r => { try { return JSON.parse(r.payload_json); } catch { return null; } }).filter(Boolean);
  } catch { /* snapshots 表空 */ }

  let events = [];
  try {
    const rows = db.prepare(
      "SELECT record_json FROM delta_log WHERE table_name='incidents' AND ts >= ? ORDER BY ts ASC LIMIT 200"
    ).all(since);
    events = rows.map(r => { try { return JSON.parse(r.record_json); } catch { return null; } }).filter(Boolean);
  } catch { /* delta_log 空 */ }

  try {
    const res = await postJSON(`${target}/api/sync/push`, {
      source_unit: 'shelter', sync_start_ts: since,
      device_id: 'shelter_pi', snapshots, events, manual_records: [],
    }, 15_000);
    if (res.status >= 200 && res.status < 300) {
      const result = JSON.parse(res.body);
      updateLastSyncToCommand(nowISO());
      log.info(`[ThreePass] OK → P1 merged:${result.pass1_merged} added:${result.pass1_added} P2 conflicts:${result.pass2_conflicts} P3:${result.pass3_added}`);
      return result;
    }
    log.warn(`[ThreePass] /api/sync/push 回應 ${res.status}，fallback`);
  } catch (err) {
    log.warn(`[ThreePass] 失敗: ${err.message}，fallback`);
  }
  // fallback：推最新快照
  if (snapshots.length > 0) await pushToCommand(snapshots[snapshots.length - 1]);
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

  -- v2.1: SNAPSHOT 表（供三 Pass 對齊用，儲存從各收容組推送的快照摘要）
  CREATE TABLE IF NOT EXISTS snapshots (
    snapshot_uuid  TEXT PRIMARY KEY,
    unit_id        TEXT NOT NULL DEFAULT 'shelter',
    source         TEXT NOT NULL DEFAULT 'pi_push',
    payload_json   TEXT NOT NULL,
    recv_at        TEXT NOT NULL,
    merged         INTEGER NOT NULL DEFAULT 0
  );
`);

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
   WebSocket 伺服器（Port 8765，支援 WSS/WS）
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
        const { username, role, device_id } = msg;
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

      /* ── v2.1: sync_push（網路恢復後，收容組推送完整記錄至 Pi）
         §10.4：收容組 Pi 收到推送後：
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
        const SYNC_TABLES = ['persons','beds','resources','incidents','shifts'];
        for (const table of SYNC_TABLES) {
          const records = tables?.[table] || [];
          for (const record of records) {
            if (!record || !record._id) continue;
            const delta = {
              src: pushDeviceId || 'shelter_push',
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
                .run(snap.snapshot_uuid, snap.unit_id || 'shelter', 'pi_push',
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

        // §10.4：網路恢復後執行三 Pass 完整同步至指揮部（非同步，不阻塞回應）
        // 使用 pushThreePassToCommand 取代 pushToCommand，帶入所有斷線期間的快照與事件
        pushThreePassToCommand(sync_start_ts).catch(err =>
          log.warn('[ThreePass] async error:', err.message)
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
   HTTP Admin API（Port 8766）
════════════════════════════════════════════════════════════════ */
const app = express();
app.use(cors({ origin: '*' }));
app.use(express.json());

// 提供 public/ 下的靜態檔案（shelter_pwa.html、sw.js、manifest.json、lib/）
// 讓平板可直接用 http://<ip>:8766/shelter_pwa.html 開啟 PWA
const PUBLIC_DIR = path.join(__dirname, '..', 'public');
if (fs.existsSync(PUBLIC_DIR)) {
  app.use(express.static(PUBLIC_DIR));
  log.info(`[Static] 提供 PWA 靜態檔案：${PUBLIC_DIR}`);
}

app.get('/', (req, res) => {
  const pwaPath = path.join(PUBLIC_DIR, 'shelter_pwa.html');
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
  if (!['組長','人管','物管','環管'].includes(role)) return res.status(400).json({ ok: false, reason: '角色不在允許清單' });
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
  if (!['組長','人管','物管','環管'].includes(role)) return res.status(400).json({ ok: false, reason: '角色不在允許清單' });
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
  // 測試連線
  try {
    const r = await fetch(`${_commandUrl}/api/health`, { signal: AbortSignal.timeout(5000) });
    const body = await r.json();
    res.json({ ok: true, command_url: _commandUrl, health: body });
  } catch (err) {
    res.json({ ok: true, command_url: _commandUrl, health_error: err.message });
  }
});

const adminServer = tlsOpts
  ? https.createServer(tlsOpts, app)
  : http.createServer(app);

adminServer.listen(ADMIN_PORT, () => {
  log.info(`[Admin] v2.1 ${PROTOCOL.toUpperCase()} Listening on port ${ADMIN_PORT}`);
  if (!getAdminPinHash()) {
    log.warn('[Admin] ⚠️  管理員 PIN 尚未設定，請 POST /admin/setup {"admin_pin":"XXXX"}');
  }
  startAutoPush();
});

process.on('SIGTERM', () => { wss.close(); db.close(); process.exit(0); });
process.on('SIGINT',  () => { wss.close(); db.close(); process.exit(0); });
