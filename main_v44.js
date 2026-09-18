import * as THREE from 'three';
import { USDLoader } from 'three/addons/loaders/USDLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { loadDefaultUIs } from './ui.js';

// v4.4 — Original Screen Shader Rebuild
//
// Single screen-shader authority, rebuilt from the original chuspeeism main.js:
// - ONE Reality canvas/texture + ONE RedBlack canvas/texture (no inner/outer pairs)
// - Both physical screens are viewports into the SAME panorama via the original
//   fixed-front ray projection (vUIPosition -> sourceUV)
// - worldMix blends Reality -> RedBlack at the shared sourceUV, then the original
//   blur/darken runs on the mixed world
// - External cover follows the original logic exactly (black at fully open),
//   no hand-made fade curves, no wrappers, no renderer monkey-patches.

const BUILD_VERSION = 'v5.0.4';

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
// V5.0.3 Geometry Lock: keep the fixed/right panel anchored in screen space.
// The old dynamic recenter/scale pass made the tower drift even though its UV
// coordinate was stable. The device now unfolds leftward from a fixed anchor.
const FIXED_PANEL_ANCHOR_X = -HALF_DEVICE_WIDTH * 0.5 * 0.90;
const QUERY = new URLSearchParams(location.search);
const NO_FX = QUERY.has('nofx');
// V5.0.4: production uses a seam-free clean crossfade.
// The previous staged leak/collapse/lock reveal remains available only for
// explicit experiments via ?reveal=staged (or ?staged=1).
const STAGED_REVEAL = !NO_FX && (QUERY.get('reveal') === 'staged' || QUERY.has('staged'));

const bend = { value: Math.PI };
const worldMix = { value: 0 };
// Lv3 staged transition: Red Leak -> Black Collapse -> Yellow Lock
const uLeak = { value: 0 };
const uCollapse = { value: 0 };
const uLock = { value: 0 };
const uImpact = { value: 0 };      // 1-frame flash + RGB split @2.15s
const uPulse = { value: 0 };       // Lv1 tower warm pulse @3.18s
const uTransActive = { value: 0 }; // staged-only blur/rim treatment
const uNoFx = { value: NO_FX ? 1 : 0 };
const uUseStagedReveal = { value: STAGED_REVEAL ? 1 : 0 };

let angle = 0;
let playing = false;
let playbackTime = 0;
let ready = false;
let uiTheme = 'wallpaper';
let worldMixOverride = null;
let recording = false;
let recordT0 = 0;
const RECORD_AUTO = QUERY.has('record');
const screens = {};
const customReady = { reality: false, redblack: false };
const movingShellMeshes = [];

if (revealSettingsButton) revealSettingsButton.hidden = true;
if (revealSettingsPopover) revealSettingsPopover.hidden = true;
const subtitle = document.querySelector('.timeline-title-block span');
if (subtitle) subtitle.textContent = NO_FX
  ? 'No-FX geometry test'
  : STAGED_REVEAL
    ? 'Experimental staged reveal'
    : 'Clean crossfade';

// ---------------------------------------------------------------------------
// Stage background is intentionally fixed in the production UI.
// ---------------------------------------------------------------------------

if (stageBackground) stageBackground.style.background = '#f6f6f3';

// ---------------------------------------------------------------------------
// World textures — ONE canvas per world, shared by both physical screens.
// ---------------------------------------------------------------------------

const defaultUIs = await loadDefaultUIs();

const WORLD_WIDTH = 1600;
const WORLD_HEIGHT = 1125;

function makeWorldCanvas() {
  const canvas = document.createElement('canvas');
  canvas.width = WORLD_WIDTH;
  canvas.height = WORLD_HEIGHT;
  const context = canvas.getContext('2d');
  context.fillStyle = '#101418';
  context.fillRect(0, 0, WORLD_WIDTH, WORLD_HEIGHT);
  return canvas;
}

function createCanvasTexture(canvas) {
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = renderer.capabilities.getMaxAnisotropy();
  texture.wrapS = THREE.ClampToEdgeWrapping;
  texture.wrapT = THREE.ClampToEdgeWrapping;
  return texture;
}

const worldCanvases = { reality: makeWorldCanvas(), redblack: makeWorldCanvas() };
const worldTextures = {
  reality: createCanvasTexture(worldCanvases.reality),
  redblack: createCanvasTexture(worldCanvases.redblack),
};

