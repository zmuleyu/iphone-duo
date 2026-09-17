import * as THREE from 'three';

// Step 4.1C — Physical Layer Cross-Transition
//
// Default Tokyo Tower transition model:
// - OUTER / COVER display = Reality only
// - INNER foldable display = RedBlack only
// - Reality exits via blur + darken + fade
// - RedBlack enters via fade-in + sharpen
// - the old right-to-left spatial reveal remains available only with ?transition=spatial
//
// This module intentionally does NOT change fold geometry, framing, or motion blur.

const params = new URLSearchParams(window.location.search);
const physicalEnabled = params.get('transition') !== 'spatial';

const previousRender = THREE.WebGLRenderer.prototype.render;
const rendererState = new WeakMap();

const INNER_NAME = 'UXtsBZYlaUvHoEh';
const OUTER_NAME = 'hhgAIoCGsHXeDPY';

const INNER_W = 1600;
const INNER_H = 1125;
const OUTER_W = 800;
const OUTER_H = 1125;

const REALITY_BLUR_LEVELS = [0, 2, 4, 8, 12, 16, 20];
const REDBLACK_BLUR_LEVELS = [0, 2, 4, 8, 12, 16];

const assets = {
  realityReady: false,
  redblackReady: false,
  realityOuter: [],
  redblackInner: [],
};

function smooth01(t) {
  const x = THREE.MathUtils.clamp(t, 0, 1);
  return x * x * (3 - 2 * x);
}

function sampleCurve(progress, points) {
  const p = THREE.MathUtils.clamp(progress, 0, 1);
  if (p <= points[0][0]) return points[0][1];
  for (let i = 0; i < points.length - 1; i++) {
    const [p0, v0] = points[i];
    const [p1, v1] = points[i + 1];
    if (p <= p1) {
      const raw = (p - p0) / Math.max(p1 - p0, 1e-6);
      return THREE.MathUtils.lerp(v0, v1, smooth01(raw));
    }
  }
  return points[points.length - 1][1];
}

const OUTER_OPACITY = [
  [0.00, 1.00],
  [0.15, 1.00],
  [0.35, 0.80],
  [0.50, 0.50],
  [0.65, 0.20],
  [0.75, 0.05],
  [0.80, 0.00],
  [1.00, 0.00],
];

const OUTER_BLUR = [
  [0.00, 0.0],
  [0.15, 0.0],
  [0.25, 2.0],
  [0.35, 4.0],
  [0.50, 10.0],
  [0.65, 14.0],
  [0.75, 18.0],
  [0.80, 20.0],
  [1.00, 20.0],
];

const OUTER_BRIGHTNESS = [
  [0.00, 1.00],
  [0.20, 1.00],
  [0.35, 0.90],
  [0.50, 0.75],
  [0.65, 0.60],
  [0.75, 0.50],
  [1.00, 0.50],
];

const INNER_OPACITY = [
  [0.00, 0.00],
  [0.12, 0.00],
  [0.20, 0.10],
  [0.35, 0.40],
  [0.50, 0.78],
  [0.60, 0.95],
  [0.70, 1.00],
  [1.00, 1.00],
];

const INNER_BLUR = [
  [0.00, 16.0],
  [0.20, 16.0],
  [0.35, 8.0],
  [0.50, 4.0],
  [0.60, 1.0],
  [0.70, 0.0],
  [1.00, 0.0],
];

const INNER_BRIGHTNESS = [
  [0.00, 0.82],
  [0.20, 0.84],
  [0.35, 0.90],
  [0.50, 0.96],
  [0.65, 1.00],
  [1.00, 1.00],
];

function makeCanvas(width, height) {
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  return canvas;
}

function fitArtwork(img) {
  const canvas = makeCanvas(INNER_W, INNER_H);
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#101418';
  ctx.fillRect(0, 0, INNER_W, INNER_H);

  const scale = Math.min(INNER_W / img.width, INNER_H / img.height);
  const width = img.width * scale;
  const height = img.height * scale;
  ctx.drawImage(
    img,
    (INNER_W - width) / 2,
    (INNER_H - height) / 2,
    width,
    height,
  );
  return canvas;
}

