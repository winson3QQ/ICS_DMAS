'use strict';

const http    = require('http');
const https   = require('https');
const express = require('express');

const { log }                    = require('./logger');
const { ADMIN_PORT, PROTOCOL, tlsOpts } = require('./config');
const { db }                     = require('./db');
const { wss, startWsServer }     = require('./ws_handler');
const { registerRoutes }         = require('./routes');
const { startPiPush }            = require('./sync');
const { getAdminPinHash }        = require('./auth');

const app         = express();
registerRoutes(app);

const adminServer = tlsOpts
  ? https.createServer(tlsOpts, app)
  : http.createServer(app);

adminServer.listen(ADMIN_PORT, () => {
  log.info(`[Admin] v2.1 ${PROTOCOL.toUpperCase()} Listening on port ${ADMIN_PORT}`);
  if (!getAdminPinHash()) {
    log.warn('[Admin] ⚠  管理員 PIN 尚未設定，請 POST /admin/setup {"admin_pin":"XXXX"}');
  }
  startPiPush();
});

startWsServer();

process.on('SIGTERM', () => { wss.close(); db.close(); process.exit(0); });
process.on('SIGINT',  () => { wss.close(); db.close(); process.exit(0); });
