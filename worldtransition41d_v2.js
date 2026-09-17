import * as THREE from 'three';

// Step 4.1D v2 — Unified World Shader Transition
//
// Why v2 exists:
// - v1 was loaded before main.js and tried to wrap materials indirectly.
// - The deployed page still showed the old Reveal/Lead UI and the old
//   Reality-vs-RedBlack split, proving the unified transition was not actually
//   becoming the active screen authority.
// - v2 is loaded AFTER main.js, so the Duo model and screen materials already
//   exist when this renderer wrapper starts observing them.
// - The shader replacement is marker-based rather than indentation/exact-string
//   based, so it survives formatting differences in main.js.
//
// One authority for screen content:
// - inner + outer share the SAME worldMix (Reality -> RedBlack)
// - the hand-off happens mainly from 30% to 45% Fold
// - only the moving outer/cover gets the original-style hinge-gradient
//   blur + darken + opacity fade
// - the inner display stays sharp and opaque
// - Step 3.7.2 framing and Step 3.8.1 shell motion blur stay untouched

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

function coverOpacityFromProgress(progress) {
  const p = THREE.MathUtils.clamp(progress, 0, 1);
  const points = [
    [0.00, 1.00],
    [0.30, 1.00],
    [0.35, 0.90],
    [0.40, 0.72],
    [0.45, 0.48],
    [0.50, 0.22],
    [0.55, 0.00],
    [1.00, 0.00],
  ];

  for (let i = 0; i < points.length - 1; i++) {
    const [p0, v0] = points[i];
    const [p1, v1] = points[i + 1];
    if (p <= p1) {
      return THREE.MathUtils.lerp(v0, v1, smoothRange(p, p0, p1));
    }
  }
  return 0;
}

function isCustomTransitionReady() {
  // Keep this deliberately simple and visible: once RedBlack shows the loaded
  // state in the current UI, the unified world transition is active.
  const button = document.querySelector('#redblack-button');
  return Boolean(
    button
    && (button.classList.contains('is-loaded') || button.textContent?.includes('✓'))
  );
}

