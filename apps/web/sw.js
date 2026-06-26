const CACHE = 'arbotflash-v0-12-authority-slice-80';
const CORE = [
  './', './index.html', './styles.css', './app.js', './offline-db.js', './manifest.webmanifest',
  './data/treeid-seed-80.json', './data/filter-definitions.json',
  '/admin/', '/admin/index.html', '/admin/styles.css', '/admin/app.js',
  './media/thumbs/treeid-acacia-acuminata.jpg',
  './media/thumbs/treeid-acacia-cyclops.jpg',
  './media/thumbs/treeid-acacia-dealbata.jpg',
  './media/thumbs/treeid-acacia-drummondii.jpg',
  './media/thumbs/treeid-acacia-melanoxylon.jpg',
  './media/thumbs/treeid-acacia-saligna.jpg',
  './media/thumbs/treeid-acer-palmatum.jpg',
  './media/thumbs/treeid-agonis-flexuosa.jpg',
  './media/thumbs/treeid-allocasuarina-fraseriana.jpg',
  './media/thumbs/treeid-allocasuarina-littoralis.jpg',
  './media/thumbs/treeid-angophora-costata.jpg',
  './media/thumbs/treeid-araucaria-bidwillii.jpg',
  './media/thumbs/treeid-araucaria-heterophylla.jpg',
  './media/thumbs/treeid-backhousia-citriodora.jpg',
  './media/thumbs/treeid-banksia-attenuata.jpg',
  './media/thumbs/treeid-banksia-grandis.jpg',
  './media/thumbs/treeid-banksia-ilicifolia.jpg',
  './media/thumbs/treeid-banksia-littoralis.jpg',
  './media/thumbs/treeid-banksia-menziesii.jpg',
  './media/thumbs/treeid-banksia-prionotes.jpg',
  './media/thumbs/treeid-brachychiton-acerifolius.jpg',
  './media/thumbs/treeid-brachychiton-populneus.jpg',
  './media/thumbs/treeid-callistemon-citrinus.jpg',
  './media/thumbs/treeid-callistemon-viminalis.jpg',
  './media/thumbs/treeid-callitris-columellaris.jpg',
  './media/thumbs/treeid-casuarina-cunninghamiana.jpg',
  './media/thumbs/treeid-cedrus-deodara.jpg',
  './media/thumbs/treeid-cinnamomum-camphora.jpg',
  './media/thumbs/treeid-corymbia-calophylla.jpg',
  './media/thumbs/treeid-corymbia-citriodora.jpg',
  './media/thumbs/treeid-corymbia-haematoxylon.jpg',
  './media/thumbs/treeid-corymbia-maculata.jpg',
  './media/thumbs/treeid-cupressus-sempervirens.jpg',
  './media/thumbs/treeid-eucalyptus-accedens.jpg',
  './media/thumbs/treeid-eucalyptus-camaldulensis.jpg',
  './media/thumbs/treeid-eucalyptus-cladocalyx.jpg',
  './media/thumbs/treeid-eucalyptus-diversicolor.jpg',
  './media/thumbs/treeid-eucalyptus-globulus.jpg',
  './media/thumbs/treeid-eucalyptus-gomphocephala.jpg',
  './media/thumbs/treeid-eucalyptus-grandis.jpg',
  './media/thumbs/treeid-eucalyptus-guilfoylei.jpg',
  './media/thumbs/treeid-eucalyptus-jacksonii.jpg',
  './media/thumbs/treeid-eucalyptus-lehmannii.jpg',
  './media/thumbs/treeid-eucalyptus-marginata.jpg',
  './media/thumbs/treeid-eucalyptus-megacarpa.jpg',
  './media/thumbs/treeid-eucalyptus-mooreana.jpg',
  './media/thumbs/treeid-eucalyptus-patens.jpg',
  './media/thumbs/treeid-eucalyptus-pleurocarpa.jpg',
  './media/thumbs/treeid-eucalyptus-rudis.jpg',
  './media/thumbs/treeid-eucalyptus-sideroxylon.jpg',
  './media/thumbs/treeid-eucalyptus-victrix.jpg',
  './media/thumbs/treeid-eucalyptus-wandoo.jpg',
  './media/thumbs/treeid-eucalyptus-youngiana.jpg',
  './media/thumbs/treeid-fraxinus-angustifolia.jpg',
  './media/thumbs/treeid-fraxinus-excelsior.jpg',
  './media/thumbs/treeid-ginkgo-biloba.jpg',
  './media/thumbs/treeid-grevillea-robusta.jpg',
  './media/thumbs/treeid-hakea-laurina.jpg',
  './media/thumbs/treeid-hakea-prostrata.jpg',
  './media/thumbs/treeid-jacaranda-mimosifolia.jpg',
  './media/thumbs/treeid-liquidambar-styraciflua.jpg',
  './media/thumbs/treeid-magnolia-grandiflora.jpg',
  './media/thumbs/treeid-melaleuca-lanceolata.jpg',
  './media/thumbs/treeid-melaleuca-preissiana.jpg',
  './media/thumbs/treeid-melaleuca-quinquenervia.jpg',
  './media/thumbs/treeid-melaleuca-rhaphiophylla.jpg',
  './media/thumbs/treeid-nuytsia-floribunda.jpg',
  './media/thumbs/treeid-pinus-pinea.jpg',
  './media/thumbs/treeid-pinus-radiata.jpg',
  './media/thumbs/treeid-xanthorrhoea-preissii.jpg',
  './media/thumbs/treeid-acacia-websteriana.jpg',
  './media/thumbs/treeid-corymbia-eximia.jpg',
  './media/thumbs/treeid-eucalyptus-norsemanica.jpg',
  './media/thumbs/treeid-lophostemon-confertus.jpg',
  './media/thumbs/treeid-platanus-acerifolia.jpg',
  './media/thumbs/treeid-populus-alba.jpg',
  './media/thumbs/treeid-syzygium-australe.jpg',
  './media/thumbs/treeid-tristaniopsis-laurina.jpg',
  './media/thumbs/treeid-ulmus-procera.jpg',
  './media/thumbs/treeid-washingtonia-robusta.jpg'
];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(CORE)));
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(
    keys.filter(key => key.startsWith('arbotflash-') && key !== CACHE).map(key => caches.delete(key))
  )));
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  const url = new URL(event.request.url);
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(event.request).then(response => {
        if (response.ok) caches.open(CACHE).then(cache => cache.put(event.request, response.clone()));
        return response;
      }).catch(() => caches.match(event.request))
    );
    return;
  }
  event.respondWith(
    caches.match(event.request).then(cached => cached || fetch(event.request).then(response => {
      if (response.ok) caches.open(CACHE).then(cache => cache.put(event.request, response.clone()));
      return response;
    }))
  );
});