const uiReferenceEye = new THREE.Vector3(0, 0, 40);
const innerUIFrame = new THREE.Vector4(-7.89935, .34562 - 5.8974, 15.7987, 11.1035);
const outerUIFrame = new THREE.Vector4(.23396, .27173 - 5.8974, 7.73936, 11.2513)
  .multiplyScalar((uiReferenceEye.z - .24948) / (uiReferenceEye.z - .825538));

for (const kind of ['inner', 'outer']) {
  const defaultTextures = {};
  for (const [theme, canvases] of Object.entries(defaultUIs)) defaultTextures[theme] = createCanvasTexture(canvases[kind]);
  const material = new THREE.MeshBasicMaterial({ map: defaultTextures[uiTheme], toneMapped: false });
  screens[kind] = {
    material,
    defaultTextures,
    frame: { value: (kind === 'inner' ? innerUIFrame : outerUIFrame).clone() },
    gradient: { value: new THREE.Vector2(kind === 'inner' ? .5 : 0, kind === 'inner' ? 0 : 1) },
    pixel: { value: new THREE.Vector2(1 / canvasesPixelWidth(defaultUIs[uiTheme][kind]), 1 / defaultUIs[uiTheme][kind].height) },
    target: { value: defaultTextures[uiTheme] },
  };
}

function canvasesPixelWidth(canvas) {
  return canvas.width;
}

// Custom world: both screens become viewports into the SAME two panoramas.
function applyCustomWorld() {
  const target = customReady.redblack ? worldTextures.redblack : worldTextures.reality;
  for (const [kind, screen] of Object.entries(screens)) {
    screen.material.map = worldTextures.reality;
    screen.target.value = target;
    screen.frame.value.copy(innerUIFrame);
    screen.gradient.value.set(.5, kind === 'inner' ? 0 : 1);
    screen.pixel.value.set(1 / WORLD_WIDTH, 1 / WORLD_HEIGHT);
  }
}

function showDefaultUI() {
  for (const [kind, screen] of Object.entries(screens)) {
    const texture = screen.defaultTextures[uiTheme];
    screen.material.map = texture;
    screen.target.value = texture;
    screen.frame.value.copy(kind === 'inner' ? innerUIFrame : outerUIFrame);
    screen.gradient.value.set(kind === 'inner' ? .5 : 0, kind === 'inner' ? 0 : 1);
    screen.pixel.value.set(1 / texture.image.width, 1 / texture.image.height);
  }
  document.querySelectorAll('[data-ui-theme]').forEach(button => button.setAttribute('aria-selected', String(button.dataset.uiTheme === uiTheme)));
}

document.querySelectorAll('[data-ui-theme]').forEach(button => button.addEventListener('click', () => {
  if (button.dataset.uiTheme === 'custom') {
    realityInput.click();
    return;
  }
  uiTheme = button.dataset.uiTheme;
  showDefaultUI();
}));

// ---------------------------------------------------------------------------
// Upload pipeline — one image fills ONE world canvas; no per-screen crops.
// ---------------------------------------------------------------------------

function drawWorld(img, canvas, texture) {
  const context = canvas.getContext('2d');
  context.fillStyle = '#101418';
  context.fillRect(0, 0, canvas.width, canvas.height);
  const scale = Math.min(canvas.width / img.width, canvas.height / img.height);
  const width = img.width * scale;
  const height = img.height * scale;
  context.drawImage(img, (canvas.width - width) / 2, (canvas.height - height) / 2, width, height);
  texture.needsUpdate = true;
}

async function decodeFile(file) {
  const url = URL.createObjectURL(file);
  const img = new Image();
  img.src = url;
  try { await img.decode(); return img; }
  finally { URL.revokeObjectURL(url); }
}

function updateSourceUI() {
  document.querySelectorAll('[data-ui-theme]').forEach(button => button.setAttribute('aria-selected', String(uiTheme === 'custom' && button.dataset.uiTheme === 'custom')));
  redBlackButton.classList.toggle('is-loaded', customReady.redblack);
  redBlackButton.textContent = customReady.redblack ? 'RedBlack ✓' : 'RedBlack';
}

