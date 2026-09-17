import * as THREE from 'three';
import { USDLoader } from 'three/addons/loaders/USDLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { loadDefaultUIs } from './ui.js';

const BUILD_VERSION = 'v4.1D.4';

const viewport = document.querySelector('#viewport');
const slider = document.querySelector('#angle');
const play = document.querySelector('#play');
const playLabel = document.querySelector('#play-label');
const closedButton = document.querySelector('#closed-button');
const openButton = document.querySelector('#open-button');
const progressReadout = document.querySelector('#progress-readout');
const angleReadout = document.querySelector('#angle-readout');
const revealReadout = document.querySelector('#reveal-readout');
const revealSummaryValue = document.querySelector('#reveal-summary-value');
const strategySummary = document.querySelector('#strategy-summary');
const snapButtons = [...document.querySelectorAll('[data-snap]')];
const realityInput = document.querySelector('#ui-upload');
const redBlackInput = document.querySelector('#redblack-upload');
const redBlackButton = document.querySelector('#redblack-button');
const revealSettingsButton = document.querySelector('#reveal-settings');
const revealSettingsPopover = document.querySelector('#reveal-settings-popover');

const stageBackground = document.querySelector('#stage-background');
const bgSolidButton = document.querySelector('#bg-solid');
const bgImageButton = document.querySelector('#bg-image');
const bgTransparentButton = document.querySelector('#bg-transparent');
const bgUpload = document.querySelector('#bg-upload');
const bgFit = document.querySelector('#bg-fit');
const bgColor = document.querySelector('#bg-color');

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(32, 1, .1, 250);
camera.position.set(0, 0, 40);

const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setClearColor(0x000000, 0);
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.18;
viewport.appendChild(renderer.domElement);

const environment = new RoomEnvironment();
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(environment, .04).texture;
environment.dispose();
pmrem.dispose();
scene.environmentIntensity = 1.35;
scene.add(new THREE.HemisphereLight(0xffffff, 0xb5baa8, 1.8));
const key = new THREE.DirectionalLight(0xfffcf5, 2.6);
key.position.set(-15, 25, 30);
scene.add(key);
const rim = new THREE.DirectionalLight(0xe8edf5, 2);
rim.position.set(15, 5, -15);
scene.add(rim);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = false;
controls.enablePan = false;
controls.enableRotate = false;
controls.enableZoom = false;
controls.target.set(0, 0, .275454);
controls.update();
controls.enabled = false;

const phone = new THREE.Group();
scene.add(phone);

const HALF_DEVICE_WIDTH = 7.89935;
const FRAMING_STRENGTH = 0.90;
const OPEN_SCALE = 0.97;
const OPTICAL_X_START = 0.45;
const OPTICAL_X_PEAK_PROGRESS = 0.65;
const OPTICAL_X_END = 0.92;
const OPTICAL_X_PEAK = 0.65;

const bend = { value: Math.PI };
const worldMix = { value: 0 };
const foldProgress = { value: 0 };
const coverFx = { value: 0 };
const coverOpacity = { value: 1 };

let angle = 0;
let playing = false;
let playbackTime = 0;
let ready = false;
let uiTheme = 'wallpaper';
const screens = {};
const customReady = { reality: false, redblack: false };
const movingShellMeshes = [];

if (revealSettingsButton) revealSettingsButton.hidden = true;
if (revealSettingsPopover) revealSettingsPopover.hidden = true;
const subtitle = document.querySelector('.timeline-title-block span');
if (subtitle) subtitle.textContent = 'Reality → RedBlack unified world hand-off';

let backgroundMode = 'solid';
let backgroundImageUrl = null;

function applyBackground() {
  const modeButtons = { solid: bgSolidButton, image: bgImageButton, transparent: bgTransparentButton };
  for (const [mode, button] of Object.entries(modeButtons)) button?.setAttribute('aria-pressed', String(mode === backgroundMode));
  stageBackground.style.filter = 'none';
  stageBackground.style.transform = 'none';
  bgFit.disabled = backgroundMode !== 'image' || !backgroundImageUrl;
  bgColor.disabled = backgroundMode !== 'solid';
  if (backgroundMode === 'transparent') {
    stageBackground.style.background = 'transparent';
    stageBackground.style.opacity = '0';
    return;
  }
  stageBackground.style.opacity = '1';
  if (backgroundMode === 'solid') {
    stageBackground.style.backgroundImage = 'none';
    stageBackground.style.backgroundColor = bgColor.value;
    return;
  }
  if (!backgroundImageUrl) {
    stageBackground.style.backgroundImage = 'none';
    stageBackground.style.backgroundColor = bgColor.value;
    return;
  }
  stageBackground.style.backgroundColor = '#111';
  stageBackground.style.backgroundImage = `url("${backgroundImageUrl}")`;
  stageBackground.style.backgroundPosition = 'center';
  stageBackground.style.backgroundRepeat = 'no-repeat';
  stageBackground.style.backgroundSize = bgFit.value === 'contain' ? 'contain' : 'cover';
  if (bgFit.value === 'blur') {
    stageBackground.style.filter = 'blur(14px)';
    stageBackground.style.transform = 'scale(1.045)';
  }
}

