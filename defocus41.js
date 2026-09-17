import * as THREE from 'three';

// Step 4.1 — Cinematic Foreground Defocus
//
// Adds a progress-driven depth-of-field treatment to the moving foreground half.
// This is intentionally separate from Step 3.8.1 motion blur:
// - motion blur = velocity driven
// - foreground defocus = fold-position / depth driven
//
// The effect is composited only inside a screen-space quad that follows the
// rotating foreground half. The rear RedBlack world and the fixed half remain sharp.

const previousRender = THREE.WebGLRenderer.prototype.render;
const rendererState = new WeakMap();

const HINGE_Z = 0.275454;
const HINGE_X = 0.0;
const MAX_DEFOCUS_PX = 4.5;

function smoothstep01(t) {
  const x = THREE.MathUtils.clamp(t, 0, 1);
  return x * x * (3 - 2 * x);
}

function computeForegroundDefocus(progress) {
  const p = THREE.MathUtils.clamp(progress, 0, 1);

  if (p <= 0.18) return 0;

  if (p <= 0.45) {
    const t = smoothstep01((p - 0.18) / (0.45 - 0.18));
    return THREE.MathUtils.lerp(0, 2.0, t);
  }

  if (p <= 0.72) {
    const t = smoothstep01((p - 0.45) / (0.72 - 0.45));
    return THREE.MathUtils.lerp(2.0, MAX_DEFOCUS_PX, t);
  }

  if (p <= 0.88) {
    const t = smoothstep01((p - 0.72) / (0.88 - 0.72));
    return THREE.MathUtils.lerp(MAX_DEFOCUS_PX, 4.0, t);
  }

  const t = smoothstep01((p - 0.88) / (1.0 - 0.88));
  return THREE.MathUtils.lerp(4.0, 0, t);
}

function makeState(renderer) {
  const postScene = new THREE.Scene();
  postScene.userData.skipMotionBlur = true;
  postScene.userData.skipCinematicDefocus = true;

  const postCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  const postMaterial = new THREE.ShaderMaterial({
    transparent: true,
    depthTest: false,
    depthWrite: false,
    uniforms: {
      tScene: { value: null },
      uTexel: { value: new THREE.Vector2(1, 1) },
      uBlurPx: { value: 0 },
      uFeather: { value: 0.002 },
      uP0: { value: new THREE.Vector2() },
      uP1: { value: new THREE.Vector2() },
      uP2: { value: new THREE.Vector2() },
      uP3: { value: new THREE.Vector2() },
    },
    vertexShader: `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = vec4(position.xy, 0.0, 1.0);
      }
    `,
    fragmentShader: `
      uniform sampler2D tScene;
      uniform vec2 uTexel;
      uniform float uBlurPx;
      uniform float uFeather;
      uniform vec2 uP0;
      uniform vec2 uP1;
      uniform vec2 uP2;
      uniform vec2 uP3;
      varying vec2 vUv;

      float cross2(vec2 a, vec2 b) {
        return a.x * b.y - a.y * b.x;
      }

      float edgeDistance(vec2 p, vec2 a, vec2 b, float orientation) {
        vec2 e = b - a;
        float len = max(length(e), 0.00001);
        return orientation * cross2(e, p - a) / len;
      }

      float quadMask(vec2 p) {
        float orientation = sign(cross2(uP1 - uP0, uP2 - uP1));
        if (orientation == 0.0) orientation = 1.0;

        float d0 = edgeDistance(p, uP0, uP1, orientation);
        float d1 = edgeDistance(p, uP1, uP2, orientation);
        float d2 = edgeDistance(p, uP2, uP3, orientation);
        float d3 = edgeDistance(p, uP3, uP0, orientation);
        float minD = min(min(d0, d1), min(d2, d3));

        return smoothstep(-uFeather, uFeather, minD);
      }

      void main() {
        vec2 dx = vec2(uTexel.x * uBlurPx, 0.0);
        vec2 dy = vec2(0.0, uTexel.y * uBlurPx);

        vec4 c = texture2D(tScene, vUv) * 0.28;
        c += texture2D(tScene, vUv + dx * 0.65) * 0.10;
        c += texture2D(tScene, vUv - dx * 0.65) * 0.10;
        c += texture2D(tScene, vUv + dy * 0.65) * 0.10;
        c += texture2D(tScene, vUv - dy * 0.65) * 0.10;
        c += texture2D(tScene, vUv + dx * 1.35) * 0.05;
        c += texture2D(tScene, vUv - dx * 1.35) * 0.05;
        c += texture2D(tScene, vUv + dy * 1.35) * 0.05;
        c += texture2D(tScene, vUv - dy * 1.35) * 0.05;
        c += texture2D(tScene, vUv + (dx + dy) * 0.75) * 0.03;
        c += texture2D(tScene, vUv + (dx - dy) * 0.75) * 0.03;
        c += texture2D(tScene, vUv + (-dx + dy) * 0.75) * 0.03;
        c += texture2D(tScene, vUv - (dx + dy) * 0.75) * 0.03;

        float mask = quadMask(vUv);
        gl_FragColor = vec4(c.rgb, c.a * mask);
      }
    `,
  });

  postScene.add(new THREE.Mesh(new THREE.PlaneGeometry(2, 2), postMaterial));

  const state = {
    target: new THREE.WebGLRenderTarget(4, 4, {
      minFilter: THREE.LinearFilter,
      magFilter: THREE.LinearFilter,
      format: THREE.RGBAFormat,
      depthBuffer: true,
      stencilBuffer: false,
    }),
    postScene,
    postCamera,
    postMaterial,
    size: new THREE.Vector2(),
    shells: [],
    phone: null,
    bounds: null,
    busy: false,
  };

  state.target.texture.generateMipmaps = false;
  rendererState.set(renderer, state);
  return state;
}

