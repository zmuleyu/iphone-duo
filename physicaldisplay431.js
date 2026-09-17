import * as THREE from 'three';

// v4.3.1 — Physical Inner Panorama + Left-Panel Defocus
//
// Root-cause correction for v4.3:
// 1) The moving left panel seen after the fold crosses toward the viewer is the
//    LEFT HALF OF THE INNER FLEXIBLE DISPLAY, not the external cover screen.
// 2) The original chuspeeism implementation already models this correctly with
//    one panorama projection plus a kind-specific uiGradient. For INNER_UI the
//    blur gradient runs from the hinge (u=.5) toward the moving left edge (u=0).
// 3) The external cover remains useful only near Closed. It fades out early so
//    it cannot visually compete with the continuous inner panorama.
//
// This module intentionally becomes the only post-main screen coordinator. It
// keeps v4.1D's world mix shader, but replaces its coordinate/blur timing with
// the original fixed-front projection and original inner/outer blur geometry.

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

function geometrySignal(angleDeg) {
  const visualAngle = THREE.MathUtils.clamp(angleDeg, 0, 90);
  return 1 - Math.cos(THREE.MathUtils.degToRad(visualAngle));
}

function worldMixFromGeometry(g) {
  // Keep v4.2 timing for now. Timing will be tuned after the spatial model is frozen.
  return smoothRange(g, 0.10, 0.92);
}

function outerOpacityFromGeometry(g) {
  // The external cover must stop dominating before the inner left half becomes
  // the cinematic foreground. This is deliberately earlier than v4.2.
  // ~15% Fold: almost fully present; ~25%: around half; ~35%: gone.
  return 1 - smoothRange(g, 0.06, 0.50);
}

