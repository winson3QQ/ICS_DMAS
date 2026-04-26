'use strict';

const http      = require('http');
const https     = require('https');
const WebSocket = require('ws');

const { log }    = require('./logger');
const { cfg, tlsOpts, WS_PORT, WS_PROTOCOL } = require('./config');
const { db, nowISO, appendDelta, getRecentDeltas, getLastSyncToCommand, updateLastSyncToCommand } = require('./db');
const { writeAuditLog } = require('./audit');
const { hashPin, isLoginLocked, recordLoginFailure, getAdminPinHash } = require('./auth');
const { getSiteSalt } = require('./db');
const { piPushOnce, getCommandStatus, setBroadcast } = require('./sync');

const wsRawServer = tlsOpts ? https.createServer(tlsOpts) : http.createServer();
const wss         = new WebSocket.Server({ server: wsRawServer, perMessageDeflate: false });
const clients     = new Map();

function broadcast(msgObj) {
  const str = JSON.stringify(msgObj);
  wss.clients.forEach(c => { if (c.readyState === WebSocket.OPEN) c.send(str); });
}
setBroadcast(broadcast);

wsRawServer.on('upgrade', (req, socket) => {
  const urlSrc = new URL(req.url, 'wss://localhost').searchParams.get('src') || '?';
  log.debug(`[WS] HTTP Upgrade from ${socket.remoteAddress} src=${urlSrc}`);
});