function makeBlurredCanvas(source, width, height, blurPx, cropX = 0, cropW = source.width) {
  const canvas = makeCanvas(width, height);
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#101418';
  ctx.fillRect(0, 0, width, height);
  ctx.save();
  ctx.filter = blurPx > 0 ? `blur(${blurPx}px)` : 'none';

  // A slight overscan prevents transparent edge loss from canvas blur.
  const pad = blurPx > 0 ? Math.ceil(blurPx * 1.7) : 0;
  ctx.drawImage(
    source,
    cropX - pad,
    -pad,
    cropW + pad * 2,
    source.height + pad * 2,
    -pad,
    -pad,
    width + pad * 2,
    height + pad * 2,
  );
  ctx.restore();
  return canvas;
}

function textureFromCanvas(canvas) {
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.wrapS = THREE.ClampToEdgeWrapping;
  texture.wrapT = THREE.ClampToEdgeWrapping;
  texture.generateMipmaps = false;
  texture.minFilter = THREE.LinearFilter;
  texture.magFilter = THREE.LinearFilter;
  return texture;
}

function disposeTextureSet(set) {
  set.forEach(entry => entry.texture.dispose());
  set.length = 0;
}

function nearestTexture(set, blurPx) {
  if (!set.length) return null;
  let best = set[0];
  let bestDistance = Math.abs(best.blur - blurPx);
  for (let i = 1; i < set.length; i++) {
    const distance = Math.abs(set[i].blur - blurPx);
    if (distance < bestDistance) {
      best = set[i];
      bestDistance = distance;
    }
  }
  return best.texture;
}

async function decodeFile(file) {
  const url = URL.createObjectURL(file);
  const img = new Image();
  img.src = url;
  try {
    await img.decode();
    return img;
  } finally {
    URL.revokeObjectURL(url);
  }
}

async function buildRealityTextures(file) {
  const img = await decodeFile(file);
  const full = fitArtwork(img);

  disposeTextureSet(assets.realityOuter);
  for (const blur of REALITY_BLUR_LEVELS) {
    const canvas = makeBlurredCanvas(
      full,
      OUTER_W,
      OUTER_H,
      blur,
      INNER_W / 2,
      INNER_W / 2,
    );
    assets.realityOuter.push({ blur, texture: textureFromCanvas(canvas) });
  }
  assets.realityReady = true;
}

async function buildRedBlackTextures(file) {
  const img = await decodeFile(file);
  const full = fitArtwork(img);

  disposeTextureSet(assets.redblackInner);
  for (const blur of REDBLACK_BLUR_LEVELS) {
    const canvas = makeBlurredCanvas(
      full,
      INNER_W,
      INNER_H,
      blur,
      0,
      INNER_W,
    );
    assets.redblackInner.push({ blur, texture: textureFromCanvas(canvas) });
  }
  assets.redblackReady = true;
}

const realityInput = document.querySelector('#ui-upload');
const redblackInput = document.querySelector('#redblack-upload');

if (realityInput) {
  realityInput.addEventListener('change', () => {
    const file = realityInput.files?.[0];
    if (!file) return;
    buildRealityTextures(file).catch(error => {
      console.error('Step 4.1C Reality texture preparation failed', error);
    });
  });
}

if (redblackInput) {
  redblackInput.addEventListener('change', () => {
    const file = redblackInput.files?.[0];
    if (!file) return;
    buildRedBlackTextures(file).catch(error => {
      console.error('Step 4.1C RedBlack texture preparation failed', error);
    });
  });
}

