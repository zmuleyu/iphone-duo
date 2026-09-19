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

const BUILD_VERSION = 'v5.1';
const PRODUCTION_BASELINE_ID = 'v5.1-production-fold';

const viewport = document.querySelector('#viewport');
const slider = document.querySelector('#angle');
const play = document.querySelector('#play');
const playLabel = document.querySelector('#play-label');
const closedButton = document.querySelector('#closed-button');
const openButton = document.querySelector('#open-button');
const progressReadout = document.querySelector('#progress-readout');
const angleReadout = document.querySelector('#angle-readout');
const angleBubble = document.querySelector('#angle-bubble');
const sequenceStrip = document.querySelector('#sequence-strip');
const sequencePlayhead = document.querySelector('#sequence-playhead');
const revealReadout = document.querySelector('#reveal-readout');
const revealSummaryValue = document.querySelector('#reveal-summary-value');
const strategySummary = document.querySelector('#strategy-summary');
const snapButtons = [...document.querySelectorAll('[data-snap]')];
const realityInput = document.querySelector('#ui-upload');
const redBlackInput = document.querySelector('#redblack-upload');
const redBlackButton = document.querySelector('#redblack-button');
const revealSettingsButton = document.querySelector('#reveal-settings');
const revealSettingsPopover = document.querySelector('#reveal-settings-popover');
const closedHoldInput = document.querySelector('#closed-hold');
const unfoldDurationInput = document.querySelector('#unfold-duration');
const openHoldInput = document.querySelector('#open-hold');
const foldEasingSelect = document.querySelector('#fold-easing');
const closedHoldValue = document.querySelector('#closed-hold-value');
const unfoldDurationValue = document.querySelector('#unfold-duration-value');
const openHoldValue = document.querySelector('#open-hold-value');
const foldTotalReadout = document.querySelector('#fold-total-readout');
const foldMotionReset = document.querySelector('#fold-motion-reset');
const foldPresetButtons = [...document.querySelectorAll('[data-fold-preset]')];
const customSourceButton = document.querySelector('[data-ui-theme="custom"]');
const qaPanel = document.querySelector('#master-pair-qa-panel');
const qaSummary = document.querySelector('#qa-summary');
const qaRealityMeta = document.querySelector('#qa-reality-meta');
const qaRedBlackMeta = document.querySelector('#qa-redblack-meta');
const qaPairMeta = document.querySelector('#qa-pair-meta');
const qaLockPairButton = document.querySelector('#qa-lock-pair');
const qaResetButton = document.querySelector('#qa-reset');
const qaAngleButtons = [...document.querySelectorAll('[data-qa-angle]')];
const qaPassButtons = [...document.querySelectorAll('[data-qa-pass]')];
const qaFailButtons = [...document.querySelectorAll('[data-qa-fail]')];
const qaRows = [...document.querySelectorAll('[data-qa-row]')];
const recordingPanel = document.querySelector('#recording-editing-panel');
const recordingSummary = document.querySelector('#recording-summary');
const recordFormatButtons = [...document.querySelectorAll('[data-record-format]')];
const recordFpsButtons = [...document.querySelectorAll('[data-record-fps]')];
const recordGuideButtons = [...document.querySelectorAll('[data-record-guide]')];
const recordGuideToggle = document.querySelector('#record-guide-toggle');
const enterRecordingModeButton = document.querySelector('#enter-recording-mode');
const recordSafeFrame = document.querySelector('#record-safe-frame');
const recordSafeFrameLabel = document.querySelector('#record-safe-frame-label');
const recordHud = document.querySelector('#record-hud');
const recordModeStatus = document.querySelector('#record-mode-status');
const recordModeMeta = document.querySelector('#record-mode-meta');
const recordModeTime = document.querySelector('#record-mode-time');
const recordStartButton = document.querySelector('#record-start');
const recordReplayButton = document.querySelector('#record-replay');
const recordResetButton = document.querySelector('#record-reset');
const recordExitButton = document.querySelector('#record-exit');
const exportPanel = document.querySelector('#export-acceptance-panel');
const stagePanels = {
  setup: document.querySelector('#setup-panel'),
  quality: document.querySelector('#master-pair-qa-panel'),
  capture: document.querySelector('#recording-editing-panel'),
  accept: document.querySelector('#export-acceptance-panel'),
};
const exportSummary = document.querySelector('#export-acceptance-summary');
const exportFormatButtons = [...document.querySelectorAll('[data-export-format]')];
const exportLoadButton = document.querySelector('#export-load');
const exportResetButton = document.querySelector('#export-reset');
const exportReviewInput = document.querySelector('#export-review-input');
const exportFileMeta = document.querySelector('#export-file-meta');
const exportResolutionMeta = document.querySelector('#export-resolution-meta');
const exportAutoMeta = document.querySelector('#export-auto-meta');
const exportReviewWrap = document.querySelector('#export-review-wrap');
const exportReviewVideo = document.querySelector('#export-review-video');
const exportReviewHingeButton = document.querySelector('#export-review-hinge');
const exportReviewEndButton = document.querySelector('#export-review-end');
const exportPassButtons = [...document.querySelectorAll('[data-export-pass]')];
const exportFailButtons = [...document.querySelectorAll('[data-export-fail]')];
const exportRows = [...document.querySelectorAll('[data-export-row]')];

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
// Capture runs (?cap=1) force 2x supersampling for crisp downscaled delivery.
// V5.9: 1.5x capture supersample (2x@60fps starved the frame clock, frozen
// spans) + opaque white clear so captures land on Apple-white, not alpha-black.
renderer.setPixelRatio(new URLSearchParams(location.search).has('cap') ? 1.25 : Math.min(devicePixelRatio, 2)); // V6.3: original-master VP9 throughput
renderer.setClearColor(new URLSearchParams(location.search).has('cap') ? 0xffffff : 0x000000,
  new URLSearchParams(location.search).has('cap') ? 1 : 0);
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
const PRODUCTION_BASELINE = true;
const DEV_EXPERIMENTS = QUERY.has('dev');
const NO_FX = QUERY.has('nofx');
// V5.1 production lock: clean crossfade is the only production reveal.
// Historical staged reveal remains accessible only behind explicit ?dev=1.
const STAGED_REVEAL = DEV_EXPERIMENTS
  && !NO_FX
  && (QUERY.get('reveal') === 'staged' || QUERY.has('staged'));
const LEGACY_TOWER_FX = false; // Tower/Bird FX stay outside the V5.1 production baseline
document.documentElement.dataset.productionBaseline = PRODUCTION_BASELINE_ID;
document.documentElement.dataset.devExperiments = DEV_EXPERIMENTS ? '1' : '0';

const bend = { value: Math.PI };
const worldMix = { value: 0 };
// Lv3 staged transition: Red Leak -> Black Collapse -> Yellow Lock
const uLeak = { value: 0 };
const uCollapse = { value: 0 };
const uLock = { value: 0 };
const uImpact = { value: 0 };      // 1-frame flash + RGB split @2.15s
// V5.6 bezel light transition: red crease leak -> titanium sweep -> open pop.
const uBezel = { value: 0 };
const uBezelPop = { value: 0 };
let uBezelPopHold = false;
const REDUCED_MOTION = matchMedia('(prefers-reduced-motion: reduce)').matches;
const BEZEL_DEBUG = QUERY.has('bezeldebug');
const uPulse = { value: 0 };       // Lv1 tower warm pulse @3.18s
const uTransActive = { value: 0 }; // staged-only blur/rim treatment
const uNoFx = { value: NO_FX ? 1 : 0 };
const uUseStagedReveal = { value: STAGED_REVEAL ? 1 : 0 };
// V5.9: tower-region reveal follows uTowerMix (record drives it late for the
// two-beat narrative); uFoldBlurScale trims the frozen oblique-angle blur on
// the record path so panels read rigid. Both are identity in preview.
const uTowerMix = { value: 0 };
const uFoldBlurScale = { value: 1 };
const uTowerBoost = { value: 0 }; // V5.9: hero glow (V6.2: disabled in record — pocket flip IS the beat)
const uRevealFront = { value: -1 }; // V6.2: spatial left->right wavefront (record drives; -1 = off)

let angle = 0;
let playing = false;
let playbackTime = 0;
let ready = false;
let uiTheme = 'wallpaper';
let worldMixOverride = null;
let recording = false;
let recordT0 = 0;
let recordFrameIndex = 0;
let recordHasRun = false;
const RECORD_AUTO = QUERY.has('record');
const RECORDING_MODE_AUTO = RECORD_AUTO || QUERY.has('studio');
const RECORD_FORMATS = Object.freeze({
  '16x9': '16:9',
  '1x1': '1:1',
  '9x16': '9:16',
});
const requestedRecordFormat = QUERY.get('format');
let recordFormat = Object.hasOwn(RECORD_FORMATS, requestedRecordFormat)
  ? requestedRecordFormat
  : '16x9';
const requestedRecordFps = Number(QUERY.get('fps'));
let recordFps = requestedRecordFps === 30 ? 30 : 60;
let recordGuide = QUERY.get('guide') !== 'off';
let recordingMode = false;
const EXPORT_CRITERIA = Object.freeze(['motion', 'hinge', 'endpoint', 'crop', 'compression']);
const exportAcceptance = Object.fromEntries(
  Object.keys(RECORD_FORMATS).map(format => [format, {
    verdicts: Object.fromEntries(EXPORT_CRITERIA.map(key => [key, null])),
    file: null,
    objectUrl: null,
    videoMeta: null,
  }]),
);
const captureHistory = Object.fromEntries(
  Object.keys(RECORD_FORMATS).map(format => [format, null]),
);
const screens = {};
const customReady = { reality: false, redblack: false };
const sourceMeta = { reality: null, redblack: null };
const QA_ANGLES = Object.freeze([0, 45, 90, 135, 180]);
const qaState = {
  locked: false,
  currentAngle: 0,
  verdicts: Object.fromEntries(QA_ANGLES.map(value => [value, null])),
};
const movingShellMeshes = [];

