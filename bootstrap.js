const BUILD_ID = 'v4.1D.4-20260917-2318';

globalThis.__IPHONE_DUO_BUILD__ = BUILD_ID;
document.documentElement.dataset.build = BUILD_ID;

function installVersionBadge() {
  const badge = document.createElement('div');
  badge.id = 'build-version-badge';
  badge.textContent = `Build ${BUILD_ID}`;
  Object.assign(badge.style, {
    position: 'fixed',
    top: '14px',
    right: '58px',
    zIndex: '10000',
    padding: '5px 9px',
    borderRadius: '999px',
    background: 'rgba(255,255,255,.88)',
    border: '1px solid rgba(74,86,66,.18)',
    color: '#485143',
    font: '600 11px/1.1 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    letterSpacing: '.01em',
    boxShadow: '0 4px 18px rgba(42,52,39,.08)',
    backdropFilter: 'blur(10px)',
    pointerEvents: 'none',
  });
  document.body.appendChild(badge);
  document.title = `iPhone Duo · ${BUILD_ID}`;
}

installVersionBadge();
console.info('iPhone Duo build', BUILD_ID);

// One shader authority: the unified world transition now lives inside main_v41d4.js.
await import(`./motionblur381.js?build=${BUILD_ID}`);
await import(`./main_v41d4.js?build=${BUILD_ID}`);