bgSolidButton?.addEventListener('click', () => { backgroundMode = 'solid'; applyBackground(); });
bgTransparentButton?.addEventListener('click', () => { backgroundMode = 'transparent'; applyBackground(); });
bgImageButton?.addEventListener('click', () => {
  if (!backgroundImageUrl) { bgUpload.click(); return; }
  backgroundMode = 'image'; applyBackground();
});
bgUpload?.addEventListener('change', () => {
  const file = bgUpload.files[0];
  if (!file) return;
  if (backgroundImageUrl) URL.revokeObjectURL(backgroundImageUrl);
  backgroundImageUrl = URL.createObjectURL(file);
  backgroundMode = 'image';
  applyBackground();
  bgUpload.value = '';
});
bgFit?.addEventListener('change', applyBackground);
bgColor?.addEventListener('input', applyBackground);
applyBackground();

const defaultUIs = await loadDefaultUIs();

function makeCanvasPair() {
  const inner = document.createElement('canvas');
  inner.width = 1600;
  inner.height = 1125;
  const outer = document.createElement('canvas');
  outer.width = 800;
  outer.height = 1125;
  return { inner, outer };
}

function createCanvasTexture(canvas) {
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = renderer.capabilities.getMaxAnisotropy();
  texture.wrapS = THREE.ClampToEdgeWrapping;
  texture.wrapT = THREE.ClampToEdgeWrapping;
  return texture;
}

const customCanvases = { reality: makeCanvasPair(), redblack: makeCanvasPair() };
const customTextures = {
  reality: { inner: createCanvasTexture(customCanvases.reality.inner), outer: createCanvasTexture(customCanvases.reality.outer) },
  redblack: { inner: createCanvasTexture(customCanvases.redblack.inner), outer: createCanvasTexture(customCanvases.redblack.outer) },
};

for (const kind of ['inner', 'outer']) {
  const defaultTextures = {};
  for (const [theme, canvases] of Object.entries(defaultUIs)) defaultTextures[theme] = createCanvasTexture(canvases[kind]);
  const material = new THREE.MeshBasicMaterial({ map: defaultTextures.wallpaper, toneMapped: false, transparent: kind === 'outer', depthWrite: kind !== 'outer' });
  screens[kind] = { material, defaultTextures, targetMap: defaultTextures.wallpaper, shader: null };
}

function drawArtwork(img, pair, textures) {
  const inner = pair.inner.getContext('2d');
  inner.fillStyle = '#101418';
  inner.fillRect(0, 0, pair.inner.width, pair.inner.height);
  const scale = Math.min(pair.inner.width / img.width, pair.inner.height / img.height);
  const width = img.width * scale;
  const height = img.height * scale;
  inner.drawImage(img, (pair.inner.width - width) / 2, (pair.inner.height - height) / 2, width, height);
  const outer = pair.outer.getContext('2d');
  outer.fillStyle = '#101418';
  outer.fillRect(0, 0, pair.outer.width, pair.outer.height);
  outer.drawImage(pair.inner, pair.inner.width / 2, 0, pair.inner.width / 2, pair.inner.height, 0, 0, pair.outer.width, pair.outer.height);
  textures.inner.needsUpdate = true;
  textures.outer.needsUpdate = true;
}

function setScreenMaps(baseSet, targetSet = baseSet) {
  for (const kind of ['inner', 'outer']) {
    const screen = screens[kind];
    screen.material.map = baseSet[kind];
    screen.targetMap = targetSet[kind];
    if (screen.shader?.uniforms?.transitionTarget) screen.shader.uniforms.transitionTarget.value = screen.targetMap;
    screen.material.needsUpdate = true;
  }
}