function makeState() {
  return {
    inner: null,
    outer: null,
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

function isCustomReady() {
  const custom = document.querySelector('[data-ui-theme="custom"]');
  const redBlack = document.querySelector('#redblack-button');
  return custom?.getAttribute('aria-selected') === 'true'
    && Boolean(redBlack?.classList.contains('is-loaded') || redBlack?.textContent?.includes('✓'));
}

function patchScreenMaterial(mesh, kind) {
  const material = mesh?.material;
  if (!material || material.userData?.physical431Wrapped) return;

  const originalCompile = material.onBeforeCompile;
  material.onBeforeCompile = shader => {
    if (originalCompile) originalCompile(shader);

    shader.vertexShader = `varying vec3 vUIPosition431;\n${shader.vertexShader}`;
    shader.fragmentShader = `varying vec3 vUIPosition431;\n${shader.fragmentShader}`;

    // Same hook as the original project: transformed already contains the fold
    // deformation before project_vertex executes.
    shader.vertexShader = shader.vertexShader.replace(
      '#include <project_vertex>',
      'vUIPosition431 = transformed;\n#include <project_vertex>',
    );

    // Replace v4.1D's raw vMapUv sampling with the original fixed-front ray
    // projection. Both screens now sample the SAME full panorama coordinates.
    shader.fragmentShader = shader.fragmentShader.replace(
      'vec2 worldUv = vMapUv;',
      `vec2 worldUv = vMapUv;
       {
         const vec3 eye431 = vec3(0.0, 0.0, 40.0);
         const vec4 frame431 = vec4(-7.89935, -5.55178, 15.7987, 11.1035);

         float depth431 = (0.24948 - eye431.z) / (vUIPosition431.z - eye431.z);
         vec2 projected431 = eye431.xy + (vUIPosition431.xy - eye431.xy) * depth431;
         vec2 sourceUv431 = (projected431 - frame431.xy) / frame431.zw;

         if (isOuter > 0.5) {
           // Original projected hinge-side anchor for the external cover.
           float foldAngle431 = (1.0 - foldProgress) * 3.141592654;
           float c431 = cos(foldAngle431);
           float s431 = sin(foldAngle431);
           vec2 hingeEdge431 = vec2(-0.23396, -0.27463 - 0.275454);
           vec2 foldedEdge431 = vec2(
             c431 * hingeEdge431.x + s431 * hingeEdge431.y,
             -s431 * hingeEdge431.x + c431 * hingeEdge431.y + 0.275454
           );
           float edgeDepth431 = (0.24948 - eye431.z) / (foldedEdge431.y - eye431.z);
           float anchorX431 = eye431.x + (foldedEdge431.x - eye431.x) * edgeDepth431;
           sourceUv431.x = 0.5 + (projected431.x - anchorX431) / frame431.z;
         }

         worldUv = sourceUv431;
       }`,
    );

    // Replace v4.1D's outer-only blur with the ORIGINAL two-sided fold logic:
    // - INNER display: hinge u=.5 -> moving LEFT edge u=0 blurs/darkens.
    // - OUTER cover: hinge u=.5 -> outside RIGHT edge u=1 blurs/darkens.
    // This is the missing behavior visible in the Spline reference.
    const oldBlurBlock = `float blurGradient = clamp(worldUv.x, 0.0, 1.0);
              float darkenGradient = clamp((worldUv.x - 0.2) / 0.8, 0.0, 1.0);
              float motion = coverFx * isOuter;
              float effect = motion * pow(darkenGradient, 1.35);
              float radius = 72.0 * motion * pow(blurGradient, 1.35);`;

    const newBlurBlock = `float gradientStart431 = 0.5;
              float gradientEnd431 = isOuter > 0.5 ? 1.0 : 0.0;
              float edge431 = (worldUv.x - gradientStart431) / (gradientEnd431 - gradientStart431);
              float blurGradient = clamp(edge431, 0.0, 1.0);
              float darkenGradient = clamp((edge431 - 0.2) / 0.8, 0.0, 1.0);

              // Recreate the original physical screen progress instead of using
              // a generic outer-only effect. foldProgress is 0=Closed, 1=Open.
              float innerMotion431 = smoothstep(0.0, 1.0, clamp((1.0 - foldProgress) * 2.0, 0.0, 1.0));
              float outerMotion431 = smoothstep(0.0, 1.0, clamp(foldProgress * 2.0, 0.0, 1.0));
              float motion = mix(innerMotion431, outerMotion431, isOuter);
              float effect = motion * pow(darkenGradient, 1.35);
              float radius = 72.0 * motion * pow(blurGradient, 1.35);`;

    if (!shader.fragmentShader.includes(oldBlurBlock)) {
      console.error('v4.3.1 blur block not found; shader layout changed');
      material.userData.physical431ShaderError = 'blur-block-not-found';
    } else {
      shader.fragmentShader = shader.fragmentShader.replace(oldBlurBlock, newBlurBlock);
    }

    material.userData.physical431Shader = shader;
  };

  const previousKey = material.customProgramCacheKey?.bind(material);
  material.customProgramCacheKey = () => `${previousKey ? previousKey() : 'screen'}-physical431-${kind}`;
  material.userData.physical431Wrapped = true;

  if (kind === 'outer') {
    material.transparent = true;
    material.depthWrite = false;
  }

  material.needsUpdate = true;
}

function syncSharedTextures(state) {
  const innerMaterial = state.inner?.material;
  const outerMaterial = state.outer?.material;
  const innerShader = innerMaterial?.userData?.physical431Shader;
  const outerShader = outerMaterial?.userData?.physical431Shader;

  if (!innerMaterial || !outerMaterial) return;

  // ONE Reality panorama: the full inner texture is the source for both physical screens.
  if (innerMaterial.map && outerMaterial.map !== innerMaterial.map) {
    outerMaterial.map = innerMaterial.map;
  }

  // ONE RedBlack panorama: the full inner target is the source for both screens.
  const innerTarget = innerShader?.uniforms?.transitionTarget?.value;
  if (innerTarget && outerShader?.uniforms?.transitionTarget) {
    outerShader.uniforms.transitionTarget.value = innerTarget;
  }
}

function updateUniforms(state, angleDeg) {
  const active = isCustomReady();
  if (!active) return;

  const g = geometrySignal(angleDeg);
  const worldMix = worldMixFromGeometry(g);
  const outerOpacity = outerOpacityFromGeometry(g);
  const progress = THREE.MathUtils.clamp(angleDeg / 180, 0, 1);

  for (const [kind, mesh] of [['inner', state.inner], ['outer', state.outer]]) {
    const shader = mesh?.material?.userData?.physical431Shader;
    if (!shader) continue;

    if (shader.uniforms.worldMix) shader.uniforms.worldMix.value = worldMix;
    if (shader.uniforms.foldProgress) shader.uniforms.foldProgress.value = progress;
    if (shader.uniforms.coverFx) shader.uniforms.coverFx.value = 1;
    if (shader.uniforms.coverOpacity) shader.uniforms.coverOpacity.value = kind === 'outer' ? outerOpacity : 1;
  }

  const readout = document.querySelector('#reveal-readout');
  const summary = document.querySelector('#reveal-summary-value');
  const strategy = document.querySelector('#strategy-summary');
  const subtitle = document.querySelector('.timeline-title-block span');

  if (readout) readout.textContent = `World ${Math.round(worldMix * 100)}%`;
  if (summary) summary.textContent = `${Math.round(worldMix * 100)}%`;
  if (strategy) strategy.textContent = 'Inner';
  if (subtitle) subtitle.textContent = 'One panorama · inner left-panel defocus';

  document.documentElement.dataset.displayModel = 'physical-inner-431';
  document.documentElement.style.setProperty('--world-mix', worldMix.toFixed(4));
  document.documentElement.style.setProperty('--outer-opacity', outerOpacity.toFixed(4));
}

THREE.WebGLRenderer.prototype.render = function physicalDisplay431Render(scene, camera) {
  const state = rendererState.get(this) || makeState();
  if (!rendererState.has(this)) rendererState.set(this, state);

  if (
    this.getRenderTarget() === null
    && scene?.isScene
    && !scene?.userData?.skipMotionBlur
    && findScreens(scene, state)
  ) {
    patchScreenMaterial(state.inner, 'inner');
    patchScreenMaterial(state.outer, 'outer');
    syncSharedTextures(state);
    updateUniforms(state, Number(document.querySelector('#angle')?.value || 0));
  }

  return previousRender.call(this, scene, camera);
};

console.info('iPhone Duo v4.3.1 physical inner panorama ready', {
  sharedPanorama: true,
  externalCover: 'early fade-out',
  innerMovingHalfBlur: true,
  innerBlurDirection: 'hinge .5 -> left edge 0',
  outerBlurDirection: 'hinge .5 -> right edge 1',
  projection: 'original fixed-front ray projection',
});
