const BUILD_ID = '5.0.1';

globalThis.__IPHONE_DUO_BUILD__ = BUILD_ID;
document.documentElement.dataset.build = BUILD_ID;

function installVersionBadge() {
  const badge = document.createElement('div');
  badge.id = 'build-version-badge';
  badge.textContent = `v${BUILD_ID}`;
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
  document.title = `iPhone Duo · v${BUILD_ID}`;
  return badge;
}

const badge = installVersionBadge();
const summaryLabel = document.querySelector('.reveal-summary > span:not(.reveal-dot)');
if (summaryLabel) summaryLabel.textContent = 'World';
const timelineSubtitle = document.querySelector('.timeline-title-block span');
if (timelineSubtitle) timelineSubtitle.textContent = 'One panorama · original screen shader';
console.info('iPhone Duo build', BUILD_ID);

try {
  // v4.4: single screen-shader authority. No wrappers, no renderer monkey-patches.
  await import(`./motionblur381.js?build=${BUILD_ID}`);
  await import(`./main_v44.js?build=${BUILD_ID}`);
  badge.textContent = `v${BUILD_ID}`;
} catch (error) {
  console.error('iPhone Duo build failed', error);
  badge.textContent = `v${BUILD_ID} · ERROR`;
  badge.style.background = 'rgba(255,235,232,.96)';
  badge.style.color = '#9b2f24';
  badge.style.borderColor = 'rgba(155,47,36,.24)';
  throw error;
}
