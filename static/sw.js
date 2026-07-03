// Service worker — install support + force-update, network-only for fetch
// (LifeLog's pattern: a stale cached shell is worse than an offline error for
// a private single-server app). The /sw.js route stamps a build marker below,
// so each deploy byte-changes this file → the browser installs a new SW → on
// a genuine UPDATE we reload controlled windows, so home-screen installs pick
// up the new shell on next launch without a manual re-add.
let _isUpdate = false;
self.addEventListener('install', () => { _isUpdate = !!self.registration.active; self.skipWaiting(); });
self.addEventListener('activate', (e) => e.waitUntil((async () => {
  await self.clients.claim();
  if (_isUpdate) {
    for (const c of await self.clients.matchAll({ type: 'window' })) {
      try { c.navigate(c.url); } catch (err) {}
    }
  }
})()));
self.addEventListener('fetch', () => { /* pass through to network */ });