realityInput.addEventListener('change', async () => {
  const file = realityInput.files[0];
  if (!file) return;
  try {
    const img = await decodeFile(file);
    drawWorld(img, worldCanvases.reality, worldTextures.reality);
    customReady.reality = true;
    uiTheme = 'custom';
    applyCustomWorld();
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
    drawWorld(img, worldCanvases.redblack, worldTextures.redblack);
    customReady.redblack = true;
    uiTheme = 'custom';
    applyCustomWorld();
    setPlaying(false); setAngle(0); updateSourceUI();
  } catch (error) {
    console.error(error);
    alert('Unable to read the RedBlack image. Choose a PNG, JPG, or WebP file.');
  } finally { redBlackInput.value = ''; }
});

redBlackButton?.addEventListener('click', () => {
  if (!customReady.reality) { alert('Upload the Reality image first.'); return; }
  redBlackInput.click();
});

// ---------------------------------------------------------------------------
// Timing — simple geometry-driven world mix; debug override for acceptance.
// ---------------------------------------------------------------------------

function smooth01(t) {
  const x = THREE.MathUtils.clamp(t, 0, 1);
  return x * x * (3 - 2 * x);
}

function smoothRange(value, start, end) {
  return smooth01((value - start) / Math.max(end - start, 1e-6));
}

function geometrySignal(angleDeg) {
  const visualAngle = THREE.MathUtils.clamp(angleDeg, 0, 90);
  return 1 - Math.cos(THREE.MathUtils.degToRad(visualAngle));
}

function worldMixFromGeometry(g) {
  return smoothRange(g, 0.10, 0.92);
}

function updateTimelineUI(progress, mix) {
  const progressPercent = Math.round(progress * 100);
  const worldPercent = Math.round(mix * 100);
  if (progressReadout) progressReadout.textContent = `${progressPercent}%`;
  if (angleReadout) angleReadout.textContent = `${Math.round(angle)}°`;
  if (revealReadout) revealReadout.textContent = `World ${worldPercent}%`;
  if (revealSummaryValue) revealSummaryValue.textContent = `${worldPercent}%`;
  if (strategySummary) strategySummary.textContent = NO_FX ? 'No FX' : 'World';
  slider.style.setProperty('--progress', `${progressPercent}%`);
  snapButtons.forEach(button => button.classList.toggle('is-current', Math.abs(angle - Number(button.dataset.snap)) < .6));
}