function updateSourceUI() {
  document.querySelectorAll('[data-ui-theme]').forEach(button => button.setAttribute('aria-selected', String(uiTheme === 'custom')));
  redBlackButton.classList.toggle('is-loaded', customReady.redblack);
  redBlackButton.textContent = customReady.redblack ? 'RedBlack ✓' : 'RedBlack';
}

async function decodeFile(file) {
  const url = URL.createObjectURL(file);
  const img = new Image();
  img.src = url;
  try { await img.decode(); return img; }
  finally { URL.revokeObjectURL(url); }
}

realityInput.addEventListener('change', async () => {
  const file = realityInput.files[0];
  if (!file) return;
  try {
    const img = await decodeFile(file);
    drawArtwork(img, customCanvases.reality, customTextures.reality);
    customReady.reality = true;
    uiTheme = 'custom';
    setScreenMaps(customTextures.reality, customReady.redblack ? customTextures.redblack : customTextures.reality);
    setPlaying(false); setAngle(0); updateSourceUI();
  } catch (error) {
    console.error(error);
    alert('Unable to read the Reality image. Choose a PNG, JPG, or WebP file.');
  } finally { realityInput.value = ''; }
});

redBlackInput.addEventListener('change', async () => {
  const file = redBlackInput.files[0];
  if (!file) return;
  if (!customReady.reality) {
    alert('Upload the Reality image first.');
    redBlackInput.value = '';
    return;
  }
  try {
    const img = await decodeFile(file);
    drawArtwork(img, customCanvases.redblack, customTextures.redblack);
    customReady.redblack = true;
    uiTheme = 'custom';
    setScreenMaps(customTextures.reality, customTextures.redblack);
    setPlaying(false); setAngle(0); updateSourceUI();
  } catch (error) {
    console.error(error);
    alert('Unable to read the RedBlack image. Choose a PNG, JPG, or WebP file.');
  } finally { redBlackInput.value = ''; }
});

document.querySelector('[data-ui-theme="custom"]')?.addEventListener('click', () => realityInput.click());
redBlackButton?.addEventListener('click', () => {
  if (!customReady.reality) { alert('Upload the Reality image first.'); return; }
  redBlackInput.click();
});

function smooth01(t) {
  const x = THREE.MathUtils.clamp(t, 0, 1);
  return x * x * (3 - 2 * x);
}

function worldMixFromProgress(progress) {
  if (progress <= 0.30) return 0;
  if (progress >= 0.45) return 1;
  return smooth01((progress - 0.30) / 0.15);
}

function coverFxFromProgress(progress) {
  if (progress <= 0.25) return 0;
  if (progress >= 0.55) return 1;
  return smooth01((progress - 0.25) / 0.30);
}

function coverOpacityFromProgress(progress) {
  const points = [[0.00,1.00],[0.30,1.00],[0.35,0.90],[0.40,0.72],[0.45,0.48],[0.50,0.22],[0.55,0.00],[1.00,0.00]];
  const p = THREE.MathUtils.clamp(progress, 0, 1);
  for (let i = 0; i < points.length - 1; i++) {
    const [p0,v0] = points[i], [p1,v1] = points[i+1];
    if (p <= p1) return THREE.MathUtils.lerp(v0, v1, smooth01((p - p0) / Math.max(p1 - p0, 1e-6)));
  }
  return 0;
}

function updateTimelineUI(progress, mix) {
  const progressPercent = Math.round(progress * 100);
  const worldPercent = Math.round(mix * 100);
  progressReadout.textContent = `Progress ${progressPercent}%`;
  angleReadout.textContent = `Angle ${Math.round(angle)}°`;
  revealReadout.textContent = `World ${worldPercent}%`;
  revealSummaryValue.textContent = `${worldPercent}%`;
  strategySummary.textContent = 'World';
  slider.style.setProperty('--progress', `${progressPercent}%`);
  snapButtons.forEach(button => button.classList.toggle('is-current', Math.abs(angle - Number(button.dataset.snap)) < .6));
}

function smoothOpticalX(progress) {
  const p = THREE.MathUtils.clamp(progress, 0, 1);
  if (p <= OPTICAL_X_START || p >= OPTICAL_X_END) return 0;
  if (p <= OPTICAL_X_PEAK_PROGRESS) return OPTICAL_X_PEAK * THREE.MathUtils.smoothstep(p, OPTICAL_X_START, OPTICAL_X_PEAK_PROGRESS);
  return OPTICAL_X_PEAK * (1 - THREE.MathUtils.smoothstep(p, OPTICAL_X_PEAK_PROGRESS, OPTICAL_X_END));
}

