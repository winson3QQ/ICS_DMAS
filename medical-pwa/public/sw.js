/* ════════════════════════════════════════════════════════════════════
   醫療組 PWA — sw.js
   Service Worker：離線快取（Offline First）
   策略：Cache First（本地），Network First（外部 CDN）
   ════════════════════════════════════════════════════════════════════ */
'use strict';

const CACHE_NAME = 'medical-pwa-v0.8.2-alpha';
const STATIC_ASSETS = [
  './medical_pwa.html',
  './sw.js',
  './manifest.json',
  './lib/dexie.min.js',
  './lib/papaparse.min.js',
  './lib/qrcode.js',
];

self.addEventListener('install', event => {
  console.log('[SW medical] install', CACHE_NAME);
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(STATIC_ASSETS).catch(e => {
        console.warn('[SW medical] Cache partial failure:', e);
      });
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  console.log('[SW medical] activate', CACHE_NAME);
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => {
        console.log('[SW medical] Removing old cache:', k);
        return caches.delete(k);
      }));
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (url.protocol === 'ws:' || url.protocol === 'wss:') return;
  if (event.request.method !== 'GET') return;

  // 外部 CDN 資源：Network First（Dexie、PapaParse、qrcode）
  if (url.origin !== self.location.origin) {
    event.respondWith(
      fetch(event.request).then(resp => {
        if (resp && resp.status === 200) {
          const clone = resp.clone();
          caches.open(CACHE_NAME).then(c => c.put(event.request, clone));
        }
        return resp;
      }).catch(() => {
        return caches.match(event.request).then(cached => {
          return cached || new Response('', { status: 503, statusText: 'Offline' });
        });
      })
    );
    return;
  }

  // 本地資源：Cache First
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

// 接收主頁面指令（動態快取更新）
self.addEventListener('message', event => {
  if (event.data && event.data.type === 'CACHE_UPDATE') {
    caches.open(CACHE_NAME).then(cache => {
      cache.add(event.data.url).catch(e => console.warn('[SW medical] CACHE_UPDATE failed:', e));
    });
  }
});
