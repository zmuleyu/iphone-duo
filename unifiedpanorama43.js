import * as THREE from 'three';

// v4.3 — Unified Panorama Coordinates
//
// Goal: Reality and RedBlack each remain ONE full 1600x1125 panorama.
// Inner and outer screens are only two physical views into the SAME panorama.
// This restores the original project's fixed front-view projection logic while
// preserving v4.1D's world mix, v4.2's geometry timing, fixed UV framing and shell blur.

const previousRender = THREE.WebGLRenderer.prototype.render;
const rendererState = new WeakMap();

const INNER_NAME = 'UXtsBZYlaUvHoEh';
const OUTER_NAME = 'hhgAIoCGsHXeDPY';

function makeState() {
  return {
    inner: null,
    outer: null,
    sharedReality: null,
    sharedTarget: null,
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

function isCustomSelected() {
  return document.querySelector('[data-ui-theme="custom"]')?.getAttribute('aria-selected') === 'true';
}

function wrapScreenMaterial(mesh, kind) {
  const material = mesh?.material;
  if (!material || material.userData?.panorama43Wrapped) return;

  const originalCompile = material.onBeforeCompile;
  material.onBeforeCompile = shader => {
    if (originalCompile) originalCompile(shader);

    shader.uniforms.panoramaActive43 = { value: 0 };

    shader.vertexShader = `varying vec3 vUIPosition43;\n${shader.vertexShader}`;
    shader.fragmentShader = `varying vec3 vUIPosition43;\nuniform float panoramaActive43;\n${shader.fragmentShader}`;

    // Capture the already-folded local screen position. main_v41d4 has already
    // replaced transformed for the moving/flexible meshes before this wrapper runs.
    shader.vertexShader = shader.vertexShader.replace(
      '#include <project_vertex>',
      'vUIPosition43 = transformed;\n#include <project_vertex>',
    );

    // Replace only the source coordinate definition inside the existing unified
    // world shader. All Reality/RedBlack mixing, blur, darken and alpha logic stays intact.
    shader.fragmentShader = shader.fragmentShader.replace(
      'vec2 worldUv = vMapUv;',
      `vec2 worldUv = vMapUv;
       if (panoramaActive43 > 0.5) {
         // Original iPhone Duo fixed front-view panorama projection.
         const vec3 eye43 = vec3(0.0, 0.0, 40.0);
         const vec4 frame43 = vec4(-7.89935, -5.55178, 15.7987, 11.1035);

         float depth43 = (0.24948 - eye43.z) / (vUIPosition43.z - eye43.z);
         vec2 projected43 = eye43.xy + (vUIPosition43.xy - eye43.xy) * depth43;
         vec2 sourceUv43 = (projected43 - frame43.xy) / frame43.zw;

         if (isOuter > 0.5) {
           // Keep the outer view anchored to the projected hinge-side edge.
           // This makes it a moving viewport into the SAME panorama rather than
           // a separately cropped image pasted onto the cover.
           float foldAngle43 = (1.0 - foldProgress) * 3.141592654;
           float c43 = cos(foldAngle43);
           float s43 = sin(foldAngle43);
           vec2 hingeEdge43 = vec2(-0.23396, -0.27463 - 0.275454);
           vec2 foldedEdge43 = vec2(
             c43 * hingeEdge43.x + s43 * hingeEdge43.y,
             -s43 * hingeEdge43.x + c43 * hingeEdge43.y + 0.275454
           );
           float edgeDepth43 = (0.24948 - eye43.z) / (foldedEdge43.y - eye43.z);
           float anchorX43 = eye43.x + (foldedEdge43.x - eye43.x) * edgeDepth43;
           sourceUv43.x = 0.5 + (projected43.x - anchorX43) / frame43.z;
         }

         worldUv = sourceUv43;
       }`,
    );

    material.userData.panorama43Shader = shader;
  };

  const previousKey = material.customProgramCacheKey?.bind(material);
  material.customProgramCacheKey = () => `${previousKey ? previousKey() : 'screen'}-panorama43-${kind}`;
  material.userData.panorama43Wrapped = true;
  material.needsUpdate = true;
}

function syncSharedPanorama(state, active) {
  if (!active || !state.inner || !state.outer) return;

  // Reality: use the inner/full panorama texture for BOTH physical screens.
  const innerReality = state.inner.material?.map;
  if (innerReality && state.outer.material?.map !== innerReality) {
    state.outer.material.map = innerReality;
    state.sharedReality = innerReality;
  }

  const innerShader = state.inner.material?.userData?.panorama43Shader;
  const outerShader = state.outer.material?.userData?.panorama43Shader;

  if (innerShader?.uniforms?.panoramaActive43) innerShader.uniforms.panoramaActive43.value = 1;
  if (outerShader?.uniforms?.panoramaActive43) outerShader.uniforms.panoramaActive43.value = 1;

  // RedBlack target: share the inner/full panorama target as well.
  const innerTarget = innerShader?.uniforms?.transitionTarget?.value;
  if (innerTarget && outerShader?.uniforms?.transitionTarget) {
    outerShader.uniforms.transitionTarget.value = innerTarget;
    state.sharedTarget = innerTarget;
  }

  document.documentElement.dataset.panoramaMode = 'unified43';
}

function disableUnifiedMode(state) {
  const innerShader = state.inner?.material?.userData?.panorama43Shader;
  const outerShader = state.outer?.material?.userData?.panorama43Shader;
  if (innerShader?.uniforms?.panoramaActive43) innerShader.uniforms.panoramaActive43.value = 0;
  if (outerShader?.uniforms?.panoramaActive43) outerShader.uniforms.panoramaActive43.value = 0;
}

THREE.WebGLRenderer.prototype.render = function unifiedPanorama43Render(scene, camera) {
  const state = rendererState.get(this) || makeState();
  if (!rendererState.has(this)) rendererState.set(this, state);

  if (
    this.getRenderTarget() === null
    && scene?.isScene
    && !scene?.userData?.skipMotionBlur
    && findScreens(scene, state)
  ) {
    wrapScreenMaterial(state.inner, 'inner');
    wrapScreenMaterial(state.outer, 'outer');

    const active = isCustomSelected();
    if (active) syncSharedPanorama(state, true);
    else disableUnifiedMode(state);

    const subtitle = document.querySelector('.timeline-title-block span');
    if (subtitle && active) subtitle.textContent = 'Unified panorama · geometry-driven world hand-off';
  }

  return previousRender.call(this, scene, camera);
};

console.info('iPhone Duo v4.3 unified panorama coordinates ready', {
  sharedRealityTexture: true,
  sharedRedBlackTexture: true,
  projection: 'fixed-front-view + projected hinge anchor',
  timing: 'v4.2 geometry-driven',
});
