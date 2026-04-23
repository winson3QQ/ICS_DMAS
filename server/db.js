'use strict';

const crypto   = require('crypto');
const Database = require('better-sqlite3');
const { log }  = require('./logger');
const { DB_PATH, DELTA_LOG_MAX, cfg, getCommandUrl, setCommandUrl } = require('./config');
const { runMigrations } = require('./migrations');

const nowISO    = () => new Date().toISOString();
const newUUID   = () => crypto.randomUUID ? crypto.randomUUID() : crypto.randomBytes(16).toString('hex');
const randomHex = (bytes = 16) => crypto.randomBytes(bytes).toString('hex');

const db = new Database(DB_PATH);
runMigrations(db);

(function initConfig() {
  if (!db.prepare("SELECT value FROM config WHERE key='last_sync_to_command'").get()) {
    db.prepare("INSERT INTO config(key,value) VALUES('last_sync_to_command','1970-01-01T00:00:00.000Z')").run();
    log.debug('[Config] Initialized last_sync_to_command = epoch');
  }

  if (!db.prepare("SELECT value FROM config WHERE key='site_salt'").get()) {
    const salt = randomHex(16);
    db.prepare("INSERT INTO config(key,value) VALUES('site_salt',?)").run(salt);
    log.info('[Config] Generated new site_salt (first startup)');
  } else {
    log.debug('[Config] site_salt loaded from DB');
  }

  if (!getCommandUrl()) {
    const row = db.prepare("SELECT value FROM config WHERE key='command_url'").get();
    if (row) {
      setCommandUrl(row.value);
      log.debug(`[Config] Loaded command_url from DB: ${row.value}`);
    }
  }

  if (!db.prepare("SELECT value FROM config WHERE key='admin_pin_hash'").get()) {
    const salt = randomHex(16);
    crypto.pbkdf2('1234', Buffer.from(salt, 'hex'), 200000, 32, 'sha256', (err, key) => {
      if (err) { log.warn('[Seed] admin PIN hash error:', err.message); return; }
      db.prepare("INSERT OR REPLACE INTO config(key,value) VALUES('admin_pin_hash',?)").run(key.toString('hex'));
      db.prepare("INSERT OR REPLACE INTO config(key,value) VALUES('admin_pin_salt',?)").run(salt);
      log.info('[Seed] 預設管理員 PIN 已設定（1234）');
      if (!db.prepare('SELECT id FROM accounts WHERE username=?').get('admin')) {
        const acctSalt = randomHex(16);
        crypto.pbkdf2('1234', Buffer.from(acctSalt, 'hex'), 200000, 32, 'sha256', (e2, k2) => {
          if (e2) return;
          db.prepare(`INSERT INTO accounts(id,username,role,pin_hash,pin_salt,status,created_at,created_by)
                      VALUES(?,?,?,?,?,?,?,?)`)
            .run(newUUID(), 'admin', cfg.roles[0], k2.toString('hex'), acctSalt, 'active', nowISO(), 'system');
          log.info(`[Seed] 預設帳號 admin/${cfg.roles[0]} 已建立`);
        });
      }
    });
  }
})();

// Delta log（in-memory buffer + persistent）
const deltaLog = [];

function appendDelta(msg) {
  deltaLog.unshift({ ...msg, recv_at: nowISO() });
  if (deltaLog.length > DELTA_LOG_MAX) deltaLog.length = DELTA_LOG_MAX;

  try {
    db.prepare(`INSERT INTO delta_log(src,table_name,record_id,record_json,ts,recv_at) VALUES(?,?,?,?,?,?)`)
      .run(
        msg.src || '',
        msg.table || '',
        String(msg.record?._id ?? msg.record?.id ?? ''),
        JSON.stringify(msg.record || {}),
        msg.ts || '',
        nowISO()
      );
    db.prepare(`DELETE FROM delta_log WHERE id NOT IN (
      SELECT id FROM delta_log ORDER BY id DESC LIMIT ?
    )`).run(DELTA_LOG_MAX);
  } catch (e) { /* non-critical */ }

  const _tbl = msg.table || '';
  const _rid = String(msg.record?._id ?? msg.record?.id ?? '');
  if (_tbl && _rid) {
    try {
      db.prepare(`INSERT INTO current_state(table_name, record_id, record_json, updated_at)
                  VALUES(?,?,?,?)
                  ON CONFLICT(table_name, record_id) DO UPDATE SET
                    record_json=excluded.record_json, updated_at=excluded.updated_at`)
        .run(_tbl, _rid, JSON.stringify(msg.record || {}), nowISO());
    } catch (e) { log.warn('[current_state] UPSERT error:', e.message); }
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
  } catch (e) { return []; }
}

function getLastSyncToCommand() {
  const row = db.prepare("SELECT value FROM config WHERE key='last_sync_to_command'").get();
  return row ? row.value : '1970-01-01T00:00:00.000Z';
}

function updateLastSyncToCommand(isoTs) {
  db.prepare("INSERT OR REPLACE INTO config(key,value) VALUES('last_sync_to_command',?)").run(isoTs);
}

function getSiteSalt() {
  const row = db.prepare("SELECT value FROM config WHERE key='site_salt'").get();
  if (row) return row.value;
  log.warn('[Config] site_salt missing from DB, regenerating');
  const salt = randomHex(16);
  db.prepare("INSERT OR REPLACE INTO config(key,value) VALUES('site_salt',?)").run(salt);
  return salt;
}

module.exports = {
  db, nowISO, newUUID, randomHex,
  appendDelta, getRecentDeltas,
  getLastSyncToCommand, updateLastSyncToCommand,
  getSiteSalt,
};
