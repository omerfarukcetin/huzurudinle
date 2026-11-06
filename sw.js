// Sesli Kitap Rafı — service worker
// 1) Uygulama kabuğunu önbelleğe alır: site hızlı ve internet zayıfken de açılır (sesler her zaman internetten gelir).
// 2) Günlük hatırlatma: tarayıcı destekliyorsa (Android'de yüklü uygulama) arka planda hedef kontrolü yapar.
// Siteyi güncelleyince aşağıdaki sürümü artırın; eski önbellek silinir.
const VERSION = 'skr-v6';
const SHELL = ['./', 'index.html', 'books.js', 'sync.js', 'firebase-config.js', 'logo.svg', 'manifest.webmanifest',
  'icons/icon-192.png', 'icons/icon-512.png', 'icons/favicon-32.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(VERSION).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k !== VERSION).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return; // MP3'ler, yazı tipi, Firebase: doğrudan internetten

  // Sayfanın kendisi: önce internet (güncel kalsın), yoksa önbellek
  // no-cache: tarayıcının HTTP önbelleğine güvenme, sunucuya "değişti mi?" diye sor
  if (req.mode === 'navigate') {
    e.respondWith(fetch(req, { cache: 'no-cache' }).then(res => {
      const copy = res.clone(); caches.open(VERSION).then(c => c.put('index.html', copy));
      return res;
    }).catch(() => caches.match('index.html')));
    return;
  }
  // Betikler ve kitap listesi (books.js vb.): önce internet, böylece güncellemeler hemen görünür
  if (req.destination !== 'image') {
    e.respondWith(fetch(req, { cache: 'no-cache' }).then(res => {
      if (res.ok) { const copy = res.clone(); caches.open(VERSION).then(c => c.put(req, copy)); }
      return res;
    }).catch(() => caches.match(req, { ignoreSearch: true })));
    return;
  }
  // Kapaklar ve simgeler: önbellekten hemen ver, arkada yenile
  e.respondWith(caches.open(VERSION).then(async c => {
    const hit = await c.match(req);
    const net = fetch(req).then(res => { if (res.ok) c.put(req, res.clone()); return res; }).catch(() => hit);
    return hit || net;
  }));
});

// ---------- Günlük hatırlatma ----------
const kv = () => new Promise((res, rej) => {
  const r = indexedDB.open('skr', 1);
  r.onupgradeneeded = () => r.result.createObjectStore('kv');
  r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error);
});
const kvGet = async k => { const db = await kv(); return new Promise(res => { const q = db.transaction('kv').objectStore('kv').get(k); q.onsuccess = () => res(q.result); q.onerror = () => res(undefined); }); };
const kvSet = async (k, v) => { const db = await kv(); return new Promise(res => { const tx = db.transaction('kv', 'readwrite'); tx.objectStore('kv').put(v, k); tx.oncomplete = res; tx.onerror = res; }); };
const today = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; };

async function checkReminder() {
  const r = await kvGet('reminder');
  if (!r || !r.on) return;
  const day = today();
  if (r.notified === day || new Date().getHours() < r.hour) return;
  const sec = r.day === day ? r.sec : 0;
  const goal = (r.goal || 15) * 60;
  if (sec >= goal) return;
  const left = Math.ceil((goal - sec) / 60);
  await self.registration.showNotification('Sesli Kitap Rafı', {
    body: sec > 0 ? `Bugünkü ${r.goal} dakikalık hedefine ${left} dakika kaldı. Kaldığın yerden devam et.` : `Bugün henüz dinlemedin. ${r.goal} dakikalık hedefin seni bekliyor.`,
    icon: 'icons/icon-192.png', badge: 'icons/favicon-32.png', tag: 'skr-reminder', lang: 'tr',
    data: { url: './#calar' }
  });
  await kvSet('reminder', { ...r, notified: day });
}

self.addEventListener('periodicsync', e => { if (e.tag === 'skr-reminder') e.waitUntil(checkReminder()); });
self.addEventListener('message', e => { if (e.data === 'check-reminder') e.waitUntil(checkReminder()); });

self.addEventListener('notificationclick', e => {
  e.notification.close();
  const target = new URL(e.notification.data?.url || './', self.registration.scope).href;
  e.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
    const open = list.find(c => c.url.startsWith(self.registration.scope));
    if (open) { open.navigate(target).catch(() => {}); return open.focus(); }
    return self.clients.openWindow(target);
  }));
});