function updateFraming(progress) {
  const p = THREE.MathUtils.clamp(progress, 0, 1);
  const foldAngle = (1 - p) * Math.PI;
  const projectedCenter = p <= .5 ? HALF_DEVICE_WIDTH * .5 : HALF_DEVICE_WIDTH * (1 - Math.cos(foldAngle)) * .5;
  phone.position.x = -projectedCenter * FRAMING_STRENGTH + smoothOpticalX(p);
  const lateOpen = THREE.MathUtils.smoothstep(p, .52, 1.0);
  phone.scale.setScalar(THREE.MathUtils.lerp(1.0, OPEN_SCALE, lateOpen));
}

function setPlaying(value) {
  playing = value;
  document.querySelector('#pause-icon')?.toggleAttribute('hidden', !value);
  document.querySelector('#play-icon')?.toggleAttribute('hidden', value);
  playLabel.textContent = value ? 'Pause' : 'Unfold';
  play.setAttribute('aria-label', value ? 'Pause unfold animation' : 'Play unfold animation');
}

function setAngle(value) {
  angle = THREE.MathUtils.clamp(value, 0, 180);
  slider.value = angle;
  bend.value = (180 - angle) / 180 * Math.PI;
  const progress = angle / 180;
  const active = uiTheme === 'custom' && customReady.reality && customReady.redblack;
  const mix = active ? worldMixFromProgress(progress) : 0;
  worldMix.value = mix;
  foldProgress.value = progress;
  coverFx.value = active ? coverFxFromProgress(progress) : 0;
  coverOpacity.value = active ? coverOpacityFromProgress(progress) : 1;
  updateTimelineUI(progress, mix);
  updateFraming(progress);
}

play.addEventListener('click', () => {
  if (playing) { setPlaying(false); return; }
  if (angle > .1) setAngle(0);
  playbackTime = 0;
  setPlaying(true);
});
closedButton.addEventListener('click', () => { setPlaying(false); playbackTime = 0; setAngle(0); });
openButton.addEventListener('click', () => { setPlaying(false); playbackTime = 0; setAngle(180); });
snapButtons.forEach(button => button.addEventListener('click', () => { setPlaying(false); playbackTime = 0; setAngle(Number(button.dataset.snap)); }));
slider.addEventListener('input', () => { setPlaying(false); playbackTime = 0; setAngle(Number(slider.value)); });

