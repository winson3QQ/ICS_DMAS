'use strict';

// HOTFIX-WS-01 Pre-auth Gate Integration Tests
// T-1 ~ T-16，對應 AC-1 ~ AC-16
// 執行：node --test server/__tests__/ws_preauth.test.js

const { test }   = require('node:test');
const assert     = require('node:assert/strict');
const { spawn, spawnSync } = require('node:child_process');
const WebSocket  = require('ws');
const fs         = require('node:fs');
const path       = require('node:path');
const os         = require('node:os');
const crypto     = require('node:crypto');

const REPO_ROOT   = path.resolve(__dirname, '../..');
const ADMIN_PORT  = 19768;
const WS_PORT     = 19767;
const SETUP_PASS  = 'Str0ng@Pass1!';
const ALICE_PIN   = '4719';
const BOB_PIN     = '5823';

// ─── helpers ────────────────────────────────────────────────────────────────

function makeTmpEnv() {
  const id = crypto.randomBytes(8).toString('hex');
  return {
    tmpDb:    path.join(os.tmpdir(), `ws_test_${id}.db`),
    tmpToken: path.join(os.tmpdir(), `ws_token_${id}`),
  };
}

function cleanupFiles(...files) {
  for (const f of files) {
    ['', '-wal', '-shm'].forEach(suffix => {
      try { fs.rmSync(f + suffix, { force: true }); } catch { /* 略 */ }
    });
  }
}

async function spawnServer(extraEnv) {
  const child = spawn(process.execPath, ['server/index.js', '--unit', 'shelter'], {
    cwd: REPO_ROOT,
    env: { ...process.env, ADMIN_PORT: String(ADMIN_PORT), WS_PORT: String(WS_PORT),
           LOG_LEVEL: 'error', ...extraEnv },
    stdio: 'pipe',
  });
  child.on('error', err => { throw err; });
  return child;
}

async function waitAdminReady(maxMs = 12_000) {
  const base = `http://localhost:${ADMIN_PORT}`;
  const deadline = Date.now() + maxMs;
  while (Date.now() < deadline) {
    try {
      const r = await fetch(`${base}/admin/status`);
      if (r.status === 200 || r.status === 423) return;
    } catch { /* 尚未就緒 */ }
    await new Promise(r => setTimeout(r, 150));
  }
  throw new Error('Server not ready within timeout');
}

async function stopServer(child) {
  return new Promise(resolve => {
    child.once('close', resolve);
    child.kill('SIGTERM');
    if (process.platform === 'win32') child.kill();
    setTimeout(() => { try { child.kill(); } catch { /* 已停止 */ } }, 3000);
  });
}

async function completeFirstRun(tmpToken) {
  const token = fs.readFileSync(tmpToken, 'utf8').trim();
  const r = await fetch(`http://localhost:${ADMIN_PORT}/admin/setup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ first_run_token: token, admin_password: SETUP_PASS }),
  });
  assert.equal(r.status, 200, 'first-run setup should succeed');
}

async function createAccount(username, role, pin) {
  const r = await fetch(`http://localhost:${ADMIN_PORT}/admin/accounts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Admin-PIN': SETUP_PASS },
    body: JSON.stringify({ username, role, pin }),
  });
  assert.equal(r.status, 200, `create account ${username} should succeed`);
}