function makeState() {
  return {
    inner: null,
    outer: null,
    lastReady: false,
    compileFailures: 0,
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

function replaceCurrentScreenMapBlock(shader) {
  const source = shader.fragmentShader;

  // main.js replaces <map_fragment> with a custom USE_MAP block. Locate the
  // block using semantic markers rather than exact whitespace.
  const sampleMarker = 'vec4 sampledDiffuseColor = texture2D(map, vMapUv);';
  const multiplyMarker = 'diffuseColor *= sampledDiffuseColor;';

  const sampleAt = source.indexOf(sampleMarker);
  if (sampleAt < 0) return false;

  const blockStart = source.lastIndexOf('#ifdef USE_MAP', sampleAt);
  const multiplyAt = source.indexOf(multiplyMarker, sampleAt);
  if (blockStart < 0 || multiplyAt < 0) return false;

  const blockEnd = source.indexOf('#endif', multiplyAt);
  if (blockEnd < 0) return false;

  const replaceEnd = blockEnd + '#endif'.length;

  const replacement = `#ifdef USE_MAP
    vec2 worldUv41d = vMapUv;
    vec2 texSize41d = vec2(textureSize(map, 0));
    vec2 uiPixel41d = 1.0 / max(texSize41d, vec2(1.0));

    vec4 reality41d = texture2D(map, worldUv41d);
    vec4 redBlack41d = texture2D(transitionTarget, worldUv41d);

    // 25-38%: warm Reality before the actual texture hand-off so the color
    // transition feels motivated rather than like a hard content swap.
    float preheat41d = smoothstep(0.25, 0.38, foldProgress41d)
      * (1.0 - worldMix41d);
    reality41d.rgb *= vec3(
      1.0 + 0.14 * preheat41d,
      1.0 - 0.045 * preheat41d,
      1.0 - 0.20 * preheat41d
    );

    // Both physical screens use the SAME world state.
    vec4 world41d = mix(reality41d, redBlack41d, worldMix41d);

    // Original-project style cover blur/darken: hinge side stays relatively
    // sharp; the outside edge becomes increasingly soft as the cover opens.
    float blurGradient41d = clamp(worldUv41d.x, 0.0, 1.0);
    float darkenGradient41d = clamp((worldUv41d.x - 0.2) / 0.8, 0.0, 1.0);
    float motion41d = coverFx41d * isOuter41d;
    float effect41d = motion41d * pow(darkenGradient41d, 1.35);
    float radius41d = 72.0 * motion41d * pow(blurGradient41d, 1.35);

    vec2 aa41d = max(fwidth(worldUv41d), uiPixel41d * 0.5);
    vec2 dx41d = dFdx(worldUv41d) / uiPixel41d;
    vec2 dy41d = dFdy(worldUv41d) / uiPixel41d;
    float baseLod41d = log2(max(1.0, max(length(dx41d), length(dy41d))));

    vec2 coverage41d = smoothstep(-aa41d, aa41d, worldUv41d)
      * (1.0 - smoothstep(vec2(1.0) - aa41d, vec2(1.0) + aa41d, worldUv41d));

    vec3 color41d = world41d.rgb * coverage41d.x * coverage41d.y;

    if (radius41d > 0.0) {
      float lod41d = max(baseLod41d, log2(max(1.0, radius41d)));
      vec2 footprint41d = max(aa41d, uiPixel41d * radius41d * 0.75);
      color41d = vec3(0.0);

      for (int y41d = -2; y41d <= 2; y41d++) {
        for (int x41d = -2; x41d <= 2; x41d++) {
          float wx41d = x41d == 0 ? 6.0 : (abs(x41d) == 1 ? 4.0 : 1.0);
          float wy41d = y41d == 0 ? 6.0 : (abs(y41d) == 1 ? 4.0 : 1.0);
          vec2 sampleUv41d = worldUv41d
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

    color41d *= (1.0 - min(1.0, effect41d * 1.75));

    vec4 sampledDiffuseColor = vec4(world41d.rgb, world41d.a);
    sampledDiffuseColor.rgb = mix(sampledDiffuseColor.rgb, color41d, isOuter41d);

    #ifdef DECODE_VIDEO_TEXTURE
      sampledDiffuseColor = sRGBTransferEOTF(sampledDiffuseColor);
    #endif

    diffuseColor *= sampledDiffuseColor;
    diffuseColor.a *= mix(1.0, coverOpacity41d, isOuter41d);
  #endif`;

  shader.fragmentShader = source.slice(0, blockStart)
    + replacement
    + source.slice(replaceEnd);

  return true;
}

function wrapScreen(mesh, kind, state) {
  const material = mesh?.material;
  if (!material || material.userData?.world41dV2Wrapped) return;

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

    const replaced = replaceCurrentScreenMapBlock(shader);
    if (!replaced) {
      state.compileFailures += 1;
      console.error('Step 4.1D v2 failed to replace the current screen map block', {
        kind,
        compileFailures: state.compileFailures,
      });
    }

    material.userData.world41dV2Shader = shader;
    material.userData.world41dV2Replaced = replaced;
  };

  const oldKey = material.customProgramCacheKey?.bind(material);
  material.customProgramCacheKey = () => `${oldKey ? oldKey() : 'screen'}-world41d-v2-${kind}`;
  material.userData.world41dV2Wrapped = true;

  // Cover alpha is controlled in the shader. Disable depth writes so a nearly
  // transparent cover cannot continue hiding the inner display.
  if (kind === 'outer') {
    material.transparent = true;
    material.depthWrite = false;
    material.opacity = 1;
  }

  material.needsUpdate = true;
}

function updateUniforms(mesh, values) {
  const material = mesh?.material;
  const shader = material?.userData?.world41dV2Shader;
  if (!shader) return false;

  shader.uniforms.worldMix41d.value = values.worldMix;
  shader.uniforms.foldProgress41d.value = values.progress;
  shader.uniforms.coverFx41d.value = values.coverFx;
  shader.uniforms.coverOpacity41d.value = values.coverOpacity;

  // Explicitly neutralize the legacy spatial reveal. transitionTarget remains
  // useful because main.js already points it at the uploaded RedBlack texture.
  if (shader.uniforms.transitionMix) shader.uniforms.transitionMix.value = values.worldMix;
  if (shader.uniforms.transitionSpatialMode) shader.uniforms.transitionSpatialMode.value = 0;

  return Boolean(material.userData.world41dV2Replaced);
}

function updateVisibleUI(worldMix, coverOpacity, active, replaced) {
  if (!active) return;

  const percent = Math.round(worldMix * 100);
  const revealReadout = document.querySelector('#reveal-readout');
  const revealSummaryValue = document.querySelector('#reveal-summary-value');
  const strategySummary = document.querySelector('#strategy-summary');
  const revealSettings = document.querySelector('#reveal-settings');
  const subtitle = document.querySelector('.timeline-title-block span');

  if (revealReadout) revealReadout.textContent = `World ${percent}%`;
  if (revealSummaryValue) revealSummaryValue.textContent = `${percent}%`;
  if (strategySummary) strategySummary.textContent = replaced ? 'World' : 'World ERR';
  if (revealSettings) revealSettings.hidden = true;
  if (subtitle) subtitle.textContent = 'Reality → RedBlack unified world hand-off';

  document.documentElement.dataset.world41d = replaced ? 'active' : 'compile-error';
  document.documentElement.style.setProperty('--world-mix', worldMix.toFixed(3));
  document.documentElement.style.setProperty('--cover-opacity', coverOpacity.toFixed(3));
}

THREE.WebGLRenderer.prototype.render = function world41dV2Render(scene, camera) {
  const state = rendererState.get(this) || makeState();
  if (!rendererState.has(this)) rendererState.set(this, state);

  if (
    this.getRenderTarget() === null
    && scene?.isScene
    && !scene?.userData?.skipMotionBlur
  ) {
    if (findScreens(scene, state)) {
      wrapScreen(state.inner, 'inner', state);
      wrapScreen(state.outer, 'outer', state);

      const progress = THREE.MathUtils.clamp(
        Number(document.querySelector('#angle')?.value || 0) / 180,
        0,
        1,
      );
      const active = isCustomTransitionReady();
      const worldMix = active ? worldMixFromProgress(progress) : 0;
      const coverFx = active ? coverFxFromProgress(progress) : 0;
      const coverOpacity = active ? coverOpacityFromProgress(progress) : 1;

      const innerReady = updateUniforms(state.inner, {
        progress,
        worldMix,
        coverFx: 0,
        coverOpacity: 1,
      });
      const outerReady = updateUniforms(state.outer, {
        progress,
        worldMix,
        coverFx,
        coverOpacity,
      });

      // main.js otherwise keeps driving the old Reveal UI every setAngle().
      // This runs every render and visibly proves whether v2 is actually active.
      updateVisibleUI(
        worldMix,
        coverOpacity,
        active,
        innerReady && outerReady,
      );
    }
  }

  return previousRender.call(this, scene, camera);
};

console.info('Step 4.1D v2 unified world shader transition loaded', {
  loadOrder: 'after-main',
  worldMixWindow: [0.30, 0.45],
  coverFadeEnd: 0.55,
  originalStyleBlur: true,
  semanticShaderReplacement: true,
});
