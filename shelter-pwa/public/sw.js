/* ════════════════════════════════════════════════════════════════════
   收容組 PWA v2.1 — sw.js
   Service Worker：離線快取（Offline First）
   策略：Cache First（HTML/CSS/JS），Network First（外部 CDN）
   v2.1 新增：qrcode-generator CDN 快取
   ════════════════════════════════════════════════════════════════════ */
'use strict';

const CACHE_NAME = 'shelter-pwa-v2.2.9';
const STATIC_ASSETS = [
  './shelter_pwa.html',
  './sw.js',
  './lib/dexie.min.js',
  './lib/papaparse.min.js',
  './lib/qrcode.js',
];

/* ── 安裝：快取靜態資源 ── */
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      console.log('[SW v2.1] Caching static assets');
      return cache.addAll(STATIC_ASSETS).catch(e => {
        console.warn('[SW v2.1] Cache partial failure:', e);
      });
    })
  );
  self.skipWaiting();
});

/* ── 啟動：清除舊快取 ── */
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(k => k !== CACHE_NAME).map(k => {
          console.log('[SW v2.1] Removing old cache:', k);
          return caches.delete(k);
        })
      )
    )
  );
  self.clients.claim();
});

/* ── 攔截請求 ── */
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // WebSocket 連線不攔截
  if (url.protocol === 'ws:' || url.protocol === 'wss:') return;

  // POST / 非 GET 不快取
  if (event.request.method !== 'GET') return;

  // 外部 CDN（Dexie, PapaParse, qrcode-generator）：Network First，失敗時用快取
  if (url.origin !== self.location.origin) {
    event.respondWith(
      fetch(event.request)
        .then(resp => {
          const clone = resp.clone();
          caches.open(CACHE_NAME).then(c => c.put(event.request, clone));
          return resp;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  // 本地靜態資源：Cache First
  event.respondWith(
    caches.match(event.request).then(cached => {
      if (cached) return cached;
      return fetch(event.request).then(resp => {
        if (resp && resp.status === 200) {
          const clone = resp.clone();
          caches.open(CACHE_NAME).then(c => c.put(event.request, clone));
        }
        return resp;
      });
    })
  );
});

/* ── 接收來自主頁面的快取更新指令 ── */
self.addEventListener('message', event => {
  if (event.data?.type === 'CACHE_UPDATE') {
    caches.open(CACHE_NAME).then(cache => {
      cache.add('./shelter_pwa_v2.1.html').catch(() => {});
    });
  }
});