// 連接 WS，回傳 { ws, firstMsg, send, waitMessage, waitClose }
async function connectWS(timeoutMs = 5000) {
  return new Promise((resolve, reject) => {
    const ws  = new WebSocket(`ws://localhost:${WS_PORT}/ws`);
    const buf = [];
    let   closeInfo = null;

    ws.on('message', raw => { try { buf.push(JSON.parse(raw)); } catch { /* 略 */ } });
    ws.on('close',  (code, reason) => { closeInfo = { code, reason: reason?.toString() }; });
    ws.on('error',  reject);

    const t = setTimeout(() => reject(new Error('WS connect timeout')), timeoutMs);
    ws.on('open', () => {
      clearTimeout(t);
      resolve({
        ws,
        send: obj => ws.send(JSON.stringify(obj)),
        waitMessage: (ms = 3000) => new Promise((res, rej) => {
          if (buf.length) return res(buf.shift());
          const tt = setTimeout(() => rej(new Error('WS message timeout')), ms);
          const poll = setInterval(() => {
            if (buf.length) { clearInterval(poll); clearTimeout(tt); res(buf.shift()); }
          }, 20);
        }),
        waitClose: (ms = 3000) => new Promise((res, rej) => {
          if (closeInfo) return res(closeInfo);
          const tt = setTimeout(() => rej(new Error('WS close timeout')), ms);
          const poll = setInterval(() => {
            if (closeInfo) { clearInterval(poll); clearTimeout(tt); res(closeInfo); }
          }, 20);
        }),
      });
    });
  });
}

// ─── 帶 first-run 完成 + accounts 的完整 server fixture ─────────────────────

async function withSetupServer(fn) {
  const { tmpDb, tmpToken } = makeTmpEnv();
  const child = await spawnServer({ DB_PATH: tmpDb, FIRST_RUN_TOKEN_PATH: tmpToken });
  try {
    await waitAdminReady();
    await completeFirstRun(tmpToken);
    await createAccount('alice', '一般', ALICE_PIN);   // role: '一般'（server-side）
    await createAccount('bob',   '組長', BOB_PIN);     // role: '組長'
    await fn();
  } finally {
    await stopServer(child);
    cleanupFiles(tmpDb, tmpToken);
  }
}