const FOLD_PRESETS = Object.freeze({
  fast: Object.freeze({
    label: 'Fast Viral',
    closedHold: 0.18,
    unfoldDuration: 1.15,
    openHold: 0.52,
    easing: 'smooth',
    motionBlur: 'natural',
  }),
  cinematic: Object.freeze({
    label: 'Cinematic',
    closedHold: 0.40,
    unfoldDuration: 1.85,
    openHold: 0.85,
    easing: 'cinematic',
    motionBlur: 'natural',
  }),
  demo: Object.freeze({
    label: 'Slow Demo',
    closedHold: 0.65,
    unfoldDuration: 2.80,
    openHold: 1.20,
    easing: 'smooth',
    motionBlur: 'off',
  }),
});
const requestedFoldPreset = QUERY.get('motion');
const DEFAULT_FOLD_PRESET = Object.hasOwn(FOLD_PRESETS, requestedFoldPreset)
  ? requestedFoldPreset
  : 'fast';
const DEFAULT_FOLD_MOTION = Object.freeze({
  closedHold: FOLD_PRESETS[DEFAULT_FOLD_PRESET].closedHold,
  unfoldDuration: FOLD_PRESETS[DEFAULT_FOLD_PRESET].unfoldDuration,
  openHold: FOLD_PRESETS[DEFAULT_FOLD_PRESET].openHold,
  easing: FOLD_PRESETS[DEFAULT_FOLD_PRESET].easing,
});
const foldMotion = { ...DEFAULT_FOLD_MOTION };
let activeFoldPreset = DEFAULT_FOLD_PRESET;
let applyingFoldPreset = false;

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

// V5.8 lock-screen chrome (?ui=1 or __duo.setScreenChrome): render-faithful Duo
// lock screen painted into the RedBlack world canvas only (open state). Layout
// follows the open-state reference: big light-weight 9:41 + date top-center,
// small Wi-Fi top-right, flashlight/camera frosted circles stacked bottom-right,
// home indicator bottom-center. Reality/cover world stays pure wallpaper.
let screenChrome = QUERY.has('ui');
const worldImages = { reality: null, redblack: null };

