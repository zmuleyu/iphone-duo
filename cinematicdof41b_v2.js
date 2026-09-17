import * as THREE from 'three';

// Step 4.1B — True Depth-Aware Near DOF (v2)
//
// Load ORDER matters: this module must load BEFORE motionblur381.js.
// That makes depth-aware DOF the base scene render, while Step 3.8.1 can still
// composite its moving-shell directional blur afterward.
//
// Goals:
// - fixed/right half defines the focus plane
// - moving foreground screen becomes progressively defocused as it comes closer
// - blur strength is driven by real scene depth, not a 2D panel mask
// - hinge side remains relatively sharp while the outer edge becomes more defocused
// - far/background content stays sharp (near-DOF only)
// - Closed and Open return to sharp via an aperture gate

const previousRender = THREE.WebGLRenderer.prototype.render;
const rendererState = new WeakMap();

const FIXED_FOCUS_LOCAL = new THREE.Vector3(3.949675, 0, 0.275454);
const FOCUS_DEADBAND = 0.30;
const NEAR_FULL_BLUR_DISTANCE = 5.5;
const MIN_BLUR_CSS_PX = 14;
const MAX_BLUR_CSS_PX = 20;
const BLUR_RATIO = 0.0155;
const DEBUG_COC = new URLSearchParams(window.location.search).get('dofDebug') === '1';

function smooth01(t) {
  const x = THREE.MathUtils.clamp(t, 0, 1);
  return x * x * (3 - 2 * x);
}

function apertureGate(progress) {
  const p = THREE.MathUtils.clamp(progress, 0, 1);
  if (p <= 0.12) return 0;
  if (p < 0.30) return smooth01((p - 0.12) / 0.18);
  if (p <= 0.82) return 1;
  return 1 - smooth01((p - 0.82) / 0.18);
}

