// Step 4.1D v2 cache-safe bootstrap.
// Every child module gets a unique build query so browser/CDN module caches
// cannot reuse an older main.js / transition module after a new deployment.
const BUILD_ID = 'step41d-v2-cachefix-20260917-2308';

globalThis.__IPHONE_DUO_BUILD__ = BUILD_ID;
document.documentElement.dataset.build = BUILD_ID;
console.info('iPhone Duo build', BUILD_ID);

await import(`./motionblur381.js?build=${BUILD_ID}`);
await import(`./main.js?build=${BUILD_ID}`);
await import(`./worldtransition41d_v2.js?build=${BUILD_ID}`);
