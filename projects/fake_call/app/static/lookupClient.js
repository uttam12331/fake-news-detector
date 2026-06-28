// Number-lookup transport. The provider (Numverify-compatible) has no CORS
// support, so a direct browser fetch() would be blocked by the browser
// itself. In the web app we route through our own Flask proxy (/api/lookup).
// Inside the Android WebView wrapper there's no backend to proxy through, so
// MainActivity exposes a JavascriptInterface ("AndroidLookup") that performs
// the HTTP call natively (not subject to browser CORS) and calls back here.
let callbackSeq = 0;
const pending = new Map();

window.__lookupCallback = (id, result) => {
  const resolve = pending.get(id);
  if (resolve) {
    pending.delete(id);
    resolve(result);
  }
};

export async function performLookup(number, apiKey) {
  if (window.AndroidLookup && window.AndroidLookup.lookupNumber) {
    return new Promise((resolve) => {
      const id = String(++callbackSeq);
      pending.set(id, resolve);
      window.AndroidLookup.lookupNumber(number, apiKey, id);
    });
  }

  const res = await fetch("/api/lookup", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ number, apiKey }),
  });
  return res.json();
}
