'use strict';

const { db, nowISO, newUUID } = require('./db');

function writeAuditLog(action, operator, deviceId, sessionId, detail) {
  db.prepare(`INSERT INTO audit_log(id,action,operator_name,device_id,session_id,timestamp,detail)
              VALUES(?,?,?,?,?,?,?)`)
    .run(newUUID(), action, operator, deviceId || null, sessionId || null, nowISO(), JSON.stringify(detail || {}));
}

module.exports = { writeAuditLog };
