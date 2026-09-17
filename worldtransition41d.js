import * as THREE from 'three';

// Step 4.1D — Unified World Shader Transition
//
// One visual authority for screen content:
// - Reality and RedBlack are mixed with the SAME worldMix on inner + outer screens.
// - worldMix happens mainly between 30% and 45% fold progress.
// - the moving cover then independently blurs, darkens and fades away.
// - the inner screen stays opaque and is revealed by the physical fold itself.
//
// This deliberately replaces Step 4.1C's "outer Reality / inner RedBlack" split.
// It also brings the proven blur/darken approach from the original
// chuspeeism/iphone-duo screen shader back onto the current fixed-UV materials.

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

function worldMixFromProgress(progress) {
  if (progress <= 0.30) return 0;
  if (progress >= 0.45) return 1;
  return smoothRange(progress, 0.30, 0.45);
}

function coverFxFromProgress(progress) {
  if (progress <= 0.25) return 0;
  if (progress >= 0.55) return 1;
  return smoothRange(progress, 0.25, 0.55);
}

function sampleCurve(progress, points) {
  const p = THREE.MathUtils.clamp(progress, 0, 1);
  if (p <= points[0][0]) return points[0][1];
  for (let i = 0; i < points.length - 1; i++) {
    const [p0, v0] = points[i];
    const [p1, v1] = points[i + 1];
    if (p <= p1) {
      return THREE.MathUtils.lerp(v0, v1, smoothRange(p, p0, p1));
    }
  }
  return points[points.length - 1][1];
}

const COVER_OPACITY = [
  [0.00, 1.00],
  [0.30, 1.00],
  [0.35, 0.90],
  [0.40, 0.72],
  [0.45, 0.48],
  [0.50, 0.22],
  [0.55, 0.00],
  [1.00, 0.00],
];

function customTransitionReady() {
  const customSelected = document.querySelector('[data-ui-theme="custom"]')
    ?.getAttribute('aria-selected') === 'true';
  const redBlackReady = document.querySelector('#redblack-button')
    ?.classList.contains('is-loaded');
  return Boolean(customSelected && redBlackReady);
}