function makeState(renderer) {
  const postScene = new THREE.Scene();
  postScene.userData.skipMotionBlur = true;
  postScene.userData.skipDepthDOF = true;

  const postCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  const material = new THREE.ShaderMaterial({
    transparent: true,
    depthTest: false,
    depthWrite: false,
    uniforms: {
      tColor: { value: null },
      tDepth: { value: null },
      uTexel: { value: new THREE.Vector2(1, 1) },
      uNear: { value: 0.1 },
      uFar: { value: 250 },
      uFocusDistance: { value: 40 },
      uFocusDeadband: { value: FOCUS_DEADBAND },
      uNearFullDistance: { value: NEAR_FULL_BLUR_DISTANCE },
      uMaxBlurPx: { value: 16 },
      uGate: { value: 0 },
      uDebug: { value: DEBUG_COC ? 1 : 0 },
    },
    vertexShader: `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = vec4(position.xy, 0.0, 1.0);
      }
    `,
    fragmentShader: `
      uniform sampler2D tColor;
      uniform sampler2D tDepth;
      uniform vec2 uTexel;
      uniform float uNear;
      uniform float uFar;
      uniform float uFocusDistance;
      uniform float uFocusDeadband;
      uniform float uNearFullDistance;
      uniform float uMaxBlurPx;
      uniform float uGate;
      uniform float uDebug;
      varying vec2 vUv;

      float linearDistance(float depth) {
        return (uNear * uFar) / max(uFar - depth * (uFar - uNear), 0.00001);
      }

      float cocAt(vec2 uv) {
        float depth = texture2D(tDepth, uv).x;
        if (depth >= 0.999999) return 0.0;
        float distanceToCamera = linearDistance(depth);
        float nearDelta = uFocusDistance - distanceToCamera;
        float coc = smoothstep(
          uFocusDeadband,
          uNearFullDistance,
          nearDelta
        );
        return coc * uGate;
      }

      void main() {
        float coc = cocAt(vUv);

        if (uDebug > 0.5) {
          // Black = in focus, red = maximum foreground defocus.
          gl_FragColor = vec4(coc, 0.0, 0.0, 1.0);
          return;
        }

        if (coc < 0.002) {
          gl_FragColor = vec4(0.0);
          return;
        }

        float radius = uMaxBlurPx * coc;
        vec2 px = uTexel * radius;

        // Isotropic bokeh-like sampling. Weights sum to ~1 so DOF does not
        // unintentionally change exposure; view-angle darkening is a later step.
        vec4 c = texture2D(tColor, vUv) * 0.22;
        c += texture2D(tColor, vUv + vec2( 0.00,  0.55) * px) * 0.055;
        c += texture2D(tColor, vUv + vec2( 0.00, -0.55) * px) * 0.055;
        c += texture2D(tColor, vUv + vec2( 0.55,  0.00) * px) * 0.055;
        c += texture2D(tColor, vUv + vec2(-0.55,  0.00) * px) * 0.055;
        c += texture2D(tColor, vUv + vec2( 0.42,  0.42) * px) * 0.050;
        c += texture2D(tColor, vUv + vec2(-0.42,  0.42) * px) * 0.050;
        c += texture2D(tColor, vUv + vec2( 0.42, -0.42) * px) * 0.050;
        c += texture2D(tColor, vUv + vec2(-0.42, -0.42) * px) * 0.050;
        c += texture2D(tColor, vUv + vec2( 0.92,  0.35) * px) * 0.045;
        c += texture2D(tColor, vUv + vec2(-0.92,  0.35) * px) * 0.045;
        c += texture2D(tColor, vUv + vec2( 0.92, -0.35) * px) * 0.045;
        c += texture2D(tColor, vUv + vec2(-0.92, -0.35) * px) * 0.045;
        c += texture2D(tColor, vUv + vec2( 0.35,  0.92) * px) * 0.045;
        c += texture2D(tColor, vUv + vec2(-0.35,  0.92) * px) * 0.045;
        c += texture2D(tColor, vUv + vec2( 0.35, -0.92) * px) * 0.045;
        c += texture2D(tColor, vUv + vec2(-0.35, -0.92) * px) * 0.045;

        // Only the current pixel's near CoC controls the overlay. The already
        // rendered base remains visible underneath for fixed/far regions.
        gl_FragColor = vec4(c.rgb, coc);
      }
    `,
  });

  postScene.add(new THREE.Mesh(new THREE.PlaneGeometry(2, 2), material));

  const target = new THREE.WebGLRenderTarget(4, 4, {
    minFilter: THREE.LinearFilter,
    magFilter: THREE.LinearFilter,
    format: THREE.RGBAFormat,
    depthBuffer: true,
    stencilBuffer: false,
  });
  target.texture.generateMipmaps = false;
  target.depthTexture = new THREE.DepthTexture(4, 4, THREE.UnsignedIntType);
  target.depthTexture.format = THREE.DepthFormat;
  target.depthTexture.type = THREE.UnsignedIntType;

  const state = {
    target,
    postScene,
    postCamera,
    material,
    size: new THREE.Vector2(),
    phone: null,
    busy: false,
    focusWorld: new THREE.Vector3(),
    focusView: new THREE.Vector3(),
  };

  rendererState.set(renderer, state);
  return state;
}

function findPhone(scene, state) {
  if (state.phone) return state.phone;
  let movingShell = null;
  scene.traverse(object => {
    if (!movingShell && object.isMesh && object.userData?.isMovingShell) {
      movingShell = object;
    }
  });
  state.phone = movingShell?.parent || null;
  return state.phone;
}