function collectMovingHalf(scene, state) {
  if (state.shells.length && state.phone && state.bounds) return true;

  const shells = [];
  scene.traverse(object => {
    if (object.isMesh && object.userData?.isMovingShell) shells.push(object);
  });

  if (!shells.length) return false;

  const phone = shells[0].parent;
  const bounds = new THREE.Box3();
  let hasBounds = false;

  shells.forEach(mesh => {
    if (!mesh.geometry.boundingBox) mesh.geometry.computeBoundingBox();
    if (!mesh.geometry.boundingBox) return;
    bounds.union(mesh.geometry.boundingBox);
    hasBounds = true;
  });

  if (!phone || !hasBounds) return false;

  state.shells = shells;
  state.phone = phone;
  state.bounds = bounds;
  return true;
}

function ensureTargetSize(renderer, state) {
  renderer.getDrawingBufferSize(state.size);
  const width = Math.max(2, Math.floor(state.size.x));
  const height = Math.max(2, Math.floor(state.size.y));

  if (state.target.width !== width || state.target.height !== height) {
    state.target.setSize(width, height);
  }

  state.postMaterial.uniforms.uTexel.value.set(1 / width, 1 / height);
  state.postMaterial.uniforms.uFeather.value = 2.0 / Math.max(width, height);
}

function rotateHingePoint(x, y, z, foldAngle) {
  const c = Math.cos(foldAngle);
  const s = Math.sin(foldAngle);
  const localZ = z - HINGE_Z;

  return new THREE.Vector3(
    c * x + s * localZ,
    y,
    -s * x + c * localZ + HINGE_Z,
  );
}

function projectUv(point, phone, camera, target) {
  point.applyMatrix4(phone.matrixWorld).project(camera);
  target.set(
    point.x * 0.5 + 0.5,
    point.y * 0.5 + 0.5,
  );
}

function updateForegroundQuad(state, camera, progress) {
  const bounds = state.bounds;
  const phone = state.phone;
  if (!bounds || !phone) return false;

  phone.updateMatrixWorld(true);
  camera.updateMatrixWorld(true);

  const foldAngle = (1 - progress) * Math.PI;
  const outerX = bounds.min.x;
  const topY = bounds.max.y;
  const bottomY = bounds.min.y;

  // Use the camera-facing shell surface as a robust approximation of the panel plane.
  const panelZ = bounds.max.z;

  const p0 = rotateHingePoint(outerX, topY, panelZ, foldAngle);
  const p1 = rotateHingePoint(HINGE_X, topY, panelZ, foldAngle);
  const p2 = rotateHingePoint(HINGE_X, bottomY, panelZ, foldAngle);
  const p3 = rotateHingePoint(outerX, bottomY, panelZ, foldAngle);

  projectUv(p0, phone, camera, state.postMaterial.uniforms.uP0.value);
  projectUv(p1, phone, camera, state.postMaterial.uniforms.uP1.value);
  projectUv(p2, phone, camera, state.postMaterial.uniforms.uP2.value);
  projectUv(p3, phone, camera, state.postMaterial.uniforms.uP3.value);

  return true;
}

THREE.WebGLRenderer.prototype.render = function cinematicDefocusRender(scene, camera) {
  const state = rendererState.get(this) || makeState(this);

  if (
    state.busy
    || this.getRenderTarget() !== null
    || !scene?.isScene
    || scene?.userData?.skipCinematicDefocus
  ) {
    return previousRender.call(this, scene, camera);
  }

  const progress = THREE.MathUtils.clamp(
    Number(document.querySelector('#angle')?.value || 0) / 180,
    0,
    1,
  );
  const defocusPx = computeForegroundDefocus(progress);

  // Always render the current sharp / motion-blurred base first.
  const baseResult = previousRender.call(this, scene, camera);

  if (defocusPx < 0.05 || !collectMovingHalf(scene, state)) {
    return baseResult;
  }

  state.busy = true;

  try {
    ensureTargetSize(this, state);
    if (!updateForegroundQuad(state, camera, progress)) return baseResult;

    const previousTarget = this.getRenderTarget();
    const previousAutoClear = this.autoClear;
    const previousClearColor = this.getClearColor(new THREE.Color()).clone();
    const previousClearAlpha = this.getClearAlpha();

    // Capture a sharp scene for the depth-of-field sample source.
    this.setRenderTarget(state.target);
    this.setClearColor(0x000000, 0);
    this.clear(true, true, true);
    previousRender.call(this, scene, camera);

    // Composite the defocused foreground half back over the existing base.
    this.setRenderTarget(previousTarget);
    this.setClearColor(previousClearColor, previousClearAlpha);
    this.autoClear = false;

    state.postMaterial.uniforms.tScene.value = state.target.texture;
    state.postMaterial.uniforms.uBlurPx.value = defocusPx * this.getPixelRatio();

    previousRender.call(this, state.postScene, state.postCamera);

    this.autoClear = previousAutoClear;
  } finally {
    state.busy = false;
  }

  return baseResult;
};

console.info('Step 4.1 cinematic foreground defocus ready', {
  maxDefocusPx: MAX_DEFOCUS_PX,
  progressDriven: true,
  movingForegroundOnly: true,
  fixedWorldStaysSharp: true,
  motionBlurCompatible: true,
});
