import * as THREE from 'three';

// v4.2 — Geometry-Driven Transition Timing
//
// This module does not replace the v4.1D.4 screen shader. It replaces only the
// timing source. Instead of driving the world hand-off, blur and fade from raw
// Fold Progress percentages, it derives a perceptual geometry signal from the
// cover's opening angle:
//
//   g = 1 - cos(min(angle, 90deg))
//
// The result is intentionally non-linear: small but visible changes begin near
// 15% Fold, then accelerate as the cover approaches edge-on at 50%.

const previousRender = THREE.WebGLRenderer.prototype.render;
const rendererState = new WeakMap();

const INNER_NAME = 'UXtsBZYlaUvHoEh';
const OUTER_NAME = 'hhgAIoCGsHXeDPY';

function smooth01(t) {
  const x = THREE.MathUtils.clamp(t, 0, 1);
  return x * x * (3 - 2 * x);
}

function smoothRange(value, start, end) {
  return smooth01((value - start) / Math.max(end - start, 1e-6));
}

function geometrySignalFromAngle(angleDeg) {
  const visualAngleDeg = Math.min(Math.max(angleDeg, 0), 90);
  const radians = THREE.MathUtils.degToRad(visualAngleDeg);
  return 1 - Math.cos(radians);
}

function signalsFromGeometry(g) {
  return {
    // Earliest signal: a slight Reality warming starts around ~15% Fold.
    preheat: smoothRange(g, 0.04, 0.22),

    // Content hand-off is deliberately broader than the old fixed 30–45% window.
    // Approx values: 20%=3%, 25%=14%, 30%=32%, 35%=57%, 40%=81%, 45%=98%.
    worldMix: smoothRange(g, 0.10, 0.92),

    // Defocus begins subtly before the content change becomes obvious.
    blur: smoothRange(g, 0.05, 0.78),

    // Darkening starts slightly later than blur.
    darken: smoothRange(g, 0.12, 0.88),

    // The cover remains fully present through the early transition and exits late.
    opacity: 1 - smoothRange(g, 0.30, 0.98),
  };
}

function makeState() {
  return {
    inner: null,
    outer: null,
    wrapped: false,
  };
}

function findScreens(scene, state) {
  if (state.inner && state.outer) return true;
  scene.traverse(object => {
    if (!object.isMesh) return;
    if (!state.inner && object.name === INNER_NAME) state.inner = object;
    if (!state.outer && object.name === OUTER_NAME) state.outer = object;
  });
  return Boolean(state.inner && state.outer);
}

function wrapScreenMaterial(mesh, kind) {
  const material = mesh?.material;
  if (!material || material.userData?.geometryTiming42Wrapped) return;

  const originalCompile = material.onBeforeCompile;
  material.onBeforeCompile = shader => {
    if (originalCompile) originalCompile(shader);

    shader.uniforms.preheatSignal42 = { value: 0 };
    shader.uniforms.darkenSignal42 = { value: 0 };

    shader.fragmentShader = `
      uniform float preheatSignal42;
      uniform float darkenSignal42;
      ${shader.fragmentShader}
    `;

    // v4.1D.4 already contains the correct unified Reality/RedBlack shader.
    // Only replace the timing terms, keeping all existing Fixed-UV / LOD / 5x5
    // weighted sampling and hinge-gradient logic intact.
    shader.fragmentShader = shader.fragmentShader.replace(
      'float preheat = smoothstep(0.25, 0.38, foldProgress) * (1.0 - worldMix);',
      'float preheat = preheatSignal42 * (1.0 - worldMix);',
    );

    shader.fragmentShader = shader.fragmentShader.replace(
      'float effect = motion * pow(darkenGradient, 1.35);',
      'float effect = darkenSignal42 * isOuter * pow(darkenGradient, 1.35);',
    );

    material.userData.geometryTiming42Shader = shader;
  };

  const previousKey = material.customProgramCacheKey?.bind(material);
  material.customProgramCacheKey = () => `${previousKey ? previousKey() : 'screen'}-geometry42-${kind}`;
  material.userData.geometryTiming42Wrapped = true;
  material.needsUpdate = true;
}

