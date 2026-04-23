'use strict';

const _LOG_LEVELS = { error: 0, warn: 1, info: 2, debug: 3 };
const _logLevel = _LOG_LEVELS[process.env.LOG_LEVEL] ?? _LOG_LEVELS.debug;
const _ts = () => new Date().toISOString().slice(11, 23);

const log = {
  error: (...a) => _logLevel >= 0 && console.error(`[E][${_ts()}]`, ...a),
  warn:  (...a) => _logLevel >= 1 && console.warn (`[W][${_ts()}]`, ...a),
  info:  (...a) => _logLevel >= 2 && console.log  (`[I][${_ts()}]`, ...a),
  debug: (...a) => _logLevel >= 3 && console.log  (`[D][${_ts()}]`, ...a),
};

module.exports = { log };