wss.on('connection', (ws, req) => {
  const ip     = req.socket.remoteAddress;
  const urlSrc = new URL(req.url, 'wss://localhost').searchParams.get('src') || '?';
  log.info(`[WS] Client connected from ${ip} src=${urlSrc}`);

  ws.isAlive = true;
  ws.on('pong', () => { ws.isAlive = true; });

  let _zombieTimer = setTimeout(() => {
    log.warn(`[WS] No message in 5s from ${ip} src=${urlSrc} → zombie suspected`);
  }, 5000);

  const _STATE_CHANGING = new Set(['delta', 'sync_push', 'session_restore', 'audit_event', 'clear_table']);

  ws.on('message', async (raw) => {
    if (_zombieTimer) { clearTimeout(_zombieTimer); _zombieTimer = null; }
    let msg;
    try { msg = JSON.parse(raw); } catch { return; }
    log.debug(`[WS] ← ${msg.type} from ${ip} ${msg.table || ''} ${msg.record?._id ?? msg.record?.id ?? ''}`);

    // First-run gate：首次設定完成前阻擋所有 state-changing 訊息
    if (!getAdminPinHash() && _STATE_CHANGING.has(msg.type)) {
      ws.send(JSON.stringify({ type: 'error', code: 'FIRST_RUN_REQUIRED', reason: '首次設定未完成' }));
      return;
    }

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
        const account = db.prepare('SELECT * FROM accounts WHERE username=? AND status=?').get(username, 'active');
        if (!account) {
          writeAuditLog('login_failed', username, device_id || '', null, { reason: '帳號不存在或已停用' });
          ws.send(JSON.stringify({ type: 'auth_result', ok: false, reason: '帳號不存在或已停用' }));
          return;
        }
        const hash = await hashPin(pin, account.pin_salt);
        if (hash !== account.pin_hash) {
          const locked = recordLoginFailure(username);
          writeAuditLog('login_failed', username, device_id || '', null, { reason: 'PIN 錯誤', now_locked: locked });
          ws.send(JSON.stringify({
            type: 'auth_result', ok: false,
            reason: locked ? '連續錯誤超過 5 次，鎖定 30 分鐘，請稍後再試' : 'PIN 錯誤',
          }));
          return;
        }
        db.prepare('DELETE FROM login_failures WHERE username=?').run(username);
        db.prepare('UPDATE accounts SET last_login=?, device_id=? WHERE username=?').run(nowISO(), device_id || null, username);
        clients.set(ws, { deviceId: device_id || ip, username, role: account.role, connectedAt: nowISO() });
        writeAuditLog('login_success', username, device_id || '', null, { role: account.role });
        ws.send(JSON.stringify({
          type: 'auth_result', ok: true, username, role: account.role,
          pi_time:              nowISO(),
          last_sync_to_command: getLastSyncToCommand(),
          site_salt:            getSiteSalt(),
        }));
        log.info(`[WS] Auth OK: ${username} (${account.role}) from ${ip}`);
        break;
      }

      /* ── Delta 廣播（L2 同步） ── */
      case 'delta': {
        appendDelta(msg);
        wss.clients.forEach(client => {
          if (client !== ws && client.readyState === WebSocket.OPEN) {
            client.send(JSON.stringify({ ...msg, _relayed_by_pi: true }));
          }
        });
        break;
      }

      /* ── debug_ping ── */
      case 'debug_ping': {
        log.info(`[WS] debug_ping from ${ip} source=${msg.source || '?'} device=${msg.device_id || '?'}`);
        break;
      }

      /* ── session_restore ── */
      case 'session_restore': {
        const { username, role: rawRole, device_id } = msg;
        const role = cfg.roles.includes(rawRole) ? rawRole : cfg.defaultRole;
        if (username && role) {
          const existing = clients.get(ws);
          clients.set(ws, { deviceId: device_id || ip, username, role, connectedAt: existing?.connectedAt || nowISO() });
          log.info(`[WS] Session restored: ${username} (${role}) device=${device_id || '?'}`);
        }
        break;
      }

      /* ── Catchup 請求 ── */
      case 'catchup_req': {
        const since  = msg.since || '1970-01-01T00:00:00.000Z';
        const deltas = getRecentDeltas(since);
        ws.send(JSON.stringify({ type: 'catchup_resp', deltas, pi_time: nowISO() }));
        log.info(`[WS] Catchup: sent ${deltas.length} deltas since ${since}`);
        break;
      }

      /* ── sync_push（網路恢復後完整記錄推送） ── */
      case 'sync_push': {
        const { sync_start_ts, tables, snapshots: pushSnapshots, device_id: pushDeviceId, full_sync_tables } = msg;
        let recordsApplied  = 0;
        let snapshotsMerged = 0;

        const SYNC_TABLES = cfg.syncTables;
        if (Array.isArray(full_sync_tables)) {
          for (const tbl of full_sync_tables) {
            if (SYNC_TABLES.includes(tbl)) {
              const result = db.prepare('DELETE FROM current_state WHERE table_name=?').run(tbl);
              log.info(`[sync_push] full_sync clear: ${tbl}, deleted ${result.changes} rows`);
            }
          }
        }

        for (const table of SYNC_TABLES) {
          const records = tables?.[table] || [];
          for (const record of records) {
            if (!record || !record._id) continue;
            const delta = {
              src: pushDeviceId || `${cfg.unitId}_push`,
              table, action: 'upsert', record,
              ts: record.updated_at || record.timestamp || nowISO(),
            };
            appendDelta(delta);
            wss.clients.forEach(client => {
              if (client !== ws && client.readyState === WebSocket.OPEN) {
                client.send(JSON.stringify({ ...delta, _relayed_by_pi: true, type: 'delta' }));
              }
            });
            recordsApplied++;
          }
        }

        const passOneResults = [];
        if (Array.isArray(pushSnapshots)) {
          for (const snap of pushSnapshots) {
            if (!snap.snapshot_uuid) continue;
            const existing = db.prepare('SELECT snapshot_uuid FROM snapshots WHERE snapshot_uuid=?').get(snap.snapshot_uuid);
            if (existing) {
              db.prepare(`UPDATE snapshots SET source='merged_from_qr', payload_json=?, merged=1 WHERE snapshot_uuid=?`)
                .run(JSON.stringify(snap), snap.snapshot_uuid);
              passOneResults.push({ uuid: snap.snapshot_uuid, action: 'merged_over_qr' });
            } else {
              db.prepare(`INSERT OR IGNORE INTO snapshots(snapshot_uuid,unit_id,source,payload_json,recv_at,merged) VALUES(?,?,?,?,?,0)`)
                .run(snap.snapshot_uuid, snap.unit_id || cfg.unitId, 'pi_push', JSON.stringify(snap), nowISO());
              passOneResults.push({ uuid: snap.snapshot_uuid, action: 'inserted' });
            }
            snapshotsMerged++;
          }
        }

        const newSyncTs = nowISO();
        updateLastSyncToCommand(newSyncTs);
        writeAuditLog('network_recovery_push', clients.get(ws)?.username || 'unknown',
          pushDeviceId || '', null,
          { sync_start_ts, records_sent: recordsApplied, snapshots_merged: snapshotsMerged, triggered_by: 'ws_reconnect' }
        );

        ws.send(JSON.stringify({
          type: 'sync_ack', ok: true, pi_time: newSyncTs,
          last_sync_to_command: newSyncTs,
          records_applied:  recordsApplied,
          snapshots_merged: snapshotsMerged,
          pass1_results:    passOneResults,
        }));
        log.info(`[WS] sync_push: applied ${recordsApplied} records, merged ${snapshotsMerged} snapshots`);

        piPushOnce().catch(err => log.warn('[PiPush] sync_push trigger error:', err.message));
        break;
      }

      /* ── 時間同步 ── */
      case 'time_sync_req': {
        ws.send(JSON.stringify({ type: 'time_sync_resp', pi_time: nowISO(), device_id: msg.device_id }));
        break;
      }

      /* ── 稽核事件上傳 ── */
      case 'audit_event': {
        try {
          writeAuditLog(
            msg.action        || 'unknown',
            msg.operator_name || '未知',
            msg.device_id     || '',
            msg.session_id    || null,
            msg.detail        || {}
          );
        } catch { /* non-critical */ }
        break;
      }

      /* ── 清除指定 table（床位重建） ── */
      case 'clear_table': {
        if (!ws.isAuthed) { ws.send(JSON.stringify({ type: 'error', reason: '未認證' })); break; }
        const CLEARABLE = ['beds', 'persons', 'resources', 'incidents', 'shifts'];
        const tbl = msg.table;
        if (!CLEARABLE.includes(tbl)) {
          ws.send(JSON.stringify({ type: 'error', reason: `不允許清除 ${tbl}` }));
          break;
        }
        db.prepare('DELETE FROM current_state WHERE table_name=?').run(tbl);
        log.info(`[clear_table] ${tbl} cleared by ${ws.username || 'unknown'}`);
        ws.send(JSON.stringify({ type: 'clear_table_ack', table: tbl, ok: true }));
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
    log.info(`[WS] Disconnected: ${info ? info.username : '(未驗證)'} code=${code} reason=${reason || ''}`);
    clients.delete(ws);
  });

  ws.on('error', err => log.warn('[WS] Error:', err.message));

  ws.send(JSON.stringify({
    type: 'welcome', pi_time: nowISO(), server_version: '2.1',
    last_sync_to_command: getLastSyncToCommand(),
    command_status: getCommandStatus(),
  }));
});

wss.on('error', err => log.error('[WS Server Error]', err));

/* ─── Server-side Ping（維持 iOS Safari 連線）── */
setInterval(() => {
  wss.clients.forEach(ws => {
    if (ws.readyState !== WebSocket.OPEN) return;
    if (ws.isAlive === false) {
      log.warn(`[WS] No pong, terminating ${clients.get(ws)?.username || '(未驗證)'}`);
      ws.terminate();
      return;
    }
    ws.isAlive = false;
    ws.ping();
  });
}, 25_000);

function startWsServer() {
  wsRawServer.listen(WS_PORT, () => {
    log.info(`[WS] ${WS_PROTOCOL.toUpperCase()} Server listening on port ${WS_PORT}`);
  });
}

module.exports = { wss, clients, broadcast, startWsServer };
