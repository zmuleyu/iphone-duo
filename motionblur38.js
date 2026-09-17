import * as THREE from 'three';

// Step 3.8 — Selective Moving-Shell Motion Blur (v1)
// Runs before main.js and patches WebGLRenderer.render. During real Unfold playback,
// only meshes tagged with userData.isMovingShell are rendered through a small
// horizontal blur pass. Screens and the fixed half remain sharp. Manual slider
// stops are sharp because blur is gated by playback state and angular velocity.

const originalRender = THREE.WebGLRenderer.prototype.render;
const rendererState = new WeakMap();
let motionBlurMode = 'natural';

function makeState(renderer) {
  const postScene = new THREE.Scene();
  const postCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  const postMaterial = new THREE.ShaderMaterial({
    transparent: true,
    depthTest: false,
    depthWrite: false,
    uniforms: {
      tShell: { value: null },
      uTexel: { value: new THREE.Vector2(1, 1) },
      uBlurPx: { value: 0 },
    },
    vertexShader: `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = vec4(position.xy, 0.0, 1.0);
      }
    `,
    fragmentShader: `
      uniform sampler2D tShell;
      uniform vec2 uTexel;
      uniform float uBlurPx;
      varying vec2 vUv;
      void main() {
        vec2 d = vec2(uTexel.x * uBlurPx, 0.0);
        vec4 c = vec4(0.0);
        c += texture2D(tShell, vUv - d * 2.2) * 0.05;
        c += texture2D(tShell, vUv - d * 1.35) * 0.10;
        c += texture2D(tShell, vUv - d * 0.65) * 0.17;
        c += texture2D(tShell, vUv) * 0.36;
        c += texture2D(tShell, vUv + d * 0.65) * 0.17;
        c += texture2D(tShell, vUv + d * 1.35) * 0.10;
        c += texture2D(tShell, vUv + d * 2.2) * 0.05;
        gl_FragColor = c;
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
    prevAngle: 0,
    prevTime: performance.now(),
    velocity: 0,
    busy: false,
  };
  state.target.texture.generateMipmaps = false;
  rendererState.set(renderer, state);
  return state;
}

function collectShells(scene, state) {
  if (state.shells.length) return state.shells;
  scene.traverse(object => {
    if (object.isMesh && object.userData?.isMovingShell) state.shells.push(object);
  });
  return state.shells;
}

function isPlaybackRunning() {
  return document.querySelector('#play-label')?.textContent?.trim() === 'Pause';
}

function updateVelocity(state) {
  const now = performance.now();
  const angle = Number(document.querySelector('#angle')?.value || 0);
  const dt = Math.max((now - state.prevTime) / 1000, 1 / 240);
  const raw = Math.abs(angle - state.prevAngle) / dt;
  state.prevAngle = angle;
  state.prevTime = now;

  const running = isPlaybackRunning();
  const targetVelocity = running ? raw : 0;
  state.velocity += (targetVelocity - state.velocity) * (running ? 0.32 : 0.55);

  const normalized = THREE.MathUtils.smoothstep(state.velocity, 24, 150);
  if (motionBlurMode === 'off') return 0;
  if (motionBlurMode === 'strong') return THREE.MathUtils.clamp(normalized * 1.25, 0, 1);
  return normalized;
}

function ensureTargetSize(renderer, state) {
  renderer.getDrawingBufferSize(state.size);
  const width = Math.max(2, Math.floor(state.size.x));
  const height = Math.max(2, Math.floor(state.size.y));
  if (state.target.width !== width || state.target.height !== height) {
    state.target.setSize(width, height);
  }
  state.postMaterial.uniforms.uTexel.value.set(1 / width, 1 / height);
}

function withVisibility(objects, visible, fn) {
  const previous = objects.map(object => object.visible);
  objects.forEach(object => { object.visible = visible; });
  try { fn(); } finally {
    objects.forEach((object, index) => { object.visible = previous[index]; });
  }
}

THREE.WebGLRenderer.prototype.render = function patchedRender(scene, camera) {
  const state = rendererState.get(this) || makeState(this);

  // Do not intercept internal/off-screen renders or our own post pass.
  if (state.busy || this.getRenderTarget() !== null || !scene?.isScene) {
    return originalRender.call(this, scene, camera);
  }

  const shells = collectShells(scene, state);
  const amount = updateVelocity(state);
  if (!shells.length || amount < 0.025) {
    return originalRender.call(this, scene, camera);
  }

  state.busy = true;
  try {
    ensureTargetSize(this, state);

    // 1) Sharp base scene, but without the moving shell.
    withVisibility(shells, false, () => {
      originalRender.call(this, scene, camera);
    });

    // 2) Moving shell only -> transparent render target.
    const meshObjects = [];
    scene.traverse(object => { if (object.isMesh) meshObjects.push(object); });
    const shellSet = new Set(shells);
    const nonShellMeshes = meshObjects.filter(object => !shellSet.has(object));

    const previousTarget = this.getRenderTarget();
    const previousAutoClear = this.autoClear;
    const previousClearColor = this.getClearColor(new THREE.Color()).clone();
    const previousClearAlpha = this.getClearAlpha();

    withVisibility(nonShellMeshes, false, () => {
      this.setRenderTarget(state.target);
      this.setClearColor(0x000000, 0);
      this.clear(true, true, true);
      originalRender.call(this, scene, camera);
    });

    // 3) Composite blurred shell back over the sharp scene.
    this.setRenderTarget(previousTarget);
    this.setClearColor(previousClearColor, previousClearAlpha);
    this.autoClear = false;
    state.postMaterial.uniforms.tShell.value = state.target.texture;
    const cssPeak = motionBlurMode === 'strong' ? 10 : 6;
    state.postMaterial.uniforms.uBlurPx.value = amount * cssPeak * this.getPixelRatio();
    originalRender.call(this, state.postScene, state.postCamera);
    this.autoClear = previousAutoClear;
  } finally {
    state.busy = false;
  }
};

function setMode(mode) {
  if (!['off', 'natural', 'strong'].includes(mode)) return;
  motionBlurMode = mode;
  document.querySelectorAll('[data-motion-blur]').forEach(button => {
    button.setAttribute('aria-pressed', String(button.dataset.motionBlur === mode));
  });
  document.documentElement.dataset.motionBlur = mode;
}

document.querySelectorAll('[data-motion-blur]').forEach(button => {
  button.addEventListener('click', () => setMode(button.dataset.motionBlur));
});
setMode('natural');

console.info('Lv3 Step 3.8 selective moving-shell motion blur ready', {
  framingBaseline: 'Step 3.7.2',
  mode: motionBlurMode,
  shellOnly: true,
  velocityDriven: true,
  staticSliderStatesStaySharp: true,
});