function ensureTarget(renderer, state) {
  renderer.getDrawingBufferSize(state.size);
  const width = Math.max(2, Math.floor(state.size.x));
  const height = Math.max(2, Math.floor(state.size.y));

  if (state.target.width !== width || state.target.height !== height) {
    state.target.setSize(width, height);
    state.target.depthTexture.image.width = width;
    state.target.depthTexture.image.height = height;
  }

  state.material.uniforms.uTexel.value.set(1 / width, 1 / height);

  const pixelRatio = renderer.getPixelRatio();
  const cssWidth = width / pixelRatio;
  const cssHeight = height / pixelRatio;
  const cssMin = Math.min(cssWidth, cssHeight);
  const maxBlurCss = THREE.MathUtils.clamp(
    cssMin * BLUR_RATIO,
    MIN_BLUR_CSS_PX,
    MAX_BLUR_CSS_PX,
  );
  state.material.uniforms.uMaxBlurPx.value = maxBlurCss * pixelRatio;
}

function focusDistanceFor(scene, camera, state) {
  const phone = findPhone(scene, state);
  if (!phone) return 40;

  phone.updateMatrixWorld(true);
  camera.updateMatrixWorld(true);

  state.focusWorld.copy(FIXED_FOCUS_LOCAL).applyMatrix4(phone.matrixWorld);
  state.focusView.copy(state.focusWorld).applyMatrix4(camera.matrixWorldInverse);
  return Math.max(0.1, -state.focusView.z);
}

THREE.WebGLRenderer.prototype.render = function depthAwareNearDofRender(scene, camera) {
  const state = rendererState.get(this) || makeState(this);

  // Orthographic cameras are post-processing passes (e.g. Step 3.8.1 shell blur),
  // never the physical Duo scene. Skipping them prevents post-process recursion.
  if (
    state.busy
    || this.getRenderTarget() !== null
    || !scene?.isScene
    || camera?.isOrthographicCamera
    || scene?.userData?.skipDepthDOF
  ) {
    return previousRender.call(this, scene, camera);
  }

  const progress = THREE.MathUtils.clamp(
    Number(document.querySelector('#angle')?.value || 0) / 180,
    0,
    1,
  );
  const gate = apertureGate(progress);

  // Base render. If Step 3.8.1 wraps this module, its moving shell may be hidden
  // for this call; that is intentional: DOF treats the moving screen as optical
  // foreground, while Step 3.8.1 composites the velocity-blurred metal shell later.
  const baseResult = previousRender.call(this, scene, camera);

  if (gate < 0.002 && !DEBUG_COC) return baseResult;

  state.busy = true;
  try {
    ensureTarget(this, state);

    const previousTarget = this.getRenderTarget();
    const previousAutoClear = this.autoClear;
    const previousClearColor = this.getClearColor(new THREE.Color()).clone();
    const previousClearAlpha = this.getClearAlpha();

    // Render the real folded scene with its existing custom vertex shaders into
    // color + depth. No override depth material is used, so fold deformation and
    // the resulting depth remain consistent.
    this.setRenderTarget(state.target);
    this.setClearColor(0x000000, 0);
    this.autoClear = true;
    this.clear(true, true, true);
    previousRender.call(this, scene, camera);

    this.setRenderTarget(previousTarget);
    this.setClearColor(previousClearColor, previousClearAlpha);
    this.autoClear = false;

    state.material.uniforms.tColor.value = state.target.texture;
    state.material.uniforms.tDepth.value = state.target.depthTexture;
    state.material.uniforms.uNear.value = camera.near;
    state.material.uniforms.uFar.value = camera.far;
    state.material.uniforms.uFocusDistance.value = focusDistanceFor(scene, camera, state);
    state.material.uniforms.uGate.value = gate;

    previousRender.call(this, state.postScene, state.postCamera);

    this.autoClear = previousAutoClear;
  } finally {
    state.busy = false;
  }

  return baseResult;
};

console.info('Step 4.1B v2 true depth-aware near DOF ready', {
  focus: 'fixed-right-half',
  nearOnly: true,
  maxBlurCssRange: [MIN_BLUR_CSS_PX, MAX_BLUR_CSS_PX],
  focusDeadband: FOCUS_DEADBAND,
  nearFullBlurDistance: NEAR_FULL_BLUR_DISTANCE,
  loadOrder: 'DOF -> motion blur -> main',
  debug: DEBUG_COC,
});
