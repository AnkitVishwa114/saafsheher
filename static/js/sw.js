// Service worker: makes the site installable and keeps static files available offline.
const CACHE = "saafshehar-v2";
const ASSETS = ["/static/css/app.css", "/static/js/app.js", "/static/img/logo.svg"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});
// Static files: network first so updates show immediately, cached copy when offline.
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || !url.pathname.startsWith("/static/")) return;
  e.respondWith(
    fetch(e.request)
      .then((res) => { if (res.ok) caches.open(CACHE).then((c) => c.put(e.request, res.clone())); return res; })
      .catch(() => caches.match(e.request))
  );
});
