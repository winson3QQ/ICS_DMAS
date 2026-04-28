import { describe, expect, test, vi, beforeAll } from 'vitest';
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';

const root = new URL('../..', import.meta.url).pathname;
const jsDir = join(root, 'static/js');
const file = path => readFileSync(join(root, path), 'utf8');

function storage() {
  const values = new Map();
  return {
    getItem: key => values.has(key) ? values.get(key) : null,
    setItem: (key, value) => values.set(key, String(value)),
    removeItem: key => values.delete(key),
    clear: () => values.clear(),
  };
}

function node(id = '') {
  return {
    id,
    classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
    style: { setProperty() {} },
    dataset: {},
    appendChild() {},
    addEventListener() {},
    removeEventListener() {},
    setAttribute() {},
    querySelector() { return null; },
    querySelectorAll() { return []; },
    blur() {},
    click() {},
    getContext() { return null; },
    textContent: '',
    innerHTML: '',
    value: '',
  };
}

beforeAll(() => {
  globalThis.location = { origin: 'http://127.0.0.1:8000' };
  globalThis.sessionStorage = storage();
  globalThis.window = globalThis;
  globalThis.document = {
    body: node('body'),
    head: node('head'),
    activeElement: null,
    getElementById: id => node(id),
    createElement: tag => node(tag),
    querySelector: () => null,
    querySelectorAll: () => [],
    addEventListener() {},
    dispatchEvent() {},
  };
  globalThis.CustomEvent = class CustomEvent {
    constructor(type, init = {}) {
      this.type = type;
      this.detail = init.detail;
    }
  };
  globalThis.fetch = vi.fn(async () => ({
    ok: true,
    json: async () => ({ maps: { indoor: { zones: [] }, outdoor: { zones: [] } } }),
  }));
  globalThis.alert = vi.fn();
  globalThis.confirm = vi.fn(() => true);
  globalThis.navigator = { clipboard: { writeText: vi.fn() } };
});

describe('C1-F commander modules', () => {
  test('ws_connects_and_sends', async () => {
    const ws = await import('../../static/js/ws.js');
    expect(typeof ws.connect).toBe('function');
    expect(ws.send({ type: 'noop' })).toBe(false);
    expect(typeof ws.onMessage).toBe('function');
  });

  test('map_initialises_without_error', async () => {
    const map = await import('../../static/js/map.js');
    await expect(map.initMap()).resolves.toBeUndefined();
    expect(map.getMapConfig()).toEqual({ maps: { indoor: { zones: [] }, outdoor: { zones: [] } } });
  });

  test('events_crud_renders', async () => {
    const events = await import('../../static/js/events.js');
    expect(events._evTypeLabel({ event_type: 'mci' })).toContain('大量傷亡');
    expect(events._parseNotes('[{\"note\":\"ok\"}]')).toEqual([{ note: 'ok' }]);
  });

  test('auth_logout_clears_session', async () => {
    const auth = await import('../../static/js/auth.js');
    sessionStorage.setItem('cmd_session_id', 'token');
    sessionStorage.setItem('cmd_username', 'admin');
    auth.clearSession();
    expect(auth.getToken()).toBeNull();
    expect(sessionStorage.getItem('cmd_username')).toBeNull();
  });

  test('charts_renders_with_chart_utils_data', async () => {
    const charts = await import('../../static/js/charts.js');
    const series = charts.getApiSeries({
      shelter_history: [{ snapshot_time: '2026-04-28T00:00:00Z', bed_used: 9, bed_total: 10, extra: '{}' }],
      medical_history: [{ snapshot_time: '2026-04-28T00:00:00Z', bed_used: 4, bed_total: 5, extra: '{}' }],
    });
    expect(series.sPct).toEqual([90]);
    expect(series.mPct).toEqual([80]);
    expect(charts.ipiCalc(2, 3)).toBe(9);
  });

  test('ai_stub_exports_frozen_object_with_marker', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const mod = await import('../../static/js/ai.js');
    expect(warn).toHaveBeenCalledWith('[ICS_DMAS] ai.js stub - not implemented');
    expect(mod.default).toEqual({ __stub: true });
    expect(Object.isFrozen(mod.default)).toBe(true);
    warn.mockRestore();
  });

  test('ttx_stub_exports_frozen_object_with_marker', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const mod = await import('../../static/js/ttx.js');
    expect(warn).toHaveBeenCalledWith('[ICS_DMAS] ttx.js stub - not implemented');
    expect(mod.default).toEqual({ __stub: true });
    expect(Object.isFrozen(mod.default)).toBe(true);
    warn.mockRestore();
  });

  test('module_boundaries_enforced', () => {
    const modules = Object.fromEntries(
      readdirSync(jsDir).filter(name => name.endsWith('.js')).map(name => [name, file(`static/js/${name}`)])
    );
    expect(modules['auth.js']).not.toMatch(/^import\s/m);
    expect([...modules['ws.js'].matchAll(/from\s+['"]([^'"]+)['"]/g)].map(m => m[1])).toEqual(['./auth.js']);
    for (const name of ['map.js', 'events.js', 'decisions.js', 'charts.js']) {
      const imports = [...modules[name].matchAll(/from\s+['"]([^'"]+)['"]/g)].map(m => m[1]);
      expect(imports.every(spec => spec === './ws.js')).toBe(true);
    }
    expect(modules['cop.js']).toMatch(/from '\.\/ws\.js'/);
    expect(modules['cop.js']).toMatch(/from '\.\/map\.js'/);
    expect(modules['ai.js']).not.toMatch(/^import\s/m);
    expect(modules['ttx.js']).not.toMatch(/^import\s/m);
  });

  test('cmd_version_from_api_version', () => {
    const html = file('static/commander_dashboard.html');
    const main = file('static/js/main.js');
    expect(html).not.toMatch(/CMD_VERSION/);
    expect(main).toMatch(/\/api\/version/);
    expect(main).toMatch(/cmd_version/);
  });
});