function makeState() {
  return {
    inner: null,
    outer: null,
    patchedInner: false,
    patchedOuter: false,
    lastInnerMap: null,
    lastOuterMap: null,
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

function neutralizeSpatialReveal(mesh, stateKey) {
  if (!mesh?.material || mesh.material.userData?.physicalLayerWrapped) return;

  const material = mesh.material;
  const originalCompile = material.onBeforeCompile;
  material.onBeforeCompile = shader => {
    if (originalCompile) originalCompile(shader);
    material.userData.physicalLayerShader = shader;
    if (shader.uniforms.transitionMix) shader.uniforms.transitionMix.value = 0;
    if (shader.uniforms.transitionSpatialMode) shader.uniforms.transitionSpatialMode.value = 0;
    if (shader.uniforms.transitionTarget && material.map) {
      shader.uniforms.transitionTarget.value = material.map;
    }
  };
  material.customProgramCacheKey = () => `physical-layer-${stateKey}-41c`;
  material.userData.physicalLayerWrapped = true;
  material.needsUpdate = true;
}

function forceSpatialRevealOff(mesh) {
  const shader = mesh?.material?.userData?.physicalLayerShader;
  if (!shader) return;
  if (shader.uniforms.transitionMix) shader.uniforms.transitionMix.value = 0;
  if (shader.uniforms.transitionSpatialMode) shader.uniforms.transitionSpatialMode.value = 0;
  if (shader.uniforms.transitionTarget && mesh.material.map) {
    shader.uniforms.transitionTarget.value = mesh.material.map;
  }
}

function applyMaterialState(mesh, map, opacity, brightness, renderOrder) {
  if (!mesh?.material || !map) return;
  const material = mesh.material;

  if (material.map !== map) material.map = map;
  material.transparent = true;
  material.depthTest = true;
  material.depthWrite = false;
  material.opacity = THREE.MathUtils.clamp(opacity, 0, 1);
  material.color.setScalar(THREE.MathUtils.clamp(brightness, 0, 1.2));
  mesh.renderOrder = renderOrder;
}

function updatePhysicalLayers(scene, state) {
  if (!physicalEnabled || !assets.realityReady || !assets.redblackReady) return;
  if (!findScreens(scene, state)) return;

  neutralizeSpatialReveal(state.inner, 'inner');
  neutralizeSpatialReveal(state.outer, 'outer');

  const progress = THREE.MathUtils.clamp(
    Number(document.querySelector('#angle')?.value || 0) / 180,
    0,
    1,
  );

  const outerOpacity = sampleCurve(progress, OUTER_OPACITY);
  const outerBlur = sampleCurve(progress, OUTER_BLUR);
  const outerBrightness = sampleCurve(progress, OUTER_BRIGHTNESS);

  const innerOpacity = sampleCurve(progress, INNER_OPACITY);
  const innerBlur = sampleCurve(progress, INNER_BLUR);
  const innerBrightness = sampleCurve(progress, INNER_BRIGHTNESS);

  const realityMap = nearestTexture(assets.realityOuter, outerBlur);
  const redblackMap = nearestTexture(assets.redblackInner, innerBlur);

  // The inner foldable display sits behind the cover during the hand-off.
  applyMaterialState(state.inner, redblackMap, innerOpacity, innerBrightness, 10);
  applyMaterialState(state.outer, realityMap, outerOpacity, outerBrightness, 20);

  forceSpatialRevealOff(state.inner);
  forceSpatialRevealOff(state.outer);

  document.documentElement.dataset.transitionMode = 'physical';
  document.documentElement.style.setProperty('--physical-reality-opacity', outerOpacity.toFixed(3));
  document.documentElement.style.setProperty('--physical-inner-opacity', innerOpacity.toFixed(3));
}

THREE.WebGLRenderer.prototype.render = function physicalLayerRender(scene, camera) {
  const state = rendererState.get(this) || makeState();
  if (!rendererState.has(this)) rendererState.set(this, state);

  if (
    physicalEnabled
    && this.getRenderTarget() === null
    && scene?.isScene
    && !scene?.userData?.skipMotionBlur
    && !scene?.userData?.skipDepthDOF
  ) {
    updatePhysicalLayers(scene, state);
  }

  return previousRender.call(this, scene, camera);
};

console.info('Step 4.1C physical layer cross-transition ready', {
  enabled: physicalEnabled,
  outerLayer: 'Reality blur + darken + fade out',
  innerLayer: 'RedBlack fade in + sharpen',
  spatialRevealDefault: false,
  legacySpatialMode: '?transition=spatial',
  framingUntouched: true,
  motionBlurUntouched: true,
});
