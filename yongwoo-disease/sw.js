/* 예외질환 검색기 서비스 워커 — 인터넷이 없어도 앱이 열리도록 파일을 기기에 보관합니다. */
var CACHE = 'yongwoo-disease-v1.0.0-r1';
var ASSETS = [
  './',
  './index.html',
  './data.js',
  './manifest.webmanifest',
  './icon.svg',
  './icon-192.png',
  './icon-512.png',
  './icon-512-maskable.png'
];

self.addEventListener('install', function (event) {
  event.waitUntil(
    caches.open(CACHE).then(function (cache) {
      return cache.addAll(ASSETS);
    }).then(function () {
      return self.skipWaiting();
    })
  );
});

self.addEventListener('activate', function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.map(function (k) {
        return k === CACHE ? null : caches.delete(k);
      }));
    }).then(function () {
      return self.clients.claim();
    })
  );
});

/* 화면(index.html)은 새 버전을 먼저 확인하고, 없으면 보관본을 씁니다.
   원본 이미지(img/*)는 한 번 본 것을 보관해 다시 열 때 빠르게 보여 줍니다.
   구글 로그인(GIS)·드라이브 API 요청은 캐시하지 않고 네트워크로 보냅니다. */
self.addEventListener('fetch', function (event) {
  var req = event.request;
  if (req.method !== 'GET') return;
  var url = new URL(req.url);
  if (/(^|\.)(google\.com|googleapis\.com|gstatic\.com)$/.test(url.hostname)) return;
  if (url.origin !== self.location.origin) return;

  if (req.mode === 'navigate' || url.pathname.endsWith('/index.html')) {
    event.respondWith(
      fetch(req).then(function (res) {
        var copy = res.clone();
        caches.open(CACHE).then(function (c) { c.put('./index.html', copy); });
        return res;
      }).catch(function () {
        return caches.match('./index.html').then(function (hit) {
          return hit || caches.match('./');
        });
      })
    );
    return;
  }

  event.respondWith(
    caches.match(req).then(function (hit) {
      if (hit) return hit;
      return fetch(req).then(function (res) {
        if (res && res.status === 200 && res.type === 'basic') {
          var copy = res.clone();
          caches.open(CACHE).then(function (c) { c.put(req, copy); });
        }
        return res;
      });
    })
  );
});