function updateShader(mesh, values) {
  const shader = mesh?.material?.userData?.geometryTiming42Shader;
  if (!shader) return false;

  // Override the v4.1D.4 progress-driven values immediately before render.
  if (shader.uniforms.worldMix) shader.uniforms.worldMix.value = values.worldMix;
  if (shader.uniforms.coverFx) shader.uniforms.coverFx.value = values.blur;
  if (shader.uniforms.coverOpacity) shader.uniforms.coverOpacity.value = values.opacity;
  if (shader.uniforms.preheatSignal42) shader.uniforms.preheatSignal42.value = values.preheat;
  if (shader.uniforms.darkenSignal42) shader.uniforms.darkenSignal42.value = values.darken;
  return true;
}

function updateVisibleUI(angleDeg, g, signals, active) {
  if (!active) return;

  const worldPercent = Math.round(signals.worldMix * 100);
  const geometryPercent = Math.round(g * 100);
  const revealReadout = document.querySelector('#reveal-readout');
  const revealSummaryValue = document.querySelector('#reveal-summary-value');
  const strategySummary = document.querySelector('#strategy-summary');
  const subtitle = document.querySelector('.timeline-title-block span');

  if (revealReadout) revealReadout.textContent = `World ${worldPercent}%`;
  if (revealSummaryValue) revealSummaryValue.textContent = `${worldPercent}%`;
  if (strategySummary) strategySummary.textContent = `Geo ${geometryPercent}%`;
  if (subtitle) subtitle.textContent = 'Geometry-driven Reality → RedBlack hand-off';

  document.documentElement.dataset.transitionTiming = 'geometry42';
  document.documentElement.style.setProperty('--geometry-signal', g.toFixed(4));
  document.documentElement.style.setProperty('--world-mix', signals.worldMix.toFixed(4));
  document.documentElement.style.setProperty('--cover-opacity', signals.opacity.toFixed(4));
  document.documentElement.style.setProperty('--cover-blur-signal', signals.blur.toFixed(4));
  document.documentElement.style.setProperty('--cover-darken-signal', signals.darken.toFixed(4));
}

THREE.WebGLRenderer.prototype.render = function geometryTiming42Render(scene, camera) {
  const state = rendererState.get(this) || makeState();
  if (!rendererState.has(this)) rendererState.set(this, state);

  if (
    this.getRenderTarget() === null
    && scene?.isScene
    && !scene?.userData?.skipMotionBlur
  ) {
    if (findScreens(scene, state)) {
      wrapScreenMaterial(state.inner, 'inner');
      wrapScreenMaterial(state.outer, 'outer');

      const angleDeg = Number(document.querySelector('#angle')?.value || 0);
      const g = geometrySignalFromAngle(angleDeg);
      const signals = signalsFromGeometry(g);
      const active = document.querySelector('#redblack-button')?.classList.contains('is-loaded')
        || document.querySelector('#redblack-button')?.textContent?.includes('✓');

      if (active) {
        updateShader(state.inner, {
          ...signals,
          blur: 0,
          darken: 0,
          opacity: 1,
        });
        updateShader(state.outer, signals);
        updateVisibleUI(angleDeg, g, signals, true);
      }
    }
  }

  return previousRender.call(this, scene, camera);
};

console.info('iPhone Duo v4.2 geometry-driven timing ready', {
  geometrySignal: '1 - cos(min(angle, 90deg))',
  preheatRange: [0.04, 0.22],
  worldMixRange: [0.10, 0.92],
  blurRange: [0.05, 0.78],
  darkenRange: [0.12, 0.88],
  opacityRange: [0.30, 0.98],
});