function drawLockChrome(canvas) {
  const ctx = canvas.getContext('2d');
  const w = canvas.width;
  const h = canvas.height;
  const padX = Math.round(w * 0.024);
  ctx.save();
  ctx.fillStyle = '#ffffff';
  ctx.strokeStyle = '#ffffff';
  ctx.shadowColor = 'rgba(0,0,0,0.45)';
  ctx.shadowBlur = h * 0.006;
  ctx.shadowOffsetY = h * 0.002;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  // Date + big time (top-center)
  ctx.font = `400 ${Math.round(h * 0.030)}px "Segoe UI Variable Display", "Segoe UI", -apple-system, sans-serif`;
  ctx.fillText('Wed Apr 1', w / 2, h * 0.068);
  ctx.font = `200 ${Math.round(h * 0.115)}px "Segoe UI Variable Display", "Segoe UI Light", "Segoe UI", -apple-system, sans-serif`;
  ctx.fillText('9:41', w / 2, h * 0.155);
  // Small Wi-Fi (top-right corner)
  const wifiX = w - padX;
  const wifiY = h * 0.055;
  ctx.lineWidth = Math.max(2, h * 0.004);
  ctx.lineCap = 'round';
  for (let k = 3; k >= 1; k--) {
    ctx.beginPath();
    ctx.arc(wifiX, wifiY, h * 0.007 * k + h * 0.004, Math.PI * 1.3, Math.PI * 1.7);
    ctx.stroke();
  }
  ctx.beginPath();
  ctx.arc(wifiX, wifiY, ctx.lineWidth * 0.7, 0, Math.PI * 2);
  ctx.fill();
  // Flashlight + camera frosted circles (stacked, bottom-right)
  const r = h * 0.037;
  const bx = w - padX - r;
  const byTorch = h * 0.78;
  const byCam = byTorch + r * 2.55;
  for (const cy of [byTorch, byCam]) {
    ctx.save();
    ctx.shadowColor = 'transparent';
    ctx.fillStyle = 'rgba(255,255,255,0.20)';
    ctx.beginPath();
    ctx.arc(bx, cy, r, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }
  ctx.fillStyle = '#ffffff';
  ctx.strokeStyle = '#ffffff';
  // Flashlight glyph
  ctx.lineWidth = Math.max(2, r * 0.11);
  ctx.beginPath();
  ctx.roundRect(bx - r * 0.20, byTorch - r * 0.42, r * 0.40, r * 0.30, r * 0.08);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(bx - r * 0.13, byTorch - r * 0.10);
  ctx.lineTo(bx - r * 0.08, byTorch + r * 0.40);
  ctx.lineTo(bx + r * 0.08, byTorch + r * 0.40);
  ctx.lineTo(bx + r * 0.13, byTorch - r * 0.10);
  ctx.closePath();
  ctx.fill();
  // Camera glyph
  ctx.beginPath();
  ctx.roundRect(bx - r * 0.46, byCam - r * 0.28, r * 0.92, r * 0.62, r * 0.14);
  ctx.fill();
  ctx.beginPath();
  ctx.roundRect(bx - r * 0.18, byCam - r * 0.40, r * 0.36, r * 0.14, r * 0.05);
  ctx.fill();
  ctx.save();
  ctx.globalCompositeOperation = 'destination-out';
  ctx.beginPath();
  ctx.arc(bx, byCam + r * 0.03, r * 0.19, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
  // Home indicator (bottom center)
  const hiW = w * 0.088;
  const hiH = Math.max(3, h * 0.0048);
  ctx.globalAlpha = 0.9;
  ctx.beginPath();
  ctx.roundRect((w - hiW) / 2, h - hiH * 2.6, hiW, hiH, hiH / 2);
  ctx.fill();
  ctx.restore();
}

function drawWorld(img, canvas, texture, chrome = false) {
  const context = canvas.getContext('2d');
  context.fillStyle = '#101418';
  context.fillRect(0, 0, canvas.width, canvas.height);
  const scale = Math.min(canvas.width / img.width, canvas.height / img.height);
  const width = img.width * scale;
  const height = img.height * scale;
  context.drawImage(img, (canvas.width - width) / 2, (canvas.height - height) / 2, width, height);
  if (chrome) drawLockChrome(canvas);
  texture.needsUpdate = true;
}

async function decodeFile(file) {
  const url = URL.createObjectURL(file);
  const img = new Image();
  img.src = url;
  try { await img.decode(); return img; }
  finally { URL.revokeObjectURL(url); }
}

function metaLabel(meta) {
  if (!meta) return 'Not loaded';
  return `${meta.width}×${meta.height} · ${meta.ratio.toFixed(4)}`;
}

function masterPairCheck() {
  const reality = sourceMeta.reality;
  const redblack = sourceMeta.redblack;
  if (!reality || !redblack) {
    return { ready: false, pass: false, sameDimensions: false, ratioDelta: null, targetDelta: null, text: 'Waiting' };
  }

  const targetRatio = WORLD_WIDTH / WORLD_HEIGHT;
  const ratioDelta = Math.abs(reality.ratio - redblack.ratio) / Math.max(reality.ratio, 1e-6);
  const targetDelta = Math.max(
    Math.abs(reality.ratio - targetRatio) / targetRatio,
    Math.abs(redblack.ratio - targetRatio) / targetRatio,
  );
  const sameDimensions = reality.width === redblack.width && reality.height === redblack.height;
  const ratioCompatible = ratioDelta <= 0.0015;
  const targetCompatible = targetDelta <= 0.005;
  const pass = sameDimensions && ratioCompatible && targetCompatible;

  let text = 'Geometry OK';
  if (!sameDimensions) text = 'Dimensions differ';
  else if (!ratioCompatible) text = 'Aspect mismatch';
  else if (!targetCompatible) text = 'Master ratio mismatch';

  return { ready: true, pass, sameDimensions, ratioDelta, targetDelta, text };
}

function resetQaVerdicts() {
  QA_ANGLES.forEach(value => { qaState.verdicts[value] = null; });
}

function updateQaUI() {
  if (qaRealityMeta) qaRealityMeta.textContent = metaLabel(sourceMeta.reality);
  if (qaRedBlackMeta) qaRedBlackMeta.textContent = metaLabel(sourceMeta.redblack);

  const pair = masterPairCheck();
  if (qaPairMeta) {
    qaPairMeta.textContent = pair.ready
      ? pair.pass
        ? `PASS · ${sourceMeta.reality.width}×${sourceMeta.reality.height}`
        : pair.text
      : 'Waiting';
  }

  const bothLoaded = customReady.reality && customReady.redblack;
  const passCount = QA_ANGLES.filter(value => qaState.verdicts[value] === 'pass').length;
  const failCount = QA_ANGLES.filter(value => qaState.verdicts[value] === 'fail').length;

  qaRows.forEach(row => {
    const value = Number(row.dataset.qaRow);
    const verdict = qaState.verdicts[value];
    row.classList.toggle('is-current', Math.abs(qaState.currentAngle - value) < 0.1);
    row.classList.toggle('is-pass', verdict === 'pass');
    row.classList.toggle('is-fail', verdict === 'fail');
  });

  qaPassButtons.forEach(button => {
    const value = Number(button.dataset.qaPass);
    button.classList.toggle('is-active', qaState.verdicts[value] === 'pass');
    button.disabled = !(ready && bothLoaded);
  });
  qaFailButtons.forEach(button => {
    const value = Number(button.dataset.qaFail);
    button.classList.toggle('is-active', qaState.verdicts[value] === 'fail');
    button.disabled = !(ready && bothLoaded);
  });
  qaAngleButtons.forEach(button => { button.disabled = !(ready && bothLoaded); });

  if (qaLockPairButton) {
    qaLockPairButton.disabled = !(ready && pair.pass) && !qaState.locked;
    qaLockPairButton.textContent = qaState.locked ? 'Unlock Pair' : 'Lock Pair';
  }
  if (qaResetButton) qaResetButton.disabled = !(ready && bothLoaded);

  const sourceLocked = qaState.locked;
  if (customSourceButton) customSourceButton.disabled = !ready || sourceLocked;
  if (redBlackButton) redBlackButton.disabled = !ready || sourceLocked;
  if (realityInput) realityInput.disabled = !ready || sourceLocked;
  if (redBlackInput) redBlackInput.disabled = !ready || sourceLocked;

  qaPanel?.classList.toggle('is-ready', pair.pass && passCount === QA_ANGLES.length && failCount === 0);
  qaPanel?.classList.toggle('is-failed', failCount > 0 || (pair.ready && !pair.pass));
  qaPanel?.classList.toggle('is-locked', qaState.locked);

  if (qaSummary) {
    if (!bothLoaded) qaSummary.textContent = 'Load both masters';
    else if (!pair.pass) qaSummary.textContent = pair.text;
    else if (failCount > 0) qaSummary.textContent = `QA FAIL · ${failCount} angle${failCount === 1 ? '' : 's'}`;
    else if (passCount === QA_ANGLES.length && qaState.locked) qaSummary.textContent = 'QA PASS · pair frozen';
    else if (passCount === QA_ANGLES.length) qaSummary.textContent = '5/5 PASS · lock pair';
    else if (qaState.locked) qaSummary.textContent = `Locked · ${passCount}/5 PASS`;
    else qaSummary.textContent = `${passCount}/5 PASS`;
  }

  updateStageStates();
}

function updateSourceUI() {
  document.querySelectorAll('[data-ui-theme]').forEach(button => button.setAttribute('aria-selected', String(uiTheme === 'custom' && button.dataset.uiTheme === 'custom')));
  redBlackButton.classList.toggle('is-loaded', customReady.redblack);
  redBlackButton.textContent = customReady.redblack ? 'RedBlack ✓' : 'RedBlack';
  updateQaUI();
}

realityInput.addEventListener('change', async () => {
  const file = realityInput.files[0];
  if (!file || qaState.locked) return;
  try {
    const img = await decodeFile(file);
    worldImages.reality = img;
    drawWorld(img, worldCanvases.reality, worldTextures.reality);
    sourceMeta.reality = {
      name: file.name,
      width: img.naturalWidth || img.width,
      height: img.naturalHeight || img.height,
      ratio: (img.naturalWidth || img.width) / Math.max(img.naturalHeight || img.height, 1),
    };
    customReady.reality = true;
    qaState.locked = false;
    resetQaVerdicts();
    resetExportAcceptanceAll({ clearFiles: true });
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
  if (!file || qaState.locked) return;
  if (!customReady.reality) {
    alert('Upload the Reality image first.');
    redBlackInput.value = '';
    return;
  }
  try {
    const img = await decodeFile(file);
    worldImages.redblack = img;
    drawWorld(img, worldCanvases.redblack, worldTextures.redblack, screenChrome);
    sourceMeta.redblack = {
      name: file.name,
      width: img.naturalWidth || img.width,
      height: img.naturalHeight || img.height,
      ratio: (img.naturalWidth || img.width) / Math.max(img.naturalHeight || img.height, 1),
    };
    customReady.redblack = true;
    qaState.locked = false;
    resetQaVerdicts();
    resetExportAcceptanceAll({ clearFiles: true });
    uiTheme = 'custom';
    applyCustomWorld();
    setPlaying(false); setAngle(0); updateSourceUI();
  } catch (error) {
    console.error(error);
    alert('Unable to read the RedBlack image. Choose a PNG, JPG, or WebP file.');
  } finally { redBlackInput.value = ''; }
});

redBlackButton?.addEventListener('click', () => {
  if (qaState.locked) return;
  if (!customReady.reality) { alert('Upload the Reality image first.'); return; }
  redBlackInput.click();
});

qaAngleButtons.forEach(button => button.addEventListener('click', () => {
  const value = Number(button.dataset.qaAngle);
  setPlaying(false);
  playbackTime = 0;
  qaState.currentAngle = value;
  setAngle(value);
  updateQaUI();
}));

qaPassButtons.forEach(button => button.addEventListener('click', () => {
  const value = Number(button.dataset.qaPass);
  qaState.verdicts[value] = qaState.verdicts[value] === 'pass' ? null : 'pass';
  updateQaUI();
}));

qaFailButtons.forEach(button => button.addEventListener('click', () => {
  const value = Number(button.dataset.qaFail);
  qaState.verdicts[value] = qaState.verdicts[value] === 'fail' ? null : 'fail';
  updateQaUI();
}));

qaLockPairButton?.addEventListener('click', () => {
  const pair = masterPairCheck();
  if (!qaState.locked && !pair.pass) {
    alert('Master Pair QA cannot lock this pair until both masters use identical dimensions and compatible panorama aspect ratio.');
    return;
  }
  qaState.locked = !qaState.locked;
  updateQaUI();
});

qaResetButton?.addEventListener('click', () => {
  resetQaVerdicts();
  qaState.currentAngle = angle;
  updateQaUI();
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
  if (angleBubble) {
    angleBubble.textContent = `${Math.round(angle)}\u00b0`;
    angleBubble.style.left = `${THREE.MathUtils.clamp(progress, 0, 1) * 100}%`;
  }
  snapButtons.forEach(button => button.classList.toggle('is-current', Math.abs(angle - Number(button.dataset.snap)) < .6));
}

function updateFraming() {
  // Geometry lock: the fixed/right panel never recenters or rescales.
  // Only the physical left panel moves around the hinge.
  phone.position.x = FIXED_PANEL_ANCHOR_X;
  phone.scale.setScalar(1);
}

function foldEase(progress) {
  const p = THREE.MathUtils.clamp(progress, 0, 1);
  if (foldMotion.easing === 'linear') return p;
  if (foldMotion.easing === 'cinematic') {
    // Smootherstep: slower settle at both ends, useful for editorial cuts.
    return p * p * p * (p * (p * 6 - 15) + 10);
  }
  return p * p * (3 - 2 * p);
}

function foldSequenceDuration() {
  return foldMotion.closedHold + foldMotion.unfoldDuration + foldMotion.openHold;
}

function updateSequenceScale() {
  if (!sequenceStrip) return;
  const total = Math.max(foldSequenceDuration(), 1e-6);
  sequenceStrip.style.setProperty('--seq-a', `${(foldMotion.closedHold / total) * 100}%`);
  sequenceStrip.style.setProperty('--seq-b', `${(foldMotion.unfoldDuration / total) * 100}%`);
}

function sequenceTimeFromAngle(angleDeg) {
  if (angleDeg <= 0) return 0;
  const foldStart = foldMotion.closedHold;
  const foldEnd = foldStart + foldMotion.unfoldDuration;
  if (angleDeg >= 180) return foldEnd;
  const target = angleDeg / 180;
  let best = 0;
  let bestDiff = Infinity;
  for (let i = 0; i <= 64; i += 1) {
    const p = i / 64;
    const diff = Math.abs(foldEase(p) - target);
    if (diff < bestDiff) { bestDiff = diff; best = p; }
  }
  return foldStart + best * foldMotion.unfoldDuration;
}

function updateSequencePlayhead() {
  if (!sequencePlayhead) return;
  const total = Math.max(foldSequenceDuration(), 1e-6);
  const t = recording
    ? Number(document.documentElement.dataset.recordT || 0)
    : playing
      ? playbackTime
      : sequenceTimeFromAngle(angle);
  const pct = `${(THREE.MathUtils.clamp(t / total, 0, 1) * 100).toFixed(2)}%`;
  if (pct !== updateSequencePlayhead.last) {
    updateSequencePlayhead.last = pct;
    sequencePlayhead.style.left = pct;
  }
}

function updateStageStates() {
  if (!stagePanels.setup) return;
  const mastersReady = customReady.reality && customReady.redblack;
  stagePanels.setup.classList.toggle('is-done', mastersReady);
  stagePanels.setup.classList.toggle('is-active', !mastersReady);
  const qaPass = document.querySelectorAll('.qa-angle-row.is-pass').length;
  stagePanels.quality.classList.toggle('is-done', qaPass >= QA_ANGLES.length);
  stagePanels.quality.classList.toggle('is-active', mastersReady && qaPass > 0 && qaPass < QA_ANGLES.length);
  stagePanels.capture.classList.toggle('is-done', recordHasRun);
  stagePanels.capture.classList.toggle('is-active', recording || recordingMode);
  const exportPass = document.querySelectorAll('.export-check-row.is-pass').length;
  stagePanels.accept.classList.toggle('is-done', exportPass >= 5);
  stagePanels.accept.classList.toggle('is-active', exportPass > 0 && exportPass < 5);
}

function refreshFoldMotionUI() {
  if (closedHoldValue) closedHoldValue.textContent = `${foldMotion.closedHold.toFixed(2)}s`;
  if (unfoldDurationValue) unfoldDurationValue.textContent = `${foldMotion.unfoldDuration.toFixed(2)}s`;
  if (openHoldValue) openHoldValue.textContent = `${foldMotion.openHold.toFixed(2)}s`;
  const total = foldSequenceDuration();
  if (foldTotalReadout) {
    const label = activeFoldPreset ? FOLD_PRESETS[activeFoldPreset].label : 'Custom';
    foldTotalReadout.textContent = `${label} · ${total.toFixed(2)}s`;
  }
  foldPresetButtons.forEach(button => {
    button.setAttribute('aria-pressed', String(button.dataset.foldPreset === activeFoldPreset));
  });
  updateSequenceScale();
  updateRecordingUI();
}

function setFoldMotion(partial = {}, source = 'manual') {
  if (source === 'manual') activeFoldPreset = null;
  if (Number.isFinite(partial.closedHold)) {
    foldMotion.closedHold = THREE.MathUtils.clamp(Number(partial.closedHold), 0, 1.5);
    if (closedHoldInput) closedHoldInput.value = String(foldMotion.closedHold);
  }
  if (Number.isFinite(partial.unfoldDuration)) {
    foldMotion.unfoldDuration = THREE.MathUtils.clamp(Number(partial.unfoldDuration), 0.8, 4);
    if (unfoldDurationInput) unfoldDurationInput.value = String(foldMotion.unfoldDuration);
  }
  if (Number.isFinite(partial.openHold)) {
    foldMotion.openHold = THREE.MathUtils.clamp(Number(partial.openHold), 0, 2.5);
    if (openHoldInput) openHoldInput.value = String(foldMotion.openHold);
  }
  if (['smooth', 'cinematic', 'linear'].includes(partial.easing)) {
    foldMotion.easing = partial.easing;
    if (foldEasingSelect) foldEasingSelect.value = foldMotion.easing;
  }
  refreshFoldMotionUI();
}

function applyFoldPreset(name, { resetView = true } = {}) {
  const preset = FOLD_PRESETS[name];
  if (!preset) return;
  activeFoldPreset = name;
  setFoldMotion(preset, 'preset');

  applyingFoldPreset = true;
  document.querySelector(`[data-motion-blur="${preset.motionBlur}"]`)?.click();
  applyingFoldPreset = false;

  if (resetView) {
    setPlaying(false);
    playbackTime = 0;
    setAngle(0);
  }
  refreshFoldMotionUI();
}

closedHoldInput?.addEventListener('input', () => setFoldMotion({ closedHold: Number(closedHoldInput.value) }));
unfoldDurationInput?.addEventListener('input', () => setFoldMotion({ unfoldDuration: Number(unfoldDurationInput.value) }));
openHoldInput?.addEventListener('input', () => setFoldMotion({ openHold: Number(openHoldInput.value) }));
foldEasingSelect?.addEventListener('change', () => setFoldMotion({ easing: foldEasingSelect.value }));
foldPresetButtons.forEach(button => button.addEventListener('click', () => {
  applyFoldPreset(button.dataset.foldPreset);
}));
document.querySelectorAll('[data-motion-blur]').forEach(button => {
  button.addEventListener('click', () => {
    if (applyingFoldPreset) return;
    activeFoldPreset = null;
    refreshFoldMotionUI();
  });
});
foldMotionReset?.addEventListener('click', () => applyFoldPreset(DEFAULT_FOLD_PRESET));
applyFoldPreset(DEFAULT_FOLD_PRESET, { resetView: false });

function updateRecordingTime(current = 0, total = foldSequenceDuration()) {
  if (recordModeTime) recordModeTime.textContent = `${current.toFixed(2)} / ${total.toFixed(2)}s`;
}

function recordingPrerequisitesReady() {
  return ready
    && customReady.reality
    && customReady.redblack
    && masterPairCheck().pass;
}

function updateRecordingUI() {
  document.documentElement.dataset.recordFormat = recordFormat;
  document.documentElement.dataset.recordingGuide = recordGuide ? 'on' : 'off';

  recordFormatButtons.forEach(button => {
    button.setAttribute('aria-pressed', String(button.dataset.recordFormat === recordFormat));
  });
  recordFpsButtons.forEach(button => {
    button.setAttribute('aria-pressed', String(Number(button.dataset.recordFps) === recordFps));
  });
  recordGuideButtons.forEach(button => {
    button.setAttribute('aria-pressed', String((button.dataset.recordGuide === 'on') === recordGuide));
  });
  recordGuideToggle?.setAttribute('aria-checked', String(recordGuide));
  if (recordGuideToggle) recordGuideToggle.disabled = !ready || recording;

  const presetLabel = activeFoldPreset ? FOLD_PRESETS[activeFoldPreset].label : 'Custom';
  if (recordingSummary) recordingSummary.textContent = `${RECORD_FORMATS[recordFormat]} · ${recordFps} fps`;
  if (recordSafeFrameLabel) recordSafeFrameLabel.textContent = `${RECORD_FORMATS[recordFormat]} SAFE FRAME`;
  if (recordModeMeta) recordModeMeta.textContent = `${RECORD_FORMATS[recordFormat]} · ${recordFps} fps · ${presetLabel}`;

  if (recordModeStatus) {
    recordModeStatus.textContent = recording
      ? 'Recording'
      : recordHasRun
        ? 'Complete'
        : 'Ready';
  }

  if (enterRecordingModeButton) {
    enterRecordingModeButton.disabled = !recordingPrerequisitesReady();
  }
  if (recordStartButton) recordStartButton.disabled = !ready || recording;
  if (recordReplayButton) recordReplayButton.disabled = !ready || recording || !recordHasRun;
  if (recordResetButton) recordResetButton.disabled = !ready;
  if (recordExitButton) recordExitButton.disabled = !ready;

  if (recordSafeFrame) recordSafeFrame.hidden = !recordingMode;
  if (recordHud) recordHud.hidden = !recordingMode;

  updateRecordingTime(
    Number(document.documentElement.dataset.recordT || 0),
    foldSequenceDuration(),
  );
  updateExportAcceptanceUI();
  updateStageStates();
}

function setRecordFormat(value) {
  if (!Object.hasOwn(RECORD_FORMATS, value) || recording) return;
  recordFormat = value;
  updateRecordingUI();
}

function setRecordFps(value) {
  const next = Number(value);
  if (![30, 60].includes(next) || recording) return;
  recordFps = next;
  updateRecordingUI();
}

function setRecordGuide(value) {
  if (recording) return;
  recordGuide = Boolean(value);
  updateRecordingUI();
}

function setRecordingMode(value) {
  recordingMode = Boolean(value);
  if (recordingMode) {
    document.documentElement.dataset.recordingMode = '1';
    setPlaying(false);
    recording = false;
    recordHasRun = false;
    playbackTime = 0;
    setAngle(0);
    delete document.documentElement.dataset.recordDone;
    delete document.documentElement.dataset.recordT;
    delete document.documentElement.dataset.recordFrame;
    delete document.documentElement.dataset.recordingActive;
  } else {
    recording = false;
    document.documentElement.removeAttribute('data-recording-mode');
    document.documentElement.removeAttribute('data-recording-active');
    delete document.documentElement.dataset.recordT;
    delete document.documentElement.dataset.recordFrame;
    delete document.documentElement.dataset.recordDone;
    setPlaying(false);
    playbackTime = 0;
    setAngle(0);
    resetRecordFraming();
  }
  updateRecordingUI();
}

function resetRecordingSession() {
  recording = false;
  recordHasRun = false;
  recordFrameIndex = 0;
  resetRecordFraming();
  document.documentElement.removeAttribute('data-recording-active');
  delete document.documentElement.dataset.recordT;
  delete document.documentElement.dataset.recordFrame;
  delete document.documentElement.dataset.recordDone;
  delete document.documentElement.dataset.recordDuration;
  setPlaying(false);
  playbackTime = 0;
  setAngle(0);
  updateRecordingUI();
}

function currentExportState() {
  return exportAcceptance[recordFormat];
}

function exportTargetRatio(format = recordFormat) {
  if (format === '1x1') return 1;
  if (format === '9x16') return 9 / 16;
  return 16 / 9;
}

function exportAutoCheck(format = recordFormat) {
  const state = exportAcceptance[format];
  const capture = captureHistory[format];
  const video = state.videoMeta;
  const targetRatio = exportTargetRatio(format);

  const capturePass = Boolean(
    capture?.done
    && capture.masterPairPass
    && capture.endpointAngle === 180
    && capture.clockPass
  );

  const aspectDelta = video
    ? Math.abs((video.width / Math.max(video.height, 1)) - targetRatio) / targetRatio
    : null;
  const aspectPass = video ? aspectDelta <= 0.015 : false;

  const expectedDuration = capture?.duration ?? null;
  const durationDelta = video && expectedDuration !== null
    ? Math.abs(video.duration - expectedDuration)
    : null;
  const durationTolerance = capture
    ? Math.max(0.35, 4 / Math.max(capture.fps, 1))
    : 0.35;
  const durationPass = durationDelta !== null
    ? durationDelta <= durationTolerance
    : false;

  const resolutionGood = video
    ? Math.min(video.width, video.height) >= 720
    : false;

  const pass = capturePass && aspectPass && durationPass;
  let text = 'Waiting for capture + export';
  if (!capture?.done) text = 'Capture required';
  else if (!video) text = 'Load exported video';
  else if (!capturePass) text = 'Capture clock / endpoint fail';
  else if (!aspectPass) text = 'Aspect ratio mismatch';
  else if (!durationPass) text = `Duration mismatch · Δ${durationDelta.toFixed(2)}s`;
  else if (!resolutionGood) text = 'PASS · resolution warning';
  else text = `PASS · Δ${durationDelta.toFixed(2)}s`;

  return {
    pass,
    capturePass,
    aspectPass,
    durationPass,
    resolutionGood,
    aspectDelta,
    durationDelta,
    durationTolerance,
    capture,
    video,
    text,
  };
}

function exportVerdictCounts(format = recordFormat) {
  const verdicts = exportAcceptance[format].verdicts;
  const pass = EXPORT_CRITERIA.filter(key => verdicts[key] === 'pass').length;
  const fail = EXPORT_CRITERIA.filter(key => verdicts[key] === 'fail').length;
  return { pass, fail };
}

function updateExportReviewSource() {
  if (!exportReviewVideo || !exportReviewWrap) return;
  const state = currentExportState();
  const url = state.objectUrl;

  if (url && exportReviewVideo.dataset.objectUrl !== url) {
    exportReviewVideo.src = url;
    exportReviewVideo.dataset.objectUrl = url;
    exportReviewVideo.load();
  } else if (!url && exportReviewVideo.dataset.objectUrl) {
    exportReviewVideo.removeAttribute('src');
    delete exportReviewVideo.dataset.objectUrl;
    exportReviewVideo.load();
  }
  exportReviewWrap.hidden = !url;
}

function updateExportAcceptanceUI() {
  const state = currentExportState();
  const auto = exportAutoCheck();
  const counts = exportVerdictCounts();

  exportFormatButtons.forEach(button => {
    button.setAttribute('aria-pressed', String(button.dataset.exportFormat === recordFormat));
    button.disabled = !ready || recording;
  });

  exportRows.forEach(row => {
    const key = row.dataset.exportRow;
    const verdict = state.verdicts[key];
    row.classList.toggle('is-pass', verdict === 'pass');
    row.classList.toggle('is-fail', verdict === 'fail');
  });
  exportPassButtons.forEach(button => {
    const key = button.dataset.exportPass;
    button.classList.toggle('is-active', state.verdicts[key] === 'pass');
    button.disabled = !state.videoMeta || recording;
  });
  exportFailButtons.forEach(button => {
    const key = button.dataset.exportFail;
    button.classList.toggle('is-active', state.verdicts[key] === 'fail');
    button.disabled = !state.videoMeta || recording;
  });

  if (exportLoadButton) exportLoadButton.disabled = !ready || recording;
  if (exportReviewInput) exportReviewInput.disabled = !ready || recording;
  if (exportResetButton) exportResetButton.disabled = !ready || recording;
  if (exportReviewHingeButton) exportReviewHingeButton.disabled = !state.videoMeta || recording;
  if (exportReviewEndButton) exportReviewEndButton.disabled = !state.videoMeta || recording;

  if (exportFileMeta) {
    exportFileMeta.textContent = state.file
      ? `${state.file.name} · ${(state.file.size / 1024 / 1024).toFixed(1)} MB`
      : 'Not loaded';
  }

  if (exportResolutionMeta) {
    exportResolutionMeta.textContent = state.videoMeta
      ? `${state.videoMeta.width}×${state.videoMeta.height} · ${state.videoMeta.duration.toFixed(2)}s`
      : 'Waiting';
  }

  if (exportAutoMeta) exportAutoMeta.textContent = auto.text;

  const autoCard = exportAutoMeta?.closest('.export-auto-card');
  autoCard?.classList.toggle('is-pass', auto.pass && auto.resolutionGood);
  autoCard?.classList.toggle('is-warn', auto.pass && !auto.resolutionGood);
  autoCard?.classList.toggle('is-fail', Boolean(auto.video && auto.capture && !auto.pass));

  const finalPass = auto.pass && counts.pass === EXPORT_CRITERIA.length && counts.fail === 0;
  const finalFail = counts.fail > 0 || (Boolean(auto.video && auto.capture) && !auto.pass);

  exportPanel?.classList.toggle('is-pass', finalPass);
  exportPanel?.classList.toggle('is-fail', finalFail);

  if (exportSummary) {
    if (finalPass) exportSummary.textContent = `${RECORD_FORMATS[recordFormat]} · EXPORT PASS`;
    else if (finalFail) exportSummary.textContent = `${RECORD_FORMATS[recordFormat]} · FAIL`;
    else if (!auto.capture?.done) exportSummary.textContent = `${RECORD_FORMATS[recordFormat]} · capture first`;
    else if (!auto.video) exportSummary.textContent = `${RECORD_FORMATS[recordFormat]} · load export`;
    else exportSummary.textContent = `${RECORD_FORMATS[recordFormat]} · ${counts.pass}/5 manual`;
  }

  document.documentElement.dataset.exportFormat = recordFormat;
  document.documentElement.dataset.exportAcceptance = finalPass
    ? 'pass'
    : finalFail
      ? 'fail'
      : 'pending';

  updateExportReviewSource();
  updateStageStates();
}

function resetExportVerdicts(format = recordFormat) {
  EXPORT_CRITERIA.forEach(key => { exportAcceptance[format].verdicts[key] = null; });
}

function clearExportFile(format = recordFormat) {
  const state = exportAcceptance[format];
  if (state.objectUrl) URL.revokeObjectURL(state.objectUrl);
  state.file = null;
  state.objectUrl = null;
  state.videoMeta = null;
}

function resetExportAcceptanceAll({ clearFiles = false } = {}) {
  Object.keys(exportAcceptance).forEach(format => {
    resetExportVerdicts(format);
    captureHistory[format] = null;
    if (clearFiles) clearExportFile(format);
  });
  updateExportAcceptanceUI();
}

function seekExportReview(kind) {
  const state = currentExportState();
  if (!exportReviewVideo || !state.videoMeta) return;

  const expected = state.videoMeta.duration;
  const capture = captureHistory[recordFormat];
  const sourceDuration = capture?.duration || foldSequenceDuration();
  const scale = expected / Math.max(sourceDuration, 1e-6);

  exportReviewVideo.pause();
  if (kind === 'hinge') {
    const hingeT = foldMotion.closedHold + foldMotion.unfoldDuration * 0.5;
    exportReviewVideo.currentTime = THREE.MathUtils.clamp(hingeT * scale, 0, Math.max(0, expected - 0.01));
  } else {
    exportReviewVideo.currentTime = Math.max(0, expected - Math.min(0.12, expected * 0.04));
  }
}

exportFormatButtons.forEach(button => button.addEventListener('click', () => {
  setRecordFormat(button.dataset.exportFormat);
}));
exportLoadButton?.addEventListener('click', () => exportReviewInput?.click());
exportResetButton?.addEventListener('click', () => {
  resetExportVerdicts();
  updateExportAcceptanceUI();
});
exportPassButtons.forEach(button => button.addEventListener('click', () => {
  const key = button.dataset.exportPass;
  const state = currentExportState();
  state.verdicts[key] = state.verdicts[key] === 'pass' ? null : 'pass';
  updateExportAcceptanceUI();
}));
exportFailButtons.forEach(button => button.addEventListener('click', () => {
  const key = button.dataset.exportFail;
  const state = currentExportState();
  state.verdicts[key] = state.verdicts[key] === 'fail' ? null : 'fail';
  updateExportAcceptanceUI();
}));
exportReviewHingeButton?.addEventListener('click', () => seekExportReview('hinge'));
exportReviewEndButton?.addEventListener('click', () => seekExportReview('end'));
exportReviewInput?.addEventListener('change', () => {
  const file = exportReviewInput.files?.[0];
  exportReviewInput.value = '';
  if (!file) return;

  const state = currentExportState();
  clearExportFile(recordFormat);
  state.file = { name: file.name, size: file.size, type: file.type };
  state.objectUrl = URL.createObjectURL(file);
  resetExportVerdicts(recordFormat);
  updateExportReviewSource();

  const handleMetadata = () => {
    state.videoMeta = {
      width: exportReviewVideo.videoWidth,
      height: exportReviewVideo.videoHeight,
      duration: Number.isFinite(exportReviewVideo.duration) ? exportReviewVideo.duration : 0,
    };
    updateExportAcceptanceUI();
  };

  if (exportReviewVideo.readyState >= 1) handleMetadata();
  else exportReviewVideo.addEventListener('loadedmetadata', handleMetadata, { once: true });
  updateExportAcceptanceUI();
});

recordFormatButtons.forEach(button => button.addEventListener('click', () => setRecordFormat(button.dataset.recordFormat)));
recordFpsButtons.forEach(button => button.addEventListener('click', () => setRecordFps(button.dataset.recordFps)));
recordGuideButtons.forEach(button => button.addEventListener('click', () => setRecordGuide(button.dataset.recordGuide === 'on')));
recordGuideToggle?.addEventListener('click', () => setRecordGuide(!recordGuide));
enterRecordingModeButton?.addEventListener('click', () => setRecordingMode(true));
recordStartButton?.addEventListener('click', () => startRecord());
recordReplayButton?.addEventListener('click', () => startRecord());
recordResetButton?.addEventListener('click', resetRecordingSession);
recordExitButton?.addEventListener('click', () => setRecordingMode(false));
updateRecordingUI();
updateSequenceScale();
updateStageStates();
updateSequencePlayhead();

function setPlaying(value) {
  playing = value;
  document.querySelector('#pause-icon')?.toggleAttribute('hidden', !value);
  document.querySelector('#play-icon')?.toggleAttribute('hidden', value);
  playLabel.textContent = value ? 'Pause' : 'Unfold';
  play.setAttribute('aria-label', value ? 'Pause unfold animation' : 'Play unfold animation');
}

function setAngle(value) {
  let nextAngle = THREE.MathUtils.clamp(value, 0, 180);
  // Endpoint stability: prevent tiny floating-point states from leaving the
  // screen in a visually half-open / half-closed sampling state.
  if (nextAngle < 0.1) nextAngle = 0;
  if (nextAngle > 179.9) nextAngle = 180;
  angle = nextAngle;
  slider.value = angle;
  bend.value = (180 - angle) / 180 * Math.PI;
  const progress = angle / 180;
  const bezelPrev = uBezel.value;
  uBezel.value = progress;
  if (!REDUCED_MOTION && angle >= 179.9 && bezelPrev * 180 < 179.9) { uBezelPopHold = false; uBezelPop.value = 1; }
  const active = uiTheme === 'custom' && customReady.reality && customReady.redblack;
  const mix = worldMixOverride ?? (active ? worldMixFromGeometry(geometrySignal(angle)) : 0);
  worldMix.value = mix;
  uTowerMix.value = mix;
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
  const qaAngle = QA_ANGLES.find(value => Math.abs(value - angle) < 0.1);
  if (qaAngle !== undefined && qaState.currentAngle !== qaAngle) {
    qaState.currentAngle = qaAngle;
    updateQaUI();
  }
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

// Dock density: only one stage panel open at a time; outside click / Esc closes it.
const workflowRow = document.querySelector('.workflow-row');
const stageDetails = workflowRow ? [...workflowRow.querySelectorAll('details.stage-panel')] : [];
stageDetails.forEach(panel => panel.addEventListener('toggle', () => {
  if (panel.open) stageDetails.forEach(other => { if (other !== panel) other.open = false; });
}));
document.addEventListener('click', event => {
  const openPanel = stageDetails.find(panel => panel.open);
  if (!openPanel || openPanel.contains(event.target)) return;
  openPanel.open = false;
});
document.addEventListener('keydown', event => {
  if (event.key === 'Escape') stageDetails.forEach(panel => { panel.open = false; });
});

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
uniform float uTowerMix;
uniform float uFoldBlurScale;
uniform float uTowerBoost;
uniform float uRevealFront;
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

// V5.9 two-beat reveal (clean-crossfade mode only): the tower's lit lattice
// holds on Reality until uTowerMix catches up; sky through the lattice belongs
// to the background phase. Identity when uTowerMix == worldMix (preview).
float finalReveal(vec2 uv, vec3 bCol) {
  float r = activeReveal(uv, bCol);
  if (uUseStagedReveal < 0.5) {
    // V6.2: spatial reveal — the world transforms left->right following the
    // opening panel, replacing the global crossfade on the record path.
    if (uRevealFront >= 0.0) {
      // V6.3: per-panel sequential reveal — the left panel transforms as it
      // opens, the right panel follows left->right; full coverage by fold end.
      float seqL = clamp(uRevealFront / 0.55, 0.0, 1.0);
      float seqR = clamp((uRevealFront - 0.45) / 0.55, 0.0, 1.0);
      float panel = uv.x < 0.5 ? seqL : seqR;
      float lu = uv.x < 0.5 ? uv.x * 2.0 : (uv.x - 0.5) * 2.0;
      r = 1.0 - smoothstep(panel * 1.25 - 0.25, panel * 1.25, lu);
    }
    r = mix(r, uTowerMix, towerContentMask(uv, bCol));  // V6.5: lattice-only hold — no cold ellipse halo
  }
  return r;
}

vec3 screenColor() {
  // Intersect the fixed front-view ray with the unfolded inner-screen plane.
  float depth = (0.24948 - uiReferenceEye.z) / (vUIPosition.z - uiReferenceEye.z);
  vec2 projected = uiReferenceEye.xy + (vUIPosition.xy - uiReferenceEye.xy) * depth;
  vec2 sourceUV = (projected - uiFrame.xy) / uiFrame.zw;
  #ifdef INNER_UI
    // V5.0.5 Hinge / Endpoint Stability:
    // 1) Keep a very narrow band around the physical hinge tied to authored
    //    panorama X so the two sides cannot visually shear apart.
    // 2) Ease into authored UV over the final ~1.2° instead of waiting until
    //    the last sub-degree, avoiding a visible last-frame correction.
    float hingeLock = 1.0 - smoothstep(0.006, 0.020, abs(vMapUv.x - 0.5));
    sourceUV.x = mix(sourceUV.x, vMapUv.x, hingeLock);
    float endpointLock = 1.0 - smoothstep(0.0, 0.020943951, abs(foldAngle));
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
  radius *= uFoldBlurScale; // V5.9: record path trims smear for rigid panels
  vec2 aa = max(fwidth(sourceUV), uiPixel * 0.5);
  vec2 dx = dFdx(sourceUV) / uiPixel;
  vec2 dy = dFdy(sourceUV) / uiPixel;
  float baseLod = log2(max(1.0, max(length(dx), length(dy))));
  vec2 coverage = smoothstep(-aa, aa, sourceUV)
    * (1.0 - smoothstep(vec2(1.0) - aa, vec2(1.0) + aa, sourceUV));
  // Invalid panorama coordinates are never allowed to copy a clamped edge
  // texel back onto the physical display.
  float sourceValid = step(0.0, sourceUV.x) * step(sourceUV.x, 1.0)
    * step(0.0, sourceUV.y) * step(sourceUV.y, 1.0);
  coverage *= sourceValid;
  #ifdef INNER_UI
    // At the exact Open endpoint the rounded physical mesh is already the
    // clipping boundary, so do not fade valid edge texels a second time.
    coverage = mix(coverage, vec2(1.0), endpointLock);
  #endif
  vec2 uvC = clamp(sourceUV, vec2(0.0), vec2(1.0));
  vec3 colA = textureLod(map, uvC, baseLod).rgb;
  vec3 colB = textureLod(transitionTarget, uvC, baseLod).rgb;
  float revealAmount = finalReveal(sourceUV, colB);
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
        float tapReveal = finalReveal(sampleUV, tapB);
        color += mix(tapA, tapB, tapReveal) * tapCoverage.x * tapCoverage.y * wx * wy / 256.0;
      }
    }
  }
  color *= 1.0 - min(1.0, effect * 2.0);
  // V5.9 tower activation: warm hero glow on the tower's lit lattice, ramped by
  // uTowerBoost at open-complete (record path only; preview stays 0).
  if (uNoFx < 0.5 && uTowerBoost > 0.001) {
    color += vec3(1.0, 0.62, 0.25) * uTowerBoost * towerContentMask(sourceUV, colB) * 0.35;
  }

  // Impact @2.15s: one-frame white-red flash + visible RGB split (screen-space
  // only, geometry untouched).
  if (uNoFx < 0.5 && uImpact > 0.001) {
    float split = uImpact * 7.0 * uiPixel.x;
    vec2 uvR = clamp(sourceUV + vec2(split, 0.0), vec2(0.0), vec2(1.0));
    vec2 uvB = clamp(sourceUV - vec2(split, 0.0), vec2(0.0), vec2(1.0));
    vec3 rB2 = textureLod(transitionTarget, uvR, baseLod).rgb;
    vec3 bB2 = textureLod(transitionTarget, uvB, baseLod).rgb;
    float rr = mix(textureLod(map, uvR, baseLod).rgb.r, rB2.r, finalReveal(uvR, rB2));
    float bb = mix(textureLod(map, uvB, baseLod).rgb.b, bB2.b, finalReveal(uvB, bB2));
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
          shader.uniforms.uTowerMix = uTowerMix;
          shader.uniforms.uFoldBlurScale = uFoldBlurScale;
          shader.uniforms.uTowerBoost = uTowerBoost;
    shader.uniforms.uRevealFront = uRevealFront;

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

    if (!kind) {
      // V5.6 bezel light: patched onto every body/hinge/shell material.
      const prevCompile = material.onBeforeCompile;
      material.onBeforeCompile = shader => {
        prevCompile?.(shader);
        if (BEZEL_DEBUG) (shader.defines = shader.defines || {}).BEZEL_DEBUG = 1;
        shader.uniforms.uBezel = uBezel;
        shader.uniforms.uBezelPop = uBezelPop;
        shader.vertexShader = `varying float vBezelX;\n${shader.vertexShader}`
          .replace('#include <project_vertex>', `vBezelX = position.x;\n#include <project_vertex>`);
        shader.fragmentShader = `varying float vBezelX;\nuniform float uBezel;\nuniform float uBezelPop;\n${shader.fragmentShader}`
          .replace('#include <opaque_fragment>', `#include <opaque_fragment>
{
  float bd = clamp(abs(vBezelX) / 7.89935, 0.0, 1.0);
  // Titanium sweep travels hinge -> outer edge across the middle of the fold.
  // (Red leak lives in the screen shader's uLeak stage; the physical bezel
  // stays a pure titanium story.)
  float sp = clamp((uBezel - 0.35) / 0.6, 0.0, 1.0);
  float band = exp(-pow((bd - sp) * 4.0, 2.0)) * step(0.0005, sp);
  vec3 bezelGlow = vec3(0.92, 0.96, 1.0) * band * 1.6;
  bezelGlow += vec3(0.9, 0.95, 1.0) * uBezelPop * 3.0 * (0.5 + 0.5 * (1.0 - bd));
  #ifdef BEZEL_DEBUG
  gl_FragColor.rgb = vec3(bd, 0.0, 1.0 - bd);
  #else
  gl_FragColor.rgb += bezelGlow;
  #endif
}`);
      };
      material.customProgramCacheKey = () => `v56e-bezel-${moving ? 'mov' : flexible ? 'flx' : 'fix'}`;
      material.userData.bezelPatched = true;
    }

    const mesh = new THREE.Mesh(geometry, material);
    mesh.name = object.name;
    mesh.frustumCulled = false;
    phone.add(mesh);
    // V6.5: white bg makes the bezel seam read as a white border; tuck the
    // inner screen slightly under the bezel (record/cap path only).
    if (kind === 'inner' && QUERY.has('cap')) mesh.scale.set(1.012, 1.008, 1);

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
    openEndpointRepair: '1.2deg projected-uv -> authored-uv + endpoint coverage lock',
    hingeContinuity: 'narrow authored-X lock around panorama midpoint',
    endpointAngleSnap: '0/180 exact-state snap',
    productionBaseline: PRODUCTION_BASELINE_ID,
    baselineLocked: PRODUCTION_BASELINE,
    devExperiments: DEV_EXPERIMENTS,
    revealMode: STAGED_REVEAL
      ? 'dev-only experimental staged reveal (?dev=1&reveal=staged)'
      : 'production-clean-crossfade',
    connectionArtifactGuard: 'valid-panorama-only + no blur bleed',
    towerHighlightGuard: 'content-aware tower mask; no broad ellipse glow',
    noFxGeometryTest: '?nofx=1',
    foldMotionControls: 'Fast Viral + Cinematic + Slow Demo presets; manual tuning remains available',
    foldMotionDefault: `${FOLD_PRESETS[DEFAULT_FOLD_PRESET].label} via ?motion=${DEFAULT_FOLD_PRESET}`,
    recordingEditingMode: 'clean UI + 16:9/1:1/9:16 safe frames + 30/60fps deterministic record clock',
    recordingQueries: '?studio=1&format=16x9|1x1|9x16&fps=30|60; ?record=1 auto-starts',
    exportAcceptance: 'load local export -> auto aspect/duration/capture QC -> 5 manual visual checks -> EXPORT PASS',
    masterPairQA: 'source dimension/aspect checks + 0/45/90/135/180 visual verdicts + pair lock',
    towerFxControls: 'removed from production; future work must use a separate R&D branch',
    birdFxControls: 'removed from production; future work must use a separate R&D branch',
    displacement: 'deferred and excluded from V5.1 baseline',
    recordTimeline: 'uses editable Fold Motion timing only',
  });

  updateSourceUI();
  document.querySelectorAll('.control-dock button, .control-dock input, .control-dock select').forEach(element => {
    if (element !== revealSettingsButton && !element.hasAttribute('data-future')) element.disabled = false;
  });
  // V6.4 P1 (record/cap path only): shell fidelity — surface the real side
  // buttons (they exist in the USDZ at x 4.64-4.72 but protrude sub-pixel),
  // warm the titanium frame family, add a warm key light for edge glints.
  if (QUERY.has('cap')) {
    const btnSig = [];
    phone.traverse(o => {
      if (!o.isMesh) return;
      o.geometry.computeBoundingBox();
      const bb = o.geometry.boundingBox.clone().applyMatrix4(o.matrixWorld);
      const sx = bb.max.x - bb.min.x, sy = bb.max.y - bb.min.y;
      const cx = (bb.max.x + bb.min.x) / 2, cy = (bb.max.y + bb.min.y) / 2;
      if (cx > 4.4 && sx < 0.2 && sy > 1.4 && sy < 2.1 && Math.abs(cy) > 1.2 && Math.abs(cy) < 3.2) btnSig.push(o);
      const m = o.material;
      if (m && m.color) {
        const c = m.color;
        if (c.r > 0.75 && c.r >= c.g && c.g >= c.b && (c.r - c.b) < 0.25) {
          c.r *= 0.935; c.g *= 0.895; c.b *= 0.82; // warm titanium, de-blown (deeper)
        }
      }
    });
    btnSig.forEach(o => { o.position.x += 0.12; });
    scene.environmentIntensity = 1.0; // was 1.35 — frame read blown-white on white bg
    key.intensity = 1.7; // was 2.6 — left-edge frame highlight read as a light band (V6.6)
  }
  ready = true;
  setPlaying(false);
  setAngle(0);
  updateQaUI();
  updateRecordingUI();
  updateExportAcceptanceUI();
  if (RECORDING_MODE_AUTO) setRecordingMode(true);
  if (RECORD_AUTO) startRecord();
} catch (error) {
  alert('Unable to load the model. Refresh the page to try again.');
  console.error(error);
}

// Debug hooks for acceptance (window.__duo.setAngle / setWorldMix / setStages / startRecord).
function recordStage(t, a, b) {
  return THREE.MathUtils.clamp((t - a) / (b - a), 0, 1);
}

// ---------------------------------------------------------------------------
// T3 in-page deterministic capture (?cap=1): records the WebGL canvas through
// the deterministic record clock; auto-downloads a webm master at recordDone.
const CAPTURE = QUERY.has('cap');
let capRecorder = null;
let capChunks = [];

function startCapture() {
  if (!CAPTURE || capRecorder || !renderer) return;
  const stream = renderer.domElement.captureStream(recordFps);
  const mime = MediaRecorder.isTypeSupported('video/webm;codecs=vp9')
    ? 'video/webm;codecs=vp9'
    : 'video/webm';
  capRecorder = new MediaRecorder(stream, { mimeType: mime, videoBitsPerSecond: 40_000_000 });
  capChunks = [];
  capRecorder.ondataavailable = e => { if (e.data && e.data.size) capChunks.push(e.data); };
  capRecorder.onstop = finalizeCapture;
  capRecorder.start(500);
  document.documentElement.dataset.capturing = '1';
}

function finalizeCapture() {
  const blob = new Blob(capChunks, { type: 'video/webm' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `duo_v${'5.8'}_${recordFormat}_${recordFps}fps_${activeFoldPreset || 'custom'}.webm`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 30000);
  capRecorder = null;
  capChunks = [];
  delete document.documentElement.dataset.capturing;
  document.documentElement.dataset.captureDone = '1';
}

function stopCapture() {
  if (capRecorder && capRecorder.state !== 'inactive') capRecorder.stop();
}

function startRecord() {
  recordT0 = performance.now();
  recordFrameIndex = 0;
  recordHasRun = false;
  recording = true;
  setPlaying(false);
  setAngle(0);
  startCapture();

  const duration = foldSequenceDuration();
  captureHistory[recordFormat] = {
    done: false,
    format: recordFormat,
    fps: recordFps,
    duration,
    expectedFrames: Math.ceil(duration * recordFps),
    finalFrame: 0,
    clockPass: false,
    endpointAngle: 0,
    masterPairPass: masterPairCheck().pass,
    preset: activeFoldPreset,
    motionBlur: document.documentElement.dataset.motionBlur || 'natural',
  };
  resetExportVerdicts(recordFormat);

  document.documentElement.dataset.recordingActive = '1';
  document.documentElement.dataset.recordFps = String(recordFps);
  document.documentElement.dataset.recordFormat = recordFormat;
  document.documentElement.dataset.recordGuide = recordGuide ? 'on' : 'off';
  delete document.documentElement.dataset.recordDone;
  delete document.documentElement.dataset.recordT;
  delete document.documentElement.dataset.recordFrame;
  document.documentElement.dataset.recordDuration = duration.toFixed(2);
  updateRecordingUI();
}

// Recording-mode cinematic framing (T3): portrait targets cannot contain the
// landscape-opened device at the preview camera, so during record the camera
// dollies out / pans left as the fold progresses. Preview (non-record) is
// never touched.
const RECORD_FRAMING = {
  '16x9': { zoom: 1.25, panX: -167 }, // V6.0: +25% size, panned to horizontal center
  '1x1': { zoom: 1.0, panX: -132 },
  '9x16': { zoom: 0.62, panX: -83 }, // V6.0.1: horizontal centering
};

function applyRecordFraming(easedProgress) {
  const f = RECORD_FRAMING[recordFormat] || RECORD_FRAMING['16x9'];
  const zoom = 1 + (f.zoom - 1) * easedProgress;
  const pan = f.panX * easedProgress;
  camera.zoom = zoom;
  if (Math.abs(pan) > 0.01) {
    camera.setViewOffset(innerWidth, innerHeight, pan, 0, innerWidth, innerHeight);
  } else {
    camera.clearViewOffset();
  }
  camera.updateProjectionMatrix();
}

function resetRecordFraming() {
  camera.zoom = 1;
  camera.clearViewOffset();
  camera.updateProjectionMatrix();
}

// Lv3 record timeline (case-study §6): real fold drives geometry, three stage
// uniforms drive the world hand-off on their own synced schedule.
function driveRecord(nowMs) {
  const rawT = (nowMs - recordT0) / 1000;
  recordFrameIndex = Math.max(0, Math.floor(rawT * recordFps + 1e-6));
  const t = recordFrameIndex / recordFps;
  const foldStart = foldMotion.closedHold;
  const foldEnd = foldStart + foldMotion.unfoldDuration;
  const sequenceEnd = foldEnd + foldMotion.openHold;

  const rawFold = THREE.MathUtils.clamp(
    (t - foldStart) / Math.max(foldMotion.unfoldDuration, 1e-6),
    0,
    1,
  );
  const easedFold = foldEase(rawFold);
  setAngle(easedFold * 180);
  applyRecordFraming(easedFold);
  // V5.9 narrative repair (record path only): the world follows the physical
  // opening (25->150deg) instead of saturating at 67deg, and the tower
  // activates late (110->165deg) as the second beat.
  // V6.0: activation window entirely after open-complete (0.3s snap).
  const recAngle = easedFold * 180;
  const foldActive = rawFold > 0 && rawFold < 1;
  worldMix.value = smoothRange(recAngle, 25, 150);
  uTowerMix.value = smoothRange(t, foldEnd + 0.05, foldEnd + 0.35);
  uTowerBoost.value = 0;              // V6.2: no artificial tower glow
  uRevealFront.value = easedFold; // V6.3: per-panel sequential windows (shader maps 0..1)
  uBezel.value = 0;                   // V6.2: real titanium shell — no sweep light in exports
  if (uBezelPop.value > 0) uBezelPop.value *= 0.5; // lock pop kept subtle
  uFoldBlurScale.value = 0.35;
  if (foldActive) uBezel.value *= 0.35;  // V6.0: soften hinge strip mid-fold (pop untouched)
  // V5.8: micro push-in across the open hold so the static plate stays alive
  // (record path only; preview untouched).
  if (t > foldEnd && foldMotion.openHold > 0) {
    const holdK = THREE.MathUtils.clamp((t - foldEnd) / foldMotion.openHold, 0, 1);
    camera.zoom *= 1 + 0.015 * holdK * holdK * (3 - 2 * holdK);
    camera.updateProjectionMatrix();
  }

  // Experimental staged reveal follows normalized fold progress rather than
  // fixed wall-clock seconds, so motion timing can be edited without desync.
  const leakStart = foldStart + foldMotion.unfoldDuration * 0.55;
  const leakEnd = foldStart + foldMotion.unfoldDuration * 0.72;
  const collapseEnd = foldStart + foldMotion.unfoldDuration * 0.90;
  uLeak.value = STAGED_REVEAL ? recordStage(t, leakStart, leakEnd) : 0;
  uCollapse.value = STAGED_REVEAL ? recordStage(t, leakEnd, collapseEnd) : 0;
  uLock.value = STAGED_REVEAL ? recordStage(t, collapseEnd, foldEnd) : 0;
  uTransActive.value = STAGED_REVEAL
    ? THREE.MathUtils.smoothstep(t, leakStart - 0.08, leakStart)
      * (1 - THREE.MathUtils.smoothstep(t, foldEnd, foldEnd + 0.12))
    : 0;

  // Fold-only production baseline: no Tower FX or Bird FX event.
  uImpact.value = 0;
  uPulse.value = 0;

  const rw = STAGED_REVEAL ? uTransActive.value : 0;
  rim.intensity = 2 + 3.2 * rw;
  rim.color.setRGB(0.91 + 0.09 * rw, 0.93 - 0.62 * rw, 0.96 - 0.68 * rw);
  document.documentElement.dataset.recordT = t.toFixed(3);
  document.documentElement.dataset.recordFrame = String(recordFrameIndex);
  document.documentElement.dataset.recordDuration = sequenceEnd.toFixed(3);
  updateRecordingTime(Math.min(t, sequenceEnd), sequenceEnd);

  if (rawT > sequenceEnd + (1 / recordFps)) {
    recording = false;
    recordHasRun = true;
    uImpact.value = 0;
    uPulse.value = 0;
    uTransActive.value = 0;
    rim.intensity = 2;
    rim.color.setHex(0xe8edf5);
    document.documentElement.dataset.recordDone = '1';
    document.documentElement.removeAttribute('data-recording-active');
    setAngle(180);
    setTimeout(stopCapture, 500); // keep a few static tail frames for editing handles

    const capture = captureHistory[recordFormat];
    if (capture) {
      capture.done = true;
      capture.finalFrame = recordFrameIndex;
      capture.clockPass = Math.abs(recordFrameIndex - capture.expectedFrames) <= 2;
      capture.endpointAngle = angle;
      capture.completedAt = Date.now();
    }

    updateRecordingUI();
  }
}

window.__duo = {
  setAngle: value => { setPlaying(false); playbackTime = 0; recording = false; setAngle(Number(value)); },
  _renderer: renderer,
  _scene: scene,
  _phone: phone,
  // V5.7: toggle iOS-style status-bar chrome on custom worlds (redraws canvases).
  setScreenChrome: flag => {
    screenChrome = !!flag;
    if (worldImages.redblack) drawWorld(worldImages.redblack, worldCanvases.redblack, worldTextures.redblack, screenChrome);
    return screenChrome;
  },
  // V5.6 debug: force bezel sweep/pop for deterministic verification.
  setBezel: (sweep, pop) => { uBezel.value = Number(sweep); uBezelPop.value = Number(pop); uBezelPopHold = Number(pop) > 0; },
  bezelDebug: () => ({
    uniforms: { sweep: uBezel.value, pop: uBezelPop.value },
    meshes: phone.children.map(m => ({
      name: m.name,
      mat: m.material?.type,
      patched: !!m.material?.userData?.bezelPatched,
      hasOBC: Object.prototype.hasOwnProperty.call(m.material ?? {}, 'onBeforeCompile'),
    })),
  }),
  setWorldMix: value => {
    if (!DEV_EXPERIMENTS) return false;
    worldMixOverride = value === null || value === undefined ? null : Number(value);
    setAngle(angle);
    return true;
  },
  setStages: (leak, collapse, lock) => {
    if (!DEV_EXPERIMENTS) return false;
    uLeak.value = Number(leak);
    uCollapse.value = Number(collapse);
    uLock.value = Number(lock);
    return true;
  },
  setFoldMotion,
  setFoldPreset: name => applyFoldPreset(name),
  setRecordingMode,
  setRecordFormat,
  setRecordFps,
  resetRecordingSession,
  resetExportAcceptance: () => {
    resetExportVerdicts();
    updateExportAcceptanceUI();
  },
  play: () => {
    if (angle > .1) setAngle(0);
    playbackTime = 0;
    setPlaying(true);
  },
  startRecord,
  get state() {
    return {
      angle, worldMix: worldMix.value, ready, recording,
      baseline: {
        id: PRODUCTION_BASELINE_ID,
        locked: PRODUCTION_BASELINE,
        devExperiments: DEV_EXPERIMENTS,
        productionReveal: 'clean-crossfade',
        excluded: ['tower-fx', 'bird-fx', 'displacement'],
      },
      stages: { leak: uLeak.value, collapse: uCollapse.value, lock: uLock.value },
      geometryLock: {
        fixedPanelAnchorX: FIXED_PANEL_ANCHOR_X,
        noDynamicScale: true,
        noFx: NO_FX,
        hingeLock: true,
        endpointSnap: true,
      },
      revealMode: STAGED_REVEAL ? 'staged' : 'clean-crossfade',
      foldMotion: {
        ...foldMotion,
        preset: activeFoldPreset,
        motionBlur: document.documentElement.dataset.motionBlur || 'natural',
        total: foldSequenceDuration(),
      },
      recordingMode: {
        active: recordingMode,
        recording,
        hasRun: recordHasRun,
        format: recordFormat,
        fps: recordFps,
        guide: recordGuide,
        frame: recordFrameIndex,
      },
      exportAcceptance: {
        format: recordFormat,
        auto: exportAutoCheck(),
        verdicts: { ...currentExportState().verdicts },
        capture: captureHistory[recordFormat] ? { ...captureHistory[recordFormat] } : null,
        video: currentExportState().videoMeta ? { ...currentExportState().videoMeta } : null,
      },
      masterPairQA: {
        locked: qaState.locked,
        currentAngle: qaState.currentAngle,
        verdicts: { ...qaState.verdicts },
        pair: masterPairCheck(),
        sourceMeta: {
          reality: sourceMeta.reality ? { ...sourceMeta.reality } : null,
          redblack: sourceMeta.redblack ? { ...sourceMeta.redblack } : null,
        },
      },
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
    const foldStart = foldMotion.closedHold;
    const foldEnd = foldStart + foldMotion.unfoldDuration;
    const sequenceEnd = foldEnd + foldMotion.openHold;

    if (playbackTime < foldStart) {
      setAngle(0);
    } else if (playbackTime < foldEnd) {
      const p = (playbackTime - foldStart) / Math.max(foldMotion.unfoldDuration, 1e-6);
      setAngle(THREE.MathUtils.lerp(0, 180, foldEase(p)));
    } else if (playbackTime < sequenceEnd) {
      setAngle(180);
    } else {
      setAngle(180);
      setPlaying(false);
    }
  }

  if (ready && recording) driveRecord(now);

  updateSequencePlayhead();
  if (!uBezelPopHold) uBezelPop.value = uBezelPop.value > 0.002 ? uBezelPop.value * 0.95 : 0;
  renderer.render(scene, camera);
});