function makeState() {
  return {
    inner: null,
    outer: null,
    wrappedInner: false,
    wrappedOuter: false,
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

function replaceLegacyMapFragment(shader) {
  const startMarker = '            #ifdef USE_MAP\n              vec4 sampledDiffuseColor = texture2D(map, vMapUv);';
  const endMarker = '              diffuseColor *= sampledDiffuseColor;\n            #endif';

  const start = shader.fragmentShader.indexOf(startMarker);
  const endStart = start >= 0
    ? shader.fragmentShader.indexOf(endMarker, start)
    : -1;

  if (start < 0 || endStart < 0) {
    console.warn('Step 4.1D could not find the legacy map fragment.');
    return false;
  }

  const end = endStart + endMarker.length;

  const replacement = `            #ifdef USE_MAP
              vec2 worldUv = vMapUv;
              vec2 uiPixel41d = 1.0 / vec2(textureSize(map, 0));

              vec4 realitySample = texture2D(map, worldUv);
              vec4 redBlackSample = texture2D(transitionTarget, worldUv);

              // Before the actual texture hand-off, warm the Reality plate slightly
              // so the blue-hour world begins to feel contaminated by RedBlack.
              float preheat41d = smoothstep(0.25, 0.38, foldProgress41d)
                * (1.0 - worldMix41d);
              realitySample.rgb *= vec3(
                1.0 + 0.12 * preheat41d,
                1.0 - 0.035 * preheat41d,
                1.0 - 0.17 * preheat41d
              );

              float blurGradient41d = clamp(worldUv.x, 0.0, 1.0);
              float darkenGradient41d = clamp((worldUv.x - 0.2) / 0.8, 0.0, 1.0);
              float motion41d = coverFx41d * isOuter41d;
              float effect41d = motion41d * pow(darkenGradient41d, 1.35);
              float radius41d = 72.0 * motion41d * pow(blurGradient41d, 1.35);

              vec2 aa41d = max(fwidth(worldUv), uiPixel41d * 0.5);
              vec2 derivX41d = dFdx(worldUv) / uiPixel41d;
              vec2 derivY41d = dFdy(worldUv) / uiPixel41d;
              float baseLod41d = log2(max(1.0, max(length(derivX41d), length(derivY41d))));

              vec2 coverage41d = smoothstep(-aa41d, aa41d, worldUv)
                * (1.0 - smoothstep(vec2(1.0) - aa41d, vec2(1.0) + aa41d, worldUv));

              vec3 realityColor41d = realitySample.rgb;
              vec3 redBlackColor41d = redBlackSample.rgb;
              vec3 color41d = mix(realityColor41d, redBlackColor41d, worldMix41d)
                * coverage41d.x * coverage41d.y;

              if (radius41d > 0.0) {
                float lod41d = max(baseLod41d, log2(max(1.0, radius41d)));
                vec2 footprint41d = max(aa41d, uiPixel41d * radius41d * 0.75);
                color41d = vec3(0.0);

                for (int y41d = -2; y41d <= 2; y41d++) {
                  for (int x41d = -2; x41d <= 2; x41d++) {
                    float wx41d = x41d == 0 ? 6.0 : (abs(x41d) == 1 ? 4.0 : 1.0);
                    float wy41d = y41d == 0 ? 6.0 : (abs(y41d) == 1 ? 4.0 : 1.0);
                    vec2 sampleUv41d = worldUv
                      + vec2(float(x41d), float(y41d)) * uiPixel41d * radius41d;

                    vec2 sampleCoverage41d = smoothstep(
                      -footprint41d,
                      footprint41d,
                      sampleUv41d
                    ) * (1.0 - smoothstep(
                      vec2(1.0) - footprint41d,
                      vec2(1.0) + footprint41d,
                      sampleUv41d
                    ));

                    vec2 clampedUv41d = clamp(sampleUv41d, vec2(0.0), vec2(1.0));
                    vec3 realityTap41d = textureLod(map, clampedUv41d, lod41d).rgb;
                    vec3 redBlackTap41d = textureLod(transitionTarget, clampedUv41d, lod41d).rgb;

                    // Keep the same global worldMix on BOTH physical screens.
                    vec3 worldTap41d = mix(realityTap41d, redBlackTap41d, worldMix41d);
                    color41d += worldTap41d
                      * sampleCoverage41d.x
                      * sampleCoverage41d.y
                      * wx41d
                      * wy41d
                      / 256.0;
                  }
                }
              }

              color41d *= (1.0 - min(1.0, effect41d * 1.65));

              vec4 sampledDiffuseColor = vec4(
                color41d,
                mix(realitySample.a, redBlackSample.a, worldMix41d)
              );

              #ifdef DECODE_VIDEO_TEXTURE
                sampledDiffuseColor = sRGBTransferEOTF(sampledDiffuseColor);
              #endif

              diffuseColor *= sampledDiffuseColor;
              diffuseColor.a *= mix(1.0, coverOpacity41d, isOuter41d);
            #endif`;

  shader.fragmentShader = shader.fragmentShader.slice(0, start)
    + replacement
    + shader.fragmentShader.slice(end);

  return true;
}

function wrapScreen(mesh, kind) {
  const material = mesh?.material;
  if (!material || material.userData?.worldTransition41dWrapped) return;

  const originalCompile = material.onBeforeCompile;
  material.onBeforeCompile = shader => {
    if (originalCompile) originalCompile(shader);

    shader.uniforms.worldMix41d = { value: 0 };
    shader.uniforms.foldProgress41d = { value: 0 };
    shader.uniforms.coverFx41d = { value: 0 };
    shader.uniforms.coverOpacity41d = { value: 1 };
    shader.uniforms.isOuter41d = { value: kind === 'outer' ? 1 : 0 };

    shader.fragmentShader = `
      uniform float worldMix41d;
      uniform float foldProgress41d;
      uniform float coverFx41d;
      uniform float coverOpacity41d;
      uniform float isOuter41d;
      ${shader.fragmentShader}
    `;

    replaceLegacyMapFragment(shader);
    material.userData.worldTransition41dShader = shader;
  };

  const oldKey = material.customProgramCacheKey?.bind(material);
  material.customProgramCacheKey = () => `${oldKey ? oldKey() : 'screen'}-world41d-${kind}`;
  material.userData.worldTransition41dWrapped = true;

  if (kind === 'outer') {
    material.transparent = true;
    material.depthWrite = false;
  }

  material.needsUpdate = true;
}

function updateScreenUniforms(mesh, values) {
  const shader = mesh?.material?.userData?.worldTransition41dShader;
  if (!shader) return;
  shader.uniforms.worldMix41d.value = values.worldMix;
  shader.uniforms.foldProgress41d.value = values.progress;
  shader.uniforms.coverFx41d.value = values.coverFx;
  shader.uniforms.coverOpacity41d.value = values.coverOpacity;

  // Neutralize the old spatial reveal authority. We keep its target texture only
  // because it is the already-correct RedBlack texture uploaded by main.js.
  if (shader.uniforms.transitionSpatialMode) {
    shader.uniforms.transitionSpatialMode.value = 0;
  }
}

function updateUI(worldMix) {
  const percent = Math.round(worldMix * 100);
  const revealReadout = document.querySelector('#reveal-readout');
  const revealSummaryValue = document.querySelector('#reveal-summary-value');
  const strategySummary = document.querySelector('#strategy-summary');
  const revealSettings = document.querySelector('#reveal-settings');

  if (revealReadout) revealReadout.textContent = `World ${percent}%`;
  if (revealSummaryValue) revealSummaryValue.textContent = `${percent}%`;
  if (strategySummary) strategySummary.textContent = 'World';
  if (revealSettings) revealSettings.hidden = true;
}

THREE.WebGLRenderer.prototype.render = function unifiedWorldRender(scene, camera) {
  const state = rendererState.get(this) || makeState();
  if (!rendererState.has(this)) rendererState.set(this, state);

  if (
    this.getRenderTarget() === null
    && scene?.isScene
    && !scene?.userData?.skipMotionBlur
  ) {
    if (findScreens(scene, state)) {
      wrapScreen(state.inner, 'inner');
      wrapScreen(state.outer, 'outer');

      const progress = THREE.MathUtils.clamp(
        Number(document.querySelector('#angle')?.value || 0) / 180,
        0,
        1,
      );

      const active = customTransitionReady();
      const worldMix = active ? worldMixFromProgress(progress) : 0;
      const coverFx = active ? coverFxFromProgress(progress) : 0;
      const coverOpacity = active ? sampleCurve(progress, COVER_OPACITY) : 1;

      updateScreenUniforms(state.inner, {
        progress,
        worldMix,
        coverFx: 0,
        coverOpacity: 1,
      });

      updateScreenUniforms(state.outer, {
        progress,
        worldMix,
        coverFx,
        coverOpacity,
      });

      if (state.outer?.material) {
        state.outer.material.opacity = coverOpacity;
      }
      if (state.inner?.material) {
        state.inner.material.opacity = 1;
      }

      if (active) updateUI(worldMix);
      document.documentElement.dataset.transitionMode = 'world41d';
      document.documentElement.style.setProperty('--world-mix', worldMix.toFixed(3));
      document.documentElement.style.setProperty('--cover-opacity', coverOpacity.toFixed(3));
    }
  }

  return previousRender.call(this, scene, camera);
};

console.info('Step 4.1D unified world shader transition ready', {
  worldMixWindow: [0.30, 0.45],
  coverFadeEnd: 0.55,
  originalShaderBlurRestored: true,
  innerOuterShareWorldState: true,
  oldSpatialRevealDisabled: true,
  framingUntouched: true,
  shellMotionBlurUntouched: true,
});