// first-run 未完成的 server fixture
async function withFreshServer(fn) {
  const { tmpDb, tmpToken } = makeTmpEnv();
  const child = await spawnServer({ DB_PATH: tmpDb, FIRST_RUN_TOKEN_PATH: tmpToken });
  try {
    await waitAdminReady();
    await fn();
  } finally {
    await stopServer(child);
    cleanupFiles(tmpDb, tmpToken);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// T-1  AC-1：未 auth client 送 delta → close(4401, "unauthorized")
// ─────────────────────────────────────────────────────────────────────────────
test('unauth_delta_closes_4401_unauthorized', async () => {
  await withSetupServer(async () => {
    const { send, waitMessage, waitClose } = await connectWS();
    await waitMessage(); // consume welcome
    send({ type: 'delta', table: 'persons', record: { _id: 'x1' } });
    const err = await waitMessage();
    assert.equal(err.reason, 'unauthorized', 'error reason should be unauthorized');
    const { code } = await waitClose();
    assert.equal(code, 4401, 'close code should be 4401');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// T-2  AC-2：未 auth client 送 sync_push → close(4401)
// ─────────────────────────────────────────────────────────────────────────────
test('unauth_sync_push_closes_4401_unauthorized', async () => {
  await withSetupServer(async () => {
    const { send, waitMessage, waitClose } = await connectWS();
    await waitMessage();
    send({ type: 'sync_push', tables: { persons: [] } });
    const err = await waitMessage();
    assert.equal(err.reason, 'unauthorized');
    const { code } = await waitClose();
    assert.equal(code, 4401);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// T-3  AC-3：未 auth client 送 catchup_req → close(4401)，無 catchup_resp
// ─────────────────────────────────────────────────────────────────────────────
test('unauth_catchup_req_closes_4401_no_data_leaked', async () => {
  await withSetupServer(async () => {
    const { send, waitMessage, waitClose } = await connectWS();
    await waitMessage();
    send({ type: 'catchup_req', since: '1970-01-01T00:00:00.000Z' });
    const msg = await waitMessage();
    // 不應是 catchup_resp
    assert.notEqual(msg.type, 'catchup_resp', 'catchup_resp must not be sent to unauth client');
    assert.equal(msg.reason, 'unauthorized');
    const { code } = await waitClose();
    assert.equal(code, 4401);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// T-4  AC-4：未 auth client 送 audit_event → close(4401)，audit log 無注入
// ─────────────────────────────────────────────────────────────────────────────
test('unauth_audit_event_closes_4401_no_log_written', async () => {
  await withSetupServer(async () => {
    const { send, waitMessage, waitClose } = await connectWS();
    await waitMessage();
    send({ type: 'audit_event', action: 'FAKE_ADMIN_ACTION', operator_name: 'attacker' });
    const err = await waitMessage();
    assert.equal(err.reason, 'unauthorized');
    const { code } = await waitClose();
    assert.equal(code, 4401);

    // 確認 audit log 無 FAKE_ADMIN_ACTION
    const r    = await fetch(`http://localhost:${ADMIN_PORT}/admin/audit-log?limit=50`,
      { headers: { 'X-Admin-PIN': SETUP_PASS } });
    const body = await r.json();
    const fake = body.logs.filter(l => l.action === 'FAKE_ADMIN_ACTION');
    assert.equal(fake.length, 0, 'FAKE_ADMIN_ACTION must not appear in audit log');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// T-5  AC-5：未 auth client 送 auth → 正常處理（不被 gate 擋）
// ─────────────────────────────────────────────────────────────────────────────
test('unauth_auth_passes_preauth_gate', async () => {
  await withSetupServer(async () => {
    const { send, waitMessage } = await connectWS();
    await waitMessage();
    send({ type: 'auth', username: 'alice', pin: ALICE_PIN });
    const res = await waitMessage();
    assert.equal(res.type, 'auth_result', 'should receive auth_result, not be closed');
    assert.equal(res.ok, true);
    assert.equal(res.username, 'alice');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// T-6  AC-6：未 auth client 送 ping → 回 pong，連線不斷
// ─────────────────────────────────────────────────────────────────────────────
test('unauth_ping_returns_pong', async () => {
  await withSetupServer(async () => {
    const { ws, send, waitMessage } = await connectWS();
    await waitMessage();
    send({ type: 'ping' });
    const res = await waitMessage();
    assert.equal(res.type, 'pong');
    assert.equal(ws.readyState, WebSocket.OPEN, 'connection should remain open');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// T-7  AC-7：未 auth client 送 time_sync_req → 回 time_sync_resp，無敏感欄位
// ─────────────────────────────────────────────────────────────────────────────
test('unauth_time_sync_req_returns_response_no_sensitive_fields', async () => {
  await withSetupServer(async () => {
    const { ws, send, waitMessage } = await connectWS();
    await waitMessage();
    send({ type: 'time_sync_req', device_id: 'D01' });
    const res = await waitMessage();
    assert.equal(res.type, 'time_sync_resp');
    assert.ok(res.pi_time, 'pi_time should be present');
    // 不應含 server uptime 等敏感欄位
    assert.equal(res.uptime,       undefined, 'uptime must not be present');
    assert.equal(res.server_info,  undefined, 'server_info must not be present');
    assert.equal(res.memory,       undefined, 'memory must not be present');
    assert.equal(ws.readyState, WebSocket.OPEN);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// T-8  AC-8：auth 成功後 clients Map 含 server-side role，ws.isAuthed = true
// ─────────────────────────────────────────────────────────────────────────────
test('auth_success_sets_clients_map_with_account_role_and_isauthed', async () => {
  await withSetupServer(async () => {
    const { ws, send, waitMessage } = await connectWS();
    await waitMessage();
    send({ type: 'auth', username: 'alice', pin: ALICE_PIN });
    const res = await waitMessage();
    assert.equal(res.ok, true);
    assert.equal(res.role, '一般', 'role must be server-side value');
    assert.ok(res.pi_time,   'pi_time should be present in auth_result');
    assert.ok(res.site_salt, 'site_salt should be present in auth_result');
    // ws.isAuthed 是 server-side 屬性；行為驗證：auth 後送 ping 不被 gate 斷線
    send({ type: 'ping' });
    const pong = await waitMessage();
    assert.equal(pong.type, 'pong', 'after auth, ping should return pong (connection stays open)');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// T-9  AC-9：auth 訊息含 client 自報 role="組長"，accounts 表實際 role="一般" → server-side wins
// ─────────────────────────────────────────────────────────────────────────────
test('auth_ignores_client_claimed_role_server_side_wins', async () => {
  await withSetupServer(async () => {
    const { send, waitMessage } = await connectWS();
    await waitMessage();
    // alice 在 DB 中是 '一般'，client 自報 '組長'
    send({ type: 'auth', username: 'alice', pin: ALICE_PIN, role: '組長' });
    const res = await waitMessage();
    assert.equal(res.ok, true);
    assert.equal(res.role, '一般', 'server-side role must win over client-claimed role');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// T-10  AC-10：session_restore（任何內容）→ close(4401, "session_expired")
// ─────────────────────────────────────────────────────────────────────────────
test('session_restore_always_closes_4401_session_expired', async () => {
  await withSetupServer(async () => {
    const { send, waitMessage, waitClose } = await connectWS();
    await waitMessage();
    send({ type: 'session_restore', username: 'alice', role: '組長', device_id: 'D01' });
    const err = await waitMessage();
    assert.equal(err.reason, 'session_expired');
    const { code } = await waitClose();
    assert.equal(code, 4401);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// T-11  AC-11：first-run 未完成 + state-changing → close(4423, "setup_required")
// ─────────────────────────────────────────────────────────────────────────────
test('first_run_state_changing_closes_4423_setup_required', async () => {
  await withFreshServer(async () => {
    const { send, waitMessage, waitClose } = await connectWS();
    await waitMessage();
    send({ type: 'delta', table: 'persons', record: { _id: 'x1' } });
    const { code, reason } = await waitClose();
    assert.equal(code,   4423,            'close code must be 4423');
    assert.equal(reason, 'setup_required', 'reason must be setup_required');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// T-12  AC-12：first-run 未完成 + catchup_req → close(4423)，無 catchup_resp
// ─────────────────────────────────────────────────────────────────────────────
test('first_run_catchup_req_closes_4423_setup_required', async () => {
  await withFreshServer(async () => {
    const { send, waitMessage, waitClose } = await connectWS();
    await waitMessage();
    send({ type: 'catchup_req', since: '1970-01-01T00:00:00.000Z' });
    // 不應收到 catchup_resp；直接看 close
    const { code, reason } = await waitClose(3000);
    assert.equal(code,   4423);
    assert.equal(reason, 'setup_required');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// T-13  AC-13：first-run 未完成 + session_restore → close(4423)（Layer 0 wins，非 4401）
// ─────────────────────────────────────────────────────────────────────────────
test('first_run_session_restore_closes_4423_layer0_wins_not_4401', async () => {
  await withFreshServer(async () => {
    const { send, waitMessage, waitClose } = await connectWS();
    await waitMessage();
    send({ type: 'session_restore', username: 'alice', role: '組長' });
    const { code, reason } = await waitClose(3000);
    assert.equal(code,   4423,            'Layer 0 must win: code must be 4423 not 4401');
    assert.equal(reason, 'setup_required', 'reason must be setup_required');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// T-14  AC-14：clear_table 使用 clients.has(ws)（auth 後可執行）
// ─────────────────────────────────────────────────────────────────────────────
test('clear_table_uses_clients_has_not_isauthed', async () => {
  await withSetupServer(async () => {
    const { send, waitMessage } = await connectWS();
    await waitMessage();
    // 先 auth
    send({ type: 'auth', username: 'bob', pin: BOB_PIN });
    const authRes = await waitMessage();
    assert.equal(authRes.ok, true, 'auth must succeed before clear_table test');
    // auth 後 clients.has(ws) = true，clear_table 應成功
    send({ type: 'clear_table', table: 'persons' });
    const clearRes = await waitMessage();
    assert.equal(clearRes.type, 'clear_table_ack', 'authenticated client should get clear_table_ack');
    assert.equal(clearRes.ok,   true);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// T-15  AC-15：HOTFIX-PI-01 17 scenarios regression
// ─────────────────────────────────────────────────────────────────────────────
test('pi01_regression_17_scenarios_all_pass', () => {
  const result = spawnSync(
    process.execPath,
    ['--test', 'server/__tests__/first_run_integration.test.js'],
    { cwd: REPO_ROOT, timeout: 60_000, encoding: 'utf8' }
  );
  assert.equal(result.status, 0,
    `first_run_integration tests failed:\n${result.stderr || result.stdout}`);
});

// ─────────────────────────────────────────────────────────────────────────────
// T-16  AC-16：三個 audit event 欄位齊備，username/role 取自 server-side
// ─────────────────────────────────────────────────────────────────────────────
test('audit_log_three_ws_events_present_with_server_side_fields', async () => {
  await withSetupServer(async () => {
    // 觸發 ws_auth_success
    const c1 = await connectWS();
    await c1.waitMessage();
    c1.send({ type: 'auth', username: 'alice', pin: ALICE_PIN });
    await c1.waitMessage();

    // 觸發 ws_unauthorized_message_blocked（T-1 路徑）
    const c2 = await connectWS();
    await c2.waitMessage();
    c2.send({ type: 'delta', table: 'persons', record: { _id: 'x1' } });
    await c2.waitMessage();
    await c2.waitClose();

    // 觸發 ws_session_restore_rejected（T-10 路徑）
    const c3 = await connectWS();
    await c3.waitMessage();
    c3.send({ type: 'session_restore', username: 'alice' });
    await c3.waitMessage();
    await c3.waitClose();

    // 查 audit log
    const r    = await fetch(`http://localhost:${ADMIN_PORT}/admin/audit-log?limit=100`,
      { headers: { 'X-Admin-PIN': SETUP_PASS } });
    const body = await r.json();
    const logs = body.logs;

    // ws_auth_success 欄位驗證
    const authEvt = logs.find(l => l.action === 'ws_auth_success');
    assert.ok(authEvt, 'ws_auth_success must be in audit log');
    const authDetail = JSON.parse(authEvt.detail || '{}');
    assert.ok(authDetail.ws_id,      'ws_auth_success must have ws_id');
    assert.equal(authDetail.username, 'alice',  'username must be server-side value');
    assert.equal(authDetail.role,     '一般',   'role must be server-side value (not client-claimed)');
    assert.ok(authDetail.source_ip,  'source_ip must be present');

    // ws_unauthorized_message_blocked 欄位驗證
    const blockEvt = logs.find(l => l.action === 'ws_unauthorized_message_blocked');
    assert.ok(blockEvt, 'ws_unauthorized_message_blocked must be in audit log');
    const blockDetail = JSON.parse(blockEvt.detail || '{}');
    assert.ok(blockDetail.ws_id,         'must have ws_id');
    assert.ok(blockDetail.message_type,  'must have message_type');
    assert.ok(blockDetail.source_ip,     'must have source_ip');
    assert.equal(blockDetail.close_code, 4401, 'close_code must be 4401');

    // ws_session_restore_rejected 欄位驗證
    const restoreEvt = logs.find(l => l.action === 'ws_session_restore_rejected');
    assert.ok(restoreEvt, 'ws_session_restore_rejected must be in audit log');
    const restoreDetail = JSON.parse(restoreEvt.detail || '{}');
    assert.ok(restoreDetail.ws_id,      'must have ws_id');
    assert.equal(restoreDetail.reason,  'no_token', 'reason must be no_token');
    assert.ok(restoreDetail.source_ip,  'must have source_ip');
  });
});
