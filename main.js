import * as THREE from 'three';
import { USDLoader } from 'three/addons/loaders/USDLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { loadDefaultUIs } from './ui.js';

const viewport = document.querySelector('#viewport');
const slider = document.querySelector('#angle');
const play = document.querySelector('#play');

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(32, 1, .1, 250);
camera.position.set(0, 0, 40);

const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setClearColor(0xf6f6f3, 0);
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

// Lv3 baseline: keep the camera completely fixed so any apparent movement comes
// only from the physical fold geometry, never from orbit/zoom drift while recording.
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

const bend = { value: Math.PI };
let angle = 0;
let playing = false;
let playbackTime = 0;
let ready = false;
const screens = {};

const defaultUIs = await loadDefaultUIs();
let uiTheme = 'wallpaper';

// Custom artwork is prepared once in a single fixed panorama coordinate system.
// The inner display receives the whole panorama. The outer display receives the
// fixed right-hand half. Neither texture is reprojected or recropped while folding.
const innerCustomCanvas = document.createElement('canvas');
innerCustomCanvas.width = 1600;
innerCustomCanvas.height = 1125;
const outerCustomCanvas = document.createElement('canvas');
outerCustomCanvas.width = 800;
outerCustomCanvas.height = 1125;

function createCanvasTexture(canvas) {
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = renderer.capabilities.getMaxAnisotropy();
  texture.wrapS = THREE.ClampToEdgeWrapping;
  texture.wrapT = THREE.ClampToEdgeWrapping;
  return texture;
}

const customTextures = {
  inner: createCanvasTexture(innerCustomCanvas),
  outer: createCanvasTexture(outerCustomCanvas),
};

for (const kind of ['inner', 'outer']) {
  const defaultTextures = {};
  for (const [theme, canvases] of Object.entries(defaultUIs)) {
    const texture = createCanvasTexture(canvases[kind]);
    defaultTextures[theme] = texture;
  }
  const material = new THREE.MeshBasicMaterial({
    map: defaultTextures[uiTheme],
    toneMapped: false,
  });
  screens[kind] = { material, defaultTextures };
}

function drawCustomArtwork(img) {
  const inner = innerCustomCanvas.getContext('2d');
  inner.fillStyle = '#101418';
  inner.fillRect(0, 0, innerCustomCanvas.width, innerCustomCanvas.height);

  // Contain once at upload time. For the recommended Duo panorama aspect ratio,
  // this is effectively a 1:1 mapping with no runtime fit calculations.
  const scale = Math.min(innerCustomCanvas.width / img.width, innerCustomCanvas.height / img.height);
  const width = img.width * scale;
  const height = img.height * scale;
  inner.drawImage(
    img,
    (innerCustomCanvas.width - width) / 2,
    (innerCustomCanvas.height - height) / 2,
    width,
    height,
  );

  const outer = outerCustomCanvas.getContext('2d');
  outer.fillStyle = '#101418';
  outer.fillRect(0, 0, outerCustomCanvas.width, outerCustomCanvas.height);
  outer.drawImage(
    innerCustomCanvas,
    innerCustomCanvas.width / 2,
    0,
    innerCustomCanvas.width / 2,
    innerCustomCanvas.height,
    0,
    0,
    outerCustomCanvas.width,
    outerCustomCanvas.height,
  );

  customTextures.inner.needsUpdate = true;
  customTextures.outer.needsUpdate = true;
}

const uiInput = document.querySelector('#ui-upload');
uiInput.addEventListener('change', async () => {
  const file = uiInput.files[0];
  if (!file) return;
  const url = URL.createObjectURL(file);
  const img = new Image();
  img.src = url;
  try {
    await img.decode();
    drawCustomArtwork(img);
    screens.inner.material.map = customTextures.inner;
    screens.outer.material.map = customTextures.outer;
    screens.inner.material.needsUpdate = true;
    screens.outer.material.needsUpdate = true;
    uiTheme = 'custom';
    document.querySelectorAll('[data-ui-theme]').forEach(button => {
      button.setAttribute('aria-selected', String(button.dataset.uiTheme === uiTheme));
    });
    setPlaying(false);
    setAngle(0);
  } catch {
    alert('Unable to read this image. Choose a PNG, JPG, or WebP file.');
  } finally {
    URL.revokeObjectURL(url);
    uiInput.value = '';
  }
});