function updateFraming() {
  // Geometry lock: the fixed/right panel never recenters or rescales.
  // Only the physical left panel moves around the hinge.
  phone.position.x = FIXED_PANEL_ANCHOR_X;
  phone.scale.setScalar(1);
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
  const mix = worldMixOverride ?? (active ? worldMixFromGeometry(geometrySignal(angle)) : 0);
  worldMix.value = mix;
  // Manual mode maps the master mix into the three stages; record mode overrides per frame.
  if (!recording) {
    uLeak.value = smoothRange(mix, 0.0, 0.45);
    uCollapse.value = smoothRange(mix, 0.30, 0.75);
    uLock.value = smoothRange(mix, 0.62, 0.90);
  }
  // Original external-cover rule: black out the cover at fully open.
  if (screens.outer) screens.outer.material.color.setScalar(angle >= 180 ? 0 : 1);
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

// ---------------------------------------------------------------------------
// Shaders — original fold geometry + original screen shader with worldMix.
// ---------------------------------------------------------------------------

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

// Original chuspeeism screenShader, extended with a second world texture and a
// shared worldMix. Coordinate/blur math is verbatim the original.
const screenShader = `
uniform float foldAngle;
uniform vec2 uiPixel;
uniform vec4 uiFrame;
uniform vec2 uiGradient;
uniform vec3 uiReferenceEye;
uniform sampler2D transitionTarget;
uniform float worldMix;
uniform float uLeak;
uniform float uCollapse;
uniform float uLock;
uniform float uImpact;
uniform float uPulse;
uniform float uTransActive;
uniform float uNoFx;
uniform float uUseStagedReveal;
varying vec3 vUIPosition;

// V5.0.2 Reveal Direction Fix.
// Physical unfolding exposes the moving INNER LEFT half from the hinge (u≈0.5)
// toward the left edge (u=0). The leak therefore propagates hinge -> left only;
// it no longer grows symmetrically onto the fixed right half.
float leakPattern(vec2 uv) {
  float center = 0.5
    + 0.012 * sin(uv.y * 23.0)
    + 0.020 * sin(uv.y * 57.0 + 1.7)
    + 0.014 * sin(uv.y * 91.0 + 4.2);
  float leftDistance = clamp((center - uv.x) / max(center, 0.001), 0.0, 1.0);
  float g = 1.0 - leftDistance;
  float movingHalf = step(uv.x, center + 0.002);
  float validUV = step(0.0, uv.x) * step(uv.x, 1.0)
    * step(0.0, uv.y) * step(uv.y, 1.0);
  float j = fract(sin(dot(floor(uv * vec2(220.0, 160.0)), vec2(12.9898, 78.233))) * 43758.5453);
  return clamp(g + (j - 0.5) * 0.10, 0.0, 1.0) * movingHalf * validUV;
}

// Tokyo Tower anchor measured on the final B asset (2670x1878).
float towerMask(vec2 uv) {
  vec2 d = (uv - vec2(0.730, 0.430)) / vec2(0.085, 0.300);
  return 1.0 - smoothstep(0.7, 1.0, length(d));
}

float towerContentMask(vec2 uv, vec3 bCol) {
  float region = towerMask(uv);
  float lum = dot(bCol, vec3(0.299, 0.587, 0.114));
  float warm = clamp((bCol.r - bCol.b) * 2.4 + (bCol.r - bCol.g) * 0.8, 0.0, 1.0);
  float bright = smoothstep(0.22, 0.58, lum);
  return region * warm * bright;
}

// Staged reveal of world B: hinge leak first, city collapse next, tower locks last.
float stagedReveal(vec2 uv, vec3 bCol) {
  float leak = leakPattern(uv);
  float lumB = dot(bCol, vec3(0.299, 0.587, 0.114));
  float city = 1.0 - smoothstep(0.045, 0.15, lumB);
  float tower = towerContentMask(uv, bCol);
  float base = smoothstep(1.0 - uLeak - 0.06, 1.0 - uLeak + 0.06, leak);
  base *= step(0.001, uLeak); // no leak stage -> no speckle from the noise term
  float reveal = base;
  reveal = mix(reveal, clamp(base + uCollapse, 0.0, 1.0), city);
  reveal = mix(reveal, clamp(base + uLock, 0.0, 1.0), tower);
  return clamp(reveal, 0.0, 1.0);
}

float activeReveal(vec2 uv, vec3 bCol) {
  // Production default: uniform A -> B crossfade across the whole panorama.
  // No moving seam, no noisy boundary, no directional wipe.
  return mix(worldMix, stagedReveal(uv, bCol), uUseStagedReveal);
}

vec3 screenColor() {
  // Intersect the fixed front-view ray with the unfolded inner-screen plane.
  float depth = (0.24948 - uiReferenceEye.z) / (vUIPosition.z - uiReferenceEye.z);
  vec2 projected = uiReferenceEye.xy + (vUIPosition.xy - uiReferenceEye.xy) * depth;
  vec2 sourceUV = (projected - uiFrame.xy) / uiFrame.zw;
  #ifdef INNER_UI
    // V5.0.1 Open Endpoint Repair:
    // In the final ~0.8° of the unfold, converge from the projected panorama
    // coordinate back to the authored mesh UV. This affects only the Open
    // endpoint and prevents sourceUV from overshooting the physical screen
    // boundary by sub-pixels.
    float endpointLock = 1.0 - smoothstep(0.0, 0.013962634, abs(foldAngle));
    vec2 endpointUV = clamp(vMapUv, uiPixel * 0.5, vec2(1.0) - uiPixel * 0.5);
    sourceUV = mix(sourceUV, endpointUV, endpointLock);
    float progress = clamp(foldAngle / 1.570796327, 0.0, 1.0);
  #else
    // Anchor the image to the projected hinge-side edge of the outer screen.
    float c = cos(foldAngle), s = sin(foldAngle);
    vec2 hingeEdge = vec2(-0.23396, -0.27463 - 0.275454);
    vec2 foldedEdge = vec2(c * hingeEdge.x + s * hingeEdge.y,
      -s * hingeEdge.x + c * hingeEdge.y + 0.275454);
    float edgeDepth = (0.24948 - uiReferenceEye.z) / (foldedEdge.y - uiReferenceEye.z);
    float anchorX = uiReferenceEye.x + (foldedEdge.x - uiReferenceEye.x) * edgeDepth;
    sourceUV.x = uiGradient.x + (projected.x - anchorX) / uiFrame.z;
    float progress = clamp((3.141592654 - foldAngle) / 1.570796327, 0.0, 1.0);
  #endif
  float edge = (sourceUV.x - uiGradient.x) / (uiGradient.y - uiGradient.x);
  float motion = smoothstep(0.0, 1.0, progress);
  float blurGradient = clamp(edge, 0.0, 1.0);
  float darkenGradient = clamp((edge - 0.2) / 0.8, 0.0, 1.0);
  float effect = motion * pow(darkenGradient, 1.35);
  float radius = 72.0 * motion * pow(blurGradient, 1.35);
  radius *= 1.0 - 0.65 * uTransActive; // keep the leak edge crisp mid-transition
  vec2 aa = max(fwidth(sourceUV), uiPixel * 0.5);
  vec2 dx = dFdx(sourceUV) / uiPixel;
  vec2 dy = dFdy(sourceUV) / uiPixel;
  float baseLod = log2(max(1.0, max(length(dx), length(dy))));
  vec2 coverage = smoothstep(-aa, aa, sourceUV)
    * (1.0 - smoothstep(vec2(1.0) - aa, vec2(1.0) + aa, sourceUV));
  #ifdef INNER_UI
    // At the exact Open endpoint the rounded physical mesh is already the
    // clipping boundary, so do not fade valid edge texels a second time.
    coverage = mix(coverage, vec2(1.0), endpointLock);
  #endif
  vec2 uvC = clamp(sourceUV, vec2(0.0), vec2(1.0));
  vec3 colA = textureLod(map, uvC, baseLod).rgb;
  vec3 colB = textureLod(transitionTarget, uvC, baseLod).rgb;
  float revealAmount = activeReveal(sourceUV, colB);
  vec3 color = mix(colA, colB, revealAmount) * coverage.x * coverage.y;
  if (radius > 0.0) {
    // Use the same mip level at zero blur, then increase it continuously.
    float lod = max(baseLod, log2(max(1.0, radius)));
    vec2 footprint = max(aa, uiPixel * radius * 0.75);
    color = vec3(0.0);
    for (int y = -2; y <= 2; y++) {
      for (int x = -2; x <= 2; x++) {
        float wx = x == 0 ? 6.0 : (abs(x) == 1 ? 4.0 : 1.0);
        float wy = y == 0 ? 6.0 : (abs(y) == 1 ? 4.0 : 1.0);
        vec2 sampleUV = sourceUV + vec2(float(x), float(y)) * uiPixel * radius;
        // Blur the image and its coverage together so color spreads into the black margin.
        vec2 tapCoverage = smoothstep(-footprint, footprint, sampleUV)
          * (1.0 - smoothstep(vec2(1.0) - footprint, vec2(1.0) + footprint, sampleUV));
        float tapValid = step(0.0, sampleUV.x) * step(sampleUV.x, 1.0)
          * step(0.0, sampleUV.y) * step(sampleUV.y, 1.0);
        tapCoverage *= tapValid;
        vec2 clampedUV = clamp(sampleUV, vec2(0.0), vec2(1.0));
        vec3 tapA = textureLod(map, clampedUV, lod).rgb;
        vec3 tapB = textureLod(transitionTarget, clampedUV, lod).rgb;
        float tapReveal = activeReveal(sampleUV, tapB);
        color += mix(tapA, tapB, tapReveal) * tapCoverage.x * tapCoverage.y * wx * wy / 256.0;
      }
    }
  }
  color *= 1.0 - min(1.0, effect * 2.0);

  // Impact @2.15s: one-frame white-red flash + visible RGB split (screen-space
  // only, geometry untouched).
  if (uNoFx < 0.5 && uImpact > 0.001) {
    float split = uImpact * 7.0 * uiPixel.x;
    vec2 uvR = clamp(sourceUV + vec2(split, 0.0), vec2(0.0), vec2(1.0));
    vec2 uvB = clamp(sourceUV - vec2(split, 0.0), vec2(0.0), vec2(1.0));
    vec3 rB2 = textureLod(transitionTarget, uvR, baseLod).rgb;
    vec3 bB2 = textureLod(transitionTarget, uvB, baseLod).rgb;
    float rr = mix(textureLod(map, uvR, baseLod).rgb.r, rB2.r, activeReveal(uvR, rB2));
    float bb = mix(textureLod(map, uvB, baseLod).rgb.b, bB2.b, activeReveal(uvB, bB2));
    color.r = mix(color.r, rr, uImpact);
    color.b = mix(color.b, bb, uImpact);
    float towerImpact = towerContentMask(sourceUV, colB);
    color = mix(color, vec3(1.0, 0.97, 0.94), uImpact * (0.38 + 0.10 * towerImpact));
  }

  // Lv1 pulse @3.18s: tower-centered warm glow + ~25% response on warm windows.
  if (uNoFx < 0.5 && uPulse > 0.001) {
    float tw = towerContentMask(sourceUV, colB);
    float lumC = dot(color, vec3(0.299, 0.587, 0.114));
    float warm = clamp((color.r - color.b) * 2.0, 0.0, 1.0) * smoothstep(0.12, 0.35, lumC);
    color += vec3(1.0, 0.62, 0.25) * uPulse * (tw * 0.22 + warm * 0.10);
  }

  return color;
}
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
    const kind = object.name === 'UXtsBZYlaUvHoEh'
      ? 'inner'
      : object.name === 'hhgAIoCGsHXeDPY'
        ? 'outer'
        : null;
    const material = kind ? screens[kind].material : object.material.clone();

    if (kind) {
      // Kept from the original: baked UVs exist so USE_MAP compiles, but the
      // screen shader samples exclusively through the projection below.
      const p = geometry.attributes.position;
      const uv = new Float32Array(p.count * 2);
      for (let i = 0; i < p.count; i++) {
        uv[i * 2] = kind === 'inner'
          ? (p.getX(i) + 7.89935) / 15.7987
          : (-.23396 - p.getX(i)) / 7.73936;
        uv[i * 2 + 1] = kind === 'inner'
          ? (p.getY(i) + 5.8974 - .34562) / 11.1035
          : (p.getY(i) + 5.8974 - .27173) / 11.2513;
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
          shader.uniforms.uiFrame = screen.frame;
          shader.uniforms.uiGradient = screen.gradient;
          shader.uniforms.uiPixel = screen.pixel;
          shader.uniforms.uiReferenceEye = { value: uiReferenceEye };
          shader.uniforms.transitionTarget = screen.target;
          shader.uniforms.worldMix = worldMix;
          shader.uniforms.uLeak = uLeak;
          shader.uniforms.uCollapse = uCollapse;
          shader.uniforms.uLock = uLock;
          shader.uniforms.uImpact = uImpact;
          shader.uniforms.uPulse = uPulse;
          shader.uniforms.uTransActive = uTransActive;
          shader.uniforms.uNoFx = uNoFx;
          shader.uniforms.uUseStagedReveal = uUseStagedReveal;

          shader.vertexShader = `varying vec3 vUIPosition;\n${shader.vertexShader}`;
          shader.vertexShader = shader.vertexShader.replace('#include <project_vertex>', `
            vUIPosition = transformed;
            #include <project_vertex>
          `);

          shader.fragmentShader = shader.fragmentShader
            .replace('#include <map_pars_fragment>', `
              #include <map_pars_fragment>
              ${kind === 'inner' ? '#define INNER_UI' : ''}
              ${screenShader}
            `)
            .replace('#include <map_fragment>', 'diffuseColor.rgb *= screenColor();');
        }
      };
      material.customProgramCacheKey = () => `v44-${flexible ? 'flexible' : moving ? 'cover' : 'fixed'}-${kind || 'body'}`;
    }

    const mesh = new THREE.Mesh(geometry, material);
    mesh.name = object.name;
    mesh.frustumCulled = false;
    phone.add(mesh);

    if (moving && !kind && !flexible) {
      mesh.userData.isMovingShell = true;
      movingShellMeshes.push(mesh);
    }

    count[flexible ? 'flexible' : moving ? 'moving' : 'fixed']++;
  });
  console.info(`${BUILD_VERSION} original screen shader rebuild ready`, {
    ...count,
    sourceMeshes: phone.children.length,
    movingShellMeshes: movingShellMeshes.length,
    oneCanvasPerWorld: true,
    coverRule: 'original-black-at-open',
    framing: 'fixed-right-panel-anchor; no dynamic recenter/scale',
    openEndpointRepair: 'projected-uv -> authored-uv + endpoint coverage lock',
    revealMode: STAGED_REVEAL ? 'experimental-staged (?reveal=staged)' : 'production-clean-crossfade',
    connectionArtifactGuard: 'valid-panorama-only + no blur bleed',
    towerHighlightGuard: 'content-aware tower mask; no broad ellipse glow',
    noFxGeometryTest: '?nofx=1',
  });

  updateSourceUI();
  document.querySelectorAll('.control-dock button, .control-dock input').forEach(element => {
    if (element !== revealSettingsButton) element.disabled = false;
  });
  ready = true;
  setPlaying(false);
  setAngle(0);
  if (RECORD_AUTO) startRecord();
} catch (error) {
  alert('Unable to load the model. Refresh the page to try again.');
  console.error(error);
}

// Debug hooks for acceptance (window.__duo.setAngle / setWorldMix / setStages / startRecord).
function recordStage(t, a, b) {
  return THREE.MathUtils.clamp((t - a) / (b - a), 0, 1);
}

function startRecord() {
  recordT0 = performance.now();
  recording = true;
  setPlaying(false);
}

// Lv3 record timeline (case-study §6): real fold drives geometry, three stage
// uniforms drive the world hand-off on their own synced schedule.
function driveRecord(nowMs) {
  const t = (nowMs - recordT0) / 1000;
  const ap = THREE.MathUtils.smoothstep(t, 1.20, 2.15);
  setAngle(ap * 180);
  uLeak.value = STAGED_REVEAL ? recordStage(t, 1.65, 1.90) : 0;
  uCollapse.value = STAGED_REVEAL ? recordStage(t, 1.90, 2.10) : 0;
  uLock.value = STAGED_REVEAL ? recordStage(t, 2.10, 2.15) : 0;
  // Blur suppression and red rim belong to the staged experiment, not the
  // clean production crossfade.
  uTransActive.value = STAGED_REVEAL
    ? THREE.MathUtils.smoothstep(t, 1.55, 1.70) * (1 - THREE.MathUtils.smoothstep(t, 2.30, 2.45))
    : 0;
  uImpact.value = NO_FX ? 0 : (t >= 2.15 && t < 2.23 ? 1 - (t - 2.15) / 0.08 : 0);
  uPulse.value = NO_FX ? 0 : (t >= 3.18 && t <= 3.98 ? Math.sin(((t - 3.18) / 0.80) * Math.PI) : 0);
  const rw = STAGED_REVEAL ? uTransActive.value : 0;
  rim.intensity = 2 + 3.2 * rw;
  rim.color.setRGB(0.91 + 0.09 * rw, 0.93 - 0.62 * rw, 0.96 - 0.68 * rw);
  document.documentElement.dataset.recordT = t.toFixed(2);
  if (t > 5.6) {
    recording = false;
    uImpact.value = 0;
    uTransActive.value = 0;
    rim.intensity = 2;
    rim.color.setHex(0xe8edf5);
    document.documentElement.dataset.recordDone = '1';
  }
}

window.__duo = {
  setAngle: value => { setPlaying(false); playbackTime = 0; recording = false; setAngle(Number(value)); },
  setWorldMix: value => { worldMixOverride = value === null || value === undefined ? null : Number(value); setAngle(angle); },
  setStages: (leak, collapse, lock) => { uLeak.value = Number(leak); uCollapse.value = Number(collapse); uLock.value = Number(lock); },
  setImpact: value => { uImpact.value = Number(value); },
  setPulse: value => { uPulse.value = Number(value); },
  startRecord,
  get state() {
    return {
      angle, worldMix: worldMix.value, ready, recording,
      stages: { leak: uLeak.value, collapse: uCollapse.value, lock: uLock.value },
      geometryLock: { fixedPanelAnchorX: FIXED_PANEL_ANCHOR_X, noDynamicScale: true, noFx: NO_FX },
      revealMode: STAGED_REVEAL ? 'staged' : 'clean-crossfade',
      customReady: { ...customReady },
    };
  },
};

let lastTime = performance.now();
renderer.setAnimationLoop(now => {
  const delta = Math.min((now - lastTime) / 1000, .05);
  lastTime = now;

  if (ready && playing) {
    playbackTime += delta;
    if (playbackTime < .45) {
      setAngle(0);
    } else if (playbackTime < 2.25) {
      const p = (playbackTime - .45) / 1.8;
      const ease = p * p * (3 - 2 * p);
      setAngle(THREE.MathUtils.lerp(0, 180, ease));
    } else if (playbackTime < 3.10) {
      setAngle(180);
    } else {
      setAngle(180);
      setPlaying(false);
    }
  }

  if (ready && recording) driveRecord(now);

  renderer.render(scene, camera);
});
