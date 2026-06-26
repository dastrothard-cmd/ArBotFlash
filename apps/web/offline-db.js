const DB_NAME = 'arbotflash-offline-v0-5';
const DB_VERSION = 1;
const PACK_CACHE = 'arbotflash-offline-pack-media-v0-5';

function requestPromise(request) {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

function transactionPromise(transaction) {
  return new Promise((resolve, reject) => {
    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error);
    transaction.onabort = () => reject(transaction.error || new Error('Offline-pack transaction aborted'));
  });
}

async function database() {
  const request = indexedDB.open(DB_NAME, DB_VERSION);
  request.onupgradeneeded = () => {
    const db = request.result;
    if (!db.objectStoreNames.contains('packs')) db.createObjectStore('packs', { keyPath: 'packKey' });
    if (!db.objectStoreNames.contains('taxa')) {
      const store = db.createObjectStore('taxa', { keyPath: 'key' });
      store.createIndex('packKey', 'packKey');
    }
    if (!db.objectStoreNames.contains('profiles')) {
      const store = db.createObjectStore('profiles', { keyPath: 'key' });
      store.createIndex('packKey', 'packKey');
    }
  };
  return requestPromise(request);
}

async function deleteByPack(store, packKey) {
  const index = store.index('packKey');
  const request = index.openKeyCursor(IDBKeyRange.only(packKey));
  return new Promise((resolve, reject) => {
    request.onsuccess = () => {
      const cursor = request.result;
      if (!cursor) { resolve(); return; }
      store.delete(cursor.primaryKey);
      cursor.continue();
    };
    request.onerror = () => reject(request.error);
  });
}

export async function listInstalledPacks() {
  const db = await database();
  const transaction = db.transaction('packs', 'readonly');
  const done = transactionPromise(transaction);
  const items = await requestPromise(transaction.objectStore('packs').getAll());
  await done;
  db.close();
  return items.sort((a, b) => a.title.localeCompare(b.title));
}

export async function loadInstalledPack(packKey) {
  const db = await database();
  const transaction = db.transaction(['packs', 'taxa', 'profiles'], 'readonly');
  const done = transactionPromise(transaction);
  const packRequest = transaction.objectStore('packs').get(packKey);
  const taxaRequest = transaction.objectStore('taxa').index('packKey').getAll(packKey);
  const profilesRequest = transaction.objectStore('profiles').index('packKey').getAll(packKey);
  const [pack, taxaRows, profileRows] = await Promise.all([
    requestPromise(packRequest), requestPromise(taxaRequest), requestPromise(profilesRequest)
  ]);
  await done;
  if (!pack) {
    db.close();
    return null;
  }
  db.close();
  return {
    manifest: pack.manifest,
    installedAt: pack.installedAt,
    taxa: taxaRows.map(row => row.value),
    profiles: Object.fromEntries(profileRows.map(row => [row.taxonId, row.value]))
  };
}

export async function installPack(packKey, apiBase = '/api/packs') {
  const base = `${apiBase}/${encodeURIComponent(packKey)}`;
  const responses = await Promise.all([
    fetch(`${base}/manifest`), fetch(`${base}/taxa`), fetch(`${base}/profiles`)
  ]);
  for (const response of responses) {
    if (!response.ok) throw new Error(`Pack download failed: ${response.status} ${response.statusText}`);
  }
  const [manifest, taxa, profiles] = await Promise.all(responses.map(response => response.json()));
  if (manifest.coverage.taxonCount !== taxa.length) throw new Error('Pack taxon count does not match its manifest');

  const cache = await caches.open(PACK_CACHE);
  const mediaUrls = new Set();
  for (const profile of Object.values(profiles)) {
    for (const media of profile.media || []) {
      if (media.storage_key) {
        media.display_url = media.storage_key;
        mediaUrls.add(media.storage_key);
      }
    }
  }
  await Promise.all([...mediaUrls].map(async url => {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`Could not cache pack media: ${url}`);
    await cache.put(url, response);
  }));

  const db = await database();
  const cleanup = db.transaction(['taxa', 'profiles'], 'readwrite');
  const cleanupDone = transactionPromise(cleanup);
  await Promise.all([
    deleteByPack(cleanup.objectStore('taxa'), packKey),
    deleteByPack(cleanup.objectStore('profiles'), packKey)
  ]);
  await cleanupDone;

  const transaction = db.transaction(['packs', 'taxa', 'profiles'], 'readwrite');
  const writeDone = transactionPromise(transaction);
  transaction.objectStore('packs').put({
    packKey, title: manifest.title, version: manifest.version,
    installedAt: new Date().toISOString(), manifest
  });
  const taxonStore = transaction.objectStore('taxa');
  taxa.forEach(taxon => taxonStore.put({ key: `${packKey}:${taxon.id}`, packKey, taxonId: taxon.id, value: taxon }));
  const profileStore = transaction.objectStore('profiles');
  Object.entries(profiles).forEach(([taxonId, profile]) => profileStore.put({ key: `${packKey}:${taxonId}`, packKey, taxonId, value: profile }));
  await writeDone;
  db.close();
  return { manifest, taxa, profiles };
}

export async function removePack(packKey) {
  const installed = await loadInstalledPack(packKey);
  const mediaUrls = new Set();
  for (const profile of Object.values(installed?.profiles || {})) {
    for (const media of profile.media || []) if (media.storage_key) mediaUrls.add(media.storage_key);
  }
  const cache = await caches.open(PACK_CACHE);
  await Promise.all([...mediaUrls].map(url => cache.delete(url)));

  const db = await database();
  const transaction = db.transaction(['packs', 'taxa', 'profiles'], 'readwrite');
  const done = transactionPromise(transaction);
  transaction.objectStore('packs').delete(packKey);
  const deletions = [
    deleteByPack(transaction.objectStore('taxa'), packKey),
    deleteByPack(transaction.objectStore('profiles'), packKey)
  ];
  await Promise.all(deletions);
  await done;
  db.close();
}