function showDefaultUI() {
  for (const [kind, screen] of Object.entries(screens)) {
    screen.material.map = screen.defaultTextures[uiTheme];
    screen.material.needsUpdate = true;
  }
  document.querySelectorAll('[data-ui-theme]').forEach(button => {
    button.setAttribute('aria-selected', String(button.dataset.uiTheme === uiTheme));
  });
}

document.querySelectorAll('[data-ui-theme]').forEach(button => button.addEventListener('click', () => {
  if (button.dataset.uiTheme === 'custom') {
    uiInput.click();
    return;
  }
  uiTheme = button.dataset.uiTheme;
  showDefaultUI();
  setPlaying(false);
  setAngle(0);
}));

function setPlaying(value) {
  playing = value;
  document.querySelector('#pause-icon').toggleAttribute('hidden', !value);
  document.querySelector('#play-icon').toggleAttribute('hidden', value);
  play.setAttribute('aria-label', value ? 'Pause animation' : 'Play animation');
}

function setAngle(value) {
  angle = THREE.MathUtils.clamp(value, 0, 180);
  slider.value = angle;
  slider.style.setProperty('--progress', `${angle / 1.8}%`);
  bend.value = (180 - angle) / 180 * Math.PI;

  // At full opening the cover display faces away from the viewer and is switched off.
  screens.outer.material.color.setScalar(angle >= 179.95 ? 0 : 1);
}

play.addEventListener('click', () => {
  if (playing) {
    setPlaying(false);
    return;
  }
  if (angle > .1) setAngle(0);
  playbackTime = 0;
  setPlaying(true);
});

slider.addEventListener('input', () => {
  setPlaying(false);
  setAngle(Number(slider.value));
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

// Geometry only. No projected-UI shader, blur, darkening, flash or image-space motion.
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
    const kind = object.name === 'UXtsBZYlaUvHoEh'
      ? 'inner'
      : object.name === 'hhgAIoCGsHXeDPY'
        ? 'outer'
        : null;
    const material = kind ? screens[kind].material : object.material.clone();

    // These UVs are authored once from the unfolded physical screen geometry and
    // never change with foldAngle. The image is therefore glued to the display.
    if (kind) {
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

    if (moving || flexible) {
      material.onBeforeCompile = shader => {
        shader.uniforms.foldAngle = bend;
        shader.vertexShader = `${flexible ? '#define FLEXIBLE_SCREEN\n' : ''}${foldShader}\n${shader.vertexShader}`;
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
      };
      material.customProgramCacheKey = () => `${flexible ? 'lv3-fold-flexible' : 'lv3-fold-cover'}-${kind || 'body'}`;
    }

    const mesh = new THREE.Mesh(geometry, material);
    mesh.name = object.name;
    mesh.frustumCulled = false;
    phone.add(mesh);
    count[flexible ? 'flexible' : moving ? 'moving' : 'fixed']++;
  });

  console.info('Lv3 Tower Anchor Lock ready', JSON.stringify({
    ...count,
    sourceMeshes: phone.children.length,
    fixedCamera: true,
    fixedUV: true,
    runtimeReprojection: false,
    foldFX: false,
  }));

  showDefaultUI();
  document.querySelectorAll('button, input').forEach(element => element.disabled = false);
  ready = true;
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

    // Deterministic 3.4 s ScreenToGif-friendly baseline:
    // 0.0–0.6 closed hold, 0.6–2.6 physical unfold, 2.6–3.4 open hold.
    if (playbackTime < .6) {
      setAngle(0);
    } else if (playbackTime < 2.6) {
      const p = (playbackTime - .6) / 2.0;
      const ease = p * p * (3 - 2 * p);
      setAngle(THREE.MathUtils.lerp(0, 180, ease));
    } else if (playbackTime < 3.4) {
      setAngle(180);
    } else {
      setAngle(180);
      setPlaying(false);
    }
  }

  renderer.render(scene, camera);
});
