const CACHE_NAME="tree-id-trainer-hosted-v23";
const CORE=["/","/index.html","/app.webmanifest","/icons/icon-192.png","/icons/icon-512.png","/icons/favicon-32.png","/icons/favicon-64.png","/icons/apple-touch-icon.png","/header-art.png","/theme-assets/journal/family.webp","/theme-assets/journal/flash.webp","/theme-assets/journal/header.webp","/theme-assets/journal/logo.webp","/theme-assets/journal/name.webp","/theme-assets/journal/tutorial.webp","/theme-assets/moonlit/family.webp","/theme-assets/moonlit/flash.webp","/theme-assets/moonlit/header.webp","/theme-assets/moonlit/logo.webp","/theme-assets/moonlit/name.webp","/theme-assets/moonlit/tutorial.webp","/theme-assets/mystical/family.webp","/theme-assets/mystical/flash.webp","/theme-assets/mystical/header.webp","/theme-assets/mystical/logo.webp","/theme-assets/mystical/name.webp","/theme-assets/mystical/tutorial.webp","/theme-assets/reddirt/family.webp","/theme-assets/reddirt/flash.webp","/theme-assets/reddirt/header.webp","/theme-assets/reddirt/logo.webp","/theme-assets/reddirt/name.webp","/theme-assets/reddirt/tutorial.webp"];

self.addEventListener("install",event=>{
  event.waitUntil(caches.open(CACHE_NAME).then(cache=>cache.addAll(CORE)));
  self.skipWaiting();
});

self.addEventListener("activate",event=>{
  event.waitUntil(
    caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE_NAME).map(k=>caches.delete(k))))
  );
  self.clients.claim();
});

self.addEventListener("fetch",event=>{
  const request=event.request;
  const url=new URL(request.url);

  if(url.pathname.startsWith("/api/"))return;

  if(request.mode==="navigate"){
    event.respondWith(
      fetch(request)
        .then(response=>{
          const copy=response.clone();
          caches.open(CACHE_NAME).then(cache=>cache.put("/index.html",copy));
          return response;
        })
        .catch(()=>caches.match("/index.html"))
    );
    return;
  }

  event.respondWith(
    caches.match(request).then(cached=>{
      if(cached)return cached;
      return fetch(request).then(response=>{
        if(request.method==="GET" && response.ok){
          const copy=response.clone();
          caches.open(CACHE_NAME).then(cache=>cache.put(request,copy));
        }
        return response;
      });
    })
  );
});
