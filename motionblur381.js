import * as THREE from 'three';

// Step 3.8.1 — Asymmetric Directional Motion Blur
// - moving shell only
// - signed angular velocity drives blur direction
// - asymmetric trailing samples reduce the rigid CG-card feel
// - static slider states stay sharp

const originalRender = THREE.WebGLRenderer.prototype.render;
const rendererState = new WeakMap();
let motionBlurMode = 'natural';

// If the visual trail is reversed for the current hinge motion, flip to -1.
const SCREEN_TRAIL_SIGN_FOR_OPEN = 1;

const VELOCITY_ONSET = 16;
const VELOCITY_PEAK = 155;
const NATURAL_PEAK_PX = 9;
const STRONG_PEAK_PX = 15;

function makeState(renderer) {
  const postScene = new THREE.Scene();
  postScene.userData.skipMotionBlur = true;
  const postCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  const postMaterial = new THREE.ShaderMaterial({
    transparent: true,
    depthTest: false,
    depthWrite: false,
    uniforms: {
      tShell: { value: null },
      uTexel: { value: new THREE.Vector2(1, 1) },
      uBlurPx: { value: 0 },
      uDirection: { value: 1 },
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
      uniform float uDirection;
      varying vec2 vUv;

      void main() {
        vec2 dir = vec2(uTexel.x * uBlurPx * uDirection, 0.0);
        vec4 c = vec4(0.0);

        // Leading side: intentionally lighter.
        c += texture2D(tShell, vUv - dir * 1.20) * 0.03;
        c += texture2D(tShell, vUv - dir * 0.70) * 0.05;
        c += texture2D(tShell, vUv - dir * 0.30) * 0.08;

        // Strong center preserves shell definition.
        c += texture2D(tShell, vUv) * 0.34;

        // Trailing side: wider, heavier shutter trail.
        c += texture2D(tShell, vUv + dir * 0.40) * 0.12;
        c += texture2D(tShell, vUv + dir * 0.85) * 0.13;
        c += texture2D(tShell, vUv + dir * 1.35) * 0.11;
        c += texture2D(tShell, vUv + dir * 1.95) * 0.09;
        c += texture2D(tShell, vUv + dir * 2.65) * 0.05;

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
    prevAngle: Number(document.querySelector('#angle')?.value || 0),
    prevTime: performance.now(),
    signedVelocity: 0,
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
  const rawSigned = (angle - state.prevAngle) / dt;

  state.prevAngle = angle;
  state.prevTime = now;

  const running = isPlaybackRunning();
  const targetVelocity = running ? rawSigned : 0;
  state.signedVelocity += (targetVelocity - state.signedVelocity)
    * (running ? 0.28 : 0.55);

  const normalized = THREE.MathUtils.smoothstep(
    Math.abs(state.signedVelocity),
    VELOCITY_ONSET,
    VELOCITY_PEAK,
  );

  if (motionBlurMode === 'off') return { amount: 0, direction: 1 };

  const amount = motionBlurMode === 'strong'
    ? THREE.MathUtils.clamp(normalized * 1.15, 0, 1)
    : normalized;

  const directionSign = Math.sign(state.signedVelocity) || 1;
  return {
    amount,
    direction: directionSign * SCREEN_TRAIL_SIGN_FOR_OPEN,
  };
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
  try {
    fn();
  } finally {
    objects.forEach((object, index) => {
      object.visible = previous[index];
    });
  }
}

THREE.WebGLRenderer.prototype.render = function patchedRender(scene, camera) {
  const state = rendererState.get(this) || makeState(this);

  // Step 4.1 compatibility: defocus post-process scenes can explicitly opt out.
  if (
    state.busy
    || this.getRenderTarget() !== null
    || !scene?.isScene
    || scene?.userData?.skipMotionBlur
  ) {
    return originalRender.call(this, scene, camera);
  }

  const shells = collectShells(scene, state);
  const { amount, direction } = updateVelocity(state);

  if (!shells.length || amount < 0.025) {
    return originalRender.call(this, scene, camera);
  }

  state.busy = true;
  try {
    ensureTargetSize(this, state);

    // Sharp base scene without the moving shell.
    withVisibility(shells, false, () => {
      originalRender.call(this, scene, camera);
    });

    // Moving shell only -> transparent target.
    const meshObjects = [];
    scene.traverse(object => {
      if (object.isMesh) meshObjects.push(object);
    });
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

    // Composite asymmetric directional shell blur over sharp scene.
    this.setRenderTarget(previousTarget);
    this.setClearColor(previousClearColor, previousClearAlpha);
    this.autoClear = false;

    state.postMaterial.uniforms.tShell.value = state.target.texture;
    state.postMaterial.uniforms.uDirection.value = direction;

    const cssPeak = motionBlurMode === 'strong'
      ? STRONG_PEAK_PX
      : NATURAL_PEAK_PX;
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

console.info('Lv3 Step 3.8.1 asymmetric directional shell motion blur ready', {
  framingBaseline: 'Step 3.7.2',
  mode: motionBlurMode,
  naturalPeakPx: NATURAL_PEAK_PX,
  strongPeakPx: STRONG_PEAK_PX,
  velocityOnset: VELOCITY_ONSET,
  velocityPeak: VELOCITY_PEAK,
  asymmetric: true,
  signedVelocity: true,
  shellOnly: true,
  staticSliderStatesStaySharp: true,
  defocusCompatibility: true,
});