function resize() {
  const { width, height } = viewport.getBoundingClientRect();
  renderer.setSize(width, height);
  camera.aspect = width / height;
  const pixelsPerUnit = Math.min(width / 25, height / 17, 37);
  camera.fov = THREE.MathUtils.radToDeg(2 * Math.atan(height / pixelsPerUnit / 2 / 40));
  camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(viewport);

const foldShader = `
uniform float foldAngle;
vec2 rotateHinge(vec2 p) {
  float c = cos(foldAngle), s = sin(foldAngle);
  p.y -= 0.275454;
  return vec2(c * p.x + s * p.y, -s * p.x + c * p.y + 0.275454);
}
#ifdef FLEXIBLE_SCREEN
vec4 bendStrip(vec3 p) {
  float halfWidth = 0.35;
  if (p.x >= halfWidth) return vec4(p.x, p.z, 1.0, 0.0);
  if (p.x <= -halfWidth) return vec4(rotateHinge(p.xz), cos(foldAngle), -sin(foldAngle));
  float t = (p.x + halfWidth) / (2.0 * halfWidth);
  float t2 = t*t, t3 = t2*t;
  vec2 a = rotateHinge(vec2(-halfWidth, p.z));
  vec2 b = vec2(halfWidth, p.z);
  vec2 ta = 2.0 * halfWidth * vec2(cos(foldAngle), -sin(foldAngle));
  vec2 tb = vec2(2.0 * halfWidth, 0.0);
  vec2 point = (2.0*t3-3.0*t2+1.0)*a + (t3-2.0*t2+t)*ta + (-2.0*t3+3.0*t2)*b + (t3-t2)*tb;
  vec2 tangent = normalize((6.0*t2-6.0*t)*a + (3.0*t2-4.0*t+1.0)*ta + (-6.0*t2+6.0*t)*b + (3.0*t2-2.0*t)*tb);
  return vec4(point, tangent);
}
#endif
`;

try {
  const model = await new USDLoader().loadAsync('./assets/iPhone_Duo_Render.usdc');
  model.scale.multiplyScalar(100);
  model.updateMatrixWorld(true);
  const count = { moving: 0, fixed: 0, flexible: 0 };

  model.traverse(object => {
    if (!object.isMesh) return;
    const geometry = object.geometry.clone().applyMatrix4(object.matrixWorld);
    geometry.translate(0, -5.8974, 0);
    let ancestor = object;
    while (ancestor && !['upTUAKvMVkPOMKq', 'SiftyleUEEZwLhF'].includes(ancestor.name)) ancestor = ancestor.parent;
    const moving = ancestor?.name === 'upTUAKvMVkPOMKq';
    const flexible = ['JnJdTkxbQgUtLwU', 'xdyyaajWsatVNxN', 'UXtsBZYlaUvHoEh', 'MvKPXGSdYDVvSpk'].includes(object.name);
    const kind = object.name === 'UXtsBZYlaUvHoEh' ? 'inner' : object.name === 'hhgAIoCGsHXeDPY' ? 'outer' : null;
    const material = kind ? screens[kind].material : object.material.clone();

    if (kind) {
      const p = geometry.attributes.position;
      const uv = new Float32Array(p.count * 2);
      for (let i = 0; i < p.count; i++) {
        uv[i * 2] = kind === 'inner' ? (p.getX(i) + 7.89935) / 15.7987 : (-.23396 - p.getX(i)) / 7.73936;
        uv[i * 2 + 1] = kind === 'inner' ? (p.getY(i) + 5.8974 - .34562) / 11.1035 : (p.getY(i) + 5.8974 - .27173) / 11.2513;
      }
      geometry.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
    }

    if (moving || flexible || kind) {
      material.onBeforeCompile = shader => {
        shader.uniforms.foldAngle = bend;
        shader.vertexShader = `${flexible ? '#define FLEXIBLE_SCREEN\n' : ''}${foldShader}\n${shader.vertexShader}`;

        if (moving || flexible) {
          shader.vertexShader = shader.vertexShader.replace('#include <begin_vertex>', flexible ? `
            vec4 folded = bendStrip(position);
            vec3 transformed = vec3(folded.x, position.y, folded.y);
          ` : `
            vec2 folded = rotateHinge(position.xz);
            vec3 transformed = vec3(folded.x, position.y, folded.y);
          `);
          shader.vertexShader = shader.vertexShader.replace('#include <beginnormal_vertex>', `
            vec3 objectNormal = vec3(normal);
            ${flexible ? 'vec4 strip = bendStrip(position); float a = atan(-strip.w, strip.z);' : 'float a = foldAngle;'}
            objectNormal.x = cos(a) * normal.x + sin(a) * normal.z;
            objectNormal.z = -sin(a) * normal.x + cos(a) * normal.z;
          `);
        }

        if (kind) {
          const screen = screens[kind];
          const isOuter = kind === 'outer' ? 1 : 0;
          shader.uniforms.transitionTarget = { value: screen.targetMap };
          shader.uniforms.worldMix = worldMix;
          shader.uniforms.foldProgress = foldProgress;
          shader.uniforms.coverFx = coverFx;
          shader.uniforms.coverOpacity = coverOpacity;
          shader.uniforms.isOuter = { value: isOuter };
          shader.fragmentShader = `
            uniform sampler2D transitionTarget;
            uniform float worldMix;
            uniform float foldProgress;
            uniform float coverFx;
            uniform float coverOpacity;
            uniform float isOuter;
            ${shader.fragmentShader}
          `;
          shader.fragmentShader = shader.fragmentShader.replace('#include <map_fragment>', `
            #ifdef USE_MAP
              vec2 worldUv = vMapUv;
              vec2 texSize = vec2(textureSize(map, 0));
              vec2 uiPixel = 1.0 / max(texSize, vec2(1.0));
              vec4 reality = texture2D(map, worldUv);
              vec4 redblack = texture2D(transitionTarget, worldUv);
              float preheat = smoothstep(0.25, 0.38, foldProgress) * (1.0 - worldMix);
              reality.rgb *= vec3(1.0 + 0.14 * preheat, 1.0 - 0.045 * preheat, 1.0 - 0.20 * preheat);
              vec4 worldSample = mix(reality, redblack, worldMix);
              float blurGradient = clamp(worldUv.x, 0.0, 1.0);
              float darkenGradient = clamp((worldUv.x - 0.2) / 0.8, 0.0, 1.0);
              float motion = coverFx * isOuter;
              float effect = motion * pow(darkenGradient, 1.35);
              float radius = 72.0 * motion * pow(blurGradient, 1.35);
              vec2 aa = max(fwidth(worldUv), uiPixel * 0.5);
              vec2 dx = dFdx(worldUv) / uiPixel;
              vec2 dy = dFdy(worldUv) / uiPixel;
              float baseLod = log2(max(1.0, max(length(dx), length(dy))));
              vec2 coverage = smoothstep(-aa, aa, worldUv) * (1.0 - smoothstep(vec2(1.0) - aa, vec2(1.0) + aa, worldUv));
              vec3 color = worldSample.rgb * coverage.x * coverage.y;
              if (radius > 0.0) {
                float lod = max(baseLod, log2(max(1.0, radius)));
                vec2 footprint = max(aa, uiPixel * radius * 0.75);
                color = vec3(0.0);
                for (int y = -2; y <= 2; y++) {
                  for (int x = -2; x <= 2; x++) {
                    float wx = x == 0 ? 6.0 : (abs(x) == 1 ? 4.0 : 1.0);
                    float wy = y == 0 ? 6.0 : (abs(y) == 1 ? 4.0 : 1.0);
                    vec2 sampleUV = worldUv + vec2(float(x), float(y)) * uiPixel * radius;
                    vec2 sampleCoverage = smoothstep(-footprint, footprint, sampleUV) * (1.0 - smoothstep(vec2(1.0) - footprint, vec2(1.0) + footprint, sampleUV));
                    vec2 clampedUV = clamp(sampleUV, vec2(0.0), vec2(1.0));
                    vec3 realityTap = textureLod(map, clampedUV, lod).rgb;
                    vec3 redblackTap = textureLod(transitionTarget, clampedUV, lod).rgb;
                    vec3 worldTap = mix(realityTap, redblackTap, worldMix);
                    color += worldTap * sampleCoverage.x * sampleCoverage.y * wx * wy / 256.0;
                  }
                }
              }
              color *= (1.0 - min(1.0, effect * 1.75));
              vec4 sampledDiffuseColor = vec4(color, worldSample.a);
              #ifdef DECODE_VIDEO_TEXTURE
                sampledDiffuseColor = sRGBTransferEOTF(sampledDiffuseColor);
              #endif
              diffuseColor *= sampledDiffuseColor;
              diffuseColor.a *= mix(1.0, coverOpacity, isOuter);
            #endif
          `);
          screen.shader = shader;
        }
      };
      material.customProgramCacheKey = () => `${flexible ? 'v41d4-flexible' : moving ? 'v41d4-cover' : 'v41d4-screen'}-${kind || 'body'}`;
    }

    const mesh = new THREE.Mesh(geometry, material);
    mesh.name = object.name;
    mesh.frustumCulled = false;
    phone.add(mesh);
    if (moving && !kind && !flexible) { mesh.userData.isMovingShell = true; movingShellMeshes.push(mesh); }
    count[flexible ? 'flexible' : moving ? 'moving' : 'fixed']++;
  });

  console.info(`${BUILD_VERSION} integrated unified world transition ready`, {
    ...count,
    sourceMeshes: phone.children.length,
    movingShellMeshes: movingShellMeshes.length,
    worldMixWindow: [0.30, 0.45],
    coverFadeEnd: 0.55,
    fixedUV: true,
    framing: 'step-3.7.2',
  });

  updateSourceUI();
  document.querySelectorAll('.control-dock button, .control-dock input').forEach(element => {
    if (element !== revealSettingsButton) element.disabled = false;
  });
  ready = true;
  setPlaying(false);
  setAngle(0);
} catch (error) {
  alert('Unable to load the model. Refresh the page to try again.');
  console.error(error);
}

let lastTime = performance.now();
renderer.setAnimationLoop(now => {
  const delta = Math.min((now - lastTime) / 1000, .05);
  lastTime = now;
  if (ready && playing) {
    playbackTime += delta;
    if (playbackTime < .45) setAngle(0);
    else if (playbackTime < 2.25) {
      const p = (playbackTime - .45) / 1.8;
      const ease = p * p * (3 - 2 * p);
      setAngle(THREE.MathUtils.lerp(0, 180, ease));
    } else if (playbackTime < 3.10) setAngle(180);
    else { setAngle(180); setPlaying(false); }
  }
  renderer.render(scene, camera);
});
